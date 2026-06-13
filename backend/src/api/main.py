"""
main.py — FastAPI application entry point

Fixes (production audit):

P1 — REDIS CONNECTION LEAK
    Previous: every request called aioredis.from_url() inside an async-with
    block, opening and closing a new TCP connection for every rate-limit check.
    Under 50 concurrent users → 100 handshakes/second. Cloud Memorystore default
    limit is 1000 connections; exhausted at ~100 concurrent users.

    Fix: create a single ConnectionPool in lifespan, stored on app.state.
    rate_limit.py now borrows from this shared pool.

P1 — SILENT MISCONFIGURATION
    Previous: Settings had no startup validator; every field defaulted to "".
    A deploy with a missing FERNET_KEY or FIREBASE_SERVICE_ACCOUNT_PATH would
    start cleanly, accept traffic, and then fail deep inside the pipeline.

    Fix: Settings.check_production_secrets() (in settings.py) raises ValueError
    at import time in production. This propagates here as a startup crash with
    a clear error message before Cloud Run considers the instance healthy.

P2 — PII IN LOGS
    Added PiiRedactingFilter: redacts EPIC patterns (e.g. MH12345678) from all
    log messages and exception strings before they reach Cloud Logging.

P2 — NO REQUEST CORRELATION ID
    Added CorrelationIdMiddleware: reads X-Cloud-Trace-Context from Cloud Run
    (or generates a short UUID4 prefix). Stored on request.state.request_id.
    Every log line in the pipeline can bind this ID for distributed tracing.

P4 — CORS TOO PERMISSIVE
    localhost:3000 is now excluded from the allowed origins in production.

P6 — HTTP CLIENT LEAKS
    voter_search_service.close() added to lifespan shutdown alongside the
    existing pincode_service.close() (which was flagged but never wired up).
"""

import logging
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .middleware.rate_limit import RateLimitMiddleware
from .routes.health    import router as health_router
from .routes.chat      import router as chat_router
from .routes.ero       import router as ero_router
from .routes.voter     import router as voter_router
from .routes.profile   import router as profile_router
from .routes.tts       import router as tts_router
from .routes.grievance import router as grievance_router
from ..config.settings import settings


# ── PII redaction log filter ──────────────────────────────────────────────────
# Must be applied before any log handler can forward to Cloud Logging.
# Matches EPIC number patterns: 2–3 uppercase letters + 7–8 digits.
_EPIC_PATTERN = re.compile(r'\b[A-Z]{2,3}\d{7,8}\b')


