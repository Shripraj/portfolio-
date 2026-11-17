import json
import os

import click

from .extensions import db
from .models import (
    AdminUser, Certification, Education, Experience, Profile, Project, ProjectCategory,
    Resume, Skill, SkillCategory, WebsiteSetting,
)
from .services import (
    CATALOGUE_KEY, CATALOGUE_VERSION, publish_snapshot, save_settings, store_upload,
    sync_catalogue, unique_slug,
)
from .validation import SETTINGS_SCHEMA, clean, slugify

SEED_PATH = os.path.join(os.path.dirname(__file__), "seed_data", "content.json")


def register_cli(app):
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(email, password):
        """Create or reset an admin account. There is no public registration."""
        email = email.strip().lower()
        if len(password) < 12:
            raise click.ClickException("Use a password of at least 12 characters.")
        user = AdminUser.query.filter_by(email=email).first()
        if user is None:
            user = AdminUser(email=email)
            db.session.add(user)
        user.set_password(password)
        db.session.commit()
        click.echo(f"Admin account ready: {email}")

    @app.cli.command("sync-catalogue")
    def sync_catalogue_command():
        """Update the eight portfolio projects and their categories. Runs once per version."""
        db.create_all()   # creates the new category link table on existing databases
        marker = db.session.get(WebsiteSetting, CATALOGUE_KEY)
        if marker is not None and marker.value == CATALOGUE_VERSION:
            click.echo("Projects are already up to date.")
            return
        with open(SEED_PATH, encoding="utf-8") as fh:
            content = json.load(fh)
        sync_catalogue(content)
        publish_snapshot()
        click.echo(f"Projects and categories updated (catalogue version {CATALOGUE_VERSION}).")

    @app.cli.command("seed")
    @click.option("--resume-data", type=click.Path(exists=True, dir_okay=False),
                  help="PDF to use as the Data Analyst resume.")
    @click.option("--resume-python", type=click.Path(exists=True, dir_okay=False),
                  help="PDF to use as the Python Software Developer resume.")
    def seed(resume_data, resume_python):
        """Create tables and load the consolidated resume content (only when empty)."""
        db.create_all()
        if Profile.query.first() is None and Project.query.first() is None:
            _seed_content()
            click.echo("Loaded consolidated content from api/seed_data/content.json")
        else:
            click.echo("Content already exists. Skipping sample content.")
        if resume_data:
            _seed_resume("data", resume_data, "Data Analyst Resume")
        if resume_python:
            _seed_resume("python", resume_python, "Python Software Developer Resume")
        publish_snapshot()
        click.echo("Public snapshot published.")


def _seed_content():
    with open(SEED_PATH, encoding="utf-8") as fh:
        content = json.load(fh)

    profile = content["profile"]
    db.session.add(Profile(**profile))

    save_settings(clean(SETTINGS_SCHEMA, content["settings"]))

    sync_catalogue(content)

    for group in content["skill_categories"]:
        skill_group = SkillCategory(
            name=group["name"], modes=group["modes"], position=group["position"], is_published=True,
        )
        db.session.add(skill_group)
        db.session.flush()
        for index, name in enumerate(group["skills"], start=1):
            db.session.add(Skill(name=name, category=skill_group, position=index, is_published=True))

    for item in content["experience"]:
        db.session.add(Experience(**item, is_published=True))
    for item in content["education"]:
        db.session.add(Education(**item, is_published=True))
    for item in content["certifications"]:
        db.session.add(Certification(**item, is_published=True))
    db.session.commit()


def _seed_resume(track, path, label):
    if Resume.query.filter_by(track=track, is_active=True).first() is not None:
        click.echo(f"A {track} resume is already active. Skipping.")
        return
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        media = store_upload(raw, os.path.basename(path), ("pdf",), alt_text=label)
    except ValueError as exc:
        raise click.ClickException(f"{path}: {exc}")
    db.session.add(media)
    db.session.flush()
    db.session.add(Resume(track=track, label=label, media=media, is_active=True))
    db.session.commit()
    click.echo(f"Resume set for track '{track}': {os.path.basename(path)}")
