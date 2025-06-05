# flask_service/app/config.py
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_strong_default_secret_key'
    MONGO_URI = os.environ.get('MONGO_URI')

    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'a_super_secret_jwt_key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', 30)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 7)))
    JWT_TOKEN_LOCATION = ['headers']

    # College Portal Configuration
    COLLEGE_LOGIN_URL = 'https://parents.msrit.edu/newparents/index.php'
    COLLEGE_BASE_URL = 'https://parents.msrit.edu'
    COLLEGE_EXAM_HISTORY_PATH = '/newparents/index.php?option=com_history&task=getResult'

    SCRAPER_USER_AGENT = 'UniCampusAppBackend/PythonScraper/1.1 (compatible; Mozilla/5.0)'
    
    # This UPLOAD_FOLDER is for the *local file system path* where files are saved on the server
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'instance', 'uploads')
    
    # The subpath for the URL, e.g., /uploads/community_icons/file.png
    STATIC_UPLOAD_SUBPATH = 'uploads' 

    # --- THIS IS THE KEY CHANGE ---
    # The public base URL for accessing your backend, including the schema (https)
    # You can also set this via an environment variable: os.environ.get('BACKEND_PUBLIC_BASE_URL')
    BACKEND_PUBLIC_BASE_URL = 'https://unicampusbackend.duckdns.org'

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB