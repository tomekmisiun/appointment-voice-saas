# Docker Rules

Docker Compose is the supported local development and CI dependency workflow.

## Rules

- Docker and Compose configuration MUST stay aligned with `app/core/config.py`.
- MUST NOT hardcode production secrets in Docker or Compose files.
- Example values MUST be safe placeholders only.
- MUST NOT introduce new Compose services without explaining why and getting
  user approval.

## Production Runtime

- MUST NOT change production Uvicorn/Docker CMD, pool-related defaults, CORS,
  or trusted-host behavior without explicit user request and updates to
  `docs/production-deployment.md` or related runtime docs.
- `docker-compose.prod.yml` is minimal by design; managed DB/Redis/S3 stay
  external.

## Documentation

- Docker, Compose, port, service, or env workflow changes MUST update
  `README.md` and any affected file under `docs/`.
