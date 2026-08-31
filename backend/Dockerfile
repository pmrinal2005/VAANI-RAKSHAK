# ==============================================================================
# VAANI-RAKSHAK Backend — Dockerfile
# Multi-stage build: builder → runtime
# ==============================================================================

# ----------------------------------------------------------
# Stage 1: builder — install dependencies into a virtual env
# ----------------------------------------------------------
FROM python:3.11-slim AS builder

# System deps for numpy/scipy compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy dependency manifest first — layer cache benefits
COPY pyproject.toml ./

# Install pip tools
RUN pip install --no-cache-dir --upgrade pip hatch

# Install project dependencies (no dev extras in production image)
RUN pip install --no-cache-dir ".[ml]" 2>/dev/null || \
    pip install --no-cache-dir .

# ----------------------------------------------------------
# Stage 2: runtime — minimal image
# ----------------------------------------------------------
FROM python:3.11-slim AS runtime

# Non-root user for security
RUN useradd --create-home --shell /bin/bash vaani

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY --chown=vaani:vaani app/ ./app/

# Switch to non-root user
USER vaani

# Environment defaults (override via docker-compose or K8s config)
ENV APP_ENV=production \
    LOG_JSON=true \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

# Health check using the liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/live')" \
    || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "warning", \
     "--no-access-log"]
