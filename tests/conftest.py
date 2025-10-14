import pytest
import os
import sys
import threading
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from app import app as flask_app, db
from user_auth import UserAuthManager
from services import AccessKeyService, NotificationService, AnnouncementService, StatisticsService


@pytest.fixture(scope="session")
def app(monkeypatch_session):
    """
    Creates a test instance of the Flask application for the entire session.
    Configured for testing with an in-memory SQLite database.
    """
    flask_app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
            "SERVER_NAME": "localhost.localdomain",  # Required for url_for to work without a request context
            "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # Set to 16MB for tests
            "CACHE_TYPE": "null",  # Wyłącz buforowanie dla testów
        }
    )
    flask_app.secret_key = flask_app.config["SECRET_KEY"]  # Explicitly set secret_key

    # Access the already initialized CSRFProtect instance from app.py
    if hasattr(flask_app, "extensions") and "csrf" in flask_app.extensions:
        csrf_instance = flask_app.extensions["csrf"]
        csrf_instance.enabled = False  # Disable CSRF for testing purposes
    else:
        # Fallback if CSRFProtect is not yet in extensions (shouldn't happen if initialized in app.py)
        from flask_wtf.csrf import CSRFProtect

        csrf_instance = CSRFProtect(flask_app)
        csrf_instance.enabled = False

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.drop_all()

# NOWA FIXTURA DLA TESTÓW BEZPIECZEŃSTWA
@pytest.fixture(scope="function")
def csrf_enabled_client(app):
    """A test client with CSRF protection enabled."""
    app.config.update({
        "WTF_CSRF_ENABLED": True,
        "TESTING": False # Trzeba wyłączyć tryb testowy, aby CSRF działał
    })
    if hasattr(app, "extensions") and "csrf" in app.extensions:
        app.extensions["csrf"].enabled = True

    with app.test_client() as client:
        yield client

    # Przywrócenie domyślnej konfiguracji po teście
    app.config.update({
        "WTF_CSRF_ENABLED": False,
        "TESTING": True
    })
    if hasattr(app, "extensions") and "csrf" in app.extensions:
        app.extensions["csrf"].enabled = False


# Fixture to control Playwright browser launch arguments
@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "headless": False,  # Force headless to False for visible browser
    }


@pytest.fixture(scope="session")
def monkeypatch_session():
    """A session-scoped monkeypatch fixture."""
    from _pytest.monkeypatch import MonkeyPatch

    m = MonkeyPatch()
    yield m
    m.undo()


@pytest.fixture(scope="session")
def live_server(app):
    """Session-scoped live server fixture for E2E tests."""
    # Set admin credentials in the environment for the subprocess
    os.environ["ADMIN_USERNAME"] = "admin_test"
    os.environ["ADMIN_PASSWORD"] = "password_test"

    server = threading.Thread(
        target=app.run, kwargs={"host": "127.0.0.1", "port": 5000}
    )
    server.daemon = True
    server.start()
    time.sleep(1)  # Give the server a moment to start
    yield "http://127.0.0.1:5000"
    # Daemon thread will exit with the main process


@pytest.fixture(scope="function")
def client(app):
    """A test client for the app for each function."""
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def db_session(app):
    """
    Provides a clean database session for each test function.
    This fixture ensures that tests are isolated from each other.
    """
    yield db.session

    # Clean up the database after each test
    db.session.remove()
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()


@pytest.fixture(scope="function")
def auth_manager(db_session):
    """Provides an instance of UserAuthManager."""
    access_key_service = AccessKeyService()
    notification_service = NotificationService()
    return UserAuthManager(access_key_service, notification_service)


@pytest.fixture(scope="function")
def access_key_service(db_session):
    """Provides an instance of AccessKeyService."""
    return AccessKeyService()


@pytest.fixture(scope="function")
def announcement_service(db_session):
    """Provides an instance of AnnouncementService."""
    return AnnouncementService()


@pytest.fixture(scope="function")
def statistics_service(db_session):
    """Provides an instance of StatisticsService."""
    return StatisticsService()


@pytest.fixture(scope="function")
def notification_service(db_session):
    """Provides an instance of NotificationService."""
    return NotificationService()


@pytest.fixture(scope="function")
def registered_user(client, auth_manager, access_key_service):
    """Fixture to create a pre-registered user and return their details."""
    key = access_key_service.generate_access_key("test_user_key")
    db.session.commit()
    username = "testuser"
    password = "password123"
    auth_manager.register_user(username, password, key, mark_tutorial_seen=True)
    return {"username": username, "password": password}


@pytest.fixture(scope="function")
def logged_in_client(client, registered_user):
    """Fixture to get a client that is already logged in and has a valid CSRF token."""
    # First, make a GET request to the login page to get a CSRF token in the session
    client.get("/login")
    with client.session_transaction() as sess:
        csrf_token = sess.get(
            "csrf_token"
        )  # Get the token that Flask-WTF put in the session

    # Now, perform the login POST request with the token from the session
    response = client.post(
        "/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
        headers={"X-CSRFToken": csrf_token},  # Use the token directly from the session
    )
    assert response.status_code == 200

    # The client's session should now be updated with the logged-in user's session
    # and the CSRF token should persist.
    # We can optionally store it on the client object for other tests if needed.
    with client.session_transaction() as sess:
        client.csrf_token = sess.get("csrf_token")

    yield client
    client.get("/logout")


@pytest.fixture(scope="function")
def admin_client(client, monkeypatch, app):
    """Fixture that provides an authenticated admin client."""
    admin_user = "admin_test"
    admin_pass = "password_test"
    monkeypatch.setenv("ADMIN_USERNAME", admin_user)
    monkeypatch.setenv("ADMIN_PASSWORD", admin_pass)

    # Import limiter from app module to reset it
    try:
        from app import limiter
        if hasattr(limiter, '_storage') and hasattr(limiter._storage, 'storage'):
            # Clear the in-memory storage to reset rate limits
            limiter._storage.storage.clear()
    except (ImportError, AttributeError, Exception):
        pass  # If limiter is not available or is DummyLimiter, just continue
    
    # First, make a GET request to the admin login page to get a CSRF token in the session
    client.get("/admin/login")
    with client.session_transaction() as sess:
        csrf_token = sess.get(
            "csrf_token"
        )  # Get the token that Flask-WTF put in the session

    response = client.post(
        "/admin/login",
        json={"username": admin_user, "password": admin_pass},
        headers={"X-CSRFToken": csrf_token},  # Use the token from the session
    )
    assert response.status_code == 200, (
        f"Admin login failed with status {response.status_code} and data: {response.get_data(as_text=True)}"
    )
    assert response.json["success"] is True

    with client.session_transaction() as sess:
        client.csrf_token = sess.get("csrf_token")  # Store it for later use if needed

    yield client

    client.get("/admin/logout")


@pytest.fixture(scope="session")
def admin_credentials():
    """Provides admin credentials for tests."""
    return {"username": "admin_test", "password": "password_test"}