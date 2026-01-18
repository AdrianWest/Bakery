"""
Unit tests for bakery_plugin module

Tests the main BakeryPlugin ActionPlugin class.
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch

# Use import helper for modules with relative imports
from import_helper import import_bakery_module


class TestPluginConstants(unittest.TestCase):
    """Test suite for plugin metadata constants"""
    
    def test_plugin_metadata_defined(self):
        """Test that plugin metadata constants are defined"""
        constants = import_bakery_module('constants')
        
        PLUGIN_NAME = constants.PLUGIN_NAME
        PLUGIN_CATEGORY = constants.PLUGIN_CATEGORY
        PLUGIN_DESCRIPTION = constants.PLUGIN_DESCRIPTION
        PLUGIN_VERSION = constants.PLUGIN_VERSION
        
        self.assertIsInstance(PLUGIN_NAME, str)
        self.assertIsInstance(PLUGIN_CATEGORY, str)
        self.assertIsInstance(PLUGIN_DESCRIPTION, str)
        self.assertIsInstance(PLUGIN_VERSION, str)
        
        self.assertGreater(len(PLUGIN_NAME), 0)
        self.assertGreater(len(PLUGIN_CATEGORY), 0)
        self.assertGreater(len(PLUGIN_DESCRIPTION), 0)
        self.assertGreater(len(PLUGIN_VERSION), 0)
    
    def test_plugin_version_format(self):
        """Test that plugin version follows semantic versioning"""
        constants = import_bakery_module('constants')
        PLUGIN_VERSION = constants.PLUGIN_VERSION
        import re
        
        version_pattern = r'^\d+\.\d+\.\d+$'
        self.assertRegex(PLUGIN_VERSION, version_pattern)
    
    def test_progress_constants_defined(self):
        """Test that progress step constants are defined"""
        constants = import_bakery_module('constants')
        
        PROGRESS_STEP_SCAN_PCB = constants.PROGRESS_STEP_SCAN_PCB
        PROGRESS_STEP_SCAN_SCHEMATICS = constants.PROGRESS_STEP_SCAN_SCHEMATICS
        PROGRESS_STEP_COPY_FOOTPRINTS = constants.PROGRESS_STEP_COPY_FOOTPRINTS
        PROGRESS_STEP_UPDATE_PCB = constants.PROGRESS_STEP_UPDATE_PCB
        
        # All should be strings
        self.assertIsInstance(PROGRESS_STEP_SCAN_PCB, str)
        self.assertIsInstance(PROGRESS_STEP_SCAN_SCHEMATICS, str)
        self.assertIsInstance(PROGRESS_STEP_COPY_FOOTPRINTS, str)
        self.assertIsInstance(PROGRESS_STEP_UPDATE_PCB, str)
    
    def test_error_message_constants(self):
        """Test that error message constants are defined"""
        constants = import_bakery_module('constants')
        
        ERROR_NO_BOARD = constants.ERROR_NO_BOARD
        ERROR_PROJECT_NOT_SAVED = constants.ERROR_PROJECT_NOT_SAVED
        
        self.assertIsInstance(ERROR_NO_BOARD, str)
        self.assertIsInstance(ERROR_PROJECT_NOT_SAVED, str)
        self.assertGreater(len(ERROR_NO_BOARD), 0)
        self.assertGreater(len(ERROR_PROJECT_NOT_SAVED), 0)


class TestBakeryPlugin(unittest.TestCase):
    """Test suite for BakeryPlugin class"""
    
    def test_localizers_import(self):
        """Test that localizer modules can be imported"""
        footprint_localizer = import_bakery_module('footprint_localizer')
        symbol_localizer = import_bakery_module('symbol_localizer')
        
        self.assertIsNotNone(footprint_localizer)
        self.assertIsNotNone(symbol_localizer)
    
    def test_library_manager_import(self):
        """Test that library_manager can be imported"""
        library_manager = import_bakery_module('library_manager')
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'LibraryManager'))


if __name__ == '__main__':
    unittest.main()
