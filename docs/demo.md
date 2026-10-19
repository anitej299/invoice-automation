# Demo and interview guide

## Five-minute walkthrough

1. Show the dashboard and explain separate currency totals.
2. Open seeded DEMO-008 (invalid total). Attempt approval; the API blocks it. Correct the total to 11800 and save. Show validation and audit records.
3. Approve with a review note, record a fictional payment reference, and show PAID and paid_at. Explain that actual money movement is external.
4. Show the duplicated DEMO-001 and why it is reviewable but cannot be paid.
5. Keep Ollama running with `llama3.2` pulled, then upload a sample and a broken PDF. The valid sample extracts using the local model; the broken one remains visible for review. Explain schema-constrained LLM extraction versus the deterministic `local` parser used in offline tests.
6. Show the four n8n workflows and notification reservation/acknowledgement design. With OAuth configured, demonstrate two attachments in one email and rerun idempotency.

## Interview explanation

“I built a finance workflow that turns invoice attachments into validated, reviewable records. n8n handles OAuth and orchestration; FastAPI owns deterministic business rules and PostgreSQL transactions. OCR and an LLM produce a typed extraction, but that output cannot approve or pay an invoice. I use one idempotency key for attachment retries and another identity for business duplicates. Human approval gates payments. Reminder reservations and delivery acknowledgements make ambiguous email delivery visible instead of blindly resending.”

Discuss tradeoffs with specifics: synchronous extraction is simpler to explain, but a leased worker queue is needed for higher throughput; vendor names are weak identities; currencies must never be summed without conversion; database transactions cannot make Gmail sending exactly-once; confidence is a model signal rather than a calibrated guarantee.

## Resume bullets

- Built an invoice processing platform with FastAPI, PostgreSQL, React and n8n, integrating Gmail/Drive intake, OCR and structured LLM extraction.
- Implemented deterministic validation, risk scoring, guarded payment state transitions, attachment idempotency, and audit history.
- Added daily payment monitoring with database-enforced reminder reservations, currency-aware reporting, Docker deployment and automated API/UI tests.

Do not invent throughput, cost reduction or accuracy metrics. Measure those with representative documents and provider configuration before claiming them.
