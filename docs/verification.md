# Verification record

Verified on 14 October 2026 in the local Windows development environment.

| Check | Result |
|---|---|
| Backend pytest | 33 tests passed against isolated SQLite databases (updated 15 October 2026), including Ollama request format, output validation, input bounds and missing-model errors |
| Frontend Vitest | 5 tests passed, including stale-response navigation regression |
| TypeScript and production Vite build | Passed; route bundles split without oversized-chunk warning |
| npm dependency audit | 0 vulnerabilities reported after build/test dependency updates |
| Python compilation and application import | Passed |
| Alembic upgrade and seed | Passed locally; 10 seeded scenario records |
| Alembic schema drift check | No new upgrade operations detected |
| Generated OpenAPI | 20 paths; required dashboard, invoice, search, processing and auth paths present |
| Docker Compose configuration | `docker compose config --quiet` passed |
| Docker build and startup | Backend/frontend Linux images built; PostgreSQL and backend health checks passed; frontend API proxy health check passed |
| PostgreSQL runtime | Migrations, demo seed, Alembic drift check, and browser-backed invoice/dashboard queries passed in Docker |
| Docker browser smoke | Login, dashboard, invoice review, vendors, audit and mobile navigation passed at localhost:8080; both frontend and backend URLs returned HTTP 200 |
| Ollama integration (15 October) | Pulled llama3.2; native schema-constrained extraction of demo-01.pdf passed both on the host and from the Docker backend. Verified invoice number DEMO-001, total INR 11800 and one line item; frontend API stayed responsive during inference |
| Startup-order recovery | Stopped backend and restarted frontend: frontend still served HTTP 200. Restarted backend: proxied health recovered to HTTP 200 without another frontend restart |
| n8n files | All four parse as JSON; unique node names, valid graph targets, inactive, no embedded credentials |
| Actual PDF processing | Fictional PDF text extracted, parsed, validated and persisted through the API test |
| PDF visual inspection | All 10 PDFs rendered with Poppler and inspected as a contact sheet |
| Browser smoke | Fresh headless Edge: login, dashboard, invoice review gate, vendors, audit navigation and mobile layout; no page errors |
| Screenshots | Dashboard, invoice review and mobile views captured from the running application |

The mocked OpenAI test checks strict response format and Pydantic parsing; it does not call a real model. Unit tests cover required fields, dates, totals/tolerance, duplicates and similarity, high value/risk, state transitions, authentication, payment idempotency, extraction failure, multiple attachments, reminder claims and currency-separated reporting.

## Checks requiring the deployment environment

- The initial Docker engine availability limitation was resolved on 14 October. Full container build/start and PostgreSQL-backed browser operation are now verified. Multi-worker concurrency stress tests remain unverified.
- On 17 October 2026, Gmail intake and payment monitoring were imported, tested and published in the local deployment. The repository templates remain inactive for safe onboarding.
- Gmail reading, Drive archival and backend intake were exercised on 17 October. An encrypted document correctly remained UNDER_REVIEW after OCR failed; this is not proof of successful invoice extraction through the full email path. A separate Gmail setup email returned SENT. Payment monitoring succeeded with no eligible reminders, so live reminder acknowledgement was not exercised. OAuth refresh longevity and a live OpenAI response remain unverified. Local Ollama `llama3.2` was tested against the fictional sample PDF on 15 October: invoice number, vendor, currency, total and line items extracted successfully in about one minute on CPU.
- Scanned/image OCR requires Tesseract. Text-PDF processing was exercised locally; image OCR should be included in Docker acceptance testing.

These are explicit verification boundaries, not claims of live integration success. Follow the README's end-to-end checklist after configuring the accounts.

One dependency deprecation warning remains in backend tests: the installed Starlette test client warns about a future transport change from httpx. It does not affect the passing application/API tests.
