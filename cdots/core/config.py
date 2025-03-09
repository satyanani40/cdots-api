import os
import json
from passlib.context import CryptContext

# Load configuration based on environment
ENVIRONMENT = os.getenv("environment", "stg")
CONFIG_FILE = f"cdots/configurations/{ENVIRONMENT}_conf.json"

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as config_file:
        config = json.load(config_file)
else:
    raise RuntimeError(f"Configuration file {CONFIG_FILE} not found!")

# Security settings
SECRET_KEY = config.get("secret_key", "your_default_secret_key")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB settings
MONGO_URI = config.get("mongo_uri", "mongodb://localhost:27017/")
MONGO_DB_NAME = config.get("mongo_db_name", "cdots")
try:
    STATIC_FOLDER_PATH = config['static_folder']
except Exception as e:
    raise Exception(f"configuration file missing static_folder path, error_info:{e}")

# Define upload folder
os.makedirs(STATIC_FOLDER_PATH, exist_ok=True)


