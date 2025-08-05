"""
Pytest configuration and fixtures for eCFR scraper tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import os

from src.database import ECFRDatabase


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data that persists for the session"""
    temp_dir = Path(tempfile.mkdtemp(prefix="ecfr_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for a single test"""
    temp_dir = Path(tempfile.mkdtemp(prefix="ecfr_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_db_path(temp_dir):
    """Provide a test database path"""
    return temp_dir / "test_ecfr.db"


@pytest.fixture
def test_database(test_db_path):
    """Create and initialize a test database"""
    db = ECFRDatabase(test_db_path)
    db.connect()
    db.initialize_schema()
    yield db
    db.disconnect()


@pytest.fixture
def populated_database(test_database):
    """Create a test database with sample data"""
    db = test_database
    
    # Add test data
    title_id = db.get_or_create_title(1, "Test Title 1")
    chapter_id = db.get_or_create_chapter(title_id, "I", "Test Chapter I")
    subchapter_id = db.get_or_create_subchapter(chapter_id, "A", "Test Subchapter A")
    part_id = db.get_or_create_part(chapter_id, subchapter_id, 1, "Test Part 1")
    
    db.insert_section(
        part_id, "1.1", "Test Section",
        "This is a test section with sample content for testing purposes."
    )
    db.insert_section(
        part_id, "1.2", "Another Section",
        "This is another test section with different content and keywords."
    )
    
    # Add more complex data
    part_id_2 = db.get_or_create_part(chapter_id, subchapter_id, 2, "Test Part 2")
    db.insert_section(
        part_id_2, "2.1", "Definitions",
        "This section contains important definitions for regulatory terms."
    )
    
    db.connection.commit()
    yield db


@pytest.fixture
def test_env_vars(test_db_path, temp_dir):
    """Set up test environment variables"""
    original_env = {}
    test_vars = {
        'ECFR_DB_PATH': str(test_db_path),
        'ECFR_DATA_DIR': str(temp_dir),
        'ECFR_DEBUG': '1'
    }
    
    # Save original values and set test values
    for key, value in test_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield test_vars
    
    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def sample_xml_content():
    """Provide sample XML content for testing"""
    return '''<?xml version="1.0" encoding="UTF-8" ?>
<DLPSTEXTCLASS>
<HEADER>
<FILEDESC>
<TITLESTMT>
<TITLE>Title 1: Test Provisions</TITLE>
</TITLESTMT>
<PUBLICATIONSTMT>
<IDNO TYPE="title">1</IDNO>
</PUBLICATIONSTMT>
</FILEDESC>
</HEADER>
<TEXT>
<BODY>
<ECFRBRWS>
<DIV1 N="1" TYPE="TITLE">
<HEAD>Title 1—Test Provisions</HEAD>

<DIV3 N="I" TYPE="CHAPTER">
<HEAD>CHAPTER I—TEST CHAPTER</HEAD>

<DIV4 N="A" TYPE="SUBCHAP">
<HEAD>SUBCHAPTER A—GENERAL</HEAD>

<DIV5 N="1" TYPE="PART">
<HEAD>PART 1—DEFINITIONS</HEAD>
<AUTH>
<HED>Authority:</HED>
<PSPACE>Test Authority Citation</PSPACE>
</AUTH>

<DIV8 N="§ 1.1" TYPE="SECTION">
<HEAD>§ 1.1 Test definitions.</HEAD>
<P>This section contains test definitions.</P>
<P><I>Term 1</I> means the first test term.</P>
<P><I>Term 2</I> means the second test term.</P>
</DIV8>

</DIV5>

</DIV4>

</DIV3>

</DIV1>
</ECFRBRWS>
</BODY>
</TEXT>
</DLPSTEXTCLASS>'''


@pytest.fixture
def sample_xml_file(temp_dir, sample_xml_content):
    """Create a sample XML file for testing"""
    xml_file = temp_dir / "sample.xml"
    xml_file.write_text(sample_xml_content)
    return xml_file


# Pytest markers for different test categories
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access"
    )


# Test collection customization
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on location"""
    for item in items:
        # Add markers based on test file names
        if "test_cli" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_database" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_scraper" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_xml_parsing" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_search" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # Mark tests that might be slow
        if "parse_complete_xml" in item.name or "scrape_all" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Mark tests that require network
        if "download" in item.name or "request" in item.name:
            item.add_marker(pytest.mark.network)