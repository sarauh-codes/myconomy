# Myconomy — Requirements Specification

## 1. Purpose

This document defines the functional and non-functional requirements for Myconomy. Requirements should be treated as planned behaviour until implemented and tested.

## 2. User Roles

- **Guest:** Can access public statistics and learning features.
- **Registered user:** Can manage personal spending, alert preferences, and saved settings.
- **System scheduler:** Refreshes cached data and evaluates alerts.
- **Maintainer:** Reviews logs and service health. Administrative screens are optional for the first release.

## 3. Functional Requirements

### FR-01 — Economic Dashboard
- Display available headline CPI/inflation values and other configured indicators.
- Show the reference period, unit, source, and last successful retrieval time.
- Provide historical charts only when sufficient valid historical data exists.
- Provide loading, empty-data, stale-data, and error states.
- Let users choose among available indicators and supported periods.

### FR-02 — Purchasing Power Calculator
- Accept a non-negative amount and two valid reference periods.
- Retrieve CPI values for both periods from a compatible series.
- Calculate an equivalent amount using: `equivalent_amount = input_amount × (CPI_target / CPI_source)`.
- Explain that this is a CPI-based estimate, not a guarantee of an individual's actual costs.
- Reject missing, non-numeric, negative, or unsupported inputs and handle a zero/missing CPI safely.
- Display both periods, the values used, the formula, and the source.
- Confirm the direction of comparison in the UI to avoid ambiguity.

### FR-03 — Personal Cost-of-Living Tracker
- Require authentication before accessing personal records.
- Allow users to create, view, edit, and delete monthly expense entries.
- Store amount, category, month, optional note, and owner.
- Validate amounts and dates on the server.
- Summarise spending by month and category.
- Compare a user's spending change with national CPI change over comparable periods, clearly labelling the comparison as indicative.
- Ensure users can access only their own records.

### FR-04 — Inflation Alerts
- Allow authenticated users to configure a threshold alert and/or a new-data alert.
- Store alert type, threshold where relevant, active status, and delivery preference.
- Check for new source data on a schedule appropriate to the provider's release frequency.
- Create an alert event only once for a given user, rule, and source data period/value.
- Show in-app notifications in the initial release. Email or messaging delivery is optional and requires provider configuration.
- Show the relevant period and source in the alert.
- Handle failed scheduled runs and avoid repeatedly sending duplicate alerts.

### FR-05 — Quick Stats Widget
- Provide a reusable compact component for displaying selected latest indicators.
- Include the value, indicator name, reference period, and a link to details/source.
- Use cached data and show stale status when applicable.
- Support responsive layout and accessible text.
- Native mobile home-screen widgets are a future extension, not a requirement for the first web release.

### FR-06 — Economic Chatbot
- Accept natural-language questions about supported indicators and concepts.
- Retrieve relevant values and metadata from the application's verified data layer before answering numerical questions.
- Include reference periods and sources for factual statistical answers.
- Explain uncertainty and say when data is unavailable rather than inventing a number.
- Separate calculations and retrieved facts from general educational explanations.
- Limit scope to supported economic topics; do not present answers as personalised financial advice.
- Handle missing LLM credentials, timeouts, rate limits, and provider errors gracefully.
- Do not send personal spending data to an external model unless the user has clearly consented and the data handling is documented.

### FR-07 — Multi-Indicator Explorer
- Register each indicator with its source dataset, schema mapping, unit, frequency, and coverage.
- Allow users to browse supported datasets such as GDP, unemployment, and population only after verifying the source datasets.
- Display the indicator's unit, reference period, geographic scope where relevant, and source.
- Do not compare values with incompatible units or periods.
- Handle dataset-specific schemas, missing values, and update schedules.

### FR-08 — Learn & Understand
- Provide educational pages for CPI, inflation, purchasing power, and supported economic indicators.
- Use simple language, examples, and interactive demonstrations where appropriate.
- Clearly distinguish illustrative examples from official figures.
- Link explanations to the relevant official sources.
- Review content when calculation logic or source definitions change.

