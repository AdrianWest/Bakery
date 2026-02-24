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
@file base_localizer.py

@brief Base class for localization functionality shared between footprint and symbol localizers

Provides common functionality for:
- Logging
- S-expression parsing
- Backup management
- Schematic file handling
- File lock detection

@section description_base_localizer Detailed Description
This module provides the BaseLocalizer abstract base class which encapsulates
common functionality shared between FootprintLocalizer and SymbolLocalizer.
This eliminates code duplication and ensures consistent behavior.

@section notes_base_localizer Notes
- All localizers should inherit from this base class
- Provides template methods for common operations
- Enforces consistent logging and error handling
"""

import os
import glob
from typing import Optional, Callable, List
from abc import ABC

from .constants import EXTENSION_SCHEMATIC
from .sexpr_parser import SExpressionParser
from .backup_manager import BackupManager
from .utils import find_schematic_files as _util_find_schematic_files


class BaseLocalizer(ABC):
    """!
    @brief Base class for footprint and symbol localizers
    
    Provides common functionality and helper methods shared between
    different types of localizers.
    
    @section methods Methods
    - :py:meth:`~BaseLocalizer.__init__`
    - :py:meth:`~BaseLocalizer.log`
    - :py:meth:`~BaseLocalizer.is_file_locked`
    - :py:meth:`~BaseLocalizer.check_schematic_locks`
    - :py:meth:`~BaseLocalizer.find_schematic_files`
    - :py:meth:`~BaseLocalizer.update_schematic_file`
    - :py:meth:`~BaseLocalizer.replace_references_in_content`
    
    @section attributes Attributes
    - logger (Callable): Logger object with info/warning/error methods
    - parser (SExpressionParser): S-expression parser instance
    - backup_manager (BackupManager): File backup manager instance
    """
    
    def __init__(self, logger: Optional[Callable] = None):
        """
        @brief Initialize the base localizer
        
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
    
    def is_file_locked(self, filepath: str) -> bool:
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
    
    def check_schematic_locks(self, project_dir: str) -> List[str]:
        """
        @brief Check for locked schematic files in project directory
        
        @param project_dir: Project directory path
        @return List of locked file basenames (empty if none locked)
        """
        schematic_files = glob.glob(os.path.join(project_dir, "**", f"*{EXTENSION_SCHEMATIC}"), recursive=True)
        
        locked_files = []
        for sch_file in schematic_files:
            if self.is_file_locked(sch_file):
                locked_files.append(os.path.basename(sch_file))
        
        return locked_files
    
    def find_schematic_files(self, project_dir: str) -> List[str]:
        """
        @brief Find all schematic files in project directory
        
        @param project_dir: Project directory path
        @return List of schematic file paths (sorted)
        """
        return _util_find_schematic_files(project_dir)
    
    def update_schematic_file(self, sch_file: str, replacements: List[tuple], 
                             create_backup: bool = True) -> int:
        """
        @brief Update a schematic file with reference replacements
        
        @param sch_file: Path to schematic file
        @param replacements: List of (old_ref, new_ref) tuples
        @param create_backup: Whether to create backup before modifying
        @return Number of replacements made
        
        @throws IOError if file operations fail
        """
        try:
            # Create backup if requested
            if create_backup:
                self.backup_manager.create_backup(sch_file)
            
            # Read the schematic file
            with open(sch_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply replacements
            updated_count, new_content = self.replace_references_in_content(
                content, replacements
            )
            
            # Write back only if changes were made
            if updated_count > 0:
                with open(sch_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.log('info', f"  Updated {updated_count} reference(s) in {os.path.basename(sch_file)}")
            else:
                self.log('info', f"  No changes needed in {os.path.basename(sch_file)}")
            
            return updated_count
            
        except Exception as e:
            self.log('error', f"Failed to update {os.path.basename(sch_file)}: {e}")
            raise
    
    def replace_references_in_content(self, content: str, 
                                     replacements: List[tuple]) -> tuple:
        """
        @brief Replace references in schematic content
        
        @param content: Original file content
        @param replacements: List of (old_ref, new_ref) tuples
        @return Tuple of (count, new_content)
        """
        new_content = content
        total_count = 0
        
        for old_ref, new_ref in replacements:
            if old_ref in new_content:
                count = new_content.count(old_ref)
                new_content = new_content.replace(old_ref, new_ref)
                total_count += count
        
        return total_count, new_content
