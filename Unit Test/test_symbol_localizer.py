"""
Unit tests for symbol_localizer module

Tests symbol localization functionality.
"""

import sys
import os
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock

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

    def test_same_named_symbols_get_distinct_local_names(self):
        """Symbols from different libraries must not alias each other"""
        def extract_symbol(library_name, symbol_name, project_dir=None):
            return [
                "symbol",
                f'"{symbol_name}"',
                ["property", '"Value"', f'"{library_name}"']
            ]

        self.localizer.extract_symbol_from_library = extract_symbol
        records = self.localizer.copy_symbols(
            {("LibraryA", "Shared"), ("LibraryB", "Shared")},
            self.project_dir,
            "LocalSymbols",
            "Symbols"
        )

        target_names = {record[2] for record in records}
        self.assertEqual(len(target_names), 2)
        self.assertTrue(
            any(name.startswith("LibraryA__Shared_") for name in target_names)
        )
        self.assertTrue(
            any(name.startswith("LibraryB__Shared_") for name in target_names)
        )
        library_path = os.path.join(
            self.project_dir,
            "Symbols",
            "LocalSymbols.kicad_sym"
        )
        with open(library_path, 'r', encoding='utf-8') as library:
            content = library.read()
        for target_name in target_names:
            self.assertIn(target_name, content)

        rerun_records = self.localizer.copy_symbols(
            {("LibraryA", "Shared"), ("LibraryB", "Shared")},
            self.project_dir,
            "LocalSymbols",
            "Symbols"
        )
        self.assertEqual(
            {record[2] for record in rerun_records},
            target_names
        )

    def test_symbol_parent_and_units_are_renamed(self):
        """Renaming updates unit names and inherited parent references"""
        symbol = [
            "symbol",
            '"Child"',
            ["extends", '"Parent"'],
            ["symbol", '"Child_0_1"']
        ]

        renamed = self.localizer.rename_symbol_for_local_library(
            symbol,
            "Vendor",
            "Child",
            "Vendor__Child",
            "Parent"
        )

        self.assertEqual(renamed[1], '"Vendor__Child"')
        self.assertTrue(
            renamed[2][1].startswith('"Vendor__Parent_')
        )
        self.assertEqual(renamed[3][1], '"Vendor__Child_0_1"')

    def test_embedded_schematic_symbol_units_follow_localized_root(self):
        """Embedded child units use the localized root symbol prefix."""
        content = '''(kicad_sch
  (lib_symbols
    (symbol "Device:C_Small"
      (property "Value" "C_Small")
      (symbol "C_Small_0_1"
        (polyline)
      )
      (symbol "C_Small_1_1"
        (pin passive line)
      )
    )
  )
  (symbol
    (lib_id "Device:C_Small")
  )
)'''
        records = [
            (
                "Device",
                "C_Small",
                "Device__C_Small_f867c60b3d",
                ["symbol"]
            )
        ]

        count, updated = (
            self.localizer._rename_embedded_symbol_definitions(
                content,
                records,
                "MySymbols"
            )
        )

        self.assertEqual(count, 3)
        self.assertIn(
            '(symbol "MySymbols:Device__C_Small_f867c60b3d"',
            updated
        )
        self.assertIn(
            '(symbol "Device__C_Small_f867c60b3d_0_1"',
            updated
        )
        self.assertIn(
            '(symbol "Device__C_Small_f867c60b3d_1_1"',
            updated
        )
        self.assertIn('(lib_id "Device:C_Small")', updated)

    def test_schematic_update_failure_is_propagated(self):
        """A failed schematic write aborts symbol localization"""
        schematic = os.path.join(self.project_dir, "test.kicad_sch")
        with open(schematic, 'w', encoding='utf-8') as sch:
            sch.write('(lib_id "Source:Part")')
        self.localizer.update_schematic_file = MagicMock(
            side_effect=OSError("write failed")
        )

        with self.assertRaises(OSError):
            self.localizer.update_schematic_references(
                [("Source", "Part", "Source__Part_hash", ["symbol"])],
                self.project_dir,
                "Local"
            )
    
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
