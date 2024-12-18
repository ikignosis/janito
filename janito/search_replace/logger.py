import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configure logging
logger = logging.getLogger("janito.search_replace")
logger.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Create file handler
def setup_file_handler():
    """Setup file handler for logging if .janito directory exists"""
    if Path(".janito").exists():
        fh = logging.FileHandler(".janito/search_logs.txt")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

setup_file_handler()

def log_match(strategy_name: str, file_type: Optional[str] = None):
    """Log successful match with strategy info"""
    msg = f"Match found using {strategy_name}"
    if file_type:
        msg += f" for file type {file_type}"
    logger.info(msg)

def log_failure(file_type: Optional[str] = None):
    """Log failed match attempt"""
    msg = "Failed to match pattern"
    if file_type:
        msg += f" for file type {file_type}"
    logger.warning(msg)