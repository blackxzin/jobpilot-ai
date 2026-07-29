# ============================================================
# JobPilot AI — Backend Dockerfile
# Multi-stage build for production
# ============================================================

# ── Dependencies ────────────────────────────────────────────
FROM python:3.12-slim AS deps

WORKDIR /app

# System deps required by psycopg2 and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ── Development Stage ───────────────────────────────────────
FROM python:3.12-slim AS development

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy source
COPY src /app/src
COPY alembic /app/alembic
COPY pyproject.toml /app/pyproject.toml

# Install dev dependencies
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --no-cache-dir -r /tmp/requirements-dev.txt

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "info"]

# ── Production Stage ────────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY src /app/src
COPY alembic /app/alembic
COPY pyproject.toml /app/pyproject.toml

# Create non-root user
RUN groupadd -r jobpilot && useradd -r -g jobpilot -d /app -s /sbin/nologin jobpilot && \
    mkdir -p /app/logs && chown -R jobpilot:jobpilot /app

USER jobpilot

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "warning"]
