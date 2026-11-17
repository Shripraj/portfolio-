"""Protected admin API. Every route requires an authenticated admin session."""
from datetime import datetime

from flask import Blueprint, abort, jsonify, request
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .http import error
from .models import (
    Certification, ContactMessage, Education, Experience, Media, Profile, Project,
    ProjectCategory, Resume, Skill, SkillCategory, WebsiteSetting,
)
from .routes_auth import admin_required
from .services import (
    delete_file, get_settings, media_url, next_position, publish_snapshot, save_settings,
    serialize, store_upload, unique_slug,
)
from .validation import (
    CERTIFICATION_SCHEMA, EDUCATION_SCHEMA, EXPERIENCE_SCHEMA,
    MESSAGE_UPDATE_SCHEMA, PROFILE_SCHEMA, PROJECT_CATEGORY_SCHEMA, PROJECT_SCHEMA,
    SETTINGS_SCHEMA, SKILL_CATEGORY_SCHEMA, SKILL_SCHEMA, ValidationError, clean, slugify,
)

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

RESUME_TRACKS = ("python", "data")

# Declarative description of each managed collection.
RESOURCES = {
    "projects": {
        "model": Project, "schema": PROJECT_SCHEMA, "slug_field": "title",
        "fks": {"image_id": Media},
        "many": {"category_ids": (ProjectCategory, "categories")},
        "search": ("title", "summary"), "position": True,
    },
    "project-categories": {
        "model": ProjectCategory, "schema": PROJECT_CATEGORY_SCHEMA, "slug_field": "name",
        "fks": {}, "search": ("name",), "position": True,
    },
    "skill-categories": {
        "model": SkillCategory, "schema": SKILL_CATEGORY_SCHEMA,
        "fks": {}, "search": ("name",), "position": True,
    },
    "skills": {
        "model": Skill, "schema": SKILL_SCHEMA,
        "fks": {"category_id": SkillCategory}, "search": ("name",), "position": True,
    },
    "experience": {
        "model": Experience, "schema": EXPERIENCE_SCHEMA,
        "fks": {}, "search": ("organization", "role"), "position": True,
    },
    "education": {
        "model": Education, "schema": EDUCATION_SCHEMA,
        "fks": {}, "search": ("institution", "qualification"), "position": True,
    },
    "certifications": {
        "model": Certification, "schema": CERTIFICATION_SCHEMA,
        "fks": {"media_id": Media}, "search": ("name", "issuer"), "position": True,
    },
    "messages": {
        "model": ContactMessage, "schema": MESSAGE_UPDATE_SCHEMA,
        "fks": {}, "search": ("name", "email", "message"), "position": False,
        "creatable": False, "publishes": False, "newest_first": True,
    },
}

def _resource(name):
    config = RESOURCES.get(name)
    if config is None:
        abort(404)
    return config


def _admin_view(resource, obj):
    data = serialize(obj)
    if resource == "projects":
        data["image_url"] = media_url(obj.image)
        data["category_ids"] = [c.id for c in obj.categories]
        data["category_names"] = [c.name for c in obj.categories]
    if resource == "certifications":
        data["media_url"] = media_url(obj.media)
    return data


def _check_foreign_keys(config, cleaned):
    errors = {}
    for field, model in config["fks"].items():
        value = cleaned.get(field)
        if value is not None and db.session.get(model, value) is None:
            errors[field] = "The selected item no longer exists."
    for field, (model, _attr) in config.get("many", {}).items():
        ids = cleaned.get(field) or []
        if ids and db.session.query(model.id).filter(model.id.in_(ids)).count() != len(ids):
            errors[field] = "One of the selected categories no longer exists."
    if errors:
        raise ValidationError(errors)


