"""
Funding Farm Backend Package

Initializes logging and other global settings.
"""

__version__ = "0.0.1"
__author__ = "Evgeniy"

import logging
import sys
import os
from app.config import settings

# Setup internal logging
# Create the folder if it doesn't exist
if not os.path.exists(settings.LOG_FOLDER):
    os.makedirs(settings.LOG_FOLDER)

# Full path for the log file
log_file_path = os.path.join(settings.LOG_FOLDER, settings.LOG_FILE)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Log level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    handlers=[
        logging.FileHandler(log_file_path),  # Log to file
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Initializing application v{__version__}")