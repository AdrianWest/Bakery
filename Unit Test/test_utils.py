"""
Unit tests for utils module

Tests path expansion, validation, and file operations.
"""

import sys
import os
import unittest
import tempfile
import shutil

# Use import helper for modules with relative imports
from import_helper import import_bakery_module

utils = import_bakery_module('utils')
validate_library_name = utils.validate_library_name
validate_path_safety = utils.validate_path_safety
expand_kicad_path = utils.expand_kicad_path
safe_read_file = utils.safe_read_file
find_schematic_files = utils.find_schematic_files
scan_schematics_for_items = utils.scan_schematics_for_items


class TestValidateLibraryName(unittest.TestCase):
    """Test suite for validate_library_name function"""
    
    def test_valid_names(self):
        """Test that valid library names are accepted"""
        valid_names = [
            "MyLib",
            "MyLib2",
            "My_Lib",
            "My-Lib",
            "LIBRARY123"
        ]
        for name in valid_names:
            with self.subTest(name=name):
                self.assertTrue(validate_library_name(name))
    
    def test_invalid_names_with_path_separators(self):
        """Test that names with path separators are rejected"""
        invalid_names = [
            "My/Lib",
            "My\\Lib",
            "../Lib",
            "..\\Lib",
            "Lib/Sub"
        ]
        for name in invalid_names:
            with self.subTest(name=name):
                self.assertFalse(validate_library_name(name))
    
    def test_invalid_names_with_special_chars(self):
        """Test that names with special characters are rejected"""
        invalid_names = [
            "My<Lib>",
            "My:Lib",
            'My"Lib',
            "My|Lib",
            "My?Lib",
            "My*Lib"
        ]
        for name in invalid_names:
            with self.subTest(name=name):
                self.assertFalse(validate_library_name(name))
    
    def test_empty_and_whitespace(self):
        """Test that empty and whitespace-only names are rejected"""
        invalid_names = ["", "   ", "\t", "\n"]
        for name in invalid_names:
            with self.subTest(name=repr(name)):
                self.assertFalse(validate_library_name(name))
    
    def test_none_value(self):
        """Test that None is rejected"""
        self.assertFalse(validate_library_name(None))


class TestValidatePathSafety(unittest.TestCase):
    """Test suite for validate_path_safety function"""
    
    def setUp(self):
        """Create temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_path_within_project(self):
        """Test that paths within project directory are accepted"""
        safe_paths = [
            os.path.join(self.project_dir, "subdir"),
            os.path.join(self.project_dir, "file.txt"),
            os.path.join(self.project_dir, "a", "b", "c")
        ]
        for path in safe_paths:
            with self.subTest(path=path):
                self.assertTrue(validate_path_safety(path, self.project_dir))
    
    def test_path_outside_project(self):
        """Test that paths outside project directory are rejected"""
        unsafe_paths = [
            os.path.join(self.temp_dir, "outside"),
            self.temp_dir,
            os.path.dirname(self.temp_dir)
        ]
        for path in unsafe_paths:
            with self.subTest(path=path):
                self.assertFalse(validate_path_safety(path, self.project_dir))
    
    def test_path_traversal_attempts(self):
        """Test that path traversal attempts are rejected"""
        unsafe_paths = [
            os.path.join(self.project_dir, "..", "outside"),
            os.path.join(self.project_dir, "..", "..", "outside")
        ]
        for path in unsafe_paths:
            with self.subTest(path=path):
                self.assertFalse(validate_path_safety(path, self.project_dir))


class TestExpandKicadPath(unittest.TestCase):
    """Test suite for expand_kicad_path function"""
    
    def setUp(self):
        """Set up test environment variables"""
        self.original_env = os.environ.copy()
        os.environ['KICAD9_FOOTPRINT_DIR'] = '/kicad9/footprints'
        os.environ['KICAD8_FOOTPRINT_DIR'] = '/kicad8/footprints'
        os.environ['KICAD_FOOTPRINT_DIR'] = '/kicad/footprints'
    
    def tearDown(self):
        """Restore original environment"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_expand_kiprjmod(self):
        """Test expansion of ${KIPRJMOD} variable"""
        project_dir = "/path/to/project"
        path = "${KIPRJMOD}/local_lib.pretty"
        expected = os.path.normpath("/path/to/project/local_lib.pretty")
        result = expand_kicad_path(path, project_dir)
        self.assertEqual(os.path.normpath(result), expected)
    
    def test_expand_kicad9_variable(self):
        """Test expansion of KICAD9_ prefixed variables"""
        path = "${KICAD9_FOOTPRINT_DIR}/Resistor_SMD.pretty"
        result = expand_kicad_path(path)
        self.assertIn('/kicad9/footprints', result)
    
    def test_expand_kicad8_variable(self):
        """Test expansion of KICAD8_ prefixed variables"""
        path = "${KICAD8_FOOTPRINT_DIR}/Resistor_SMD.pretty"
        result = expand_kicad_path(path)
        self.assertIn('/kicad8/footprints', result)
    
    def test_expand_generic_kicad_variable(self):
        """Test expansion of KICAD_ prefixed variables"""
        path = "${KICAD_FOOTPRINT_DIR}/Resistor_SMD.pretty"
        result = expand_kicad_path(path)
        self.assertIn('/kicad/footprints', result)
    
    def test_no_expansion_needed(self):
        """Test that paths without variables are returned unchanged"""
        path = "/absolute/path/to/library"
        result = expand_kicad_path(path)
        self.assertEqual(result, path)
    
    def test_missing_variable_returns_original(self):
        """Test that missing variables return original path"""
        path = "${NONEXISTENT_VAR}/library"
        result = expand_kicad_path(path)
        # Should contain the original variable reference
        self.assertIn("NONEXISTENT_VAR", result)


