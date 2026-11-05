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

## 3c. Milestone 4 build notes (Purchasing power calculator)

- Formula (FR-02): `equivalent_amount = input × (target CPI ÷ starting CPI)`.
  Calculated in `app/services/calculator_service.py` with `Decimal`, rounded to the cent.
  Checked against an independent calculation: 100 from 2020-01 (CPI 122.4) to 2026-09 (CPI 137.6) = RM 112.42.
- Currency: amounts are treated as **Malaysian ringgit (RM)**. This is my assumption;
  the requirements do not state a currency. Confirm before release.
- Input rules: zero or positive, up to two decimal places, thousands commas and spaces allowed,
  maximum RM 1 trillion. Months are `YYYY-MM`.
- Missing months and missing CPI values are never estimated. The message names the month and
  shows the stored range.
- The form uses GET, so results can be shared as a link. Nothing is saved, so no CSRF token is needed here.
  Invalid input returns HTTP 400 with per-field messages and a summary that links to each field.
- The result states the direction (starting month to target month), the CPI values used, the ratio,
  the formula, the data status, and the reference period.
- Verified in the browser at 1280px and 375px, dark mode: the result renders with the real data, and the phone layout has no horizontal scroll.
- Tests: 131 passing, one live test skipped by default.

## 3d. Milestone 5 build notes (Learn & understand)

- Pages: `/learn` (index), `/learn/cpi`, `/learn/inflation`, `/learn/purchasing-power`.
- Each topic shows three labelled kinds of content:
  - **Explanation** (plain language, in `app/services/learning_content.py`).
  - **Illustrative** example with invented numbers, labelled "Invented numbers for explanation only".
  - **Official** example, computed from stored OpenDOSM data at request time, showing its reference period and data status. If data is missing, it says so.
- The purchasing power formula is one constant (`FORMULA_TEXT` in `calculator_service.py`), used by the calculator page and the explanation. Test LEARN-03 checks both.
- Inflation uses the same 12-month calculation as the dashboard.
- Every topic links to the OpenDOSM documentation. Content should be reviewed when calculation logic or source definitions change.
- Verified against live data: `/learn/inflation` shows +1.8% to 2026-09, matching the dashboard; `/learn/purchasing-power` shows RM 112.42, matching the calculator.
- Tests: 145 passing, one live test skipped by default.
- Not yet covered: Malay (Bahasa Malaysia) translations, which decision D4 requires in a later milestone.

## 3e. Milestone 6 build notes (Multi-Indicator Explorer)

Verified live on 2026-11-05 (`meta=true`, full responses):

| Dataset | Frequency | Coverage | Shape | Verified facts | Unconfirmed |
|---|---|---|---|---|---|
| `cpi_headline` (filter `overall@division`) | Monthly | 1980-01 to 2026-09 | `date`, `index`, `division` | National; no nulls | Base year |
| `gdp_qtr_real` | Quarterly | 2015-Q1 to 2026-Q2, 46 quarters per series | `date`, `series`, `value` | Three series: `abs` (level), `growth_yoy` and `growth_qoq` (per cent). `growth_yoy` starts 2016-Q1 and `growth_qoq` starts 2015-Q2, as expected for lagged growth. | Unit and price base of `abs`. Magnitude suggests RM million. |
| `lfs_month` | Monthly | 2010-01 to 2026-08, 200 months, no gaps | `date`, `lf`, `u_rate`, `p_rate`, `ep_ratio`, `lf_employed`, `lf_unemployed`, `lf_outside` | `u_rate` equals `lf_unemployed` ÷ `lf` × 100 (checked: 436.7 ÷ 12,367.9 ≈ 3.5). National. | — |
| `population_state` | Yearly | 2020 to 2023 only | `date`, `state`, `age`, `sex`, `ethnicity`, `population` | 16 states. The sex split sums to the overall total in every state. | Unit (probably thousands). No national row, so a national total would be summed from the states. The provider's next update (2024-07) has passed, so data is older than expected. |

Decisions in this milestone:

- **Population is deferred.** It needs a national total calculated from states, which the registry
  does not support yet, and its unit is unconfirmed. It will be added once both are settled.
- **Only verified indicators are registered:** CPI, real GDP level, real GDP growth, and unemployment.
- **Rate series show no change figures.** Growth and unemployment are already rates, so a
  "change" of a rate is not meaningful here. The dashboard says so.
- **Quarterly periods.** Year-on-year is 12 months back, and change from the previous period is
  one quarter back. Period labels read `2026-Q2`.
- **Freshness now honours the provider's schedule.** A snapshot becomes stale when the provider's
  `next_update` has passed, even if our own window has not expired.
- **One provider request per dataset per refresh.** GDP level and growth come from one response.
- **Data shape per dataset.** Where a dataset holds several series, the registry names the series.
  If the request was server-filtered, any other series is treated as malformed. If unfiltered,
  other series are skipped.
- **No cross-indicator comparison.** The explorer shows metadata side by side and says indicators
  are not compared, because their units and periods can differ.

