"""
main.py — FastAPI application entry point

Critical fix: the previous version only registered the health router.
All feature routes (chat, ero, voter, profile, tts) were defined but
never mounted, making the entire API unreachable.

This version registers every router at the root level to match the
frontend's API call paths:
  POST /chat         → chat.py
  GET  /ero/{pin}   → ero.py
  GET  /voter/status → voter.py
  GET/POST /profile  → profile.py
  POST /tts          → tts.py
  GET  /health       → health.py
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .middleware.rate_limit import RateLimitMiddleware
from .routes.health  import router as health_router
from .routes.chat    import router as chat_router
from .routes.ero     import router as ero_router
from .routes.voter   import router as voter_router
from .routes.profile import router as profile_router
from .routes.tts     import router as tts_router
from ..config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hooks."""
    logger.info("MatdaanMitra API starting — environment: %s", settings.environment)
    yield
    logger.info("MatdaanMitra API shutting down")


app = FastAPI(
    title="MatdaanMitra API",
    description="Intelligent voter assistance platform for Indian elections.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url=None,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Rate limiting (Redis-backed) ───────────────────────────────────────────────
app.add_middleware(RateLimitMiddleware)

# ── Routers ────────────────────────────────────────────────────────────────────
# NOTE: order matters for OpenAPI docs; keep health first so it's easy to find.
app.include_router(health_router)   # GET  /health
app.include_router(chat_router)     # POST /chat
app.include_router(ero_router)      # GET  /ero/{pincode}
app.include_router(voter_router)    # GET  /voter/status
app.include_router(profile_router)  # GET/POST /profile/...
app.include_router(tts_router)      # POST /tts

logger.info(
    "Routers mounted: health · chat · ero · voter · profile · tts"
)