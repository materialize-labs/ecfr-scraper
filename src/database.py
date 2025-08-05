"""
Database operations for eCFR scraper
Handles SQLite database connections, schema creation, and data operations
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import hashlib

from config.settings import DB_PATH, DB_SCHEMA_PATH

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class ECFRDatabase:
    """Main database class for eCFR scraper"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection"""
        self.db_path = db_path or DB_PATH
        self.connection: Optional[sqlite3.Connection] = None
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def connect(self) -> sqlite3.Connection:
        """Create database connection with optimizations"""
        try:
            self.connection = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            
            # Enable WAL mode for better concurrent access
            self.connection.execute("PRAGMA journal_mode=WAL")
            
            # Optimize for performance
            self.connection.execute("PRAGMA synchronous=NORMAL")
            self.connection.execute("PRAGMA cache_size=10000")
            self.connection.execute("PRAGMA temp_store=MEMORY")
            
            # Enable foreign keys
            self.connection.execute("PRAGMA foreign_keys=ON")
            
            self.connection.row_factory = sqlite3.Row
            
            logger.info(f"Connected to database: {self.db_path}")
            return self.connection
            
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Failed to connect to database: {e}")
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
    
    def initialize_schema(self) -> bool:
        """Create database schema from SQL file"""
        try:
            if not DB_SCHEMA_PATH.exists():
                raise DatabaseError(f"Schema file not found: {DB_SCHEMA_PATH}")
            
            with open(DB_SCHEMA_PATH, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Execute schema in transaction
            with self.connection:
                self.connection.executescript(schema_sql)
            
            logger.info("Database schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Schema initialization error: {e}")
            raise DatabaseError(f"Failed to initialize schema: {e}")
    
    def get_or_create_title(self, title_number: int, title_name: str) -> int:
        """Get existing title or create new one"""
        try:
            cursor = self.connection.cursor()
            
            # Try to get existing title
            cursor.execute(
                "SELECT id FROM titles WHERE title_number = ?",
                (title_number,)
            )
            row = cursor.fetchone()
            
            if row:
                return row['id']
                
            # Create new title
            cursor.execute(
                """INSERT INTO titles (title_number, title_name, last_updated)
                   VALUES (?, ?, ?)""",
                (title_number, title_name, datetime.now())
            )
            
            title_id = cursor.lastrowid
            logger.debug(f"Created title {title_number}: {title_name}")
            return title_id
            
        except sqlite3.Error as e:
            logger.error(f"Error with title {title_number}: {e}")
            raise DatabaseError(f"Title operation failed: {e}")
    
    def get_or_create_chapter(self, title_id: int, chapter_number: str, chapter_name: str) -> int:
        """Get existing chapter or create new one"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute(
                "SELECT id FROM chapters WHERE title_id = ? AND chapter_number = ?",
                (title_id, chapter_number)
            )
            row = cursor.fetchone()
            
            if row:
                return row['id']
            
            cursor.execute(
                """INSERT INTO chapters (title_id, chapter_number, chapter_name)
                   VALUES (?, ?, ?)""",
                (title_id, chapter_number, chapter_name)
            )
            
            chapter_id = cursor.lastrowid
            logger.debug(f"Created chapter {chapter_number}: {chapter_name}")
            return chapter_id
            
        except sqlite3.Error as e:
            logger.error(f"Error with chapter {chapter_number}: {e}")
            raise DatabaseError(f"Chapter operation failed: {e}")
    
    def get_or_create_subchapter(self, chapter_id: int, subchapter_letter: str, subchapter_name: str) -> int:
        """Get existing subchapter or create new one"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute(
                "SELECT id FROM subchapters WHERE chapter_id = ? AND subchapter_letter = ?",
                (chapter_id, subchapter_letter)
            )
            row = cursor.fetchone()
            
            if row:
                return row['id']
            
            cursor.execute(
                """INSERT INTO subchapters (chapter_id, subchapter_letter, subchapter_name)
                   VALUES (?, ?, ?)""",
                (chapter_id, subchapter_letter, subchapter_name)
            )
            
            subchapter_id = cursor.lastrowid
            logger.debug(f"Created subchapter {subchapter_letter}: {subchapter_name}")
            return subchapter_id
            
        except sqlite3.Error as e:
            logger.error(f"Error with subchapter {subchapter_letter}: {e}")
            raise DatabaseError(f"Subchapter operation failed: {e}")
    
    def get_or_create_part(self, chapter_id: int, subchapter_id: Optional[int], 
                          part_number: int, part_name: str, 
                          authority: Optional[str] = None, source: Optional[str] = None) -> int:
        """Get existing part or create new one"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute(
                "SELECT id FROM parts WHERE chapter_id = ? AND part_number = ?",
                (chapter_id, part_number)
            )
            row = cursor.fetchone()
            
            if row:
                return row['id']
            
            cursor.execute(
                """INSERT INTO parts (chapter_id, subchapter_id, part_number, part_name, 
                                     authority_citation, source_citation)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (chapter_id, subchapter_id, part_number, part_name, authority, source)
            )
            
            part_id = cursor.lastrowid
            logger.debug(f"Created part {part_number}: {part_name}")
            return part_id
            
        except sqlite3.Error as e:
            logger.error(f"Error with part {part_number}: {e}")
            raise DatabaseError(f"Part operation failed: {e}")
    
    def insert_section(self, part_id: int, section_number: str, section_heading: str,
                      section_content: str, authority: Optional[str] = None,
                      source: Optional[str] = None, xml_node_id: Optional[str] = None) -> int:
        """Insert or update a section"""
        try:
            cursor = self.connection.cursor()
            
            # Check if section exists
            cursor.execute(
                "SELECT id FROM sections WHERE part_id = ? AND section_number = ?",
                (part_id, section_number)
            )
            row = cursor.fetchone()
            
            if row:
                # Update existing section
                cursor.execute(
                    """UPDATE sections 
                       SET section_heading = ?, section_content = ?, 
                           authority_citation = ?, source_citation = ?, xml_node_id = ?
                       WHERE id = ?""",
                    (section_heading, section_content, authority, source, xml_node_id, row['id'])
                )
                section_id = row['id']
                logger.debug(f"Updated section {section_number}")
            else:
                # Insert new section
                cursor.execute(
                    """INSERT INTO sections (part_id, section_number, section_heading, 
                                           section_content, authority_citation, source_citation, xml_node_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (part_id, section_number, section_heading, section_content, authority, source, xml_node_id)
                )
                section_id = cursor.lastrowid
                logger.debug(f"Created section {section_number}")
            
            return section_id
            
        except sqlite3.Error as e:
            logger.error(f"Error with section {section_number}: {e}")
            raise DatabaseError(f"Section operation failed: {e}")
    
    def update_scraping_metadata(self, title_number: int, status: str, 
                               file_size: Optional[int] = None, 
                               file_hash: Optional[str] = None,
                               error_message: Optional[str] = None,
                               records_processed: int = 0):
        """Update scraping metadata for a title"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute(
                """INSERT OR REPLACE INTO scraping_metadata 
                   (title_number, last_scraped, file_size, file_hash, scraping_status, 
                    error_message, records_processed)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (title_number, datetime.now(), file_size, file_hash, status, error_message, records_processed)
            )
            
            logger.debug(f"Updated metadata for title {title_number}: {status}")
            
        except sqlite3.Error as e:
            logger.error(f"Error updating metadata for title {title_number}: {e}")
            raise DatabaseError(f"Metadata update failed: {e}")
    
    def get_scraping_metadata(self, title_number: int) -> Optional[Dict[str, Any]]:
        """Get scraping metadata for a title"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT * FROM scraping_metadata WHERE title_number = ?",
                (title_number,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting metadata for title {title_number}: {e}")
            return None
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        try:
            cursor = self.connection.cursor()
            
            stats = {}
            tables = ['titles', 'chapters', 'subchapters', 'parts', 'sections', 'paragraphs']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()['count']
            
            return stats
            
        except sqlite3.Error as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def search_sections(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Full-text search in sections"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """SELECT s.*, p.part_name, t.title_name 
                   FROM sections_fts sf
                   JOIN sections s ON sf.rowid = s.id
                   JOIN parts p ON s.part_id = p.id
                   JOIN chapters c ON p.chapter_id = c.id
                   JOIN titles t ON c.title_id = t.id
                   WHERE sections_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit)
            )
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Search error: {e}")
            return []
    
    def vacuum_database(self):
        """Optimize database"""
        try:
            self.connection.execute("VACUUM")
            logger.info("Database vacuumed successfully")
        except sqlite3.Error as e:
            logger.error(f"Vacuum error: {e}")
    
    def backup_database(self, backup_path: Path):
        """Create database backup"""
        try:
            backup_conn = sqlite3.connect(backup_path)
            self.connection.backup(backup_conn)
            backup_conn.close()
            logger.info(f"Database backed up to: {backup_path}")
        except sqlite3.Error as e:
            logger.error(f"Backup error: {e}")
            raise DatabaseError(f"Backup failed: {e}")


def calculate_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return ""