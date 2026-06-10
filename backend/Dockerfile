# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System libraries required by PyMuPDF wheels on linux/amd64
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libglib2.0-0 \
    libgomp1 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: production runtime ───────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Minimal runtime libs for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user — Cloud Run security best practice
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application source
COPY src/      ./src/
COPY corpus/   ./corpus/

# Firebase service account (mounted as secret in Cloud Run, copied here for local runs)
# In production this file is provided via Secret Manager → mounted volume
RUN mkdir -p /app/secrets && chown appuser:appgroup /app/secrets

# Set ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Ensure pip-installed scripts are on PATH
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# Cloud Run sends traffic on 8080 (not 8000)
CMD ["uvicorn", "src.api.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8080", \
    "--workers", "1", \
    "--loop", "uvloop", \
    "--http", "httptools", \
    "--log-level", "info"]

# Health check — Cloud Run polls this before marking instance healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
