# Real-Time Analytics & Reporting Platform

Production-grade multi-tenant analytics SaaS with event ingestion, dashboards, and real-time updates.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, TypeScript, TailwindCSS, Shadcn-style UI, Zustand, TanStack Query, Recharts |
| Backend | FastAPI, Python 3.11+, SQLAlchemy 2.0 async, PostgreSQL, Alembic |
| Async | Celery, Celery Beat, Redis |
| Real-time | WebSockets, Redis Pub/Sub |
| Auth | JWT access tokens + HTTP-only refresh cookies, bcrypt |

## Architecture

```
Routers → Services → Repositories → Models
         ↘ Schemas (Pydantic I/O)
```

- **Multi-tenancy**: Organization-scoped data with role hierarchy (Owner > Admin > Analyst > Viewer)
- **Ingestion**: Validate → Redis queue → Celery worker → PostgreSQL
- **Dashboards**: Widgets (line, bar, pie, KPI) with time-range queries
- **WebSockets**: Live event notifications per organization

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # HTTP routers
│   │   ├── core/            # Config, security, deps, permissions
│   │   ├── db/              # SQLAlchemy base & session
│   │   ├── models/          # ORM models
│   │   ├── repositories/    # Data access
│   │   ├── schemas/         # Pydantic v2
│   │   ├── services/        # Business logic
│   │   ├── tasks/           # Celery workers
│   │   ├── websocket/       # WS manager & routes
│   │   ├── middleware/      # Correlation IDs
│   │   └── utils/           # Response wrapper, pagination, rate limits
│   └── alembic/             # Migrations
├── frontend/                # Next.js App Router
└── docker-compose.yml
```

## Quick Start (Docker)

### Prerequisites

- Docker & Docker Compose
- (Optional) Node 20+ and Python 3.11+ for local dev without Docker

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

For Docker, update `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://analytics:analytics@postgres:5432/analytics
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CORS_ORIGINS=http://localhost:3000
JWT_SECRET_KEY=your-long-random-secret-here
```

### 2. Start services

```bash
docker compose up --build
```

### 3. Run migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. Access

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Start PostgreSQL and Redis locally, update DATABASE_URL / REDIS_URL

alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Separate terminals:
celery -A app.tasks.celery_app worker --loglevel=info
celery -A app.tasks.celery_app beat --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## API Overview

### Auth
- `POST /api/v1/auth/signup` — Create user + organization
- `POST /api/v1/auth/login` — Returns access token, sets refresh cookie
- `POST /api/v1/auth/refresh` — Rotate tokens (cookie)
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Organizations
- `GET /api/v1/organizations/current`
- `GET /api/v1/organizations/members`
- `POST /api/v1/organizations/invitations`
- `POST /api/v1/organizations/invitations/accept`

### Events (API key)
- `POST /api/v1/events` — Single event (202)
- `POST /api/v1/events/batch` — Up to 1000 events (202)
- `POST /api/v1/events/upload` — CSV (JWT, Analyst+)

Header: `X-API-Key: ak_...`

### Dashboards (JWT)
Header: `Authorization: Bearer <token>`  
Header: `X-Organization-ID: <uuid>` (optional if embedded in token)

- CRUD `/api/v1/dashboards`
- Widgets `/api/v1/dashboards/{id}/widgets`
- Metrics `/api/v1/dashboards/widgets/{id}/metrics`
- Public `/api/v1/dashboards/public/{share_token}`

### WebSocket

```
ws://localhost:8000/ws?token=<access_token>&org_id=<uuid>
```

## Example: Ingest Events

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ak_YOUR_KEY" \
  -d '{"event_name":"page_view","properties":{"page":"/home"}}'
```

## Roles & Permissions

| Action | Min Role |
|--------|----------|
| View dashboards | Viewer |
| Create widgets / CSV upload | Analyst |
| API keys, invites, delete dashboards | Admin |
| Full org control | Owner |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis for cache, rate limits, pub/sub |
| `CELERY_BROKER_URL` | Celery message broker |
| `CELERY_RESULT_BACKEND` | Celery result store |
| `JWT_SECRET_KEY` | Signing secret (32+ chars in production) |
| `CORS_ORIGINS` | Comma-separated frontend origins |
| `INGEST_RATE_LIMIT_PER_MINUTE` | Per-org ingest cap |

## Production Checklist

- [ ] Rotate `JWT_SECRET_KEY` and use secrets manager
- [ ] Set `CORS_ORIGINS` to your frontend URL (e.g. Vercel)
- [ ] For cross-origin SPA: `COOKIE_SECURE=true` and `COOKIE_SAMESITE=none` (refresh cookie)
- [ ] Partition `events` table by month (see model TODO)
- [ ] Add email provider for invitations
- [ ] Configure OpenTelemetry / structured log aggregation
- [ ] Horizontal scaling: multiple API instances + Redis pub/sub (included)

## TODO (Scalability)

- Monthly partitions on `events` table
- Materialized views for hot dashboard queries
- Idempotency keys on ingest
- Row-level security in PostgreSQL
- Audit log for admin actions

## License

MIT
