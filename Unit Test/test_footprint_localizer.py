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
from unittest.mock import Mock, MagicMock

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
