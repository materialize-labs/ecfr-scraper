"""
Tests for XML parsing functionality
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET

from src.scraper import ECFRScraper
from src.database import ECFRDatabase


class TestXMLParsing(unittest.TestCase):
    """Test XML parsing with real eCFR XML structure"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_ecfr.db"
        self.db = ECFRDatabase(self.db_path)
        self.db.connect()
        self.db.initialize_schema()
        
        self.scraper = ECFRScraper(self.db)
    
    def tearDown(self):
        """Clean up test environment"""
        self.scraper.close()
        self.db.disconnect()
        shutil.rmtree(self.test_dir)
    
    def create_sample_xml(self, title_number=1):
        """Create a sample eCFR XML file for testing"""
        xml_content = f'''<?xml version="1.0" encoding="UTF-8" ?>
<DLPSTEXTCLASS>
<HEADER>
<FILEDESC>
<TITLESTMT>
<TITLE>Title {title_number}: Test Provisions</TITLE>
</TITLESTMT>
<PUBLICATIONSTMT>
<IDNO TYPE="title">{title_number}</IDNO>
<DATE>2024-01-01</DATE>
</PUBLICATIONSTMT>
</FILEDESC>
</HEADER>
<TEXT>
<BODY>
<ECFRBRWS>
<AMDDATE>Dec. 29, 2024</AMDDATE>

<DIV1 N="{title_number}" NODE="{title_number}:1" TYPE="TITLE">
<HEAD>Title {title_number}—Test Provisions--Volume 1</HEAD>

<DIV3 N="I" NODE="{title_number}:1.0.1" TYPE="CHAPTER">
<HEAD>CHAPTER I—TEST ADMINISTRATIVE COMMITTEE</HEAD>

<DIV4 N="A" NODE="{title_number}:1.0.1.1" TYPE="SUBCHAP">
<HEAD>SUBCHAPTER A—GENERAL</HEAD>

<DIV5 N="1" NODE="{title_number}:1.0.1.1.1" TYPE="PART">
<HEAD>PART 1—DEFINITIONS</HEAD>
<AUTH>
<HED>Authority:</HED>
<PSPACE>44 U.S.C. 1506; sec. 6, E.O. 10530, 19 FR 2709.</PSPACE>
</AUTH>

<DIV8 N="§ 1.1" NODE="{title_number}:1.0.1.1.1.0.1.1" TYPE="SECTION">
<HEAD>§ 1.1 Definitions.</HEAD>
<P>As used in this chapter, unless the context requires otherwise—</P>
<P><I>Administrative Committee</I> means the Administrative Committee of the Federal Register established under section 1506 of title 44, United States Code;</P>
<P><I>Director</I> means the Director of the Federal Register;</P>
<P><I>Document</I> means a Presidential proclamation or Executive order;</P>
</DIV8>

<DIV8 N="§ 1.2" NODE="{title_number}:1.0.1.1.1.0.1.2" TYPE="SECTION">
<HEAD>§ 1.2 Scope.</HEAD>
<P>This part establishes general definitions and scope for regulatory procedures.</P>
<P>(a) <I>General application.</I> These definitions apply throughout this title unless otherwise specified.</P>
<P>(b) <I>Specific exceptions.</I> Certain sections may provide alternative definitions where context requires.</P>
</DIV8>

</DIV5>

<DIV5 N="2" NODE="{title_number}:1.0.1.1.2" TYPE="PART">
<HEAD>PART 2—GENERAL INFORMATION</HEAD>
<AUTH>
<HED>Authority:</HED>
<PSPACE>44 U.S.C. 1506, 1510.</PSPACE>
</AUTH>
<SOURCE>
<HED>Source:</HED>
<PSPACE>37 FR 23607, Nov. 4, 1972, unless otherwise noted.</PSPACE>
</SOURCE>

<DIV8 N="§ 2.1" NODE="{title_number}:1.0.1.1.2.0.1.1" TYPE="SECTION">
<HEAD>§ 2.1 Purpose and scope.</HEAD>
<P>(a) This chapter sets forth the policies, procedures, and delegations under which the Administrative Committee operates.</P>
<P>(b) The provisions apply to all federal agencies unless specifically exempted.</P>
</DIV8>

</DIV5>

</DIV4>

<DIV4 N="B" NODE="{title_number}:1.0.1.2" TYPE="SUBCHAP">
<HEAD>SUBCHAPTER B—PROCEDURES</HEAD>

<DIV5 N="10" NODE="{title_number}:1.0.1.2.1" TYPE="PART">
<HEAD>PART 10—PROCEDURES</HEAD>

<DIV8 N="§ 10.1" NODE="{title_number}:1.0.1.2.1.0.1.1" TYPE="SECTION">
<HEAD>§ 10.1 General procedures.</HEAD>
<P>This section establishes general procedural requirements.</P>
</DIV8>

</DIV5>

</DIV4>

</DIV3>

<DIV3 N="II" NODE="{title_number}:1.0.2" TYPE="CHAPTER">
<HEAD>CHAPTER II—TEST OFFICE OF THE FEDERAL REGISTER</HEAD>

<DIV5 N="50" NODE="{title_number}:1.0.2.1" TYPE="PART">
<HEAD>PART 50—SPECIAL PROVISIONS</HEAD>

<DIV8 N="§ 50.1" NODE="{title_number}:1.0.2.1.0.1.1" TYPE="SECTION">
<HEAD>§ 50.1 Special requirements.</HEAD>
<P>This section contains special requirements for federal agencies.</P>
<P>These requirements are in addition to general provisions in other parts.</P>
</DIV8>

</DIV5>

</DIV3>

</DIV1>

</ECFRBRWS>
</BODY>
</TEXT>
</DLPSTEXTCLASS>'''
        
        xml_file = self.test_dir / f"test_title_{title_number}.xml"
        xml_file.write_text(xml_content)
        return xml_file
    
    def test_parse_complete_xml_structure(self):
        """Test parsing a complete XML structure"""
        xml_file = self.create_sample_xml(1)
        
        # Parse the XML
        records_processed = self.scraper.parse_title_xml(xml_file, 1)
        
        # Should have processed multiple sections
        self.assertGreater(records_processed, 0)
        self.assertEqual(records_processed, 5)  # 5 sections in our test XML
        
        # Verify database contents
        stats = self.db.get_database_stats()
        self.assertEqual(stats['titles'], 1)
        self.assertEqual(stats['chapters'], 2)  # Chapter I and II
        self.assertEqual(stats['subchapters'], 2)  # Subchapter A and B
        self.assertEqual(stats['parts'], 4)  # Parts 1, 2, 10, 50
        self.assertEqual(stats['sections'], 5)  # 5 sections total
    
    def test_parse_title_extraction(self):
        """Test title name extraction from XML"""
        xml_file = self.create_sample_xml(5)
        
        self.scraper.parse_title_xml(xml_file, 5)
        
        # Check title was created correctly
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT title_name FROM titles WHERE title_number = ?", (5,))
        row = cursor.fetchone()
        self.assertIn("Title 5—Test Provisions", row['title_name'])
    
    def test_parse_chapter_extraction(self):
        """Test chapter extraction from XML"""
        xml_file = self.create_sample_xml(1)
        
        self.scraper.parse_title_xml(xml_file, 1)
        
        # Check chapters were created
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT chapter_number, chapter_name FROM chapters ORDER BY chapter_number")
        chapters = cursor.fetchall()
        
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0]['chapter_number'], "I")
        self.assertIn("TEST ADMINISTRATIVE COMMITTEE", chapters[0]['chapter_name'])
        self.assertEqual(chapters[1]['chapter_number'], "II")
        self.assertIn("TEST OFFICE OF THE FEDERAL REGISTER", chapters[1]['chapter_name'])
    
    def test_parse_subchapter_extraction(self):
        """Test subchapter extraction from XML"""
        xml_file = self.create_sample_xml(1)
        
        self.scraper.parse_title_xml(xml_file, 1)
        
        # Check subchapters were created
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT subchapter_letter, subchapter_name FROM subchapters ORDER BY subchapter_letter")
        subchapters = cursor.fetchall()
        
        self.assertEqual(len(subchapters), 2)
        self.assertEqual(subchapters[0]['subchapter_letter'], "A")
        self.assertIn("GENERAL", subchapters[0]['subchapter_name'])
        self.assertEqual(subchapters[1]['subchapter_letter'], "B")
        self.assertIn("PROCEDURES", subchapters[1]['subchapter_name'])
    
    def test_parse_part_extraction(self):
        """Test part extraction from XML"""
        xml_file = self.create_sample_xml(1)
        
        self.scraper.parse_title_xml(xml_file, 1)
        
        # Check parts were created
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT part_number, part_name, authority_citation, source_citation 
            FROM parts ORDER BY part_number
        """)
        parts = cursor.fetchall()
        
        self.assertEqual(len(parts), 4)
        
        # Part 1
        self.assertEqual(parts[0]['part_number'], 1)
        self.assertIn("DEFINITIONS", parts[0]['part_name'])
        self.assertIn("44 U.S.C. 1506", parts[0]['authority_citation'])
        
        # Part 2
        self.assertEqual(parts[1]['part_number'], 2)
        self.assertIn("GENERAL INFORMATION", parts[1]['part_name'])
        self.assertIn("44 U.S.C. 1506, 1510", parts[1]['authority_citation'])
        self.assertIn("37 FR 23607", parts[1]['source_citation'])
    
    def test_parse_section_extraction(self):
        """Test section extraction from XML"""
        xml_file = self.create_sample_xml(1)
        
        self.scraper.parse_title_xml(xml_file, 1)
        
        # Check sections were created
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT section_number, section_heading, section_content, xml_node_id
            FROM sections ORDER BY section_number
        """)
        sections = cursor.fetchall()
        
        self.assertEqual(len(sections), 5)
        
        # Section 1.1
        section_1_1 = sections[0]
        self.assertEqual(section_1_1['section_number'], "1.1")
        self.assertEqual(section_1_1['section_heading'], "Definitions.")
        self.assertIn("Administrative Committee", section_1_1['section_content'])
        self.assertIn("Director", section_1_1['section_content'])
        self.assertIn("Document", section_1_1['section_content'])
        self.assertIn("1:1.0.1.1.1.0.1.1", section_1_1['xml_node_id'])
        
        # Section 1.2
        section_1_2 = sections[1]
        self.assertEqual(section_1_2['section_number'], "1.2")
        self.assertEqual(section_1_2['section_heading'], "Scope.")
        self.assertIn("general definitions", section_1_2['section_content'])
        self.assertIn("General application", section_1_2['section_content'])
        self.assertIn("Specific exceptions", section_1_2['section_content'])
        
        # Section 2.1
        section_2_1 = sections[2]
        self.assertEqual(section_2_1['section_number'], "2.1")
        self.assertEqual(section_2_1['section_heading'], "Purpose and scope.")
        self.assertIn("policies, procedures, and delegations", section_2_1['section_content'])
        
        # Section 10.1
        section_10_1 = sections[3]
        self.assertEqual(section_10_1['section_number'], "10.1")
        self.assertEqual(section_10_1['section_heading'], "General procedures.")
        
        # Section 50.1
        section_50_1 = sections[4]
        self.assertEqual(section_50_1['section_number'], "50.1")
        self.assertEqual(section_50_1['section_heading'], "Special requirements.")
        self.assertIn("special requirements for federal agencies", section_50_1['section_content'])
    
    def test_parse_content_formatting(self):
        """Test that section content is properly formatted"""
        xml_file = self.create_sample_xml(1)
        
        self.scraper.parse_title_xml(xml_file, 1)
        
        # Get section 1.2 which has structured content
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT section_content FROM sections WHERE section_number = ?", ("1.2",))
        content = cursor.fetchone()['section_content']
        
        # Should contain both paragraphs
        self.assertIn("establishes general definitions", content)
        self.assertIn("General application", content)
        self.assertIn("Specific exceptions", content)
        
        # Paragraphs should be separated by double newlines
        self.assertIn("\n\n", content)
    
    def test_parse_hierarchical_relationships(self):
        """Test that hierarchical relationships are maintained"""
        xml_file = self.create_sample_xml(1)
        
        self.scraper.parse_title_xml(xml_file, 1)
        
        # Verify relationships using JOINs
        cursor = self.db.connection.cursor()
        
        # Test title -> chapter -> subchapter -> part -> section chain
        cursor.execute("""
            SELECT t.title_name, c.chapter_name, sc.subchapter_name, p.part_name, s.section_heading
            FROM sections s
            JOIN parts p ON s.part_id = p.id
            JOIN subchapters sc ON p.subchapter_id = sc.id
            JOIN chapters c ON sc.chapter_id = c.id
            JOIN titles t ON c.title_id = t.id
            WHERE s.section_number = '1.1'
        """)
        
        row = cursor.fetchone()
        self.assertIn("Test Provisions", row[0])  # title
        self.assertIn("ADMINISTRATIVE COMMITTEE", row[1])  # chapter
        self.assertIn("GENERAL", row[2])  # subchapter
        self.assertIn("DEFINITIONS", row[3])  # part
        self.assertEqual("Definitions.", row[4])  # section
        
        # Test direct chapter -> part relationship (no subchapter)
        cursor.execute("""
            SELECT t.title_name, c.chapter_name, p.part_name, s.section_heading
            FROM sections s
            JOIN parts p ON s.part_id = p.id
            JOIN chapters c ON p.chapter_id = c.id
            JOIN titles t ON c.title_id = t.id
            WHERE s.section_number = '50.1' AND p.subchapter_id IS NULL
        """)
        
        row = cursor.fetchone()
        self.assertIn("Test Provisions", row[0])  # title
        self.assertIn("OFFICE OF THE FEDERAL REGISTER", row[1])  # chapter
        self.assertIn("SPECIAL PROVISIONS", row[2])  # part
        self.assertEqual("Special requirements.", row[3])  # section
    
    def test_parse_malformed_xml(self):
        """Test handling of malformed XML"""
        malformed_xml = '''<?xml version="1.0"?>
        <DLPSTEXTCLASS>
            <unclosed_tag>
            <BODY>Content</BODY>
        </DLPSTEXTCLASS>'''
        
        xml_file = self.test_dir / "malformed.xml"
        xml_file.write_text(malformed_xml)
        
        # Should handle gracefully and update metadata as failed
        with self.assertRaises(Exception):
            self.scraper.parse_title_xml(xml_file, 99)
        
        # Check that metadata shows failure
        metadata = self.db.get_scraping_metadata(99)
        self.assertEqual(metadata['scraping_status'], 'failed')
        self.assertIsNotNone(metadata['error_message'])
    
    def test_parse_empty_xml(self):
        """Test handling of empty/minimal XML"""
        empty_xml = '''<?xml version="1.0"?>
        <DLPSTEXTCLASS>
            <HEADER><TITLE>Empty Title</TITLE></HEADER>
            <TEXT><BODY></BODY></TEXT>
        </DLPSTEXTCLASS>'''
        
        xml_file = self.test_dir / "empty.xml"
        xml_file.write_text(empty_xml)
        
        records_processed = self.scraper.parse_title_xml(xml_file, 98)
        
        # Should process successfully but with 0 records
        self.assertEqual(records_processed, 0)
        
        # Should still create the title
        stats = self.db.get_database_stats()
        self.assertEqual(stats['titles'], 1)
        self.assertEqual(stats['sections'], 0)


