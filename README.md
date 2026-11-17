# Shridhar Patil – Portfolio and Admin

One Flask app. It serves the public portfolio, the admin dashboard and the API, and stores everything in one SQLite file.

## Run it on Windows (three steps)

Open Command Prompt in the project folder, then run:

```bat
python -m venv env
env\Scripts\activate
python run.py
```

On the first run, `run.py` does the following:
1. Installs the packages from `requirements.txt`.
2. Creates `.env` with two new secret keys.
3. Builds the database and loads the content.
4. Asks you to set the admin password (typed twice, hidden).
5. Starts the site.

Then open:
- Portfolio: http://localhost:5000
- Admin: http://localhost:5000/admin

Press Ctrl+C in the window to stop the site. Next time, `python run.py` starts it straight away.

If `.env` already exists from an earlier attempt, delete it once so new keys are created.

## Projects and categories

The site shows the eight projects from the brief. Each project can belong to several categories, so it appears under each relevant filter:

| Filter | Projects |
|---|---|
| Python Development | 3 |
| Full Stack Development | 3 |
| Machine Learning | 2 |
| Data Analytics | 5 |

The Python view shows GoVigyan, GlowGuide and CodeSpace. The Data Analyst view shows the five data projects. "Show all" displays all eight.

Project records and the catalogue live in `api/seed_data/content.json`. On an existing database, the catalogue update runs once automatically the next time you start `run.py`. It never deletes records, and it keeps text you have already written in the admin.

Items still to complete in the admin:
- CodeSpace: description, problem, solution, technologies and links.
- Forage project: details from your Forage materials.
- Gender Pay: live demo link.
- Siksha: hidden from the site because it isn't one of the eight. Publish it from the admin to show it.

## Admin dashboard

Sign in at `/admin`. Manage profile, projects (including multiple categories, GitHub and demo links, images and publishing), skills, experience, education, certifications, resumes (Python and Data Analyst PDFs), site settings, messages and the media library.

Changes go live on the public site as soon as you save them. Drafts are never shown publicly.

## Layout

```
run.py              one-command launcher (start here)
app.py              the Flask app entry point
api/                models, routes, validation, CLI commands, seed data
templates/          public pages and the admin page
static/             stylesheet, scripts and the admin dashboard
requirements.txt    Python packages
render.yaml         deployment settings for Render
```

## Deployment (Render)

`render.yaml` describes a single web service with a persistent disk at `/var/data`. Set `SITE_URL` to your public address after the first deploy. Render needs a paid plan with persistent disks for the SQLite file to survive restarts.

## Tests

```bat
python -m pytest api/tests
```