### FR-09 — Data Retrieval, Caching, and Refresh
- Use a backend service layer for upstream API requests; do not call the API independently from every page.
- Set connection and read timeouts.
- Validate response status, JSON format, expected structure, and required fields.
- Handle empty arrays, missing fields, unexpected data types, schema changes, and upstream errors.
- Cache successful responses with a configurable time-to-live appropriate to each dataset's release frequency.
- Preserve the last successful data snapshot when refresh fails.
- Display the reference period separately from the retrieval timestamp.
- Record refresh status and errors without storing secrets.
- Use pagination or a suitable historical endpoint when a feature needs historical records.
- Respect provider guidance and avoid unnecessary polling.

### FR-10 — Authentication and Account Management
- Provide secure registration, login, logout, and password hashing if accounts are enabled.
- Validate all input on the server.
- Protect state-changing routes against CSRF.
- Use secure session configuration in production.
- Allow a user to manage their own preferences and records.

### FR-11 — Observability and Maintenance
- Record refresh outcomes, application errors, and scheduled-task failures.
- Avoid logging passwords, session secrets, API keys, or unnecessary personal data.
- Provide a basic health/status check for the application and data-refresh process.

## 4. Non-Functional Requirements

### NFR-01 — Usability
- Use clear labels and simple explanations.
- Make reference periods and stale-data notices easy to see.
- Provide consistent loading, empty, success, and error states.

### NFR-02 — Performance
- Serve cached data for normal page views whenever appropriate.
- Avoid a blocking upstream request for every page load.
- Paginate or limit large personal and statistical result sets.

### NFR-03 — Reliability
- The application must remain usable when the upstream provider is temporarily unavailable, using the last valid cached snapshot where possible.
- Failed refreshes must not overwrite good data with invalid or empty responses unless an empty response is explicitly verified as legitimate.

### NFR-04 — Security and Privacy
- Store passwords using a recognised password-hashing method.
- Use parameterised database operations/ORM protections.
- Enforce ownership checks for personal records.
- Protect forms and sessions.
- Keep secrets in environment variables or a secret manager, never in source control.
- Minimise collection and retention of personal data.

### NFR-05 — Data Integrity
- Store source identifiers and reference periods.
- Validate numeric values and units.
- Keep raw-source snapshots or enough metadata to audit displayed figures, subject to reasonable storage limits.

### NFR-06 — Accessibility and Responsive Design
- Support keyboard navigation and labelled form controls.
- Do not rely on colour alone to communicate chart meaning.
- Make layouts usable on desktop and mobile browsers.

### NFR-07 — Maintainability
- Separate routes, business logic, data access, and templates.
- Keep indicator-specific schema mappings in configuration/service code rather than scattering field assumptions throughout templates.
- Use automated tests and documented setup steps.

## 5. Constraints and Dependencies

- OpenDOSM is an external dependency and may be temporarily unavailable or change its schema.
- CPI is published periodically; a successful API request does not mean the figure describes the current day.
- Chatbot use may require a third-party API key and may incur cost. Keep the chatbot provider replaceable.
- Scheduled alerts require a reliable scheduler or external scheduled task.
- SQLite is suitable for an initial local/single-instance deployment; deployment architecture may require PostgreSQL or a separate task queue.

## 6. Acceptance Criteria

- All eight features have a route/page or clearly documented UI entry point.
- The dashboard displays data provenance and reference period.
- Calculator results match independently verified formula tests.
- Spending CRUD operations enforce user ownership.
- Alerts are generated without duplicates in tests.
- Widget shows a stale state when cached data exceeds its configured freshness threshold.
- Chatbot numerical answers are grounded in retrieved data or explicitly report that data is unavailable.
- Multi-indicator views show correct units and source metadata.
- Educational content links to official sources.
- Empty data, malformed JSON, timeouts, rate limits, and server errors are tested.
