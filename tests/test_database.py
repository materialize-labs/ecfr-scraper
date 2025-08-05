"""
Unit tests for database operations
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from src.database import ECFRDatabase, DatabaseError, calculate_file_hash


class TestECFRDatabase(unittest.TestCase):
    """Test cases for ECFRDatabase class"""
    
    def setUp(self):
        """Set up test database"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_ecfr.db"
        self.db = ECFRDatabase(self.db_path)
        self.db.connect()
        self.db.initialize_schema()
    
    def tearDown(self):
        """Clean up test database"""
        self.db.disconnect()
        shutil.rmtree(self.test_dir)
    
    def test_database_initialization(self):
        """Test database initialization"""
        self.assertTrue(self.db_path.exists())
        
        # Test that tables exist
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {
            'titles', 'chapters', 'subchapters', 'parts', 'sections',
            'paragraphs', 'cross_references', 'amendments', 'scraping_metadata'
        }
        
        self.assertTrue(expected_tables.issubset(tables))
    
    def test_get_or_create_title(self):
        """Test title creation and retrieval"""
        # Create new title
        title_id = self.db.get_or_create_title(1, "Test Title 1")
        self.assertIsInstance(title_id, int)
        self.assertGreater(title_id, 0)
        
        # Get existing title
        same_title_id = self.db.get_or_create_title(1, "Test Title 1")
        self.assertEqual(title_id, same_title_id)
        
        # Create different title
        title_id_2 = self.db.get_or_create_title(2, "Test Title 2")
        self.assertNotEqual(title_id, title_id_2)
    
    def test_get_or_create_chapter(self):
        """Test chapter creation and retrieval"""
        title_id = self.db.get_or_create_title(1, "Test Title")
        
        # Create new chapter
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter I")
        self.assertIsInstance(chapter_id, int)
        self.assertGreater(chapter_id, 0)
        
        # Get existing chapter
        same_chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter I")
        self.assertEqual(chapter_id, same_chapter_id)
    
    def test_get_or_create_subchapter(self):
        """Test subchapter creation and retrieval"""
        title_id = self.db.get_or_create_title(1, "Test Title")
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter")
        
        # Create new subchapter
        subchapter_id = self.db.get_or_create_subchapter(chapter_id, "A", "Test Subchapter A")
        self.assertIsInstance(subchapter_id, int)
        self.assertGreater(subchapter_id, 0)
        
        # Get existing subchapter
        same_subchapter_id = self.db.get_or_create_subchapter(chapter_id, "A", "Test Subchapter A")
        self.assertEqual(subchapter_id, same_subchapter_id)
    
    def test_get_or_create_part(self):
        """Test part creation and retrieval"""
        title_id = self.db.get_or_create_title(1, "Test Title")
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter")
        subchapter_id = self.db.get_or_create_subchapter(chapter_id, "A", "Test Subchapter")
        
        # Create new part with subchapter
        part_id = self.db.get_or_create_part(
            chapter_id, subchapter_id, 1, "Test Part 1", "Test Authority", "Test Source"
        )
        self.assertIsInstance(part_id, int)
        self.assertGreater(part_id, 0)
        
        # Create part without subchapter
        part_id_2 = self.db.get_or_create_part(
            chapter_id, None, 2, "Test Part 2"
        )
        self.assertIsInstance(part_id_2, int)
        self.assertNotEqual(part_id, part_id_2)
    
    def test_insert_section(self):
        """Test section insertion and updates"""
        title_id = self.db.get_or_create_title(1, "Test Title")
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter")
        part_id = self.db.get_or_create_part(chapter_id, None, 1, "Test Part")
        
        # Insert new section
        section_id = self.db.insert_section(
            part_id, "1.1", "Test Section", "Test content",
            "Test authority", "Test source", "test-node-id"
        )
        self.assertIsInstance(section_id, int)
        self.assertGreater(section_id, 0)
        
        # Update existing section
        updated_section_id = self.db.insert_section(
            part_id, "1.1", "Updated Section", "Updated content"
        )
        self.assertEqual(section_id, updated_section_id)
        
        # Verify update
        cursor = self.db.connection.cursor()
        cursor.execute(
            "SELECT section_heading, section_content FROM sections WHERE id = ?",
            (section_id,)
        )
        row = cursor.fetchone()
        self.assertEqual(row['section_heading'], "Updated Section")
        self.assertEqual(row['section_content'], "Updated content")
    
    def test_scraping_metadata(self):
        """Test scraping metadata operations"""
        # Update metadata
        self.db.update_scraping_metadata(
            1, 'completed', 1024, 'test-hash', None, 10
        )
        
        # Get metadata
        metadata = self.db.get_scraping_metadata(1)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['title_number'], 1)
        self.assertEqual(metadata['scraping_status'], 'completed')
        self.assertEqual(metadata['file_size'], 1024)
        self.assertEqual(metadata['file_hash'], 'test-hash')
        self.assertEqual(metadata['records_processed'], 10)
        
        # Get non-existent metadata
        no_metadata = self.db.get_scraping_metadata(999)
        self.assertIsNone(no_metadata)
    
    def test_database_stats(self):
        """Test database statistics"""
        # Add some test data
        title_id = self.db.get_or_create_title(1, "Test Title")
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter")
        part_id = self.db.get_or_create_part(chapter_id, None, 1, "Test Part")
        self.db.insert_section(part_id, "1.1", "Test Section", "Test content")
        
        stats = self.db.get_database_stats()
        self.assertEqual(stats['titles'], 1)
        self.assertEqual(stats['chapters'], 1)
        self.assertEqual(stats['parts'], 1)
        self.assertEqual(stats['sections'], 1)
    
    def test_search_sections(self):
        """Test full-text search functionality"""
        # Add test data
        title_id = self.db.get_or_create_title(1, "Test Title")
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter")
        part_id = self.db.get_or_create_part(chapter_id, None, 1, "Test Part")
        
        self.db.insert_section(
            part_id, "1.1", "Definitions", "This section contains important definitions"
        )
        self.db.insert_section(
            part_id, "1.2", "General Rules", "This section contains general administrative rules"
        )
        
        # Commit changes for FTS to work
        self.db.connection.commit()
        
        # Search for "definitions"
        results = self.db.search_sections("definitions")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['section_number'], "1.1")
        
        # Search for "administrative"
        results = self.db.search_sections("administrative")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['section_number'], "1.2")
        
        # Search with limit
        results = self.db.search_sections("section", limit=1)
        self.assertEqual(len(results), 1)
    
    def test_backup_database(self):
        """Test database backup functionality"""
        # Add some test data
        title_id = self.db.get_or_create_title(1, "Test Title")
        
        # Create backup
        backup_path = self.test_dir / "backup.db"
        self.db.backup_database(backup_path)
        
        self.assertTrue(backup_path.exists())
        
        # Verify backup contains data
        backup_db = ECFRDatabase(backup_path)
        backup_db.connect()
        stats = backup_db.get_database_stats()
        self.assertEqual(stats['titles'], 1)
        backup_db.disconnect()
    
    def test_vacuum_database(self):
        """Test database vacuum operation"""
        # This should not raise an exception
        self.db.vacuum_database()


class TestDatabaseUtilities(unittest.TestCase):
    """Test utility functions"""
    
    def setUp(self):
        """Set up test files"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_file = self.test_dir / "test.txt"
        self.test_file.write_text("Hello, World!")
    
    def tearDown(self):
        """Clean up test files"""
        shutil.rmtree(self.test_dir)
    
    def test_calculate_file_hash(self):
        """Test file hash calculation"""
        hash1 = calculate_file_hash(self.test_file)
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 32)  # MD5 hash length
        
        # Same file should produce same hash
        hash2 = calculate_file_hash(self.test_file)
        self.assertEqual(hash1, hash2)
        
        # Different content should produce different hash
        self.test_file.write_text("Different content")
        hash3 = calculate_file_hash(self.test_file)
        self.assertNotEqual(hash1, hash3)
    
    def test_calculate_file_hash_nonexistent(self):
        """Test file hash calculation for non-existent file"""
        nonexistent = self.test_dir / "nonexistent.txt"
        hash_result = calculate_file_hash(nonexistent)
        self.assertEqual(hash_result, "")


if __name__ == '__main__':
    unittest.main()