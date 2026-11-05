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
| `offset` | **Not a documented parameter.** The official request-query page lists only `limit`, `sort`, `filter`, and `ifilter`/`contains`/`icontains`. Live calls ignore it. Not used. |
| Limit | No documented maximum. A filtered call with `limit=100000` returned all 7854 unfiltered rows of `cpi_headline` in one response. |
| Latest reference period | 2026-09-01 on 2026-11-05 (about two months behind). |
| Null values | `cpi_core` division `02` returns `index: null` for recent months. |
| Unknown dataset | HTTP 404 with a clear message. |
| Working datasets seen | `cpi_headline`, `cpi_core`, `gdp_qtr_real`, `lfs_month`, `lfs_qtr`, `population_state`. `population_district` returned an empty list with `limit=1`. |
| Dataset IDs that returned 404 | `gdp_qtr`, `gdp_quarterly`, `population`, `labour_force_monthly`. |
| Metadata | `meta=true` adds `meta` with `data_as_of`, `last_updated`, `next_update`, `update_frequency`, `data_source`, `total`. The envelope is `{"meta": {...}, "data": [...]}`. |
| Update schedules (live `meta`) | `cpi_headline`, `cpi_core`, `lfs_month`: MONTHLY. `gdp_qtr_real`: QUARTERLY. `population_state`: YEARLY (data as of 2023). |
| Rate limit | **4 requests per minute** for the OpenDOSM API (developer.data.gov.my/rate-limit). Live test: requests 1–4 returned 200; requests 5 and 6 returned **429**. |
| Error format | `{"status": <int>, "errors": [...]}`. Statuses: 200, 400, 404, 429, 500. |
| Retry-After header | Not documented and not observed. |
| API key | Not mentioned in the docs. None used. |
| Population units | Not stated in the metadata. `population_state` Johor = `4009.7`, which suggests thousands. **Unconfirmed.** |
| CPI base year | Not stated in the metadata. The unit is shown as "base year not confirmed". **Unconfirmed.** |

## 2a. Milestone 2 open questions (resolved or not)

- Offset pagination: resolved. Not documented, not used. A single request with a large `limit` returns full series.
- Rate limit: resolved. 4 per minute, so the client spaces requests by 15 seconds and waits 60 seconds after a 429.
- Update schedule: resolved for the datasets seen above, from `meta`.
- CPI base year: **open**.
- Population units: **open** (suggested thousands; needs confirmation before any population display).

## 3. Milestone 1 build notes

- Python 3.15.2 on Windows. Flask 3.1.3, Flask-SQLAlchemy 3.1.1,
  Flask-Migrate 4.1.0, python-dotenv 1.2.4, pytest 9.2.0 (pinned in
  `requirements.txt`).
- The project uses `app/` at the root, as in the system design. An empty
  `src/` folder already existed in the repository and was left untouched.
- Flask-Migrate initialised; no models yet, so no migration revision was
  generated (Alembic reported no schema changes).
- The tests use a separate in-memory database.

## 3a. Milestone 2 build notes

- Provider client (`app/services/opendosm_client.py`): explicit timeouts,
  retries for timeouts, connection errors, and 5xx (exponential backoff), a
  60-second wait then one retry for 429, no retry for other 4xx, and
  per-process request spacing of 15 seconds.
- Spacing is per process. The scheduled refresh must run as one process, or the limit can be exceeded.
- Dataset mappings live in code (`app/services/dataset_registry.py`), not in
  the database. This keeps verified field names under code review. The
  `indicators` table is synced from this registry on each refresh. This is a
  small change from the database design, which stored a mapping JSON in the table.
- Refresh is all-or-nothing: the full response is validated before any row is
  written. An empty response, or a failed fetch, keeps the previous data and
  marks the status as stale.
- Stored times are UTC. The status page labels retrieval time separately from the reference period.
- Live refresh on 2026-11-05 stored 561 observations for `cpi_headline`.
- Tests: 58 passing with no network access. One optional live test runs with `RUN_LIVE_TESTS=1`.

## 3b. Milestone 3 build notes (Economic dashboard)

- Page: `/dashboard?indicator=…&range=1y|5y|10y|all`. Invalid indicator or range
  shows a message with HTTP 400. Nothing reaches the database with unvalidated input.
- JSON: `/api/indicators/<code>/series?range=…` for the chart and for later features (widget, chatbot).
- Changes: 12-month and month-on-month changes are calculated from stored values
  (`app/services/dashboard_service.py`). They are only shown when both months exist,
  and only for monthly series. Missing values are never estimated.
- Ranges are counted in stored months, so a range always ends at the latest stored period, not today.
- Chart library: Chart.js 4.5.1 from cdnjs. Released 2025-10-13, so it meets the
  two-week rule. (4.6.1 was released 2026-10-22, only two weeks before this build.)
  The page falls back to the data table if the library cannot load.
- Chart colours come from the design tokens and redraw when the theme changes.
  Animation is disabled for reduced-motion users.
- The chart has a text alternative (table under "View data table") so no information relies on colour alone.
- Verified in the browser at 1280px and 375px, dark and light: no horizontal scroll;
  chart loads and redraws on theme change.
- Tests: 85 passing (58 from Milestone 2, plus calculation, route, and series tests).

## 4. Open questions still to answer

- Chatbot LLM provider and whether personal data may ever be sent to it
  (default: never).
- Account deletion and data export behaviour (FR-03, FR-10).
- Freshness threshold for each dataset (for the widget's stale status).
- Whether the CPI series has been rebased (affects comparisons across years).
- CPI base year and population units (see section 2a).
- Whether the rate limit is shared across all API categories (the docs say each category has the same limit; the live test covered one).
