# Myconomy

Myconomy helps people explore Malaysia's official economic statistics from
OpenDOSM (Department of Statistics Malaysia), with clear reference periods,
sources, and plain-language explanations.

**Status:** Milestone 1 (project foundation). The app runs and has a health
check, but it does not yet show economic figures. OpenDOSM integration is
Milestone 2.

## Requirements

- Python 3.11 or newer (developed and tested on Python 3.15)
- Git

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` if you want to change defaults. Leave `SECRET_KEY` empty for
local development. The app then generates a temporary key on each start.

## Run the app

```powershell
python run.py
```

Open http://127.0.0.1:5000/ in a browser. The health check is at `/health`.

## Database

```powershell
flask --app run db upgrade
```

Local data is stored in `instance/myconomy.db`. This folder is git-ignored
because it can contain personal data.

## Refresh OpenDOSM data

```powershell
flask --app run refresh-data
```

This fetches every registered indicator. The OpenDOSM API allows 4 requests
per minute, so the command spaces requests automatically. Run the command
from one process only. Visit `/data-status` to see what was retrieved.

## Tests

```powershell
pytest
```

Tests use an in-memory database and never touch local data. No test calls
the live OpenDOSM API.

## Configuration

Settings are read from environment variables (see `.env.example`).

| Variable | Purpose |
|---|---|
| `FLASK_CONFIG` | `development`, `testing`, or `production` |
| `SECRET_KEY` | Session signing key. Required in production. |
| `DATABASE_URL` | Database location. Defaults to SQLite in `instance/`. |
| `LOG_LEVEL` | Logging level |

Never commit `.env` or any file containing real secrets.

## Project layout

See [docs/04_database_design.md](docs/04_database_design.md) and
[docs/03_system_design.md](docs/03_system_design.md) for the planned
architecture. Decisions made so far are recorded in
[docs/07_decisions_and_dev_notes.md](docs/07_decisions_and_dev_notes.md).

## Data source

Statistics come from OpenDOSM, provided by the Department of Statistics
Malaysia: https://developer.data.gov.my/static-api/opendosm
