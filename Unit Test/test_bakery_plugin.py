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


class FakeActionPlugin:
    """Minimal pcbnew ActionPlugin test double"""

    def __init__(self, *args, **kwargs):
        pass


class FakeDialog:
    """Minimal wx dialog test double"""

    def __init__(self, *args, **kwargs):
        pass

    def ShowModal(self, *args, **kwargs):
        return 1

    def Destroy(self, *args, **kwargs):
        pass

    def EndModal(self, *args, **kwargs):
        return None


class FakeFrame(FakeDialog):
    """Minimal wx frame test double"""


def load_bakery_plugin_module():
    """Import bakery_plugin with lightweight KiCad and wx test doubles"""
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
        OK=0,
        YES=1,
        NO=2,
        YES_NO=0,
        GetApp=lambda: types.SimpleNamespace(Yield=lambda: None),
        BoxSizer=lambda *args, **kwargs: types.SimpleNamespace(
            Add=lambda *a, **k: None
        ),
        VERTICAL=0,
        HORIZONTAL=1,
        ALL=0,
        EXPAND=0,
        LEFT=0,
        RIGHT=0,
        BOTTOM=0,
        ALIGN_CENTER=0,
        StaticText=lambda *args, **kwargs: types.SimpleNamespace(
            GetFont=lambda: types.SimpleNamespace(
                SetStyle=lambda *a, **k: None,
                SetFont=lambda *a, **k: None
            )
        ),
        TextCtrl=lambda *args, **kwargs: types.SimpleNamespace(
            GetValue=lambda: '',
            SetValue=lambda *a, **k: None
        ),
        Button=lambda *args, **kwargs: types.SimpleNamespace(
            Bind=lambda *a, **k: None,
            Enable=lambda *a, **k: None
        ),
        EVT_BUTTON=None,
        FONTSTYLE_ITALIC=0,
        SetSizer=lambda *a, **k: None,
        Centre=lambda *a, **k: None,
        CheckBox=lambda *args, **kwargs: types.SimpleNamespace(
            SetValue=lambda *a, **k: None,
            GetValue=lambda: False
        ),
    )
    with patch.dict(
        sys.modules,
        {
            'pcbnew': types.SimpleNamespace(ActionPlugin=FakeActionPlugin),
            'wx': wx_stub
        }
    ):
        return import_bakery_module('bakery_plugin')


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

    def test_plugin_config_omits_backups(self):
        """Test that the removed backup option is absent from plugin config."""
        plugin = load_bakery_plugin_module().BakeryPlugin()
        self.assertNotIn('create_backups', plugin.config)

    def test_footprint_table_failure_stops_reference_updates(self):
        """Reference rewrites do not run after fp-lib-table failure"""
        plugin = load_bakery_plugin_module().BakeryPlugin()
        plugin.logger = MagicMock()
        footprint_localizer = MagicMock()
        footprint_localizer.scan_pcb_footprints.return_value = {
            ("Source", "Part")
        }
        footprint_localizer.scan_schematic_footprints.return_value = set()
        footprint_localizer.copy_footprints.return_value = [
            (
                "Source",
                "Part",
                "Source__Part",
                "source.kicad_mod",
                "dest.kicad_mod"
            )
        ]
        library_manager = MagicMock()
        library_manager.update_fp_lib_table.return_value = False

        with self.assertRaises(RuntimeError):
            plugin._localize_footprints(
                MagicMock(),
                "project.kicad_pcb",
                "project",
                footprint_localizer,
                library_manager
            )

        footprint_localizer.update_pcb_references.assert_not_called()
        footprint_localizer.update_schematic_references.assert_not_called()

    def test_backup_failure_stops_localization_before_scanning(self):
        """A failed initial project backup prevents project modification."""
        plugin_module = load_bakery_plugin_module()
        plugin = plugin_module.BakeryPlugin()
        plugin.logger = MagicMock()
        backup_manager_instance = MagicMock()
        backup_manager_instance.create_project_backup.side_effect = OSError(
            "backup failed"
        )
        footprint_localizer = MagicMock()

        with patch.object(
            plugin_module,
            'BackupManager',
            return_value=backup_manager_instance
        ), patch.object(
            plugin_module,
            'FootprintLocalizer',
            return_value=footprint_localizer
        ):
            with self.assertRaises(OSError):
                plugin.run_localization(
                    MagicMock(),
                    os.path.join("project", "Design.kicad_pcb"),
                    "project"
                )

        backup_manager_instance.create_project_backup.assert_called_once_with(
            "project",
            "Design"
        )
        footprint_localizer.scan_pcb_footprints.assert_not_called()

    def test_symbol_table_failure_stops_reference_updates(self):
        """Reference rewrites do not run after sym-lib-table failure"""
        plugin = load_bakery_plugin_module().BakeryPlugin()
        plugin.logger = MagicMock()
        symbol_localizer = MagicMock()
        symbol_localizer.scan_schematic_symbols.return_value = {
            ("Source", "Part")
        }
        symbol_localizer.copy_symbols.return_value = [
            ("Source", "Part", "Source__Part", ["symbol"])
        ]
        symbol_localizer.update_sym_lib_table.return_value = False

        with self.assertRaises(RuntimeError):
            plugin._localize_symbols("project", symbol_localizer)

        symbol_localizer.update_schematic_references.assert_not_called()

    def test_datasheet_localization_uses_recursive_schematic_list(self):
        """Hierarchical schematic files are passed to datasheet localization"""
        plugin_module = load_bakery_plugin_module()
        plugin = plugin_module.BakeryPlugin()
        plugin.logger = MagicMock()
        nested_sheet = os.path.join(
            "project",
            "sheets",
            "child.kicad_sch"
        )
        datasheet_localizer = MagicMock()
        datasheet_localizer.localize_all_datasheets.return_value = (1, 1)

        with patch.object(
            plugin_module,
            'find_schematic_files',
            return_value=[nested_sheet]
        ), patch.object(
            plugin_module,
            'DataSheetLocalizer',
            return_value=datasheet_localizer
        ):
            board = MagicMock()
            plugin._localize_datasheets("project", board)

        datasheet_localizer.localize_all_datasheets.assert_called_once_with(
            [],
            [nested_sheet],
            board=board
        )

    def test_datasheet_localization_runs_for_board_only_project(self):
        """PCB footprint datasheets are scanned without schematic files."""
        plugin_module = load_bakery_plugin_module()
        plugin = plugin_module.BakeryPlugin()
        plugin.logger = MagicMock()
        board = MagicMock()
        datasheet_localizer = MagicMock()
        datasheet_localizer.localize_all_datasheets.return_value = (1, 1)

        with patch.object(
            plugin_module,
            'find_schematic_files',
            return_value=[]
        ), patch.object(
            plugin_module,
            'DataSheetLocalizer',
            return_value=datasheet_localizer
        ):
            plugin._localize_datasheets("project", board)

        datasheet_localizer.localize_all_datasheets.assert_called_once_with(
            [],
            [],
            board=board
        )

    def test_live_board_datasheets_are_updated_before_save(self):
        """Datasheet fields are changed in memory before the final PCB save."""
        plugin_module = load_bakery_plugin_module()
        plugin = plugin_module.BakeryPlugin()
        plugin.logger = MagicMock()
        plugin.config = {
            'local_lib_name': 'LocalFootprints',
            'symbol_lib_name': 'LocalSymbols',
            'models_dir_name': '3D_Models',
            'datasheets_dir_name': 'Data_Sheets'
        }
        events = []
        board = MagicMock()
        board.Save.side_effect = lambda _path: events.append("save")

        plugin._schematics_are_available = MagicMock(return_value=True)
        plugin._localize_footprints = MagicMock(return_value=[])
        plugin._localize_symbols = MagicMock(return_value=[])
        plugin._localize_datasheets = MagicMock(
            side_effect=lambda _project_dir, _board: events.append(
                "datasheets"
            ) or 0
        )
        plugin._complete_localization = MagicMock()
        footprint_localizer = MagicMock()

        with patch.object(
            plugin_module,
            'BackupManager'
        ), patch.object(
            plugin_module,
            'FootprintLocalizer',
            return_value=footprint_localizer
        ), patch.object(
            plugin_module,
            'SymbolLocalizer'
        ), patch.object(
            plugin_module,
            'LibraryManager'
        ):
            plugin.run_localization(
                board,
                os.path.join("project", "Design.kicad_pcb"),
                "project"
            )

        self.assertEqual(events, ["datasheets", "save"])

    def test_completion_counts_only_newly_copied_assets(self):
        """Completion counts exclude reused symbols and local footprints"""
        plugin = load_bakery_plugin_module().BakeryPlugin()
        plugin.logger = MagicMock()
        copied_footprints = [
            ("Source", "A", "target-a", "source-a", "dest-a"),
            ("Local", "B", "B", "same-b", "same-b")
        ]
        copied_symbols = [
            ("Source", "A", "target-a", ["symbol"]),
            ("Source", "B", "target-b", None)
        ]

        plugin._complete_localization(
            copied_footprints,
            copied_symbols,
            0
        )

        info_messages = [
            call.args[0]
            for call in plugin.logger.info.call_args_list
        ]
        self.assertTrue(
            any(
                "Copied 1 footprints and 1 symbols" in message
                for message in info_messages
            )
        )


if __name__ == '__main__':
    unittest.main()