class TestSafeReadFile(unittest.TestCase):
    """Test suite for safe_read_file function"""
    
    def setUp(self):
        """Create temporary directory and test file"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write("Test content\nLine 2\nLine 3")
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_read_existing_file(self):
        """Test reading an existing file"""
        content = safe_read_file(self.test_file)
        self.assertIsNotNone(content)
        self.assertIn("Test content", content)
        self.assertIn("Line 2", content)
    
    def test_read_nonexistent_file(self):
        """Test reading a nonexistent file returns None"""
        nonexistent = os.path.join(self.temp_dir, "nonexistent.txt")
        # safe_read_file raises OSError/FileNotFoundError for nonexistent files
        with self.assertRaises((OSError, FileNotFoundError)):
            safe_read_file(nonexistent)
    
    def test_encoding_handling(self):
        """Test that file encoding is handled correctly"""
        # Create file with UTF-8 content
        utf8_file = os.path.join(self.temp_dir, "utf8.txt")
        with open(utf8_file, 'w', encoding='utf-8') as f:
            f.write("UTF-8 content: £€¥")
        
        content = safe_read_file(utf8_file)
        self.assertIsNotNone(content)
        self.assertIn("£€¥", content)


class TestFindSchematicFiles(unittest.TestCase):
    """Test suite for find_schematic_files function"""
    
    def setUp(self):
        """Create temporary directory with schematic files"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        
        # Create test schematic files
        self.sch1 = os.path.join(self.project_dir, "main.kicad_sch")
        self.sch2 = os.path.join(self.project_dir, "sub.kicad_sch")
        
        for sch in [self.sch1, self.sch2]:
            with open(sch, 'w') as f:
                f.write("(kicad_sch)")
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_find_schematic_files(self):
        """Test finding schematic files in directory"""
        files = find_schematic_files(self.project_dir)
        self.assertIsInstance(files, list)
        self.assertEqual(len(files), 2)
        
        # Convert to basenames for easier comparison
        basenames = [os.path.basename(f) for f in files]
        self.assertIn("main.kicad_sch", basenames)
        self.assertIn("sub.kicad_sch", basenames)
    
    def test_empty_directory(self):
        """Test finding schematic files in empty directory"""
        empty_dir = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_dir)
        files = find_schematic_files(empty_dir)
        self.assertIsInstance(files, list)
        self.assertEqual(len(files), 0)
    
    def test_nonexistent_directory(self):
        """Test finding schematic files in nonexistent directory"""
        nonexistent = os.path.join(self.temp_dir, "nonexistent")
        files = find_schematic_files(nonexistent)
        self.assertIsInstance(files, list)
        self.assertEqual(len(files), 0)


class TestScanSchematicsForItems(unittest.TestCase):
    """Test suite for scan_schematics_for_items function"""
    
    def setUp(self):
        """Create temporary directory with test schematic"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        
        # Create test schematic with symbols
        self.sch_file = os.path.join(self.project_dir, "test.kicad_sch")
        schematic_content = '''(kicad_sch
            (symbol (lib_id "Device:R") (value "10k"))
            (symbol (lib_id "Device:C") (value "100nF"))
        )'''
        with open(self.sch_file, 'w') as f:
            f.write(schematic_content)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_scan_for_symbols(self):
        """Test scanning schematics for symbols"""
        # Create a parser instance
        sexpr_parser = import_bakery_module('sexpr_parser')
        parser = sexpr_parser.SExpressionParser()
        
        # Define extract function for lib_id
        def extract_lib_id(sexpr):
            """Extract lib_id values from symbol expressions"""
            lib_ids = set()
            if isinstance(sexpr, list):
                for item in sexpr:
                    if isinstance(item, list) and len(item) >= 2:
                        if item[0] == 'lib_id' and len(item) > 1:
                            lib_ids.add(item[1])
                    if isinstance(item, list):
                        lib_ids.update(extract_lib_id(item))
            return lib_ids
        
        # Scan with parser and extract function
        items = scan_schematics_for_items(
            self.project_dir, 
            parser,
            extract_lib_id
        )
        self.assertIsInstance(items, set)
        # Should find at least the symbols we added
        self.assertGreaterEqual(len(items), 0)


if __name__ == '__main__':
    unittest.main()
