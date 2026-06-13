"""
settings.py — Centralised application configuration

Fix (production audit):

P1 — SILENT MISCONFIGURATION (CRITICAL)
    Previous: every field defaulted to "". Pydantic Settings would succeed even
    if every secret was absent. The app would start cleanly, serve traffic, and
    then fail at the first operation with an opaque error deep inside the pipeline
    (e.g. Fernet raises "Fernet key must be 32 url-safe base64-encoded bytes"
    after a real user has already waited 4 seconds for the pipeline to run).

    Fix: @model_validator(mode="after") check_production_secrets() raises
    ValueError on startup if any required secret is missing when
    ENVIRONMENT=production. Cloud Run will reject the instance before routing
    any traffic to it, so the failure is always operator-visible (deployment
    rollout stalls) rather than user-visible (intermittent 500s).

    In development / CI, all fields remain optional (default "")
    so local dev and CI pipelines don't need real credentials.

    Required env vars in production:
      GCP_PROJECT_ID
      FERNET_KEY                  (generate: see below)
      FIREBASE_SERVICE_ACCOUNT_PATH
      SARVAM_API_KEY
      REDIS_URL                   (Cloud Memorystore URL)
      MAPBOX_ACCESS_TOKEN

    Generate FERNET_KEY:
      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── GCP ────────────────────────────────────────────────────────────────
    gcp_project_id: str = ""
    gcp_location:   str = "asia-south1"

    # ── Vertex AI (RAG + Gemini) ───────────────────────────────────────────
    vertex_ai_index_id:          str = ""
    vertex_ai_index_endpoint_id: str = ""

    # ── Language & Voice — Sarvam AI ──────────────────────────────────────
    sarvam_api_key: str = ""

    # ── Geospatial — Mapbox ────────────────────────────────────────────────
    mapbox_access_token: str = ""

    # ── Firebase ──────────────────────────────────────────────────────────
    firebase_project_id:           str = ""
    firebase_service_account_path: str = ""

    # ── Infrastructure ────────────────────────────────────────────────────
    redis_url:       str = "redis://localhost:6379"
    gcs_bucket_name: str = "matdaan-eci-corpus"

    # ── Security ──────────────────────────────────────────────────────────
    fernet_key: str = ""
    fernet_key_versions: str = ""   # e.g. "v0:oldkey1,v2:oldkey2"

    # ── App ───────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"
    environment:  str = "development"
    log_level:    str = "INFO"

    # ── Production startup validator ──────────────────────────────────────
    @model_validator(mode="after")
    def check_production_secrets(self) -> "Settings":
        """
        Fail fast with a clear error if required secrets are missing in production.

        This validator runs at application startup. In production, a missing secret
        causes the FastAPI lifespan to raise, which prevents Cloud Run from marking
        the instance healthy — traffic is never routed to a misconfigured instance.

        In development / CI (ENVIRONMENT != "production"), all fields remain optional
        so the app starts without real credentials (Vertex AI, Firebase, etc. will
        be unavailable and will use fallback paths or fail with clear log messages).
        """
        if self.environment != "production":
            return self

        required: dict[str, str] = {
            "GCP_PROJECT_ID":                   self.gcp_project_id,
            "FERNET_KEY":                        self.fernet_key,
            "FIREBASE_SERVICE_ACCOUNT_PATH":     self.firebase_service_account_path,
            "SARVAM_API_KEY":                    self.sarvam_api_key,
            "REDIS_URL":                         self.redis_url
                                                 if self.redis_url != "redis://localhost:6379"
                                                 else "",
            "MAPBOX_ACCESS_TOKEN":               self.mapbox_access_token,
        }

        missing = [name for name, value in required.items() if not value]

        if missing:
            raise ValueError(
                f"\n\n"
                f"╔══════════════════════════════════════════════════════════╗\n"
                f"║   PRODUCTION STARTUP BLOCKED — MISSING ENV VARS          ║\n"
                f"╠══════════════════════════════════════════════════════════╣\n"
                + "".join(f"║   ✗  {name:<52} ║\n" for name in missing)
                + f"╚══════════════════════════════════════════════════════════╝\n"
                f"\n"
                f"Set the above variables in Cloud Run env vars or Secret Manager.\n"
                f"See backend/.env.example for expected formats.\n"
            )

        return self


settings = Settings()