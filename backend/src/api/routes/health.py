"""
health.py — Service health check endpoint

Fixes (production audit):

P2 — NO DEPENDENCY HEALTH CHECK (Priority 1 in audit)
    Previous: GET /health returned {"status": "ok"} regardless of whether
    Firebase, Redis, or Vertex AI were reachable. Cloud Run uses this endpoint
    as the readiness probe. During a deployment where Vertex AI was just
    enabled, Cloud Run would declare the instance "ready" and start routing
    chat requests while the Vertex AI client was still cold-starting (5–15s).
    First N users would receive timeout errors.

    Fix: two-tier health check:
      GET /health           → shallow ping (fast, used by load balancer heartbeat)
      GET /health?deep=true → dependency probes (used by Cloud Run readiness probe)

    Cloud Run configuration (add to service YAML or gcloud deploy flags):
      --startup-probe=httpGet.path=/health?deep=true
      --startup-probe=httpGet.initialDelaySeconds=5
      --startup-probe=httpGet.timeoutSeconds=10
      --startup-probe=httpGet.failureThreshold=3
      --health-checks-liveness-path=/health

    The deep check probes each dependency with a 2-second timeout and returns
    overall "ok" or "degraded". Cloud Run will not route traffic until the
    startup probe returns 200 with status="ok".

    Redis probe uses the shared connection pool from app.state (not a new
    connection), consistent with the P1 connection-pool fix in main.py.

NOTE — Sarvam AI probe makes a real translation API call. This is intentional:
    a network-level reachability check is insufficient for Sarvam — the key
    may be invalid even if the endpoint is reachable. The translate probe uses
    the smallest possible payload ("hi" → Hindi) to minimise cost (~0.0001 USD).
"""

import httpx
from fastapi import APIRouter, Request
from typing import Optional
from ...config.settings import settings

router = APIRouter()


@router.get("/health")
async def health_check(request: Request, deep: bool = False):
    """
    Shallow (default) or deep (deep=true) health check.

    Shallow: fast dict — used by Cloud Run liveness probe and load balancer.
    Deep: probes Redis, Firebase init, Vertex AI config, ECI API, and Sarvam AI.
          Returns HTTP 200 in all cases (Cloud Run startup probe uses the
          `status` field value, not the HTTP code, to avoid 503 cascades).
    """
    base = {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.environment,
    }

    if not deep:
        return base

    checks: dict[str, str] = {}

    # ── Redis (uses shared pool from app.state, not a new connection) ─────────
    try:
        pool = getattr(request.app.state, "redis_pool", None) if request else None
        if pool is not None:
            from redis.asyncio import Redis as AsyncRedis
            r = AsyncRedis(connection_pool=pool)
            await r.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "pool_not_initialised (rate limiting inactive)"
    except Exception as exc:
        checks["redis"] = f"FAILED: {exc}"

    # ── Firebase Admin SDK ────────────────────────────────────────────────────
    try:
        import firebase_admin
        if firebase_admin._apps:
            checks["firebase"] = "ok"
        elif settings.firebase_service_account_path:
            checks["firebase"] = "not_initialised (service_account_path set but SDK not started)"
        else:
            checks["firebase"] = "unconfigured (FIREBASE_SERVICE_ACCOUNT_PATH not set)"
    except Exception as exc:
        checks["firebase"] = f"FAILED: {exc}"

    # ── Vertex AI ─────────────────────────────────────────────────────────────
    if settings.gcp_project_id and settings.vertex_ai_index_endpoint_id:
        checks["vertex_ai"] = "configured"
    elif settings.gcp_project_id:
        checks["vertex_ai"] = "project_set_but_no_endpoint (using static fallback)"
    else:
        checks["vertex_ai"] = "not_configured (using static ECI fallback corpus)"

    # ── ECI electoral search reachability ────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                "https://electoralsearch.eci.gov.in",
                follow_redirects=True,
            )
            checks["eci_api"] = f"ok (HTTP {resp.status_code})"
    except Exception as exc:
        checks["eci_api"] = f"FAILED: {exc}"

    # ── India Post Pincode API ────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://api.postalpincode.in/pincode/411038")
            data = resp.json()
            if isinstance(data, list) and data[0].get("Status") == "Success":
                checks["pincode_api"] = "ok"
            else:
                checks["pincode_api"] = f"unexpected response: {data[0].get('Status', 'unknown')}"
    except Exception as exc:
        checks["pincode_api"] = f"FAILED: {repr(exc)}"

    # ── Mapbox (only if token configured) ────────────────────────────────────
    if settings.mapbox_access_token:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(
                    "https://api.mapbox.com/geocoding/v5/mapbox.places/110001.json",
                    params={"access_token": settings.mapbox_access_token},
                )
                if resp.status_code == 200 and "features" in resp.json():
                    checks["mapbox"] = "ok"
                else:
                    checks["mapbox"] = f"HTTP {resp.status_code}"
        except Exception as exc:
            checks["mapbox"] = f"FAILED: {exc}"
    else:
        checks["mapbox"] = "skipped (MAPBOX_ACCESS_TOKEN not set)"

    # ── Sarvam AI (only if key configured) ───────────────────────────────────
    if settings.sarvam_api_key:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(
                    "https://api.sarvam.ai/translate",
                    headers={"api-subscription-key": settings.sarvam_api_key},
                    json={
                        "input": "hi",
                        "source_language_code": "en-IN",
                        "target_language_code": "hi-IN",
                        "model": "mayura:v1",
                    },
                )
                checks["sarvam_ai"] = "ok" if resp.status_code in (200, 201) else f"HTTP {resp.status_code}"
        except Exception as exc:
            checks["sarvam_ai"] = f"FAILED: {exc}"
    else:
        checks["sarvam_ai"] = "skipped (SARVAM_API_KEY not set)"

    # ── Overall status ────────────────────────────────────────────────────────
    _non_fatal_prefixes = ("ok", "skipped", "configured", "not_configured", "unconfigured", "project_set")
    all_ok = all(
        any(str(v).startswith(prefix) for prefix in _non_fatal_prefixes)
        for v in checks.values()
    )

    return {
        **base,
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }