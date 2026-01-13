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

"""
@brief Library management for Bakery plugin

Handles creation and management of KiCad footprint and symbol libraries:
- Creating local library folders
- Finding library paths in global tables
- Updating fp-lib-table and sym-lib-table files
- Path validation and environment variable expansion
"""

import os
import re
from typing import Optional, Callable

from .constants import (
    KICAD_VERSIONS, ENV_VAR_KIPRJMOD, ENV_VAR_PREFIX_PRIMARY,
    ENV_VAR_PREFIX_FALLBACK, ENV_VAR_PREFIX_GENERIC, EXTENSION_FOOTPRINT_LIB,
    EXTENSION_FP_LIB_TABLE, SEXPR_FP_LIB_TABLE, SEXPR_LIB, SEXPR_NAME,
    SEXPR_TYPE, SEXPR_URI, SEXPR_OPTIONS, SEXPR_DESCR, LIBRARY_TYPE_KICAD,
    KICAD_VERSION_PRIMARY
)
from .sexpr_parser import SExpressionParser
from .utils import validate_library_name, validate_path_safety, expand_kicad_path


class LibraryManager:
    """
    @brief Manages creation and updates of local KiCad libraries
    
    Handles footprint and symbol library creation, fp-lib-table updates,
    and library path resolution.
    """
    
    def __init__(self, logger: Optional[Callable] = None):
        """
        @brief Initialize the library manager
        
        @param logger: Optional logger object with info/warning/error methods
        """
        self.logger = logger
        self.parser = SExpressionParser()
        self.env_vars = self.expand_kicad_env_vars()
    
    def log(self, level: str, message: str):
        """
        @brief Internal logging helper
        
        @param level: Log level (info, warning, error)
        @param message: Message to log
        """
        if self.logger:
            method = getattr(self.logger, level, None)
            if method:
                method(message)
    
    def expand_kicad_env_vars(self) -> Dict[str, str]:
        """
        @brief Expand all KiCad environment variables once at initialization
        
        @return Dictionary of expanded environment variables
        """
        expanded = {}
        
        # List of KiCad environment variables to check
        var_names = [
            KICAD_ENV_FOOTPRINT_DIR,
            KICAD_ENV_3DMODEL_DIR,
            KICAD_ENV_SYMBOL_DIR
        ]
        
        for var_base in var_names:
            # Try version-specific variables first
            for version in KICAD_VERSIONS:
                var_name = f"KICAD{version.replace('.', '_')}_{var_base}"
                value = os.environ.get(var_name)
                if value:
                    expanded[var_name] = value
                    self.log('info', f"Found ${{{var_name}}} = {value}")
                    break
            
            # Also try generic version
            generic_var = f"{ENV_VAR_PREFIX_GENERIC}{var_base}"
            value = os.environ.get(generic_var)
            if value and generic_var not in expanded:
                expanded[generic_var] = value
                self.log('info', f"Found ${{{generic_var}}} = {value}")
        
        return expanded
    
    def expand_path(self, path: str) -> str:
        """
        @brief Expand environment variables in a path
        
        @param path: Path with ${VAR_NAME} placeholders
        @return Expanded path
        """
        expanded_path = path
        
        # Find all environment variables
        env_vars = re.findall(r'\$\{([^}]+)\}', path)
        
        for var in env_vars:
            # Check our cached expanded variables first
            if var in self.env_vars:
                expanded_path = expanded_path.replace(f"${{{var}}}", self.env_vars[var])
                continue
            
            # Try direct environment lookup
            env_value = os.environ.get(var, "")
            
            # If KiCad 9 variable not found, try KiCad 8 equivalent
            if not env_value and var.startswith(ENV_VAR_PREFIX_PRIMARY):
                kicad8_var = var.replace(ENV_VAR_PREFIX_PRIMARY, ENV_VAR_PREFIX_FALLBACK)
                env_value = os.environ.get(kicad8_var, "")
                if env_value:
                    self.log('info', f"Using ${{{kicad8_var}}} as fallback")
            
            # Also try without version number
            if not env_value:
                generic_var = var.replace(ENV_VAR_PREFIX_PRIMARY, ENV_VAR_PREFIX_GENERIC).replace(
                    ENV_VAR_PREFIX_FALLBACK, ENV_VAR_PREFIX_GENERIC)
                env_value = os.environ.get(generic_var, "")
                if env_value:
                    self.log('info', f"Using ${{{generic_var}}} as fallback")
            
            if env_value:
                expanded_path = expanded_path.replace(f"${{{var}}}", env_value)
                # Cache for future use
                self.env_vars[var] = env_value
            else:
                self.log('warning', f"Environment variable ${{{var}}} not found")
        
        # Handle file:// URIs
        if expanded_path.startswith("file://"):
            expanded_path = expanded_path[7:]
        
        return expanded_path
    
    def create_local_footprint_library(self, project_dir: str, lib_name: str) -> str:
        """
        @brief Create a local footprint library folder
        
        @param project_dir: Project directory path
        @param lib_name: Library name (without .pretty extension)
        @return Path to created library
        
        @throws ValueError if library name is invalid
        @throws OSError if library creation fails
        """
        # Validate library name
        if not validate_library_name(lib_name):
            raise ValueError(f"Invalid library name: {lib_name}")
        
        lib_path = os.path.join(project_dir, f"{lib_name}{EXTENSION_FOOTPRINT_LIB}")
        old_path = os.path.join(project_dir, lib_name)
        
        # Validate paths are within project directory
        if not validate_path_safety(lib_path, project_dir):
            raise ValueError(f"Library path is outside project directory: {lib_path}")
        
        try:
            # Check if folder exists without .pretty extension
            if os.path.exists(old_path) and not os.path.exists(lib_path):
                # Rename the folder to add .pretty extension
                os.rename(old_path, lib_path)
                self.log('info', f"Renamed '{lib_name}' to '{lib_name}{EXTENSION_FOOTPRINT_LIB}'")
            else:
                os.makedirs(lib_path, exist_ok=True)
                self.log('info', f"Created/verified local library: {lib_name}{EXTENSION_FOOTPRINT_LIB}")
            return lib_path
        except OSError as e:
            self.log('error', f"Failed to create library directory: {e}")
            raise
    
    def find_footprint_library_path(self, lib_name: str) -> Optional[str]:
        """
        @brief Find the filesystem path to a footprint library
        
        @param lib_name: Library nickname
        @return Absolute path to .pretty folder or None if not found
        """
        try:
            # Try common locations for global fp-lib-table
            possible_table_paths = [
                os.path.join(os.environ.get('APPDATA', ''), 'kicad', KICAD_VERSION_PRIMARY, 
                            EXTENSION_FP_LIB_TABLE),
                os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'KiCad', 
                            KICAD_VERSION_PRIMARY, EXTENSION_FP_LIB_TABLE),
                os.path.join(os.path.expanduser('~'), '.config', 'kicad', 
                            KICAD_VERSION_PRIMARY, EXTENSION_FP_LIB_TABLE),
            ]
            
            # Also try fallback version
            for base_path in list(possible_table_paths):
                fallback_path = base_path.replace(KICAD_VERSION_PRIMARY, KICAD_VERSION_FALLBACK)
                possible_table_paths.append(fallback_path)
            
            fp_lib_table_path = None
            for path in possible_table_paths:
                if os.path.exists(path):
                    fp_lib_table_path = path
                    self.log('info', f"Found fp-lib-table: {path}")
                    break
            
            if not fp_lib_table_path:
                self.log('warning', "Could not find global fp-lib-table")
                return None
            
            # Read and parse the fp-lib-table file
            with open(fp_lib_table_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse S-expression
            sexpr = self.parser.parse(content)
            
            # Find library path
            lib_path = self.parser.find_library_path(sexpr, lib_name)
            
            if not lib_path:
                self.log('warning', f"Library '{lib_name}' not found in fp-lib-table")
                return None
            
            # Expand environment variables
            expanded_path = self.expand_path(lib_path)
            
            self.log('info', f"Resolved {lib_name} to {expanded_path}")
            
            return expanded_path
                    
        except Exception as e:
            self.log('error', f"Exception finding library path: {str(e)}")
            return None
    
    def update_fp_lib_table(self, project_dir: str, lib_name: str) -> bool:
        """
        @brief Add local library to project's fp-lib-table
        
        @param project_dir: Project directory path
        @param lib_name: Library name to add
        @return True if successful, False otherwise
        """
        fp_lib_table_path = os.path.join(project_dir, EXTENSION_FP_LIB_TABLE)
        
        self.log('info', "Updating project fp-lib-table...")
        
        try:
            # Check if fp-lib-table exists
            if os.path.exists(fp_lib_table_path):
                self.log('info', "Found existing fp-lib-table")
                
                # Read existing file
                with open(fp_lib_table_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the S-expression
                sexpr = self.parser.parse(content)
                
                # Check if library already exists and update URI if needed
                lib_found = False
                if isinstance(sexpr, list):
                    for item in sexpr:
                        if isinstance(item, list) and len(item) > 0 and item[0] == SEXPR_LIB:
                            # Check if this is our library
                            lib_entry_name = None
                            uri_index = None
                            for i, subitem in enumerate(item):
                                if isinstance(subitem, list) and len(subitem) >= 2:
                                    if subitem[0] == SEXPR_NAME:
                                        lib_entry_name = subitem[1].strip('"').strip("'")
                                    elif subitem[0] == SEXPR_URI:
                                        uri_index = i
                            
                            if lib_entry_name == lib_name:
                                lib_found = True
                                # Update URI to ensure it points to .pretty folder
                                correct_uri = f'"${{{ENV_VAR_KIPRJMOD}}}/{lib_name}{EXTENSION_FOOTPRINT_LIB}"'
                                if uri_index is not None:
                                    current_uri = item[uri_index][1].strip('"').strip("'")
                                    if not current_uri.endswith(EXTENSION_FOOTPRINT_LIB):
                                        item[uri_index] = [SEXPR_URI, correct_uri]
                                        self.log('info', f"Updated URI for '{lib_name}' to point to .pretty folder")
                                break
                
                if lib_found:
                    # Write the updated table
                    fp_lib_content = self.parser.to_string(sexpr)
                    with open(fp_lib_table_path, 'w', encoding='utf-8') as f:
                        f.write(fp_lib_content)
                    self.log('info', f"Library '{lib_name}' entry updated in fp-lib-table")
                    return True
                
            else:
                self.log('info', "Creating new fp-lib-table")
                # Create new fp-lib-table structure
                sexpr = [SEXPR_FP_LIB_TABLE]
            
            # Add library entry
            new_lib_entry = [
                SEXPR_LIB,
                [SEXPR_NAME, f'"{lib_name}"'],
                [SEXPR_TYPE, f'"{LIBRARY_TYPE_KICAD}"'],
                [SEXPR_URI, f'"${{{ENV_VAR_KIPRJMOD}}}/{lib_name}{EXTENSION_FOOTPRINT_LIB}"'],
                [SEXPR_OPTIONS, '""'],
                [SEXPR_DESCR, '"Local project library"']
            ]
            
            # Add the new library entry to the table
            if isinstance(sexpr, list) and len(sexpr) > 0:
                sexpr.append(new_lib_entry)
            
            # Convert S-expression back to text
            fp_lib_content = self.parser.to_string(sexpr)
            
            # Write the updated fp-lib-table
            with open(fp_lib_table_path, 'w', encoding='utf-8') as f:
                f.write(fp_lib_content)
            
            self.log('info', f"Added '{lib_name}' to project fp-lib-table")
            return True
            
        except Exception as e:
            self.log('error', f"Failed to update fp-lib-table: {e}")
            return False
