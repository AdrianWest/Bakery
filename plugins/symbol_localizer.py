"""!
Copyright (C) 2026 Adrian West

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
@file symbol_localizer.py

@brief Symbol localization for Bakery plugin

Handles localization of schematic symbols:
- Scanning schematic files for symbol references
- Copying symbols from global to local libraries
- Updating symbol library tables
- Updating symbol references in schematics

@section description_symbol_localizer Detailed Description
This module provides the SymbolLocalizer class which manages the complete
lifecycle of symbol localization from global KiCad libraries to project-local
libraries. It parses .kicad_sch files, extracts symbol definitions from global
.kicad_sym libraries, and creates consolidated local symbol libraries.

@section notes_symbol_localizer Notes
- Supports KiCad 10 environment variable formats; legacy KICAD9_* tokens in
  existing project files are normalized to KICAD10_* as input migration only
- Handles both absolute and relative library paths
"""

import os
import copy
import re
from typing import Set, Tuple, List, Optional, Callable

from .constants import (
    EXTENSION_SYMBOL, EXTENSION_SYM_LIB_TABLE,
    SEXPR_SYMBOL, SEXPR_LIB_SYMBOLS, SEXPR_LIB_ID, SEXPR_SYM_LIB_TABLE,
    SEXPR_EXTENDS, SEXPR_GENERATOR, SEXPR_GENERATOR_VERSION, SEXPR_VERSION,
    PROGRESS_STEP_SCAN_SYMBOLS, PROGRESS_STEP_COPY_SYMBOLS, ENV_VAR_KIPRJMOD,
    KICAD_SYMBOL_VERSION, KICAD_GENERATOR_NAME, KICAD_GENERATOR_VERSION,
    LIB_SYMBOLS_METADATA_COUNT
)
from .base_localizer import BaseLocalizer
from .sexpr_parser import SExpressionParseError
from .utils import (
    atomic_write_file, make_localized_item_name, resolve_library_path,
    safe_read_file, scan_schematics_for_items, update_library_table,
    validate_path_safety
)


