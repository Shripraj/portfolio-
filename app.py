"""
Shridhar Patil — Personal Portfolio
Flask backend: public site + JSON-driven content + secure admin dashboard.
"""

import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory, abort, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
app.config["DATABASE"] = os.path.join(BASE_DIR, "database", "portfolio.db")
app.config["SCHEMA"] = os.path.join(BASE_DIR, "database", "schema.sql")

app.config["CERT_UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "images", "certificates")
app.config["PROJECT_UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "images", "projects")
app.config["RESUME_UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "resume")

app.config["ALLOWED_IMAGE_EXT"] = {"png", "jpg", "jpeg", "webp", "gif"}
app.config["ALLOWED_RESUME_EXT"] = {"pdf"}
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload cap

DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")

SOCIAL_LINKS = {
    "github": "https://github.com/Shripraj/Shridhar-Patil",
    "linkedin": "https://www.linkedin.com/in/patilshridhar",
    "email": "patilshridhar1301@gmail.com",
}

CONTACT_INFO = {
    "phone": "+91 9591081475",
    "email": "patilshridhar1301@gmail.com",
    "location": "Bengaluru, Karnataka",
}

TITLES = [
    "Computer Science Engineering Student",
    "Python Developer",
    "Data Analyst",
]

# Fixed project categories — used for the admin "group" dropdown and the
# public filter tabs, so new projects automatically slot into the right group.
PROJECT_CATEGORIES = [
    "Data Analysis",
    "Data Science",
    "Machine Learning",
    "Web Development",
]

# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables (if needed) and seed initial content."""
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    with open(app.config["SCHEMA"], "r") as f:
        db.executescript(f.read())

    # --- Migration: add `category` column to projects if upgrading from an
    # older database created before this feature existed ---
    existing_cols = [row["name"] for row in db.execute("PRAGMA table_info(projects)").fetchall()]
    if "category" not in existing_cols:
        db.execute("ALTER TABLE projects ADD COLUMN category TEXT NOT NULL DEFAULT 'Data Analysis'")
        db.commit()

    # --- Migration: gallery tables for multi-photo certificates/projects ---
    # Each row is one image belonging to one certificate/project. The
    # existing `certificates.image` / `projects.image` column is kept as the
    # "cover" image (first upload) for backward compatibility with anything
    # that only expects a single image.
    db.executescript("""
        CREATE TABLE IF NOT EXISTS certificate_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS project_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
    """)
    db.commit()

    # Seed admin user
    cur = db.execute("SELECT COUNT(*) AS c FROM admin")
    if cur.fetchone()["c"] == 0:
        db.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            (DEFAULT_ADMIN_USERNAME, generate_password_hash(DEFAULT_ADMIN_PASSWORD)),
        )

    # Seed settings (About text + hero intro)
    default_settings = {
        "about_text": (
            "I am a Computer Science Engineering student passionate about Python "
            "development, Data Analytics, Flask web development, SQL databases, "
            "Power BI, and solving real-world business problems through technology."
        ),
        "hero_intro": (
            "I build clean Python applications and turn raw data into decisions — "
            "blending backend engineering with analytical thinking."
        ),
        "site_name": "Shridhar Patil",
    }
    for key, value in default_settings.items():
        cur = db.execute("SELECT 1 FROM settings WHERE key = ?", (key,))
        if not cur.fetchone():
            db.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

    # Seed skills
    cur = db.execute("SELECT COUNT(*) AS c FROM skills")
    if cur.fetchone()["c"] == 0:
        skills = [
            ("Programming", "Python", 90, "fa-brands fa-python"),
            ("Web", "Flask", 82, "fa-solid fa-flask"),
            ("Databases", "MySQL", 78, "fa-solid fa-database"),
            ("Databases", "PostgreSQL", 74, "fa-solid fa-database"),
            ("Data Analysis", "NumPy", 82, "fa-solid fa-chart-line"),
            ("Data Analysis", "Pandas", 85, "fa-solid fa-table"),
            ("Data Analysis", "Excel", 88, "fa-solid fa-file-excel"),
            ("Data Analysis", "Power BI", 84, "fa-solid fa-chart-pie"),
            ("Data Analysis", "Data Visualization", 83, "fa-solid fa-chart-simple"),
            ("Data Analysis", "Data Cleaning", 80, "fa-solid fa-broom"),
            ("Data Analysis", "Exploratory Data Analysis", 81, "fa-solid fa-magnifying-glass-chart"),
            ("Tools", "VS Code", 90, "fa-solid fa-code"),
            ("Tools", "PyCharm", 80, "fa-solid fa-laptop-code"),
            ("Tools", "Git", 85, "fa-brands fa-git-alt"),
            ("Tools", "GitHub", 88, "fa-brands fa-github"),
            ("Tools", "Jupyter Notebook", 82, "fa-solid fa-book"),
        ]
        for i, (cat, name, prof, icon) in enumerate(skills):
            db.execute(
                "INSERT INTO skills (category, name, proficiency, icon, sort_order) VALUES (?, ?, ?, ?, ?)",
                (cat, name, prof, icon, i),
            )

    # Seed projects
    cur = db.execute("SELECT COUNT(*) AS c FROM projects")
    if cur.fetchone()["c"] == 0:
        projects = [
            (
                "Gender Pay Equality Analysis",
                "Performed analysis on employee salary data using Excel and Power BI. "
                "Created dashboards to identify pay inequality and business insights.",
                "Excel, Power BI",
                "Data Analysis",
                None, "#", "https://github.com/Shripraj/Shridhar-Patil",
            ),
            (
                "Retail Business Data Analysis",
                "Analyzed retail business data using Excel and Power BI to identify revenue "
                "trends, customer segments, and high-performing regions.",
                "Excel, Power BI",
                "Data Analysis",
                None, "#", "https://github.com/Shripraj/Shridhar-Patil",
            ),
        ]
        for i, (title, desc, tech, category, image, purl, gurl) in enumerate(projects):
            db.execute(
                """INSERT INTO projects (title, description, technologies, category, image, project_url, github_url, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, desc, tech, category, image, purl, gurl, i),
            )

    # Seed certificates
    cur = db.execute("SELECT COUNT(*) AS c FROM certificates")
    if cur.fetchone()["c"] == 0:
        certs = [
            ("Deloitte Australia Data Analytics Job Simulation", "Deloitte Australia", "2025", None, "#"),
            ("Tata Data Visualisation: Empowering Business with Effective Insights", "Tata (Forage)", "2025", None, "#"),
            ("Git and GitHub", "Simplilearn", "2025", None, "#"),
        ]
        for i, (name, org, date, image, url) in enumerate(certs):
            db.execute(
                """INSERT INTO certificates (name, organization, completion_date, image, certificate_url, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, org, date, image, url, i),
            )

    # Seed education
    cur = db.execute("SELECT COUNT(*) AS c FROM education")
    if cur.fetchone()["c"] == 0:
        edu = [
            ("B.E.", "Computer Science Engineering", "S.G. Balekundri Institute of Technology", "Graduation: 2027"),
            ("PUC", None, "Alva's PU College", "79.16%"),
            ("SSLC", None, "Alva's English Medium School", "87.52%"),
        ]
        for i, (degree, field, inst, meta) in enumerate(edu):
            db.execute(
                "INSERT INTO education (degree, field, institution, meta, sort_order) VALUES (?, ?, ?, ?, ?)",
                (degree, field, inst, meta, i),
            )

    db.commit()
    db.close()


def get_setting(key, default=""):
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def get_certificate_gallery(cert_id):
    """All images for a certificate (id + url), in upload order (cover image included)."""
    db = get_db()
    rows = db.execute(
        "SELECT id, filename FROM certificate_images WHERE certificate_id = ? ORDER BY sort_order, id",
        (cert_id,),
    ).fetchall()
    return [{"id": r["id"], "url": url_for("certificate_file", filename=r["filename"])} for r in rows]


def get_project_gallery(project_id):
    """All images for a project (id + url), in upload order (cover image included)."""
    db = get_db()
    rows = db.execute(
        "SELECT id, filename FROM project_images WHERE project_id = ? ORDER BY sort_order, id",
        (project_id,),
    ).fetchall()
    return [{"id": r["id"], "url": url_for("static", filename="images/projects/" + r["filename"])} for r in rows]


# --------------------------------------------------------------------------
# Auth helpers
# --------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the admin dashboard.", "warning")
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename, allowed_ext):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_ext


def save_upload(file_storage, folder, allowed_ext, prefix=""):
    """Save a single uploaded file safely and return its stored filename, or None."""
    if not file_storage or file_storage.filename == "":
        return None
    filename = secure_filename(file_storage.filename)
    if not allowed_file(filename, allowed_ext):
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    stored_name = f"{prefix}{timestamp}_{filename}"
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, stored_name))
    return stored_name


