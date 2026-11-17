import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Holds the SQLite database and uploaded files. On Render, point this at the persistent disk.
DATA_DIR = os.path.abspath(os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "instance")))


def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _env_list(name, default=""):
    return [o.strip().rstrip("/") for o in os.environ.get(name, default).split(",") if o.strip()]


def _database_url():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return "sqlite:///" + os.path.join(DATA_DIR, "portfolio.db")
    # Render and Heroku hand out postgres:// URLs, which SQLAlchemy 2 rejects.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


class Config:
    ENV = os.environ.get("FLASK_ENV", "production")
    SECRET_KEY = os.environ.get("SECRET_KEY", "")

    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Authentication: JWT stored in HttpOnly cookies, with CSRF protection
    # enforced by Flask-JWT-Extended on every unsafe request.
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_COOKIE_SECURE = _env_bool("COOKIE_SECURE", False)
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True

    # Cross-origin access for the admin app only.
    CORS_ORIGINS = _env_list("ADMIN_ORIGINS", "http://localhost:5001")

    # Uploads
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    MAX_UPLOAD_BYTES = 10 * 1024 * 1024
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(DATA_DIR, "uploads"))
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")   # local | s3
    S3_BUCKET = os.environ.get("S3_BUCKET", "")
    S3_PUBLIC_BASE_URL = os.environ.get("S3_PUBLIC_BASE_URL", "").rstrip("/")
    # Empty means same origin (the single-app setup). Media URLs become /media/<file>.
    API_PUBLIC_URL = os.environ.get("API_PUBLIC_URL", "").rstrip("/")

    # Set to "1" only when the API sits behind exactly one trusted proxy.
    TRUST_PROXY = _env_bool("TRUST_PROXY", True)