class SymbolLocalizer(BaseLocalizer):
    """!
    @brief Handles localization of symbols from global to local libraries
    
    Scans schematic files, identifies external symbol references, copies
    them to project-local symbol libraries, and updates all references.
    
    Inherits common functionality from BaseLocalizer.
    
    @section methods Methods
    - :py:meth:`~SymbolLocalizer.__init__`
    - :py:meth:`~SymbolLocalizer.scan_schematic_symbols`
    - :py:meth:`~SymbolLocalizer.find_symbols_in_sexpr`
    - :py:meth:`~SymbolLocalizer.copy_symbols`
    - :py:meth:`~SymbolLocalizer.get_symbols_in_library`
    - :py:meth:`~SymbolLocalizer.extract_symbol_from_library`
    - :py:meth:`~SymbolLocalizer.find_symbol_library_path`
    - :py:meth:`~SymbolLocalizer.write_symbol_library`
    - :py:meth:`~SymbolLocalizer.update_schematic_references`
    - :py:meth:`~SymbolLocalizer.update_sym_lib_table`
    
    @section attributes Attributes
    - logger (Callable): Logger object with info/warning/error methods (inherited)
    - parser (SExpressionParser): S-expression parser instance (inherited)
    """
    
    def __init__(self, logger: Optional[Callable] = None):
        """
        @brief Initialize the symbol localizer
        
        @param logger: Optional logger object with info/warning/error methods
        """
        super().__init__(logger)
    
    def scan_schematic_symbols(self, project_dir: str) -> Set[Tuple[str, str]]:
        """
        @brief Scan schematic files for symbol references

        @param project_dir: Project directory containing schematic files
        @return Set of (library, symbol) tuples excluding power symbols
        """
        
        def extract_and_filter_symbols(sexpr):
            """
            @brief Extract symbols while excluding the power library

            @param sexpr: Parsed schematic S-expression
            @return Set of non-power (library, symbol) tuples
            """
            symbols = self.find_symbols_in_sexpr(sexpr)
            # Filter out power library symbols
            return {(lib, sym) for lib, sym in symbols if lib.lower() != 'power'}
        
        symbol_set = scan_schematics_for_items(
            project_dir,
            self.parser,
            extract_and_filter_symbols,
            self.logger,
            PROGRESS_STEP_SCAN_SYMBOLS
        )
        
        return symbol_set
    
    def find_symbols_in_sexpr(self, sexpr) -> Set[Tuple[str, str]]:
        """
        @brief Recursively find all symbol references in S-expression
        
        @param sexpr: Parsed S-expression (nested lists)
        @return Set of (library, symbol) tuples
        """
        symbols = set()
        
        def search(node):
            """
            @brief Recursively collect symbol references

            @param node: Current S-expression node
            """
            if isinstance(node, list) and len(node) >= 2:
                # Look for (symbol (lib_id "Library:Symbol") ...)
                if node[0] == SEXPR_SYMBOL:
                    for item in node:
                        if isinstance(item, list) and len(item) >= 2:
                            if item[0] == SEXPR_LIB_ID:
                                lib_id = item[1].strip('"')
                                if ':' in lib_id:
                                    lib, sym = lib_id.split(':', 1)
                                    if lib.strip() and sym.strip():
                                        symbols.add((lib.strip(), sym.strip()))
                
                # Recurse into all sub-lists
                for item in node:
                    if isinstance(item, list):
                        search(item)
        
        search(sexpr)
        return symbols
    
    def copy_symbols(self, symbols: Set[Tuple[str, str]], project_dir: str, 
                    symbol_lib_name: str, symbol_dir_name: str) -> List[Tuple[str, str, str, Optional[list]]]:
        """
        @brief Copy symbols from global libraries to local library
        
        @param symbols: Set of (lib_name, symbol_name) tuples
        @param project_dir: Project directory path
        @param symbol_lib_name: Name for the local symbol library
        @param symbol_dir_name: Name for the symbol directory
        @return List of source library, source name, target name, and optional
                symbol content tuples available for reference updates
        """
        self.log('info', PROGRESS_STEP_COPY_SYMBOLS + "...")
        
        # Create symbol directory
        symbol_dir_path = os.path.join(project_dir, symbol_dir_name)
        if not validate_path_safety(symbol_dir_path, project_dir):
            self.log('error', f"Symbol directory name is unsafe, aborting: {symbol_dir_name}")
            return []
        if not os.path.exists(symbol_dir_path):
            self.log('info', f"Creating symbol directory: {symbol_dir_name}")
            os.makedirs(symbol_dir_path)
        else:
            self.log('info', f"Using existing symbol directory: {symbol_dir_name}")
        
        # Create symbol library file path
        symbol_lib_path = os.path.join(symbol_dir_path, f"{symbol_lib_name}{EXTENSION_SYMBOL}")
        
        # Filter out symbols already in local library
        symbols_to_copy = set()
        skipped_count = 0
        
        # Check if local library exists and what symbols it contains
        existing_symbols = set()
        if os.path.exists(symbol_lib_path):
            try:
                content = safe_read_file(symbol_lib_path)
                sexpr = self.parser.parse(content)
                existing_symbols = self.get_symbols_in_library(sexpr)
                self.log('info', f"Found {len(existing_symbols)} existing symbols in {symbol_lib_name}")
            except (OSError, ValueError, SExpressionParseError) as e:
                self.log('warning', f"Could not read existing library: {e}")
        
        for lib_name, sym_name in symbols:
            # Skip power library symbols
            if lib_name.lower() == 'power':
                self.log('info', f"  → Skipping {lib_name}:{sym_name} (power library)")
                skipped_count += 1
            elif lib_name == symbol_lib_name:
                self.log(
                    'info',
                    f"  → Skipping {lib_name}:{sym_name} (already local)"
                )
                skipped_count += 1
            else:
                symbols_to_copy.add((lib_name, sym_name))
        
        if skipped_count > 0:
            self.log('info', f"Skipped {skipped_count} symbols already in {symbol_lib_name}")
        
        # Copy symbols to local library. Use a work queue so that parent
        # symbols referenced via (extends ...) are copied along with the
        # symbols that use them - KiCad requires the parent to exist in the
        # same library file.
        copied_count = 0
        failed_count = 0
        localized_symbols = []
        symbol_contents = []
        work_queue = sorted(symbols_to_copy)
        processed = set()
        
        while work_queue:
            lib_name, sym_name = work_queue.pop()
            if (lib_name, sym_name) in processed:
                continue
            processed.add((lib_name, sym_name))
            target_name = make_localized_item_name(lib_name, sym_name)

            if target_name in existing_symbols:
                self.log(
                    'info',
                    f"  → Reusing {symbol_lib_name}:{target_name}"
                )
                localized_symbols.append(
                    (lib_name, sym_name, target_name, None)
                )
                continue
            
            try:
                # Find and extract the symbol from global library
                symbol_data = self.extract_symbol_from_library(lib_name, sym_name, project_dir)
                
                if symbol_data:
                    parent_name = self.get_symbol_parent(symbol_data)
                    localized_data = self.rename_symbol_for_local_library(
                        symbol_data,
                        lib_name,
                        sym_name,
                        target_name,
                        parent_name
                    )
                    self.log(
                        'info',
                        f"  ✓ Extracted {lib_name}:{sym_name} as {target_name}"
                    )
                    copied_count += 1
                    localized_symbols.append(
                        (lib_name, sym_name, target_name, localized_data)
                    )
                    symbol_contents.append(localized_data)
                    
                    # Queue the parent symbol if this symbol extends one and
                    # it is not already present in the local library
                    parent_target = (
                        make_localized_item_name(lib_name, parent_name)
                        if parent_name
                        else None
                    )
                    if (
                        parent_name
                        and parent_target not in existing_symbols
                        and (lib_name, parent_name) not in processed
                    ):
                        self.log('info', f"    → Queuing parent symbol {lib_name}:{parent_name}")
                        work_queue.append((lib_name, parent_name))
                else:
                    self.log('warning', f"  ✗ Could not find source for {lib_name}:{sym_name}")
                    failed_count += 1
                    
            except Exception as e:
                self.log('error', f"  ✗ Failed to extract {lib_name}:{sym_name}: {str(e)}")
                failed_count += 1
        
        # Write all copied symbols to the local library file
        if symbol_contents:
            self.write_symbol_library(symbol_lib_path, symbol_contents)
            self.log('success', f"Copied {copied_count} symbols to {symbol_lib_name}{EXTENSION_SYMBOL}")
        else:
            self.log('info', f"No new symbols to add to library")
        
        if failed_count > 0:
            self.log('warning', f"{failed_count} symbols could not be copied")
        
        return localized_symbols

    def rename_symbol_for_local_library(
        self,
        symbol_data: list,
        source_library: str,
        source_name: str,
        target_name: str,
        parent_name: Optional[str] = None
    ) -> list:
        """
        @brief Rename a symbol definition for collision-safe local storage

        @param symbol_data: Source symbol S-expression
        @param source_library: Original library nickname
        @param source_name: Original symbol name
        @param target_name: Local collision-safe symbol name
        @param parent_name: Optional source parent symbol name
        @return Deep-copied and renamed symbol S-expression
        """
        localized_data = copy.deepcopy(symbol_data)
        target_parent = (
            make_localized_item_name(source_library, parent_name)
            if parent_name
            else None
        )

        def rename(node):
            """
            @brief Recursively rename symbol and extends nodes

            @param node: Current S-expression node
            """
            if not isinstance(node, list) or not node:
                return
            if node[0] == SEXPR_SYMBOL and len(node) >= 2:
                item_name = node[1].strip('"').strip("'")
                if (
                    item_name == source_name
                    or item_name.startswith(f"{source_name}_")
                ):
                    node[1] = f'"{target_name}{item_name[len(source_name):]}"'
            elif (
                node[0] == SEXPR_EXTENDS
                and len(node) >= 2
                and target_parent
            ):
                node[1] = f'"{target_parent}"'
            for child in node[1:]:
                rename(child)

        rename(localized_data)
        return localized_data
    
    def get_symbols_in_library(self, sexpr) -> Set[str]:
        """
        @brief Extract symbol names from a library S-expression
        
        @param sexpr: Parsed library S-expression
        @return Set of symbol names
        """
        symbols = set()
        
        if isinstance(sexpr, list) and len(sexpr) > 0:
            for item in sexpr:
                if isinstance(item, list) and len(item) >= 2:
                    if item[0] == SEXPR_SYMBOL:
                        # Symbol name is the second element
                        sym_name = item[1].strip('"')
                        symbols.add(sym_name)
        
        return symbols
    
    def get_symbol_parent(self, symbol_sexpr: list) -> Optional[str]:
        """
        @brief Get the parent symbol name from a symbol's (extends ...) clause
        
        KiCad symbols can inherit from a parent in the same library via
        (extends "ParentName"). The parent must exist in the same library
        file for the library to load.
        
        @param symbol_sexpr: Parsed symbol S-expression
        @return Parent symbol name, or None if the symbol has no parent
        """
        if isinstance(symbol_sexpr, list):
            for item in symbol_sexpr:
                if (
                    isinstance(item, list)
                    and len(item) >= 2
                    and item[0] == SEXPR_EXTENDS
                ):
                    return item[1].strip('"').strip("'")
        return None
    
    def extract_symbol_from_library(self, lib_name: str, sym_name: str,
                                    project_dir: Optional[str] = None) -> Optional[list]:
        """
        @brief Extract a symbol definition from a global library
        
        @param lib_name: Library nickname
        @param sym_name: Symbol name
        @param project_dir: Optional project directory whose table takes precedence
        @return Symbol S-expression or None if not found
        """
        try:
            # Find library path
            lib_path = self.find_symbol_library_path(lib_name, project_dir)
            
            if not lib_path or not os.path.exists(lib_path):
                self.log('warning', f"    Library not found: {lib_name}")
                return None
            
            content = safe_read_file(lib_path)
            
            # Parse library
            sexpr = self.parser.parse(content)
            
            # Find the specific symbol
            if isinstance(sexpr, list):
                for item in sexpr:
                    if isinstance(item, list) and len(item) >= 2:
                        if item[0] == SEXPR_SYMBOL:
                            item_name = item[1].strip('"')
                            if item_name == sym_name:
                                return item
            
            return None
            
        except (OSError, ValueError, SExpressionParseError) as e:
            self.log('error', f"    Exception extracting symbol: {str(e)}")
            return None
    
    def find_symbol_library_path(self, lib_name: str, project_dir: Optional[str] = None) -> Optional[str]:
        """
        @brief Find the filesystem path to a symbol library
        
        @param lib_name: Library nickname
        @param project_dir: Optional project directory whose table takes precedence
        @return Absolute path to .kicad_sym file or None if not found
        """
        return resolve_library_path(
            EXTENSION_SYM_LIB_TABLE,
            lib_name,
            self.parser,
            self.logger,
            project_dir
        )
    
    def write_symbol_library(
        self,
        lib_path: str,
        symbol_contents: List[list]
    ) -> None:
        """
        @brief Write symbols to a library file
        
        @param lib_path: Path to the library file
        @param symbol_contents: List of symbol S-expressions to add
        """
        try:
            empty_library = [
                SEXPR_LIB_SYMBOLS,
                [SEXPR_VERSION, KICAD_SYMBOL_VERSION],
                [SEXPR_GENERATOR, KICAD_GENERATOR_NAME],
                [SEXPR_GENERATOR_VERSION, KICAD_GENERATOR_VERSION]
            ]

            # Start with library header or read existing file
            if os.path.exists(lib_path):
                self.log('info', f"Reading existing library file: {lib_path}")
                content = safe_read_file(lib_path)
                
                # Check if file is empty or just has whitespace
                if not content.strip():
                    self.log('warning', f"Existing library file is empty, creating new structure")
                    lib_sexpr = empty_library
                else:
                    lib_sexpr = self.parser.parse(content)
                    # Validate that it's a proper symbol library
                    if not (isinstance(lib_sexpr, list) and len(lib_sexpr) > 0 and lib_sexpr[0] == SEXPR_LIB_SYMBOLS):
                        self.log('warning', f"Existing file is not a valid symbol library, creating new structure")
                        lib_sexpr = empty_library
                    else:
                        self.log('info', f"Existing library has {len(lib_sexpr) - LIB_SYMBOLS_METADATA_COUNT} symbols")
            else:
                self.log('info', f"Creating new library file: {lib_path}")
                # Create new library structure (matching KiCad format)
                lib_sexpr = empty_library
            
            # Add new symbols
            symbols_added = 0
            for symbol_data in symbol_contents:
                lib_sexpr.append(symbol_data)
                symbols_added += 1
            
            self.log('info', f"Writing {symbols_added} new symbols to library")
            
            # Convert to string
            lib_content = self.parser.to_string(lib_sexpr)
            
            self.log('info', f"Library content size: {len(lib_content)} characters")
            
            atomic_write_file(lib_path, lib_content)
            
            self.log('info', f"Successfully wrote symbol library to {lib_path}")
                
        except (OSError, ValueError, SExpressionParseError) as e:
            self.log('error', f"Failed to write symbol library: {e}")
            raise
    
    def update_schematic_references(
        self,
        copied_symbols: List[Tuple[str, str, str, Optional[list]]],
        project_dir: str,
        local_lib_name: str
    ) -> int:
        """
        @brief Update schematic files to use local symbol library
        
        @param copied_symbols: Localized symbol records including target names
        @param project_dir: Project directory path
        @param local_lib_name: Local library name
        @return Total number of updated symbol references

        @throws RuntimeError if schematic files are locked
        @throws OSError if a schematic cannot be updated
        """
        if not copied_symbols:
            self.log('info', "No symbols to update in schematics")
            return 0
        
        self.log('info', "Updating schematic symbol library references...")
        
        # Find all schematic files
        schematic_files = self.find_schematic_files(project_dir)
        
        if not schematic_files:
            self.log('warning', "No schematic files found")
            return 0
        
        # Check for locked files
        locked_files = self.check_schematic_locks(project_dir)
        if locked_files:
            self.log('warning', f"The following schematic file(s) appear to be open: {', '.join(locked_files)}")
            self.log('error', "Cannot update schematics - files are locked")
            raise RuntimeError("Cannot update locked schematic files")
        
        total_updated = 0
        
        for sch_file in schematic_files:
            self.log('info', f"Processing {os.path.basename(sch_file)}...")
            
            # Build replacement list for this file
            replacements = []
            for lib_name, sym_name, target_name, _ in copied_symbols:
                old_ref = f'"{lib_name}:{sym_name}"'
                new_ref = f'"{local_lib_name}:{target_name}"'
                replacements.append((old_ref, new_ref))
            
            try:
                updated_count = self.update_schematic_file(
                    sch_file,
                    replacements,
                    lambda content: self._rename_embedded_symbol_definitions(
                        content,
                        copied_symbols,
                        local_lib_name
                    )
                )
                total_updated += updated_count
                    
            except Exception as e:
                self.log('error', f"Failed to update {os.path.basename(sch_file)}: {str(e)}")
                raise
        
        if total_updated > 0:
            self.log('success', f"Updated {total_updated} total symbol reference(s) in schematic files")
        else:
            self.log('info', "No symbol references needed updating in schematics")

        return total_updated

    @staticmethod
    def _find_sexpr_end(content: str, start: int) -> int:
        """
        @brief Find the end of an S-expression while ignoring quoted text.

        @param content: S-expression document text.
        @param start: Offset of the opening parenthesis.
        @return Offset immediately after the matching closing parenthesis.

        @throws ValueError if the expression is not balanced.
        """
        depth = 0
        in_string = False
        escaped = False

        for index in range(start, len(content)):
            character = content[index]
            if in_string:
                if escaped:
                    escaped = False
                elif character == '\\':
                    escaped = True
                elif character == '"':
                    in_string = False
                continue

            if character == '"':
                in_string = True
            elif character == '(':
                depth += 1
            elif character == ')':
                depth -= 1
                if depth == 0:
                    return index + 1

        raise ValueError("Unbalanced embedded symbol definition")

    def _rename_embedded_symbol_definitions(
        self,
        content: str,
        copied_symbols: List[Tuple[str, str, str, Optional[list]]],
        local_lib_name: str
    ) -> tuple:
        """
        @brief Rename embedded symbol roots and child units consistently.

        KiCad schematic files embed symbol definitions. A definition root uses
        `Library:Symbol`, while its child graphics use names such as
        `Symbol_0_1`. When the root is localized, every child must receive the
        same new symbol-name prefix.

        @param content: Schematic file content.
        @param copied_symbols: Localized symbol records.
        @param local_lib_name: Local symbol library nickname.
        @return Tuple containing replacement count and updated content.
        """
        replacement_count = 0

        for source_library, source_name, target_name, _ in copied_symbols:
            source_root = f"{source_library}:{source_name}"
            target_root = f"{local_lib_name}:{target_name}"
            root_pattern = re.compile(
                r'(\(symbol\s+")'
                + re.escape(source_root)
                + r'(")'
            )
            search_offset = 0

            while True:
                root_match = root_pattern.search(content, search_offset)
                if root_match is None:
                    break

                expression_start = root_match.start()
                expression_end = self._find_sexpr_end(
                    content,
                    expression_start
                )
                symbol_block = content[expression_start:expression_end]
                symbol_block, root_count = root_pattern.subn(
                    rf'\g<1>{target_root}\g<2>',
                    symbol_block,
                    count=1
                )
                child_pattern = re.compile(
                    r'(\(symbol\s+")'
                    + re.escape(source_name)
                    + r'(_[^"]*")'
                )
                symbol_block, child_count = child_pattern.subn(
                    rf'\g<1>{target_name}\g<2>',
                    symbol_block
                )

                content = (
                    content[:expression_start]
                    + symbol_block
                    + content[expression_end:]
                )
                replacement_count += root_count + child_count
                search_offset = expression_start + len(symbol_block)

        return replacement_count, content
    
    def update_sym_lib_table(self, project_dir: str, symbol_lib_name: str, symbol_dir_name: str) -> bool:
        """
        @brief Add local symbol library to project sym-lib-table
        
        @param project_dir: Project directory path
        @param symbol_lib_name: Symbol library name to add
        @param symbol_dir_name: Symbol directory name
        @return True if successful, False otherwise
        """
        self.log('info', "Updating project sym-lib-table...")
        return update_library_table(
            os.path.join(project_dir, EXTENSION_SYM_LIB_TABLE),
            SEXPR_SYM_LIB_TABLE,
            symbol_lib_name,
            (
                f"${{{ENV_VAR_KIPRJMOD}}}/{symbol_dir_name}/"
                f"{symbol_lib_name}{EXTENSION_SYMBOL}"
            ),
            self.parser,
            self.logger,
            "Local project symbol library"
        )
