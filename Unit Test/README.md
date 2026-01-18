# Bakery KiCad Plugin - Unit Tests

This directory contains comprehensive unit tests for all modules in the Bakery KiCad plugin.

## Test Coverage

The test suite includes tests for the following modules:

- **test_constants.py** - Tests for constants and configuration values
- **test_utils.py** - Tests for utility functions (path validation, file operations)
- **test_sexpr_parser.py** - Tests for S-expression parsing and serialization
- **test_backup_manager.py** - Tests for file backup functionality
- **test_library_manager.py** - Tests for library creation and management
- **test_base_localizer.py** - Tests for base localizer functionality
- **test_footprint_localizer.py** - Tests for footprint localization
- **test_symbol_localizer.py** - Tests for symbol localization
- **test_ui_components.py** - Tests for UI dialogs and logger
- **test_bakery_plugin.py** - Tests for main plugin entry point

## Running the Tests

### Run All Tests

```powershell
# From the Unit Test directory
python run_tests.py

# Or from the project root
python "Unit Test\run_tests.py"
```

### Run with Verbose Output

```powershell
python run_tests.py -v
```

### Run with Coverage Report

```powershell
# Requires: pip install coverage
python run_tests.py --coverage
```

### Run Specific Test File

```powershell
# Run a single test module
python -m unittest test_constants

# Run a specific test class
python -m unittest test_constants.TestConstants

# Run a specific test method
python -m unittest test_constants.TestConstants.test_plugin_version_format
```

### List All Available Tests

```powershell
python run_tests.py --list
```

## Test Structure

Each test file follows this structure:

```python
import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module_name import ClassName

class TestClassName(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        pass
    
    def tearDown(self):
        """Clean up after tests"""
        pass
    
    def test_feature(self):
        """Test a specific feature"""
        self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()
```

## Mock Objects

Since many modules depend on KiCad's `pcbnew` and `wx` libraries which are only available within KiCad, the tests use mocking where necessary:

- **pcbnew** - Mocked for testing PCB-related functionality
- **wx** - Mocked for testing UI components
- **board/footprint objects** - Mocked for testing localization logic

## Test Data

Tests create temporary directories and files as needed using Python's `tempfile` module. All temporary data is cleaned up in the `tearDown()` method.

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Unit Tests
  run: python "Unit Test/run_tests.py" --coverage

- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

## Coverage Goals

The test suite aims for:

- **Line Coverage**: >80%
- **Branch Coverage**: >70%
- **Function Coverage**: >90%

## Writing New Tests

When adding new functionality to Bakery:

1. Create corresponding test methods in the appropriate test file
2. Follow existing test naming conventions: `test_<feature_name>`
3. Include docstrings explaining what each test validates
4. Use `setUp()` and `tearDown()` for test isolation
5. Test both success cases and error/edge cases

## Test Utilities

Common test utilities are available in each test file:

- **MockLogger** - Mock logger for testing log messages
- **Temporary directories** - Using `tempfile.mkdtemp()`
- **Mock environment variables** - Saved and restored in setUp/tearDown

## Dependencies

The tests require:

- Python 3.7+
- Standard library modules (unittest, tempfile, shutil, etc.)
- Optional: `coverage` for coverage reports

## Troubleshooting

### Import Errors

If you encounter import errors, ensure you're running tests from the correct directory and that the parent directory is in the Python path.

### Missing Dependencies

Some tests may be skipped if dependencies (like wxPython) are not available. This is expected outside of the KiCad environment.

### Platform-Specific Tests

Some tests may behave differently on Windows vs. Linux/macOS (e.g., file locking). These tests are designed to handle platform differences gracefully.

## Contributing

When contributing tests:

1. Ensure all tests pass before submitting
2. Add tests for new features
3. Update tests when modifying existing features
4. Follow the existing test structure and naming conventions
5. Document complex test scenarios

## License

These tests are part of the Bakery KiCad Plugin and are licensed under the GNU General Public License v3.0.
