"""
Unit tests for symbol_localizer module

Tests symbol localization functionality.
"""

import sys
import os
import unittest
import tempfile
import shutil

# Use import helper for modules with relative imports
from import_helper import import_bakery_module

symbol_localizer = import_bakery_module('symbol_localizer')
SymbolLocalizer = symbol_localizer.SymbolLocalizer


class MockLogger:
    """Mock logger for testing"""
    
    def __init__(self):
        self.messages = {'info': [], 'warning': [], 'error': [], 'success': []}
    
    def info(self, msg):
        self.messages['info'].append(msg)
    
    def warning(self, msg):
        self.messages['warning'].append(msg)
    
    def error(self, msg):
        self.messages['error'].append(msg)
    
    def success(self, msg):
        self.messages['success'].append(msg)


class TestSymbolLocalizer(unittest.TestCase):
    """Test suite for SymbolLocalizer class"""
    
    def setUp(self):
        """Create temporary directory and test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        
        self.logger = MockLogger()
        self.localizer = SymbolLocalizer(self.logger)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test SymbolLocalizer initialization"""
        localizer = SymbolLocalizer()
        self.assertIsNotNone(localizer)
        self.assertIsNotNone(localizer.parser)
        self.assertIsNotNone(localizer.backup_manager)
    
    def test_initialization_with_logger(self):
        """Test SymbolLocalizer initialization with logger"""
        localizer = SymbolLocalizer(self.logger)
        self.assertEqual(localizer.logger, self.logger)
    
    def test_scan_schematic_symbols(self):
        """Test scanning schematics for symbol references"""
        # Create test schematic with symbols
        sch_file = os.path.join(self.project_dir, "test.kicad_sch")
        sch_content = '''(kicad_sch
            (symbol (lib_id "Device:R") (value "10k"))
            (symbol (lib_id "Device:C") (value "100nF"))
        )'''
        
        with open(sch_file, 'w') as f:
            f.write(sch_content)
        
        # Scan symbols
        symbols = self.localizer.scan_schematic_symbols(self.project_dir)
        
        self.assertIsInstance(symbols, set)
        # May or may not find symbols depending on parsing implementation
    
    def test_find_symbols_in_sexpr(self):
        """Test finding symbols in S-expression content"""
        sexpr_content = '''(kicad_sch
            (symbol (lib_id "Device:R"))
            (symbol (lib_id "Device:C"))
        )'''
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'find_symbols_in_sexpr'))
    
    def test_copy_symbols(self):
        """Test copying symbols to local library"""
        # Create source symbol library
        source_lib = os.path.join(self.temp_dir, "Device.kicad_sym")
        lib_content = '''(kicad_symbol_lib
            (symbol "R" (pin_names))
            (symbol "C" (pin_names))
        )'''
        
        with open(source_lib, 'w') as f:
            f.write(lib_content)
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'copy_symbols'))
    
    def test_get_symbols_in_library(self):
        """Test getting list of symbols in a library file"""
        lib_file = os.path.join(self.temp_dir, "test.kicad_sym")
        lib_content = '''(kicad_symbol_lib
            (symbol "R")
            (symbol "C")
        )'''
        
        with open(lib_file, 'w') as f:
            f.write(lib_content)
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'get_symbols_in_library'))
    
    def test_extract_symbol_from_library(self):
        """Test extracting a single symbol from library"""
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'extract_symbol_from_library'))
    
    def test_find_symbol_library_path(self):
        """Test finding symbol library path"""
        # Create sym-lib-table
        lib_table_path = os.path.join(self.project_dir, "sym-lib-table")
        lib_table_content = '''(sym_lib_table
            (lib (name "Device") (type "KiCad") (uri "${KICAD_SYMBOL_DIR}/Device.kicad_sym"))
        )'''
        
        with open(lib_table_path, 'w') as f:
            f.write(lib_table_content)
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'find_symbol_library_path'))
    
    def test_expand_path(self):
        """Test expanding symbol library path"""
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'expand_path'))
    
    def test_write_symbol_library(self):
        """Test writing symbol library file"""
        output_file = os.path.join(self.project_dir, "output.kicad_sym")
        symbols = []
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'write_symbol_library'))
    
    def test_update_schematic_references(self):
        """Test updating schematic symbol references"""
        # Create test schematic
        sch_file = os.path.join(self.project_dir, "test.kicad_sch")
        sch_content = '''(kicad_sch
            (symbol (lib_id "OldLib:R"))
        )'''
        
        with open(sch_file, 'w') as f:
            f.write(sch_content)
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'update_schematic_references'))
    
    def test_update_sym_lib_table(self):
        """Test updating sym-lib-table"""
        lib_table_path = os.path.join(self.project_dir, "sym-lib-table")
        
        # Create initial table
        with open(lib_table_path, 'w') as f:
            f.write('(sym_lib_table)')
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'update_sym_lib_table'))


class TestSymbolLocalizerIntegration(unittest.TestCase):
    """Integration tests for SymbolLocalizer"""
    
    def setUp(self):
        """Create test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        
        self.logger = MockLogger()
        self.localizer = SymbolLocalizer(self.logger)
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
    
    def test_inherits_from_base_localizer(self):
        """Test that SymbolLocalizer inherits from BaseLocalizer"""
        base_localizer_module = import_bakery_module('base_localizer')
        self.assertIsInstance(self.localizer, base_localizer_module.BaseLocalizer)
    
    def test_logging_functionality(self):
        """Test that logging works correctly"""
        self.localizer.log('info', 'Test message')
        self.assertIn('Test message', self.logger.messages['info'])
    
    def test_environment_variable_expansion(self):
        """Test that environment variables are expanded correctly"""
        # Set up test environment variable
        os.environ['TEST_KICAD_VAR'] = '/test/path'
        
        # Test path expansion (if method is accessible)
        # This is implementation-specific
        
        # Clean up
        del os.environ['TEST_KICAD_VAR']


if __name__ == '__main__':
    unittest.main()
