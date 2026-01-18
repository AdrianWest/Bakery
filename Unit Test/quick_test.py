"""
Quick test runner - Run a single test to verify setup

Usage:
    python quick_test.py
"""

import sys
import os

# Import helper for Bakery modules
from import_helper import import_bakery_module

# Test imports
print("Testing imports...")
print("-" * 70)

try:
    print("✓ Importing constants...")
    constants = import_bakery_module('constants')
    print(f"  Plugin Version: {constants.PLUGIN_VERSION}")
    
    print("✓ Importing utils...")
    utils = import_bakery_module('utils')
    
    print("✓ Importing sexpr_parser...")
    sexpr_parser = import_bakery_module('sexpr_parser')
    
    print("\nAll core imports successful!")
    print("-" * 70)
    
    # Run a simple test
    print("\nRunning simple validation test...")
    result = utils.validate_library_name("TestLib")
    assert result == True, "validate_library_name failed"
    print("✓ validate_library_name('TestLib') = True")
    
    result = utils.validate_library_name("../BadLib")
    assert result == False, "validate_library_name should reject path separators"
    print("✓ validate_library_name('../BadLib') = False")
    
    print("\n" + "=" * 70)
    print("SUCCESS: Basic functionality verified!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
