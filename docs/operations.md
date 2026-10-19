# Operational runbook

## Start, inspect, migrate

```powershell
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 backend n8n
docker compose exec backend alembic current
docker compose exec backend alembic check
```

Never expose the demonstration HTTP configuration publicly. Compose binds ports to loopback. Use TLS and secure cookies for an external n8n hostname, preserve N8N_ENCRYPTION_KEY, and back up the n8n volume and PostgreSQL. Database passwords, LLM keys, OAuth refresh tokens and JWT secrets require a managed secret store in a real deployment.

## Durable processing recovery

A job is committed before OCR. A killed process can leave PROCESSING without a completion time. Inspect jobs older than the maximum expected OCR/LLM duration (30 pages at 45 seconds each plus network time), verify no worker remains, then mark the invoice UNDER_REVIEW and the job FAILED in one transaction with an audit entry. Correct its extracted fields through review. Replaying an attachment returns the existing record rather than hiding a failed job with a new row. A worker queue with leases would automate this recovery at larger scale.

## Ambiguous notification delivery

RESERVED with no sent_at means delivery is unacknowledged, not necessarily unsent. Look up the subject/recipient in Gmail Sent. If present, call the acknowledgement endpoint with its actual Gmail ID. If definitely absent, manually send the reserved message once and acknowledge. Never implement automatic retry by deleting the reservation. Gmail and PostgreSQL cannot commit atomically.

## Auditing and privacy

Audit logs store actor, time and action. Text extraction is sensitive business data. Limit database access, maintain a retention policy, and avoid exporting production invoices into screenshots/test fixtures. n8n error execution data can contain attachments. Workflows save error executions and prune them after seven days under Compose.

## Verification boundaries

Local tests exercise API and rules against SQLite. Validate concurrent reservation and business-key races against PostgreSQL before increasing worker count. Validate imported workflows and OAuth against a disposable mailbox/Drive folder before enabling unattended runs. The repository does not automatically contact Gmail, Drive, or an LLM during tests.
