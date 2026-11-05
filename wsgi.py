"""Production entry point.

Run with a production server, not `flask run`:

    waitress-serve --listen=127.0.0.1:8000 wsgi:app

Put an HTTPS reverse proxy in front of it (for example IIS, nginx, or Caddy).
Set FLASK_CONFIG=production and a long random SECRET_KEY in the environment.
"""

import os

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("FLASK_CONFIG", "production")

from app import create_app  # noqa: E402

app = create_app()
