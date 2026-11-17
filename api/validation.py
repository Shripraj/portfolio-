"""Pure-Python validation and helper logic.

This module deliberately has no Flask or SQLAlchemy imports so that it can be
unit-tested in isolation (see api/tests/test_validation.py).
"""
import json
import re
import threading
import time
import unicodedata
from collections import defaultdict, deque

MODES = ("python", "data")
SECTIONS = ("about", "projects", "experience", "skills", "certifications", "contact")
THEMES = ("light", "dark")

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Validation failed")


class F:
    """Declarative description of one input field."""

    def __init__(self, kind, required=False, max_len=None, choices=None,
                 max_items=None, max_item_len=None, min_len=None):
        self.kind = kind            # str | text | url | email | int | bool | id | list | choice | modes | slug
        self.required = required
        self.max_len = max_len
        self.min_len = min_len
        self.choices = choices
        self.max_items = max_items
        self.max_item_len = max_item_len


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("", "0", "false", "no", "off"):
            return False
    raise ValueError("must be true or false")


def _to_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("["):
            try:
                value = json.loads(s)
            except ValueError as exc:
                raise ValueError("must be a list") from exc
        else:
            # Admin textareas send one item per line.
            value = s.splitlines()
    if not isinstance(value, list):
        raise ValueError("must be a list")
    items = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("list items must be text")
        item = item.strip()
        if item:
            items.append(item)
    return items


def _to_id(value):
    if value is None or value == "" or value == "null":
        return None
    if isinstance(value, bool):
        raise ValueError("must be an id")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("must be an id") from exc
    if number <= 0:
        raise ValueError("must be a positive id")
    return number


def _clean_one(name, spec, raw, errors):
    """Return the cleaned value for one field, or record an error."""
    kind = spec.kind

    if kind in ("str", "text", "slug", "email", "url"):
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            errors[name] = "must be text"
            return None
        raw = raw.strip()
        if raw == "":
            if spec.required:
                errors[name] = "This field is required."
                return None
            return None if kind in ("email", "url", "slug") else ""
        if spec.max_len and len(raw) > spec.max_len:
            errors[name] = f"Must be {spec.max_len} characters or fewer."
            return None
        if spec.min_len and len(raw) < spec.min_len:
            errors[name] = f"Must be at least {spec.min_len} characters."
            return None
        if kind == "email" and not EMAIL_RE.match(raw):
            errors[name] = "Enter a valid email address."
            return None
        if kind == "url" and not URL_RE.match(raw):
            errors[name] = "Enter a full link starting with https://"
            return None
        if kind == "slug" and not SLUG_RE.match(raw):
            errors[name] = "Use lowercase letters, numbers and hyphens only."
            return None
        return raw

    try:
        if kind == "bool":
            if raw is None:
                return False
            return _to_bool(raw)
        if kind == "int":
            if raw in (None, ""):
                return None   # service layer chooses the default position
            return int(raw)
        if kind == "id":
            return _to_id(raw)
        if kind == "list":
            items = _to_list(raw)
            if spec.max_items and len(items) > spec.max_items:
                errors[name] = f"At most {spec.max_items} items."
                return None
            if spec.max_item_len and any(len(i) > spec.max_item_len for i in items):
                errors[name] = f"Each item must be {spec.max_item_len} characters or fewer."
                return None
            if spec.choices and any(i not in spec.choices for i in items):
                errors[name] = "Contains an unsupported value."
                return None
            return items
        if kind == "ids":
            if raw in (None, "", []):
                return []
            if not isinstance(raw, list):
                raise ValueError("must be a list of ids")
            ids = [_to_id(item) for item in raw]
            if any(item is None for item in ids):
                raise ValueError("must be a list of ids")
            ids = sorted(set(ids))
            if spec.max_items and len(ids) > spec.max_items:
                errors[name] = f"At most {spec.max_items} items."
                return None
            return ids
        if kind == "choice":
            if raw not in spec.choices:
                errors[name] = "Choose one of the listed options."
                return None
            return raw
        if kind == "modes":
            items = _to_list(raw)
            if any(i not in spec.choices for i in items):
                errors[name] = "Contains an unsupported value."
                return None
            return items
    except ValueError as exc:
        msg = str(exc)
        errors[name] = msg[:1].upper() + msg[1:] + ("" if msg.endswith(".") else ".")
        return None
    raise ValueError(f"Unknown field kind {kind}")


def clean(schema, data, partial=False):
    """Validate `data` against `schema` (dict of name -> F).

    partial=True validates only the keys that are present (used for PUT and
    PATCH). Unknown keys are ignored so that clients can send whole objects.
    Raises ValidationError with a dict of field errors.
    """
    if data is None or not hasattr(data, "get"):
        raise ValidationError({"_body": "Expected an object."})
    errors = {}
    cleaned = {}
    for name, spec in schema.items():
        if partial and name not in data:
            continue
        raw = data.get(name)
        if not partial and raw is None and spec.required:
            errors[name] = "This field is required."
            continue
        value = _clean_one(name, spec, raw, errors)
        if name not in errors:
            cleaned[name] = value
    if errors:
        raise ValidationError(errors)
    return cleaned


def slugify(text, fallback="item"):
    normalised = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalised).strip("-").lower()
    return slug[:150].strip("-") or fallback


