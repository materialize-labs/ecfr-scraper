#!/usr/bin/env python3
"""
Test runner for eCFR scraper
Provides different ways to run the test suite
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_unittest_suite():
    """Run tests using Python's unittest framework"""
    print("Running tests with unittest...")
    
    # Discover and run all tests
    result = subprocess.run([
        sys.executable, '-m', 'unittest', 'discover', 
        '-s', 'tests', '-p', 'test_*.py', '-v'
    ], cwd=Path(__file__).parent)
    
    return result.returncode


def run_pytest_suite(args=None):
    """Run tests using pytest"""
    print("Running tests with pytest...")
    
    cmd = [sys.executable, '-m', 'pytest']
    
    if args:
        cmd.extend(args)
    else:
        cmd.extend(['-v', 'tests/'])
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def run_specific_test_file(test_file, framework='unittest'):
    """Run a specific test file"""
    print(f"Running {test_file} with {framework}...")
    
    if framework == 'pytest':
        cmd = [sys.executable, '-m', 'pytest', '-v', f'tests/{test_file}']
    else:
        cmd = [sys.executable, '-m', 'unittest', f'tests.{test_file[:-3]}', '-v']
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='eCFR Scraper Test Runner')
    parser.add_argument(
        '--framework', 
        choices=['unittest', 'pytest'], 
        default='unittest',
        help='Test framework to use (default: unittest)'
    )
    parser.add_argument(
        '--file', 
        help='Run specific test file (e.g., test_database.py)'
    )
    parser.add_argument(
        '--unit-only', 
        action='store_true',
        help='Run only unit tests (pytest only)'
    )
    parser.add_argument(
        '--integration-only', 
        action='store_true',
        help='Run only integration tests (pytest only)'
    )
    parser.add_argument(
        '--fast', 
        action='store_true',
        help='Skip slow tests (pytest only)'
    )
    parser.add_argument(
        '--coverage', 
        action='store_true',
        help='Run with coverage report (pytest only)'
    )
    
    args = parser.parse_args()
    
    # Check if pytest is available for pytest-specific options
    if args.framework == 'pytest' or any([args.unit_only, args.integration_only, args.fast, args.coverage]):
        try:
            import pytest
        except ImportError:
            print("pytest not available. Install with: pip install pytest")
            print("Falling back to unittest...")
            args.framework = 'unittest'
    
    # Run specific test file
    if args.file:
        return run_specific_test_file(args.file, args.framework)
    
    # Run with unittest
    if args.framework == 'unittest':
        return run_unittest_suite()
    
    # Run with pytest
    pytest_args = ['-v', 'tests/']
    
    if args.unit_only:
        pytest_args.extend(['-m', 'unit'])
    elif args.integration_only:
        pytest_args.extend(['-m', 'integration'])
    
    if args.fast:
        pytest_args.extend(['-m', 'not slow'])
    
    if args.coverage:
        pytest_args.extend(['--cov=src', '--cov-report=html', '--cov-report=term-missing'])
    
    return run_pytest_suite(pytest_args)


if __name__ == '__main__':
    sys.exit(main())