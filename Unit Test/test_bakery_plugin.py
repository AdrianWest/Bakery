"""
Unit tests for bakery_plugin module

Tests the main BakeryPlugin ActionPlugin class.
"""

import sys
import os
import types
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

    def test_plugin_defaults_disable_backups(self):
        """Test that backup creation is off by default for the plugin config."""
        constants = import_bakery_module('constants')

        class FakeActionPlugin:
            def __init__(self, *args, **kwargs):
                pass

        class FakeDialog:
            def __init__(self, *args, **kwargs):
                pass

            def ShowModal(self, *args, **kwargs):
                return 1

            def Destroy(self, *args, **kwargs):
                pass

            def EndModal(self, *args, **kwargs):
                return None

        class FakeFrame(FakeDialog):
            pass

        wx_stub = types.SimpleNamespace(
            Dialog=FakeDialog,
            Frame=FakeFrame,
            MessageBox=lambda *args, **kwargs: None,
            ID_OK=1,
            ID_CANCEL=2,
            ICON_WARNING=0,
            ICON_ERROR=0,
            ICON_QUESTION=0,
            ICON_INFORMATION=0,
            YES=1,
            NO=2,
            GetApp=lambda: types.SimpleNamespace(Yield=lambda: None),
            BoxSizer=lambda *args, **kwargs: types.SimpleNamespace(Add=lambda *a, **k: None),
            VERTICAL=0,
            HORIZONTAL=1,
            ALL=0,
            EXPAND=0,
            LEFT=0,
            RIGHT=0,
            BOTTOM=0,
            ALIGN_CENTER=0,
            StaticText=lambda *args, **kwargs: types.SimpleNamespace(GetFont=lambda: types.SimpleNamespace(SetStyle=lambda *a, **k: None, SetFont=lambda *a, **k: None)),
            TextCtrl=lambda *args, **kwargs: types.SimpleNamespace(GetValue=lambda: '', SetValue=lambda *a, **k: None),
            Button=lambda *args, **kwargs: types.SimpleNamespace(Bind=lambda *a, **k: None),
            EVT_BUTTON=None,
            FONTSTYLE_ITALIC=0,
            SetSizer=lambda *a, **k: None,
            Centre=lambda *a, **k: None,
            CheckBox=lambda *args, **kwargs: types.SimpleNamespace(SetValue=lambda *a, **k: None, GetValue=lambda: False),
        )

        cgi_stub = MagicMock()
        cgi_stub.parse_header.return_value = ('', {})
        with patch.dict(sys.modules, {'pcbnew': types.SimpleNamespace(ActionPlugin=FakeActionPlugin), 'wx': wx_stub, 'cgi': cgi_stub}):
            sys.modules.pop('Bakery.bakery_plugin', None)
            plugin_module = import_bakery_module('bakery_plugin')
            plugin = plugin_module.BakeryPlugin()
            self.assertFalse(plugin.config[constants.CONFIG_CREATE_BACKUPS])


if __name__ == '__main__':
    unittest.main()
