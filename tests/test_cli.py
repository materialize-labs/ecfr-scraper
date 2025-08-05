"""
Integration tests for CLI commands
"""

import unittest
import tempfile
import shutil
import subprocess
import json
from pathlib import Path
from unittest.mock import patch


class TestCLICommands(unittest.TestCase):
    """Test cases for CLI command integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_ecfr.db"
        
        # Set environment variables to use test database
        self.env_vars = {
            'ECFR_DB_PATH': str(self.db_path),
            'ECFR_DATA_DIR': str(self.test_dir)
        }
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def run_cli_command(self, args, expect_success=True):
        """Helper to run CLI commands"""
        cmd = ['python', '-m', 'src.main'] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={**self.env_vars, 'PATH': subprocess.os.environ.get('PATH', '')}
        )
        
        if expect_success:
            if result.returncode != 0:
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
            self.assertEqual(result.returncode, 0, f"Command failed: {' '.join(args)}")
        
        return result
    
    def test_cli_help(self):
        """Test CLI help command"""
        result = self.run_cli_command(['--help'])
        self.assertIn('eCFR Scraper', result.stdout)
        self.assertIn('Electronic Code of Federal Regulations', result.stdout)
    
    def test_init_db_command(self):
        """Test database initialization command"""
        result = self.run_cli_command(['init-db'])
        self.assertIn('Database initialized successfully', result.stdout)
        self.assertTrue(self.db_path.exists())
    
    def test_init_db_force(self):
        """Test database initialization with force flag"""
        # Create database first
        self.run_cli_command(['init-db'])
        
        # Force recreate
        result = self.run_cli_command(['init-db', '--force'])
        self.assertIn('Database initialized successfully', result.stdout)
    
    def test_stats_empty_database(self):
        """Test stats command on empty database"""
        self.run_cli_command(['init-db'])
        result = self.run_cli_command(['stats'])
        
        self.assertIn('Database Statistics', result.stdout)
        self.assertIn('Titles      : 0', result.stdout)
        self.assertIn('Chapters    : 0', result.stdout)
        self.assertIn('Parts       : 0', result.stdout)
        self.assertIn('Sections    : 0', result.stdout)
    
    def test_list_titles_empty(self):
        """Test list-titles command on empty database"""
        self.run_cli_command(['init-db'])
        result = self.run_cli_command(['list-titles'])
        
        self.assertIn('CFR Titles in Database', result.stdout)
        self.assertIn('Title  Sections   Status', result.stdout)
    
    def test_search_empty_database(self):
        """Test search command on empty database"""
        self.run_cli_command(['init-db'])
        result = self.run_cli_command(['search', 'test'])
        
        self.assertIn('No results found', result.stdout)
    
    def test_search_json_format(self):
        """Test search command with JSON output"""
        self.run_cli_command(['init-db'])
        result = self.run_cli_command(['search', 'test', '--format', 'json'])
        
        # Should be valid JSON (empty array)
        try:
            data = json.loads(result.stdout.strip())
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 0)
        except json.JSONDecodeError:
            self.fail("Output is not valid JSON")
    
    def test_backup_command(self):
        """Test database backup command"""
        self.run_cli_command(['init-db'])
        backup_path = self.test_dir / "backup.db"
        
        result = self.run_cli_command(['backup', str(backup_path)])
        self.assertIn('Database backed up', result.stdout)
        self.assertTrue(backup_path.exists())
    
    def test_vacuum_command(self):
        """Test database vacuum command"""
        self.run_cli_command(['init-db'])
        result = self.run_cli_command(['vacuum'])
        
        self.assertIn('Database optimized successfully', result.stdout)
    
    def test_debug_logging(self):
        """Test debug logging flag"""
        result = self.run_cli_command(['--debug', 'init-db'])
        # Debug logging should show more detailed messages
        self.assertIn('DEBUG', result.stderr)
    
    def test_no_log_file(self):
        """Test disabling file logging"""
        result = self.run_cli_command(['--no-log-file', 'init-db'])
        # Should still work, just without file logging
        self.assertIn('Database initialized successfully', result.stdout)
    
    def test_invalid_command(self):
        """Test invalid command handling"""
        result = self.run_cli_command(['invalid-command'], expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No such command', result.stderr)
    
    def test_scrape_invalid_titles(self):
        """Test scrape command with invalid title numbers"""
        self.run_cli_command(['init-db'])
        result = self.run_cli_command(['scrape', '--titles', '999'], expect_success=False)
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid CFR titles', result.stderr)
    
    def test_scrape_valid_titles_format(self):
        """Test scrape command with valid title format (without actual scraping)"""
        self.run_cli_command(['init-db'])
        
        # This will fail because we don't have internet access in tests,
        # but it should pass the title validation
        result = self.run_cli_command(['scrape', '--titles', '1,2,3'], expect_success=False)
        
        # Should not fail on title validation
        self.assertNotIn('Invalid CFR titles', result.stderr)
    
    def test_check_updates_command(self):
        """Test check-updates command"""
        self.run_cli_command(['init-db'])
        
        # This will fail due to network, but should validate titles
        result = self.run_cli_command(['check-updates', '--titles', '1'], expect_success=False)
        self.assertNotIn('Invalid CFR titles', result.stderr)
    
    def test_list_titles_specific(self):
        """Test list-titles command with specific title"""
        self.run_cli_command(['init-db'])
        result = self.run_cli_command(['list-titles', '--title', '999'])
        
        self.assertIn('not found in database', result.stdout)


class TestCLIErrorHandling(unittest.TestCase):
    """Test CLI error handling scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        # Don't create database to test error handling
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def run_cli_command(self, args, env_vars=None):
        """Helper to run CLI commands"""
        cmd = ['python', '-m', 'src.main'] + args
        env = env_vars or {}
        env['PATH'] = subprocess.os.environ.get('PATH', '')
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return result
    
    def test_stats_no_database(self):
        """Test stats command without database"""
        env_vars = {
            'ECFR_DB_PATH': str(self.test_dir / "nonexistent.db"),
            'ECFR_DATA_DIR': str(self.test_dir)
        }
        
        result = self.run_cli_command(['stats'], env_vars)
        self.assertNotEqual(result.returncode, 0)
    
    def test_search_no_database(self):
        """Test search command without database"""
        env_vars = {
            'ECFR_DB_PATH': str(self.test_dir / "nonexistent.db"),
            'ECFR_DATA_DIR': str(self.test_dir)
        }
        
        result = self.run_cli_command(['search', 'test'], env_vars)
        self.assertNotEqual(result.returncode, 0)
    
    def test_scrape_no_database(self):
        """Test scrape command without initialized database"""
        env_vars = {
            'ECFR_DB_PATH': str(self.test_dir / "empty.db"),
            'ECFR_DATA_DIR': str(self.test_dir)
        }
        
        result = self.run_cli_command(['scrape', '--titles', '1'], env_vars)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not initialized', result.stderr)


