"""
check_apis.py — MatdaanMitra API connectivity checker

Runs a quick smoke-test against every external service.
Run from backend/ directory:
    python check_apis.py

Green  ✅ = service reachable and credentials valid
Yellow ⚠️  = service reachable but not configured / using placeholder
Red    ❌ = service unreachable or credentials rejected
"""

import asyncio
import os
import sys

# Bootstrap path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(".env")

from config.settings import settings

PASS  = "  ✅"
WARN  = "  ⚠️ "
FAIL  = "  ❌"


def _status(ok: bool | None, detail: str) -> str:
    icon = PASS if ok is True else (WARN if ok is None else FAIL)
    return f"{icon}  {detail}"


# ── 1. Settings sanity ─────────────────────────────────────────────────────────

def check_settings() -> list[str]:
    results = []
    checks = {
        "GCP Project ID":          bool(settings.gcp_project_id),
        "Firebase Project ID":     bool(settings.firebase_project_id),
        "Firebase SA Path":        bool(settings.firebase_service_account_path),
        "Sarvam API Key":          bool(settings.sarvam_api_key),
        "Mapbox Token":            bool(settings.mapbox_access_token),
        "Fernet Key":              bool(settings.fernet_key),
        "Redis URL (non-default)": settings.redis_url != "redis://localhost:6379",
        "Vertex AI Index ID":      bool(settings.vertex_ai_index_id),
        "Vertex AI Endpoint ID":   bool(settings.vertex_ai_index_endpoint_id),
    }
    for name, configured in checks.items():
        results.append(_status(True if configured else None,
                               f"{name}: {'configured' if configured else 'using placeholder'}"))
    return results


# ── 2. Firebase Admin ──────────────────────────────────────────────────────────

def check_firebase() -> str:
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        sa_path = settings.firebase_service_account_path
        if not sa_path or not os.path.exists(sa_path):
            return _status(None, f"Firebase Admin: SA file not found at '{sa_path}'")

        if not firebase_admin._apps:
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)

        db = firestore.client()
        # Lightweight test: read a non-existent document
        db.collection("_health_check").document("ping").get()
        return _status(True, "Firebase Admin: connected to Firestore")
    except Exception as exc:
        return _status(False, f"Firebase Admin: {exc}")


# ── 3. Sarvam AI ───────────────────────────────────────────────────────────────

async def check_sarvam() -> str:
    import httpx
    if not settings.sarvam_api_key:
        return _status(None, "Sarvam AI: SARVAM_API_KEY not set")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
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
        if resp.status_code == 200:
            return _status(True, "Sarvam AI: translate endpoint OK")
        return _status(False, f"Sarvam AI: HTTP {resp.status_code} — {resp.text[:120]}")
    except Exception as exc:
        return _status(False, f"Sarvam AI: {exc}")


# ── 4. Mapbox ──────────────────────────────────────────────────────────────────

async def check_mapbox() -> str:
    import httpx
    if not settings.mapbox_access_token:
        return _status(None, "Mapbox: MAPBOX_ACCESS_TOKEN not set")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                "https://api.mapbox.com/search/geocode/v6/forward",
                params={"q": "400001, India", "access_token": settings.mapbox_access_token, "limit": 1},
            )
        if resp.status_code == 200:
            return _status(True, "Mapbox: geocoding endpoint OK")
        return _status(False, f"Mapbox: HTTP {resp.status_code}")
    except Exception as exc:
        return _status(False, f"Mapbox: {exc}")


# ── 5. Redis ───────────────────────────────────────────────────────────────────

async def check_redis() -> str:
    try:
        import redis.asyncio as aioredis
        async with aioredis.from_url(settings.redis_url) as r:
            pong = await r.ping()
        return _status(True if pong else None,
                       f"Redis: {'PONG received' if pong else 'connected but no PONG'}")
    except Exception as exc:
        return _status(None, f"Redis: {exc} (rate limiting will fail open)")


# ── 6. Vertex AI ───────────────────────────────────────────────────────────────

def check_vertex() -> str:
    if not settings.gcp_project_id:
        return _status(None, "Vertex AI: GCP_PROJECT_ID not set")
    try:
        import vertexai
        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location)
        return _status(True, f"Vertex AI: SDK initialized (project={settings.gcp_project_id})")
    except Exception as exc:
        return _status(False, f"Vertex AI: {exc}")


# ── 7. ECI reachability ────────────────────────────────────────────────────────

async def check_eci() -> str:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            resp = await client.get("https://electoralsearch.eci.gov.in")
        return _status(True, f"ECI Portal: reachable (HTTP {resp.status_code})")
    except Exception as exc:
        return _status(False, f"ECI Portal: {exc}")


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 55)
    print("  MatdaanMitra — API Connectivity Check")
    print("=" * 55)

    print("\n📋  Settings:")
    for line in check_settings():
        print(line)

    print("\n🔥  Firebase Admin:")
    print(check_firebase())

    print("\n🌐  Sarvam AI:")
    print(await check_sarvam())

    print("\n🗺️   Mapbox:")
    print(await check_mapbox())

    print("\n⚡  Redis:")
    print(await check_redis())

    print("\n🤖  Vertex AI:")
    print(check_vertex())

    print("\n🗳️   ECI Portal:")
    print(await check_eci())

    print("\n" + "=" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())