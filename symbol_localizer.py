"""
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
"""

"""!
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
- Supports KiCad 8 and 9 environment variable formats
- Handles both absolute and relative library paths
- Creates backups before modifying schematic files
"""

import os
import shutil
import glob
from datetime import datetime
from typing import Set, Tuple, List, Optional, Callable

from .constants import (
    EXTENSION_SYMBOL, EXTENSION_SCHEMATIC, EXTENSION_SYM_LIB_TABLE,
    SEXPR_SYMBOL, SEXPR_LIB_SYMBOLS, SEXPR_LIB_ID, SEXPR_NAME, SEXPR_TYPE,
    SEXPR_URI, SEXPR_OPTIONS, SEXPR_DESCR, SEXPR_LIB, SEXPR_SYM_LIB_TABLE,
    LIBRARY_TYPE_KICAD, PROGRESS_STEP_SCAN_SYMBOLS, PROGRESS_STEP_COPY_SYMBOLS,
    PROGRESS_STEP_UPDATE_SYM_LIB_TABLE, ENV_VAR_KIPRJMOD,
    KICAD_VERSION_PRIMARY, KICAD_VERSION_FALLBACK,
    ENV_VAR_PREFIX_PRIMARY, ENV_VAR_PREFIX_FALLBACK, ENV_VAR_PREFIX_GENERIC
)
from .sexpr_parser import SExpressionParser
from .backup_manager import BackupManager
from .utils import (
    expand_kicad_path, safe_read_file, find_schematic_files,
    scan_schematics_for_items
)


