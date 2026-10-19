# Security

This project is a local finance-operations demonstration. It requires additional deployment hardening before handling production financial records. See [operations](docs/operations.md) and the README's deployment limits.

- Keep generated secrets in `.env` and n8n's encrypted credential store; never publish them in issues or screenshots.
- Keep Docker ports bound to loopback unless you have configured HTTPS, authentication, and appropriate access controls.
- Review extracted fields before approval. Payment confirmation records an external payment; it does not transfer money.
- Reconcile uncertain email delivery before retrying to avoid duplicate reminders.
- Back up PostgreSQL, n8n data, and the n8n encryption key securely.

Report security problems privately to the repository maintainer using GitHub private vulnerability reporting if available. Do not include credentials, personal invoices, or exploit details in a public issue. If a secret is exposed, revoke or rotate it immediately; removing the file from the latest commit does not remove it from history.
