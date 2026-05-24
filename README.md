# Real-Time Analytics & Reporting Platform

Production-grade multi-tenant analytics SaaS: event ingestion, customizable dashboards, threshold alerts, and real-time updates.

## Live Demo

| Service | URL |
|---------|-----|
| **Web app** | [https://real-time-analytics-reporting-platf.vercel.app](https://real-time-analytics-reporting-platf.vercel.app/login) |
| **API** | [https://analytics-api-6xzy.onrender.com](https://analytics-api-6xzy.onrender.com) |
| **API docs (Swagger)** | [https://analytics-api-6xzy.onrender.com/docs](https://analytics-api-6xzy.onrender.com/docs) |

### Try it in ~3 minutes

1. Open the [web app](https://real-time-analytics-reporting-platf.vercel.app/signup) and **sign up** (creates your user + organization).
2. Go to **API Keys**, create a key, and copy it (shown once).
3. Ingest an event (replace `ak_YOUR_KEY`):

```bash
curl -X POST https://analytics-api-6xzy.onrender.com/api/v1/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ak_YOUR_KEY" \
  -d '{"event_name":"page_view","properties":{"page":"/home"}}'
```

4. Open **Dashboards** → create a dashboard → add a **line** or **KPI** widget for `page_view` → metrics appear after the ingest worker processes the queue (usually within a few seconds).
5. Optional: open **Live Events** to see the stream update; **Alerts** to define a threshold rule.

> **Hosted on free tiers (Vercel + Render).** Services spin down after a period of inactivity. The first visit after idle may take **up to a minute** while instances wake up—especially the API and background worker on Render. If a request times out, wait a moment and retry; subsequent requests are typically fast.

---

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Zustand, TanStack Query, Recharts |
| Backend | FastAPI, Python 3.11+, SQLAlchemy 2.0 (async), PostgreSQL, Alembic |
| Async jobs | Celery + Redis (worker + Beat on Render) |
| Real-time | WebSockets + Redis Pub/Sub |
| Auth | JWT access token + HTTP-only refresh cookie, bcrypt |
| Hosting | [Vercel](https://real-time-analytics-reporting-platf.vercel.app) (frontend), [Render](https://analytics-api-6xzy.onrender.com) (API, worker, Postgres, Redis) |

---

## Architecture

```
Routers → Services → Repositories → Models
         ↘ Schemas (Pydantic v2 I/O)
```

- **Multi-tenancy** — Organization-scoped data; roles: Owner → Admin → Analyst → Viewer
- **Ingestion** — Validate (Pydantic) → Redis queue → Celery worker → PostgreSQL → Redis pub/sub → WebSocket clients
- **Dashboards** — Widgets (line, bar, pie, KPI) backed by saved queries and configurable time ranges
- **Alerts** — Threshold rules evaluated on a schedule (Celery Beat); in-app + webhook notifications

---

## Project structure

```
├── Backend/
│   ├── app/
│   │   ├── api/v1/       # HTTP routers
│   │   ├── core/         # Config, security, deps, permissions
│   │   ├── db/           # SQLAlchemy session
│   │   ├── models/       # ORM models
│   │   ├── repositories/ # Data access
│   │   ├── schemas/      # Pydantic v2
│   │   ├── services/     # Business logic
│   │   ├── tasks/        # Celery workers & Beat schedule
│   │   ├── websocket/    # WS manager & routes
│   │   └── middleware/   # Correlation IDs
│   └── alembic/          # Migrations
└── Frontend/             # Next.js App Router
```

---

## Features implemented

| Module | Highlights |
|--------|------------|
| **Auth & orgs** | Sign up/in, JWT + refresh cookie, invites, role-based API guards, org data isolation |
| **Ingestion** | Single/batch events, CSV upload, API keys (rotate/revoke), per-org & per-key rate limits |
| **Dashboards** | CRUD, widgets, metrics API, public share links, auto-refresh (30s / 1m / 5m) |
| **Alerts** | Threshold rules, mute/snooze, incident history, in-app + Slack-compatible webhooks |
| **Real-time** | WebSocket live updates, event stream viewer, reconnect on the client |

---

## API overview

Base URL (production): `https://analytics-api-6xzy.onrender.com`

### Auth

- `POST /api/v1/auth/signup` — Create user + organization
- `POST /api/v1/auth/login` — Access token + refresh cookie
- `POST /api/v1/auth/refresh` — Rotate tokens (cookie)
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Organizations

- `GET /api/v1/organizations/current`
- `GET /api/v1/organizations/members`
- `POST /api/v1/organizations/invitations`
- `POST /api/v1/organizations/invitations/accept`

### Events (API key: `X-API-Key: ak_...`)

- `POST /api/v1/events` — Single event (202)
- `POST /api/v1/events/batch` — Up to 1000 events (202)
- `POST /api/v1/events/upload` — CSV (JWT, Analyst+)
- `GET /api/v1/events/stream` — Recent events (JWT, live viewer)

### Dashboards (JWT: `Authorization: Bearer <token>`)

Optional header: `X-Organization-ID: <uuid>`

- CRUD `/api/v1/dashboards`
- Widgets `/api/v1/dashboards/{id}/widgets`
- Metrics `/api/v1/dashboards/widgets/{id}/metrics`
- Public read `/api/v1/dashboards/public/{share_token}`

### Alerts & notifications

- CRUD `/api/v1/alerts`, mute/unmute, `/api/v1/alerts/{id}/history`
- `/api/v1/notifications` — In-app notifications

### WebSocket (production)

```
wss://analytics-api-6xzy.onrender.com/ws?token=<access_token>&org_id=<uuid>
```

### Health

- `GET /api/v1/health` — API, database, Redis, ingest queue depth

---

## Roles & permissions

| Action | Min role |
|--------|----------|
| View dashboards, events stream | Viewer |
| Create widgets, CSV upload, manage alerts | Analyst |
| API keys, invites | Admin |
| Full org control | Owner |

---

## Deployment

### Frontend (Vercel)

- Root directory: `Frontend`
- Environment variables:
  - `NEXT_PUBLIC_API_URL=https://analytics-api-6xzy.onrender.com`
  - `NEXT_PUBLIC_APP_URL=https://real-time-analytics-reporting-platf.vercel.app`

### Backend (Render)

- **Web service** — `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Background worker** — `Backend/start_worker.sh` (Celery worker + Beat)
- **PostgreSQL** + **Redis** — linked via `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

Production backend env (important):

```env
FRONTEND_URL=https://real-time-analytics-reporting-platf.vercel.app
CORS_ORIGINS=https://real-time-analytics-reporting-platf.vercel.app
COOKIE_SECURE=true
COOKIE_SAMESITE=none
JWT_SECRET_KEY=<strong-secret>
```

Run migrations on deploy: `alembic upgrade head`

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Async PostgreSQL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Cache, rate limits, pub/sub |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Celery |
| `JWT_SECRET_KEY` | Token signing (32+ chars in production) |
| `CORS_ORIGINS` | Frontend origin(s), comma-separated |
| `FRONTEND_URL` | Share & invite links |
| `INGEST_RATE_LIMIT_PER_MINUTE` | Per-org ingest cap |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | Cross-origin refresh cookie (Vercel + Render) |

See `Backend/.env.example` and `Frontend/.env.example` for the full list.

---

## Tests

Backend uses **pytest** + **httpx** (async API tests) + **fakeredis** (no real Redis needed for most tests).

```bash
cd Backend
pip install -r requirements-dev.txt
python -m pytest -v
```

**Unit tests** (permissions, CSV parsing) run with no database.

**Integration tests** need PostgreSQL — set `TEST_DATABASE_URL`, then run the full suite:

```bash
set TEST_DATABASE_URL=postgresql+asyncpg://analytics:analytics@localhost:5432/analytics_test
python -m pytest -v
```

CI runs integration tests on push via GitHub Actions (`.github/workflows/backend-tests.yml`).
