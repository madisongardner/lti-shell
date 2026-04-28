"""Shared pytest configuration and path setup."""
import os
import sys
import tempfile
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to sys.path so that imports like
# `from services.grading_service import ...` resolve correctly.
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database import Base
from config import Config


class TestConfig(Config):
    """Test configuration with in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_ECHO = False
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)
    
    yield TestSessionLocal
    
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config.from_object(TestConfig)
    
    # Use temp directory for session files
    app.config['SESSION_FILE_DIR'] = tempfile.mkdtemp()
    
    # Mock LTI config file path
    os.environ['LTI_CONFIG_FILE'] = os.path.join(
        Path(__file__).resolve().parent.parent / "backend" / "configs",
        "lti.json"
    )
    
    return app


@pytest.fixture(scope="function")
def client(app, test_db, monkeypatch):
    """Create a Flask test client."""
    # Patch SessionLocal in database module to use test_db
    from database import SessionLocal as _original_sessionlocal
    monkeypatch.setattr("database.SessionLocal", test_db)
    
    # Patch the global SessionLocal where it's imported in routes/models
    import routes.assignments
    monkeypatch.setattr("routes.assignments.SessionLocal", test_db)
    
    # Initialize extensions
    from extensions import cache, sess
    cache.init_app(app)
    sess.init_app(app)
    
    # Create all tables
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    
    with app.app_context():
        yield app.test_client()


@pytest.fixture(scope="function")
def session(app, test_db):
    """Create a database session for a test."""
    session_instance = test_db()
    yield session_instance
    session_instance.close()


@pytest.fixture(scope="function")
def mock_lti_user():
    """Fixture for a mock LTI user in session."""
    return {
        'sub': 'user-123',
        'name': 'Test Student',
        'email': 'student@example.com',
        'role': 'student',
        'course_id': 'course-456',
        'resource_link_id': 'resource-789',
        'lineitem_url': 'https://moodle.example.com/ags/lineitem/1',
        'ags_scopes': ['https://purl.imsglobal.org/spec/lti-ags/scope/lineitem'],
        'launch_id': 'launch-xyz'
    }


@pytest.fixture(scope="function")
def mock_lti_teacher():
    """Fixture for a mock LTI teacher in session."""
    return {
        'sub': 'teacher-123',
        'name': 'Test Teacher',
        'email': 'teacher@example.com',
        'role': 'teacher',
        'course_id': 'course-456',
        'resource_link_id': 'resource-789',
        'lineitem_url': 'https://moodle.example.com/ags/lineitem/1',
        'ags_scopes': ['https://purl.imsglobal.org/spec/lti-ags/scope/lineitem'],
        'launch_id': 'launch-xyz'
    }
