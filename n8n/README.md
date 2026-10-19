# n8n workflows

Import the four files in `workflows/` through **Import from file** in the n8n editor. They are inactive and contain no credential values or credential IDs. The Compose image is pinned; validate against your chosen n8n version before upgrading it.

For CLI import into the local Compose instance:

```powershell
docker compose exec n8n n8n import:workflow --separate --input=/workflows
```

After import, select Gmail OAuth2, Google Drive OAuth2, backend HTTP Header Auth (`X-Automation-Key`), and webhook Header Auth credentials in the editor. Replace the Drive folder ID. Configure the owner account through n8n's first-run UI. `N8N_USER`/`N8N_PASSWORD` are not an automatic account-provisioning mechanism.

## Invoice intake

The trigger polls every minute using:

```text
has:attachment (subject:invoice OR filename:invoice) (filename:pdf OR filename:png OR filename:jpg OR filename:jpeg)
```

Include **invoice** in the email subject or attachment filename. Use an unencrypted PDF or supported image. Password-protected documents cannot be extracted and are sent to review.

Gmail trigger finds supported attachments, Gmail Get downloads them, Code splits each binary into an individual item, and Loop Over Items processes one at a time. Drive upload preserves the original; Restore Attachment Context restores both source metadata and binary after Drive returns its file metadata. Backend Process sends multipart form data with the binary field `data` named `file`.

Read-only Gmail download and idempotent backend processing retry transient errors. Drive upload does not retry automatically after an uncertain response. Drive/backend error outputs log the error and return to the attachment loop, so another attachment can continue. A Gmail-download failure appears in execution error output; rerun that message after fixing OAuth/network access.

The backend key includes message, attachment, filename, and bytes. Re-executing intake can leave another Drive copy, but it cannot create another invoice for the same attachment. Drive upload and backend commit are not one transaction. Reconcile orphaned Drive files from failed runs before manual retry.

## Payment monitoring

At 08:00 Asia/Kolkata: call `/automation/monitor`, claim that day's due-soon/overdue notifications, loop through Gmail sends, then acknowledge each returned message ID. Change both the workflow timezone and backend TIMEZONE if your business timezone differs. Reminders go to FINANCE_EMAIL, not an OCR-extracted vendor address.

## High-risk alerts

Every 15 minutes: claim HIGH invoices still UNDER_REVIEW, send the supplied plain-text finance message, and acknowledge delivery. The daily database uniqueness rule prevents repeated polling from resending the same alert that day.

## Payment update

Activate the authenticated webhook. Use its production URL, not the test URL, for an actual integration. Example PowerShell request (use your own secret via environment variable):

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:5678/webhook/invoice-payment-confirmed `
  -Headers @{ 'X-Payment-Webhook-Key' = $env:PAYMENT_WEBHOOK_KEY } `
  -ContentType application/json `
  -Body '{"invoice_id":1,"payment_reference":"CONFIRMED-PAYMENT-001"}'
```

The backend rejects unapproved, rejected and otherwise invalid payment transitions. Repeating a confirmation for an already-paid invoice is a no-op. This webhook records confirmation; it never executes a transfer.

## Failure reconciliation

### Google sign-in troubleshooting

- `redirect_uri_mismatch`: register the exact callback displayed in the n8n credential. For the local Docker setup it is `http://localhost:5678/rest/oauth2-credential/callback`. Use localhost consistently when signing in.
- `Request had insufficient authentication scopes`: reconnect the Gmail credential and approve both reading and sending permissions. The configured scope list alone does not prove the account granted them. Intake needs `https://www.googleapis.com/auth/gmail.readonly`; reminders need `https://www.googleapis.com/auth/gmail.send`.
- For uploads to a pre-existing Drive folder, authorize Drive access and verify that the connected account can write to that folder.
- First test intake and a one-time email to your configured finance inbox. Publish the intake and payment-monitoring workflows only after successful tests. High-risk alerts and payment webhooks are optional separate workflows.

Credentials and activation state belong to each deployment. The repository deliberately contains inactive templates with placeholders, not a copy of an authorized n8n database.

Inspect failed executions and backend `reminders`/`processing_jobs`. A reserved notification is deliberately not auto-retried: the email might already have been sent. Check Gmail Sent, then acknowledge its actual Gmail message ID through the API. For a confirmed unsent email, manually send once and acknowledge it. Do not delete reminder rows to bypass uniqueness.

Set an n8n error workflow or external monitoring before unattended deployment. Execution records may contain invoice data; retention is seven days in Compose. Successful execution payloads are not retained by these workflows. Google OAuth is a manual setup step; live OAuth and delivery need acceptance testing with the user's account.

Regenerate/validate files if modifying the generator:

```powershell
python scripts/build_workflows.py
python scripts/validate_workflows.py
```
