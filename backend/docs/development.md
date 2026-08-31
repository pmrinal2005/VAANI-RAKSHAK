# VAANI-RAKSHAK — Backend Development Guide

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required |
| pip / uv | latest | `pip install uv` for faster installs |
| Docker Desktop | 4.x+ | For Compose |
| Docker Compose | V2 | Bundled with Docker Desktop |

---

## Quick Start (Local)

```bash
# 1. Clone and enter backend directory
cd backend

# 2. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install development dependencies
pip install -e ".[dev]"

# 4. Copy environment template
cp .env.example .env
# Edit .env if needed (defaults work for local development)

# 5. Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Verify
curl http://localhost:8000/api/v1/health/live
# → {"status": "alive"}
```

---

## Running Tests

```bash
cd backend

# All tests with coverage
python -m pytest

# Specific test file
python -m pytest tests/unit/test_health.py -v

# Skip coverage (faster)
python -m pytest --no-cov -v
```

---

## Linting & Type Checking

```bash
cd backend

# Ruff (linting + formatting check)
ruff check app/ tests/
ruff format --check app/ tests/

# Auto-fix ruff issues
ruff check --fix app/ tests/
ruff format app/ tests/

# mypy (static type checking)
mypy app/
```

---

## Docker Compose (Full Stack)

```bash
cd backend

# Start all services (FastAPI + Kafka + Zookeeper + Kafka UI)
docker compose up -d

# View logs
docker compose logs -f vaani-api

# Health check
curl http://localhost:8000/api/v1/health

# Kafka UI (topic browser)
# Open http://localhost:8080

# Stop everything
docker compose down

# Stop and remove volumes
docker compose down -v
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── core/
│   │   ├── config.py        # Pydantic Settings v2
│   │   ├── logging.py       # structlog configuration
│   │   ├── exceptions.py    # Exception hierarchy
│   │   └── lifecycle.py     # Startup/shutdown hooks
│   ├── api/
│   │   ├── dependencies.py  # DI providers
│   │   └── routes/
│   │       └── health.py    # Health check endpoints
│   ├── detection/           # Phase 1 — detector protocols + mocks
│   ├── fusion/              # Phase 4 — fusion engine
│   ├── orchestration/       # Phase 3 — cascade
│   ├── messaging/           # Phase 2 — Kafka
│   ├── services/            # Phase 3+ — application services
│   ├── schemas/             # Phase 1 — Pydantic schemas
│   ├── domain/              # Phase 1 — domain models
│   └── integrations/        # Phase 7/8 — telephony, audit
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## Environment Variables

See [`.env.example`](.env.example) for a full reference with comments.

Key variables:

| Variable | Default | Description |
|---|---|---|
| `DETECTION_MODE` | `mock` | `mock` or `onnx` (Phase 1+) |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker |
| `RISK_LOW_MAX` | `29` | Risk score threshold |
| `AUDIT_MODE` | `mock` | `mock` or `fabric` (Phase 8+) |

---

## API Documentation

When running locally:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

---

## Health Endpoints

| Endpoint | Purpose | Returns |
|---|---|---|
| `GET /api/v1/health` | Aggregated health with components | `{status, version, components}` |
| `GET /api/v1/health/live` | Kubernetes liveness probe | `{status: "alive"}` |
| `GET /api/v1/health/ready` | Kubernetes readiness probe | `{status: "ready"\|"not_ready"}` |

---

## Architecture Principles

1. **Never hardcode** — all config via environment variables
2. **Mock ≠ real** — mocks are labeled, never presented as production ML
3. **No score=0 on failure** — model failure → explicit `UNCERTAIN` state
4. **Sensitive data** — raw audio, credentials, PII never in logs
5. **Idempotency** — all endpoints safe to retry
6. **Async-first** — all I/O uses `async/await`

---

## Phase Status

See [`docs/r2-progress.md`](r2-progress.md) for the full phase checklist.
