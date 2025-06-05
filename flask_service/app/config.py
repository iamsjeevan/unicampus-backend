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
    COLLEGE_EXAM_HISTORY_PATH = '/newparents/index.php?option=com_history&task=getResult' # Note: The leading '/' is fine if urljoin handles it, but often paths are relative without it.
                                                                                       # The cURL shows `index.php?option=...` directly.
                                                                                       # My code uses urljoin(Config.COLLEGE_BASE_URL, Config.COLLEGE_EXAM_HISTORY_PATH)
                                                                                       # so "newparents/index.php?..." might be slightly cleaner for the path if COLLEGE_BASE_URL is just the domain.
                                                                                       # For your current setup, ensure it resolves correctly.
                                                                                       # The previous `newparents/index.php?option=com_history&task=getResult` was good.

    # User Agent for the scraper
    SCRAPER_USER_AGENT = 'UniCampusAppBackend/PythonScraper/1.1 (compatible; Mozilla/5.0)'
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'instance', 'uploads')
    
    # The subpath within your static URL path where uploads are served.
    # e.g., if UPLOAD_FOLDER is instance/uploads, and you serve instance/uploads as /static/media
    # this would be 'media'.
    # If UPLOAD_FOLDER is app/static/uploads, this would be 'uploads'.
    # This is used by url_for('static', filename=STATIC_UPLOAD_SUBPATH + '/folder/file.png')
    STATIC_UPLOAD_SUBPATH = 'uploads' # Assumes UPLOAD_FOLDER is configured to be served under /static/uploads/
                                     # For example, if app.static_folder is 'app/static',
                                     # and UPLOAD_FOLDER is 'app/static/uploads'

    # Optional: Max content length for uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    # Or, if you want to mimic the browser more closely from your cURL:
    # SCRAPER_USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'

    # JOOMLA_TOKEN_NAME and JOOMLA_TOKEN_VALUE are removed as they are handled dynamically by the scraper.
