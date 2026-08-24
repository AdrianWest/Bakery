"""!
@file test_backup_manager.py

@brief Unit tests for KiCad-compatible project ZIP backups.
"""

import os
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from import_helper import import_bakery_module

backup_manager = import_bakery_module('backup_manager')
BackupManager = backup_manager.BackupManager


class MockLogger:
    """Collect backup log messages for assertions."""

    def __init__(self):
        self.messages = {
            'info': [],
            'warning': [],
            'error': [],
            'success': []
        }

    def info(self, message):
        self.messages['info'].append(message)

    def warning(self, message):
        self.messages['warning'].append(message)

    def error(self, message):
        self.messages['error'].append(message)

    def success(self, message):
        self.messages['success'].append(message)


class TestBackupManager(unittest.TestCase):
    """Tests for KiCad-compatible project archives."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_name = "5V_REG_20A"
        self.logger = MockLogger()
        self.manager = BackupManager(self.logger)

        files = {
            f"{self.project_name}.kicad_pro": "project",
            f"{self.project_name}.kicad_prl": "settings",
            f"{self.project_name}.kicad_pcb": "board",
            f"{self.project_name}.kicad_sch": "schematic",
            "fp-lib-table": "(fp_lib_table)",
            "sym-lib-table": "(sym_lib_table)",
            "metadata.json": "{}",
            "notes.txt": "not archived",
            "datasheet.pdf": "%PDF",
            "model.step": "STEP"
        }
        for name, content in files.items():
            with open(
                os.path.join(self.temp_dir, name),
                'w',
                encoding='utf-8'
            ) as project_file:
                project_file.write(content)

        footprint_dir = os.path.join(self.temp_dir, "Local.pretty")
        os.makedirs(footprint_dir)
        with open(
            os.path.join(footprint_dir, "Part.kicad_mod"),
            'w',
            encoding='utf-8'
        ) as footprint:
            footprint.write("(footprint Part)")

        hidden_dir = os.path.join(self.temp_dir, ".history")
        os.makedirs(hidden_dir)
        with open(
            os.path.join(hidden_dir, "hidden.kicad_sch"),
            'w',
            encoding='utf-8'
        ) as hidden_file:
            hidden_file.write("(kicad_sch)")

        existing_backup_dir = os.path.join(
            self.temp_dir,
            f"{self.project_name}-backups"
        )
        os.makedirs(existing_backup_dir)
        with open(
            os.path.join(existing_backup_dir, "must-not-archive.kicad_sch"),
            'w',
            encoding='utf-8'
        ) as backup_content:
            backup_content.write("(kicad_sch)")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch.object(backup_manager, 'datetime')
    def test_creates_kicad_named_archive(self, mock_datetime):
        """Archive naming and contents match KiCad's ZIP backup convention."""
        mock_datetime.now.return_value.strftime.return_value = (
            "2026-01-11_205526"
        )

        backup_path = self.manager.create_project_backup(
            self.temp_dir,
            self.project_name
        )

        expected_path = os.path.join(
            self.temp_dir,
            "5V_REG_20A-backups",
            "5V_REG_20A-2026-01-11_205526.zip"
        )
        self.assertEqual(backup_path, expected_path)
        self.assertTrue(os.path.exists(backup_path))

        with zipfile.ZipFile(backup_path, 'r') as archive:
            archived_names = set(archive.namelist())

        self.assertIn("5V_REG_20A.kicad_pro", archived_names)
        self.assertIn("5V_REG_20A.kicad_pcb", archived_names)
        self.assertIn("5V_REG_20A.kicad_sch", archived_names)
        self.assertIn("Local.pretty/Part.kicad_mod", archived_names)
        self.assertIn("fp-lib-table", archived_names)
        self.assertIn("metadata.json", archived_names)
        self.assertIn("notes.txt", archived_names)
        self.assertIn("datasheet.pdf", archived_names)
        self.assertIn("model.step", archived_names)
        self.assertNotIn(".history/hidden.kicad_sch", archived_names)
        self.assertNotIn(
            "5V_REG_20A-backups/must-not-archive.kicad_sch",
            archived_names
        )

    def test_rejects_project_without_kicad_files(self):
        """Backup creation fails instead of producing an empty archive."""
        empty_project = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_project)

        with self.assertRaises(RuntimeError):
            self.manager.create_project_backup(empty_project, "empty")

    def test_rejects_unsafe_project_name(self):
        """Project names cannot alter the backup destination path."""
        with self.assertRaises(ValueError):
            self.manager.create_project_backup(
                self.temp_dir,
                "../outside"
            )
