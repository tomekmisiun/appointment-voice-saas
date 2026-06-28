# Production Runtime Examples

This guide complements `docs/operations/deployment.md` with concrete reverse-proxy
patterns, **API process scaling examples**, and a GitHub Actions environment
checklist. It does not replace your hosting provider's runbook.

## Default API Process Model

The production Docker image (`Dockerfile` production target) intentionally starts
**single-process Uvicorn** with `--proxy-headers`:

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

This default is deliberate:

- **Horizontal scaling** — run multiple API replicas behind a load balancer; each
  replica uses one process and a sized DB pool (see pool formula in
  `docs/operations/deployment.md`).
- **Operator choice** — forks pick in-process workers (Uvicorn or Gunicorn) or
  replica count without the template forcing one model in the image.
- **Worker separation** — background jobs stay in the `worker` service, not in
  API worker processes.

**Production expectation:** treat the Dockerfile `CMD` as a safe baseline. Override
the command when your sizing guide or load tests require multi-process Uvicorn or
Gunicorn on a single host.

Restrict `--forwarded-allow-ips` to your proxy subnet in real deployments
(Uvicorn defaults can trust all forwarded headers when `--proxy-headers` is set).

## Uvicorn and Gunicorn Examples

### Single-process Uvicorn (image default)

Use as-is for small deployments, staging, or when you scale by **replica count**
instead of in-process workers:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
```

Docker Compose (same as image default — no override required):

```yaml
services:
  api:
    image: ${API_IMAGE}
    env_file:
      - .env
    ports:
      - "8000:8000"
```

### Multi-worker Uvicorn (single host)

When one VM runs one API container but needs multiple CPU-bound workers **inside**
that container:

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --proxy-headers
```

Docker Compose override (`docker-compose.prod.yml` or a host-specific override file):

```yaml
services:
  api:
    image: ${API_IMAGE}
    env_file:
      - .env
    command:
      - uvicorn
      - app.main:app
      - --host
      - 0.0.0.0
      - --port
      - "8000"
      - --workers
      - "2"
      - --proxy-headers
    ports:
      - "8000:8000"
```

Before raising `--workers`, confirm Postgres `max_connections` can absorb
`workers × (DB_POOL_SIZE + DB_MAX_OVERFLOW)` per replica. The API logs effective
pool settings at startup (`app/db/pool_config.py`).

### Gunicorn with Uvicorn workers

Use Gunicorn when you want a mature parent process manager (graceful reload,
worker lifecycle) in front of Uvicorn workers. Install `gunicorn` in your fork
if not already present in the image.

```bash
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120 \
  --graceful-timeout 30 \
  --keep-alive 5
```

Docker Compose command override:

```yaml
services:
  api:
    image: ${API_IMAGE}
    env_file:
      - .env
    command:
      - gunicorn
      - app.main:app
      - -k
      - uvicorn.workers.UvicornWorker
      - --bind
      - 0.0.0.0:8000
      - --workers
      - "2"
      - --timeout
      - "120"
      - --graceful-timeout
      - "30"
      - --keep-alive
      - "5"
    ports:
      - "8000:8000"
```

Pass Uvicorn proxy settings through Gunicorn when behind a reverse proxy, for
example:

```yaml
command:
  - gunicorn
  - app.main:app
  - -k
  - uvicorn.workers.UvicornWorker
  - --bind
  - 0.0.0.0:8000
  - --workers
  - "2"
  - --timeout
  - "120"
  - --env
  - FORWARDED_ALLOW_IPS=10.0.0.0/8
  - --env
  - PROXY_HEADERS=true
```

Adjust env names and values to match your Uvicorn/Gunicorn version and network
layout.

### Multiple API replicas (recommended at scale)

Prefer **replicas + single-process Uvicorn** over very large in-process worker
counts when load is mixed (I/O + CPU):

```yaml
services:
  api:
    image: ${API_IMAGE}
    env_file:
      - .env
    deploy:
      replicas: 2
    ports:
      - "8000:8000"
```

On a single VM without Swarm/Kubernetes, run two Compose services or systemd units
with different host ports and load-balance in Nginx/Traefik.

See also `docs/architecture/scaling.md` for load-test profiles and sizing notes.

## What `docker-compose.prod.yml` Is

`docker-compose.prod.yml` is a **minimal VM-style runtime manifest** for promoted
API and worker containers. It is intentionally small:

- runs `api` and `worker` from the same promoted `API_IMAGE`
- loads environment from a production `.env` on the host
- exposes `8000` on the host for simple VM deployments

It does **not** include:

- PostgreSQL, Redis, MinIO, or other managed dependencies
- TLS termination or a reverse proxy
- observability sidecars
- database migration execution

Use external managed services for PostgreSQL, Redis, and object storage. Run
Alembic migrations through the GitHub Actions deploy workflow, a release job, or
your own migration process before or during promotion.

Typical remote layout for SSH deployments:

```text
/opt/my-api/
├── docker-compose.prod.yml
├── .env
└── (optional) reverse-proxy config managed separately
```

Promotion through `scripts/deploy_promote.sh` sets `API_IMAGE` and runs:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Recommended Runtime Shape

```text
Internet
   │
   ▼
Reverse proxy / load balancer (TLS termination)
   │
   ├──► API replicas (Uvicorn, port 8000)
   │
   └──► Worker replicas (Redis queue consumer)

External managed services:
- PostgreSQL
- Redis
- S3-compatible object storage
- SMTP provider
```

Health checks:

- liveness: `GET /health/live`
- readiness: `GET /health/ready`
- metrics (if scraped internally): `GET /metrics`

