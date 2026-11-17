import logging
import os

from flask import Flask, current_app, abort, request, send_from_directory
from flask_jwt_extended.exceptions import JWTExtendedException
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from .cli import register_cli
from .config import Config
from .extensions import cors, db, jwt, migrate
from .http import error
from .models import Media
from .routes_admin import bp as admin_bp
from .routes_auth import bp as auth_bp
from .routes_public import bp as public_bp
from .validation import ValidationError
from .web import register_web

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEV_SECRET = "dev-only-insecure-secret-change-me"

CONTENT_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self'; "
    "form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
)


def create_app(config_object=Config, overrides=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(ROOT_DIR, "templates"),
        static_folder=os.path.join(ROOT_DIR, "static"),
        static_url_path="/static",
    )
    app.config.from_object(config_object)
    if overrides:
        app.config.update(overrides)

    if not app.config["SECRET_KEY"]:
        if os.environ.get("FLASK_DEBUG") == "1" or app.config.get("TESTING"):
            app.config["SECRET_KEY"] = DEV_SECRET
        else:
            raise RuntimeError("SECRET_KEY must be set. Refusing to start without it.")
    if not app.config.get("JWT_SECRET_KEY"):
        app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]

    if app.config["TRUST_PROXY"]:
        # Render, Railway and Vercel all sit behind exactly one proxy hop.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    _ensure_sqlite_folder(app.config["SQLALCHEMY_DATABASE_URI"])
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"], "supports_credentials": True}},
        allow_headers=["Content-Type", "X-CSRF-TOKEN"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    register_cli(app)
    register_web(app)
    _register_jwt_handlers()
    _register_error_handlers(app)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/media/<path:key>")
    def serve_media(key):
        """Serves uploaded files from local disk. Not used when STORAGE_BACKEND=s3."""
        if current_app.config["STORAGE_BACKEND"] == "s3":
            abort(404)
        media = Media.query.filter_by(storage_key=key).first()
        if media is None:
            abort(404)
        return send_from_directory(
            current_app.config["UPLOAD_DIR"], key, mimetype=media.mime_type, max_age=86400,
        )

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Content-Security-Policy", CONTENT_CSP)
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    return app


def _ensure_sqlite_folder(uri):
    """SQLite will not create missing folders, so make sure the database folder exists."""
    prefix = "sqlite:///"
    if uri.startswith(prefix):
        path = uri[len(prefix):]
        if path and path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def _register_jwt_handlers():
    @jwt.unauthorized_loader
    def _missing_token(reason):
        return error(401, "Please sign in to continue.")

    @jwt.invalid_token_loader
    def _invalid_token(reason):
        return error(401, "Your session is no longer valid. Please sign in again.")

    @jwt.expired_token_loader
    def _expired_token(_header, _payload):
        return error(401, "Your session has expired. Please sign in again.")


def _register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def _validation(exc):
        return error(400, "Please check the highlighted fields.", exc.errors)

    @app.errorhandler(JWTExtendedException)
    def _jwt(exc):
        return error(401, "Your session could not be verified. Please sign in again.")

    @app.errorhandler(HTTPException)
    def _http(exc):
        if request.path.startswith(("/api/", "/media/")):
            return error(exc.code or 500, exc.description or exc.name)
        from .web import html_error
        return html_error(exc.code or 500, exc.description or exc.name)

    @app.errorhandler(Exception)
    def _unexpected(exc):
        logging.getLogger(__name__).exception("Unhandled error")
        db.session.rollback()
        if request.path.startswith(("/api/", "/media/")):
            return error(500, "Something went wrong on our side. Please try again.")
        from .web import html_error
        return html_error(500, "Something went wrong on our side. Please try again.")
