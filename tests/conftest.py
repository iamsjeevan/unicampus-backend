# tests/conftest.py
import pytest
from app import create_app # Your Flask app factory
from app.config import Config # Your base config

class TestConfig(Config):
    """Configuration for testing."""
    TESTING = True
    DEBUG = True # Optional: can be helpful for debugging tests
    # Use a different MongoDB URI for testing if you want to avoid hitting your dev/prod DB
    # For now, we can use the main MONGO_URI or mock it later for more isolated tests
    # MONGO_URI = "mongomock://localhost/test_unicampus_db" # Example using mongomock
    # If using a real test DB:
    # MONGO_URI = os.environ.get('TEST_MONGO_URI', 'mongodb://localhost:27017/unicampus_test_db')
    
    # Disable CSRF protection if you have it enabled and it interferes with tests
    # WTF_CSRF_ENABLED = False 
    # LOGIN_DISABLED = True # If you want to bypass login for some tests (use with caution)

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    # _app = create_app(config_class=TestConfig) # Use TestConfig
    _app = create_app() # Using default Config for now, which loads from .env
                        # For true isolation, TestConfig with a mock/test DB is better.

    # Establish an application context before running the tests.
    with _app.app_context():
        yield _app # provide the app instance

@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture()
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

# Optional: Fixture for an authenticated client (more advanced, for later)
# @pytest.fixture
# def authenticated_client(client, app):
#     # This would involve creating a test user, generating a token,
#     # and setting the Authorization header on the client.
#     # Example (very simplified):
#     # with app.app_context():
#     #     # from flask_jwt_extended import create_access_token
#     #     # access_token = create_access_token(identity="test_user_id")
#     #     # client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
#     # pass
#     return client # Placeholder for nowtouch