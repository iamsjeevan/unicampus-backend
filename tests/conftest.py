# tests/conftest.py
import pytest
from app import create_app # Your Flask app factory
from app.config import Config # Your base config
import os # For potentially setting test-specific env vars if needed

# It's good practice to use a separate test configuration if your app behaves differently
# or if you want to connect to a different test database (e.g., mongomock or a different real DB)
class TestConfig(Config):
    TESTING = True
    DEBUG = False # Usually False for tests to mimic production more closely unless debugging tests
    # Example: Use an in-memory MongoDB for tests or a specific test DB
    # MONGO_URI = "mongomock://localhost/test_unicampus_db" # Requires pip install mongomock pymongo-srv
    # OR, if you have a dedicated test MongoDB instance:
    # MONGO_URI = os.environ.get('TEST_MONGO_URI', 'mongodb://localhost:27017/unicampus_test_db')
    
    # For now, we'll let it use the .env MONGO_URI, assuming it's acceptable for testing.
    # Be careful if your tests modify data and you're pointing to your dev Atlas DB.
    # Ideally, tests should run against a dedicated, isolated test database.

    JWT_SECRET_KEY = "test_jwt_secret_key" # Use a fixed secret for tests
    # Make token expiry very short for testing expiry, or very long to not worry about it
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = 15 
    JWT_REFRESH_TOKEN_EXPIRES_DAYS = 1


@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    # For more isolated tests, you would use TestConfig:
    # _app = create_app(config_class=TestConfig)
    # For now, using default config which loads from .env
    # This means tests might interact with your development Atlas DB.
    # Consider this carefully. Using a mock DB or a test DB instance is safer.
    _app = create_app() # Uses Config which loads .env by default

    # Establish an application context before running the tests.
    with _app.app_context():
        yield _app

@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture()
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

# Helper fixture to get auth tokens for a test user
@pytest.fixture
def auth_tokens(client):
    """Provides auth tokens for a predefined test user."""
    # For a real test, you might create a test user here or ensure one exists
    # For now, using your hardcoded test credentials
    login_data = {
        "usn": "1MS22CS118", # Use known test credentials
        "dob_dd": "13",
        "dob_mm": "04",
        "dob_yyyy": "2004"
    }
    response = client.post('/api/v1/auth/login/student', json=login_data)
    if response.status_code != 200:
        print("Login failed in auth_tokens fixture. Response:", response.get_data(as_text=True))
        pytest.fail("Failed to log in test user to get tokens.")
    
    tokens = response.get_json()
    return {
        "access_token": tokens.get("accessToken"),
        "refresh_token": tokens.get("refreshToken"),
        "user_id": tokens.get("data", {}).get("user", {}).get("id") # Assuming login response includes user ID
    }