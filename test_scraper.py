#!/usr/bin/env python3
"""
Test script for eCFR Scraper
Validates the complete functionality of the scraper
"""

import sys
import subprocess
import time
from pathlib import Path

def run_command(command, description):
    """Run a command and display results"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode != 0:
        print(f"❌ Command failed with return code {result.returncode}")
        return False
    else:
        print("✅ Command executed successfully")
        return True

def main():
    """Main test function"""
    print("eCFR Scraper - Comprehensive Test Suite")
    print("=" * 60)
    
    # Activate virtual environment prefix
    venv_prefix = "source venv/bin/activate && "
    
    tests = [
        (f"{venv_prefix}python -m src.main --help", "CLI Help Command"),
        (f"{venv_prefix}python -m src.main init-db --force", "Database Initialization"),
        (f"{venv_prefix}python -m src.main scrape --titles 1", "Scrape CFR Title 1"),
        (f"{venv_prefix}python -m src.main stats", "Database Statistics"),
        (f"{venv_prefix}python -m src.main list-titles", "List All Titles"),
        (f"{venv_prefix}python -m src.main list-titles --title 1", "Show Title 1 Details"),
        (f"{venv_prefix}python -m src.main search 'definitions' --limit 3", "Search Functionality"),
        (f"{venv_prefix}python -m src.main search 'privacy' --format json --limit 2", "JSON Search Output"),
        (f"{venv_prefix}python -m src.main check-updates --titles 1", "Check for Updates"),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for command, description in tests:
        if run_command(command, description):
            passed_tests += 1
        time.sleep(1)  # Brief pause between tests
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed_tests}/{total_tests} tests passed")
    print(f"{'='*60}")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The eCFR scraper is working correctly.")
        return 0
    else:
        print(f"❌ {total_tests - passed_tests} test(s) failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())