"""Shared business logic: publishing snapshot, storage, uploads and settings."""
import os
import uuid
from datetime import datetime, timezone

from flask import current_app

from .extensions import db
from .models import (
    Certification, Education, Experience, Media, PublishedContent, Profile,
    Project, ProjectCategory, Resume, Skill, SkillCategory, WebsiteSetting,
)
from .validation import SETTINGS_DEFAULTS, SETTINGS_SCHEMA, check_upload, slugify

SNAPSHOT_KEY = "site"


# ------------------------------------------------------------------ storage

def _s3_client():
    import boto3  # imported lazily: only needed for the S3 backend
    return boto3.client("s3")


def write_file(key, raw, mime_type):
    if current_app.config["STORAGE_BACKEND"] == "s3":
        _s3_client().put_object(
            Bucket=current_app.config["S3_BUCKET"], Key=key, Body=raw,
            ContentType=mime_type, CacheControl="public, max-age=31536000, immutable",
        )
        return
    directory = current_app.config["UPLOAD_DIR"]
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, key), "wb") as fh:
        fh.write(raw)


def delete_file(key):
    if not key:
        return
    if current_app.config["STORAGE_BACKEND"] == "s3":
        _s3_client().delete_object(Bucket=current_app.config["S3_BUCKET"], Key=key)
        return
    path = os.path.join(current_app.config["UPLOAD_DIR"], key)
    if os.path.isfile(path):
        os.remove(path)


def media_url(media):
    if media is None:
        return None
    if current_app.config["STORAGE_BACKEND"] == "s3":
        return f"{current_app.config['S3_PUBLIC_BASE_URL']}/{media.storage_key}"
    return f"{current_app.config['API_PUBLIC_URL']}/media/{media.storage_key}"


def store_upload(raw, original_name, allowed_kinds, alt_text=""):
    """Validate bytes, store them, and return a new (uncommitted) Media row."""
    ext, mime = check_upload(raw, allowed_kinds, current_app.config["MAX_UPLOAD_BYTES"])
    key = f"{uuid.uuid4().hex}.{ext}"
    write_file(key, raw, mime)
    return Media(
        kind="pdf" if ext == "pdf" else "image",
        original_name=(original_name or key)[:255], storage_key=key,
        mime_type=mime, size_bytes=len(raw), alt_text=(alt_text or "")[:255],
    )


# ----------------------------------------------------------------- helpers

def serialize(obj, exclude=()):
    data = {}
    for column in obj.__table__.columns:
        if column.name in exclude:
            continue
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        data[column.name] = value
    return data


def next_position(model, extra_filter=None):
    query = db.session.query(db.func.max(model.position))
    if extra_filter is not None:
        query = query.filter(extra_filter)
    current = query.scalar()
    return (current or 0) + 1


def unique_slug(model, base, exclude_id=None):
    slug = base
    counter = 2
    while True:
        query = model.query.filter(model.slug == slug)
        if exclude_id is not None:
            query = query.filter(model.id != exclude_id)
        if query.first() is None:
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def get_settings():
    values = dict(SETTINGS_DEFAULTS)
    for row in WebsiteSetting.query.all():
        if row.key in SETTINGS_SCHEMA:
            values[row.key] = row.value
    return values


def save_settings(cleaned):
    for key, value in cleaned.items():
        row = db.session.get(WebsiteSetting, key) or WebsiteSetting(key=key)
        row.value = value
        db.session.add(row)


# ------------------------------------------------------- publishing snapshot

def _project_dict(project):
    return {
        "id": project.id,
        "title": project.title,
        "slug": project.slug,
        "categories": [
            {"id": c.id, "name": c.name, "slug": c.slug} for c in project.categories
        ],
        "summary": project.summary,
        "problem": project.problem,
        "solution": project.solution,
        "details": project.details,
        "technologies": project.technologies or [],
        "features": project.features or [],
        "outcomes": project.outcomes or [],
        "github_url": project.github_url,
        "live_url": project.live_url,
        "image": _media_dict(project.image),
        "modes": project.modes or [],
        "featured": bool(project.featured),
        "position": project.position,
    }


def _media_dict(media):
    if media is None:
        return None
    return {"url": media_url(media), "alt": media.alt_text or "", "kind": media.kind}


def _used_categories(projects):
    """Only categories with at least one published project appear as filters."""
    used = {c.id: c for p in projects for c in p.categories}
    ordered = sorted(used.values(), key=lambda c: (c.position, c.id))
    return [{"id": c.id, "name": c.name, "slug": c.slug} for c in ordered]


