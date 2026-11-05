# Myconomy — Testing Plan

## 1. Purpose

This plan defines how to test Myconomy's eight features, data integration, security, reliability, and user experience.

## 2. Testing Levels

- **Unit tests:** Test calculation functions, validation, schema mapping, and alert rules in isolation.
- **Integration tests:** Test database operations, provider client behaviour, cache logic, and service interactions.
- **Route tests:** Use Flask's test client to verify HTTP responses, permissions, form validation, and error states.
- **End-to-end tests:** Test complete user journeys through the browser.
- **Manual usability/accessibility tests:** Check responsive layout, keyboard navigation, labels, chart readability, and understandable error messages.
- **Operational tests:** Verify scheduled jobs, logging, backups, and recovery from failed data refreshes.

## 3. Test Environment

- Use a separate test database; never run destructive tests against real user data.
- Mock OpenDOSM responses for deterministic automated tests.
- Use synthetic users and expense records.
- Keep LLM integration tests mocked by default; use a separately configured sandbox only for optional live checks.
- Test configuration must not contain production secrets.
- Add a small number of optional smoke tests against the real public API, but do not make the whole test suite depend on network availability.

## 4. Feature Test Cases

### Feature 1 — Economic Dashboard

| ID | Test | Expected result |
|---|---|---|
| DASH-01 | Valid cached indicator data exists | Dashboard displays value, unit, reference period, source, and retrieval time |
| DASH-02 | Historical data contains multiple valid periods | Chart displays correctly ordered points |
| DASH-03 | Provider returns an empty list | Clear no-data state; app does not crash or erase valid prior data automatically |
| DASH-04 | Provider times out | Cached snapshot is shown with stale warning, or a clear unavailable state appears |
| DASH-05 | Response schema changes | Validation catches the mismatch and prevents invalid values from being displayed as valid |
| DASH-06 | User selects an unsupported indicator/period | Safe validation message; no server error |

### Feature 2 — Purchasing Power Calculator

| ID | Test | Expected result |
|---|---|---|
| CALC-01 | Valid amount and compatible CPI periods | Correct equivalent amount is returned |
| CALC-02 | Source and target periods are the same | Result equals the input amount, assuming the same positive CPI value |
| CALC-03 | Amount is negative or non-numeric | Validation error; no calculation |
| CALC-04 | One period is unavailable | Clear message; no fabricated estimate |
| CALC-05 | CPI value is missing, zero, or invalid | Calculation is rejected safely |
| CALC-06 | Formula direction is checked with known values | Result matches the independently calculated ratio |

### Feature 3 — Personal Cost-of-Living Tracker

| ID | Test | Expected result |
|---|---|---|
| EXP-01 | Authenticated user creates an expense | Valid record is saved |
| EXP-02 | User edits or deletes their own expense | Only the intended record changes |
| EXP-03 | User attempts to access another user's record | Request is denied without exposing the record |
| EXP-04 | Amount, month, or category is invalid | Server rejects the input |
| EXP-05 | Monthly summary is requested | Totals and category breakdown match test records |
| EXP-06 | CPI comparison periods are incompatible | Comparison is withheld or clearly marked unavailable |

### Feature 4 — Inflation Alerts

| ID | Test | Expected result |
|---|---|---|
| ALERT-01 | Valid threshold rule is saved | Rule is persisted with correct settings |
| ALERT-02 | Indicator crosses a configured threshold | One notification is created |
| ALERT-03 | Same source event is processed twice | No duplicate notification |
| ALERT-04 | New reference period appears | New-data alert is created once for eligible rules |
| ALERT-05 | Refresh fails | No false new-data alert is created |
| ALERT-06 | Rule is inactive | No notification is generated for it |

### Feature 5 — Quick Stats Widget

| ID | Test | Expected result |
|---|---|---|
| WID-01 | Fresh data exists | Widget displays value, indicator, and reference period |
| WID-02 | Cached data exceeds freshness threshold | Widget displays a stale indicator |
| WID-03 | No data exists | Widget shows a compact unavailable state |
| WID-04 | Narrow viewport or keyboard navigation is used | Content remains usable and accessible |

### Feature 6 — Economic Chatbot

