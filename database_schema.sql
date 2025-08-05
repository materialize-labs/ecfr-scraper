-- Electronic Code of Federal Regulations (eCFR) Database Schema
-- SQLite database schema for storing complete CFR hierarchy and content

-- Create tables in dependency order

-- Titles table (top level - CFR Title 1-50)
CREATE TABLE titles (
    id INTEGER PRIMARY KEY,
    title_number INTEGER UNIQUE NOT NULL,
    title_name TEXT NOT NULL,
    last_updated DATE,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chapters table (Chapter I, II, III, etc.)
CREATE TABLE chapters (
    id INTEGER PRIMARY KEY,
    title_id INTEGER NOT NULL,
    chapter_number TEXT NOT NULL, -- Roman numerals like 'I', 'II', 'III'
    chapter_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (title_id) REFERENCES titles(id) ON DELETE CASCADE,
    UNIQUE(title_id, chapter_number)
);

-- Subchapters table (Subchapter A, B, C, etc.)
CREATE TABLE subchapters (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER NOT NULL,
    subchapter_letter TEXT NOT NULL, -- 'A', 'B', 'C', etc.
    subchapter_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    UNIQUE(chapter_id, subchapter_letter)
);

-- Parts table (Part 1, 2, 3, etc.)
CREATE TABLE parts (
    id INTEGER PRIMARY KEY,
    subchapter_id INTEGER,
    chapter_id INTEGER NOT NULL, -- Some parts may not have subchapters
    part_number INTEGER NOT NULL,
    part_name TEXT NOT NULL,
    authority_citation TEXT,
    source_citation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subchapter_id) REFERENCES subchapters(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    UNIQUE(chapter_id, part_number)
);

-- Sections table (§ 1.1, 1.2, etc.)
CREATE TABLE sections (
    id INTEGER PRIMARY KEY,
    part_id INTEGER NOT NULL,
    section_number TEXT NOT NULL, -- e.g., '1.1', '1.2', '100.1'
    section_heading TEXT NOT NULL,
    section_content TEXT, -- Full text content
    authority_citation TEXT,
    source_citation TEXT,
    effective_date DATE,
    xml_node_id TEXT, -- For tracking XML structure
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE,
    UNIQUE(part_id, section_number)
);

-- Subsections/Paragraphs table (for complex nested content)
CREATE TABLE paragraphs (
    id INTEGER PRIMARY KEY,
    section_id INTEGER NOT NULL,
    parent_paragraph_id INTEGER, -- For nested paragraphs
    paragraph_marker TEXT, -- (a), (1), (i), etc.
    paragraph_content TEXT NOT NULL,
    paragraph_order INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_paragraph_id) REFERENCES paragraphs(id) ON DELETE CASCADE
);

-- Cross-references table (for citations between sections)
CREATE TABLE cross_references (
    id INTEGER PRIMARY KEY,
    source_section_id INTEGER NOT NULL,
    target_section_id INTEGER,
    citation_text TEXT NOT NULL,
    citation_type TEXT, -- 'internal', 'external', 'usc', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_section_id) REFERENCES sections(id) ON DELETE CASCADE,
    FOREIGN KEY (target_section_id) REFERENCES sections(id) ON DELETE CASCADE
);

-- Amendments/Changes tracking table
CREATE TABLE amendments (
    id INTEGER PRIMARY KEY,
    section_id INTEGER NOT NULL,
    amendment_date DATE NOT NULL,
    federal_register_citation TEXT,
    amendment_type TEXT, -- 'added', 'revised', 'removed', 'redesignated'
    amendment_description TEXT,
    effective_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
);

-- Scraping metadata table
CREATE TABLE scraping_metadata (
    id INTEGER PRIMARY KEY,
    title_number INTEGER NOT NULL,
    last_scraped TIMESTAMP NOT NULL,
    file_size INTEGER,
    file_hash TEXT, -- MD5/SHA256 hash for change detection
    scraping_status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed'
    error_message TEXT,
    records_processed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title_number)
);

-- Create indexes for performance
CREATE INDEX idx_titles_number ON titles(title_number);
CREATE INDEX idx_chapters_title ON chapters(title_id);
CREATE INDEX idx_subchapters_chapter ON subchapters(chapter_id);
CREATE INDEX idx_parts_chapter ON parts(chapter_id);
CREATE INDEX idx_parts_subchapter ON parts(subchapter_id);
CREATE INDEX idx_sections_part ON sections(part_id);
CREATE INDEX idx_sections_number ON sections(section_number);
CREATE INDEX idx_paragraphs_section ON paragraphs(section_id);
CREATE INDEX idx_paragraphs_order ON paragraphs(paragraph_order);
CREATE INDEX idx_crossrefs_source ON cross_references(source_section_id);
CREATE INDEX idx_amendments_section ON amendments(section_id);
CREATE INDEX idx_amendments_date ON amendments(amendment_date);
CREATE INDEX idx_scraping_status ON scraping_metadata(scraping_status);

-- Full-text search virtual table for sections content
CREATE VIRTUAL TABLE sections_fts USING fts5(
    section_heading,
    section_content,
    content='sections',
    content_rowid='id'
);

-- Triggers to keep FTS table in sync
CREATE TRIGGER sections_fts_insert AFTER INSERT ON sections BEGIN
    INSERT INTO sections_fts(rowid, section_heading, section_content) 
    VALUES (new.id, new.section_heading, new.section_content);
END;

CREATE TRIGGER sections_fts_update AFTER UPDATE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, section_heading, section_content) 
    VALUES('delete', old.id, old.section_heading, old.section_content);
    INSERT INTO sections_fts(rowid, section_heading, section_content) 
    VALUES (new.id, new.section_heading, new.section_content);
END;

CREATE TRIGGER sections_fts_delete AFTER DELETE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, section_heading, section_content) 
    VALUES('delete', old.id, old.section_heading, old.section_content);
END;

-- Update timestamp triggers
CREATE TRIGGER update_titles_timestamp AFTER UPDATE ON titles FOR EACH ROW BEGIN
    UPDATE titles SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_chapters_timestamp AFTER UPDATE ON chapters FOR EACH ROW BEGIN
    UPDATE chapters SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_subchapters_timestamp AFTER UPDATE ON subchapters FOR EACH ROW BEGIN
    UPDATE subchapters SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_parts_timestamp AFTER UPDATE ON parts FOR EACH ROW BEGIN
    UPDATE parts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_sections_timestamp AFTER UPDATE ON sections FOR EACH ROW BEGIN
    UPDATE sections SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_scraping_metadata_timestamp AFTER UPDATE ON scraping_metadata FOR EACH ROW BEGIN
    UPDATE scraping_metadata SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;