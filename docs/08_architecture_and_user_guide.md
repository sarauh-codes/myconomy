# Myconomy — Architecture Summary and User Guide

This document describes how Myconomy is built and how to use it. It is written for maintainers and for users.
Decisions and verified API facts are in `07_decisions_and_dev_notes.md`.

## 1. Architecture

Myconomy is a server-rendered Flask application with a SQLite database (SQLAlchemy and Flask-Migrate).
Each layer has one job:

| Layer | Location | Job |
|---|---|---|
| Configuration | `app/config.py` | Environment-based settings. Secrets come from the environment. |
| Application factory | `app/__init__.py` | Builds the app, registers extensions, blueprints, error pages, and security headers. |
| Routes | `app/routes/` | HTTP only: parse input, call services, render templates or JSON. |
| Services | `app/services/` | Business rules: provider client, validation, calculations, alerts, chatbot. |
| Models | `app/models/` | Database tables: users, expenses, indicators, data points, cache, alerts. |
| Templates | `app/templates/` | Jinja pages and macros (forms, widgets). |
| Static files | `app/static/` | CSS (design tokens, light and dark themes) and small progressive-enhancement scripts. |
| Command line | `app/cli.py` | `refresh-data` and `evaluate-alerts`, for scheduled runs. |

### Data flow

```
OpenDOSM API ──► opendosm_client (timeouts, retries, 4/min pacing)
                      │
                      ▼
            series_parser (validate the whole response; nothing partial is saved)
                      │
                      ▼
            data_service ──► data_points (values) + cache_entries (status, retrieval time)
                      │
        ┌─────────────┼──────────────┬───────────────┬─────────────┐
        ▼             ▼              ▼               ▼             ▼
   dashboard     calculator      explorer        widgets       chatbot
   (charts)     (FR-02)        (metadata)      (cache only)   (stored facts only)
                                                                  │
                    alerts (evaluate-alerts) ◄── data_points ─────┘
```

Key rules that the code enforces:

- **Pages never call OpenDOSM.** Only `refresh-data` does. Pages read the cache.
- **A bad refresh never erases good data.** Responses are validated before any write.
- **Every figure has a reference period, a retrieval time, and a status**: Current, Stale, or Unavailable.
- **Indicators are registered in code** (`dataset_registry.py`). Each mapping records the verified dataset,
  dimension, unit, and frequency. Units the API does not state are labelled as inferred or unconfirmed.
- **Personal data is private.** Every expense query includes the owner's id. Other users' records return 404.
- **The chatbot and the explanations do not invent numbers.** They use stored values and the reviewed learning content.

### Security summary

- Passwords are salted hashes. Sign-in is locked for 15 minutes after five failures on an account.
- CSRF protection on every form and state-changing request.
- Content-Security-Policy allows only the app's own scripts and styles, plus Chart.js (cdnjs) and Google Fonts.
- Secure cookies and HSTS when `FLASK_CONFIG=production`.
- Errors show a friendly page. Tracebacks are logged, not shown.
- The health check reports the database and data status, without secrets.

### Known limitations

- **Single-process scheduling.** The 4-requests-per-minute pacing is per process. Run `refresh-data` from one process only.
- **No email or messaging delivery.** Alerts are in-app.
- **No language model.** The chatbot matches keywords and answers from stored data.
- **Keyboard and screen-reader testing** has been done structurally (labels, focus styles, skip links), not with assistive technology.
- **Population** is not registered. Its national total and unit are not yet verified.
- **Bahasa Malaysia** is not yet provided.

## 2. Running the application

### Development

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python.exe -m flask --app run db upgrade
.\.venv\Scripts\python.exe -m flask --app run refresh-data
.\.venv\Scripts\python.exe run.py
```

### Production

1. Set `FLASK_CONFIG=production` and a long random `SECRET_KEY` in the environment.
2. Set `DATABASE_URL` to a database file that holds real data, outside the source folder, and back it up.
3. Apply migrations: `flask --app wsgi db upgrade`.
4. Start the server: `waitress-serve --listen=127.0.0.1:8000 wsgi:app`.
5. Put an HTTPS reverse proxy (IIS, nginx, or Caddy) in front of it. Do not expose the Waitress port directly.
6. Schedule the jobs (see section 3). Refresh runs first, then alerts.

## 3. Scheduled jobs

Run these in order, once a day, from one process. Windows Task Scheduler works well:

```powershell
.\.venv\Scripts\python.exe -m flask --app wsgi refresh-data
.\.venv\Scripts\python.exe -m flask --app wsgi evaluate-alerts
```

- `refresh-data` exits with status 1 if any indicator failed. Check the log.
- `evaluate-alerts` is safe to run repeatedly. It never creates duplicate notifications.
- Both commands use the same database as the web app.

## 4. User guide

### Public pages (no account needed)

- **Home:** the latest figures from the cache, with their reference period and status.
- **Dashboard:** choose an indicator and a time range. See the latest value, changes, a chart, and a table.
- **Calculator:** convert an amount in ringgit between two months. This is a CPI-based estimate, not your own costs.
- **Explore:** each indicator's unit, geography, frequency, stored coverage, and source.
- **Learn:** short explanations of CPI, inflation, and purchasing power, with labelled examples.
- **Ask:** ask about the economy in plain language. Answers come from stored data, with sources.
- **Data status:** when each indicator was last refreshed, and whether it is current.

### Your account (optional)

1. **Create an account** with an email and a password of at least 12 characters.
2. **My spending:** add a record for each month and category. Only you can see your records.
3. **Compare with CPI:** see how your total spending changed between two months, next to the national CPI change.
   This is indicative only. It is withheld if either month is missing data.
4. **Alerts:** create a threshold alert (the 12-month change crosses a value) or a new-data alert (a newer period is published).
   Read your notifications on the same page.
5. **Account:** delete your account and all of your records at any time. This cannot be undone.

### Reading figures

- **Current:** retrieved within the expected update window.
- **Stale:** the last refresh failed, or the provider's next scheduled update has passed. The last good value is shown.
- **Unavailable:** nothing has been stored yet.
- **Reference period** is the month or quarter the statistic describes. **Retrieved** is when Myconomy fetched it (UTC).
  These two dates are different.

### Limits and safety

- Myconomy does not give personal financial, tax, or investment advice.
- Statistics are national averages. They do not measure any individual's costs.
- Questions to the chatbot are not stored.
