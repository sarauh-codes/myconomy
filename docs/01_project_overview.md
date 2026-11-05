# Myconomy — Project Overview

**Tagline:** Understand Malaysia's economy.  
**Project type:** Web application  
**Proposed stack:** Python, Flask, SQLite, HTML, CSS, JavaScript  
**Primary data source:** OpenDOSM, provided by Malaysia's Department of Statistics Malaysia (DOSM)

## 1. Project Summary

Myconomy is a web platform that makes Malaysian economic statistics easier to explore and understand. It combines official open data, interactive visualisations, practical calculators, personal spending tools, alerts, and educational explanations in one application.

The application is intended for Malaysians, students, researchers, and anyone interested in how economic changes affect everyday life.

## 2. Problem Statement

Official economic statistics can be difficult for the general public to interpret. Data may be spread across datasets, and users may not know how inflation relates to purchasing power or their personal spending. Myconomy presents relevant data in a more approachable interface and explains what the numbers do—and do not—mean.

## 3. Goals

- Present official Malaysian economic statistics with clear reference periods and sources.
- Help users explore CPI and inflation trends.
- Explain changes in purchasing power using transparent calculations.
- Let users track their own spending and compare it with national CPI trends.
- Offer configurable notifications when new data is available or a chosen threshold is crossed.
- Answer supported economic questions using retrieved data and clearly identify the data period.
- Expand beyond CPI to other suitable OpenDOSM datasets.
- Teach users basic economic concepts through examples.

## 4. Scope: Eight Main Features

1. **Economic Dashboard:** Summary cards, historical charts, latest available values, reference periods, and data-source links.
2. **Purchasing Power Calculator:** Compare the purchasing power of an amount between two periods using CPI values.
3. **Personal Cost-of-Living Tracker:** Let signed-in users record monthly spending by category and compare spending growth with CPI.
4. **Inflation Alerts:** Let users configure thresholds and/or new-data notifications. A scheduled job checks for updates and creates notifications.
5. **Quick Stats Widget:** Display a compact, embeddable in-app widget with the latest available statistics and reference period. Native phone home-screen widgets are a possible later extension.
6. **Economic Chatbot:** Answer supported questions using retrieved, dated statistics and reliable explanations. The chatbot must not invent figures.
7. **Multi-Indicator Explorer:** Explore additional datasets such as GDP, unemployment, and population after verifying their availability, schema, coverage, and update frequency.
8. **Learn & Understand:** Explain CPI, inflation, purchasing power, and other indicators with simple language and interactive examples.

## 5. Out of Scope for the Initial Release

- Providing investment, tax, or personalised financial advice.
- Claiming national CPI exactly reflects an individual's cost of living.
- Guaranteeing real-time economic figures when the source publishes periodically.
- Training a custom large language model.
- Native Android/iOS applications or native phone home-screen widgets in the first release.
- Automatically importing bank transactions.

## 6. Users

- **Guest:** Browse public dashboards, calculators, educational content, and the in-app quick stats widget.
- **Registered user:** Save spending records, alert preferences, and personal settings.
- **Administrator/maintainer:** Monitor data refreshes and application errors; manage system configuration. An admin interface is optional for the first release.

## 7. Success Measures

- Dashboard data includes a visible reference period and source.
- The app handles empty responses, API errors, and stale data without crashing.
- CPI calculations are covered by unit tests and display the formula used.
- Users can create, edit, view, and delete their spending records.
- Alerts do not repeatedly notify users for the same event.
- Chatbot answers distinguish sourced facts from general explanations.
- All eight features are represented in the design; delivery is phased.

## 8. Data Source and Assumptions

Initial example endpoint:

`GET https://api.data.gov.my/opendosm?id=cpi_headline&limit=1`

Documentation: https://developer.data.gov.my/static-api/opendosm

The example endpoint returns at most one row, so it is not sufficient by itself for historical charts or period-to-period calculations. Confirm the dataset schema, historical coverage, pagination options, and actual field names from the official documentation and live responses before implementation. Do not hard-code unverified field names.

Other indicators will use separately verified OpenDOSM datasets. The application must show the data's reference period, last successful retrieval time, and source.

## 9. Proposed Technology

- **Backend:** Python and Flask
- **Frontend:** HTML templates (Jinja), CSS, JavaScript
- **Charts:** A JavaScript charting library such as Chart.js
- **Database:** SQLite for the initial single-instance version; consider PostgreSQL for a deployed multi-user version
- **Database layer:** SQLAlchemy and Flask-Migrate/Alembic
- **HTTP client:** Requests
- **Validation/configuration:** Environment variables and server-side validation
- **Testing:** pytest and Flask's test client
- **Scheduling:** A separate scheduled task/worker for refreshes and alerts; do not rely on an in-process timer for production
- **Chatbot:** Optional LLM API behind a service layer, with retrieval from verified data and clear failure handling

## 10. Key Risks

- Upstream API downtime, schema changes, or incomplete historical coverage.
- Misinterpreting CPI or mixing incompatible indicator periods/units.
- Stale data presented as current.
- Unreliable chatbot answers.
- Privacy risks from personal spending records.
- Background tasks running twice or missing execution in a multi-worker deployment.

Mitigations are detailed in the requirements, design, and testing documents.
