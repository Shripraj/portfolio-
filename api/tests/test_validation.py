"""Unit tests for the pure-Python validation layer. No database or Flask needed."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from api.validation import (  # noqa: E402
    CONTACT_SCHEMA, PROJECT_SCHEMA, RateLimiter, SETTINGS_SCHEMA, ValidationError,
    check_upload, clean, detect_file_type, slugify,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PDF = b"%PDF-1.7\n" + b"\x00" * 32
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 16


def test_contact_accepts_valid_message():
    cleaned = clean(CONTACT_SCHEMA, {"name": " Asha ", "email": "asha@example.com",
                                     "message": "Hello, I would like to discuss a role."})
    assert cleaned["name"] == "Asha"
    assert cleaned["email"] == "asha@example.com"


def test_contact_rejects_bad_email_and_short_message():
    with pytest.raises(ValidationError) as exc:
        clean(CONTACT_SCHEMA, {"name": "A", "email": "not-an-email", "message": "short"})
    assert set(exc.value.errors) == {"name", "email", "message"} or "email" in exc.value.errors
    assert "email" in exc.value.errors
    assert "message" in exc.value.errors


def test_required_fields_reported_on_create():
    with pytest.raises(ValidationError) as exc:
        clean(PROJECT_SCHEMA, {"is_published": True})
    assert "title" in exc.value.errors
    assert "summary" in exc.value.errors


def test_partial_update_ignores_missing_required_fields():
    cleaned = clean(PROJECT_SCHEMA, {"is_published": False}, partial=True)
    assert cleaned == {"is_published": False}


def test_booleans_accept_form_strings():
    assert clean(PROJECT_SCHEMA, {"title": "T", "summary": "S", "featured": "true"})["featured"] is True
    assert clean(PROJECT_SCHEMA, {"title": "T", "summary": "S", "featured": "off"})["featured"] is False


def test_absent_boolean_defaults_to_false_on_create():
    cleaned = clean(PROJECT_SCHEMA, {"title": "T", "summary": "S"})
    assert cleaned["is_published"] is False
    assert cleaned["featured"] is False


def test_list_fields_accept_lines_json_and_lists():
    lines = clean(PROJECT_SCHEMA, {"title": "T", "summary": "S", "technologies": "Python\n\nFlask\n"})
    assert lines["technologies"] == ["Python", "Flask"]
    as_json = clean(PROJECT_SCHEMA, {"title": "T", "summary": "S", "technologies": '["Pandas", "NumPy"]'})
    assert as_json["technologies"] == ["Pandas", "NumPy"]


def test_modes_must_come_from_allowed_set():
    with pytest.raises(ValidationError) as exc:
        clean(PROJECT_SCHEMA, {"title": "T", "summary": "S", "modes": ["marketing"]})
    assert "modes" in exc.value.errors


def test_urls_must_be_absolute_http():
    with pytest.raises(ValidationError) as exc:
        clean(PROJECT_SCHEMA, {"title": "T", "summary": "S", "github_url": "github.com/x"})
    assert "github_url" in exc.value.errors
    ok = clean(PROJECT_SCHEMA, {"title": "T", "summary": "S", "github_url": "https://github.com/x/y"})
    assert ok["github_url"] == "https://github.com/x/y"


def test_empty_optional_url_becomes_none():
    cleaned = clean(PROJECT_SCHEMA, {"title": "T", "summary": "S", "live_url": ""})
    assert cleaned["live_url"] is None


def test_settings_reject_unknown_theme_and_sections():
    with pytest.raises(ValidationError):
        clean(SETTINGS_SCHEMA, {"default_theme": "neon"}, partial=True)
    with pytest.raises(ValidationError):
        clean(SETTINGS_SCHEMA, {"visible_sections": ["about", "crypto"]}, partial=True)


def test_slugify_is_url_safe():
    assert slugify("Karnataka Rainfall Analytics & Forecasting Dashboard") == \
        "karnataka-rainfall-analytics-forecasting-dashboard"
    assert slugify("   ") == "item"
    assert slugify("Café Résumé") == "cafe-resume"


def test_detect_file_type_uses_magic_bytes_not_filename():
    assert detect_file_type(PNG[:16]) == "png"
    assert detect_file_type(JPG[:16]) == "jpg"
    assert detect_file_type(WEBP[:16]) == "webp"
    assert detect_file_type(PDF[:16]) == "pdf"
    assert detect_file_type(b"<script>alert(1)</script>") is None


def test_upload_rejects_disguised_files():
    fake_pdf = b"<html><script>alert(1)</script></html>"
    with pytest.raises(ValueError):
        check_upload(fake_pdf, ("pdf",), 10_000)


def test_upload_rejects_wrong_kind_and_oversize():
    with pytest.raises(ValueError):
        check_upload(PNG, ("pdf",), 10_000)     # images are not valid resumes
    with pytest.raises(ValueError):
        check_upload(PDF, ("pdf",), 10)         # over the size limit
    with pytest.raises(ValueError):
        check_upload(b"", ("pdf",), 10)


def test_upload_returns_extension_and_mime():
    assert check_upload(PDF, ("pdf",), 10_000) == ("pdf", "application/pdf")
    assert check_upload(PNG, ("png", "jpg"), 10_000) == ("png", "image/png")


def test_rate_limiter_blocks_after_limit_and_recovers_after_window():
    limiter = RateLimiter()
    assert all(limiter.allow("ip-1", limit=3, window_seconds=60, now=t) for t in (0, 1, 2))
    assert limiter.allow("ip-1", limit=3, window_seconds=60, now=3) is False
    assert limiter.allow("ip-2", limit=3, window_seconds=60, now=3) is True   # separate key
    assert limiter.allow("ip-1", limit=3, window_seconds=60, now=100) is True  # window passed
