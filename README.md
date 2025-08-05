# eCFR Scraper

A comprehensive Python tool for scraping and storing Electronic Code of Federal Regulations (eCFR) data from the U.S. Government Publishing Office's bulk data repository.

## Features

- **Complete CFR Coverage**: Scrapes all CFR titles (1-50) with full hierarchical structure
- **Robust Database Schema**: SQLite database with proper relationships and full-text search
- **Incremental Updates**: Smart detection of changed regulations to avoid unnecessary re-processing
- **Error Handling**: Comprehensive error handling with retry logic and detailed logging
- **Progress Tracking**: Real-time progress bars and detailed status reporting
- **Command Line Interface**: Full-featured CLI with multiple operations
- **Data Validation**: XML validation and data integrity checks
- **Production Ready**: Proper logging, configuration management, and optimization

## Quick Start

### 1. Setup

```bash
# Clone or download the project
cd ecfr_scraper

# Run the setup script (creates virtual environment and installs dependencies)
python setup.py

# Activate the virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\\Scripts\\activate  # On Windows
```

### 2. Initialize Database

```bash
# Create the database schema
python -m src.main init-db
```

### 3. Start Scraping

```bash
# Scrape all CFR titles (this will take a while - 50 titles)
python -m src.main scrape

# Or scrape specific titles
python -m src.main scrape --titles 1,2,3

# Force re-download and re-process
python -m src.main scrape --force
```

## Project Structure

```
ecfr_scraper/
├── src/
│   ├── __init__.py
│   ├── main.py          # Command-line interface
│   ├── scraper.py       # Core scraping logic
│   ├── database.py      # Database operations
│   └── logger.py        # Logging configuration
├── config/
│   ├── __init__.py
│   └── settings.py      # Configuration settings
├── data/                # Downloaded XML files and database
├── logs/                # Log files
├── tests/               # Test files (future)
├── database_schema.sql  # SQLite schema definition
├── requirements.txt     # Python dependencies
├── setup.py            # Setup script
└── README.md           # This file
```

## Database Schema

The database stores CFR data in a hierarchical structure:

- **Titles** (1-50): Top-level CFR divisions
- **Chapters** (I, II, III, etc.): Roman numeral subdivisions
- **Subchapters** (A, B, C, etc.): Letter subdivisions
- **Parts** (1, 2, 3, etc.): Numbered regulation groups
- **Sections** (1.1, 1.2, etc.): Individual regulations

Additional tables store metadata, cross-references, amendments, and scraping status.

## Command Reference

### Database Operations

```bash
# Initialize database
python -m src.main init-db

# Show database statistics
python -m src.main stats

# List all titles
python -m src.main list-titles

# Show details for specific title
python -m src.main list-titles --title 12

# Create database backup
python -m src.main backup /path/to/backup.db

# Optimize database
python -m src.main vacuum
```

### Scraping Operations

```bash
# Scrape all titles
python -m src.main scrape

# Scrape specific titles
python -m src.main scrape --titles 1,2,3,10,15

# Force re-download (ignore existing files)
python -m src.main scrape --force

# Incremental update (only changed titles)
python -m src.main scrape --incremental

# Check which titles need updates
python -m src.main check-updates
```

### Search Operations

```bash
# Search regulation content
python -m src.main search "environmental protection"

# Limit results
python -m src.main search "bank" --limit 5

# JSON output
python -m src.main search "privacy" --format json
```

### Debug and Logging

```bash
# Enable debug logging
python -m src.main --debug scrape --titles 1

# Disable file logging
python -m src.main --no-log-file stats
```

## Configuration

The scraper can be configured by modifying `config/settings.py` or using environment variables:

```bash
# Custom database location
export ECFR_DB_PATH="/custom/path/ecfr.db"

# Custom data directory
export ECFR_DATA_DIR="/custom/data/directory"

# Enable debug mode
export ECFR_DEBUG=1
```

## Data Sources

The scraper uses the official U.S. Government Publishing Office (GPO) bulk data repository:
- **Base URL**: https://www.govinfo.gov/bulkdata/ECFR/
- **Format**: XML files (one per CFR title)
- **Update Frequency**: Daily
- **Coverage**: All CFR titles (1-50)

## Performance and Storage

### Typical Data Sizes
- **Database Size**: ~2-5 GB (all titles)
- **XML Files**: ~500 MB total
- **Processing Time**: 2-6 hours (all titles, depends on connection)

### Optimization Features
- WAL mode for concurrent access
- Indexed database for fast queries
- Batch processing with progress tracking
- Rate limiting to respect server resources
- Incremental updates to avoid re-processing

## Development

### Requirements
- Python 3.8+
- Internet connection for downloading CFR data
- ~10 GB free disk space (recommended)

### Adding Features
1. Database changes: Update `database_schema.sql`
2. New scrapers: Extend `ECFRScraper` class
3. CLI commands: Add to `src/main.py`
4. Configuration: Update `config/settings.py`

### Testing
```bash
# Run with a single title for testing
python -m src.main scrape --titles 1 --debug

# Check database integrity
python -m src.main stats
```

## Troubleshooting

### Common Issues

1. **Database not initialized**
   ```bash
   python -m src.main init-db
   ```

2. **Network timeouts**
   - Check internet connection
   - Increase timeout in `config/settings.py`

3. **Disk space**
   - Ensure adequate free space (~10 GB recommended)
   - Use `--incremental` for updates

4. **Permission errors**
   - Check write permissions in project directory
   - Run setup script as appropriate user

### Log Files
- All logs: `logs/ecfr_scraper_YYYYMMDD.log`
- Error logs: `logs/ecfr_scraper_errors_YYYYMMDD.log`

## Legal Notice

This tool is for educational and research purposes. The Electronic Code of Federal Regulations is public domain, but please respect the government servers by:
- Not running excessive concurrent requests
- Using incremental updates when possible
- Following the built-in rate limiting

## License

This project is released under the MIT License. See LICENSE file for details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review log files for detailed error information
3. Open an issue with relevant logs and system information