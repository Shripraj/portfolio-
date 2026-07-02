# Shridhar Patil — Portfolio (Flask)

A full-stack, glassmorphism-styled personal portfolio built with Flask, vanilla
JS, and SQLite. Includes a public site and a password-protected admin panel to
manage projects, certificates, resume, skills, and the About section — no
redeploy required.

## Features

- Hero section with an animated canvas particle background and a terminal-style
  signature card with a live typing effect (cycles through your titles)
- Dark / light mode with saved preference, glassmorphism cards, gradient accents
- About, Skills (animated progress bars), Projects, Certifications, Education
  timeline, Resume, and Contact sections
- Contact form that saves messages to SQLite (submits via AJAX, no page reload)
- Secure admin dashboard (session-based login, hashed password) to:
  - Edit the About text and hero intro
  - Add / delete skills
  - Add / delete projects (with image upload)
  - Add / delete certificates, replace certificate images
  - Upload a new resume PDF (auto-activates as the live download)
  - View and delete contact messages
- Scroll progress bar, back-to-top button, mobile nav drawer, custom cursor,
  loading screen, AOS scroll reveals, animated counters, floating social icons
- Custom 404 / 500 error pages, SEO meta tags, favicon, `robots.txt`

## Project Structure

```
portfolio/
├── app.py                     # Flask app: routes, auth, uploads, DB access
├── requirements.txt
├── database/
│   ├── schema.sql              # Table definitions
│   └── portfolio.db            # Created automatically on first run
├── templates/
│   ├── base.html                # Shared shell (nav, loader, cursor, etc.)
│   ├── index.html                # Assembles all public sections
│   ├── _skills.html, _projects.html, _certifications.html,
│   │   _education.html, _resume.html, _contact.html   # Section partials
│   ├── 404.html / 500.html
│   └── admin/
│       ├── base.html, login.html, dashboard.html,
│       │   about.html, skills.html, projects.html,
│       │   certificates.html, resume.html, messages.html
└── static/
    ├── css/style.css            # Design system + all component styles
    ├── css/admin.css            # Admin dashboard styles
    ├── js/main.js                # Nav, theme, cursor, scroll fx, counters
    ├── js/particles.js           # Hero canvas particle network
    ├── js/typing.js              # Hero typing effect
    ├── js/contact.js             # AJAX contact form submit
    ├── js/admin.js
    ├── images/certificates/      # Certificate images (admin-managed)
    ├── images/projects/          # Project images (admin-managed)
    └── resume/                   # Uploaded resume PDFs
```

## Setup

1. **Create a virtual environment (recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   python app.py
   ```
   The database (`database/portfolio.db`) and seed content (skills, sample
   projects, sample certificates, education, admin user) are created
   automatically on first run.

4. **Open the site**
   - Public site: http://127.0.0.1:5000
   - Admin panel: http://127.0.0.1:5000/admin/login

### Default admin credentials

```
Username: admin
Password: ChangeMe123!
```

**Change these immediately.** Either edit the row in `database/portfolio.db`
(the `admin` table) or set environment variables before the *first* run
(they only seed the initial account):

```bash
export ADMIN_USERNAME="your_username"
export ADMIN_PASSWORD="a_strong_password"
```

Also set a real `SECRET_KEY` in production:
```bash
export SECRET_KEY="a-long-random-string"
```

## Replacing your content

- **Profile photo**: replace `static/images/profile-placeholder.svg`, or add
  your own image and update the `src` in `templates/index.html` (hero section).
- **Resume**: upload a PDF from `/admin/resume` — it becomes the live download
  immediately.
- **Certificates / projects**: manage entirely from `/admin/certificates` and
  `/admin/projects` (upload, replace, delete).
- **About / hero text / skills**: edit from `/admin/about` and `/admin/skills`.
- **Education**: seeded from the brief; edit directly in `database/schema.sql`
  seed data or via a DB browser if you want an admin UI for it too.

## Notes

- Uploaded files are validated by extension (`png/jpg/jpeg/webp/gif` for
  images, `pdf` for resumes) and filenames are sanitized with
  `werkzeug.utils.secure_filename`.
- Max upload size is capped at 10 MB (`MAX_CONTENT_LENGTH` in `app.py`).
- This uses Flask's built-in dev server for local development. For
  production, run behind a WSGI server such as **gunicorn**:
  ```bash
  pip install gunicorn
  gunicorn -w 2 -b 0.0.0.0:8000 app:app
  ```
