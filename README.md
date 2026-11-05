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

## Quick stats widget

The home page shows three quick stats. Each one is also available on its own:
- http://127.0.0.1:5000/widget/cpi_headline (an HTML fragment for embedding)
- http://127.0.0.1:5000/api/indicators/cpi_headline/latest (JSON)

Widgets read only the cache, so they never call OpenDOSM.

## Accounts and the spending tracker

Accounts are optional. Public pages (dashboard, calculator, learning, explorer) work without one.

- Create an account at http://127.0.0.1:5000/register. Passwords must be at least 12 characters.
- Records are at http://127.0.0.1:5000/expenses. Only you can see them.
- The comparison page at `/expenses/compare` shows your spending change next to the CPI change.
  It is indicative only, and is withheld when either month lacks data.
- Delete your account (and every record) at `/account`. This cannot be undone.

Remember to run `flask --app run db upgrade` after pulling, so the users and expenses tables exist.

## Explore indicators

Open http://127.0.0.1:5000/explore to see each registered indicator's unit,
geography, frequency, stored coverage, and source. Each indicator links to its
dashboard view. Run `flask --app run refresh-data` first to load the data.

## Learn and understand

Open http://127.0.0.1:5000/learn for short explanations of CPI, inflation, and
purchasing power. Each page separates invented illustrative examples from
official figures computed from the stored data.

## Purchasing power calculator

Open http://127.0.0.1:5000/calculator. Enter an amount in RM and two months
(YYYY-MM). The result uses the national headline CPI, so it is an estimate, not
a measure of your own costs. Results can be shared as a link.

## Dashboard

Open http://127.0.0.1:5000/dashboard after running a refresh. The page
shows the latest value, 12-month and monthly changes, a chart, a data table,
and the source. Its JSON data is at `/api/indicators/cpi_headline/series`.

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
