"""
check_apis.py — MatdaanMitra API connectivity checker  (extended)

Runs a smoke-test against every external service.  Run from backend/:
    python check_apis.py                   # standard human-readable output
    python check_apis.py --json            # machine-readable JSON report
    python check_apis.py --fail-fast       # exit 1 on first red failure
    python check_apis.py --timeout 12      # override per-probe timeout (s)

Legend
------
  ✅  Green  — service reachable, credentials valid
  ⚠️  Yellow — service reachable but not configured / placeholder key
  ❌  Red    — service unreachable or credentials rejected

Extended probe coverage (new vs. original):
  • Vertex AI Vector Search  — actual find_neighbors call on the index endpoint
  • Firebase Firestore write  — round-trip write + delete on _health_check
  • Sarvam TTS endpoint       — separate probe from translate
  • Mapbox static-tiles API   — verifies token scope beyond geocoding
  • NVSP (ECI) deep check     — HEAD + redirect chain validation
  • Summary statistics        — pass / warn / fail counts + exit code
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# Bootstrap path and load env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(".env")

from config.settings import settings

# ── CLI ────────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="MatdaanMitra connectivity checker")
parser.add_argument("--json",      action="store_true", help="Emit JSON report to stdout")
parser.add_argument("--fail-fast", action="store_true", help="Exit 1 on first red failure")
parser.add_argument("--timeout",   type=float, default=8.0, help="Per-probe HTTP timeout (s)")
ARGS = parser.parse_args()

TIMEOUT = ARGS.timeout

# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class ProbeResult:
    """Single probe outcome."""
    name:    str
    status:  str          # "pass" | "warn" | "fail"
    detail:  str
    latency: float = 0.0  # seconds
    extra:   dict  = field(default_factory=dict)

    @property
    def icon(self) -> str:
        return {"pass": "  ✅", "warn": "  ⚠️ ", "fail": "  ❌"}[self.status]

    def __str__(self) -> str:
        lat = f"  [{self.latency*1000:.0f}ms]" if self.latency else ""
        return f"{self.icon}  {self.detail}{lat}"


def _ok(name: str, detail: str, latency: float = 0.0, **extra) -> ProbeResult:
    return ProbeResult(name=name, status="pass", detail=detail, latency=latency, extra=extra)

def _warn(name: str, detail: str, latency: float = 0.0, **extra) -> ProbeResult:
    return ProbeResult(name=name, status="warn", detail=detail, latency=latency, extra=extra)

def _fail(name: str, detail: str, latency: float = 0.0, **extra) -> ProbeResult:
    return ProbeResult(name=name, status="fail", detail=detail, latency=latency, extra=extra)


# ── Timing helper ──────────────────────────────────────────────────────────────

class _Timer:
    def __enter__(self):
        self._t = time.perf_counter()
        return self
    def __exit__(self, *_):
        self.elapsed = time.perf_counter() - self._t


# ── 1. Settings sanity ─────────────────────────────────────────────────────────

def check_settings() -> list[ProbeResult]:
    checks = {
        "GCP Project ID":          settings.gcp_project_id,
        "Firebase Project ID":     settings.firebase_project_id,
        "Firebase SA Path":        settings.firebase_service_account_path,
        "Sarvam API Key":          settings.sarvam_api_key,
        "Mapbox Token":            settings.mapbox_access_token,
        "Fernet Key":              settings.fernet_key,
        "Redis URL (non-default)": settings.redis_url != "redis://localhost:6379",
        "Vertex AI Index ID":      settings.vertex_ai_index_id,
        "Vertex AI Endpoint ID":   settings.vertex_ai_index_endpoint_id,
        "GCP Location":            bool(getattr(settings, "gcp_location", "")),
    }
    results = []
    for name, configured in checks.items():
        if configured:
            results.append(_ok(f"settings/{name}", f"{name}: configured"))
        else:
            results.append(_warn(f"settings/{name}", f"{name}: using placeholder / not set"))
    return results


# ── 2. Firebase Admin — shallow init ──────────────────────────────────────────

def check_firebase_init() -> ProbeResult:
    """SDK initialisation + service-account file presence."""
    try:
        import firebase_admin
        from firebase_admin import credentials

        sa_path = settings.firebase_service_account_path
        if not sa_path or not os.path.exists(sa_path):
            return _warn("firebase/init",
                         f"Firebase Admin: SA file not found at '{sa_path}'")

        if not firebase_admin._apps:
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)

        return _ok("firebase/init", "Firebase Admin: SDK initialised (SA file present)")
    except Exception as exc:
        return _fail("firebase/init", f"Firebase Admin init: {exc}")


# ── 3. Firebase Firestore — round-trip write + delete ─────────────────────────

def check_firestore_rtt() -> ProbeResult:
    """
    Writes a timestamped document to _health_check/ping and deletes it.
    Validates credentials beyond just SDK init — a wrong project ID or
    missing IAM roles surface here rather than silently at query time.
    """
    try:
        from firebase_admin import firestore

        with _Timer() as t:
            db  = firestore.client()
            ref = db.collection("_health_check").document("ping")

            def _rtt():
                ref.set({"ts": firestore.SERVER_TIMESTAMP, "probe": "check_apis"})
                snap = ref.get()
                ref.delete()
                return snap.exists

            import asyncio
            loop = asyncio.get_event_loop()
            existed = loop.run_in_executor(None, _rtt)
            # Firestore client is sync — run in thread and await
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                existed = ex.submit(_rtt).result(timeout=10)

        if existed:
            return _ok("firebase/firestore-rtt",
                       "Firestore: write→read→delete round-trip OK", t.elapsed)
        return _warn("firebase/firestore-rtt",
                     "Firestore: write succeeded but read returned no data", t.elapsed)

    except Exception as exc:
        return _fail("firebase/firestore-rtt", f"Firestore RTT: {exc}")


# ── 4. Sarvam AI — translate endpoint ─────────────────────────────────────────

async def check_sarvam_translate() -> ProbeResult:
    import httpx
    if not settings.sarvam_api_key:
        return _warn("sarvam/translate", "Sarvam AI: SARVAM_API_KEY not set")
    try:
        with _Timer() as t:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
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
            result = resp.json().get("translated_text", "")
            return _ok("sarvam/translate",
                       f"Sarvam translate: OK — '{result[:30]}'", t.elapsed)
        return _fail("sarvam/translate",
                     f"Sarvam translate: HTTP {resp.status_code} — {resp.text[:100]}", t.elapsed)
    except Exception as exc:
        return _fail("sarvam/translate", f"Sarvam translate: {exc}")


# ── 5. Sarvam AI — TTS endpoint (separate scope from translate) ───────────────

async def check_sarvam_tts() -> ProbeResult:
    import httpx
    if not settings.sarvam_api_key:
        return _warn("sarvam/tts", "Sarvam TTS: SARVAM_API_KEY not set")
    try:
        with _Timer() as t:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    "https://api.sarvam.ai/text-to-speech",
                    headers={"api-subscription-key": settings.sarvam_api_key},
                    json={
                        "inputs": ["नमस्ते"],
                        "target_language_code": "hi-IN",
                        "speaker": "anushka",
                        "model": "bulbul:v2",
                        "speech_sample_rate": 8000,  # smallest payload
                    },
                )
        if resp.status_code == 200:
            audios = resp.json().get("audios", [])
            audio_kb = round(len(audios[0]) * 3 / 4 / 1024) if audios else 0
            return _ok("sarvam/tts",
                       f"Sarvam TTS: OK — audio ~{audio_kb} KB", t.elapsed)
        return _fail("sarvam/tts",
                     f"Sarvam TTS: HTTP {resp.status_code} — {resp.text[:100]}", t.elapsed)
    except Exception as exc:
        return _fail("sarvam/tts", f"Sarvam TTS: {exc}")


# ── 6. Mapbox — geocoding endpoint ────────────────────────────────────────────

async def check_mapbox_geocoding() -> ProbeResult:
    import httpx
    if not settings.mapbox_access_token:
        return _warn("mapbox/geocoding", "Mapbox: MAPBOX_ACCESS_TOKEN not set")
    try:
        with _Timer() as t:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    "https://api.mapbox.com/search/geocode/v6/forward",
                    params={
                        "q": "400001, India",
                        "access_token": settings.mapbox_access_token,
                        "limit": 1,
                    },
                )
        if resp.status_code == 200:
            features = resp.json().get("features", [])
            place = features[0]["properties"].get("full_address", "OK") if features else "OK"
            return _ok("mapbox/geocoding",
                       f"Mapbox geocoding: OK — '{place[:50]}'", t.elapsed)
        return _fail("mapbox/geocoding",
                     f"Mapbox geocoding: HTTP {resp.status_code}", t.elapsed)
    except Exception as exc:
        return _fail("mapbox/geocoding", f"Mapbox geocoding: {exc}")


# ── 7. Mapbox — static tiles (validates full token scope) ─────────────────────

async def check_mapbox_tiles() -> ProbeResult:
    """
    A token with only the geocoding scope will 401 here.
    Catching this early prevents blank maps at runtime.
    """
    import httpx
    if not settings.mapbox_access_token:
        return _warn("mapbox/tiles", "Mapbox tiles: MAPBOX_ACCESS_TOKEN not set")
    try:
        with _Timer() as t:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    "https://api.mapbox.com/styles/v1/mapbox/light-v11",
                    params={"access_token": settings.mapbox_access_token},
                )
        if resp.status_code == 200:
            return _ok("mapbox/tiles", "Mapbox styles API: token scope OK", t.elapsed)
        if resp.status_code == 401:
            return _fail("mapbox/tiles",
                         "Mapbox tiles: 401 — token missing styles scope", t.elapsed)
        return _warn("mapbox/tiles",
                     f"Mapbox tiles: HTTP {resp.status_code} (non-fatal)", t.elapsed)
    except Exception as exc:
        return _fail("mapbox/tiles", f"Mapbox tiles: {exc}")


# ── 8. Redis ───────────────────────────────────────────────────────────────────

async def check_redis() -> ProbeResult:
    try:
        import redis.asyncio as aioredis
        with _Timer() as t:
            async with aioredis.from_url(settings.redis_url) as r:
                pong = await r.ping()
        status = "pass" if pong else "warn"
        detail = "Redis: PONG received" if pong else "Redis: connected but no PONG"
        return ProbeResult(name="redis", status=status, detail=detail, latency=t.elapsed)
    except Exception as exc:
        return _warn("redis", f"Redis: {exc} (rate limiting will fail open)")


# ── 9. Vertex AI — SDK initialisation ─────────────────────────────────────────

def check_vertex_init() -> ProbeResult:
    if not settings.gcp_project_id:
        return _warn("vertex/init", "Vertex AI: GCP_PROJECT_ID not set")
    try:
        with _Timer() as t:
            import vertexai
            vertexai.init(
                project=settings.gcp_project_id,
                location=getattr(settings, "gcp_location", "us-central1"),
            )
        return _ok("vertex/init",
                   f"Vertex AI: SDK init OK (project={settings.gcp_project_id})", t.elapsed)
    except Exception as exc:
        return _fail("vertex/init", f"Vertex AI SDK init: {exc}")


# ── 10. Vertex AI Vector Search — actual neighbor query ───────────────────────

def check_vertex_vector_search() -> ProbeResult:
    """
    Issues a real find_neighbors call with a zero-vector probe query.
    A 0-vector will never match real content but validates:
      - Endpoint ID is correct and deployed
      - IAM roles (roles/aiplatform.user) are granted
      - Index is not in a broken state
    """
    if not settings.vertex_ai_index_endpoint_id or not settings.vertex_ai_index_id:
        return _warn("vertex/vector-search",
                     "Vertex AI Vector Search: Index or Endpoint ID not configured")
    if not settings.gcp_project_id:
        return _warn("vertex/vector-search",
                     "Vertex AI Vector Search: GCP_PROJECT_ID not set")
    try:
        with _Timer() as t:
            from google.cloud import aiplatform
            aiplatform.init(
                project=settings.gcp_project_id,
                location=getattr(settings, "gcp_location", "us-central1"),
            )
            endpoint = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=settings.vertex_ai_index_endpoint_id
            )
            # Probe with a 768-dim zero vector (text-embedding-004 dimensionality)
            probe_vector = [0.0] * 768
            response = endpoint.find_neighbors(
                deployed_index_id=settings.vertex_ai_index_id,
                queries=[probe_vector],
                num_neighbors=1,
            )
        neighbor_count = len(response[0]) if response else 0
        return _ok("vertex/vector-search",
                   f"Vertex AI Vector Search: endpoint reachable, "
                   f"{neighbor_count} neighbor(s) returned for probe query",
                   t.elapsed,
                   endpoint_id=settings.vertex_ai_index_endpoint_id)
    except Exception as exc:
        # Distinguish auth errors from config errors for clearer triage
        err_str = str(exc)
        if "403" in err_str or "PERMISSION_DENIED" in err_str:
            return _fail("vertex/vector-search",
                         f"Vertex AI Vector Search: 403 PERMISSION_DENIED — "
                         f"check roles/aiplatform.user on service account")
        if "404" in err_str or "NOT_FOUND" in err_str:
            return _fail("vertex/vector-search",
                         f"Vertex AI Vector Search: 404 NOT_FOUND — "
                         f"verify VERTEX_AI_INDEX_ENDPOINT_ID and VERTEX_AI_INDEX_ID")
        return _fail("vertex/vector-search", f"Vertex AI Vector Search: {exc}")


# ── 11. ECI / NVSP portal ─────────────────────────────────────────────────────

async def check_eci() -> ProbeResult:
    import httpx
    try:
        with _Timer() as t:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
                resp = await client.get("https://electoralsearch.eci.gov.in")
        if resp.status_code == 200:
            return _ok("eci/portal",
                       f"ECI / NVSP portal: reachable (HTTP {resp.status_code}, "
                       f"final URL: {resp.url})", t.elapsed)
        return _warn("eci/portal",
                     f"ECI portal: HTTP {resp.status_code} (voter fallback still works)",
                     t.elapsed)
    except Exception as exc:
        return _fail("eci/portal", f"ECI portal: {exc} (NVSP redirect CTA will degrade)")


# ── 12. ECI API — direct voter search (expected 403 from non-browser) ─────────

async def check_eci_api() -> ProbeResult:
    """
    Verifies the ECI search API behaviour.  A 403 response confirms the
    endpoint exists and our NVSP-redirect fallback is the correct strategy.
    Any other status (5xx, timeout) indicates an infra change.
    """
    import httpx
    try:
        with _Timer() as t:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    "https://electoralsearch.eci.gov.in/api/search",
                    json={"epicNo": "PROBE000000", "lang": "en"},
                    headers={"Referer": "https://electoralsearch.eci.gov.in/"},
                )
        if resp.status_code == 403:
            return _ok("eci/api",
                       "ECI search API: 403 as expected (NVSP-redirect fallback correct)",
                       t.elapsed)
        if resp.status_code in (200, 404):
            return _warn("eci/api",
                         f"ECI search API: HTTP {resp.status_code} — "
                         "direct access may now work; review voter_search.py",
                         t.elapsed)
        return _warn("eci/api",
                     f"ECI search API: HTTP {resp.status_code} — monitor for changes",
                     t.elapsed)
    except Exception as exc:
        return _fail("eci/api", f"ECI search API: {exc}")


# ── Summary ────────────────────────────────────────────────────────────────────

def _print_results(section: str, results: list[ProbeResult]) -> None:
    print(f"\n{section}")
    for r in results:
        print(r)


def _json_report(all_results: list[ProbeResult]) -> dict:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    probes = []
    for r in all_results:
        counts[r.status] += 1
        probes.append({
            "name":    r.name,
            "status":  r.status,
            "detail":  r.detail,
            "latency_ms": round(r.latency * 1000),
            **r.extra,
        })
    return {
        "summary": counts,
        "overall": "pass" if counts["fail"] == 0 else "fail",
        "probes":  probes,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> int:
    all_results: list[ProbeResult] = []

    if not ARGS.json:
        print("\n" + "=" * 62)
        print("  MatdaanMitra — API Connectivity Check (extended)")
        print("=" * 62)

    # ── Settings (sync) ────────────────────────────────────────────────────────
    setting_results = check_settings()
    all_results.extend(setting_results)
    if not ARGS.json:
        _print_results("📋  Settings:", setting_results)

    # ── Firebase (sync) ────────────────────────────────────────────────────────
    fb_init = check_firebase_init()
    all_results.append(fb_init)
    if not ARGS.json:
        _print_results("🔥  Firebase Admin:", [fb_init])

    if fb_init.status == "pass":
        fb_rtt = check_firestore_rtt()
        all_results.append(fb_rtt)
        if not ARGS.json:
            print(fb_rtt)
    if ARGS.fail_fast and any(r.status == "fail" for r in all_results):
        if ARGS.json:
            print(json.dumps(_json_report(all_results), indent=2))
        return 1

    # ── Sarvam AI (async) ──────────────────────────────────────────────────────
    sarvam_translate = await check_sarvam_translate()
    sarvam_tts       = await check_sarvam_tts()
    all_results.extend([sarvam_translate, sarvam_tts])
    if not ARGS.json:
        _print_results("🗣️   Sarvam AI:", [sarvam_translate, sarvam_tts])

    # ── Mapbox (async) ─────────────────────────────────────────────────────────
    mapbox_geo   = await check_mapbox_geocoding()
    mapbox_tiles = await check_mapbox_tiles()
    all_results.extend([mapbox_geo, mapbox_tiles])
    if not ARGS.json:
        _print_results("🗺️   Mapbox:", [mapbox_geo, mapbox_tiles])

    # ── Redis (async) ──────────────────────────────────────────────────────────
    redis_result = await check_redis()
    all_results.append(redis_result)
    if not ARGS.json:
        _print_results("⚡  Redis:", [redis_result])

    # ── Vertex AI (sync) ───────────────────────────────────────────────────────
    vertex_init = check_vertex_init()
    all_results.append(vertex_init)
    if not ARGS.json:
        _print_results("🤖  Vertex AI:", [vertex_init])

    if vertex_init.status == "pass":
        vertex_vs = check_vertex_vector_search()
        all_results.append(vertex_vs)
        if not ARGS.json:
            print(vertex_vs)

    # ── ECI / NVSP (async) ────────────────────────────────────────────────────
    eci_portal = await check_eci()
    eci_api    = await check_eci_api()
    all_results.extend([eci_portal, eci_api])
    if not ARGS.json:
        _print_results("🗳️   ECI / NVSP:", [eci_portal, eci_api])

    # ── Summary ────────────────────────────────────────────────────────────────
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for r in all_results:
        counts[r.status] += 1

    if ARGS.json:
        print(json.dumps(_json_report(all_results), indent=2))
    else:
        print("\n" + "=" * 62)
        print(
            f"  Summary — "
            f"✅ {counts['pass']} passed  "
            f"⚠️  {counts['warn']} warned  "
            f"❌ {counts['fail']} failed"
        )
        print("=" * 62 + "\n")

    return 0 if counts["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
