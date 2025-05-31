import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_strong_default_secret_key'
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/unicampus_dev_db'
    
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'a_super_secret_jwt_key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', 30)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 7)))
    JWT_TOKEN_LOCATION = ['headers']

    # College Portal Configuration
    COLLEGE_LOGIN_URL = 'https://parents.msrit.edu/newparents/index.php'
    COLLEGE_BASE_URL = 'https://parents.msrit.edu'
    COLLEGE_EXAM_HISTORY_PATH = '/newparents/index.php?option=com_history&task=getResult'
    
    JOOMLA_TOKEN_NAME = "c4687d49910f5bc56504838230a3f690" # As per your JS
    JOOMLA_TOKEN_VALUE = "1" # As per your JS

    SCRAPER_USER_AGENT = 'UniCampusAppBackend/PythonScraper/1.1 (compatible; Mozilla/5.0)'