def build_public_payload():
    """Only published content goes in here. Drafts are never included."""
    profile = Profile.query.first()
    profile_data = {}
    if profile:
        profile_data = {
            "name": profile.name, "headline": profile.headline,
            "primary_title": profile.primary_title, "secondary_title": profile.secondary_title,
            "bio": profile.bio, "intro_developer": profile.intro_developer,
            "intro_analyst": profile.intro_analyst, "email": profile.email,
            "phone": profile.phone, "location": profile.location,
            "linkedin_url": profile.linkedin_url, "github_url": profile.github_url,
            "photo": _media_dict(profile.photo),
        }

    projects = (
        Project.query.filter_by(is_published=True)
        .order_by(Project.position, Project.id).all()
    )

    skill_groups = []
    for group in SkillCategory.query.order_by(SkillCategory.position, SkillCategory.id).all():
        if not group.is_published:
            continue
        skills = [s.name for s in group.skills if s.is_published]
        if skills:
            skill_groups.append({
                "id": group.id, "name": group.name, "modes": group.modes or [],
                "position": group.position, "skills": skills,
            })

    resumes = {}
    for row in Resume.query.filter_by(is_active=True).all():
        resumes[row.track] = {"label": row.label, "url": media_url(row.media)}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile_data,
        "settings": get_settings(),
        "project_categories": _used_categories(projects),
        "projects": [_project_dict(p) for p in projects],
        "skill_categories": skill_groups,
        "experience": [
            {
                "organization": e.organization, "role": e.role, "location": e.location,
                "employment_type": e.employment_type, "start_label": e.start_label,
                "end_label": e.end_label, "responsibilities": e.responsibilities or [],
            }
            for e in Experience.query.filter_by(is_published=True)
            .order_by(Experience.position, Experience.id).all()
        ],
        "education": [
            {
                "institution": e.institution, "qualification": e.qualification,
                "location": e.location, "period": e.period, "details": e.details,
            }
            for e in Education.query.filter_by(is_published=True)
            .order_by(Education.position, Education.id).all()
        ],
        "certifications": [
            {
                "name": c.name, "issuer": c.issuer, "issued_label": c.issued_label,
                "verification_url": c.verification_url,
                "file": _media_dict(c.media),
            }
            for c in Certification.query.filter_by(is_published=True)
            .order_by(Certification.position, Certification.id).all()
        ],
        "resumes": resumes,
    }


def publish_snapshot():
    """Rebuild the live snapshot and commit it together with the pending changes.

    Every admin write calls this, so the public site can only ever show
    content that was published at the moment of the last save.
    """
    payload = build_public_payload()
    row = PublishedContent.query.filter_by(key=SNAPSHOT_KEY).first()
    if row is None:
        row = PublishedContent(key=SNAPSHOT_KEY, payload=payload, version=1)
    else:
        row.payload = payload
        row.version = (row.version or 0) + 1
        row.published_at = datetime.now(timezone.utc)
    db.session.add(row)
    db.session.commit()
    return row


def snapshot_etag():
    row = PublishedContent.query.filter_by(key=SNAPSHOT_KEY).first()
    return (row.version if row else 0), row


# ------------------------------------------------------- catalogue sync

CATALOGUE_VERSION = "2"
CATALOGUE_KEY = "catalogue_version"


def sync_catalogue(content):
    """Bring projects and project categories in line with the catalogue file.

    Safe to run more than once, and it never deletes anything. Existing records
    are matched by title or by a legacy title. Text the administrator has
    already written is kept: text fields are filled only when they are blank.
    Title, categories, career views, links, order and published state come
    from the catalogue file.
    """
    categories = {}
    for item in content["project_categories"]:
        row = ProjectCategory.query.filter_by(name=item["name"]).first()
        if row is None:
            row = ProjectCategory(
                name=item["name"], slug=unique_slug(ProjectCategory, slugify(item["name"])),
            )
            db.session.add(row)
        row.position = item["position"]
        categories[item["name"]] = row
    db.session.flush()

    for item in content["projects"]:
        names = [item["title"], *item.get("legacy_titles", [])]
        project = Project.query.filter(Project.title.in_(names)).first()
        if project is None:
            project = Project(slug=unique_slug(Project, slugify(item["title"])))
            db.session.add(project)
        project.title = item["title"]
        for field in ("summary", "problem", "solution", "details"):
            if not getattr(project, field) and item.get(field):
                setattr(project, field, item[field])
        for field in ("technologies", "features", "outcomes"):
            if not getattr(project, field) and item.get(field):
                setattr(project, field, item[field])
        for field in ("github_url", "live_url"):
            if item.get(field):
                setattr(project, field, item[field])
        project.categories = [categories[name] for name in item["categories"]]
        project.modes = item["modes"]
        project.featured = item["featured"]
        project.position = item["position"]
        project.is_published = item["is_published"]
    db.session.flush()

    marker = db.session.get(WebsiteSetting, CATALOGUE_KEY) or WebsiteSetting(key=CATALOGUE_KEY)
    marker.value = CATALOGUE_VERSION
    db.session.add(marker)
