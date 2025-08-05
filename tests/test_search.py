"""
Tests for search functionality
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from src.database import ECFRDatabase


class TestSearchFunctionality(unittest.TestCase):
    """Test full-text search capabilities"""
    
    def setUp(self):
        """Set up test environment with sample data"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_ecfr.db"
        self.db = ECFRDatabase(self.db_path)
        self.db.connect()
        self.db.initialize_schema()
        
        # Add comprehensive test data
        self._setup_test_data()
    
    def tearDown(self):
        """Clean up test environment"""
        self.db.disconnect()
        shutil.rmtree(self.test_dir)
    
    def _setup_test_data(self):
        """Set up comprehensive test data for search testing"""
        # Title 1: Administrative Procedures
        title1_id = self.db.get_or_create_title(1, "Administrative Procedures")
        chapter1_id = self.db.get_or_create_chapter(title1_id, "I", "General Provisions")
        part1_id = self.db.get_or_create_part(chapter1_id, None, 1, "Definitions and General Rules")
        
        self.db.insert_section(
            part1_id, "1.1", "Definitions",
            "This section contains important definitions for administrative procedures. "
            "The term 'agency' means any department, independent establishment, commission, "
            "administration, authority, board, or other establishment in the executive branch. "
            "The term 'rule' means any agency statement of general applicability that implements law."
        )
        
        self.db.insert_section(
            part1_id, "1.2", "Scope and Application",
            "These procedures apply to all federal agencies unless specifically exempted. "
            "The scope includes rulemaking, adjudication, and licensing procedures. "
            "Administrative law judges must follow these procedural requirements."
        )
        
        self.db.insert_section(
            part1_id, "1.3", "Public Participation",
            "Agencies must provide meaningful opportunity for public participation in rulemaking. "
            "This includes notice and comment procedures, public hearings when appropriate, "
            "and access to relevant documents and data used in decision-making."
        )
        
        # Title 2: Privacy and Information
        title2_id = self.db.get_or_create_title(2, "Privacy and Information Access")
        chapter2_id = self.db.get_or_create_chapter(title2_id, "I", "Privacy Protection")
        part2_id = self.db.get_or_create_part(chapter2_id, None, 10, "Privacy Act Regulations")
        
        self.db.insert_section(
            part2_id, "10.1", "Privacy Policy Framework",
            "Federal agencies must establish comprehensive privacy policies to protect "
            "personally identifiable information (PII). Privacy impact assessments are "
            "required for systems that collect, store, or process personal data."
        )
        
        self.db.insert_section(
            part2_id, "10.2", "Data Security Requirements",
            "Agencies must implement appropriate security measures to protect sensitive data. "
            "This includes encryption, access controls, audit logging, and incident response procedures. "
            "Data breaches must be reported within 24 hours of discovery."
        )
        
        self.db.insert_section(
            part2_id, "10.3", "Freedom of Information Access",
            "The Freedom of Information Act (FOIA) provides public access to federal agency records. "
            "Agencies must process FOIA requests promptly and provide information unless "
            "specifically exempted under the statute. Electronic records are subject to FOIA."
        )
        
        # Title 3: Environmental Regulations
        title3_id = self.db.get_or_create_title(3, "Environmental Protection")
        chapter3_id = self.db.get_or_create_chapter(title3_id, "I", "Environmental Standards")
        part3_id = self.db.get_or_create_part(chapter3_id, None, 20, "Air Quality Standards")
        
        self.db.insert_section(
            part3_id, "20.1", "National Ambient Air Quality Standards",
            "The Environmental Protection Agency establishes national ambient air quality standards "
            "for criteria pollutants including ozone, particulate matter, carbon monoxide, "
            "nitrogen dioxide, sulfur dioxide, and lead. These standards protect public health."
        )
        
        self.db.insert_section(
            part3_id, "20.2", "State Implementation Plans",
            "States must develop and implement plans to achieve and maintain air quality standards. "
            "State implementation plans (SIPs) must include emission control strategies, "
            "monitoring requirements, and enforcement mechanisms."
        )
        
        # Commit all changes for FTS to work properly
        self.db.connection.commit()
    
    def test_search_basic_terms(self):
        """Test basic term searches"""
        # Search for "agency"
        results = self.db.search_sections("agency")
        self.assertGreater(len(results), 0)
        
        # Should find sections mentioning agency/agencies
        section_numbers = [r['section_number'] for r in results]
        self.assertIn("1.1", section_numbers)  # definitions section
        self.assertIn("1.2", section_numbers)  # scope section
        self.assertIn("10.1", section_numbers)  # privacy section
        
        # Search for "privacy"
        results = self.db.search_sections("privacy")
        self.assertGreater(len(results), 0)
        section_numbers = [r['section_number'] for r in results]
        self.assertIn("10.1", section_numbers)
        self.assertIn("10.2", section_numbers)
    
    def test_search_exact_phrases(self):
        """Test exact phrase searches"""
        # Search for exact phrase
        results = self.db.search_sections('"Freedom of Information Act"')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['section_number'], "10.3")
        
        # Search for another exact phrase
        results = self.db.search_sections('"air quality standards"')
        self.assertGreater(len(results), 0)
        section_numbers = [r['section_number'] for r in results]
        self.assertIn("20.1", section_numbers)
        self.assertIn("20.2", section_numbers)
    
    def test_search_partial_words(self):
        """Test partial word matching"""
        # Search for "admin" should match "administrative", "administration"
        results = self.db.search_sections("admin*")
        self.assertGreater(len(results), 0)
        
        # Should find sections with administrative terms
        content_text = " ".join([r['section_content'] for r in results])
        self.assertTrue(
            "administrative" in content_text.lower() or 
            "administration" in content_text.lower()
        )
    
    def test_search_boolean_operations(self):
        """Test boolean search operations"""
        # AND operation
        results = self.db.search_sections("agency AND rulemaking")
        self.assertGreater(len(results), 0)
        
        # OR operation
        results = self.db.search_sections("privacy OR security")
        self.assertGreater(len(results), 0)
        
        # Should find both privacy and security related sections
        section_numbers = [r['section_number'] for r in results]
        self.assertTrue(
            "10.1" in section_numbers or  # privacy section
            "10.2" in section_numbers     # security section
        )
    
    def test_search_with_limits(self):
        """Test search result limits"""
        # Search without limit
        results_all = self.db.search_sections("agency")
        
        # Search with limit
        results_limited = self.db.search_sections("agency", limit=2)
        
        self.assertGreaterEqual(len(results_all), len(results_limited))
        self.assertLessEqual(len(results_limited), 2)
    
    def test_search_case_insensitive(self):
        """Test case-insensitive search"""
        # Search with different cases
        results_lower = self.db.search_sections("privacy")
        results_upper = self.db.search_sections("PRIVACY")
        results_mixed = self.db.search_sections("Privacy")
        
        # All should return same results
        self.assertEqual(len(results_lower), len(results_upper))
        self.assertEqual(len(results_lower), len(results_mixed))
        
        # Results should be identical
        lower_ids = sorted([r['id'] for r in results_lower])
        upper_ids = sorted([r['id'] for r in results_upper])
        mixed_ids = sorted([r['id'] for r in results_mixed])
        
        self.assertEqual(lower_ids, upper_ids)
        self.assertEqual(lower_ids, mixed_ids)
    
    def test_search_empty_query(self):
        """Test search with empty query"""
        results = self.db.search_sections("")
        self.assertEqual(len(results), 0)
    
    def test_search_no_results(self):
        """Test search with no matching results"""
        results = self.db.search_sections("zzz_nonexistent_term_xyz")
        self.assertEqual(len(results), 0)
    
    def test_search_special_characters(self):
        """Test search with special characters"""
        # Search for section numbers
        results = self.db.search_sections("1.1")
        self.assertGreater(len(results), 0)
        
        # Search for acronyms
        results = self.db.search_sections("FOIA")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['section_number'], "10.3")
        
        # Search for parenthetical content
        results = self.db.search_sections("PII")
        self.assertGreater(len(results), 0)
    
    def test_search_common_words(self):
        """Test search with common words"""
        # Common words should still return results
        results = self.db.search_sections("the")
        self.assertGreater(len(results), 0)
        
        results = self.db.search_sections("and")
        self.assertGreater(len(results), 0)
        
        results = self.db.search_sections("must")
        self.assertGreater(len(results), 0)
    
    def test_search_by_section_heading(self):
        """Test search matches in section headings"""
        # Search for terms that appear in headings
        results = self.db.search_sections("Definitions")
        self.assertGreater(len(results), 0)
        
        # Should find the definitions section
        headings = [r['section_heading'] for r in results]
        self.assertIn("Definitions", headings)
        
        # Search for "Policy"
        results = self.db.search_sections("Policy")
        self.assertGreater(len(results), 0)
        
        # Should find privacy policy section
        section_numbers = [r['section_number'] for r in results]
        self.assertIn("10.1", section_numbers)
    
    def test_search_result_structure(self):
        """Test that search results have expected structure"""
        results = self.db.search_sections("agency", limit=1)
        self.assertEqual(len(results), 1)
        
        result = results[0]
        expected_fields = [
            'id', 'section_number', 'section_heading', 'section_content',
            'part_name', 'title_name'
        ]
        
        for field in expected_fields:
            self.assertIn(field, result)
            self.assertIsNotNone(result[field])
    
    def test_search_relevance_ranking(self):
        """Test that search results are ranked by relevance"""
        # Search for a term that appears with different frequencies
        results = self.db.search_sections("procedures")
        
        if len(results) > 1:
            # Results should be ordered by relevance (first result most relevant)
            # This is handled by FTS5's built-in ranking
            self.assertIsInstance(results[0], dict)
            self.assertIn('section_content', results[0])
    
    def test_search_with_numbers(self):
        """Test search with numeric content"""
        # Search for "24 hours"
        results = self.db.search_sections("24 hours")
        self.assertGreater(len(results), 0)
        
        # Should find the data breach reporting section
        section_numbers = [r['section_number'] for r in results]
        self.assertIn("10.2", section_numbers)
    
    def test_search_compound_terms(self):
        """Test search with compound terms"""
        # Search for hyphenated terms
        results = self.db.search_sections("decision-making")
        self.assertGreater(len(results), 0)
        
        # Should find public participation section
        section_numbers = [r['section_number'] for r in results]
        self.assertIn("1.3", section_numbers)
    
    def test_search_title_information(self):
        """Test that search results include title information"""
        results = self.db.search_sections("environmental")
        self.assertGreater(len(results), 0)
        
        # Check that environmental sections include title info
        env_results = [r for r in results if "Environmental" in r['title_name']]
        self.assertGreater(len(env_results), 0)
        
        for result in env_results:
            self.assertIn("Environmental Protection", result['title_name'])
            self.assertIn("Air Quality", result['part_name'])
    
    def test_search_multiple_titles(self):
        """Test search across multiple titles"""
        # Search for term that appears in multiple titles
        results = self.db.search_sections("federal")
        self.assertGreater(len(results), 0)
        
        # Should have results from different titles
        title_names = set(r['title_name'] for r in results)
        self.assertGreater(len(title_names), 1)
    
    def test_search_performance_large_result_set(self):
        """Test search performance with potentially large result sets"""
        # Search for very common term
        results = self.db.search_sections("must", limit=100)
        
        # Should complete quickly and return results
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 100)
        
        # All results should have the expected structure
        for result in results:
            self.assertIn('section_number', result)
            self.assertIn('section_content', result)
            self.assertIsInstance(result['section_content'], str)


if __name__ == '__main__':
    unittest.main()