| ID | Test | Expected result |
|---|---|---|
| CHAT-01 | User asks for a supported figure | Answer uses retrieved data and includes period/source |
| CHAT-02 | No relevant observation exists | Bot says data is unavailable rather than inventing a value |
| CHAT-03 | LLM provider times out or rate-limits | Graceful error or fallback response |
| CHAT-04 | User asks an unsupported or unrelated question | Bot states its scope and redirects appropriately |
| CHAT-05 | Prompt attempts to override data constraints | Bot continues to use verified retrieval and does not fabricate statistics |
| CHAT-06 | Personal spending data is not needed | No personal record is sent to the external model |

### Feature 7 — Multi-Indicator Explorer

| ID | Test | Expected result |
|---|---|---|
| IND-01 | Valid dataset mapping is configured | Data is normalised and displayed with the correct unit |
| IND-02 | One dataset has a different schema | Its own mapping is used; other datasets continue working |
| IND-03 | Data has different geographic or temporal scope | UI shows the scope and avoids misleading comparison |
| IND-04 | Dataset is disabled or unavailable | User sees a clear unavailable state |
| IND-05 | Values contain missing or malformed fields | Invalid observations are rejected or explicitly marked missing |

### Feature 8 — Learn & Understand

| ID | Test | Expected result |
|---|---|---|
| LEARN-01 | User opens an educational page | Content is readable and links to relevant sources |
| LEARN-02 | Page contains an illustrative example | It is clearly labelled as illustrative |
| LEARN-03 | Calculation explanation is displayed | Formula and wording match the implemented calculation |
| LEARN-04 | User navigates by keyboard | Links and interactive elements are reachable and labelled |

## 5. Data Integration and Reliability Tests

| ID | Test | Expected result |
|---|---|---|
| DATA-01 | Valid JSON and expected fields | Response is parsed and saved |
| DATA-02 | Invalid JSON | Error is logged safely; previous good data remains |
| DATA-03 | HTTP 429 rate limit | Retry/backoff policy is respected; no rapid retry loop |
| DATA-04 | HTTP 5xx response | Bounded retry policy applies; cached data remains available |
| DATA-05 | HTTP 4xx response | Error is handled without endless retries |
| DATA-06 | Response is empty | Empty state is handled and prior data is not discarded without policy |
| DATA-07 | Historical result is paginated | All required pages are fetched within configured limits |
| DATA-08 | Data is stale but available | UI labels freshness accurately |
| DATA-09 | Scheduled job runs twice | Data remains consistent and alerts are not duplicated |
| DATA-10 | Provider adds/removes a field | Schema validation detects unexpected changes and avoids silent corruption |

## 6. Security Tests

- Verify password hashes are stored rather than plaintext passwords.
- Verify unauthenticated users cannot access protected spending and alert routes.
- Verify one user cannot read, update, or delete another user's records.
- Verify CSRF protection on state-changing forms.
- Verify database queries use ORM/parameterised operations.
- Verify secrets are absent from repository files, logs, and error responses.
- Verify production error pages do not expose stack traces.
- Verify login and chatbot routes have appropriate abuse/rate controls.
- Verify user-controlled text is safely rendered and cannot inject executable HTML.
- Verify session and cookie settings are secure in production.

## 7. Performance and Usability Tests

- Measure dashboard response time with cached data.
- Confirm normal page views do not cause unnecessary provider requests.
- Test charts with longer historical ranges.
- Test mobile and desktop viewport sizes.
- Check contrast, keyboard focus, form labels, and accessible chart summaries.
- Confirm currency formatting and period labels are consistent.
- Confirm stale, loading, empty, and failure states are visually distinct.

## 8. Backup and Recovery Tests

- Back up the database using the selected deployment procedure.
- Restore a backup into a test environment.
- Simulate provider downtime and verify the app uses the last successful snapshot.
- Simulate a failed scheduled task and verify it is observable and can be rerun safely.
- Confirm logs omit credentials and unnecessary personal information.

## 9. Entry and Exit Criteria

### Entry
- Requirements and dataset mappings for the tested feature are documented.
- Test environment and fixtures are available.
- Relevant implementation is deployed to the test environment.

### Exit
- All critical and high-priority tests pass.
- No known critical security or data-integrity defects remain.
- Error and stale-data paths have been tested.
- Calculator results are independently verified.
- All eight features have documented test coverage, even if some are scheduled for later milestones.
- Known limitations are recorded before release.

## 10. Test Reporting

For each test run, record:
- Test ID and build/commit.
- Environment and date.
- Result: Pass, Fail, Blocked, or Not Run.
- Actual result and expected result.
- Defect reference and severity, if applicable.
- Retest result after a fix.
