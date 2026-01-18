"""
Test configuration and setup utilities

This module helps configure the test environment to handle imports properly.
"""

import sys
import os


def setup_test_environment():
    """
    Set up the test environment for running unit tests.
    
    This function:
    1. Adds the parent directory to sys.path for imports
    2. Sets up the Bakery package to handle relative imports
    """
    # Get paths
    test_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(test_dir)
    
    # Add parent to path if not already there
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Try to make parent directory a package for relative imports
    init_file = os.path.join(parent_dir, '__init__.py')
    
    return parent_dir


# Auto-setup when imported
setup_test_environment()
