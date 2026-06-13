# Template Onboarding (Agent Workflow)

Agent workflow for **cloning this repository into a new product**. User-facing
steps live in `docs/template-onboarding.md` and `docs/template-usage.md`.

## When to use

User says: new project, fork template, clone for X, onboard example-app, strip
unused modules.

## Agent steps

### 1. Discover product context

Ask or infer (minimal questions):

- Product / repo name
- Domain (what the new API will add beyond template modules)
- Which template modules stay enabled: auth, multi-tenancy, workers, uploads,
  webhooks, audit logs, observability stack
- Registration policy (`public` vs `disabled`)
- Platform admin model (demo `platform_admin` vs fork-specific design — see
  `docs/platform-admin-model.md`)

### 2. Rename placeholders

| Item | Location |
|------|----------|
| README title and links | `README.md` |
| App name | `APP_NAME` env or `settings.app_name` |
| Dev seed emails | `app/seed_dev_data.py` |
| Example image in Makefile dry-run | `Makefile` `deploy-dry-run` |
| GitHub repo | remote URL; release uses `GITHUB_REPOSITORY` automatically |

Do **not** rename internal Python package `app` unless user explicitly requests
a package rename (large scope).

### 3. Environment and secrets

- Copy `.env.example` → `.env`; generate strong `SECRET_KEY`
- Document required production vars in fork runbook (see
  `TEMPLATE_FREEZE_CHECKLIST.md`)
- Remove or rotate any shared staging credentials

### 4. Validate locally

```bash
make bootstrap   # or docker-up + migration-upgrade + seed-tenant + seed + smoke
make validate
make policy-guards
make validate-ai-workflows
```

### 5. Trim optional modules (only if requested)

If user disables a module, plan safe removal:

- Routes: unregister from `app/api/v1.py`
- Services/models: only remove with migration plan
- Docs: update README and `PROJECT_STATUS.md` to match **actual** code
- Do not leave docs claiming features that were removed

### 6. Produce next-project checklist

Output for the user:

- Completed rename/config steps
- Enabled modules
- First domain module suggestion (models → migration → service → route → tests)
- Production decisions still open (hosting, SMTP, S3, Redis HA)
- Links: `docs/production-deployment.md`, `docs/production-runtime-examples.md`

Use `.commands/template-onboard.md` for a copy-paste onboarding prompt.

Persona: `agents/template-onboarding-agent.md`.