def _apply(config, obj, cleaned, creating):
    model = config["model"]
    for key, value in cleaned.items():
        if key in ("slug", "position"):
            continue
        if key in config.get("many", {}):
            related_model, attr = config["many"][key]
            ids = value or []
            setattr(obj, attr, related_model.query.filter(related_model.id.in_(ids)).all() if ids else [])
            continue
        column = model.__table__.columns.get(key)
        if value is None and column is not None and not column.nullable:
            value = ""  # blank text is stored as an empty string, never NULL
        setattr(obj, key, value)

    if config.get("slug_field"):
        if creating or cleaned.get("slug"):
            wanted = cleaned.get("slug") or slugify(getattr(obj, config["slug_field"]) or "")
            obj.slug = unique_slug(model, wanted, exclude_id=obj.id)

    if config["position"]:
        if cleaned.get("position") is not None:
            obj.position = cleaned["position"]
        elif creating:
            obj.position = next_position(model)


def _commit(config):
    """Commit, republishing the public snapshot when the content is public."""
    try:
        if config.get("publishes", True):
            publish_snapshot()
        else:
            db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error(409, "An item with that name already exists.")
    return None


# ------------------------------------------------------------- generic CRUD

@bp.get("/<resource>")
@admin_required
def list_items(resource):
    config = _resource(resource)
    model = config["model"]
    if config.get("newest_first"):
        query = model.query.order_by(model.created_at.desc(), model.id.desc())
    else:
        query = model.query.order_by(model.position, model.id)

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(*[getattr(model, f).ilike(like) for f in config["search"]]))
    if resource == "messages" and request.args.get("unread") == "1":
        query = query.filter(model.is_read.is_(False))

    return jsonify({"items": [_admin_view(resource, obj) for obj in query.all()]})


@bp.post("/<resource>")
@admin_required
def create_item(resource):
    config = _resource(resource)
    if not config.get("creatable", True):
        abort(405)
    cleaned = clean(config["schema"], request.get_json(silent=True))
    _check_foreign_keys(config, cleaned)

    obj = config["model"]()
    _apply(config, obj, cleaned, creating=True)
    db.session.add(obj)
    conflict = _commit(config)
    if conflict:
        return conflict
    return jsonify(_admin_view(resource, obj)), 201


@bp.get("/<resource>/<int:item_id>")
@admin_required
def get_item(resource, item_id):
    config = _resource(resource)
    obj = db.session.get(config["model"], item_id)
    if obj is None:
        abort(404)
    return jsonify(_admin_view(resource, obj))


@bp.put("/<resource>/<int:item_id>")
@admin_required
def update_item(resource, item_id):
    config = _resource(resource)
    obj = db.session.get(config["model"], item_id)
    if obj is None:
        abort(404)
    cleaned = clean(config["schema"], request.get_json(silent=True), partial=True)
    _check_foreign_keys(config, cleaned)
    _apply(config, obj, cleaned, creating=False)
    conflict = _commit(config)
    if conflict:
        return conflict
    return jsonify(_admin_view(resource, obj))


@bp.delete("/<resource>/<int:item_id>")
@admin_required
def delete_item(resource, item_id):
    config = _resource(resource)
    obj = db.session.get(config["model"], item_id)
    if obj is None:
        abort(404)
    db.session.delete(obj)
    conflict = _commit(config)
    if conflict:
        return conflict
    return jsonify({"ok": True})


@bp.post("/<resource>/reorder")
@admin_required
def reorder_items(resource):
    config = _resource(resource)
    if not config["position"]:
        abort(405)
    data = request.get_json(silent=True) or {}
    ids = data.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise ValidationError({"ids": "Provide a list of item ids."})
    model = config["model"]
    items = {obj.id: obj for obj in model.query.filter(model.id.in_(ids)).all()}
    for index, item_id in enumerate(ids, start=1):
        if item_id in items:
            items[item_id].position = index
    conflict = _commit(config)
    if conflict:
        return conflict
    return jsonify({"ok": True})


# ---------------------------------------------------------- singletons

def _profile_view(profile):
    data = serialize(profile, exclude=("photo_id",))
    data["photo_id"] = profile.photo_id
    data["photo_url"] = media_url(profile.photo)
    return data


