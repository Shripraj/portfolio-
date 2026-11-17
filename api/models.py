from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Timestamped:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class AdminUser(Timestamped, db.Model):
    __tablename__ = "admin_users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Media(Timestamped, db.Model):
    __tablename__ = "media"
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(16), nullable=False)            # image | pdf
    original_name = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(255), unique=True, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    alt_text = db.Column(db.String(255), nullable=False, default="")


class Profile(Timestamped, db.Model):
    __tablename__ = "profile"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default="")
    headline = db.Column(db.String(255), nullable=False, default="")
    primary_title = db.Column(db.String(120), nullable=False, default="")
    secondary_title = db.Column(db.String(120), nullable=False, default="")
    bio = db.Column(db.Text, nullable=False, default="")
    intro_developer = db.Column(db.Text, nullable=False, default="")
    intro_analyst = db.Column(db.Text, nullable=False, default="")
    email = db.Column(db.String(255), nullable=False, default="")
    phone = db.Column(db.String(30), nullable=False, default="")
    location = db.Column(db.String(120), nullable=False, default="")
    linkedin_url = db.Column(db.String(500))
    github_url = db.Column(db.String(500))
    photo_id = db.Column(db.Integer, db.ForeignKey("media.id", ondelete="SET NULL"))
    photo = db.relationship("Media")


class ProjectCategory(Timestamped, db.Model):
    __tablename__ = "project_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(90), unique=True, nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)


# Many-to-many link: one project can belong to several categories.
project_category_links = db.Table(
    "project_category_links",
    db.Column("project_id", db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("project_categories.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Timestamped, db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    # Legacy single-category column. Kept so no existing data is dropped; not used any more.
    category_id = db.Column(db.Integer, db.ForeignKey("project_categories.id", ondelete="SET NULL"))
    categories = db.relationship(
        "ProjectCategory", secondary=project_category_links, lazy="selectin",
        order_by="ProjectCategory.position",
        backref=db.backref("projects", lazy="selectin"),
    )
    summary = db.Column(db.Text, nullable=False, default="")
    problem = db.Column(db.Text, nullable=False, default="")
    solution = db.Column(db.Text, nullable=False, default="")
    details = db.Column(db.Text, nullable=False, default="")
    technologies = db.Column(db.JSON, nullable=False, default=list)
    features = db.Column(db.JSON, nullable=False, default=list)
    outcomes = db.Column(db.JSON, nullable=False, default=list)
    github_url = db.Column(db.String(500))
    live_url = db.Column(db.String(500))
    image_id = db.Column(db.Integer, db.ForeignKey("media.id", ondelete="SET NULL"))
    image = db.relationship("Media")
    modes = db.Column(db.JSON, nullable=False, default=list)   # career modes this project leads
    featured = db.Column(db.Boolean, nullable=False, default=False)
    is_published = db.Column(db.Boolean, nullable=False, default=False, index=True)
    position = db.Column(db.Integer, nullable=False, default=0, index=True)


class SkillCategory(Timestamped, db.Model):
    __tablename__ = "skill_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    modes = db.Column(db.JSON, nullable=False, default=list)
    position = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, nullable=False, default=True)
    skills = db.relationship("Skill", back_populates="category", order_by="Skill.position")


class Skill(Timestamped, db.Model):
    __tablename__ = "skills"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("skill_categories.id", ondelete="CASCADE"), nullable=False)
    category = db.relationship("SkillCategory", back_populates="skills")
    position = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, nullable=False, default=True)


class Experience(Timestamped, db.Model):
    __tablename__ = "experience"
    id = db.Column(db.Integer, primary_key=True)
    organization = db.Column(db.String(160), nullable=False)
    role = db.Column(db.String(160), nullable=False)
    location = db.Column(db.String(120), nullable=False, default="")
    employment_type = db.Column(db.String(60), nullable=False, default="")
    start_label = db.Column(db.String(40), nullable=False)
    end_label = db.Column(db.String(40), nullable=False, default="")
    responsibilities = db.Column(db.JSON, nullable=False, default=list)
    position = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, nullable=False, default=False)


class Education(Timestamped, db.Model):
    __tablename__ = "education"
    id = db.Column(db.Integer, primary_key=True)
    institution = db.Column(db.String(200), nullable=False)
    qualification = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(120), nullable=False, default="")
    period = db.Column(db.String(60), nullable=False, default="")
    details = db.Column(db.Text, nullable=False, default="")
    position = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, nullable=False, default=False)


class Certification(Timestamped, db.Model):
    __tablename__ = "certifications"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    issuer = db.Column(db.String(160), nullable=False)
    issued_label = db.Column(db.String(60), nullable=False, default="")
    verification_url = db.Column(db.String(500))
    media_id = db.Column(db.Integer, db.ForeignKey("media.id", ondelete="SET NULL"))
    media = db.relationship("Media")
    position = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, nullable=False, default=False)


class Resume(Timestamped, db.Model):
    __tablename__ = "resumes"
    __table_args__ = (
        # At most one active resume per career track, enforced by the database.
        db.Index(
            "uq_resumes_active_track", "track", unique=True,
            sqlite_where=db.text("is_active = 1"),
            postgresql_where=db.text("is_active = true"),
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    track = db.Column(db.String(16), nullable=False)          # python | data
    label = db.Column(db.String(120), nullable=False, default="")
    media_id = db.Column(db.Integer, db.ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    media = db.relationship("Media")
    is_active = db.Column(db.Boolean, nullable=False, default=False)


class ContactMessage(Timestamped, db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)


class WebsiteSetting(db.Model):
    __tablename__ = "website_settings"
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.JSON, nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class PublishedContent(db.Model):
    """Snapshot of everything that is live. The public site reads only this row."""
    __tablename__ = "published_content"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(40), unique=True, nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=0)
    published_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
