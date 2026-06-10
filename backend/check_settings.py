"""
check_settings.py — Verify all MatdaanMitra settings load correctly

Run from backend/ directory:
    python check_settings.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from config.settings import settings

def mask(value: str, show: int = 6) -> str:
    """Show only first N chars of a secret value."""
    if not value:
        return "⚠️  NOT SET"
    if len(value) <= show:
        return "✅  " + "*" * len(value)
    return "✅  " + value[:show] + "…" + "*" * max(0, len(value) - show)

def check(label: str, value: str, secret: bool = False) -> None:
    display = mask(value) if secret else (f"✅  {value}" if value else "⚠️  NOT SET")
    print(f"  {label:<38} {display}")


print("\n" + "=" * 62)
print("  MatdaanMitra — Settings Verification")
print("=" * 62)

print("\n🏗️   Application")
check("ENVIRONMENT",           settings.environment)
check("LOG_LEVEL",             settings.log_level)
check("FRONTEND_URL",          settings.frontend_url)

print("\n☁️   GCP / Vertex AI")
check("GCP_PROJECT_ID",                   settings.gcp_project_id)
check("GCP_LOCATION",                     settings.gcp_location)
check("VERTEX_AI_INDEX_ID",               settings.vertex_ai_index_id)
check("VERTEX_AI_INDEX_ENDPOINT_ID",      settings.vertex_ai_index_endpoint_id)

print("\n🔥  Firebase")
check("FIREBASE_PROJECT_ID",              settings.firebase_project_id)
check("FIREBASE_SERVICE_ACCOUNT_PATH",    settings.firebase_service_account_path)

print("\n🌐  External APIs")
check("SARVAM_API_KEY",        settings.sarvam_api_key,        secret=True)
check("MAPBOX_ACCESS_TOKEN",   settings.mapbox_access_token,   secret=True)

print("\n🔒  Security")
check("FERNET_KEY",            settings.fernet_key,            secret=True)

print("\n⚡  Infrastructure")
check("REDIS_URL",             settings.redis_url)
check("GCS_BUCKET_NAME",       settings.gcs_bucket_name)

# Summary
missing = [
    name for name, value in [
        ("GCP_PROJECT_ID",              settings.gcp_project_id),
        ("FIREBASE_PROJECT_ID",         settings.firebase_project_id),
        ("FIREBASE_SERVICE_ACCOUNT_PATH", settings.firebase_service_account_path),
        ("SARVAM_API_KEY",              settings.sarvam_api_key),
        ("MAPBOX_ACCESS_TOKEN",         settings.mapbox_access_token),
        ("FERNET_KEY",                  settings.fernet_key),
    ]
    if not value
]

print("\n" + "=" * 62)
if missing:
    print(f"  ⚠️  {len(missing)} setting(s) not configured: {', '.join(missing)}")
else:
    print("  ✅  All required settings configured")
print("=" * 62 + "\n")