@bp.get("/profile")
@admin_required
def get_profile():
    profile = Profile.query.first()
    if profile is None:
        return jsonify({"id": None, "name": "", "headline": "", "photo_id": None, "photo_url": None})
    return jsonify(_profile_view(profile))


@bp.put("/profile")
@admin_required
def put_profile():
    cleaned = clean(PROFILE_SCHEMA, request.get_json(silent=True), partial=True)
    _check_foreign_keys({"fks": {"photo_id": Media}}, cleaned)
    profile = Profile.query.first()
    if profile is None:
        profile = Profile()
        db.session.add(profile)
    for key, value in cleaned.items():
        column = Profile.__table__.columns.get(key)
        if value is None and column is not None and not column.nullable:
            value = ""
        setattr(profile, key, value)
    publish_snapshot()
    return jsonify(_profile_view(profile))


@bp.get("/settings")
@admin_required
def get_settings_route():
    return jsonify(get_settings())


@bp.put("/settings")
@admin_required
def put_settings():
    cleaned = clean(SETTINGS_SCHEMA, request.get_json(silent=True), partial=True)
    save_settings(cleaned)
    publish_snapshot()
    return jsonify(get_settings())


# --------------------------------------------------------------- overview

@bp.get("/overview")
@admin_required
def overview():
    def counts(model):
        total = model.query.count()
        published = model.query.filter_by(is_published=True).count() if hasattr(model, "is_published") else total
        return {"total": total, "published": published, "draft": total - published}

    recent = []
    labels = [
        (Project, "Project", lambda o: o.title),
        (Skill, "Skill", lambda o: o.name),
        (Experience, "Experience", lambda o: f"{o.role}, {o.organization}"),
        (Education, "Education", lambda o: o.institution),
        (Certification, "Certification", lambda o: o.name),
    ]
    for model, label, title_of in labels:
        for obj in model.query.order_by(model.updated_at.desc()).limit(8).all():
            recent.append({"type": label, "title": title_of(obj), "updated_at": obj.updated_at.isoformat()})
    recent.sort(key=lambda r: r["updated_at"], reverse=True)

    return jsonify({
        "projects": counts(Project),
        "skills": {"total": Skill.query.count()},
        "certifications": counts(Certification),
        "experience": counts(Experience),
        "education": counts(Education),
        "media": Media.query.count(),
        "unread_messages": ContactMessage.query.filter_by(is_read=False).count(),
        "recent_updates": recent[:10],
    })


# ------------------------------------------------------------------ media

def _media_view(media):
    data = serialize(media, exclude=("storage_key",))
    data["url"] = media_url(media)
    return data


@bp.get("/media")
@admin_required
def list_media():
    query = Media.query.order_by(Media.created_at.desc())
    kind = request.args.get("kind")
    if kind in ("image", "pdf"):
        query = query.filter_by(kind=kind)
    return jsonify({"items": [_media_view(m) for m in query.all()]})


def _uploaded_file():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise ValidationError({"file": "Choose a file to upload."})
    return upload


@bp.post("/media")
@admin_required
def upload_media():
    upload = _uploaded_file()
    try:
        media = store_upload(upload.read(), upload.filename, ("png", "jpg", "webp", "pdf"),
                             alt_text=request.form.get("alt_text", ""))
    except ValueError as exc:
        raise ValidationError({"file": str(exc)})
    db.session.add(media)
    publish_snapshot()
    return jsonify(_media_view(media)), 201


@bp.put("/media/<int:media_id>")
@admin_required
def replace_media(media_id):
    media = db.session.get(Media, media_id)
    if media is None:
        abort(404)
    if "alt_text" in request.form:
        media.alt_text = request.form.get("alt_text", "")[:255]
    old_key = None
    if request.files.get("file") and request.files["file"].filename:
        upload = request.files["file"]
        try:
            replacement = store_upload(upload.read(), upload.filename, ("png", "jpg", "webp", "pdf"))
        except ValueError as exc:
            raise ValidationError({"file": str(exc)})
        old_key = media.storage_key
        media.kind = replacement.kind
        media.original_name = replacement.original_name
        media.storage_key = replacement.storage_key
        media.mime_type = replacement.mime_type
        media.size_bytes = replacement.size_bytes
    publish_snapshot()
    delete_file(old_key)
    return jsonify(_media_view(media))


