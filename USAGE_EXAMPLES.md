# eCFR Scraper - Usage Examples

This document provides practical examples of how to use the eCFR scraper for various tasks.

## Quick Start

```bash
# 1. Setup the project
python setup.py

# 2. Activate virtual environment
source venv/bin/activate

# 3. Initialize database
python -m src.main init-db

# 4. Scrape a single title for testing
python -m src.main scrape --titles 1

# 5. Check the results
python -m src.main stats
```

## Basic Operations

### Database Management

```bash
# Initialize or recreate database
python -m src.main init-db --force

# Show database statistics
python -m src.main stats

# Create a backup
python -m src.main backup /path/to/backup.db

# Optimize database performance
python -m src.main vacuum
```

### Scraping Operations

```bash
# Scrape all CFR titles (takes several hours)
python -m src.main scrape

# Scrape specific titles
python -m src.main scrape --titles 1,2,3,12,15

# Force re-download and re-process files
python -m src.main scrape --titles 1 --force

# Incremental update (only changed titles)
python -m src.main scrape --incremental

# Check which titles need updates
python -m src.main check-updates
```

### Data Exploration

```bash
# List all scraped titles
python -m src.main list-titles

# Show detailed information for a specific title
python -m src.main list-titles --title 12

# Search regulation content
python -m src.main search "environmental protection"
python -m src.main search "privacy policy" --limit 5
python -m src.main search "definitions" --format json
```

## Advanced Usage

### Debugging and Logging

```bash
# Enable debug logging
python -m src.main --debug scrape --titles 1

# Disable file logging (console only)
python -m src.main --no-log-file stats

# View log files
tail -f logs/ecfr_scraper_$(date +%Y%m%d).log
```

### Production Scenarios

```bash
# Daily update script
python -m src.main scrape --incremental

# Full re-scrape with backup
python -m src.main backup data/ecfr_backup_$(date +%Y%m%d).db
python -m src.main scrape --force

# Monitor scraping progress
python -m src.main --debug scrape --titles 1,2,3 2>&1 | tee scrape.log
```

### Search Examples

```bash
# Find regulations about specific topics
python -m src.main search "federal register"
python -m src.main search "administrative procedure"
python -m src.main search "privacy act"
python -m src.main search "freedom of information"

# Search with different output formats
python -m src.main search "definitions" --format json --limit 10
python -m src.main search "enforcement" --limit 20
```

## Automation Scripts

### Daily Update Script

```bash
#!/bin/bash
# daily_update.sh

source venv/bin/activate

echo "Starting daily eCFR update at $(date)"

# Check for updates
python -m src.main check-updates > update_check.log 2>&1

# Run incremental update if needed
python -m src.main scrape --incremental >> update_check.log 2>&1

# Show final statistics
python -m src.main stats >> update_check.log 2>&1

echo "Daily update completed at $(date)"
```

### Full Scraping Script

```bash
#!/bin/bash
# full_scrape.sh

source venv/bin/activate

echo "Starting full eCFR scrape at $(date)"

# Create backup first
python -m src.main backup "data/backup_$(date +%Y%m%d_%H%M%S).db"

# Run full scrape
python -m src.main scrape --force > full_scrape.log 2>&1

# Optimize database
python -m src.main vacuum >> full_scrape.log 2>&1

# Show final statistics
python -m src.main stats

echo "Full scrape completed at $(date)"
```

## Configuration Examples

### Environment Variables

```bash
# Custom database location
export ECFR_DB_PATH="/custom/path/ecfr.db"

# Custom data directory
export ECFR_DATA_DIR="/custom/data/directory"

# Enable debug mode
export ECFR_DEBUG=1

# Run with custom settings
python -m src.main scrape --titles 1
```

### Batch Processing

```bash
# Process titles in batches
for batch in "1,2,3,4,5" "6,7,8,9,10" "11,12,13,14,15"; do
    echo "Processing batch: $batch"
    python -m src.main scrape --titles $batch
    sleep 60  # Pause between batches
done
```

## Common Use Cases

### Legal Research

```bash
# Search for specific legal concepts
python -m src.main search "due process"
python -m src.main search "administrative law judge"
python -m src.main search "rulemaking procedure"
```

### Compliance Monitoring

```bash
# Monitor specific CFR titles for changes
python -m src.main check-updates --titles 12,15,21,40
python -m src.main scrape --incremental
```

### Data Analysis

```bash
# Export search results for analysis
python -m src.main search "environmental" --format json --limit 1000 > environmental_regs.json
python -m src.main search "safety" --format json --limit 1000 > safety_regs.json
```

## Performance Tips

1. **Use incremental updates** for regular maintenance
2. **Scrape specific titles** instead of all titles during development
3. **Enable debug logging** only when troubleshooting
4. **Run vacuum** periodically to optimize database performance
5. **Create backups** before major operations

## Error Handling

```bash
# Check logs for errors
grep ERROR logs/ecfr_scraper_*.log

# Retry failed titles
python -m src.main scrape --titles 5,12,34 --force

# Reinitialize if database is corrupted
python -m src.main init-db --force
```

## Integration Examples

### With Python Scripts

```python
#!/usr/bin/env python3
import subprocess
import json

# Run search and parse results
result = subprocess.run([
    'python', '-m', 'src.main', 'search', 
    'privacy', '--format', 'json', '--limit', '10'
], capture_output=True, text=True)

if result.returncode == 0:
    data = json.loads(result.stdout)
    for item in data:
        print(f"Section {item['section_number']}: {item['section_heading']}")
```

### With Shell Scripts

```bash
#!/bin/bash
# Monitor specific regulations

KEYWORDS=("privacy" "security" "data protection")

for keyword in "${KEYWORDS[@]}"; do
    echo "Searching for: $keyword"
    python -m src.main search "$keyword" --limit 5
    echo "---"
done
```

This completes the usage examples. The scraper provides flexible options for various use cases from simple searches to complex automated workflows.