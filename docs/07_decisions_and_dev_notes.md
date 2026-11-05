# Myconomy — Decisions and Developer Notes

This file records decisions and verified facts. The six original documents
are not edited; changes to them are recorded here until they are reviewed.

## 1. Decisions (approved 2026-11-05)

| # | Decision | Effect on documents |
|---|---|---|
| D1 | Headline CPI uses `cpi_headline` filtered with `overall@division`. | Resolves the open dataset question in the database design. |
| D2 | Inflation alert thresholds use year-on-year % change, not index level. | Adds a rule the requirements did not state. |
| D3 | Do not use the `offset` parameter until it is verified (see section 2). Use date filters and limits instead. | Pagination approach changes from the original plan. |
| D4 | Bahasa Malaysia support is in scope. | **New requirement.** Not yet built. Needs a translation plan in a later milestone. |
| D5 | Milestone 1 is a lean foundation: app factory, config, base layout, health check, error pages, tests, and dev setup. | Adds a health check and security headers (FR-11). |
| D6 | Accounts (registration, login, logout) are included. Authentication is **optional**: guests can use all public features without signing in. Only personal features (spending, alerts, saved settings) require an account. | Resolves the system-design open question on whether auth is needed in the first milestone. Auth itself is still scheduled for Milestone 7. |

## 2. Verified OpenDOSM API facts (checked 2026-11-05)

Base URL: `https://api.data.gov.my/opendosm/` (trailing slash required; the
URL without the slash returns a 301 redirect).

| Check | Result |
|---|---|
| `id=cpi_headline&limit=1` | Returns a row from division `03`, 1986. **Not the headline series.** |
| Headline series | `filter=overall@division` returns 561 monthly rows, 1980-01 to 2026-09. |
| Filter syntax | `<value>@<column>`. `division eq "02"` returns HTTP 400. |
| Sorting | `sort=-date` works (newest first). |
| `offset` | Appears **ignored** in tests (returns the same first rows). Not used. |
| Latest reference period | 2026-09-01 on 2026-11-05 (about two months behind). |
| Null values | `cpi_core` division `02` returns `index: null` for recent months. |
| Unknown dataset | HTTP 404 with a clear message. |
| Working datasets seen | `cpi_headline`, `cpi_core`, `gdp_qtr_real`, `lfs_month`, `lfs_qtr`, `population_state`. `population_district` returned an empty list with `limit=1`. |
| Dataset IDs that returned 404 | `gdp_qtr`, `gdp_quarterly`, `population`, `labour_force_monthly`. |
| Metadata | Not yet verified. `/data-catalogue?id=` returns data, not metadata. |
| Rate limits, update schedule | Not yet verified. |

Open checks before Milestone 2 coding: confirm the offset behaviour, rate
limits, update schedule per dataset, CPI base year, and population units.

## 3. Milestone 1 build notes

- Python 3.15.2 on Windows. Flask 3.1.3, Flask-SQLAlchemy 3.1.1,
  Flask-Migrate 4.1.0, python-dotenv 1.2.4, pytest 9.2.0 (pinned in
  `requirements.txt`).
- The project uses `app/` at the root, as in the system design. An empty
  `src/` folder already existed in the repository and was left untouched.
- Flask-Migrate initialised; no models yet, so no migration revision was
  generated (Alembic reported no schema changes).
- The tests use a separate in-memory database.

## 4. Open questions still to answer

- Chatbot LLM provider and whether personal data may ever be sent to it
  (default: never).
- Account deletion and data export behaviour (FR-03, FR-10).
- Freshness threshold for each dataset (for the widget's stale status).
- Whether the CPI series has been rebased (affects comparisons across years).
