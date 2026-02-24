# 07 — Deployment & Infrastructure

---

## Production stack overview

| Service | Provider | Purpose |
|---------|----------|---------|
| API (web dyno) | Heroku Container Registry | FastAPI + Uvicorn |
| Worker dyno | Heroku Container Registry | Celery email worker |
| PostgreSQL | NeonDB (serverless) | Primary database |
| Redis | Upstash (serverless) | Availability cache + metrics |
| Message broker | CloudAMQP (RabbitMQ) | Celery task queue |
| Email | Resend API | Booking confirmations |
| Frontend | Vercel | Next.js 15 |

All services are on free/low-cost tiers. Total infra cost ≈ $5/month (Heroku Eco dynos).

---

## Local development stack (Docker Compose)

The full stack runs locally with one command:
```bash
docker-compose up
```

7 services defined in `docker-compose.yml`:

| Service | Image | Port |
|---------|-------|------|
| `db` | postgres:15-alpine | 5434 → 5432 |
| `test_db` | postgres:15-alpine | 5433 → 5432 |
| `redis` | redis:7-alpine | 6380 → 6379 |
| `rabbitmq` | rabbitmq:3.13-management | 5672, 15672 |
| `mailpit` | axllent/mailpit | 8025 (UI), 1025 (SMTP) |
| `backend` | (built from Dockerfile) | 8000 |
| `notification_worker` | (built from Dockerfile) | — |

`test_db` is a separate PostgreSQL instance so concurrency tests don't pollute development data. The host port for `db` is `5434` (not 5432) to avoid conflicts with any locally installed PostgreSQL.

Service dependencies in Compose:
- `backend` waits for `redis` (healthcheck) and `rabbitmq` (healthcheck) before starting
- `notification_worker` waits for `rabbitmq` (healthcheck)

---

## Docker: two images, same codebase

### `Dockerfile` (web)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

`$PORT` is shell-expanded at runtime — Heroku injects this env var dynamically (it's not always 8000). The CMD is in **shell form** (not exec form) specifically so `$PORT` gets expanded.

### `Dockerfile.worker`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
CMD ["celery", "-A", "app.worker", "worker", "--loglevel=info"]
```

Identical base image, different CMD. Same codebase — the worker just runs a different process.

---

## Heroku deployment process

Heroku uses **Container Registry** (not the standard Git push buildpack). The flow:

```bash
# Step 1: Login to Heroku container registry
heroku container:login

# Step 2: Build and push web image
heroku container:push web --app scalable-booking-app
# This runs: docker build -t registry.heroku.com/scalable-booking-app/web .
# Then pushes to Heroku's registry

# Step 3: Build and push worker image manually
docker build -f Dockerfile.worker -t registry.heroku.com/scalable-booking-app/worker:latest .
docker push registry.heroku.com/scalable-booking-app/worker:latest

# Step 4: Release both
heroku container:release web worker --app scalable-booking-app
```

Heroku pulls the new images from the registry and replaces running dynos with zero downtime.

### Why Container Registry and not Git push?

Standard Heroku Git push uses buildpacks (auto-detected from requirements.txt). Container Registry gives full control over the runtime environment — exact Python version, system dependencies, separate Dockerfiles per process type. For a multi-process app (web + worker), it's the right choice.

### Heroku config vars (env vars in production)

All secrets are set as Heroku config vars:
```bash
heroku config:set DATABASE_URL=postgresql://...   --app scalable-booking-app
heroku config:set SECRET_KEY=...                  --app scalable-booking-app
heroku config:set RABBITMQ_URL=amqps://...        --app scalable-booking-app
heroku config:set REDIS_URL=rediss://...          --app scalable-booking-app
heroku config:set RESEND_API_KEY=re_...           --app scalable-booking-app
heroku config:set ENVIRONMENT=production          --app scalable-booking-app
heroku config:set RESEND_TO_OVERRIDE=...@gmail.com --app scalable-booking-app
```

None of these are in the codebase or Docker image. `Pydantic Settings` reads them from the environment at startup.

### Eco dynos — the catch

Heroku Eco dynos ($5/month flat for all Eco dynos) **sleep after 30 minutes of inactivity**. The first request after sleep wakes the dyno — cold start takes ~10–15 seconds. This is acceptable for a portfolio project but not for production. Standard dynos ($25/month) don't sleep.

---

## Database: NeonDB

NeonDB is a **serverless PostgreSQL** provider. Key properties:
- Standard PostgreSQL 15 — all SQL features, Alembic migrations work normally
- Serverless: compute scales to zero when idle (no persistent connection cost)
- Connection pooling via pgBouncer is built-in (use the `-pooler` connection string)
- Free tier: 512 MB storage, shared compute

The connection string in production uses the pooler:
```
postgresql://neondb_owner:...@ep-old-union-a1rp2g15-pooler.ap-southeast-1.aws.neon.tech/bookingdb?sslmode=require
```

### Alembic migrations

Database schema is version-controlled with Alembic:
```bash
# Generate a new migration
alembic revision --autogenerate -m "description"

# Apply migrations to production
alembic upgrade head
```

Migration files live in `alembic/versions/`. Two migrations exist:
1. `902bb8897c35_initial_database_schema.py` — full initial schema
2. `c2559617e066_add_organizer_id_to_event_table.py` — added organizer FK

---

## Redis: Upstash

Upstash is a **serverless Redis** provider. Key properties:
- REST API and standard Redis protocol both supported
- Free tier: 10,000 commands/day, 256 MB
- Per-request billing (no idle cost)
- TLS required: connection string uses `rediss://` (note double `s`)

Used for:
1. Availability cache (key: `availability:{event_id}`, TTL 300s)
2. Metrics counters (`metrics:cache_hits`, `metrics:cache_misses`, etc.)

---

## Message broker: CloudAMQP

CloudAMQP hosts managed RabbitMQ. Free tier ("Little Lemur"):
- 1 million messages/month
- 20 connections
- Sufficient for portfolio/demo use

Connection string: `amqps://...@...cloudamqp.com/...` — note `amqps://` (TLS).

---

## Frontend: Vercel

```bash
vercel --prod --yes
```

- Next.js 15 App Router
- Static pages pre-rendered at build time, dynamic routes SSR
- Automatic HTTPS, global CDN
- Deploys from GitHub main branch automatically on push

The backend allows all `*.vercel.app` origins via `allow_origin_regex` in CORS config — this covers Vercel's unique preview deploy URLs.

---

## Deploy checklist (for reference)

When making backend changes:
```bash
cd backend
git add -A && git commit -m "..."
heroku container:push web --app scalable-booking-app
docker build -f Dockerfile.worker -t registry.heroku.com/scalable-booking-app/worker:latest .
docker push registry.heroku.com/scalable-booking-app/worker:latest
heroku container:release web worker --app scalable-booking-app
git push origin main
```

When making frontend changes:
```bash
cd frontend
npm run build   # verify passes locally
git add -A && git commit -m "..."
git push origin main
vercel --prod --yes
```

---

## Interview one-liner

> "The backend runs as two separate Heroku Container Registry dynos — a web dyno for FastAPI and a worker dyno for Celery — both built from separate Dockerfiles from the same codebase. PostgreSQL is on NeonDB serverless, Redis on Upstash, and RabbitMQ on CloudAMQP. The frontend is Next.js 15 on Vercel. Locally I run the full 7-service stack with Docker Compose including a separate test database so concurrency tests use real commits without polluting dev data."
