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
@file library_manager.py

@brief Library management for Bakery plugin

Handles creation and management of KiCad footprint and symbol libraries:
- Creating local library folders
- Finding library paths in global tables
- Updating fp-lib-table and sym-lib-table files
- Path validation and environment variable expansion

@section description_library_manager Detailed Description
This module provides the LibraryManager class which handles all library-related
operations including creating local .pretty directories, managing fp-lib-table
entries, resolving library paths from global tables, and expanding KiCad
environment variables.

@section notes_library_manager Notes
- Supports KiCad 10 environment variable naming conventions; normalizes
  legacy KICAD9_* tokens found in project files as input migration only
- Handles ${KIPRJMOD}, ${KICAD10_3DMODEL_DIR}, ${KICAD_3DMODEL_DIR}
- Validates library paths before operations
"""

import os
from typing import Optional

from .constants import (
    ENV_VAR_KIPRJMOD, EXTENSION_FOOTPRINT_LIB, EXTENSION_FP_LIB_TABLE,
    SEXPR_FP_LIB_TABLE
)
from .utils import (
    expand_kicad_path, ParserLoggerMixin, resolve_library_path,
    update_library_table, validate_library_name, validate_path_safety
)


class LibraryManager(ParserLoggerMixin):
    """!
    @brief Manages creation and updates of local KiCad libraries
    
    Handles footprint and symbol library creation, fp-lib-table updates,
    and library path resolution.
    
    @section methods Methods
    - :py:meth:`~LibraryManager.__init__`
    - :py:meth:`~LibraryManager.log`
    - :py:meth:`~LibraryManager.expand_path`
    - :py:meth:`~LibraryManager.create_local_footprint_library`
    - :py:meth:`~LibraryManager.find_footprint_library_path`
    - :py:meth:`~LibraryManager.update_fp_lib_table`
    
    @section attributes Attributes
    - logger (Callable): Logger object with info/warning/error methods
    - parser (SExpressionParser): S-expression parser instance
    """
    
    def expand_path(self, path: str, project_dir: Optional[str] = None) -> str:
        """
        @brief Expand environment variables in a path

        Delegates to the single shared resolver in utils.py so footprints,
        symbols, 3D models, and datasheets all resolve paths identically.

        @param path: Path with ${VAR_NAME} placeholders
        @param project_dir: Optional project directory for ${KIPRJMOD}
        @return Expanded path

        @throws KicadPathResolutionError if a variable cannot be resolved
        """
        return expand_kicad_path(path, project_dir)
    
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
    
    def find_footprint_library_path(self, lib_name: str, project_dir: Optional[str] = None) -> Optional[str]:
        """
        @brief Find the filesystem path to a footprint library
        
        @param lib_name: Library nickname
        @param project_dir: Optional project directory whose table takes precedence
        @return Absolute path to .pretty folder or None if not found
        """
        return resolve_library_path(
            EXTENSION_FP_LIB_TABLE,
            lib_name,
            self.parser,
            self.logger,
            project_dir
        )
    
    def update_fp_lib_table(self, project_dir: str, lib_name: str) -> bool:
        """
        @brief Add local library to project's fp-lib-table
        
        @param project_dir: Project directory path
        @param lib_name: Library name to add
        @return True if successful, False otherwise
        """
        self.log('info', "Updating project fp-lib-table...")
        return update_library_table(
            os.path.join(project_dir, EXTENSION_FP_LIB_TABLE),
            SEXPR_FP_LIB_TABLE,
            lib_name,
            f"${{{ENV_VAR_KIPRJMOD}}}/{lib_name}{EXTENSION_FOOTPRINT_LIB}",
            self.parser,
            self.logger,
            "Local project library"
        )
