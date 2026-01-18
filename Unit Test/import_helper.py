"""
Import helper for unit tests

This module provides a helper to import Bakery modules that use relative imports.
It temporarily modifies sys.modules to make relative imports work.
"""

import sys
import os
import importlib.util
from types import ModuleType


class BakeryImporter:
    """Helper class to import Bakery modules for testing"""
    
    def __init__(self):
        self.bakery_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.modules = {}
        self._setup_package()
    
    def _setup_package(self):
        """Set up Bakery as a package in sys.modules"""
        if 'Bakery' not in sys.modules:
            # Create a fake package
            bakery_package = ModuleType('Bakery')
            bakery_package.__path__ = [self.bakery_dir]
            bakery_package.__file__ = os.path.join(self.bakery_dir, '__init__.py')
            sys.modules['Bakery'] = bakery_package
    
    def import_module(self, module_name):
        """
        Import a Bakery module by name
        
        Args:
            module_name: Name of the module (e.g., 'constants', 'utils')
        
        Returns:
            The imported module
        """
        if module_name in self.modules:
            return self.modules[module_name]
        
        # Import as Bakery.module_name
        full_name = f'Bakery.{module_name}'
        
        if full_name in sys.modules:
            self.modules[module_name] = sys.modules[full_name]
            return sys.modules[full_name]
        
        # Load the module
        module_path = os.path.join(self.bakery_dir, f'{module_name}.py')
        
        if not os.path.exists(module_path):
            raise ImportError(f"Module {module_name} not found at {module_path}")
        
        spec = importlib.util.spec_from_file_location(full_name, module_path)
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules before executing to handle circular imports
        sys.modules[full_name] = module
        
        # Execute the module
        spec.loader.exec_module(module)
        
        # Cache it
        self.modules[module_name] = module
        
        return module


# Create a global importer instance
_importer = BakeryImporter()


def import_bakery_module(module_name):
    """
    Import a Bakery module for testing
    
    Usage:
        constants = import_bakery_module('constants')
        utils = import_bakery_module('utils')
    """
    return _importer.import_module(module_name)
