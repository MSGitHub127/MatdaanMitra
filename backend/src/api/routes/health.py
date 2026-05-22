import redis.asyncio as aioredis
import httpx
from fastapi import APIRouter
from src.config.settings import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    results = {}

    # 1. Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        results["redis"] = "ok"
    except Exception as e:
        results["redis"] = f"FAILED: {str(e)}"

    # 2. ECI API reachability
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://electoralsearch.eci.gov.in",
                follow_redirects=True
            )
            results["eci_api"] = f"ok (HTTP {resp.status_code})"
    except Exception as e:
        results["eci_api"] = f"FAILED: {str(e)}"

    # 3. India Post Pincode API
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://api.postalpincode.in/pincode/411038"
            )
            data = resp.json()
            if data[0]["Status"] == "Success":
                results["pincode_api"] = "ok"
            else:
                results["pincode_api"] = f"unexpected: {data[0]['Status']}"
    except Exception as e:
        results["pincode_api"] = f"FAILED: {str(e)}"

    # 4. Mapbox (only if configured)
    if settings.check_api_available("maps"):
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    "https://api.mapbox.com/geocoding/v5/mapbox.places/411038.json",
                    params={
                        "access_token": settings.mapbox_access_token
                    }
                )
                data = resp.json()
                if resp.status_code == 200 and "features" in data:
                    results["mapbox"] = "ok"
                else:
                    results["mapbox"] = f"API error: {data.get('message', 'Unknown')}"
        except Exception as e:
            results["mapbox"] = f"FAILED: {str(e)}"
    else:
        results["mapbox"] = "skipped (not configured)"

    all_ok = all(
        "ok" in str(v) or "skipped" in str(v)
        for v in results.values()
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "environment": settings.environment,
        "checks": results
    }
