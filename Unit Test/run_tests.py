"""
Test runner for Bakery KiCad Plugin Unit Tests

This script discovers and runs all unit tests in the Unit Test directory.
It can be run from the command line or integrated into CI/CD pipelines.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Run with verbose output
    python run_tests.py --coverage   # Run with coverage report (requires coverage.py)
"""

import sys
import os
import unittest
import argparse

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_tests(verbosity=2, pattern='test_*.py', coverage=False):
    """
    Run all unit tests
    
    Args:
        verbosity (int): Verbosity level (0=quiet, 1=normal, 2=verbose)
        pattern (str): Pattern for test file discovery
        coverage (bool): Whether to run with coverage reporting
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Discover tests in current directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    if coverage:
        try:
            import coverage as cov
            # Start coverage
            coverage_obj = cov.Coverage(source=[os.path.dirname(test_dir)])
            coverage_obj.start()
            print("Running tests with coverage...\n")
        except ImportError:
            print("Warning: coverage.py not installed. Run without coverage.")
            print("Install with: pip install coverage\n")
            coverage = False
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern=pattern)
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Show coverage report if requested
    if coverage:
        coverage_obj.stop()
        coverage_obj.save()
        
        print("\n" + "=" * 70)
        print("Coverage Report")
        print("=" * 70)
        coverage_obj.report()
        
        # Generate HTML report
        html_dir = os.path.join(test_dir, 'htmlcov')
        coverage_obj.html_report(directory=html_dir)
        print(f"\nHTML coverage report generated in: {html_dir}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    success = result.wasSuccessful()
    if success:
        print("\n[PASS] All tests passed!")
    else:
        print("\n[FAIL] Some tests failed.")
    
    return success


def list_tests(pattern='test_*.py'):
    """
    List all available test files
    
    Args:
        pattern (str): Pattern for test file discovery
    """
    test_dir = os.path.dirname(os.path.abspath(__file__))
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern=pattern)
    
    print("Available test modules:")
    print("=" * 70)
    
    test_files = set()
    for test_group in suite:
        for test_case in test_group:
            if hasattr(test_case, '__iter__'):
                for test in test_case:
                    module = test.__class__.__module__
                    test_files.add(module)
    
    for test_file in sorted(test_files):
        print(f"  - {test_file}")
    
    print(f"\nTotal: {len(test_files)} test modules")


def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(
        description='Run unit tests for Bakery KiCad Plugin'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet output'
    )
    
    parser.add_argument(
        '-c', '--coverage',
        action='store_true',
        help='Run with coverage report (requires coverage.py)'
    )
    
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List all available tests'
    )
    
    parser.add_argument(
        '-p', '--pattern',
        default='test_*.py',
        help='Pattern for test discovery (default: test_*.py)'
    )
    
    args = parser.parse_args()
    
    # Determine verbosity
    if args.quiet:
        verbosity = 0
    elif args.verbose:
        verbosity = 2
    else:
        verbosity = 1
    
    # List tests if requested
    if args.list:
        list_tests(args.pattern)
        return 0
    
    # Run tests
    print("Bakery KiCad Plugin - Unit Test Runner")
    print("=" * 70)
    print()
    
    success = run_tests(
        verbosity=verbosity,
        pattern=args.pattern,
        coverage=args.coverage
    )
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