def save_uploads(file_storages, folder, allowed_ext, prefix=""):
    """Save multiple uploaded files. Returns the list of stored filenames
    (invalid/empty entries are silently skipped)."""
    stored = []
    for file_storage in file_storages or []:
        name = save_upload(file_storage, folder, allowed_ext, prefix=prefix)
        if name:
            stored.append(name)
    return stored


# --------------------------------------------------------------------------
# Public routes
# --------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    skills_rows = db.execute("SELECT * FROM skills ORDER BY category, sort_order").fetchall()
    skills_by_category = {}
    for row in skills_rows:
        skills_by_category.setdefault(row["category"], []).append(row)

    project_rows = db.execute("SELECT * FROM projects ORDER BY sort_order, id").fetchall()
    projects = [dict(p, images=get_project_gallery(p["id"])) for p in project_rows]

    projects_by_category = {}
    for p in projects:
        projects_by_category.setdefault(p["category"], []).append(p)
    # Keep a stable, predictable tab order: fixed categories first, then any
    # custom category an admin might type in later, in first-seen order.
    category_order = [c for c in PROJECT_CATEGORIES if c in projects_by_category]
    category_order += [c for c in projects_by_category if c not in category_order]

    cert_rows = db.execute("SELECT * FROM certificates ORDER BY sort_order, id").fetchall()
    certificates = [dict(c, images=get_certificate_gallery(c["id"])) for c in cert_rows]

    education = db.execute("SELECT * FROM education ORDER BY sort_order, id").fetchall()
    resume = db.execute(
        "SELECT * FROM resume WHERE is_active = 1 ORDER BY uploaded_at DESC LIMIT 1"
    ).fetchone()

    return render_template(
        "index.html",
        site_name=get_setting("site_name", "Shridhar Patil"),
        about_text=get_setting("about_text"),
        hero_intro=get_setting("hero_intro"),
        titles=TITLES,
        skills_by_category=skills_by_category,
        projects=projects,
        projects_by_category=projects_by_category,
        project_categories=category_order,
        certificates=certificates,
        education=education,
        resume=resume,
        social=SOCIAL_LINKS,
        contact=CONTACT_INFO,
    )