class SymbolLocalizer:
    """!
    @brief Handles localization of symbols from global to local libraries
    
    Scans schematic files, identifies external symbol references, copies
    them to project-local symbol libraries, and updates all references.
    
    @section methods Methods
    - :py:meth:`~SymbolLocalizer.__init__`
    - :py:meth:`~SymbolLocalizer.log`
    - :py:meth:`~SymbolLocalizer.scan_schematic_symbols`
    - :py:meth:`~SymbolLocalizer.find_symbols_in_sexpr`
    - :py:meth:`~SymbolLocalizer.copy_symbols`
    - :py:meth:`~SymbolLocalizer.get_symbols_in_library`
    - :py:meth:`~SymbolLocalizer.extract_symbol_from_library`
    - :py:meth:`~SymbolLocalizer.find_symbol_library_path`
    - :py:meth:`~SymbolLocalizer.expand_path`
    - :py:meth:`~SymbolLocalizer.write_symbol_library`
    - :py:meth:`~SymbolLocalizer.update_schematic_references`
    - :py:meth:`~SymbolLocalizer.update_sym_lib_table`
    
    @section attributes Attributes
    - logger (Callable): Logger object with info/warning/error methods
    - parser (SExpressionParser): S-expression parser instance
    - backup_manager (BackupManager): File backup manager instance
    """
    
    def __init__(self, logger: Optional[Callable] = None):
        """
        @brief Initialize the symbol localizer
        
        @param logger: Optional logger object with info/warning/error methods
        """
        self.logger = logger
        self.parser = SExpressionParser()
        self.backup_manager = BackupManager(logger)
    
    def log(self, level: str, message: str) -> None:
        """
        @brief Internal logging helper
        
        @param level: Log level (info, warning, error, success)
        @param message: Message to log
        """
        if self.logger:
            method = getattr(self.logger, level, None)
            if method:
                method(message)
    
    def scan_schematic_symbols(self, project_dir: str) -> Set[Tuple[str, str]]:
        """
        @brief Scan schematic files for symbol references
        """
        
        def extract_and_filter_symbols(sexpr):
            """Extract symbols and filter out power library"""
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
                    symbol_lib_name: str, symbol_dir_name: str) -> List[Tuple[str, str, str]]:
        """
        @brief Copy symbols from global libraries to local library
        
        @param symbols: Set of (lib_name, symbol_name) tuples
        @param project_dir: Project directory path
        @param symbol_lib_name: Name for the local symbol library
        @param symbol_dir_name: Name for the symbol directory
        @return List of (lib_name, symbol_name, symbol_content) tuples that were copied
        """
        self.log('info', PROGRESS_STEP_COPY_SYMBOLS + "...")
        
        # Create symbol directory
        symbol_dir_path = os.path.join(project_dir, symbol_dir_name)
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
                with open(symbol_lib_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                sexpr = self.parser.parse(content)
                existing_symbols = self.get_symbols_in_library(sexpr)
                self.log('info', f"Found {len(existing_symbols)} existing symbols in {symbol_lib_name}")
            except Exception as e:
                self.log('warning', f"Could not read existing library: {e}")
        
        for lib_name, sym_name in symbols:
            # Skip power library symbols
            if lib_name.lower() == 'power':
                self.log('info', f"  → Skipping {lib_name}:{sym_name} (power library)")
                skipped_count += 1
            # Skip if already in local library
            elif sym_name in existing_symbols:
                self.log('info', f"  → Skipping {lib_name}:{sym_name} (already in local library)")
                skipped_count += 1
            else:
                symbols_to_copy.add((lib_name, sym_name))
        
        if skipped_count > 0:
            self.log('info', f"Skipped {skipped_count} symbols already in {symbol_lib_name}")
        
        # Copy symbols to local library
        copied_count = 0
        failed_count = 0
        copied_symbols = []
        symbol_contents = []
        
        for lib_name, sym_name in symbols_to_copy:
            try:
                # Find and extract the symbol from global library
                symbol_data = self.extract_symbol_from_library(lib_name, sym_name)
                
                if symbol_data:
                    self.log('info', f"  ✓ Extracted {lib_name}:{sym_name}")
                    copied_count += 1
                    copied_symbols.append((lib_name, sym_name))
                    symbol_contents.append(symbol_data)
                else:
                    self.log('warning', f"  ✗ Could not find source for {lib_name}:{sym_name}")
                    failed_count += 1
                    
            except Exception as e:
                self.log('error', f"  ✗ Failed to extract {lib_name}:{sym_name}: {str(e)}")
                failed_count += 1
        
        # Write all copied symbols to the local library file
        if symbol_contents:
            self.write_symbol_library(symbol_lib_path, symbol_lib_name, symbol_contents, existing_symbols)
            self.log('success', f"Copied {copied_count} symbols to {symbol_lib_name}{EXTENSION_SYMBOL}")
        else:
            self.log('info', f"No new symbols to add to library")
        
        if failed_count > 0:
            self.log('warning', f"{failed_count} symbols could not be copied")
        
        # Return list of (lib, sym, content) for reference updating
        return list(zip([x[0] for x in copied_symbols], 
                       [x[1] for x in copied_symbols],
                       symbol_contents))
    
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
    
    def extract_symbol_from_library(self, lib_name: str, sym_name: str) -> Optional[list]:
        """
        @brief Extract a symbol definition from a global library
        
        @param lib_name: Library nickname
        @param sym_name: Symbol name
        @return Symbol S-expression or None if not found
        """
        try:
            # Find library path
            lib_path = self.find_symbol_library_path(lib_name)
            
            if not lib_path or not os.path.exists(lib_path):
                self.log('warning', f"    Library not found: {lib_name}")
                return None
            
            # Read library file
            with open(lib_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
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
            
        except Exception as e:
            self.log('error', f"    Exception extracting symbol: {str(e)}")
            return None
    
    def find_symbol_library_path(self, lib_name: str) -> Optional[str]:
        """
        @brief Find the filesystem path to a symbol library
        
        @param lib_name: Library nickname
        @return Absolute path to .kicad_sym file or None if not found
        """
        try:
            # Try common locations for global sym-lib-table
            possible_table_paths = [
                os.path.join(os.environ.get('APPDATA', ''), 'kicad', KICAD_VERSION_PRIMARY, 
                            EXTENSION_SYM_LIB_TABLE),
                os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'KiCad', 
                            KICAD_VERSION_PRIMARY, EXTENSION_SYM_LIB_TABLE),
                os.path.join(os.path.expanduser('~'), '.config', 'kicad', 
                            KICAD_VERSION_PRIMARY, EXTENSION_SYM_LIB_TABLE),
            ]
            
            # Also try fallback version
            for base_path in list(possible_table_paths):
                fallback_path = base_path.replace(KICAD_VERSION_PRIMARY, KICAD_VERSION_FALLBACK)
                possible_table_paths.append(fallback_path)
            
            sym_lib_table_path = None
            for path in possible_table_paths:
                if os.path.exists(path):
                    sym_lib_table_path = path
                    break
            
            if not sym_lib_table_path:
                return None
            
            # Read and parse the sym-lib-table file
            with open(sym_lib_table_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse S-expression
            sexpr = self.parser.parse(content)
            
            # Find library path
            lib_path = self.parser.find_library_path(sexpr, lib_name)
            
            if not lib_path:
                return None
            
            # Expand environment variables
            expanded_path = self.expand_path(lib_path)
            
            return expanded_path
                    
        except Exception as e:
            return None
    
    def expand_path(self, path: str) -> str:
        """
        @brief Expand environment variables in a path
        
        @param path: Path with ${VAR_NAME} placeholders
        @return Expanded path
        """
        import re
        
        expanded_path = path
        
        # Find all environment variables
        env_vars = re.findall(r'\$\{([^}]+)\}', path)
        
        for var in env_vars:
            env_value = os.environ.get(var, "")
            
            # If KiCad 9 variable not found, try KiCad 8 equivalent
            if not env_value and var.startswith(ENV_VAR_PREFIX_PRIMARY):
                kicad8_var = var.replace(ENV_VAR_PREFIX_PRIMARY, ENV_VAR_PREFIX_FALLBACK)
                env_value = os.environ.get(kicad8_var, "")
            
            # Also try without version number
            if not env_value:
                generic_var = var.replace(ENV_VAR_PREFIX_PRIMARY, ENV_VAR_PREFIX_GENERIC).replace(
                    ENV_VAR_PREFIX_FALLBACK, ENV_VAR_PREFIX_GENERIC)
                env_value = os.environ.get(generic_var, "")
            
            if env_value:
                expanded_path = expanded_path.replace(f"${{{var}}}", env_value)
        
        # Handle file:// URIs
        if expanded_path.startswith("file://"):
            expanded_path = expanded_path[7:]
        
        return expanded_path
    
    def write_symbol_library(self, lib_path: str, lib_name: str, 
                            symbol_contents: List[list], existing_symbols: Set[str]):
        """
        @brief Write symbols to a library file
        
        @param lib_path: Path to the library file
        @param lib_name: Library name
        @param symbol_contents: List of symbol S-expressions to add
        @param existing_symbols: Set of symbol names already in library
        """
        try:
            # Start with library header or read existing file
            if os.path.exists(lib_path):
                self.log('info', f"Reading existing library file: {lib_path}")
                with open(lib_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file is empty or just has whitespace
                if not content.strip():
                    self.log('warning', f"Existing library file is empty, creating new structure")
                    lib_sexpr = [SEXPR_LIB_SYMBOLS, 
                               ['version', '20241209'], 
                               ['generator', 'kicad_symbol_editor'], 
                               ['generator_version', '9.0']]
                else:
                    lib_sexpr = self.parser.parse(content)
                    # Validate that it's a proper symbol library
                    if not (isinstance(lib_sexpr, list) and len(lib_sexpr) > 0 and lib_sexpr[0] == SEXPR_LIB_SYMBOLS):
                        self.log('warning', f"Existing file is not a valid symbol library, creating new structure")
                        lib_sexpr = [SEXPR_LIB_SYMBOLS, 
                                   ['version', '20241209'], 
                                   ['generator', 'kicad_symbol_editor'], 
                                   ['generator_version', '9.0']]
                    else:
                        self.log('info', f"Existing library has {len(lib_sexpr) - 4} symbols")
            else:
                self.log('info', f"Creating new library file: {lib_path}")
                # Create new library structure (matching KiCad format)
                lib_sexpr = [SEXPR_LIB_SYMBOLS, 
                           ['version', '20241209'], 
                           ['generator', 'kicad_symbol_editor'], 
                           ['generator_version', '9.0']]
            
            # Add new symbols
            symbols_added = 0
            for symbol_data in symbol_contents:
                lib_sexpr.append(symbol_data)
                symbols_added += 1
            
            self.log('info', f"Writing {symbols_added} new symbols to library")
            
            # Convert to string
            lib_content = self.parser.to_string(lib_sexpr)
            
            self.log('info', f"Library content size: {len(lib_content)} characters")
            
            # Write to file
            with open(lib_path, 'w', encoding='utf-8') as f:
                f.write(lib_content)
            
            self.log('info', f"Successfully wrote symbol library to {lib_path}")
                
        except Exception as e:
            self.log('error', f"Failed to write symbol library: {e}")
            raise
    
    def _is_file_locked(self, filepath: str) -> bool:
        """
        @brief Check if a file is locked/open by another process
        
        @param filepath: Path to file to check
        @return True if file is locked, False otherwise
        """
        try:
            # Try to open file in exclusive mode
            with open(filepath, 'r+', encoding='utf-8') as f:
                pass
            return False
        except (IOError, PermissionError):
            return True
    
    def update_schematic_references(self, copied_symbols: List[Tuple[str, str, list]], 
                                   project_dir: str, local_lib_name: str, create_backups: bool):
        """
        @brief Update schematic files to use local symbol library
        
        @param copied_symbols: List of (lib_name, sym_name, sexpr) tuples
        @param project_dir: Project directory path
        @param local_lib_name: Local library name
        @param create_backups: Whether to create backups before modifying
        """
        if not copied_symbols:
            self.log('info', "No symbols to update in schematics")
            return
        
        self.log('info', "Updating schematic symbol library references...")
        
        # Create a mapping of old library names to new library name
        old_libs = set()
        for lib_name, sym_name, _ in copied_symbols:
            old_libs.add(lib_name)
        
        # Find all schematic files
        schematic_files = glob.glob(os.path.join(project_dir, f"*{EXTENSION_SCHEMATIC}"))
        
        if not schematic_files:
            self.log('warning', "No schematic files found")
            return
        
        # Note: File lock check is now done upfront in bakery_plugin.py
        # This is a redundant safety check
        locked_files = []
        for sch_file in schematic_files:
            if self._is_file_locked(sch_file):
                locked_files.append(os.path.basename(sch_file))
        
        if locked_files:
            self.log('warning', f"The following schematic file(s) appear to be open: {', '.join(locked_files)}")
            self.log('error', "Cannot update schematics - files are locked")
            return
        
        total_updated = 0
        
        for sch_file in schematic_files:
            self.log('info', f"Processing {os.path.basename(sch_file)}...")
            
            try:
                # Create backup if requested
                if create_backups:
                    self.backup_manager.create_backup(sch_file)
                
                # Read the schematic file
                with open(sch_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Track if any changes were made
                original_content = content
                file_updated = 0
                
                # Replace lib_id references using simple find-and-replace
                # Format in schematic: (lib_id "Library:Symbol")
                for lib_name, sym_name, _ in copied_symbols:
                    old_ref = f'"{lib_name}:{sym_name}"'
                    new_ref = f'"{local_lib_name}:{sym_name}"'
                    
                    if old_ref in content:
                        count = content.count(old_ref)
                        content = content.replace(old_ref, new_ref)
                        file_updated += count
                        self.log('info', f"  ✓ Updated {count} reference(s): {lib_name}:{sym_name} → {local_lib_name}:{sym_name}")
                
                # Write back if changes were made
                if content != original_content:
                    with open(sch_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.log('success', f"  Updated {file_updated} symbol reference(s) in {os.path.basename(sch_file)}")
                    total_updated += file_updated
                else:
                    self.log('info', f"  No updates needed in {os.path.basename(sch_file)}")
                    
            except Exception as e:
                self.log('error', f"  Failed to update {os.path.basename(sch_file)}: {str(e)}")
        
        if total_updated > 0:
            self.log('success', f"Updated {total_updated} total symbol reference(s) in schematic files")
        else:
            self.log('info', "No symbol references needed updating in schematics")
    
    def update_sym_lib_table(self, project_dir: str, symbol_lib_name: str, symbol_dir_name: str) -> bool:
        """
        @brief Add local symbol library to project sym-lib-table
        
        @param project_dir: Project directory path
        @param symbol_lib_name: Symbol library name to add
        @param symbol_dir_name: Symbol directory name
        @return True if successful, False otherwise
        """
        sym_lib_table_path = os.path.join(project_dir, EXTENSION_SYM_LIB_TABLE)
        
        self.log('info', "Updating project sym-lib-table...")
        
        try:
            # Check if sym-lib-table exists
            if os.path.exists(sym_lib_table_path):
                self.log('info', "Found existing sym-lib-table")
                
                # Read existing file
                with open(sym_lib_table_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if library already exists in the table
                if f'({SEXPR_NAME} "{symbol_lib_name}")' in content or f"({SEXPR_NAME} '{symbol_lib_name}')" in content:
                    self.log('info', f"Library '{symbol_lib_name}' already exists in sym-lib-table")
                    return True
                
                # Parse the S-expression
                sexpr = self.parser.parse(content)
                
            else:
                self.log('info', "Creating new sym-lib-table")
                # Create new sym-lib-table structure
                sexpr = [SEXPR_SYM_LIB_TABLE]
            
            # Add library entry
            new_lib_entry = [
                SEXPR_LIB,
                [SEXPR_NAME, f'"{symbol_lib_name}"'],
                [SEXPR_TYPE, f'"{LIBRARY_TYPE_KICAD}"'],
                [SEXPR_URI, f'"${{{ENV_VAR_KIPRJMOD}}}/{symbol_dir_name}/{symbol_lib_name}{EXTENSION_SYMBOL}"'],
                [SEXPR_OPTIONS, '""'],
                [SEXPR_DESCR, '"Local project symbol library"']
            ]
            
            # Add the new library entry to the table
            if isinstance(sexpr, list) and len(sexpr) > 0:
                sexpr.append(new_lib_entry)
            
            # Convert S-expression back to text
            sym_lib_content = self.parser.to_string(sexpr)
            
            # Write the updated sym-lib-table
            with open(sym_lib_table_path, 'w', encoding='utf-8') as f:
                f.write(sym_lib_content)
            
            self.log('info', f"Added '{symbol_lib_name}' to project sym-lib-table")
            return True
            
        except Exception as e:
            self.log('error', f"Failed to update sym-lib-table: {e}")
            return False
