# Bakery KiCad Plugin - Unit Testing Guide

## Overview

This directory contains a comprehensive unit test suite for the Bakery KiCad Plugin. The tests are designed to verify all functionality without requiring KiCad to be installed, using mocks where necessary.

## Quick Start

### Run All Tests

```powershell
cd "Unit Test"
python run_tests.py
```

### Run Quick Validation

```powershell
cd "Unit Test"
python quick_test.py
```

This runs a quick smoke test to verify the test environment is set up correctly.

## Test Files

| File | Description | Coverage |
|------|-------------|----------|
| `test_constants.py` | Constants and configuration | Plugin metadata, UI constants, file extensions |
| `test_utils.py` | Utility functions | Path validation, file operations, library name validation |
| `test_sexpr_parser.py` | S-expression parser | Parsing, serialization, caching |
| `test_backup_manager.py` | File backup system | Backup creation, tracking, timestamping |
| `test_library_manager.py` | Library management | Library creation, path expansion, fp-lib-table updates |
| `test_base_localizer.py` | Base localizer class | Common functionality, file locking, schematic scanning |
| `test_footprint_localizer.py` | Footprint localization | PCB scanning, footprint copying, 3D model localization |
| `test_symbol_localizer.py` | Symbol localization | Symbol scanning, library extraction, reference updates |
| `test_data_sheet_localizer.py` | Datasheet localization | URL/path detection, PDF validation, scan, copy/download, reference updates, full workflow |
| `test_ui_components.py` | UI components | Config dialog, logger window |
| `test_bakery_plugin.py` | Main plugin | Plugin coordination, workflow |

## Test Structure

Each test file follows a consistent structure:

```python
# 1. Import the import helper
from import_helper import import_bakery_module

# 2. Import the module to test
module_name = import_bakery_module('module_name')

# 3. Define test classes
class TestModuleName(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        
    def tearDown(self):
        """Clean up after tests"""
        
    def test_feature(self):
        """Test a specific feature"""
```

## Import Helper

Due to the KiCad plugin structure using relative imports (`from .constants import ...`), we provide an import helper:

```python
from import_helper import import_bakery_module

# Import modules
constants = import_bakery_module('constants')
utils = import_bakery_module('utils')
```

The import helper creates a temporary `Bakery` package in `sys.modules` to make relative imports work during testing.

## Running Tests

### All Tests

```powershell
python run_tests.py
```

### Verbose Output

```powershell
python run_tests.py -v
```

### Quiet Output

```powershell
python run_tests.py -q
```

### With Coverage

```powershell
# Install coverage first
pip install coverage

# Run with coverage
python run_tests.py --coverage
```

This generates an HTML coverage report in `htmlcov/`.

### Specific Test Module

```powershell
python -m unittest test_constants
```

### Specific Test Class

```powershell
python -m unittest test_constants.TestConstants
```

### Specific Test Method

```powershell
python -m unittest test_constants.TestConstants.test_plugin_version_format
```

### List Available Tests

```powershell
python run_tests.py --list
```

## Test Utilities

### MockLogger

Most tests use a `MockLogger` class to capture log messages:

```python
class MockLogger:
    def __init__(self):
        self.messages = {
            'info': [],
            'warning': [],
            'error': [],
            'success': []
        }
    
    def info(self, msg):
        self.messages['info'].append(msg)
```

Usage in tests:

```python
def test_logging(self):
    logger = MockLogger()
    manager = SomeManager(logger)
    manager.do_something()
    
    # Verify logging occurred
    self.assertIn('expected message', logger.messages['info'])
```

### Temporary Directories

Tests use `tempfile.mkdtemp()` for isolated file operations:

```python
def setUp(self):
    self.temp_dir = tempfile.mkdtemp()
    
def tearDown(self):
    shutil.rmtree(self.temp_dir)
```

### Mock Objects

For KiCad-specific objects (pcbnew, wx):

```python
from unittest.mock import Mock, patch

@patch('module.pcbnew')
def test_with_mock_pcbnew(self, mock_pcbnew):
    # Test code here
    pass
```

## Test Categories

### Unit Tests
Test individual functions and methods in isolation.

### Integration Tests
Test how components work together (e.g., `BaseLocalizer` integration).

### Mock Tests
Test components that depend on KiCad APIs using mocks.

## Continuous Integration

### GitHub Actions Example

```yaml
name: Unit Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Run Tests
        run: python "Unit Test/run_tests.py" --coverage
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
```

## Coverage Goals

- **Line Coverage**: >80%
- **Branch Coverage**: >70%
- **Function Coverage**: >90%

Current coverage can be viewed by running:

```powershell
python run_tests.py --coverage
```

## Writing New Tests

### Checklist

- [ ] Import using `import_helper`
- [ ] Create test class inheriting from `unittest.TestCase`
- [ ] Implement `setUp()` and `tearDown()` if needed
- [ ] Write descriptive docstrings for each test
- [ ] Test both success and failure cases
- [ ] Test edge cases and boundary conditions
- [ ] Use meaningful assertion messages
- [ ] Clean up temporary files/resources

### Example

```python
from import_helper import import_bakery_module
import unittest
import tempfile
import shutil

module_name = import_bakery_module('module_name')

class TestNewFeature(unittest.TestCase):
    """Test suite for new feature"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
    
    def test_feature_success(self):
        """Test that feature works in success case"""
        result = module_name.new_function()
        self.assertEqual(result, expected_value)
    
    def test_feature_failure(self):
        """Test that feature handles errors correctly"""
        with self.assertRaises(ValueError):
            module_name.new_function(invalid_input)
    
    def test_feature_edge_case(self):
        """Test edge case handling"""
        result = module_name.new_function(edge_case_input)
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()
```

## Troubleshooting

### Import Errors

**Problem**: `ImportError: attempted relative import with no known parent package`

**Solution**: Use the import helper:
```python
from import_helper import import_bakery_module
module = import_bakery_module('module_name')
```

### Missing Dependencies

**Problem**: `ImportError: No module named 'wx'` or `'pcbnew'`

**Solution**: These are expected outside KiCad. Tests use mocks for these dependencies.

### File Permission Errors

**Problem**: Tests fail due to file access issues

**Solution**: Ensure `tearDown()` properly cleans up files and that no processes are holding locks.

### Platform-Specific Failures

**Problem**: Tests pass on one platform but fail on another

**Solution**: Use platform-independent paths (`os.path.join`) and handle platform-specific behavior (e.g., file locking on Windows vs Unix).

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Always clean up resources in `tearDown()`
3. **Descriptive Names**: Use clear, descriptive test method names
4. **One Assert Per Test**: Focus each test on one specific behavior
5. **Documentation**: Add docstrings explaining what each test verifies
6. **Mock External Dependencies**: Use mocks for pcbnew, wx, file system when appropriate
7. **Test Edge Cases**: Don't just test the happy path

## Resources

- [Python unittest documentation](https://docs.python.org/3/library/unittest.html)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py documentation](https://coverage.readthedocs.io/)

## Contributing

When adding new functionality:

1. Write tests first (TDD approach recommended)
2. Ensure all existing tests still pass
3. Add tests for new features
4. Update this documentation if needed
5. Aim for >80% code coverage

## License

These tests are part of the Bakery KiCad Plugin and are licensed under the GNU General Public License v3.0.

Copyright (C) 2026 Adrian West