Verified live: `flask refresh-data` stored 561 CPI, 46 GDP level, 42 GDP growth, and 200
unemployment observations, with three provider requests in total.

Tests: 167 passing, one live test skipped by default.

## 3f. Milestone 7 build notes (Accounts and the cost-of-living tracker)

Dependencies (checked against PyPI release dates on 2026-11-05): Flask-Login 0.6.3 (2023),
Flask-WTF 1.3.0 (2026-04-23), WTForms 3.3.2. All are pinned in `requirements.txt`.

Security design:
- Passwords hashed with Werkzeug's `generate_password_hash` (salted). Plain text is never stored or logged.
- Minimum password length 12, maximum 128. No composition rules, which follows current NIST guidance.
- Failed sign-in returns one message whether the email or password was wrong. A dummy hash check
  runs for unknown emails, so response time is similar either way.
- Registration of an existing email returns a generic message that does not say the email is registered.
  This is a partial mitigation: a determined person can still tell by trying known addresses.
- CSRF protection is global (Flask-WTF `CSRFProtect`). All state-changing routes are POST, and there is a test for each.
- The `next` redirect accepts only local paths. External targets and `//` prefixes are ignored (tested).
- Sign-in sessions expire after 8 hours. There is no "remember me" option.
- Every expense query includes the owner's id. A record that belongs to someone else returns 404, the
  same as a missing record (tested for edit, update, and delete).
- Account deletion requires the current password and removes all of the user's expense records
  immediately. The ORM does the cascade, because SQLite does not enforce foreign keys by default
  (a bug found by a test during this milestone).

Decisions I made (please confirm):
- **Expense categories:** Food and drink, Transport, Housing, Utilities, Health, Education, Clothing,
  Entertainment, Other. The requirements do not list categories.
- **Months:** records can be entered from 1990 up to the current month. Future months are rejected.
- **Amount limit:** RM 10 million per record. Amounts have up to two decimal places.
- **Deletion is immediate.** No grace period and no export. Data export is still an open question (section 4).

CPI comparison (FR-03):
- Shows the change in the user's total spending and the change in headline CPI between two months.
- Withheld, with the reason, when either month has no records or no stored CPI value. Never estimated.
- Labelled "indicative only" on the page. The method explains the formula.

Not done in this milestone:
- **Login rate limiting.** The design says to consider it. It is not implemented, and an in-process
  limit would not hold across several worker processes.
- **Personal data export.** Open question D-export.
- **Bahasa Malaysia.** Still outstanding under decision D4.

Verification:
- Tests: 237 passing (about 25 seconds, mostly password hashing). One live test skipped by default.
- HTTP check on the local dev server: sign-up, adding an expense, rejecting a negative amount, the comparison
  withholding a month without records, anonymous redirect to sign-in, and account deletion removing the
  user and records. The test account was deleted afterwards.
- Browser check: not completed. The browser pane stopped rendering, so the account and tracker pages have
  not been checked visually. The layout reuses the existing components, but this needs a look.

## 3g. Milestone 8 build notes (Quick Stats widget)

- The widget is a reusable Jinja macro (`app/templates/_widgets.html`) with the value, indicator name,
  reference period, retrieval time (UTC), a text status, and links to details and the source.
- Endpoints: `/widget/<code>` (standalone HTML fragment) and `/api/indicators/<code>/latest` (JSON).
- Widgets read only the cache (`app/services/quick_stats.py`). They never call OpenDOSM. A test patches
  the client to fail and checks every widget route still responds.
- Stale and unavailable states are stated in words ("Stale", "Unavailable") and explained, not shown by colour alone.
- The home page shows three widgets: CPI, unemployment, and real GDP growth. They are chosen in `home_stats()`.
- Formatting: rates show a percent sign; levels use thousands separators; index values show one decimal.
- Tests: 255 passing across the suite; 18 widget-specific tests.

Copy corrections made while building this milestone. Earlier pages said that OpenDOSM was not yet
connected and that no figures were shown. Both were out of date after Milestones 2 to 6, so I corrected:
the home page status card, the fact strip (now counts registered indicators), the footer, the FAQ,
and the route docstring.

Browser check:
- The home page widgets were checked in the browser: values, reference periods, and statuses are correct,
  with no horizontal scroll at 375px. The stat grid goes from three columns to one.
- The sign-in page was checked: all visible inputs have labels; the CSRF token is the only unlabelled input, which is hidden.
- The Milestone 7 tracker and account pages have still not been checked visually; the browser pane was intermittently blank.

## 3h. Milestone 9 build notes (Inflation alerts)

- Two rule types. **Threshold** compares a 12-month change with a value (decision D2), above or below.
  It applies only to index and level indicators, because the change of a rate is not what the rule means.
  **New data** fires when a newer period is stored than the rule last saw.
- A new-data rule starts with a baseline (the latest stored period). Existing periods do not alert on creation.
- Idempotence: each notification has a unique `event_key` built from the rule, type, period, and (for thresholds)
  the change value. Running the evaluation again creates nothing new. A revised value for the same period is a
  new event, so the user is told about the revision.
