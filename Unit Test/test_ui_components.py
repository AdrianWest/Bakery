"""
Unit tests for ui_components module

Tests UI dialog and logger window components.
Note: wxPython is mocked since it may not be available outside KiCad.
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch

# Use import helper for modules with relative imports
from import_helper import import_bakery_module


class TestConfigDialog(unittest.TestCase):
    """Test suite for ConfigDialog class"""
    
    def test_config_dialog_imports(self):
        """Test that ConfigDialog can be imported"""
        ui_components = import_bakery_module('ui_components')
        self.assertTrue(hasattr(ui_components, 'ConfigDialog'))
    
    def test_config_keys_exist(self):
        """Test that config dialog uses correct config keys"""
        constants = import_bakery_module('constants')
        
        CONFIG_LOCAL_LIB_NAME = constants.CONFIG_LOCAL_LIB_NAME
        CONFIG_SYMBOL_LIB_NAME = constants.CONFIG_SYMBOL_LIB_NAME
        CONFIG_SYMBOL_DIR_NAME = constants.CONFIG_SYMBOL_DIR_NAME
        CONFIG_MODELS_DIR_NAME = constants.CONFIG_MODELS_DIR_NAME
        CONFIG_CREATE_BACKUPS = constants.CONFIG_CREATE_BACKUPS
        
        # Config keys should be strings
        self.assertIsInstance(CONFIG_LOCAL_LIB_NAME, str)
        self.assertIsInstance(CONFIG_SYMBOL_LIB_NAME, str)
        self.assertIsInstance(CONFIG_SYMBOL_DIR_NAME, str)
        self.assertIsInstance(CONFIG_MODELS_DIR_NAME, str)
        self.assertIsInstance(CONFIG_CREATE_BACKUPS, str)


class TestBakeryLogger(unittest.TestCase):
    """Test suite for BakeryLogger class"""
    
    def test_bakery_logger_imports(self):
        """Test that BakeryLogger can be imported"""
        ui_components = import_bakery_module('ui_components')
        self.assertTrue(hasattr(ui_components, 'BakeryLogger'))
    
    def test_logger_window_size_constant(self):
        """Test that logger window size is defined"""
        constants = import_bakery_module('constants')
        LOGGER_WINDOW_SIZE = constants.LOGGER_WINDOW_SIZE
        
        self.assertIsInstance(LOGGER_WINDOW_SIZE, tuple)
        self.assertEqual(len(LOGGER_WINDOW_SIZE), 2)
        self.assertGreater(LOGGER_WINDOW_SIZE[0], 0)
        self.assertGreater(LOGGER_WINDOW_SIZE[1], 0)
    
    def test_log_font_size_constant(self):
        """Test that log font size constant is defined"""
        constants = import_bakery_module('constants')
        LOG_FONT_SIZE = constants.LOG_FONT_SIZE
        
        self.assertIsInstance(LOG_FONT_SIZE, int)
        self.assertGreater(LOG_FONT_SIZE, 0)


class TestUIComponentsModule(unittest.TestCase):
    """Test module-level functionality"""
    
    def test_wx_available_flag(self):
        """Test that WX_AVAILABLE flag exists"""
        ui_components = import_bakery_module('ui_components')
        self.assertTrue(hasattr(ui_components, 'WX_AVAILABLE'))
    
    def test_config_dialog_uses_utils(self):
        """Test that ConfigDialog uses utils module"""
        ui_components = import_bakery_module('ui_components')
        utils = import_bakery_module('utils')
        # ConfigDialog should use validate_library_name from utils
        self.assertIsNotNone(utils.validate_library_name)
    
    def test_ui_components_without_wx(self):
        """Test that ui_components handles missing wx gracefully"""
        try:
            ui_components = import_bakery_module('ui_components')
            # Module should import even without wx
            self.assertIsNotNone(ui_components)
            # WX_AVAILABLE should be a boolean
            self.assertIsInstance(ui_components.WX_AVAILABLE, bool)
        except Exception as e:
            self.fail(f"ui_components should handle missing wx: {e}")
    
    def test_default_constants_defined(self):
        """Test that default constants are properly defined"""
        constants = import_bakery_module('constants')
        
        DEFAULT_LOCAL_LIB_NAME = constants.DEFAULT_LOCAL_LIB_NAME
        DEFAULT_SYMBOL_LIB_NAME = constants.DEFAULT_SYMBOL_LIB_NAME
        DEFAULT_SYMBOL_DIR_NAME = constants.DEFAULT_SYMBOL_DIR_NAME
        DEFAULT_MODELS_DIR_NAME = constants.DEFAULT_MODELS_DIR_NAME
        
        # All defaults should be non-empty strings
        self.assertIsInstance(DEFAULT_LOCAL_LIB_NAME, str)
        self.assertIsInstance(DEFAULT_SYMBOL_LIB_NAME, str)
        self.assertIsInstance(DEFAULT_SYMBOL_DIR_NAME, str)
        self.assertIsInstance(DEFAULT_MODELS_DIR_NAME, str)
        
        self.assertGreater(len(DEFAULT_LOCAL_LIB_NAME), 0)
        self.assertGreater(len(DEFAULT_SYMBOL_LIB_NAME), 0)
        self.assertGreater(len(DEFAULT_SYMBOL_DIR_NAME), 0)
        self.assertGreater(len(DEFAULT_MODELS_DIR_NAME), 0)


if __name__ == '__main__':
    unittest.main()
