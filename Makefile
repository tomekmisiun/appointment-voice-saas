install:
	uv sync

API_BASE_URL ?= http://localhost:8000
DEV_ADMIN_EMAIL ?= admin@example.local
DEV_PASSWORD ?= devpassword123

BACKUP_DIR ?= backups
BACKUP_FILE ?= $(BACKUP_DIR)/app_db.dump
DB_NAME ?= app_db
DB_SERVICE ?= db
DB_USER ?= app_user
RESTORE_CHECK_DB ?= app_restore_check

run:
	uv run uvicorn app.main:app --reload

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

test:
	docker compose exec api pytest -v

test-coverage:
	docker compose run --rm api pytest \
		--cov=app \
		--cov-report=term-missing \
		--cov-fail-under=85 \
		-v

lint:
	docker compose exec api ruff check .

lint-fix:
	docker compose exec api ruff check . --fix

migration-current:
	docker compose run --rm api alembic current

migration-heads:
	docker compose run --rm api alembic heads

migration-upgrade:
	docker compose run --rm api alembic upgrade head

db-backup:
	bash scripts/db_backup.sh

db-restore-check:
	bash scripts/db_restore_rehearsal.sh

db-backup-dry-run:
	DRY_RUN=true bash scripts/db_backup.sh

db-restore-check-dry-run:
	DRY_RUN=true bash scripts/db_restore_rehearsal.sh

seed-tenant:
	docker compose run --rm api python -m app.seed_default_tenant

seed:
	docker compose run --rm api python -m app.seed_dev_data

smoke:
	API_BASE_URL=$(API_BASE_URL) DEV_ADMIN_EMAIL=$(DEV_ADMIN_EMAIL) DEV_PASSWORD=$(DEV_PASSWORD) ./scripts/smoke_test.sh

ENVIRONMENT ?= staging
IMAGE_TAG ?= latest

deploy-dry-run:
	ENVIRONMENT=$(ENVIRONMENT) IMAGE_REF=ghcr.io/example/fastapi-production-foundation/api:$(IMAGE_TAG) DRY_RUN=true RUN_MIGRATIONS=true bash scripts/deploy_promote.sh

COVERAGE_FAIL_UNDER ?= 85

validate:
	docker compose run --rm api ruff check .
	docker compose run --rm api pytest \
		--cov=app \
		--cov-report=term-missing \
		--cov-fail-under=$(COVERAGE_FAIL_UNDER) \
		-v

policy-guards:
	bash scripts/ci/run_policy_guards.sh

validate-ai-workflows:
	bash scripts/validate-ai-workflows.sh

bootstrap: docker-up migration-upgrade seed-tenant seed smoke

LOAD_REQUESTS ?= 50
LOAD_CONCURRENCY ?= 5
LOAD_API_BASE_URL ?= http://api:8000
LOAD_MAX_P95_MS ?=
LOAD_MAX_P99_MS ?=
LOAD_MIN_THROUGHPUT_RPS ?=

load-smoke:
	docker compose run --rm api python -m perf.load_baseline \
		--base-url $(LOAD_API_BASE_URL) \
		--requests $(LOAD_REQUESTS) \
		--concurrency $(LOAD_CONCURRENCY)

load-smoke-ready:
	docker compose run --rm api python -m perf.load_baseline \
		--base-url $(LOAD_API_BASE_URL) \
		--path /health/ready \
		--requests $(LOAD_REQUESTS) \
		--concurrency $(LOAD_CONCURRENCY)

load-smoke-thresholds:
	docker compose run --rm api python -m perf.load_baseline \
		--base-url $(LOAD_API_BASE_URL) \
		--profile health \
		--check-thresholds \
		--requests $(LOAD_REQUESTS) \
		--concurrency $(LOAD_CONCURRENCY) \
		$(if $(LOAD_MAX_P95_MS),--max-p95-ms $(LOAD_MAX_P95_MS),) \
		$(if $(LOAD_MAX_P99_MS),--max-p99-ms $(LOAD_MAX_P99_MS),) \
		$(if $(LOAD_MIN_THROUGHPUT_RPS),--min-throughput-rps $(LOAD_MIN_THROUGHPUT_RPS),)

load-smoke-ready-thresholds:
	docker compose run --rm api python -m perf.load_baseline \
		--base-url $(LOAD_API_BASE_URL) \
		--profile health-ready \
		--check-thresholds \
		--requests $(LOAD_REQUESTS) \
		--concurrency $(LOAD_CONCURRENCY) \
		$(if $(LOAD_MAX_P95_MS),--max-p95-ms $(LOAD_MAX_P95_MS),) \
		$(if $(LOAD_MAX_P99_MS),--max-p99-ms $(LOAD_MAX_P99_MS),) \
		$(if $(LOAD_MIN_THROUGHPUT_RPS),--min-throughput-rps $(LOAD_MIN_THROUGHPUT_RPS),)

load-validate: load-smoke-thresholds load-smoke-ready-thresholds

load-smoke-auth-login:
	docker compose run --rm api python -m perf.load_baseline \
		--base-url $(LOAD_API_BASE_URL) \
		--profile auth-login \
		--requests $(LOAD_REQUESTS) \
		--concurrency $(LOAD_CONCURRENCY)

load-smoke-auth-login-thresholds:
	docker compose run --rm api python -m perf.load_baseline \
		--base-url $(LOAD_API_BASE_URL) \
		--profile auth-login \
		--check-thresholds \
		--requests 8 \
		--concurrency 2 \
		$(if $(LOAD_MAX_P95_MS),--max-p95-ms $(LOAD_MAX_P95_MS),) \
		$(if $(LOAD_MAX_P99_MS),--max-p99-ms $(LOAD_MAX_P99_MS),) \
		$(if $(LOAD_MIN_THROUGHPUT_RPS),--min-throughput-rps $(LOAD_MIN_THROUGHPUT_RPS),)

# Lighter threshold check used by CI pull-request smoke (see .github/workflows/ci.yml).
load-smoke-ci:
	docker compose run --rm api python -m perf.load_baseline \
		--base-url $(LOAD_API_BASE_URL) \
		--profile health \
		--check-thresholds \
		--requests 30 \
		--concurrency 3