class TestXMLElementParsing(unittest.TestCase):
    """Test individual XML element parsing functions"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_ecfr.db"
        self.db = ECFRDatabase(self.db_path)
        self.db.connect()
        self.db.initialize_schema()
        
        self.scraper = ECFRScraper(self.db)
    
    def tearDown(self):
        """Clean up test environment"""
        self.scraper.close()
        self.db.disconnect()
        shutil.rmtree(self.test_dir)
    
    def test_extract_section_content_complex(self):
        """Test extraction of complex section content"""
        xml_content = '''
        <DIV8 TYPE="SECTION">
            <HEAD>§ 1.1 Test Section</HEAD>
            <P>First paragraph with <I>italics</I> and <E T="03">emphasis</E>.</P>
            <P>(a) <I>Subsection a.</I> Content of subsection a with references.</P>
            <P>(1) <I>Paragraph 1.</I> First numbered paragraph.</P>
            <P>(2) <I>Paragraph 2.</I> Second numbered paragraph with more detail.</P>
            <P>(b) <I>Subsection b.</I> Content of subsection b.</P>
            <P>Final paragraph after subsections.</P>
        </DIV8>
        '''
        
        element = ET.fromstring(xml_content)
        content = self.scraper._extract_section_content(element)
        
        self.assertIn("First paragraph with italics", content)
        self.assertIn("Subsection a", content)
        self.assertIn("First numbered paragraph", content)
        self.assertIn("Second numbered paragraph", content)
        self.assertIn("Subsection b", content)
        self.assertIn("Final paragraph after", content)
        
        # Should have paragraph breaks
        paragraphs = content.split('\n\n')
        self.assertGreater(len(paragraphs), 5)
    
    def test_extract_authority_complex(self):
        """Test extraction of complex authority citations"""
        xml_content = '''
        <PART>
            <AUTH>
                <HED>Authority:</HED>
                <PSPACE>Secs. 1, 2, 3, and 5 of the Act of June 25, 1938, as amended (15 U.S.C. 717-717w); 
                sec. 402(f) of the Department of Energy Organization Act (42 U.S.C. 7172(f)); 
                3 CFR, 1977 Comp., p. 69; E.O. 12009, 42 FR 46267.</PSPACE>
            </AUTH>
        </PART>
        '''
        
        element = ET.fromstring(xml_content)
        authority = self.scraper._extract_authority(element)
        
        self.assertIn("15 U.S.C. 717-717w", authority)
        self.assertIn("42 U.S.C. 7172(f)", authority)
        self.assertIn("3 CFR, 1977 Comp.", authority)
        self.assertIn("E.O. 12009", authority)
    
    def test_extract_source_complex(self):
        """Test extraction of complex source citations"""
        xml_content = '''
        <PART>
            <SOURCE>
                <HED>Source:</HED>
                <PSPACE>Order 154, 18 FR 4813, Aug. 20, 1953, unless otherwise noted. 
                Redesignated at 47 FR 13327, Mar. 30, 1982.</PSPACE>
            </SOURCE>
        </PART>
        '''
        
        element = ET.fromstring(xml_content)
        source = self.scraper._extract_source(element)
        
        self.assertIn("Order 154", source)
        self.assertIn("18 FR 4813", source)
        self.assertIn("Aug. 20, 1953", source)
        self.assertIn("Redesignated at 47 FR 13327", source)
        self.assertIn("Mar. 30, 1982", source)


if __name__ == '__main__':
    unittest.main()