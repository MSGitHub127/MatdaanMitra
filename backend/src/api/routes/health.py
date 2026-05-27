"""
health.py — Service health check endpoint

GET /health  →  checks Redis, ECI API reachability, Pincode API, Mapbox, Sarvam AI.
Previously called settings.check_api_available("maps") which does not exist — fixed.
"""

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter
from ...config.settings import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    results: dict[str, str] = {}

    # ── 1. Redis ──────────────────────────────────────────────────────────────
    try:
        async with aioredis.from_url(settings.redis_url) as r:
            await r.ping()
        results["redis"] = "ok"
    except Exception as exc:
        results["redis"] = f"FAILED: {exc}"

    # ── 2. ECI electoral search reachability ──────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://electoralsearch.eci.gov.in",
                follow_redirects=True,
            )
            results["eci_api"] = f"ok (HTTP {resp.status_code})"
    except Exception as exc:
        results["eci_api"] = f"FAILED: {exc}"

    # ── 3. India Post Pincode API ──────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get("https://api.postalpincode.in/pincode/411038")
            data = resp.json()
            if data[0]["Status"] == "Success":
                results["pincode_api"] = "ok"
            else:
                results["pincode_api"] = f"unexpected: {data[0]['Status']}"
    except Exception as exc:
        results["pincode_api"] = f"FAILED: {exc}"

    # ── 4. Mapbox — only if token is configured ────────────────────────────────
    if settings.mapbox_access_token:
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    "https://api.mapbox.com/geocoding/v5/mapbox.places/411038.json",
                    params={"access_token": settings.mapbox_access_token},
                )
                data = resp.json()
                if resp.status_code == 200 and "features" in data:
                    results["mapbox"] = "ok"
                else:
                    results["mapbox"] = f"API error: {data.get('message', 'unknown')}"
        except Exception as exc:
            results["mapbox"] = f"FAILED: {exc}"
    else:
        results["mapbox"] = "skipped (MAPBOX_ACCESS_TOKEN not set)"

    # ── 5. Sarvam AI — only if key is configured ──────────────────────────────
    if settings.sarvam_api_key:
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.post(
                    "https://api.sarvam.ai/translate",
                    headers={"api-subscription-key": settings.sarvam_api_key},
                    json={
                        "input": "hello",
                        "source_language_code": "en-IN",
                        "target_language_code": "hi-IN",
                        "model": "mayura:v1",
                    },
                )
                if resp.status_code in (200, 201):
                    results["sarvam_ai"] = "ok"
                else:
                    results["sarvam_ai"] = f"HTTP {resp.status_code}"
        except Exception as exc:
            results["sarvam_ai"] = f"FAILED: {exc}"
    else:
        results["sarvam_ai"] = "skipped (SARVAM_API_KEY not set)"

    all_ok = all(
        "ok" in str(v) or "skipped" in str(v)
        for v in results.values()
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "environment": settings.environment,
        "checks": results,
    }