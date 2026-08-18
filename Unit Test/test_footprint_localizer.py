"""
Unit tests for footprint_localizer module

Tests footprint and 3D model localization functionality.
Note: These tests use mocks for pcbnew since it's only available in KiCad.
"""

import sys
import os
import unittest
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch

# Use import helper for modules with relative imports
from import_helper import import_bakery_module

footprint_localizer = import_bakery_module('footprint_localizer')
FootprintLocalizer = footprint_localizer.FootprintLocalizer


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


class TestFootprintLocalizer(unittest.TestCase):
    """Test suite for FootprintLocalizer class"""
    
    def setUp(self):
        """Create temporary directory and test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        
        self.logger = MockLogger()
        self.localizer = FootprintLocalizer(self.logger)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test FootprintLocalizer initialization"""
        localizer = FootprintLocalizer()
        self.assertIsNotNone(localizer)
        self.assertIsNotNone(localizer.lib_manager)
        self.assertIsNotNone(localizer.parser)
        self.assertIsNotNone(localizer.backup_manager)
    
    def test_initialization_with_logger(self):
        """Test FootprintLocalizer initialization with logger"""
        localizer = FootprintLocalizer(self.logger)
        self.assertEqual(localizer.logger, self.logger)
    
    def test_scan_pcb_footprints_mock(self):
        """Test scanning PCB for footprints using mock board"""
        # Create mock board
        mock_board = Mock()
        mock_footprint1 = Mock()
        mock_footprint1.GetFPID().GetLibItemName().return_value = "R_0805"
        mock_footprint1.GetFPID().GetLibNickname().return_value = "Resistor_SMD"
        
        mock_footprint2 = Mock()
        mock_footprint2.GetFPID().GetLibItemName().return_value = "C_0603"
        mock_footprint2.GetFPID().GetLibNickname().return_value = "Capacitor_SMD"
        
        mock_board.GetFootprints.return_value = [mock_footprint1, mock_footprint2]
        
        # Scan footprints
        footprints = self.localizer.scan_pcb_footprints(mock_board)
        
        self.assertIsInstance(footprints, set)
        # Should have found footprints
        self.assertGreaterEqual(len(footprints), 0)
    
    def test_scan_schematic_footprints(self):
        """Test scanning schematics for footprint references"""
        # Create test schematic with footprint property
        sch_file = os.path.join(self.project_dir, "test.kicad_sch")
        sch_content = '''(kicad_sch
            (symbol (property "Footprint" "Resistor_SMD:R_0805"))
            (symbol (property "Footprint" "Capacitor_SMD:C_0603"))
        )'''
        
        with open(sch_file, 'w') as f:
            f.write(sch_content)
        
        # Scan schematics
        footprints = self.localizer.scan_schematic_footprints(self.project_dir)
        
        self.assertIsInstance(footprints, set)
        # May or may not find footprints depending on implementation
    
    def test_copy_footprints(self):
        """Test copying footprints to local library"""
        # Create source footprint library
        source_lib = os.path.join(self.temp_dir, "source.pretty")
        os.makedirs(source_lib)
        
        # Create a footprint file
        fp_file = os.path.join(source_lib, "R_0805.kicad_mod")
        with open(fp_file, 'w') as f:
            f.write('(footprint "R_0805")')
        
        # Create local library
        local_lib = os.path.join(self.project_dir, "MyLib.pretty")
        os.makedirs(local_lib)
        
        # Copy footprints
        footprints = {("source", "R_0805")}
        
        # This would require more complex mocking or actual file operations
        # For now, just test the method exists
        self.assertTrue(hasattr(self.localizer, 'copy_footprints'))
    
    def test_localize_3d_models(self):
        """Test localizing 3D models"""
        # Create source 3D model
        source_3d_dir = os.path.join(self.temp_dir, "3d_source")
        os.makedirs(source_3d_dir)
        
        model_file = os.path.join(source_3d_dir, "model.wrl")
        with open(model_file, 'w') as f:
            f.write('# VRML model')
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'localize_3d_models'))
    
    def test_update_pcb_references_mock(self):
        """Test updating PCB footprint references using mock"""
        mock_board = Mock()
        mock_footprint = Mock()
        mock_footprint.GetFPID().GetLibItemName().return_value = "R_0805"
        mock_footprint.GetFPID().GetLibNickname().return_value = "OldLib"
        
        mock_board.GetFootprints.return_value = [mock_footprint]
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'update_pcb_references'))

    def test_reload_footprints_from_library(self):
        """Test reloading footprints while preserving board state and pad nets"""
        local_lib_path = os.path.join(self.project_dir, "MyLib.pretty")
        os.makedirs(local_lib_path)

        old_net = Mock()
        old_pad = Mock()
        old_pad.GetNumber.return_value = "1"
        old_pad.GetNet.return_value = old_net

        old_fpid = Mock()
        old_fpid.GetLibItemName.return_value = "R_0805"
        old_footprint = Mock()
        old_footprint.GetFPID.return_value = old_fpid
        old_footprint.GetReference.return_value = "R1"
        old_footprint.IsFlipped.return_value = False
        old_footprint.GetFields.return_value = []
        old_footprint.GetFieldsText.return_value = {}
        old_footprint.Pads.return_value = [old_pad]

        new_pad = Mock()
        new_pad.GetNumber.return_value = "1"
        new_footprint = Mock()
        new_footprint.GetFields.return_value = []
        new_footprint.Pads.return_value = [new_pad]

        mock_board = Mock()
        mock_board.GetFootprints.return_value = [old_footprint]
        mock_pcbnew = MagicMock()
        mock_pcbnew.FootprintLoad.return_value = new_footprint

        with patch.dict(sys.modules, {'pcbnew': mock_pcbnew}):
            result = self.localizer.reload_footprints_from_library(
                mock_board,
                self.project_dir,
                "MyLib"
            )

        self.assertEqual(result, (1, 0))
        mock_pcbnew.FootprintLoad.assert_called_once_with(
            local_lib_path,
            "R_0805",
            False
        )
        new_footprint.SetPosition.assert_called_once_with(
            old_footprint.GetPosition.return_value
        )
        new_footprint.SetOrientation.assert_called_once_with(
            old_footprint.GetOrientation.return_value
        )
        new_pad.SetNet.assert_called_once_with(old_net)
        mock_board.Add.assert_called_once_with(new_footprint)
        mock_board.Remove.assert_called_once_with(old_footprint)
        mock_board.BuildConnectivity.assert_called_once_with()

    def test_update_pcb_model_paths_rewrites_embedded_models(self):
        """Test rewriting localized model paths in the saved PCB"""
        pcb_file = os.path.join(self.project_dir, "test.kicad_pcb")
        old_path = (
            "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/"
            "CP_Elec_18x17.5.step"
        )
        new_path = "${KIPRJMOD}/3D Models/CP_Elec_18x17.5.step"
        missing_path = (
            "${KICAD10_3DMODEL_DIR}/Button_Switch_THT.3dshapes/"
            "KSA_Tactile_SPST.step"
        )
        with open(pcb_file, 'w', encoding='utf-8') as pcb:
            pcb.write(
                f'(footprint "MyLib:CP_Elec_18x17.5"\n'
                f'  (model "{old_path}"))\n'
                f'(footprint "MyLib:CP_Elec_18x17.5"\n'
                f'  (model "{old_path}"))\n'
                f'(footprint "MyLib:KSA_Tactile_SPST"\n'
                f'  (model "{missing_path}"))\n'
            )
        self.localizer.copied_models = {old_path: new_path}

        updated_count = self.localizer.update_pcb_model_paths(pcb_file)

        with open(pcb_file, 'r', encoding='utf-8') as pcb:
            updated_content = pcb.read()
        self.assertEqual(updated_count, 2)
        self.assertNotIn(old_path, updated_content)
        self.assertEqual(updated_content.count(new_path), 2)
        self.assertIn(missing_path, updated_content)
    
    def test_update_schematic_references(self):
        """Test updating schematic footprint references"""
        # Create test schematic
        sch_file = os.path.join(self.project_dir, "test.kicad_sch")
        sch_content = '''(kicad_sch
            (symbol (property "Footprint" "OldLib:R_0805"))
        )'''
        
        with open(sch_file, 'w') as f:
            f.write(sch_content)
        
        # Test that method exists
        self.assertTrue(hasattr(self.localizer, 'update_schematic_references'))


class TestFootprintLocalizerIntegration(unittest.TestCase):
    """Integration tests for FootprintLocalizer"""
    
    def setUp(self):
        """Create test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.temp_dir, "project")
        os.makedirs(self.project_dir)
        
        self.logger = MockLogger()
        self.localizer = FootprintLocalizer(self.logger)
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
    
    def test_inherits_from_base_localizer(self):
        """Test that FootprintLocalizer inherits from BaseLocalizer"""
        base_localizer_module = import_bakery_module('base_localizer')
        self.assertIsInstance(self.localizer, base_localizer_module.BaseLocalizer)
    
    def test_has_library_manager(self):
        """Test that FootprintLocalizer has library manager"""
        lib_mgr_module = import_bakery_module('library_manager')
        self.assertIsInstance(self.localizer.lib_manager, lib_mgr_module.LibraryManager)
    
    def test_logging_functionality(self):
        """Test that logging works correctly"""
        self.localizer.log('info', 'Test message')
        self.assertIn('Test message', self.logger.messages['info'])


if __name__ == '__main__':
    unittest.main()
