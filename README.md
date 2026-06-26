<div align="center">

# 📞 VoxSlot

### Voice-first booking automation for appointment-based businesses

VoxSlot answers missed calls, guides customers through an IVR flow, creates appointments, sends SMS notifications and keeps business operations synchronized.

<br />

[![Live Demo](https://img.shields.io/badge/LIVE_DEMO-OPEN_VOXSLOT-2ea44f?style=for-the-badge&logo=railway&logoColor=white)](https://voxslot.up.railway.app/)
[![Project Status](https://img.shields.io/badge/PROJECT_STATUS-VIEW-1f6feb?style=for-the-badge&logo=github&logoColor=white)](PROJECT_STATUS.md)
[![Roadmap](https://img.shields.io/badge/ROADMAP-VIEW-8a2be2?style=for-the-badge&logo=githubprojects&logoColor=white)](ROADMAP.md)

<br />

[![CI](https://github.com/tomekmisiun/appointment-voice-saas/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/tomekmisiun/appointment-voice-saas/actions/workflows/ci.yml)
[![Deploy](https://github.com/tomekmisiun/appointment-voice-saas/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/tomekmisiun/appointment-voice-saas/actions/workflows/deploy.yml)
[![Last commit](https://img.shields.io/github/last-commit/tomekmisiun/appointment-voice-saas?style=flat-square)](https://github.com/tomekmisiun/appointment-voice-saas/commits/main)
[![Repository size](https://img.shields.io/github/repo-size/tomekmisiun/appointment-voice-saas?style=flat-square)](https://github.com/tomekmisiun/appointment-voice-saas)
[![Open issues](https://img.shields.io/github/issues/tomekmisiun/appointment-voice-saas?style=flat-square)](https://github.com/tomekmisiun/appointment-voice-saas/issues)

<br />

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-Frontend-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Queue_%26_Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white)

![Twilio](https://img.shields.io/badge/Twilio-Voice_%26_SMS-F22F46?style=for-the-badge&logo=twilio&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containers-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-Deployment-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)

</div>

---

## Table of contents

- [About](#about)
- [Problem](#problem)
- [How it works](#how-it-works)
- [Key features](#key-features)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Quick start](#quick-start)
- [Local demo](#local-demo)
- [Testing and validation](#testing-and-validation)
- [Security and reliability](#security-and-reliability)
- [Project status](#project-status)
- [Roadmap](#roadmap)
- [Repository structure](#repository-structure)
- [Documentation](#documentation)
- [Development workflow](#development-workflow)
- [Author](#author)

---

## About

**VoxSlot** is a multi-tenant SaaS platform for salons, barbers, clinics and other appointment-based businesses that lose calls while employees are serving customers.

The system combines:

- a phone IVR,
- an appointment scheduling engine,
- SMS communication,
- calendar synchronization,
- an owner-facing web dashboard,
- production-oriented backend infrastructure.

A caller can book, cancel or reschedule an appointment without waiting for the business owner to answer the phone.

### Operating modes

| Mode | Description |
|---|---|
| **Internal booking** | VoxSlot manages services, staff availability and bookings directly. |
| **External booking link** | The caller receives an SMS link to an external booking platform such as Booksy. |

### At a glance

| Area | Current state |
|---|---|
| Backend domain and scheduling | ✅ Implemented |
| Twilio voice and SMS | ✅ Implemented |
| Calendar integration | ✅ Implemented |
| Local IVR simulation | ✅ Implemented |
| Owner authentication | ✅ Implemented |
| Owner dashboard | 🟡 Functional and expanding |
| Controlled pilot | ✅ Supported |
| Full self-service SaaS | 🟡 In progress |
| Billing and phone provisioning | 🧭 Planned |

---

## Problem

Appointment-based businesses often miss phone calls because staff cannot interrupt a service to answer the phone.

A missed call can mean:

- a lost appointment,
- repeated interruptions,
- manual follow-up,
- unnecessary administrative work,
- a poor customer experience.

VoxSlot moves the first stage of booking from the business owner to an automated voice flow while keeping the final booking data inside one operational system.

---

## How it works

```mermaid
sequenceDiagram
    participant Caller
    participant Twilio
    participant API as FastAPI / IVR
    participant DB as PostgreSQL
    participant Queue as Redis worker
    participant SMS as SMS provider
    participant Calendar as Calendar provider
    participant Owner as Next.js dashboard

    Caller->>Twilio: Calls the business number
    Twilio->>API: Sends a signed voice webhook
    API->>DB: Loads business configuration and availability
    API-->>Caller: Presents IVR options

    alt Internal booking
        Caller->>API: Selects service, staff and slot
        API->>DB: Creates the booking atomically
        API->>Queue: Enqueues notifications and calendar sync
        Queue->>SMS: Sends confirmation
        Queue->>Calendar: Creates calendar event
    else External booking link
        Caller->>API: Requests booking link
        API->>Queue: Enqueues SMS with external URL
        Queue->>SMS: Sends booking link
    end

    Owner->>API: Manages the business through the dashboard
```

### Typical caller flow

```text
Incoming call
    ↓
Business greeting
    ↓
[1] Book an appointment
[2] Connect to the business
    ↓
Choose service
    ↓
Choose preferred staff or any available employee
    ↓
Choose an available time slot
    ↓
Booking created
    ↓
SMS confirmation + calendar synchronization
```

---

## Key features

| Area | Capabilities |
|---|---|
| **📞 Voice and IVR** | Twilio voice webhooks<br>Signature verification and idempotency<br>Keypad-based navigation<br>Service, staff and slot selection<br>Booking, cancellation and rescheduling<br>Call transfer<br>External booking-link delivery<br>Local IVR simulation |
| **📅 Scheduling** | Business and staff working hours<br>Availability exceptions and closures<br>Recurring staff blocks<br>Timezone and DST handling<br>Multi-service bookings<br>Database-level overlap protection<br>Waitlist offers and escalation |
| **💬 Communication** | Transactional notification outbox<br>Twilio SMS and fake local providers<br>Confirmations, reminders and cancellations<br>Inbound SMS commands<br>Google Calendar adapter<br>Retries, backoff and reconciliation |
| **🖥️ Owner application** | Landing page<br>Registration and authentication<br>Protected dashboard<br>Business setup overview<br>Booking and staff management<br>Typed OpenAPI contract<br>Next.js Backend-for-Frontend<br>Encrypted HttpOnly session |
| **🏢 SaaS platform** | Multi-tenant data model<br>Tenant-scoped authorization<br>Business memberships<br>Role-based access control<br>Audit logging<br>Public and protected endpoint policies |
| **⚙️ Operations** | Redis queues, cache and rate limiting<br>Alembic migrations<br>MinIO / S3-compatible storage<br>Health and readiness checks<br>Prometheus metrics<br>Structured logging and Sentry<br>Docker Compose<br>CI/CD and security workflows |

---

## Architecture

```mermaid
flowchart LR
    Caller[Phone caller] --> Twilio[Twilio Voice]
    Twilio --> API[FastAPI API]

    Browser[Owner browser] --> Next[Next.js BFF]
    Next --> API

    API --> Postgres[(PostgreSQL)]
    API --> Redis[(Redis)]
    API --> Storage[(MinIO / S3)]

    Redis --> Worker[Background worker]
    Worker --> SMS[Twilio SMS]
    Worker --> Calendar[Google Calendar]
    Worker --> Postgres

    API --> Metrics[Prometheus metrics]
    Worker --> Metrics
    Metrics --> Observability[Grafana / Alertmanager]
```

### Main design decisions

| Area | Approach |
|---|---|
| **API** | Versioned FastAPI routes with thin controllers and a service layer |
| **Frontend** | Next.js App Router using a Backend-for-Frontend pattern |
| **Authentication** | Backend JWTs remain server-side inside an encrypted frontend session |
| **Persistence** | PostgreSQL with SQLAlchemy 2.0 and Alembic |
| **Concurrency** | Transactional operations and database-level overlap protection |
| **Async work** | Redis queues with delayed jobs, retries and failed-job handling |
| **Integrations** | Provider interfaces with fake and production adapters |
| **Notifications** | Transactional outbox preserves delivery intent |
| **Tenancy** | Tenant and business scope enforced throughout domain services |
| **API contract** | Frontend TypeScript types generated from backend OpenAPI |
| **Observability** | Health checks, structured logs, metrics and alerts |

---

## Technology stack

### Backend

<p>
<img src="https://img.shields.io/badge/Python_3.13-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
<img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
<img src="https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic" />
<img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy" />
<img src="https://img.shields.io/badge/Alembic-6BA81E?style=flat-square" alt="Alembic" />
</p>

### Frontend

<p>
<img src="https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js" />
<img src="https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB" alt="React" />
<img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" />
<img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS" />
<img src="https://img.shields.io/badge/TanStack_Query-FF4154?style=flat-square&logo=reactquery&logoColor=white" alt="TanStack Query" />
<img src="https://img.shields.io/badge/React_Hook_Form-EC5990?style=flat-square&logo=reacthookform&logoColor=white" alt="React Hook Form" />
<img src="https://img.shields.io/badge/Zod-3E67B1?style=flat-square&logo=zod&logoColor=white" alt="Zod" />
</p>

### Infrastructure and integrations

<p>
<img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" />
<img src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis" />
<img src="https://img.shields.io/badge/Twilio-F22F46?style=flat-square&logo=twilio&logoColor=white" alt="Twilio" />
<img src="https://img.shields.io/badge/Google_Calendar-4285F4?style=flat-square&logo=googlecalendar&logoColor=white" alt="Google Calendar" />
<img src="https://img.shields.io/badge/MinIO-C72E49?style=flat-square&logo=minio&logoColor=white" alt="MinIO" />
<img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker" />
<img src="https://img.shields.io/badge/Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white" alt="Railway" />
</p>

### Quality and observability

<p>
<img src="https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white" alt="pytest" />
<img src="https://img.shields.io/badge/Vitest-6E9F18?style=flat-square&logo=vitest&logoColor=white" alt="Vitest" />
<img src="https://img.shields.io/badge/Ruff-D7FF64?style=flat-square&logo=ruff&logoColor=black" alt="Ruff" />
<img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white" alt="GitHub Actions" />
<img src="https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white" alt="Prometheus" />
<img src="https://img.shields.io/badge/Grafana-F46800?style=flat-square&logo=grafana&logoColor=white" alt="Grafana" />
<img src="https://img.shields.io/badge/Sentry-362D59?style=flat-square&logo=sentry&logoColor=white" alt="Sentry" />
</p>

---

## Quick start

### Requirements

- Docker and Docker Compose
- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 20+
- [`pnpm`](https://pnpm.io/)
- Make

### 1. Clone and configure the repository

```bash
git clone https://github.com/tomekmisiun/appointment-voice-saas.git
cd appointment-voice-saas

cp .env.example .env
```

Set a strong development secret in `.env`:

```env
SECRET_KEY=replace-with-a-strong-random-secret
```

### 2. Start the backend stack

```bash
make bootstrap
make seed-demo
```

### 3. Configure and start the frontend

```bash
cd frontend

pnpm install
cp .env.example .env.local
openssl rand -base64 32
```

Set the generated value in `frontend/.env.local`:

```env
BACKEND_API_URL=http://localhost:8000
SESSION_SECRET=<generated-base64-secret>
APP_ORIGIN=http://localhost:3000
BFF_TRUST_FORWARDED_HEADERS=false
```

Start the frontend:

```bash
pnpm dev
```

### Local services

| Service | Address |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Readiness check | http://localhost:8000/health/ready |
| MinIO console | http://localhost:9001 |

### Local development account

```text
Email:    admin@example.local
Password: devpassword123
```

> [!WARNING]
> These credentials are intended only for local development. Never use them in a shared or production environment.

---

## Local demo

Create deterministic demo data:

```bash
make seed-demo
```

The seed creates a sample business with staff, services and working hours.

The IVR can be tested without a real Twilio phone number:

```text
POST /api/v1/ivr/simulate/call
POST /api/v1/ivr/simulate/press
```

This makes it possible to exercise the booking flow locally while using fake SMS and calendar providers.

---

## Testing and validation

### Backend

Run the main validation suite:

```bash
make validate
```

Run tests only:

```bash
make test
```

Run tests in parallel:

```bash
make test-parallel
```

### Frontend

```bash
cd frontend

pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Verify that generated frontend types match the backend OpenAPI schema:

```bash
pnpm api:check
```

---

## Security and reliability

VoxSlot includes production-oriented safeguards across the API, frontend and asynchronous workers.

| Area | Safeguard |
|---|---|
| **Frontend session** | Encrypted, HttpOnly session cookie |
| **CSRF** | Origin checks for state-changing frontend requests |
| **Authorization** | Tenant and business-level data isolation |
| **Scheduling** | Database-level booking overlap prevention |
| **Webhooks** | Twilio signature verification and idempotency |
| **Notifications** | Transactional outbox |
| **Public endpoints** | Redis-backed rate limiting |
| **Async jobs** | Retries, backoff and failed-job handling |
| **Operations** | Health checks, readiness checks and metrics |
| **Auditability** | Structured audit logs |
| **Supply chain** | Dependency review and secret scanning |
| **Recovery** | Scheduled backups and restore rehearsals |

---

## Project status

| Area | Status |
|---|---|
| Backend domain and scheduling engine | ✅ Available |
| Voice IVR and Twilio adapters | ✅ Available |
| SMS and calendar integrations | ✅ Available |
| Local end-to-end demo | ✅ Available |
| Owner registration and authentication | ✅ Available |
| Owner dashboard | 🟡 Functional, actively expanding |
| Controlled pilot deployment | ✅ Supported |
| Full self-service SaaS operations | 🟡 In progress |
| Public read-only product demo | 🟡 In progress |
| Subscription billing | 🧭 Planned |
| Automated phone provisioning | 🧭 Planned |

> [!NOTE]
> The repository is suitable as a portfolio project, complete local demo and controlled pilot. It is not yet presented as a finished, generally available commercial SaaS.

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for the evidence-backed implementation status.

---

## Roadmap

Current development areas:

- completing owner dashboard management screens,
- public read-only demo access,
- staff accounts and business permissions,
- owner metrics and CSV exports,
- payment and deposit workflows,
- subscription billing and plan enforcement,
- automated phone-number provisioning,
- deeper calendar synchronization,
- operational integration reconciliation.

More details:

- [`ROADMAP.md`](ROADMAP.md)
- [`TECH_DEBT.md`](TECH_DEBT.md)
- [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md)

---

## Repository structure

```text
.
├── app/
│   ├── api/             # FastAPI routes and dependencies
│   ├── core/            # Configuration, security, middleware and metrics
│   ├── models/          # SQLAlchemy domain models
│   ├── schemas/         # Pydantic request and response schemas
│   ├── services/        # Domain logic and provider abstractions
│   └── worker.py        # Redis background worker
│
├── frontend/
│   ├── app/             # Next.js pages and BFF endpoints
│   ├── components/      # Shared UI and marketing components
│   ├── features/        # Auth, dashboard, bookings and staff
│   ├── lib/             # API contract, session and validation
│   └── tests/           # Frontend test utilities and mocks
│
├── alembic/             # Database migrations
├── tests/               # Backend unit, integration and smoke tests
├── docs/                # Product documentation, audits and runbooks
├── observability/       # Prometheus, Grafana and alert configuration
├── perf/                # Load-test baselines
├── scripts/             # Deployment, backup, CI and operational scripts
└── .github/workflows/   # CI, deploy, backup, release and security workflows
```

---

## Documentation

| Document | Purpose |
|---|---|
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Verified implementation and readiness status |
| [`ROADMAP.md`](ROADMAP.md) | High-level product roadmap |
| [`TECH_DEBT.md`](TECH_DEBT.md) | Known gaps and technical debt |
| [`docs/product-scope.md`](docs/product-scope.md) | Product problem, users and scope |
| [`docs/domain-model.md`](docs/domain-model.md) | Domain terminology and relationships |
| [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md) | Detailed implementation backlog |
| [`docs/mvp-pilot-deployment-checklist.md`](docs/mvp-pilot-deployment-checklist.md) | Pilot deployment checklist |
| [`docs/twilio-provider-runbook.md`](docs/twilio-provider-runbook.md) | Twilio integration runbook |
| [`docs/learning/`](docs/learning/) | Codebase mental maps and learning notes |

---

## Development workflow

The repository follows these rules:

- one task per branch,
- Conventional Commits,
- targeted tests before broad validation,
- full validation before merge,
- CI policy guards,
- cross-provider AI-assisted review rules.

Read these files before making automated changes:

- [`AGENTS.md`](AGENTS.md)
- [`CLAUDE.md`](CLAUDE.md)
- [`.ai-rules/`](.ai-rules/)

---

## Author

<div align="center">

### Tomasz Misiun

[![GitHub](https://img.shields.io/badge/GitHub-tomekmisiun-181717?style=for-the-badge&logo=github)](https://github.com/tomekmisiun)
[![VoxSlot](https://img.shields.io/badge/VoxSlot-Live_application-2ea44f?style=for-the-badge&logo=railway&logoColor=white)](https://voxslot.up.railway.app/)

<br />

Built as a production-oriented portfolio project and evolving SaaS product.

</div>

---

<div align="center">

**This repository is under active development.**

No open-source license is currently included.

[Back to top](#-voxslot)

</div>
