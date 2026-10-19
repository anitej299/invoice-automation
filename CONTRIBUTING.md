# Contributing

Use fictional invoices and an isolated development database. See the README for Docker and local setup, configuration, and test commands.

1. Create a branch for your change.
2. Keep backend rules and approval gates deterministic; treat OCR and model output as untrusted input.
3. Add focused tests when changing behavior. Run backend pytest, frontend tests/typecheck/build, and `python scripts/validate_workflows.py` for affected components.
4. If changing n8n workflows, update `scripts/build_workflows.py` and regenerate the JSON templates. Keep templates inactive and credential-free.
5. Describe the behavior change, verification, and any migration or configuration requirements in your pull request.

Never commit `.env`, OAuth tokens, workflow execution exports, database dumps, real invoices, or personal customer information. Use `.env.example` for configuration names and placeholders. Do not add an open-source license without the repository owner's choice.
