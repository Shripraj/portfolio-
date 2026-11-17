"""Start the whole site (public pages, admin and API) with one command:

    flask run --port 5000        (set FLASK_APP=api.wsgi:app first)
    python app.py                 (set FLASK_DEBUG=1 for local development)
"""
import os

from api.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")),
            debug=os.environ.get("FLASK_DEBUG") == "1")
