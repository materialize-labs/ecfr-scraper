"""
eCFR XML scraper and parser
Downloads and processes CFR XML files from GovInfo bulk data repository
"""

import requests
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import re
from urllib.parse import urljoin
from datetime import datetime
import logging
from tqdm import tqdm

from config.settings import (
    GOVINFO_BASE_URL, CFR_TITLES, REQUEST_TIMEOUT, MAX_RETRIES, 
    RETRY_DELAY, USER_AGENT, REQUESTS_PER_SECOND, DELAY_BETWEEN_REQUESTS,
    DATA_DIR, VALIDATE_XML, SKIP_EXISTING, CHUNK_SIZE
)
from src.database import ECFRDatabase, calculate_file_hash, DatabaseError

logger = logging.getLogger(__name__)


class ScrapingError(Exception):
    """Custom exception for scraping operations"""
    pass


class ECFRScraper:
    """Main scraper class for eCFR data"""
    
    def __init__(self, database: ECFRDatabase):
        """Initialize scraper with database connection"""
        self.database = database
        self.session = self._create_session()
        self.download_dir = DATA_DIR / "xml_files"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def _create_session(self) -> requests.Session:
        """Create configured requests session"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'application/xml, text/xml, */*',
            'Accept-Encoding': 'gzip, deflate'
        })
        return session
    
    def _make_request(self, url: str, stream: bool = False) -> requests.Response:
        """Make HTTP request with retry logic"""
        last_exception = None
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"Requesting {url} (attempt {attempt + 1})")
                
                response = self.session.get(
                    url, 
                    timeout=REQUEST_TIMEOUT,
                    stream=stream
                )
                response.raise_for_status()
                
                # Rate limiting
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
                return response
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    
        raise ScrapingError(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {last_exception}")
    
    def download_title_xml(self, title_number: int, force_download: bool = False) -> Optional[Path]:
        """Download XML file for a specific CFR title"""
        try:
            xml_url = f"{GOVINFO_BASE_URL}/title-{title_number}/ECFR-title{title_number}.xml"
            xml_file = self.download_dir / f"ECFR-title{title_number}.xml"
            
            # Check if file exists and skip if not forcing
            if xml_file.exists() and not force_download:
                if SKIP_EXISTING:
                    logger.info(f"XML file for title {title_number} already exists, skipping download")
                    return xml_file
            
            logger.info(f"Downloading XML for CFR Title {title_number}")
            
            # Download with progress bar
            response = self._make_request(xml_url, stream=True)
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(xml_file, 'wb') as f:
                if total_size > 0:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Title {title_number}") as pbar:
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                else:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
            
            # Validate XML if enabled
            if VALIDATE_XML:
                if not self._validate_xml(xml_file):
                    raise ScrapingError(f"Invalid XML file for title {title_number}")
            
            logger.info(f"Downloaded XML for title {title_number}: {xml_file}")
            return xml_file
            
        except Exception as e:
            logger.error(f"Error downloading title {title_number}: {e}")
            raise ScrapingError(f"Download failed for title {title_number}: {e}")
    
    def _validate_xml(self, xml_file: Path) -> bool:
        """Validate XML file structure"""
        try:
            ET.parse(xml_file)
            return True
        except ET.ParseError as e:
            logger.error(f"XML validation failed for {xml_file}: {e}")
            return False
    
    def parse_title_xml(self, xml_file: Path, title_number: int) -> int:
        """Parse XML file and extract CFR structure"""
        try:
            logger.info(f"Parsing XML file: {xml_file}")
            
            # Update scraping metadata
            file_size = xml_file.stat().st_size
            file_hash = calculate_file_hash(xml_file)
            
            self.database.update_scraping_metadata(
                title_number, 'in_progress', file_size, file_hash
            )
            
            # Parse XML
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            records_processed = 0
            
            # Extract title information
            title_element = root.find('.//HEAD')
            if title_element is None:
                title_element = root.find('.//TITLE')
            title_name = self._clean_text(title_element.text) if title_element is not None else f"Title {title_number}"
            
            title_id = self.database.get_or_create_title(title_number, title_name)
            
            # Process chapters (DIV3 elements with TYPE="CHAPTER")
            for chapter_elem in root.findall('.//DIV3[@TYPE="CHAPTER"]'):
                chapter_id = self._process_chapter(chapter_elem, title_id)
                if chapter_id:
                    records_processed += self._process_chapter_content(chapter_elem, chapter_id)
            
            # Update successful completion
            self.database.update_scraping_metadata(
                title_number, 'completed', file_size, file_hash, None, records_processed
            )
            
            # Commit all changes for this title
            self.database.connection.commit()
            
            logger.info(f"Successfully parsed title {title_number}: {records_processed} records")
            return records_processed
            
        except Exception as e:
            logger.error(f"Error parsing XML file {xml_file}: {e}")
            self.database.update_scraping_metadata(
                title_number, 'failed', None, None, str(e), 0
            )
            raise ScrapingError(f"XML parsing failed: {e}")
    
    def _process_chapter(self, chapter_elem: ET.Element, title_id: int) -> Optional[int]:
        """Process a chapter element"""
        try:
            # Extract chapter number and name from HEAD element
            chapter_hd = chapter_elem.find('HEAD')
            if chapter_hd is None:
                return None
                
            chapter_text = self._clean_text(chapter_hd.text) if chapter_hd.text else ""
            
            # Parse chapter number (Roman numerals) - handle different formats
            chapter_match = re.search(r'CHAPTER\s+([IVXLCDM]+)', chapter_text, re.IGNORECASE)
            if not chapter_match:
                # Try to get from the N attribute
                chapter_number = chapter_elem.get('N')
                if not chapter_number:
                    logger.warning(f"Could not parse chapter number from: {chapter_text}")
                    return None
            else:
                chapter_number = chapter_match.group(1)
            
            chapter_name = chapter_text
            
            return self.database.get_or_create_chapter(title_id, chapter_number, chapter_name)
            
        except Exception as e:
            logger.error(f"Error processing chapter: {e}")
            return None
    
    def _process_chapter_content(self, chapter_elem: ET.Element, chapter_id: int) -> int:
        """Process all content within a chapter"""
        records_count = 0
        
        # Process subchapters (DIV4 elements with TYPE="SUBCHAP")
        for subchapter_elem in chapter_elem.findall('.//DIV4[@TYPE="SUBCHAP"]'):
            subchapter_id = self._process_subchapter(subchapter_elem, chapter_id)
            if subchapter_id:
                records_count += self._process_subchapter_content(subchapter_elem, chapter_id, subchapter_id)
        
        # Process parts that are directly under chapter (no subchapter) - DIV5 with TYPE="PART"
        for part_elem in chapter_elem.findall('./DIV5[@TYPE="PART"]'):
            records_count += self._process_part(part_elem, chapter_id, None)
        
        return records_count
    
    def _process_subchapter(self, subchapter_elem: ET.Element, chapter_id: int) -> Optional[int]:
        """Process a subchapter element"""
        try:
            subchap_hd = subchapter_elem.find('HEAD')
            if subchap_hd is None:
                return None
                
            subchapter_text = self._clean_text(subchap_hd.text) if subchap_hd.text else ""
            
            # Parse subchapter letter - handle different formats
            subchapter_match = re.search(r'SUBCHAPTER\s+([A-Z])', subchapter_text, re.IGNORECASE)
            if not subchapter_match:
                # Try to get from the N attribute
                subchapter_letter = subchapter_elem.get('N')
                if not subchapter_letter:
                    logger.warning(f"Could not parse subchapter letter from: {subchapter_text}")
                    return None
            else:
                subchapter_letter = subchapter_match.group(1)
            
            subchapter_name = subchapter_text
            
            return self.database.get_or_create_subchapter(chapter_id, subchapter_letter, subchapter_name)
            
        except Exception as e:
            logger.error(f"Error processing subchapter: {e}")
            return None
    
    def _process_subchapter_content(self, subchapter_elem: ET.Element, chapter_id: int, subchapter_id: int) -> int:
        """Process all parts within a subchapter"""
        records_count = 0
        
        for part_elem in subchapter_elem.findall('.//DIV5[@TYPE="PART"]'):
            records_count += self._process_part(part_elem, chapter_id, subchapter_id)
            
        return records_count
    
    def _process_part(self, part_elem: ET.Element, chapter_id: int, subchapter_id: Optional[int]) -> int:
        """Process a part element"""
        try:
            # Extract part number and name from HEAD element
            part_hd = part_elem.find('HEAD')
            if part_hd is None:
                return 0
                
            part_text = self._clean_text(part_hd.text) if part_hd.text else ""
            
            # Parse part number - handle different formats
            part_match = re.search(r'PART\s+(\d+)', part_text, re.IGNORECASE)
            if not part_match:
                # Try to get from the N attribute
                part_number_str = part_elem.get('N')
                if part_number_str and part_number_str.isdigit():
                    part_number = int(part_number_str)
                else:
                    logger.warning(f"Could not parse part number from: {part_text}")
                    return 0
            else:
                part_number = int(part_match.group(1))
            
            part_name = part_text
            
            # Extract authority and source
            authority = self._extract_authority(part_elem)
            source = self._extract_source(part_elem)
            
            part_id = self.database.get_or_create_part(
                chapter_id, subchapter_id, part_number, part_name, authority, source
            )
            
            # Process sections (DIV8 elements with TYPE="SECTION")
            sections_count = 0
            for section_elem in part_elem.findall('.//DIV8[@TYPE="SECTION"]'):
                if self._process_section(section_elem, part_id):
                    sections_count += 1
            
            logger.debug(f"Processed part {part_number}: {sections_count} sections")
            return sections_count
            
        except Exception as e:
            logger.error(f"Error processing part: {e}")
            return 0
    
    def _process_section(self, section_elem: ET.Element, part_id: int) -> bool:
        """Process a section element"""
        try:
            # Extract section number from N attribute or HEAD element
            section_number = section_elem.get('N', '')
            if section_number.startswith('§ '):
                section_number = section_number[2:].strip()
            
            # If no N attribute, try to extract from HEAD
            if not section_number:
                head_elem = section_elem.find('HEAD')
                if head_elem is not None:
                    head_text = self._clean_text(head_elem.text) if head_elem.text else ""
                    section_match = re.search(r'§\s*([\d.]+)', head_text)
                    if section_match:
                        section_number = section_match.group(1)
                
            if not section_number:
                logger.warning("Could not extract section number")
                return False
            
            # Extract section heading from HEAD element
            head_elem = section_elem.find('HEAD')
            if head_elem is not None:
                head_text = self._clean_text(head_elem.text) if head_elem.text else ""
                # Remove the section number part to get just the heading
                section_heading = re.sub(r'§\s*[\d.]+\s*', '', head_text).strip()
            else:
                section_heading = ""
            
            # Extract section content
            section_content = self._extract_section_content(section_elem)
            
            # Extract authority and source
            authority = self._extract_authority(section_elem)
            source = self._extract_source(section_elem)
            
            # Get XML node ID if available
            xml_node_id = section_elem.get('NODE', None)
            
            self.database.insert_section(
                part_id, section_number, section_heading, section_content,
                authority, source, xml_node_id
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing section: {e}")
            return False
    
    def _extract_section_content(self, section_elem: ET.Element) -> str:
        """Extract full text content from a section"""
        content_parts = []
        
        # Get all paragraph elements
        for para_elem in section_elem.findall('.//P'):
            para_text = self._extract_element_text(para_elem)
            if para_text.strip():
                content_parts.append(para_text.strip())
        
        return '\n\n'.join(content_parts)
    
    def _extract_element_text(self, element: ET.Element) -> str:
        """Extract text from element including nested elements"""
        if element is None:
            return ""
            
        # Get direct text
        text_parts = [element.text or ""]
        
        # Get text from all child elements
        for child in element:
            text_parts.append(self._extract_element_text(child))
            text_parts.append(child.tail or "")
        
        return " ".join(text_parts).strip()
    
    def _extract_authority(self, element: ET.Element) -> Optional[str]:
        """Extract authority citation from element"""
        auth_elem = element.find('.//AUTH')
        if auth_elem is not None:
            return self._clean_text(self._extract_element_text(auth_elem))
        return None
    
    def _extract_source(self, element: ET.Element) -> Optional[str]:
        """Extract source citation from element"""
        source_elem = element.find('.//SOURCE')
        if source_elem is not None:
            return self._clean_text(self._extract_element_text(source_elem))
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
            
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common XML artifacts
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&apos;', "'")
        
        return text.strip()
    
    def scrape_all_titles(self, title_numbers: Optional[List[int]] = None, 
                         force_download: bool = False) -> Dict[int, int]:
        """Scrape all specified CFR titles"""
        titles_to_process = title_numbers or CFR_TITLES
        results = {}
        
        logger.info(f"Starting scrape of {len(titles_to_process)} CFR titles")
        
        with tqdm(total=len(titles_to_process), desc="Processing titles") as pbar:
            for title_number in titles_to_process:
                try:
                    pbar.set_description(f"Processing Title {title_number}")
                    
                    # Download XML file
                    xml_file = self.download_title_xml(title_number, force_download)
                    if xml_file is None:
                        logger.error(f"Failed to download title {title_number}")
                        results[title_number] = 0
                        continue
                    
                    # Parse and store data
                    records_count = self.parse_title_xml(xml_file, title_number)
                    results[title_number] = records_count
                    
                    logger.info(f"Completed title {title_number}: {records_count} records")
                    
                except Exception as e:
                    logger.error(f"Failed to process title {title_number}: {e}")
                    results[title_number] = 0
                
                finally:
                    pbar.update(1)
        
        total_records = sum(results.values())
        successful_titles = sum(1 for count in results.values() if count > 0)
        
        logger.info(f"Scraping completed: {successful_titles}/{len(titles_to_process)} titles, "
                   f"{total_records} total records")
        
        return results
    
    def check_for_updates(self, title_number: int) -> bool:
        """Check if a title has been updated since last scrape"""
        try:
            metadata = self.database.get_scraping_metadata(title_number)
            if not metadata:
                return True  # Never scraped before
            
            # Download current file to compare hash
            xml_file = self.download_title_xml(title_number, force_download=True)
            if not xml_file:
                return False
            
            current_hash = calculate_file_hash(xml_file)
            return current_hash != metadata.get('file_hash')
            
        except Exception as e:
            logger.error(f"Error checking updates for title {title_number}: {e}")
            return True  # Assume updated on error
    
    def incremental_update(self) -> Dict[int, int]:
        """Perform incremental update of changed titles only"""
        logger.info("Starting incremental update check")
        
        updated_titles = []
        for title_number in CFR_TITLES:
            if self.check_for_updates(title_number):
                updated_titles.append(title_number)
        
        if not updated_titles:
            logger.info("No titles need updating")
            return {}
        
        logger.info(f"Found {len(updated_titles)} titles to update: {updated_titles}")
        return self.scrape_all_titles(updated_titles, force_download=True)
    
    def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close()