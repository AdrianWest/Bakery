"""
Copyright (C) 2026 Bakery Contributors

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
@brief File backup management for Bakery plugin

Provides functionality for creating timestamped backups of files before
modification. Maintains a list of all backups created during a session.
"""

import os
import shutil
from typing import List, Optional, Callable
from datetime import datetime

from .constants import BACKUP_SUFFIX, BACKUP_TIMESTAMP_FORMAT, ERROR_BACKUP_FAILED


class BackupManager:
    """
    @brief Manages file backups before modifications
    """
    
    def __init__(self, logger: Optional[Callable] = None):
        """
        @brief Initialize backup manager
        
        @param logger: Optional logger object
        """
        self.logger = logger
        self.backups = []
    
    def log(self, level: str, message: str) -> None:
        """@brief Internal logging helper"""
        if self.logger:
            method = getattr(self.logger, level, None)
            if method:
                method(message)
    
    def create_backup(self, filepath: str) -> Optional[str]:
        """
        @brief Create a timestamped backup of a file
        
        @param filepath: Path to file to backup
        @return Path to backup file or None if failed
        
        @throws IOError if backup fails
        """
        try:
            if not os.path.exists(filepath):
                self.log('warning', f"File not found for backup: {filepath}")
                return None
            
            timestamp = datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
            backup_path = f"{filepath}{BACKUP_SUFFIX}_{timestamp}"
            
            shutil.copy2(filepath, backup_path)
            self.backups.append(backup_path)
            self.log('info', f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.log('error', f"{ERROR_BACKUP_FAILED}: {e}")
            raise
    
    def get_backups(self) -> List[str]:
        """
        @brief Get list of all backups created in this session
        
        @return List of backup file paths
        """
        return self.backups.copy()
