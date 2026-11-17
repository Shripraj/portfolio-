"""Start the portfolio with one command: python run.py

First run: installs the packages, creates a .env file with new secret keys,
builds the database, asks for the admin password, and starts the site.
Later runs: starts the site straight away.
"""
import importlib.util
import os
import secrets
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
REQUIREMENTS = ROOT / "requirements.txt"
DEFAULT_DB = ROOT / "instance" / "portfolio.db"
ADMIN_EMAIL = "patilshridhar1301@gmail.com"
PORT = int(os.environ.get("PORT", "5000"))
REQUIRED_PACKAGES = ["flask", "flask_sqlalchemy", "flask_jwt_extended", "flask_cors"]


def read_env_file():
    """Return the non-empty values from .env."""
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if value.strip():
                    values[key.strip()] = value.strip()
    return values


def ensure_env_file():
    """Create .env, or add any missing secret keys, with freshly generated values."""
    existing = read_env_file()
    lines = []
    if not ENV_FILE.exists():
        lines.append("SITE_URL=http://localhost:5000")
    for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
        if key not in existing:
            lines.append(f"{key}={secrets.token_hex(32)}")
            print(f"Saved a new {key} to .env")
    if lines:
        with ENV_FILE.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


def load_env_file():
    for key, value in read_env_file().items():
        os.environ.setdefault(key, value)


def ensure_packages():
    """Install requirements.txt only if a required package is missing."""
    missing = [name for name in REQUIRED_PACKAGES if importlib.util.find_spec(name) is None]
    if missing:
        print("Installing the required packages. This only happens the first time...\n")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])


def database_file():
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("sqlite:///"):
        return Path(url[len("sqlite:///"):])
    return DEFAULT_DB


def query_one(db_file, sql, params=()):
    with closing(sqlite3.connect(db_file)) as conn:
        return conn.execute(sql, params).fetchone()


def run_flask(*args):
    return subprocess.call([sys.executable, "-m", "flask", *args], cwd=ROOT)


def prepare_database():
    db = database_file()
    db.parent.mkdir(parents=True, exist_ok=True)

    tables_ready = db.exists() and query_one(
        db, "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_users'"
    ) is not None
    if not tables_ready:
        print("Building the database and loading the content...")
        if run_flask("seed") != 0:
            sys.exit("The database could not be built. Read the error above, then run python run.py again.")

    if query_one(db, "SELECT COUNT(*) FROM admin_users")[0] == 0:
        print(f"\nCreate the admin login for {ADMIN_EMAIL}.")
        print("Type a password (it stays hidden), then type it again to confirm.\n")
        if run_flask("create-admin", "--email", ADMIN_EMAIL) != 0:
            sys.exit("The admin account could not be created. Run python run.py again to retry.")


def start_site():
    sys.path.insert(0, str(ROOT))
    from app import app

    print(f"\nPortfolio: http://localhost:{PORT}")
    print(f"Admin:     http://localhost:{PORT}/admin")
    print("Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=PORT, debug=False)


def main():
    os.chdir(ROOT)
    print("Portfolio setup\n")
    ensure_env_file()
    load_env_file()
    ensure_packages()
    prepare_database()
    if run_flask("sync-catalogue") != 0:
        sys.exit("The project list could not be updated. Read the error above, then run python run.py again.")
    start_site()


if __name__ == "__main__":
    main()
