"""
Configuration settings for eCFR Scraper
"""

import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DB_DIR = DATA_DIR

# Database settings
DB_PATH = DB_DIR / "ecfr.db"
DB_SCHEMA_PATH = PROJECT_ROOT / "database_schema.sql"

# eCFR data source settings
GOVINFO_BASE_URL = "https://www.govinfo.gov/bulkdata/ECFR"
CFR_TITLES = list(range(1, 51))  # CFR Titles 1-50

# HTTP settings
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
USER_AGENT = "eCFR-Scraper/1.0 (Educational/Research Purpose)"

# Rate limiting
REQUESTS_PER_SECOND = 2
DELAY_BETWEEN_REQUESTS = 0.5  # seconds

# Logging settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Processing settings
BATCH_SIZE = 100
CHUNK_SIZE = 8192  # bytes for file downloads

# Validation settings
VALIDATE_XML = True
SKIP_EXISTING = True  # Skip already processed files if hash matches

# Progress tracking
SHOW_PROGRESS = True
PROGRESS_UPDATE_INTERVAL = 10  # sections

# Environment-specific overrides
if os.getenv("ECFR_DEBUG"):
    LOG_LEVEL = "DEBUG"
    
if os.getenv("ECFR_DB_PATH"):
    DB_PATH = Path(os.getenv("ECFR_DB_PATH"))

if os.getenv("ECFR_DATA_DIR"):
    DATA_DIR = Path(os.getenv("ECFR_DATA_DIR"))
    DB_DIR = DATA_DIR