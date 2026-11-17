"""Public portfolio pages, contact form and admin dashboard page.

Everything is served by the same Flask app as the API. Pages read the published
snapshot straight from the database, so no HTTP calls are needed.
"""
import os
from datetime import datetime, timezone

from flask import abort, make_response, redirect, render_template, request, url_for

from .extensions import db, ratelimit
from .models import ContactMessage, PublishedContent
from .services import SNAPSHOT_KEY, build_public_payload
from .validation import CONTACT_SCHEMA, ValidationError, clean

SITE_URL = os.environ.get("SITE_URL", "http://localhost:5000").rstrip("/")

MODES = {"python": "Python Software Developer", "data": "Data Analyst"}
DEFAULT_MODE = "python"

CONTACT_NOTICES = {
    "sent": ("Thank you. Your message has been sent and I will reply soon.", "ok"),
    "invalid": ("Please check the highlighted fields and try again.", "error"),
    "limit": ("Too many messages from this address. Please try again later.", "error"),
    "unavailable": ("The message could not be sent right now. Please email me directly.", "error"),
}


def load_site():
    """The published snapshot. Drafts are never in it, so they can't leak here."""
    row = PublishedContent.query.filter_by(key=SNAPSHOT_KEY).first()
    if row is not None:
        return row.payload
    return build_public_payload()


def current_mode():
    mode = request.args.get("mode") or request.cookies.get("mode") or DEFAULT_MODE
    return mode if mode in MODES else DEFAULT_MODE


def _mode_rank(project, mode):
    """Projects led by this mode come first, then ones that belong only to it."""
    modes = project.get("modes") or []
    return (mode not in modes, len(modes) != 1, project.get("position", 0))


def build_view(site, mode):
    profile = site.get("profile") or {}
    settings = site.get("settings") or {}
    projects = sorted(site.get("projects", []), key=lambda p: _mode_rank(p, mode))
    skill_groups = sorted(
        site.get("skill_categories", []),
        key=lambda g: (mode not in (g.get("modes") or []), g.get("position", 0)),
    )
    featured = [p for p in projects if p.get("featured") and mode in (p.get("modes") or [])][:4]
    intro = (
        profile.get("intro_developer") if mode == "python" else profile.get("intro_analyst")
    ) or profile.get("bio", "")
    visible = set(settings.get("visible_sections") or [])
    return {
        "profile": profile,
        "settings": settings,
        "projects": projects,
        "featured": featured,
        "skill_groups": skill_groups,
        "categories": site.get("project_categories", []),
        "experience": site.get("experience", []),
        "education": site.get("education", []),
        "certifications": site.get("certifications", []),
        "resume": site.get("resumes", {}).get(mode),
        "resumes": site.get("resumes", {}),
        "intro": intro,
        "mode": mode,
        "mode_label": MODES[mode],
        "modes": MODES,
        "visible": visible,
        "generated_at": site.get("generated_at"),
        "page_title": settings.get("site_title") or profile.get("name", ""),
        "meta_description": settings.get("meta_description", ""),
        "keywords": settings.get("seo_keywords", ""),
        "default_theme": settings.get("default_theme", "light"),
        "headline": settings.get("homepage_headline") or profile.get("headline", ""),
        "homepage_bio": settings.get("homepage_bio") or intro,
    }


def html_error(code, message):
    try:
        site = load_site()
    except Exception:  # the page must still render if content is missing
        site = None
    view = build_view(site or {}, DEFAULT_MODE)
    return make_response(
        render_template("error.html", **view, site=site, code=code, message=message), code,
    )


def _resume_redirect(track):
    resume = load_site().get("resumes", {}).get(track)
    if not resume or not resume.get("url"):
        abort(404)
    return redirect(resume["url"], code=302)


def register_web(app):
    @app.context_processor
    def _globals():
        return {"current_year": datetime.now(timezone.utc).year}

    @app.get("/")
    def index():
        mode = current_mode()
        view = build_view(load_site(), mode)
        everything = view["projects"]
        show_all = request.args.get("all") == "1"
        if not show_all:
            view["projects"] = [p for p in everything if mode in (p.get("modes") or [])]
        view["show_all"] = show_all
        view["all_count"] = len(everything)
        notice = CONTACT_NOTICES.get(request.args.get("contact"))
        response = make_response(render_template(
            "index.html", **view, notice=notice, canonical=f"{SITE_URL}/",
        ))
        if request.args.get("mode") in MODES:
            response.set_cookie(
                "mode", mode, max_age=60 * 60 * 24 * 365, samesite="Lax",
                secure=SITE_URL.startswith("https"),
            )
        return response

    @app.get("/projects/<slug>")
    def project_detail(slug):
        site = load_site()
        projects = site.get("projects", [])
        position = next((i for i, p in enumerate(projects) if p["slug"] == slug), None)
        if position is None:
            abort(404)
        project = projects[position]
        paragraphs = [
            part.strip() for part in (project.get("details") or "").split("\n\n") if part.strip()
        ]
        return render_template(
            "project.html",
            **build_view(site, current_mode()),
            project=project,
            paragraphs=paragraphs,
            previous=projects[position - 1] if position > 0 else None,
            following=projects[position + 1] if position < len(projects) - 1 else None,
            canonical=f"{SITE_URL}/projects/{project['slug']}",
        )

    @app.get("/resume")
    def resume_default():
        return _resume_redirect(current_mode())

    @app.get("/resume/<track>")
    def resume_for_track(track):
        if track not in MODES:
            abort(404)
        return _resume_redirect(track)

    @app.post("/contact")
    def contact():
        ip = request.remote_addr or "unknown"
        if not ratelimit.allow(f"contact:{ip}", limit=5, window_seconds=3600):
            key = "limit"
        else:
            data = {
                "name": request.form.get("name", ""),
                "email": request.form.get("email", ""),
                "message": request.form.get("message", ""),
                "website": request.form.get("website", ""),  # honeypot
            }
            try:
                cleaned = clean(CONTACT_SCHEMA, data)
            except ValidationError:
                key = "invalid"
            else:
                if not cleaned.get("website"):
                    db.session.add(ContactMessage(
                        name=cleaned["name"], email=cleaned["email"], message=cleaned["message"],
                    ))
                    db.session.commit()
                key = "sent"
        return redirect(url_for("index", contact=key, _anchor="contact"), code=303)

    @app.get("/admin")
    def admin_dashboard():
        response = make_response(render_template("admin.html", api_base="", public_url="/"))
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/robots.txt")
    def robots():
        body = f"User-agent: *\nAllow: /\nDisallow: /admin\n\nSitemap: {SITE_URL}/sitemap.xml\n"
        return body, 200, {"Content-Type": "text/plain; charset=utf-8"}

    @app.get("/sitemap.xml")
    def sitemap():
        site = load_site()
        stamp = (site.get("generated_at") or "")[:10]
        urls = [{"loc": f"{SITE_URL}/", "lastmod": stamp}]
        urls += [
            {"loc": f"{SITE_URL}/projects/{p['slug']}", "lastmod": stamp}
            for p in site.get("projects", [])
        ]
        xml = render_template("sitemap.xml", urls=urls)
        return xml, 200, {"Content-Type": "application/xml; charset=utf-8"}
