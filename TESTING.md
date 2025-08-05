# eCFR Scraper - Testing Guide

This document provides comprehensive information about testing the eCFR scraper project.

## Test Structure

The test suite is organized into multiple test files covering different aspects of the system:

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── test_database.py         # Database operations tests
├── test_scraper.py          # Core scraping functionality tests
├── test_cli.py              # Command-line interface tests
├── test_xml_parsing.py      # XML parsing and data extraction tests
└── test_search.py           # Full-text search functionality tests
```

## Test Categories

### Unit Tests
- **Database Operations** (`test_database.py`)
  - CRUD operations for all database entities
  - Database schema validation
  - Search functionality
  - Backup and maintenance operations

- **Scraper Core** (`test_scraper.py`)
  - HTTP request handling with retry logic
  - XML validation
  - Text cleaning and processing
  - Error handling and recovery

- **XML Parsing** (`test_xml_parsing.py`)
  - Complete XML document parsing
  - Hierarchical data extraction
  - Element-specific parsing functions
  - Malformed XML handling

- **Search** (`test_search.py`)
  - Full-text search queries
  - Boolean operations
  - Phrase matching
  - Case sensitivity and ranking

### Integration Tests
- **CLI Commands** (`test_cli.py`)
  - All command-line operations
  - Environment variable handling
  - Error conditions and edge cases
  - Output format validation

## Running Tests

### Quick Start
```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python run_tests.py

# Run specific test category
python run_tests.py --file test_database.py
```

### Using unittest (Built-in)
```bash
# Run all tests
python -m unittest discover -s tests -p "test_*.py" -v

# Run specific test file
python -m unittest tests.test_database -v

# Run specific test class
python -m unittest tests.test_database.TestECFRDatabase -v

# Run specific test method
python -m unittest tests.test_database.TestECFRDatabase.test_get_or_create_title -v
```

### Using pytest (Advanced)
```bash
# Install pytest first
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/ -v -m unit

# Run integration tests only  
pytest tests/ -v -m integration

# Run with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Run fast tests only (skip slow ones)
pytest tests/ -v -m "not slow"
```

### Using the Test Runner
```bash
# Show help
python run_tests.py --help

# Run with different frameworks
python run_tests.py --framework unittest
python run_tests.py --framework pytest

# Run specific categories
python run_tests.py --unit-only
python run_tests.py --integration-only
python run_tests.py --fast

# Run with coverage
python run_tests.py --coverage
```

### Using Make (if available)
```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration

# Run with coverage
make test-coverage

# Quick test (unit + CLI)
make quick-test
```

## Test Configuration

### Environment Variables
Tests use isolated test databases and directories:
- `ECFR_DB_PATH` - Test database location
- `ECFR_DATA_DIR` - Test data directory
- `ECFR_DEBUG` - Enable debug logging

### Pytest Configuration
See `pytest.ini` for detailed configuration:
- Test discovery patterns
- Markers for test categories
- Logging configuration
- Coverage settings

### Test Fixtures
The `conftest.py` file provides reusable fixtures:
- `test_database` - Clean database for each test
- `populated_database` - Database with sample data
- `sample_xml_content` - XML content for parsing tests
- `temp_dir` - Temporary directory for file operations

## Continuous Integration

### GitHub Actions
The `.github/workflows/tests.yml` file defines CI pipeline:
- Tests on Python 3.8, 3.9, 3.10, 3.11
- Code linting and formatting checks
- Integration testing
- Test artifact collection

### Tox (Multi-environment Testing)
```bash
# Install tox
pip install tox

# Run tests in all environments
tox

# Run specific environment
tox -e py310
tox -e lint
tox -e integration
tox -e coverage
```

## Writing New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Example Test Structure
```python
import unittest
import tempfile
from pathlib import Path
from src.database import ECFRDatabase

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db = ECFRDatabase(self.test_dir / "test.db")
        self.db.connect()
        self.db.initialize_schema()
    
    def tearDown(self):
        """Clean up test environment"""
        self.db.disconnect()
        shutil.rmtree(self.test_dir)
    
    def test_feature_functionality(self):
        """Test specific functionality"""
        # Arrange
        test_data = "sample data"
        
        # Act
        result = self.feature_function(test_data)
        
        # Assert
        self.assertEqual(result, expected_value)
```

### Test Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Always clean up temporary resources
3. **Clear Names**: Test names should describe what they test
4. **Arrange-Act-Assert**: Structure tests clearly
5. **Edge Cases**: Test boundary conditions and error cases
6. **Mock External Dependencies**: Use mocks for network calls
7. **Fast Execution**: Keep unit tests fast-running

### Adding Test Markers
```python
import pytest

@pytest.mark.unit
def test_unit_functionality():
    """Unit test"""
    pass

@pytest.mark.integration
def test_integration_functionality():
    """Integration test"""
    pass

@pytest.mark.slow
def test_slow_operation():
    """Test that takes time"""
    pass

@pytest.mark.network
def test_network_operation():
    """Test requiring network"""
    pass
```

## Troubleshooting Tests

### Common Issues

1. **Database Lock Errors**
   ```
   sqlite3.OperationalError: database is locked
   ```
   - Ensure proper cleanup in tearDown methods
   - Check that database connections are closed

2. **Temporary Directory Issues**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   - Verify temp directory cleanup
   - Check file permissions in test environment

3. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'src'
   ```
   - Run tests from project root directory
   - Ensure virtual environment is activated

4. **Fixture Conflicts**
   ```
   pytest.FixtureRequest.node
   ```
   - Check fixture scope and dependencies
   - Verify conftest.py configuration

### Debug Mode
```bash
# Run with debug logging
python run_tests.py --framework pytest -- --log-cli-level=DEBUG

# Run single test with debug
python -m unittest tests.test_database.TestECFRDatabase.test_get_or_create_title -v
```

### Test Data Inspection
```bash
# Check test database after failure
sqlite3 test_database.db ".tables"
sqlite3 test_database.db "SELECT * FROM titles;"
```

## Performance Testing

### Timing Tests
```python
import time
import unittest

class TestPerformance(unittest.TestCase):
    def test_database_performance(self):
        start_time = time.time()
        # Perform operation
        end_time = time.time()
        
        self.assertLess(end_time - start_time, 1.0)  # Should take < 1 second
```

### Memory Usage
```bash
# Monitor memory during tests
python -m memory_profiler run_tests.py
```

## Test Reporting

### Coverage Reports
```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Test Results
```bash
# Generate JUnit XML for CI
pytest tests/ --junitxml=test-results.xml
```

This comprehensive test suite ensures the eCFR scraper is reliable, maintainable, and production-ready.