# ---------------------------------------------------------------- uploads

IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}
PDF_TYPE = {"pdf": "application/pdf"}


def detect_file_type(head: bytes):
    """Identify an upload from its leading bytes (never trust the filename)."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head.startswith(b"%PDF-"):
        return "pdf"
    return None


def check_upload(raw: bytes, allowed_kinds, max_bytes):
    """Return (extension, mime) or raise ValueError with a user-facing message."""
    if not raw:
        raise ValueError("The file is empty.")
    if len(raw) > max_bytes:
        raise ValueError(f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
    ext = detect_file_type(raw[:16])
    if ext is None or ext not in allowed_kinds:
        raise ValueError("Unsupported file type. Allowed: " + ", ".join(allowed_kinds) + ".")
    mime = {**IMAGE_TYPES, **PDF_TYPE}[ext]
    return ext, mime


# ------------------------------------------------------------ rate limiting

class RateLimiter:
    """Sliding-window limiter kept in process memory.

    Good for a single instance. For several instances, back it with Redis.
    """

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key, limit, window_seconds, now=None):
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self):
        with self._lock:
            self._hits.clear()


# ------------------------------------------------------------------ schemas

PROJECT_SCHEMA = {
    "title": F("str", required=True, max_len=160),
    "slug": F("slug", max_len=180),
    "category_ids": F("ids", max_items=6),
    "summary": F("text", required=True, max_len=1000),
    "problem": F("text", max_len=1500),
    "solution": F("text", max_len=1500),
    "details": F("text", max_len=8000),
    "technologies": F("list", max_items=25, max_item_len=60),
    "features": F("list", max_items=20, max_item_len=200),
    "outcomes": F("list", max_items=10, max_item_len=200),
    "github_url": F("url", max_len=500),
    "live_url": F("url", max_len=500),
    "image_id": F("id"),
    "modes": F("modes", choices=MODES),
    "featured": F("bool"),
    "is_published": F("bool"),
    "position": F("int"),
}

PROJECT_CATEGORY_SCHEMA = {
    "name": F("str", required=True, max_len=80),
    "slug": F("slug", max_len=90),
    "position": F("int"),
}

SKILL_CATEGORY_SCHEMA = {
    "name": F("str", required=True, max_len=80),
    "modes": F("modes", choices=MODES),
    "position": F("int"),
    "is_published": F("bool"),
}

SKILL_SCHEMA = {
    "name": F("str", required=True, max_len=80),
    "category_id": F("id", required=True),
    "position": F("int"),
    "is_published": F("bool"),
}

EXPERIENCE_SCHEMA = {
    "organization": F("str", required=True, max_len=160),
    "role": F("str", required=True, max_len=160),
    "location": F("str", max_len=120),
    "employment_type": F("str", max_len=60),
    "start_label": F("str", required=True, max_len=40),
    "end_label": F("str", max_len=40),
    "responsibilities": F("list", max_items=15, max_item_len=400),
    "position": F("int"),
    "is_published": F("bool"),
}

EDUCATION_SCHEMA = {
    "institution": F("str", required=True, max_len=200),
    "qualification": F("str", required=True, max_len=200),
    "location": F("str", max_len=120),
    "period": F("str", max_len=60),
    "details": F("text", max_len=1000),
    "position": F("int"),
    "is_published": F("bool"),
}

CERTIFICATION_SCHEMA = {
    "name": F("str", required=True, max_len=200),
    "issuer": F("str", required=True, max_len=160),
    "issued_label": F("str", max_len=60),
    "verification_url": F("url", max_len=500),
    "media_id": F("id"),
    "position": F("int"),
    "is_published": F("bool"),
}

PROFILE_SCHEMA = {
    "name": F("str", required=True, max_len=120),
    "headline": F("str", required=True, max_len=255),
    "primary_title": F("str", max_len=120),
    "secondary_title": F("str", max_len=120),
    "bio": F("text", max_len=2000),
    "intro_developer": F("text", max_len=1200),
    "intro_analyst": F("text", max_len=1200),
    "email": F("email", max_len=255),
    "phone": F("str", max_len=30),
    "location": F("str", max_len=120),
    "linkedin_url": F("url", max_len=500),
    "github_url": F("url", max_len=500),
    "photo_id": F("id"),
}

SETTINGS_SCHEMA = {
    "site_title": F("str", max_len=120),
    "meta_description": F("text", max_len=300),
    "seo_keywords": F("str", max_len=300),
    "homepage_headline": F("str", max_len=255),
    "homepage_bio": F("text", max_len=1000),
    "default_theme": F("choice", choices=THEMES),
    "visible_sections": F("list", choices=SECTIONS),
}

SETTINGS_DEFAULTS = {
    "site_title": "",
    "meta_description": "",
    "seo_keywords": "",
    "homepage_headline": "",
    "homepage_bio": "",
    "default_theme": "light",
    "visible_sections": list(SECTIONS),
}

CONTACT_SCHEMA = {
    "name": F("str", required=True, max_len=120),
    "email": F("email", required=True, max_len=255),
    "message": F("text", required=True, min_len=10, max_len=3000),
    "website": F("str", max_len=200),   # honeypot, must stay empty
}

MESSAGE_UPDATE_SCHEMA = {
    "is_read": F("bool"),
}
