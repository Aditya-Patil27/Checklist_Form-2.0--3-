import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    
    # Paths
    BASE_DIR = BASE_DIR
    SCHEMA_DIR = BASE_DIR / "data" / "checklists"
    TEMPLATE_DIR = BASE_DIR / "data" / "unfilled"
    SUBMISSION_DIR = BASE_DIR / "data" / "submissions"
    ACTIVE_DIR = BASE_DIR / "data" / "active"
    USERS_FILE = BASE_DIR / "users.json"
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:password@localhost/mahle_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security
    BCRYPT_ROUNDS = 12
    SESSION_COOKIE_SECURE = False  # Set True in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://127.0.0.1:5000").split(",")
    
    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "100 per hour"


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}


def get_config(env=None):
    """Get configuration based on environment."""
    env = env or os.environ.get("FLASK_ENV", "default")
    return config.get(env, DevelopmentConfig)