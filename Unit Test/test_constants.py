"""
Unit tests for constants module

Tests validate that all required constants are defined
and have the expected types and values.
"""

import sys
import os
import unittest

# Use import helper for modules with relative imports (constants doesn't have relative imports but for consistency)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import constants


class TestConstants(unittest.TestCase):
    """Test suite for constants module"""
    
    def test_plugin_metadata_exists(self):
        """Test that plugin metadata constants are defined"""
        self.assertTrue(hasattr(sys.modules['constants'], 'PLUGIN_VERSION'))
        self.assertTrue(hasattr(sys.modules['constants'], 'PLUGIN_NAME'))
        self.assertTrue(hasattr(sys.modules['constants'], 'PLUGIN_CATEGORY'))
        self.assertTrue(hasattr(sys.modules['constants'], 'PLUGIN_DESCRIPTION'))
    
    def test_plugin_version_format(self):
        """Test that plugin version follows semantic versioning"""
        import re
        version_pattern = r'^\d+\.\d+\.\d+$'
        self.assertRegex(constants.PLUGIN_VERSION, version_pattern,
                        "Version should follow format X.Y.Z")
    
    def test_plugin_name_not_empty(self):
        """Test that plugin name is not empty"""
        self.assertIsInstance(constants.PLUGIN_NAME, str)
        self.assertGreater(len(constants.PLUGIN_NAME), 0)
    
    def test_ui_constants_are_tuples(self):
        """Test that UI size constants are tuples"""
        self.assertIsInstance(constants.LOGGER_WINDOW_SIZE, tuple)
        self.assertIsInstance(constants.CONFIG_DIALOG_SIZE, tuple)
        self.assertEqual(len(constants.LOGGER_WINDOW_SIZE), 2)
        self.assertEqual(len(constants.CONFIG_DIALOG_SIZE), 2)
    
    def test_ui_sizes_are_positive(self):
        """Test that UI sizes are positive integers"""
        self.assertGreater(constants.LOGGER_WINDOW_SIZE[0], 0)
        self.assertGreater(constants.LOGGER_WINDOW_SIZE[1], 0)
        self.assertGreater(constants.CONFIG_DIALOG_SIZE[0], 0)
        self.assertGreater(constants.CONFIG_DIALOG_SIZE[1], 0)
    
    def test_color_constants_are_tuples(self):
        """Test that color constants are RGB tuples"""
        self.assertIsInstance(constants.COLOR_WARNING_BG, tuple)
        self.assertIsInstance(constants.COLOR_ERROR_BG, tuple)
        self.assertEqual(len(constants.COLOR_WARNING_BG), 3)
        self.assertEqual(len(constants.COLOR_ERROR_BG), 3)
    
    def test_color_values_valid_range(self):
        """Test that color values are in valid RGB range (0-255)"""
        for color in constants.COLOR_WARNING_BG:
            self.assertGreaterEqual(color, 0)
            self.assertLessEqual(color, 255)
        for color in constants.COLOR_ERROR_BG:
            self.assertGreaterEqual(color, 0)
            self.assertLessEqual(color, 255)
    
    def test_default_library_names_not_empty(self):
        """Test that default library names are defined"""
        self.assertIsInstance(constants.DEFAULT_LOCAL_LIB_NAME, str)
        self.assertIsInstance(constants.DEFAULT_SYMBOL_LIB_NAME, str)
        self.assertIsInstance(constants.DEFAULT_SYMBOL_DIR_NAME, str)
        self.assertIsInstance(constants.DEFAULT_MODELS_DIR_NAME, str)
        self.assertGreater(len(constants.DEFAULT_LOCAL_LIB_NAME), 0)
        self.assertGreater(len(constants.DEFAULT_SYMBOL_LIB_NAME), 0)
        self.assertGreater(len(constants.DEFAULT_SYMBOL_DIR_NAME), 0)
        self.assertGreater(len(constants.DEFAULT_MODELS_DIR_NAME), 0)
    
    def test_file_extensions_start_with_dot(self):
        """Test that file extensions start with a dot"""
        extensions = [
            constants.EXTENSION_FOOTPRINT,
            constants.EXTENSION_FOOTPRINT_LIB,
            constants.EXTENSION_SYMBOL,
            constants.EXTENSION_SCHEMATIC,
            constants.EXTENSION_PCB,
            constants.BACKUP_SUFFIX
        ]
        for ext in extensions:
            if ext != constants.EXTENSION_FP_LIB_TABLE and ext != constants.EXTENSION_SYM_LIB_TABLE:
                self.assertTrue(ext.startswith('.'), f"Extension {ext} should start with .")
    
    def test_kicad_versions_is_list(self):
        """Test that KICAD_VERSIONS is a list"""
        self.assertIsInstance(constants.KICAD_VERSIONS, list)
        self.assertGreater(len(constants.KICAD_VERSIONS), 0)
    
    def test_kicad_version_compatibility(self):
        """Test that primary and fallback versions are in KICAD_VERSIONS"""
        self.assertIn(constants.KICAD_VERSION_PRIMARY, constants.KICAD_VERSIONS)
        self.assertIn(constants.KICAD_VERSION_FALLBACK, constants.KICAD_VERSIONS)
    
    def test_env_var_prefixes_defined(self):
        """Test that environment variable prefixes are defined"""
        self.assertTrue(hasattr(sys.modules['constants'], 'ENV_VAR_PREFIX_PRIMARY'))
        self.assertTrue(hasattr(sys.modules['constants'], 'ENV_VAR_PREFIX_FALLBACK'))
        self.assertTrue(hasattr(sys.modules['constants'], 'ENV_VAR_PREFIX_GENERIC'))
        self.assertTrue(hasattr(sys.modules['constants'], 'ENV_VAR_KIPRJMOD'))
    
    def test_env_var_prefixes_end_with_underscore(self):
        """Test that environment variable prefixes end with underscore"""
        self.assertTrue(constants.ENV_VAR_PREFIX_PRIMARY.endswith('_'))
        self.assertTrue(constants.ENV_VAR_PREFIX_FALLBACK.endswith('_'))
        self.assertTrue(constants.ENV_VAR_PREFIX_GENERIC.endswith('_'))
    
    def test_backup_timestamp_format_valid(self):
        """Test that backup timestamp format is valid strftime format"""
        from datetime import datetime
        try:
            # Try to format current time with the timestamp format
            timestamp = datetime.now().strftime(constants.BACKUP_TIMESTAMP_FORMAT)
            self.assertIsInstance(timestamp, str)
            self.assertGreater(len(timestamp), 0)
        except Exception as e:
            self.fail(f"BACKUP_TIMESTAMP_FORMAT is not a valid strftime format: {e}")
    
    def test_sexpr_keywords_are_strings(self):
        """Test that S-expression keywords are strings"""
        keywords = [
            constants.SEXPR_LIB, constants.SEXPR_NAME, constants.SEXPR_TYPE
        ]
        for keyword in keywords:
            self.assertIsInstance(keyword, str)
            self.assertGreater(len(keyword), 0)
    
    def test_config_keys_defined(self):
        """Test that configuration keys are defined"""
        config_keys = [
            constants.CONFIG_LOCAL_LIB_NAME,
            constants.CONFIG_SYMBOL_LIB_NAME,
            constants.CONFIG_SYMBOL_DIR_NAME,
            constants.CONFIG_MODELS_DIR_NAME,
            constants.CONFIG_CREATE_BACKUPS
        ]
        for key in config_keys:
            self.assertIsInstance(key, str)
            self.assertGreater(len(key), 0)


if __name__ == '__main__':
    unittest.main()
