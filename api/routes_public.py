from flask import Blueprint, jsonify, make_response, request

from .extensions import db, ratelimit
from .http import error
from .models import ContactMessage
from .services import snapshot_etag
from .validation import CONTACT_SCHEMA, ValidationError, clean

bp = Blueprint("public", __name__, url_prefix="/api/public")


@bp.get("/site")
def site():
    """Everything that is published, as one cacheable document."""
    version, row = snapshot_etag()
    if row is None:
        return error(503, "Content has not been published yet.")
    etag = f'"site-v{version}"'
    if request.headers.get("If-None-Match") == etag:
        response = make_response("", 304)
    else:
        response = jsonify(row.payload)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=300"
    return response


@bp.post("/contact")
def contact():
    ip = request.remote_addr or "unknown"
    if not ratelimit.allow(f"contact:{ip}", limit=5, window_seconds=3600):
        return error(429, "Too many messages from this address. Please try again later.")

    try:
        cleaned = clean(CONTACT_SCHEMA, request.get_json(silent=True))
    except ValidationError as exc:
        return error(400, "Please check the highlighted fields.", exc.errors)

    # Honeypot: real visitors never fill this in. Bots get a success response
    # but nothing is stored.
    if cleaned.get("website"):
        return jsonify({"ok": True}), 201

    db.session.add(ContactMessage(
        name=cleaned["name"], email=cleaned["email"], message=cleaned["message"],
    ))
    db.session.commit()
    return jsonify({"ok": True}), 201
