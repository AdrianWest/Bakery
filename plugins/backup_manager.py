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
@file backup_manager.py

@brief KiCad-compatible timestamped project ZIP backups.

Creates a project archive before Bakery modifies any project files. The archive
uses KiCad's project-directory naming while preserving all visible project
files and subdirectories.

@section description_backup_manager Detailed Description
Backups are written to a sibling directory named `<project>-backups` using
`<project>-YYYY-MM-DD_HHMMSS.zip`. Project contents are archived recursively
while hidden files, hidden directories, and the project's backup directory are
excluded.
"""

import os
import stat
import tempfile
import zipfile
from datetime import datetime
from typing import Callable, List, Optional

from .constants import (
    PROJECT_BACKUP_DIRECTORY_SUFFIX,
    PROJECT_BACKUP_TIMESTAMP_FORMAT
)
from .utils import log_message, validate_path_safety


class BackupManager:
    """!
    @brief Creates KiCad-compatible project backup archives.

    @section methods Methods
    - :py:meth:`~BackupManager.__init__`
    - :py:meth:`~BackupManager.create_project_backup`

    @section attributes Attributes
    - logger (Callable): Optional Bakery logger.
    """

    def __init__(self, logger: Optional[Callable] = None):
        """
        @brief Initialize the project backup manager.

        @param logger: Optional logger object.
        """
        self.logger = logger

    @staticmethod
    def _is_hidden(path: str) -> bool:
        """
        @brief Determine whether a path is hidden on the current platform.

        @param path: File or directory path.
        @return True for dot-prefixed or OS-hidden paths.
        """
        if os.path.basename(path).startswith('.'):
            return True
        try:
            attributes = getattr(os.stat(path), 'st_file_attributes', 0)
            hidden_flag = getattr(stat, 'FILE_ATTRIBUTE_HIDDEN', 0)
            return bool(hidden_flag and attributes & hidden_flag)
        except OSError:
            return False

    def _find_project_files(
        self,
        project_dir: str,
        backup_dir: str
    ) -> List[str]:
        """
        @brief Find visible project files eligible for the backup archive.

        @param project_dir: Project root directory.
        @param backup_dir: Backup directory to exclude from traversal.
        @return Sorted absolute file paths.
        """
        files = []
        backup_realpath = os.path.realpath(backup_dir)

        for root, directory_names, file_names in os.walk(project_dir):
            directory_names[:] = [
                name
                for name in directory_names
                if (
                    not self._is_hidden(os.path.join(root, name))
                    and os.path.realpath(os.path.join(root, name))
                    != backup_realpath
                )
            ]
            for file_name in file_names:
                file_path = os.path.join(root, file_name)
                if self._is_hidden(file_path):
                    continue
                files.append(file_path)

        return sorted(files)

    @staticmethod
    def _validate_project_name(project_name: str) -> None:
        """
        @brief Validate a project name used to construct backup paths.

        @param project_name: KiCad project name without extension.

        @throws ValueError if the name is empty or contains path components.
        """
        if not project_name or os.path.basename(project_name) != project_name:
            raise ValueError(f"Invalid project name for backup: {project_name}")

    @classmethod
    def _get_backup_directory(
        cls,
        project_dir: str,
        project_name: str
    ) -> str:
        """
        @brief Resolve and validate the project's backup directory.

        @param project_dir: Project root directory.
        @param project_name: KiCad project name without extension.
        @return Absolute backup directory path.

        @throws ValueError if the project name or backup path is unsafe.
        """
        cls._validate_project_name(project_name)
        backup_dir = os.path.join(
            project_dir,
            f"{project_name}{PROJECT_BACKUP_DIRECTORY_SUFFIX}"
        )
        if not validate_path_safety(backup_dir, project_dir):
            raise ValueError(f"Unsafe project backup path: {backup_dir}")
        return backup_dir

    def create_project_backup(
        self,
        project_dir: str,
        project_name: str
    ) -> str:
        """
        @brief Create a timestamped ZIP archive before localization.

        @param project_dir: Project root directory.
        @param project_name: KiCad project name without extension.
        @return Absolute path to the created ZIP archive.

        @throws ValueError if the project or backup path is invalid.
        @throws OSError if directories or archive files cannot be created.
        @throws RuntimeError if no KiCad project files are available to archive.
        @throws zipfile.BadZipFile if ZIP creation fails.
        """
        backup_dir = self._get_backup_directory(project_dir, project_name)

        files = self._find_project_files(project_dir, backup_dir)
        if not files:
            raise RuntimeError(
                f"No project files found to back up in: {project_dir}"
            )

        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime(PROJECT_BACKUP_TIMESTAMP_FORMAT)
        backup_path = os.path.join(
            backup_dir,
            f"{project_name}-{timestamp}.zip"
        )
        if os.path.exists(backup_path):
            raise FileExistsError(
                f"Project backup already exists: {backup_path}"
            )

        file_descriptor, temp_path = tempfile.mkstemp(
            dir=backup_dir,
            prefix=f".{project_name}-",
            suffix=".zip.tmp"
        )
        os.close(file_descriptor)

        try:
            with zipfile.ZipFile(
                temp_path,
                mode='w',
                compression=zipfile.ZIP_DEFLATED,
                allowZip64=True
            ) as archive:
                for file_path in files:
                    archive_name = os.path.relpath(
                        file_path,
                        project_dir
                    ).replace(os.sep, '/')
                    archive.write(file_path, archive_name)
            os.replace(temp_path, backup_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        log_message(
            self.logger,
            'success',
            f"Project backup created: {backup_path}"
        )
        log_message(
            self.logger,
            'info',
            f"Backed up {len(files)} project file(s)"
        )
        return backup_path
