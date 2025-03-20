import os
import logging
import json
from logging.handlers import TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger

from cdots.core.config import LOGS_FOLDER as LOG_DIR

# Log Directory
os.makedirs(LOG_DIR, exist_ok=True)

# Log file paths
JSON_LOG_FILE = os.path.join(LOG_DIR, "app_log.json")
TEXT_LOG_FILE = os.path.join(LOG_DIR, "app_log.txt")

# Log format for text logs
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Configure Rotating File Handler (Plain Text Logs)
text_handler = TimedRotatingFileHandler(TEXT_LOG_FILE, when="midnight", interval=1, backupCount=7)
text_handler.suffix = "%Y-%m-%d"
text_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Configure Rotating File Handler (JSON Logs)
json_handler = TimedRotatingFileHandler(JSON_LOG_FILE, when="midnight", interval=1, backupCount=7)
json_handler.suffix = "%Y-%m-%d"
json_formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(message)s")
json_handler.setFormatter(json_formatter)

# Standard Python Logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[text_handler, json_handler],
)

# Custom Logger Instance
logger = logging.getLogger("cdots_logger")
logger.setLevel(logging.INFO)

# Add Handlers
logger.addHandler(text_handler)
logger.addHandler(json_handler)
# Include stdout handler if not in production
ENVIRONMENT = os.getenv("environment", "stg")
if ENVIRONMENT != 'prd':
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

def get_logger():
    """Returns the configured logger instance."""
    return logger
