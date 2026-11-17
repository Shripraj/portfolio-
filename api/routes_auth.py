from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token, get_csrf_token, get_jwt, get_jwt_identity, jwt_required,
    set_access_cookies, unset_jwt_cookies,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, ratelimit
from .http import error
from .models import AdminUser

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Used to keep response timing similar when the email address is unknown.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def admin_required(fn):
    """Requires a valid admin session cookie plus the CSRF header on unsafe methods."""

    @jwt_required()
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = db.session.get(AdminUser, int(get_jwt_identity()))
        if user is None:
            return error(401, "Please sign in to continue.")
        return fn(*args, **kwargs)

    return wrapper


@bp.post("/login")
def login():
    ip = request.remote_addr or "unknown"
    if not ratelimit.allow(f"login:{ip}", limit=10, window_seconds=900):
        return error(429, "Too many sign-in attempts. Try again in 15 minutes.")

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not email or not password:
        return error(400, "Enter your email and password.")

    user = AdminUser.query.filter_by(email=email).first()
    if user is None:
        check_password_hash(_DUMMY_HASH, password)
        return error(401, "Incorrect email or password.")
    if not user.check_password(password):
        return error(401, "Incorrect email or password.")

    token = create_access_token(identity=str(user.id))
    # The admin app runs on another origin and cannot read the API's cookies,
    # so the CSRF token is returned in the body and sent back as a header.
    response = jsonify({
        "user": {"id": user.id, "email": user.email},
        "csrf_token": get_csrf_token(token),
    })
    set_access_cookies(response, token)
    return response


@bp.post("/logout")
def logout():
    response = jsonify({"ok": True})
    unset_jwt_cookies(response)
    return response


@bp.get("/me")
@admin_required
def me():
    user = db.session.get(AdminUser, int(get_jwt_identity()))
    return jsonify({
        "user": {"id": user.id, "email": user.email},
        "csrf_token": get_jwt().get("csrf"),
    })
