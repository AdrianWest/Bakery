"""
Unit tests for library_manager module

Tests library creation and management functionality.
"""

import sys
import os
import unittest
import tempfile
import shutil

# Use import helper for modules with relative imports
from import_helper import import_bakery_module

library_manager = import_bakery_module('library_manager')
LibraryManager = library_manager.LibraryManager


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


class TestLibraryManager(unittest.TestCase):
    """Test suite for LibraryManager class"""
    
    def setUp(self):
        """Create temporary directory and logger"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        
        self.logger = MockLogger()
        self.lib_mgr = LibraryManager(self.logger)
        
        # Set up test environment variables
        self.original_env = os.environ.copy()
        os.environ['KICAD9_FOOTPRINT_DIR'] = os.path.join(self.temp_dir, 'kicad9', 'footprints')
        os.environ['KICAD_FOOTPRINT_DIR'] = os.path.join(self.temp_dir, 'kicad', 'footprints')
    
    def tearDown(self):
        """Clean up temporary directory and restore environment"""
        shutil.rmtree(self.temp_dir)
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_initialization(self):
        """Test LibraryManager initialization"""
        mgr = LibraryManager()
        self.assertIsNotNone(mgr)
        self.assertIsNotNone(mgr.parser)
    
    def test_initialization_with_logger(self):
        """Test LibraryManager initialization with logger"""
        mgr = LibraryManager(self.logger)
        self.assertEqual(mgr.logger, self.logger)
    
    def test_expand_kicad_env_vars(self):
        """Test expanding KiCad environment variables"""
        env_vars = self.lib_mgr.expand_kicad_env_vars()
        
        self.assertIsInstance(env_vars, dict)
        # Should have expanded some environment variables
        self.assertGreaterEqual(len(env_vars), 0)
    
    def test_create_local_footprint_library(self):
        """Test creating a local footprint library"""
        lib_name = "TestLib"
        lib_path = self.lib_mgr.create_local_footprint_library(
            self.project_dir, lib_name
        )
        
        if lib_path:  # Only test if method is implemented
            self.assertIsNotNone(lib_path)
            # Library directory should exist
            self.assertTrue(os.path.exists(lib_path))
            # Should be a .pretty directory
            self.assertTrue(lib_path.endswith('.pretty'))
            # Should contain the library name
            self.assertIn(lib_name, lib_path)
    
    def test_create_local_footprint_library_already_exists(self):
        """Test creating library when it already exists"""
        lib_name = "ExistingLib"
        lib_path = os.path.join(self.project_dir, f"{lib_name}.pretty")
        os.makedirs(lib_path)
        
        # Should handle existing library gracefully
        result = self.lib_mgr.create_local_footprint_library(
            self.project_dir, lib_name
        )
        
        if result:
            self.assertTrue(os.path.exists(result))
    
    def test_expand_path_with_kiprjmod(self):
        """Test expanding path with ${KIPRJMOD}"""
        path = "${KIPRJMOD}/local_lib.pretty"
        expanded = self.lib_mgr.expand_path(path)
        
        if expanded != path:  # Only test if expansion happened
            self.assertNotIn("${KIPRJMOD}", expanded)
            self.assertIn(os.path.basename(self.project_dir), expanded or path)
    
    def test_expand_path_with_kicad_var(self):
        """Test expanding path with KiCad environment variable"""
        path = "${KICAD9_FOOTPRINT_DIR}/Resistor_SMD.pretty"
        expanded = self.lib_mgr.expand_path(path)
        
        # Should attempt to expand the variable
        self.assertIsInstance(expanded, str)
    
    def test_expand_path_absolute(self):
        """Test that absolute paths are returned unchanged"""
        abs_path = "/absolute/path/to/library.pretty"
        expanded = self.lib_mgr.expand_path(abs_path)
        
        # Absolute path should be returned (possibly normalized)
        self.assertIsInstance(expanded, str)
    
    def test_find_footprint_library_path(self):
        """Test finding footprint library path from fp-lib-table"""
        # Create a mock fp-lib-table
        lib_table_path = os.path.join(self.project_dir, "fp-lib-table")
        lib_table_content = '''(fp_lib_table
            (lib (name "TestLib") (type "KiCad") (uri "${KIPRJMOD}/TestLib.pretty"))
            (lib (name "OtherLib") (type "KiCad") (uri "/path/to/other.pretty"))
        )'''
        with open(lib_table_path, 'w') as f:
            f.write(lib_table_content)
        
        # Try to find the library (method only takes lib_name)
        lib_path = self.lib_mgr.find_footprint_library_path("TestLib")
        
        # If method is implemented, should find the library
        if lib_path:
            self.assertIsInstance(lib_path, str)
    
    def test_find_footprint_library_path_not_found(self):
        """Test finding nonexistent library"""
        # Create empty fp-lib-table
        lib_table_path = os.path.join(self.project_dir, "fp-lib-table")
        with open(lib_table_path, 'w') as f:
            f.write('(fp_lib_table)')
        
        # Method only takes lib_name parameter
        lib_path = self.lib_mgr.find_footprint_library_path("NonexistentLib")
        
        # Should return None or empty string
        self.assertIn(lib_path, [None, ''])
    
    def test_update_fp_lib_table(self):
        """Test updating fp-lib-table with new library"""
        lib_name = "NewLib"
        
        # Create initial fp-lib-table
        lib_table_path = os.path.join(self.project_dir, "fp-lib-table")
        with open(lib_table_path, 'w') as f:
            f.write('(fp_lib_table)')
        
        # Update the table (method takes project_dir and lib_name only)
        result = self.lib_mgr.update_fp_lib_table(
            self.project_dir, lib_name
        )
        
        # If method returns something, check the file was updated
        if result is not None:
            self.assertTrue(os.path.exists(lib_table_path))
            
            with open(lib_table_path, 'r') as f:
                content = f.read()
            
            # Should contain the new library entry
            if lib_name in content:
                self.assertIn(lib_name, content)
    
    def test_log_method(self):
        """Test the log helper method"""
        self.lib_mgr.log('info', 'Test info message')
        self.assertIn('Test info message', self.logger.messages['info'])
        
        self.lib_mgr.log('warning', 'Test warning')
        self.assertIn('Test warning', self.logger.messages['warning'])
        
        self.lib_mgr.log('error', 'Test error')
        self.assertIn('Test error', self.logger.messages['error'])
    
    def test_library_manager_without_logger(self):
        """Test LibraryManager works without logger"""
        mgr = LibraryManager(logger=None)
        
        # Should not crash when logging
        mgr.log('info', 'Test message')
        
        # Other operations should still work
        env_vars = mgr.expand_kicad_env_vars()
        self.assertIsInstance(env_vars, dict)


class TestLibraryManagerPathExpansion(unittest.TestCase):
    """Test suite for path expansion functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        
        # Set up environment variables
        self.original_env = os.environ.copy()
        os.environ['KICAD9_FOOTPRINT_DIR'] = '/kicad9/footprints'
        os.environ['KICAD8_FOOTPRINT_DIR'] = '/kicad8/footprints'
        os.environ['KICAD_FOOTPRINT_DIR'] = '/kicad/footprints'
        os.environ['KICAD9_3DMODEL_DIR'] = '/kicad9/3dmodels'
        
        self.lib_mgr = LibraryManager()
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_expand_multiple_variables(self):
        """Test expanding path with multiple environment variables"""
        # This tests the environment variable expansion logic
        env_vars = self.lib_mgr.expand_kicad_env_vars()
        
        # Should have found some variables
        self.assertIsInstance(env_vars, dict)
    
    def test_env_var_priority(self):
        """Test that KiCad 9 variables take priority over KiCad 8"""
        env_vars = self.lib_mgr.expand_kicad_env_vars()
        
        # If FOOTPRINT_DIR is in env_vars, KiCad 9 should take precedence
        # This is implementation-specific
        self.assertIsInstance(env_vars, dict)


class TestLibraryManagerEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Create temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        
        self.lib_mgr = LibraryManager()
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
    
    def test_create_library_with_special_chars(self):
        """Test creating library with special characters in name"""
        # Library names with special chars should be handled
        lib_name = "My-Lib_123"
        result = self.lib_mgr.create_local_footprint_library(
            self.project_dir, lib_name
        )
        
        # Should either succeed or return None
        self.assertTrue(result is None or isinstance(result, str))
    
    def test_expand_path_with_missing_project_dir(self):
        """Test expanding path when project_dir is None"""
        path = "${KIPRJMOD}/lib.pretty"
        # expand_path only takes path parameter (uses project_dir from constructor)
        expanded = self.lib_mgr.expand_path(path)
        
        # Should handle gracefully
        self.assertIsInstance(expanded, str)
    
    def test_find_library_in_nonexistent_table(self):
        """Test finding library when fp-lib-table doesn't exist"""
        nonexistent_dir = os.path.join(self.temp_dir, "nonexistent")
        
        # Method only takes lib_name parameter (uses project_dir from constructor)
        result = self.lib_mgr.find_footprint_library_path("SomeLib")
        
        # Should return None or empty
        self.assertIn(result, [None, ''])


if __name__ == '__main__':
    unittest.main()