@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    subject = request.form.get("subject", "").strip()
    message = request.form.get("message", "").strip()

    errors = []
    if not name:
        errors.append("Name is required.")
    if not email or "@" not in email:
        errors.append("A valid email is required.")
    if not message:
        errors.append("Message cannot be empty.")

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if errors:
        if is_ajax:
            return jsonify({"success": False, "errors": errors}), 400
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("index", _anchor="contact"))

    db = get_db()
    db.execute(
        "INSERT INTO messages (name, email, subject, message) VALUES (?, ?, ?, ?)",
        (name, email, subject, message),
    )
    db.commit()

    if is_ajax:
        return jsonify({"success": True, "message": "Thanks! Your message has been sent."})

    flash("Thanks! Your message has been sent.", "success")
    return redirect(url_for("index", _anchor="contact"))


@app.route("/resume/download")
def resume_download():
    db = get_db()
    resume = db.execute(
        "SELECT * FROM resume WHERE is_active = 1 ORDER BY uploaded_at DESC LIMIT 1"
    ).fetchone()
    if not resume:
        abort(404)
    return send_from_directory(
        app.config["RESUME_UPLOAD_FOLDER"], resume["filename"],
        as_attachment=True, download_name="Shridhar_Patil_Resume.pdf",
    )
@app.route("/resume/preview")
def resume_preview():
    db = get_db()
    resume = db.execute(
        "SELECT * FROM resume WHERE is_active = 1 ORDER BY uploaded_at DESC LIMIT 1"
    ).fetchone()

    if not resume:
        abort(404)

    return send_from_directory(
        app.config["RESUME_UPLOAD_FOLDER"],
        resume["filename"],
        as_attachment=False
    )


@app.route("/certificates/<path:filename>")
def certificate_file(filename):
    return send_from_directory(app.config["CERT_UPLOAD_FOLDER"], filename)


