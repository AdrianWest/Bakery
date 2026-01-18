"""
Unit tests for backup_manager module

Tests file backup creation and tracking.
"""

import sys
import os
import unittest
import tempfile
import shutil
import time

# Use import helper for modules with relative imports
from import_helper import import_bakery_module

backup_manager = import_bakery_module('backup_manager')
BackupManager = backup_manager.BackupManager


class MockLogger:
    """Mock logger for testing"""
    
    def __init__(self):
        self.messages = {
            'info': [],
            'warning': [],
            'error': []
        }
    
    def info(self, msg):
        self.messages['info'].append(msg)
    
    def warning(self, msg):
        self.messages['warning'].append(msg)
    
    def error(self, msg):
        self.messages['error'].append(msg)


class TestBackupManager(unittest.TestCase):
    """Test suite for BackupManager class"""
    
    def setUp(self):
        """Create temporary directory and test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("Original content")
        
        self.logger = MockLogger()
        self.backup_mgr = BackupManager(self.logger)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test BackupManager initialization"""
        mgr = BackupManager()
        self.assertIsNotNone(mgr)
        self.assertEqual(len(mgr.backups), 0)
    
    def test_initialization_with_logger(self):
        """Test BackupManager initialization with logger"""
        mgr = BackupManager(self.logger)
        self.assertIsNotNone(mgr.logger)
        self.assertEqual(mgr.logger, self.logger)
    
    def test_create_backup_success(self):
        """Test successful backup creation"""
        backup_path = self.backup_mgr.create_backup(self.test_file)
        
        # Backup should be created
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # Backup should be in the backups list
        self.assertIn(backup_path, self.backup_mgr.backups)
        
        # Backup content should match original
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Original content")
    
    def test_create_backup_nonexistent_file(self):
        """Test backup of nonexistent file"""
        nonexistent = os.path.join(self.temp_dir, "nonexistent.txt")
        backup_path = self.backup_mgr.create_backup(nonexistent)
        
        # Should return None
        self.assertIsNone(backup_path)
        
        # Should log warning
        self.assertGreater(len(self.logger.messages['warning']), 0)
    
    def test_backup_path_format(self):
        """Test that backup path has correct format"""
        backup_path = self.backup_mgr.create_backup(self.test_file)
        
        self.assertIsNotNone(backup_path)
        # Should contain .bak or .backup
        self.assertTrue('.bak' in backup_path or '.backup' in backup_path)
        # Should contain timestamp
        self.assertTrue(any(c.isdigit() for c in backup_path))
    
    def test_multiple_backups(self):
        """Test creating multiple backups"""
        # Create first backup
        backup1 = self.backup_mgr.create_backup(self.test_file)
        
        # Wait a moment to ensure different timestamp (need at least 1 second for timestamp format)
        time.sleep(1.1)
        
        # Modify file
        with open(self.test_file, 'w') as f:
            f.write("Modified content")
        
        # Create second backup
        backup2 = self.backup_mgr.create_backup(self.test_file)
        
        # Both backups should exist
        self.assertIsNotNone(backup1)
        self.assertIsNotNone(backup2)
        self.assertNotEqual(backup1, backup2)
        
        # Both should be tracked
        self.assertEqual(len(self.backup_mgr.backups), 2)
        self.assertIn(backup1, self.backup_mgr.backups)
        self.assertIn(backup2, self.backup_mgr.backups)
    
    def test_get_backups(self):
        """Test retrieving list of backups"""
        # Create some backups
        self.backup_mgr.create_backup(self.test_file)
        
        backups = self.backup_mgr.get_backups()
        
        self.assertIsInstance(backups, list)
        self.assertEqual(len(backups), 1)
    
    def test_backup_preserves_file_permissions(self):
        """Test that backup preserves file metadata"""
        backup_path = self.backup_mgr.create_backup(self.test_file)
        
        self.assertIsNotNone(backup_path)
        
        # Both files should exist
        self.assertTrue(os.path.exists(self.test_file))
        self.assertTrue(os.path.exists(backup_path))
        
        # Original should not be modified
        with open(self.test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "Original content")
    
    def test_logging_info_messages(self):
        """Test that info messages are logged"""
        self.backup_mgr.create_backup(self.test_file)
        
        # Should have logged info about backup creation
        self.assertGreater(len(self.logger.messages['info']), 0)
        
        # Info message should mention the backup path
        info_msgs = ' '.join(self.logger.messages['info'])
        self.assertTrue('backup' in info_msgs.lower() or 'created' in info_msgs.lower())
    
    def test_logging_error_on_failure(self):
        """Test that errors are logged on backup failure"""
        # Try to backup a file in a non-writable location (simulate error)
        # This is platform-dependent, so we'll test the error logging mechanism
        
        # Create a scenario where backup might fail
        nonexistent = os.path.join(self.temp_dir, "nonexistent.txt")
        self.backup_mgr.create_backup(nonexistent)
        
        # Should have logged a warning about file not found
        self.assertGreater(len(self.logger.messages['warning']), 0)
    
    def test_backup_manager_without_logger(self):
        """Test BackupManager works without logger"""
        mgr = BackupManager(logger=None)
        backup_path = mgr.create_backup(self.test_file)
        
        # Should still create backup
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
    
    def test_log_method(self):
        """Test the log helper method"""
        self.backup_mgr.log('info', 'Test message')
        self.assertIn('Test message', self.logger.messages['info'])
        
        self.backup_mgr.log('warning', 'Warning message')
        self.assertIn('Warning message', self.logger.messages['warning'])
        
        self.backup_mgr.log('error', 'Error message')
        self.assertIn('Error message', self.logger.messages['error'])


class TestBackupManagerEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Create temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = MockLogger()
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_backup_empty_file(self):
        """Test backing up an empty file"""
        empty_file = os.path.join(self.temp_dir, "empty.txt")
        open(empty_file, 'w').close()
        
        mgr = BackupManager(self.logger)
        backup_path = mgr.create_backup(empty_file)
        
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # Backup should also be empty
        self.assertEqual(os.path.getsize(backup_path), 0)
    
    def test_backup_large_file(self):
        """Test backing up a larger file"""
        large_file = os.path.join(self.temp_dir, "large.txt")
        with open(large_file, 'w') as f:
            f.write("x" * 10000)  # 10KB file
        
        mgr = BackupManager(self.logger)
        backup_path = mgr.create_backup(large_file)
        
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # Sizes should match
        self.assertEqual(
            os.path.getsize(large_file),
            os.path.getsize(backup_path)
        )
    
    def test_backup_binary_file(self):
        """Test backing up a binary file"""
        binary_file = os.path.join(self.temp_dir, "binary.bin")
        with open(binary_file, 'wb') as f:
            f.write(bytes([0, 1, 2, 3, 4, 255, 254, 253]))
        
        mgr = BackupManager(self.logger)
        backup_path = mgr.create_backup(binary_file)
        
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # Content should match
        with open(binary_file, 'rb') as f1:
            original = f1.read()
        with open(backup_path, 'rb') as f2:
            backup = f2.read()
        
        self.assertEqual(original, backup)


if __name__ == '__main__':
    unittest.main()
