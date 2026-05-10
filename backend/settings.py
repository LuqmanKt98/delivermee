import os
from dotenv import load_dotenv

load_dotenv(verbose=False)

# Database mode — always Firestore in this deployment
USE_FIREBASE_DB = os.getenv("USE_FIREBASE_DB", "false").lower() == "true"

# Database settings (ORM_DISABLED: kept for reference only)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/deliver_me").strip()

# Flask settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

# Application settings
APP_NAME = "DeliverMee API"
APP_VERSION = "1.0.0"
API_PREFIX = "/api"
API_VERSION = "v1"

# ORM_DISABLED: SQLAlchemy config kept for reference
SQLALCHEMY_DATABASE_URI = DATABASE_URL
SQLALCHEMY_TRACK_MODIFICATIONS = False
