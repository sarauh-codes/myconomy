"""Local entry point.

Usage:
    python run.py                 # development server
    flask --app run db upgrade    # apply database migrations

Environment variables are read from .env when that file exists. Real
environment variables take precedence over values in .env.
"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402  (must run after load_dotenv)

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
