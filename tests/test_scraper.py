"""
Unit tests for scraper functionality
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET
import requests

from src.scraper import ECFRScraper, ScrapingError
from src.database import ECFRDatabase


class TestECFRScraper(unittest.TestCase):
    """Test cases for ECFRScraper class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_ecfr.db"
        self.db = ECFRDatabase(self.db_path)
        self.db.connect()
        self.db.initialize_schema()
        
        self.scraper = ECFRScraper(self.db)
        self.scraper.download_dir = self.test_dir / "xml_files"
        self.scraper.download_dir.mkdir()
    
    def tearDown(self):
        """Clean up test environment"""
        self.scraper.close()
        self.db.disconnect()
        shutil.rmtree(self.test_dir)
    
    def test_scraper_initialization(self):
        """Test scraper initialization"""
        self.assertIsNotNone(self.scraper.database)
        self.assertIsNotNone(self.scraper.session)
        self.assertTrue(self.scraper.download_dir.exists())
    
    @patch('src.scraper.requests.Session.get')
    def test_make_request_success(self, mock_get):
        """Test successful HTTP request"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.scraper._make_request("http://example.com")
        self.assertEqual(result, mock_response)
        mock_get.assert_called_once()
    
    @patch('src.scraper.requests.Session.get')
    def test_make_request_retry(self, mock_get):
        """Test HTTP request with retry logic"""
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = requests.exceptions.RequestException("Error")
        
        mock_response_success = Mock()
        mock_response_success.raise_for_status.return_value = None
        
        mock_get.side_effect = [mock_response_fail, mock_response_success]
        
        result = self.scraper._make_request("http://example.com")
        self.assertEqual(result, mock_response_success)
        self.assertEqual(mock_get.call_count, 2)
    
    @patch('src.scraper.requests.Session.get')
    def test_make_request_max_retries(self, mock_get):
        """Test HTTP request max retries exceeded"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Error")
        mock_get.return_value = mock_response
        
        with self.assertRaises(ScrapingError):
            self.scraper._make_request("http://example.com")
        
        self.assertEqual(mock_get.call_count, 3)  # MAX_RETRIES = 3
    
    def test_validate_xml_valid(self):
        """Test XML validation with valid XML"""
        xml_file = self.test_dir / "valid.xml"
        xml_file.write_text('<?xml version="1.0"?><root><child>content</child></root>')
        
        result = self.scraper._validate_xml(xml_file)
        self.assertTrue(result)
    
    def test_validate_xml_invalid(self):
        """Test XML validation with invalid XML"""
        xml_file = self.test_dir / "invalid.xml"
        xml_file.write_text('<root><child>unclosed tag</root>')
        
        result = self.scraper._validate_xml(xml_file)
        self.assertFalse(result)
    
    def test_clean_text(self):
        """Test text cleaning functionality"""
        test_cases = [
            ("  multiple   spaces  ", "multiple spaces"),
            ("text&amp;more", "text&more"),
            ("&lt;tag&gt;", "<tag>"),
            ("&quot;quoted&quot;", '"quoted"'),
            ("line1\n\nline2", "line1 line2"),
            ("", ""),
        ]
        
        for input_text, expected in test_cases:
            result = self.scraper._clean_text(input_text)
            self.assertEqual(result, expected)
    
    def test_extract_element_text(self):
        """Test XML element text extraction"""
        xml_content = '''
        <root>
            Text before
            <child>Child text</child>
            Text after
            <nested>
                <deep>Deep text</deep>
            </nested>
        </root>
        '''
        root = ET.fromstring(xml_content)
        
        result = self.scraper._extract_element_text(root)
        self.assertIn("Text before", result)
        self.assertIn("Child text", result)
        self.assertIn("Text after", result)
        self.assertIn("Deep text", result)
    
    def test_extract_authority(self):
        """Test authority citation extraction"""
        xml_content = '''
        <section>
            <AUTH>
                <HED>Authority:</HED>
                <PSPACE>44 U.S.C. 1506; sec. 6, E.O. 10530</PSPACE>
            </AUTH>
        </section>
        '''
        element = ET.fromstring(xml_content)
        
        result = self.scraper._extract_authority(element)
        self.assertIn("44 U.S.C. 1506", result)
        self.assertIn("E.O. 10530", result)
    
    def test_extract_source(self):
        """Test source citation extraction"""
        xml_content = '''
        <section>
            <SOURCE>
                <HED>Source:</HED>
                <PSPACE>37 FR 23607, Nov. 4, 1972</PSPACE>
            </SOURCE>
        </section>
        '''
        element = ET.fromstring(xml_content)
        
        result = self.scraper._extract_source(element)
        self.assertIn("37 FR 23607", result)
        self.assertIn("Nov. 4, 1972", result)
    
    def test_process_chapter(self):
        """Test chapter processing"""
        title_id = self.db.get_or_create_title(1, "Test Title")
        
        xml_content = '''
        <DIV3 N="I" TYPE="CHAPTER">
            <HEAD>CHAPTER I—TEST CHAPTER</HEAD>
        </DIV3>
        '''
        chapter_elem = ET.fromstring(xml_content)
        
        chapter_id = self.scraper._process_chapter(chapter_elem, title_id)
        self.assertIsNotNone(chapter_id)
        self.assertIsInstance(chapter_id, int)
        
        # Verify chapter was created
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT chapter_number, chapter_name FROM chapters WHERE id = ?", (chapter_id,))
        row = cursor.fetchone()
        self.assertEqual(row['chapter_number'], "I")
        self.assertIn("TEST CHAPTER", row['chapter_name'])
    
    def test_process_subchapter(self):
        """Test subchapter processing"""
        title_id = self.db.get_or_create_title(1, "Test Title")
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter")
        
        xml_content = '''
        <DIV4 N="A" TYPE="SUBCHAP">
            <HEAD>SUBCHAPTER A—TEST SUBCHAPTER</HEAD>
        </DIV4>
        '''
        subchapter_elem = ET.fromstring(xml_content)
        
        subchapter_id = self.scraper._process_subchapter(subchapter_elem, chapter_id)
        self.assertIsNotNone(subchapter_id)
        self.assertIsInstance(subchapter_id, int)
        
        # Verify subchapter was created
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT subchapter_letter, subchapter_name FROM subchapters WHERE id = ?", (subchapter_id,))
        row = cursor.fetchone()
        self.assertEqual(row['subchapter_letter'], "A")
        self.assertIn("TEST SUBCHAPTER", row['subchapter_name'])
    
    def test_process_part(self):
        """Test part processing"""
        title_id = self.db.get_or_create_title(1, "Test Title")
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter")
        
        xml_content = '''
        <DIV5 N="1" TYPE="PART">
            <HEAD>PART 1—TEST PART</HEAD>
            <AUTH>
                <HED>Authority:</HED>
                <PSPACE>Test Authority</PSPACE>
            </AUTH>
            <DIV8 N="§ 1.1" TYPE="SECTION">
                <HEAD>§ 1.1 Test Section</HEAD>
                <P>Test section content</P>
            </DIV8>
        </DIV5>
        '''
        part_elem = ET.fromstring(xml_content)
        
        sections_count = self.scraper._process_part(part_elem, chapter_id, None)
        self.assertEqual(sections_count, 1)
        
        # Verify part was created
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT part_number, part_name FROM parts WHERE chapter_id = ?", (chapter_id,))
        row = cursor.fetchone()
        self.assertEqual(row['part_number'], 1)
        self.assertIn("TEST PART", row['part_name'])
    
    def test_process_section(self):
        """Test section processing"""
        title_id = self.db.get_or_create_title(1, "Test Title")
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter")
        part_id = self.db.get_or_create_part(chapter_id, None, 1, "Test Part")
        
        xml_content = '''
        <DIV8 N="§ 1.1" TYPE="SECTION">
            <HEAD>§ 1.1 Test Section Heading</HEAD>
            <P>This is the first paragraph of the section.</P>
            <P>This is the second paragraph with more content.</P>
        </DIV8>
        '''
        section_elem = ET.fromstring(xml_content)
        
        result = self.scraper._process_section(section_elem, part_id)
        self.assertTrue(result)
        
        # Verify section was created
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT section_number, section_heading, section_content FROM sections WHERE part_id = ?", (part_id,))
        row = cursor.fetchone()
        self.assertEqual(row['section_number'], "1.1")
        self.assertEqual(row['section_heading'], "Test Section Heading")
        self.assertIn("first paragraph", row['section_content'])
        self.assertIn("second paragraph", row['section_content'])
    
    @patch('src.scraper.calculate_file_hash')
    def test_check_for_updates_no_metadata(self, mock_hash):
        """Test update check with no existing metadata"""
        mock_hash.return_value = "new-hash"
        
        with patch.object(self.scraper, 'download_title_xml') as mock_download:
            mock_download.return_value = Path("test.xml")
            
            result = self.scraper.check_for_updates(1)
            self.assertTrue(result)
    
    @patch('src.scraper.calculate_file_hash')
    def test_check_for_updates_different_hash(self, mock_hash):
        """Test update check with different hash"""
        # Set up existing metadata
        self.db.update_scraping_metadata(1, 'completed', 1024, 'old-hash', None, 10)
        mock_hash.return_value = "new-hash"
        
        with patch.object(self.scraper, 'download_title_xml') as mock_download:
            mock_download.return_value = Path("test.xml")
            
            result = self.scraper.check_for_updates(1)
            self.assertTrue(result)
    
    @patch('src.scraper.calculate_file_hash')
    def test_check_for_updates_same_hash(self, mock_hash):
        """Test update check with same hash"""
        # Set up existing metadata
        self.db.update_scraping_metadata(1, 'completed', 1024, 'same-hash', None, 10)
        mock_hash.return_value = "same-hash"
        
        with patch.object(self.scraper, 'download_title_xml') as mock_download:
            mock_download.return_value = Path("test.xml")
            
            result = self.scraper.check_for_updates(1)
            self.assertFalse(result)
    
    def test_scraper_close(self):
        """Test scraper cleanup"""
        # Should not raise an exception
        self.scraper.close()


class TestScrapingError(unittest.TestCase):
    """Test ScrapingError exception"""
    
    def test_scraping_error(self):
        """Test ScrapingError creation and usage"""
        error_msg = "Test scraping error"
        error = ScrapingError(error_msg)
        
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), error_msg)
        
        # Test raising
        with self.assertRaises(ScrapingError) as context:
            raise ScrapingError(error_msg)
        
        self.assertEqual(str(context.exception), error_msg)


if __name__ == '__main__':
    unittest.main()