Configure the proxy to route public API traffic to the FastAPI service. Keep
worker containers off the public internet.

## Application Settings Behind A Proxy

When TLS terminates at the proxy, align these settings with your public hostname:

```env
ENVIRONMENT=production
TRUSTED_HOSTS_ENABLED=true
TRUSTED_HOSTS=api.example.com
HSTS_ENABLED=true
CORS_ENABLED=true
CORS_ALLOW_ORIGINS=https://app.example.com
```

The production Docker image starts Uvicorn with `--proxy-headers`. Restrict
`--forwarded-allow-ips` to your proxy or load balancer subnet in real
deployments instead of trusting all forwarded headers.

## Nginx Example

Minimal TLS reverse proxy in front of the Compose `api` service:

```nginx
upstream fpf_api {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/ssl/certs/api.example.com.fullchain.pem;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;

    client_max_body_size 10m;

    location / {
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_pass http://fpf_api;
    }

    location = /health/live {
        proxy_pass http://fpf_api/health/live;
        access_log off;
    }

    location = /health/ready {
        proxy_pass http://fpf_api/health/ready;
        access_log off;
    }
}
```

Notes:

- bind `docker-compose.prod.yml` to `127.0.0.1:8000:8000` when Nginx runs on
  the same host
- terminate TLS only at Nginx unless you operate end-to-end TLS inside the
  cluster
- tune `client_max_body_size` for your upload limits

## Caddy Example

Caddy handles TLS automatically when public DNS points at the host:

```caddyfile
api.example.com {
    encode gzip zstd

    reverse_proxy 127.0.0.1:8000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

Run Caddy on the host or as a separate container attached to the same Docker
network as `api`.

## Traefik Example (Docker Labels)

When Traefik and the API share a Docker network, route by hostname with labels
on the `api` service:

```yaml
services:
  api:
    image: ${API_IMAGE}
    env_file:
      - .env
    labels:
      - traefik.enable=true
      - traefik.http.routers.fpf-api.rule=Host(`api.example.com`)
      - traefik.http.routers.fpf-api.entrypoints=websecure
      - traefik.http.routers.fpf-api.tls.certresolver=letsencrypt
      - traefik.http.services.fpf-api.loadbalancer.server.port=8000
    networks:
      - edge

networks:
  edge:
    external: true
```

Do not publish `8000` on the host when Traefik is the only public entrypoint.

## GitHub Environments Checklist

Configure two GitHub environments in the repository settings:

- `staging`
- `production`

The manual `Deploy` workflow uses `environment: ${{ inputs.environment }}`, so
each environment can define its own secrets, variables, and protection rules.

### Required Decisions

| Item | Staging | Production |
|------|---------|------------|
| Public API hostname | `api.staging.example.com` | `api.example.com` |
| Deploy backend | hook, SSH, or dry-run only | hook, SSH, or dry-run only |
| Image tag policy | release tag or SHA | immutable release tag or SHA |
| `ALLOW_LATEST_PRODUCTION` | usually unset / `false` | keep `false` unless explicitly approved |
| Database | staging PostgreSQL | production PostgreSQL |
| Redis | staging Redis | production Redis |
| Object storage | staging bucket | production bucket |
| SMTP | staging-safe sender | production sender |

### Environment Variables (`vars`)

| Variable | Used for | Staging | Production |
|----------|----------|---------|------------|
| `API_BASE_URL` | post-deploy smoke checks | `https://api.staging.example.com` | `https://api.example.com` |
| `REMOTE_APP_DIR` | SSH compose path | `/opt/my-api-staging` | `/opt/my-api` |
| `SMOKE_ADMIN_EMAIL` | smoke login account | staging admin email | production admin email |
| `ALLOW_LATEST_PRODUCTION` | block `latest` tag | optional | keep `false` |

### Environment Secrets (`secrets`)

| Secret | Used for | Notes |
|--------|----------|-------|
| `DEPLOY_HOOK_URL` | hook-based promotion | optional if using SSH only |
| `DEPLOY_HOOK_TOKEN` | authenticated hook calls | optional if hook has other auth |
| `DEPLOY_SSH_HOST` | SSH promotion target | optional if using hook only |
| `DEPLOY_SSH_USER` | SSH user | required with SSH host |
| `DEPLOY_SSH_PRIVATE_KEY` | SSH auth | required with SSH host |
| `DATABASE_URL` | runner-side Alembic migrations | optional; skip if migrations run elsewhere |
| `SMOKE_ADMIN_PASSWORD` | smoke login password | required when smoke checks run |

### Recommended Protection Rules

Production environment:

- require reviewer approval before deploy
- restrict deployment branches to release tags or protected `main`
- store production secrets only in the `production` environment
- run `dry_run=true` first for every new image tag

Staging environment:

- allow faster promotion for integration testing
- use separate database, Redis, bucket, and SMTP credentials from production
- keep `ENVIRONMENT=staging` in the remote `.env`

### Promotion Smoke Sequence

1. Tag and publish an image with `release.yml`.
2. Run `Deploy` with `dry_run=true`.
3. Run `Deploy` with `dry_run=false`, migrations enabled, smoke checks enabled.
4. Confirm:
   - `GET ${API_BASE_URL}/health/ready` returns `200`
   - authenticated smoke login succeeds
   - worker logs show Redis connectivity
   - uploads work if the feature is enabled

## Related Documents

- `docs/operations/deployment.md` — deployment model and env validation
- `docs/security/secret-management.md` — secret inventory and rotation
- `docs/operations/configuration.md` — environment and runtime configuration
- `docs/operations/observability.md` — metrics and logging in production
