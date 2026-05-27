"""
settings.py — Centralised application configuration

All secrets and environment variables are loaded here via Pydantic Settings.
This replaces the previous version which had no sarvam_api_key field,
causing a NameError when translator.py tried to access it.

Required additions to backend/.env:
  SARVAM_API_KEY=your-sarvam-api-key

The Google Cloud Translation fields have been removed — Sarvam AI is
now the sole language/translation provider per the project specification.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── GCP ────────────────────────────────────────────────────────────────
    gcp_project_id:  str = ""
    gcp_location:    str = "asia-south1"

    # ── Vertex AI (RAG + Gemini) ───────────────────────────────────────────
    vertex_ai_index_id:          str = ""
    vertex_ai_index_endpoint_id: str = ""

    # ── Language & Voice — Sarvam AI ──────────────────────────────────────
    sarvam_api_key: str = ""

    # ── Geospatial — Mapbox ────────────────────────────────────────────────
    mapbox_access_token: str = ""

    # ── Firebase ──────────────────────────────────────────────────────────
    firebase_project_id:          str = ""
    firebase_service_account_path: str = ""

    # ── Infrastructure ────────────────────────────────────────────────────
    redis_url:       str = "redis://localhost:6379"
    gcs_bucket_name: str = "matdaan-eci-corpus"

    # ── Security ──────────────────────────────────────────────────────────
    fernet_key: str = ""

    # ── App ───────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"
    environment:  str = "development"
    log_level:    str = "INFO"


settings = Settings()