@bp.delete("/media/<int:media_id>")
@admin_required
def delete_media(media_id):
    media = db.session.get(Media, media_id)
    if media is None:
        abort(404)
    Profile.query.filter_by(photo_id=media.id).update({"photo_id": None})
    Project.query.filter_by(image_id=media.id).update({"image_id": None})
    Certification.query.filter_by(media_id=media.id).update({"media_id": None})
    Resume.query.filter_by(media_id=media.id).delete()
    key = media.storage_key
    db.session.delete(media)
    publish_snapshot()
    delete_file(key)
    return jsonify({"ok": True})


# ---------------------------------------------------------------- resumes

def _resume_view(resume):
    return {
        "id": resume.id, "track": resume.track, "label": resume.label,
        "is_active": resume.is_active, "media_id": resume.media_id,
        "file_name": resume.media.original_name if resume.media else None,
        "url": media_url(resume.media), "updated_at": resume.updated_at.isoformat(),
    }


@bp.get("/resumes")
@admin_required
def list_resumes():
    rows = Resume.query.order_by(Resume.track, Resume.id).all()
    return jsonify({"items": [_resume_view(r) for r in rows], "tracks": list(RESUME_TRACKS)})


@bp.post("/resumes")
@admin_required
def create_resume():
    track = (request.form.get("track") or "").strip()
    if track not in RESUME_TRACKS:
        raise ValidationError({"track": "Choose Python Developer or Data Analyst."})
    upload = _uploaded_file()
    try:
        media = store_upload(upload.read(), upload.filename, ("pdf",))
    except ValueError as exc:
        raise ValidationError({"file": str(exc)})
    label = (request.form.get("label") or "").strip()[:120] or (
        "Python Software Developer Resume" if track == "python" else "Data Analyst Resume"
    )
    is_first = Resume.query.filter_by(track=track, is_active=True).first() is None
    db.session.add(media)
    db.session.flush()
    resume = Resume(track=track, label=label, media=media, is_active=is_first)
    db.session.add(resume)
    publish_snapshot()
    return jsonify(_resume_view(resume)), 201


@bp.put("/resumes/<int:resume_id>")
@admin_required
def update_resume(resume_id):
    resume = db.session.get(Resume, resume_id)
    if resume is None:
        abort(404)
    if request.files.get("file") and request.files["file"].filename:
        upload = request.files["file"]
        try:
            replacement = store_upload(upload.read(), upload.filename, ("pdf",))
        except ValueError as exc:
            raise ValidationError({"file": str(exc)})
        media = resume.media
        old_key = media.storage_key
        media.original_name = replacement.original_name
        media.storage_key = replacement.storage_key
        media.mime_type = replacement.mime_type
        media.size_bytes = replacement.size_bytes
        db.session.flush()
        publish_snapshot()
        delete_file(old_key)
        return jsonify(_resume_view(resume))

    data = request.get_json(silent=True) or {}
    if "label" in data:
        resume.label = str(data["label"]).strip()[:120]
    if "is_active" in data:
        if data["is_active"]:
            # Deactivate the current default first so the unique index holds.
            Resume.query.filter(
                Resume.track == resume.track, Resume.id != resume.id
            ).update({"is_active": False}, synchronize_session=False)
            resume.is_active = True
        else:
            resume.is_active = False
    publish_snapshot()
    return jsonify(_resume_view(resume))


@bp.delete("/resumes/<int:resume_id>")
@admin_required
def delete_resume(resume_id):
    resume = db.session.get(Resume, resume_id)
    if resume is None:
        abort(404)
    media = resume.media
    key = media.storage_key if media else None
    db.session.delete(resume)
    if media is not None:
        db.session.delete(media)
    publish_snapshot()
    delete_file(key)
    return jsonify({"ok": True})
