# Myconomy — Development Plan

## 1. Approach

Build Myconomy in small, testable milestones. The architecture should account for all eight features from the beginning, but each feature does not need to be fully implemented at once.

Use Python and Flask for the web application, Jinja templates for server-rendered pages, JavaScript for interactive charts and UI behaviour, and SQLite for initial persistence.

## 2. Suggested Milestones

### Milestone 1 — Project Foundation
- Create a Git repository and Flask application structure.
- Set up a virtual environment and dependency file.
- Add configuration using environment variables and `.env.example`.
- Add a base template, navigation, responsive layout, and error pages.
- Configure SQLAlchemy and database migrations.
- Add pytest and basic CI if desired.
- Write a README with setup instructions.

**Deliverable:** A runnable Flask application with a tested foundation.

### Milestone 2 — OpenDOSM Integration
- Read the official OpenDOSM documentation.
- Verify the CPI dataset's schema, period fields, and historical coverage.
- Implement a reusable provider client with timeouts and error handling.
- Validate JSON structure and numeric values.
- Add a data service and persistent cache.
- Preserve the last successful snapshot when a refresh fails.
- Display source, reference period, retrieval time, and stale status.

**Deliverable:** Reliable data retrieval with empty/error/stale states.

### Milestone 3 — Feature 1: Economic Dashboard
- Build summary cards and historical charts.
- Add indicator and period selection.
- Show data source, units, reference period, and freshness.
- Add loading, no-data, and error states.

**Deliverable:** First complete, useful public-facing feature.

### Milestone 4 — Feature 2: Purchasing Power Calculator
- Implement server-side input validation.
- Retrieve compatible CPI values for selected periods.
- Implement and test the formula.
- Show the result, inputs, source periods, and explanation.
- Add cases for unavailable periods and invalid values.

**Deliverable:** Transparent and tested calculator.

### Milestone 5 — Feature 8: Learn & Understand
- Create short learning pages for CPI, inflation, and purchasing power.
- Add simple worked examples.
- Distinguish illustrative values from official statistics.
- Link to official source documentation.

**Deliverable:** Educational section integrated with the dashboard and calculator.

### Milestone 6 — Feature 7: Multi-Indicator Explorer
- Identify suitable OpenDOSM datasets for GDP, unemployment, and population.
- Verify schemas, coverage, units, geography, and update frequency separately.
- Extend the indicator registry and data service.
- Add indicator-specific visualisations and filters.
- Prevent misleading comparisons between incompatible series.

**Deliverable:** Several verified indicators available through a consistent interface.

### Milestone 7 — Accounts and Feature 3: Cost-of-Living Tracker
- Implement registration, login, logout, and secure password hashing.
- Add CSRF protection and session security.
- Create expense CRUD operations and monthly/category summaries.
- Enforce record ownership.
- Compare personal spending growth with compatible CPI periods.
- Add privacy and deletion behaviour.

**Deliverable:** Personal spending tracker for authenticated users.

### Milestone 8 — Feature 5: Quick Stats Widget
- Build a reusable compact stats component.
- Add a route or component for the latest cached value.
- Show reference period and stale status.
- Test responsive layout and accessibility.

**Deliverable:** An in-app quick stats widget. Native phone home-screen widgets can be evaluated later.

### Milestone 9 — Feature 4: Inflation Alerts
- Build alert-rule forms and validation.
- Add a scheduled refresh/evaluation task.
- Detect new data and threshold crossings.
- Add idempotent notification creation.
- Add an in-app notification list and read state.
- Test retries and duplicate prevention.

**Deliverable:** Configurable in-app alerts.

### Milestone 10 — Feature 6: Economic Chatbot
- Define supported question types and safe response boundaries.
- Retrieve relevant statistics through the data service.
- Add a chatbot service abstraction.
- Optionally connect an LLM provider using environment-based credentials.
- Require source periods and citations/links for numerical answers.
- Handle timeouts, rate limits, missing data, and unavailable credentials.
- Add a non-AI fallback for common questions if practical.
- Document privacy implications before sending any user data to an external service.

**Deliverable:** A chatbot that explains verified data and admits when it cannot answer.

### Milestone 11 — Hardening and Release
- Run all unit, integration, route, and end-to-end tests.
- Test keyboard navigation and mobile layouts.
- Review security, error handling, logs, and configuration.
- Add production WSGI configuration and HTTPS deployment.
- Verify scheduled jobs run reliably in the deployment environment.
- Write user documentation and a project architecture summary.

**Deliverable:** Release candidate with setup and maintenance documentation.

## 3. Recommended Implementation Order

The sequence above prioritises data reliability before features that depend on it. Features 1, 2, and 8 provide an early usable version. Features 3, 4, 5, 6, and 7 can then be layered onto the same data and service architecture.

The eight features remain in scope even though delivery is phased.

## 4. Definition of Done

A feature is complete when:
- Requirements and acceptance criteria are met.
- Input validation and error states are implemented.
- Unit and relevant integration tests pass.
- Data source and reference periods are visible where applicable.
- Security and privacy checks are complete.
- UI is usable on desktop and mobile.
- Documentation is updated.
- No secrets or personal data are committed to source control.

## 5. Initial Dependencies

Suggested starting dependencies (verify compatible versions when installing):
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Login
- Flask-WTF
- requests
- python-dotenv
- pytest
- A charting library such as Chart.js (frontend asset)
- Optional: a maintained scheduler/task queue when scheduled jobs are introduced
- Optional: an LLM provider SDK for the chatbot

Do not install every optional dependency at the start. Add packages when the related milestone begins.

## 6. Development Practices

- Use feature branches and meaningful commits.
- Keep API requests in a provider client/service, not in templates.
- Keep credentials in `.env`, and commit only `.env.example`.
- Mock upstream responses in tests instead of relying on the live API for every test.
- Record verified dataset schema and example responses in developer notes without including secrets.
- Use migrations for database changes.
- Review charts and calculations for misleading labels or period mismatches.
