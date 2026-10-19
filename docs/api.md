# API reference

Interactive, generated schemas: `http://localhost:8000/docs`. Base path: `/api`.

Login with `POST /auth/login` and JSON `{ "email": "...", "password": "..." }`; send `Authorization: Bearer <access_token>` afterward. Automated calls use `X-Automation-Key` instead where supported. All routes except health and login require authentication.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Database connectivity |
| POST | `/auth/login` | JWT login |
| GET / POST | `/invoices` | Search/list or create structured invoice |
| GET / PATCH | `/invoices/{id}` | Detail or partial extraction-field update |
| POST | `/invoices/{id}/approve` | Human approval; blocking errors prohibited |
| POST | `/invoices/{id}/reject` | Human rejection |
| POST | `/invoices/{id}/pay` | Record confirmed payment |
| GET | `/invoices/overdue`, `/invoices/due-soon`, `/invoices/high-risk` | Dedicated paginated queues |
| POST | `/processing/invoice` | Multipart upload and processing |
| GET | `/vendors`, `/audit-logs` | Paginated directory/history |
| GET | `/dashboard/stats`, `/dashboard/charts` | Currency-aware summary/charts |
| GET | `/search` | Invoice search alias |
| GET | `/invoices/{id}/reminders` | Reserved/sent reminder history |
| POST | `/automation/monitor` | Refresh payable date states |
| POST | `/automation/notifications/claim?kind=payment` | Reserve payment notifications |
| POST | `/automation/notifications/claim?kind=risk` | Reserve risk alerts |
| POST | `/automation/notifications/{id}/sent` | Acknowledge Gmail delivery ID |

Invoice query parameters: `page` (1-based), `page_size` (1–100), `q`, `vendor`, `status`, `risk`, `date_from`, `date_to`, `amount_min`, `amount_max`, `sort`, `direction`. Dates filter invoice date, not due date. Sort is allowlisted. Collection responses contain `items` and `total`; invoice collections also return page/page_size. Charts take `currency`, default INR.

Decision endpoints require `{ "reason": "review note or payment reference" }` (3–2000 characters). PATCH accepts only extraction fields; status, paid timestamps, risk output, source URLs and audit records cannot be changed through it. `line_items` replaces items when supplied; omitted fields remain unchanged. Decimal amounts serialize as strings in invoice schemas. Detail returns `items` for persisted line items; input uses `line_items`.

Processing multipart fields: `file` (required), `gmail_message_id`, `attachment_id`, `source_email`, `google_drive_url` (optional). A supported but unreadable file returns HTTP 200 with an UNDER_REVIEW invoice and useful validation errors; caller must examine status. Unsupported extension is 415, oversize file 413, malformed request 422, invalid transition 409, invalid credentials 401, login throttling 429, database outage 503.

Errors use `{ "error": { "code": 409, "message": "..." } }`; invalid fields include field names without echoing sensitive request values. Notification acknowledgement requires `{ "delivery_id": "actual-gmail-message-id" }`.