@app.route("/robots.txt")
def robots():
    return app.response_class(
        "User-agent: *\nAllow: /\nSitemap: " + request.url_root + "sitemap.xml\n",
        mimetype="text/plain",
    )


# --------------------------------------------------------------------------
# Admin auth
# --------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        row = db.execute("SELECT * FROM admin WHERE username = ?", (username,)).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = username
            flash("Welcome back!", "success")
            next_url = request.args.get("next") or url_for("admin_dashboard")
            return redirect(next_url)
        flash("Invalid username or password.", "danger")

    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("admin_login"))


# --------------------------------------------------------------------------
# Admin dashboard
# --------------------------------------------------------------------------

@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    stats = {
        "projects": db.execute("SELECT COUNT(*) c FROM projects").fetchone()["c"],
        "certificates": db.execute("SELECT COUNT(*) c FROM certificates").fetchone()["c"],
        "messages": db.execute("SELECT COUNT(*) c FROM messages").fetchone()["c"],
        "unread": db.execute("SELECT COUNT(*) c FROM messages WHERE is_read = 0").fetchone()["c"],
    }
    recent_messages = db.execute(
        "SELECT * FROM messages ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    return render_template("admin/dashboard.html", stats=stats, recent_messages=recent_messages)


@app.route("/admin/about", methods=["GET", "POST"])
@login_required
def admin_about():
    db = get_db()
    if request.method == "POST":
        about_text = request.form.get("about_text", "").strip()
        hero_intro = request.form.get("hero_intro", "").strip()
        site_name = request.form.get("site_name", "").strip()
        db.execute("UPDATE settings SET value = ? WHERE key = 'about_text'", (about_text,))
        db.execute("UPDATE settings SET value = ? WHERE key = 'hero_intro'", (hero_intro,))
        db.execute("UPDATE settings SET value = ? WHERE key = 'site_name'", (site_name,))
        db.commit()
        flash("About section updated.", "success")
        return redirect(url_for("admin_about"))

    return render_template(
        "admin/about.html",
        about_text=get_setting("about_text"),
        hero_intro=get_setting("hero_intro"),
        site_name=get_setting("site_name", "Shridhar Patil"),
    )


@app.route("/admin/skills", methods=["GET", "POST"])
@login_required
def admin_skills():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            db.execute(
                "INSERT INTO skills (category, name, proficiency, icon, sort_order) VALUES (?, ?, ?, ?, ?)",
                (
                    request.form.get("category", "").strip(),
                    request.form.get("name", "").strip(),
                    int(request.form.get("proficiency", 80) or 80),
                    request.form.get("icon", "").strip(),
                    0,
                ),
            )
            flash("Skill added.", "success")
        elif action == "delete":
            db.execute("DELETE FROM skills WHERE id = ?", (request.form.get("skill_id"),))
            flash("Skill removed.", "success")
        db.commit()
        return redirect(url_for("admin_skills"))

    skills = db.execute("SELECT * FROM skills ORDER BY category, sort_order").fetchall()
    return render_template("admin/skills.html", skills=skills)


@app.route("/admin/projects", methods=["GET", "POST"])
@login_required
def admin_projects():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            image_files = request.files.getlist("images")
            stored_list = save_uploads(
                image_files, app.config["PROJECT_UPLOAD_FOLDER"],
                app.config["ALLOWED_IMAGE_EXT"], prefix="proj_",
            )
            cover_image = stored_list[0] if stored_list else None
            category = request.form.get("category", "").strip() or PROJECT_CATEGORIES[0]

            cur = db.execute(
                """INSERT INTO projects (title, description, technologies, category, image, project_url, github_url, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.form.get("title", "").strip(),
                    request.form.get("description", "").strip(),
                    request.form.get("technologies", "").strip(),
                    category,
                    cover_image,
                    request.form.get("project_url", "").strip(),
                    request.form.get("github_url", "").strip(),
                    0,
                ),
            )
            project_id = cur.lastrowid
            for i, fname in enumerate(stored_list):
                db.execute(
                    "INSERT INTO project_images (project_id, filename, sort_order) VALUES (?, ?, ?)",
                    (project_id, fname, i),
                )
            flash(
                f"Project added with {len(stored_list)} photo(s)." if stored_list else "Project added.",
                "success",
            )
        elif action == "add_images":
            # Append more photos to an existing project without editing its other fields.
            project_id = request.form.get("project_id")
            image_files = request.files.getlist("images")
            stored_list = save_uploads(
                image_files, app.config["PROJECT_UPLOAD_FOLDER"],
                app.config["ALLOWED_IMAGE_EXT"], prefix="proj_",
            )
            existing_count = db.execute(
                "SELECT COUNT(*) c FROM project_images WHERE project_id = ?", (project_id,)
            ).fetchone()["c"]
            for i, fname in enumerate(stored_list):
                db.execute(
                    "INSERT INTO project_images (project_id, filename, sort_order) VALUES (?, ?, ?)",
                    (project_id, fname, existing_count + i),
                )
            # If the project had no cover image yet, promote the first new upload.
            row = db.execute("SELECT image FROM projects WHERE id = ?", (project_id,)).fetchone()
            if row and not row["image"] and stored_list:
                db.execute("UPDATE projects SET image = ? WHERE id = ?", (stored_list[0], project_id))
            flash(f"Added {len(stored_list)} photo(s) to the project." if stored_list else "No valid photos uploaded.", "success")
        elif action == "delete_image":
            image_id = request.form.get("image_id")
            project_id = request.form.get("project_id")
            row = db.execute("SELECT filename FROM project_images WHERE id = ?", (image_id,)).fetchone()
            db.execute("DELETE FROM project_images WHERE id = ?", (image_id,))
            if row:
                # If the deleted image was the cover, promote the next remaining image (if any).
                proj = db.execute("SELECT image FROM projects WHERE id = ?", (project_id,)).fetchone()
                if proj and proj["image"] == row["filename"]:
                    next_img = db.execute(
                        "SELECT filename FROM project_images WHERE project_id = ? ORDER BY sort_order, id LIMIT 1",
                        (project_id,),
                    ).fetchone()
                    db.execute(
                        "UPDATE projects SET image = ? WHERE id = ?",
                        (next_img["filename"] if next_img else None, project_id),
                    )
                try:
                    os.remove(os.path.join(app.config["PROJECT_UPLOAD_FOLDER"], row["filename"]))
                except OSError:
                    pass
            flash("Photo removed.", "success")
        elif action == "delete":
            db.execute("DELETE FROM projects WHERE id = ?", (request.form.get("project_id"),))
            flash("Project deleted.", "success")
        db.commit()
        return redirect(url_for("admin_projects"))

    project_rows = db.execute("SELECT * FROM projects ORDER BY sort_order, id").fetchall()
    projects = [dict(p, images=get_project_gallery(p["id"])) for p in project_rows]
    return render_template("admin/projects.html", projects=projects, categories=PROJECT_CATEGORIES)


@app.route("/admin/certificates", methods=["GET", "POST"])
@login_required
def admin_certificates():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            image_files = request.files.getlist("images")
            stored_list = save_uploads(
                image_files, app.config["CERT_UPLOAD_FOLDER"],
                app.config["ALLOWED_IMAGE_EXT"], prefix="cert_",
            )
            cover_image = stored_list[0] if stored_list else None

            cur = db.execute(
                """INSERT INTO certificates (name, organization, completion_date, image, certificate_url, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    request.form.get("name", "").strip(),
                    request.form.get("organization", "").strip(),
                    request.form.get("completion_date", "").strip(),
                    cover_image,
                    request.form.get("certificate_url", "").strip(),
                    0,
                ),
            )
            cert_id = cur.lastrowid
            for i, fname in enumerate(stored_list):
                db.execute(
                    "INSERT INTO certificate_images (certificate_id, filename, sort_order) VALUES (?, ?, ?)",
                    (cert_id, fname, i),
                )
            flash(
                f"Certificate added with {len(stored_list)} photo(s)." if stored_list else "Certificate added.",
                "success",
            )
        elif action == "add_images":
            cert_id = request.form.get("cert_id")
            image_files = request.files.getlist("images")
            stored_list = save_uploads(
                image_files, app.config["CERT_UPLOAD_FOLDER"],
                app.config["ALLOWED_IMAGE_EXT"], prefix="cert_",
            )
            existing_count = db.execute(
                "SELECT COUNT(*) c FROM certificate_images WHERE certificate_id = ?", (cert_id,)
            ).fetchone()["c"]
            for i, fname in enumerate(stored_list):
                db.execute(
                    "INSERT INTO certificate_images (certificate_id, filename, sort_order) VALUES (?, ?, ?)",
                    (cert_id, fname, existing_count + i),
                )
            row = db.execute("SELECT image FROM certificates WHERE id = ?", (cert_id,)).fetchone()
            if row and not row["image"] and stored_list:
                db.execute("UPDATE certificates SET image = ? WHERE id = ?", (stored_list[0], cert_id))
            flash(f"Added {len(stored_list)} photo(s) to the certificate." if stored_list else "No valid photos uploaded.", "success")
        elif action == "delete_image":
            image_id = request.form.get("image_id")
            cert_id = request.form.get("cert_id")
            row = db.execute("SELECT filename FROM certificate_images WHERE id = ?", (image_id,)).fetchone()
            db.execute("DELETE FROM certificate_images WHERE id = ?", (image_id,))
            if row:
                cert = db.execute("SELECT image FROM certificates WHERE id = ?", (cert_id,)).fetchone()
                if cert and cert["image"] == row["filename"]:
                    next_img = db.execute(
                        "SELECT filename FROM certificate_images WHERE certificate_id = ? ORDER BY sort_order, id LIMIT 1",
                        (cert_id,),
                    ).fetchone()
                    db.execute(
                        "UPDATE certificates SET image = ? WHERE id = ?",
                        (next_img["filename"] if next_img else None, cert_id),
                    )
                try:
                    os.remove(os.path.join(app.config["CERT_UPLOAD_FOLDER"], row["filename"]))
                except OSError:
                    pass
            flash("Photo removed.", "success")
        elif action == "replace_image":
            cert_id = request.form.get("cert_id")
            image_file = request.files.get("image")
            stored = save_upload(image_file, app.config["CERT_UPLOAD_FOLDER"],
                                  app.config["ALLOWED_IMAGE_EXT"], prefix="cert_")
            if stored:
                db.execute("UPDATE certificates SET image = ? WHERE id = ?", (stored, cert_id))
                flash("Certificate image replaced.", "success")
        elif action == "delete":
            db.execute("DELETE FROM certificates WHERE id = ?", (request.form.get("cert_id"),))
            flash("Certificate deleted.", "success")
        db.commit()
        return redirect(url_for("admin_certificates"))

    cert_rows = db.execute("SELECT * FROM certificates ORDER BY sort_order, id").fetchall()
    certificates = [dict(c, images=get_certificate_gallery(c["id"])) for c in cert_rows]
    return render_template("admin/certificates.html", certificates=certificates)


@app.route("/admin/resume", methods=["GET", "POST"])
@login_required
def admin_resume():
    db = get_db()
    if request.method == "POST":
        resume_file = request.files.get("resume")
        stored = save_upload(resume_file, app.config["RESUME_UPLOAD_FOLDER"],
                              app.config["ALLOWED_RESUME_EXT"], prefix="resume_")
        if stored:
            db.execute("UPDATE resume SET is_active = 0")
            db.execute(
                "INSERT INTO resume (filename, original_name, is_active) VALUES (?, ?, 1)",
                (stored, secure_filename(resume_file.filename)),
            )
            db.commit()
            flash("Resume uploaded and set as active.", "success")
        else:
            flash("Please upload a valid PDF file.", "danger")
        return redirect(url_for("admin_resume"))

    resumes = db.execute("SELECT * FROM resume ORDER BY uploaded_at DESC").fetchall()
    return render_template("admin/resume.html", resumes=resumes)


@app.route("/admin/messages")
@login_required
def admin_messages():
    db = get_db()
    db.execute("UPDATE messages SET is_read = 1")
    db.commit()
    messages = db.execute("SELECT * FROM messages ORDER BY created_at DESC").fetchall()
    return render_template("admin/messages.html", messages=messages)


@app.route("/admin/messages/<int:message_id>/delete", methods=["POST"])
@login_required
def admin_delete_message(message_id):
    db = get_db()
    db.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    db.commit()
    flash("Message deleted.", "success")
    return redirect(url_for("admin_messages"))


# --------------------------------------------------------------------------
# Error handlers
# --------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# --------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.path.exists(app.config["DATABASE"]):
        init_db()
    else:
        # Ensure schema/seed data exists even if db file already present
        init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