- Safety: evaluation only uses a source whose last refresh succeeded. A failed or empty refresh creates no alert.
  Inactive rules and inactive accounts are skipped. Each rule commits separately, so one failure does not stop the rest.
- Notifications show the indicator, the change or value, the reference period, and the source. Each has read state.
- Limits: 20 rules per user. The threshold must be between -50% and 100%.
- Scheduling: `flask --app run evaluate-alerts`, run after `refresh-data`. No in-process timer.
  Use Windows Task Scheduler or cron. Running it repeatedly is safe.
- Nav shows an unread count for signed-in users only.
- Tests: 289 passing (34 new alert tests across the integration and route suites).
- Live check: `evaluate-alerts` runs against the local database and reports 0 rules created, as expected.
- Still open: email or messaging delivery (in-app only for now), and login rate limiting (Milestone 7).
- The browser check of the alerts page has not been done yet.

Home page corrections made during this milestone (requested by the user): the roadmap, access list,
feature count, and footer now match the built features. The roadmap shows public statistics and the
tracker and alerts as done, and the chatbot and release as next.

## 3i. Milestone 10 build notes (Economic chatbot)

Decision: **no external language model by default.** The design left the provider open. Choosing one
involves cost, privacy, and an exact model version, so the default is a retrieval-only chatbot:
answers come from stored values and the reviewed learning content. `app/services/llm.py` provides the
interface for a later provider. Its default sends nothing outside the application.

- Intents: latest value, 12-month change (index and level indicators), concept explanations (CPI,
  inflation, purchasing power, linked to the learning pages), refusals for personal financial advice,
  and a scope message for anything else.
- Numbers come only from the data layer, with the reference period and source. A missing value or
  comparison month produces an "unavailable" answer, never an estimate.
- Injection: the question is treated as text to match, not as instructions. Tests check that
  "ignore previous instructions" cannot change a figure or add a source.
- Privacy: the chatbot module does not import the expense models (a test checks this), and answers
  never include personal records (tested with a seeded expense). Questions are not stored, and no chat table exists.
- Input: up to 300 characters, control characters removed, CSRF protected.
- Intent matching is keyword-based. It is simple to test and explain, but it will miss paraphrases.
  Unrecognised questions get the scope message.
- Live check on the local data: inflation +1.8% (2026-09), unemployment 2.9% (2026-08), and GDP growth
  6.0% (2026-Q2) match the dashboard.
- Tests: 320 passing. The chatbot suite has 31 tests.
- Not done: a browser check of the chat page, and any real LLM provider. The keyword matching has not been
  tested against real user phrasing.

## 3j. Milestone 11 build notes (Hardening and release)

Changes:
- **Login lockout** stored in the database (`failed_login_count`, `locked_until`). Five failures lock the
  account for 15 minutes. The lock works across worker processes. A locked account refuses even the correct
  password, with the same message as any failure, so the form does not reveal which accounts exist.
  Unknown emails are not counted. Limitation: an attacker can still try many accounts slowly, so IP-based
  limits at the reverse proxy are recommended.
- **Content-Security-Policy:** script and style sources limited to the app, cdnjs (Chart.js), and Google Fonts.
  No `unsafe-inline`. Checked in the browser: the dashboard chart renders under the policy with no console errors.
- **Permissions-Policy** disables camera, microphone, and geolocation. **HSTS** is sent when cookies are secure (production).
- **Health check** reports data status per indicator. Stale or unavailable data does not make it fail.
- **Production entry point** `wsgi.py` with Waitress 3.0.2 (released 2024-11-16). Checked: the server starts with
  `FLASK_CONFIG=production`, cookies are `Secure`, and HSTS, CSP, and the health check respond.
- **Mobile check:** at 375px, the home, calculator, explorer, chat, and sign-in pages have no horizontal scroll.
  Sign-in fields all have labels.
- **Documentation:** `docs/08_architecture_and_user_guide.md` (architecture, running, scheduled jobs, user guide).

Test runs: 331 passing, 1 live test skipped. One run took 11 minutes; reruns took about 30 seconds, so the slow run was
environmental, not a test problem.

Not done in this milestone (listed honestly as known limitations):
- Assistive-technology and keyboard-only testing (checked structurally only).
- Continuous integration.
- A real HTTPS deployment (the reverse proxy and certificate depend on where the app is hosted).
- Backup and restore testing (the testing plan requires it; the procedure is not yet written).
- Population indicator and Bahasa Malaysia.

## 4. Open questions still to answer

- Chatbot LLM provider and whether personal data may ever be sent to it
  (default: never).
- Account deletion and data export behaviour (FR-03, FR-10).
- Freshness threshold for each dataset (for the widget's stale status).
- Whether the CPI series has been rebased (affects comparisons across years).
- CPI base year and population units (see section 2a).
- Whether the rate limit is shared across all API categories (the docs say each category has the same limit; the live test covered one).