class TestCLIWithMockData(unittest.TestCase):
    """Test CLI commands with mock data"""
    
    def setUp(self):
        """Set up test environment with data"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_ecfr.db"
        
        # Set up database with test data
        from src.database import ECFRDatabase
        self.db = ECFRDatabase(self.db_path)
        self.db.connect()
        self.db.initialize_schema()
        
        # Add test data
        title_id = self.db.get_or_create_title(1, "Test Title 1")
        chapter_id = self.db.get_or_create_chapter(title_id, "I", "Test Chapter I")
        part_id = self.db.get_or_create_part(chapter_id, None, 1, "Test Part 1")
        self.db.insert_section(
            part_id, "1.1", "Test Section", "This section contains test definitions and rules"
        )
        self.db.connection.commit()
        self.db.disconnect()
        
        self.env_vars = {
            'ECFR_DB_PATH': str(self.db_path),
            'ECFR_DATA_DIR': str(self.test_dir)
        }
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def run_cli_command(self, args):
        """Helper to run CLI commands"""
        cmd = ['python', '-m', 'src.main'] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={**self.env_vars, 'PATH': subprocess.os.environ.get('PATH', '')}
        )
        
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        
        return result
    
    def test_stats_with_data(self):
        """Test stats command with actual data"""
        result = self.run_cli_command(['stats'])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Titles      : 1', result.stdout)
        self.assertIn('Chapters    : 1', result.stdout)
        self.assertIn('Parts       : 1', result.stdout)
        self.assertIn('Sections    : 1', result.stdout)
    
    def test_list_titles_with_data(self):
        """Test list-titles command with actual data"""
        result = self.run_cli_command(['list-titles'])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Test Title 1', result.stdout)
        self.assertIn('1      1', result.stdout)  # Title 1 with 1 section
    
    def test_list_titles_specific_with_data(self):
        """Test list-titles command for specific title"""
        result = self.run_cli_command(['list-titles', '--title', '1'])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('CFR Title 1: Test Title 1', result.stdout)
        self.assertIn('Chapters: 1', result.stdout)
        self.assertIn('Parts: 1', result.stdout)
        self.assertIn('Sections: 1', result.stdout)
    
    def test_search_with_data(self):
        """Test search command with actual data"""
        result = self.run_cli_command(['search', 'definitions'])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Found 1 results for 'definitions'", result.stdout)
        self.assertIn('Test Section', result.stdout)
        self.assertIn('1.1', result.stdout)
    
    def test_search_json_with_data(self):
        """Test search command with JSON output and data"""
        result = self.run_cli_command(['search', 'test', '--format', 'json'])
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        data = json.loads(result.stdout.strip())
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['section_number'], '1.1')
        self.assertEqual(data[0]['section_heading'], 'Test Section')


if __name__ == '__main__':
    unittest.main()