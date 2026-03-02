import os
from tempfile import mkdtemp


class Config:
    # Flask core - secret key used to sign session cookies
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # Session configuration - store sessions as files on the server
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = mkdtemp()
    SESSION_COOKIE_NAME = 'lti-shell-session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False       # Set True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'    # Required for cross-site LTI launches

    # Flask-Caching - used by pylti1p3 to store data between login and launch
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 600

    # LTI configuration paths
    LTI_CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'configs')
    LTI_CONFIG_FILE = os.path.join(LTI_CONFIG_DIR, 'lti.json')