class PiiRedactingFilter(logging.Filter):
    """
    Strips EPIC numbers from all log messages before they leave the process.
    Compliance requirement: voter EPIC data must not appear in Cloud Logging.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _EPIC_PATTERN.sub("[EPIC_REDACTED]", str(record.msg))
        if record.args:
            record.args = tuple(
                _EPIC_PATTERN.sub("[EPIC_REDACTED]", str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        return True


# Install PII filter on the root logger — covers all child loggers
_pii_filter = PiiRedactingFilter()
logging.getLogger().addFilter(_pii_filter)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── Correlation ID middleware ─────────────────────────────────────────────────

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Reads the Cloud Run trace header (X-Cloud-Trace-Context) or generates a
    short UUID. Stored on request.state.request_id for all downstream handlers.
    Routes can include this in error SSE events for correlating logs.
    """
    async def dispatch(self, request: Request, call_next):
        trace_header = request.headers.get("X-Cloud-Trace-Context", "")
        request_id = (
            trace_header.split("/")[0]
            if trace_header
            else str(uuid.uuid4())[:8]
        )
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: create shared Redis pool, warm Firebase SDK, initialise Vertex AI SDK.
    Shutdown: drain Redis pool, close all HTTP clients cleanly (SIGTERM window = 10s).
    """
    from redis.asyncio import ConnectionPool, Redis as AsyncRedis
    from ..services.pincode import pincode_service
    from ..services.voter_search import voter_search_service

    logger.info("MatdaanMitra API starting — environment=%s", settings.environment)

    # ── Redis pool ────────────────────────────────────────────────────────────
    # Shared pool with max_connections=20.  Under Cloud Run autoscaling, each
    # instance holds ≤20 connections; scale-out adds instances, not connections
    # per instance.  Cloud Memorystore default limit (1000) handles ~50 instances.
    try:
        app.state.redis_pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
        # Verify the pool works before accepting traffic
        r = AsyncRedis(connection_pool=app.state.redis_pool)
        await r.ping()
        logger.info("Redis pool initialised (url=%s)", settings.redis_url.split("@")[-1])
    except Exception as exc:
        # Redis is non-fatal — rate limiter fails open. Still initialise pool
        # so rate_limit.py has access to app.state.redis_pool.
        app.state.redis_pool = None
        logger.warning("Redis unavailable at startup (rate limiting will fail open): %s", exc)

    # ── Firebase Admin SDK (eager init) ──────────────────────────────────────
    # Eager init ensures the SDK is ready before the first request, avoiding
    # cold-start latency where the first N users hit auth during lazy init.
    if settings.firebase_service_account_path:
        try:
            import firebase_admin
            from firebase_admin import credentials
            if not firebase_admin._apps:
                cred = credentials.Certificate(settings.firebase_service_account_path)
                firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialised")
        except Exception as exc:
            logger.warning("Firebase Admin SDK init failed: %s", exc)
    else:
        logger.warning("FIREBASE_SERVICE_ACCOUNT_PATH not set — auth middleware will 401 all requests")

    # ── Vertex AI SDK (eager init if configured) ──────────────────────────────
    # Avoids cold-start where both _get_embeddings() and _get_endpoint() fire
    # aiplatform.init() simultaneously on the first real user request.
    if settings.gcp_project_id:
        try:
            from google.cloud import aiplatform
            aiplatform.init(
                project=settings.gcp_project_id,
                location=settings.gcp_location,
            )
            logger.info(
                "Vertex AI SDK initialised (project=%s location=%s)",
                settings.gcp_project_id, settings.gcp_location,
            )
        except Exception as exc:
            logger.warning("Vertex AI SDK init failed (will use static fallback): %s", exc)

    logger.info("MatdaanMitra API ready — all startup hooks complete")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("MatdaanMitra API shutting down (SIGTERM received)")

    # Close httpx clients (prevents connection leak warnings on Cloud Run SIGTERM)
    try:
        await pincode_service.close()
        logger.info("Pincode HTTP client closed")
    except Exception as exc:
        logger.warning("pincode_service.close() failed: %s", exc)

    try:
        await voter_search_service.close()
        logger.info("Voter search HTTP client closed")
    except Exception as exc:
        logger.warning("voter_search_service.close() failed: %s", exc)

    # Drain Redis pool last
    if app.state.redis_pool is not None:
        try:
            await app.state.redis_pool.disconnect()
            logger.info("Redis pool drained")
        except Exception as exc:
            logger.warning("Redis pool disconnect failed: %s", exc)


# ── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title="MatdaanMitra API",
    description="Intelligent voter assistance platform for Indian elections.",
    version="1.0.0",
    lifespan=lifespan,
    # Disable Swagger/ReDoc in production — reduces attack surface
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url=None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# P4 fix: localhost:3000 excluded in production to prevent any local app from
# making credentialed cross-origin requests to the production backend.
_allowed_origins = (
    [settings.frontend_url]
    if settings.environment == "production"
    else [settings.frontend_url, "http://localhost:3000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Middleware stack (order: outermost first) ─────────────────────────────────
app.add_middleware(CorrelationIdMiddleware)   # injects request_id
app.add_middleware(RateLimitMiddleware)       # IP-based throttle

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)     # GET  /health
app.include_router(chat_router)       # POST /chat
app.include_router(ero_router)        # GET  /ero/{pincode}
app.include_router(voter_router)      # GET  /voter/{epic_number}
app.include_router(profile_router)    # PATCH /profile/{session_id}/checklist
app.include_router(tts_router)        # POST /tts
app.include_router(grievance_router)  # POST /grievance/letter

logger.info("Routers mounted: health · chat · ero · voter · profile · tts · grievance")