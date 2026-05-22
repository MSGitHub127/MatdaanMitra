from pydantic_settings import BaseSettings
from pydantic import validator
from cryptography.fernet import Fernet
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Keys that are genuinely required even in development
# (needed for the app to start at all)
HARD_REQUIRED = {"gcp_project_id", "fernet_key", "frontend_url"}

# Keys that are required in production but can be "dummy" in dev
# (the routes that use them will return a clear error if called)
SOFT_REQUIRED = {
    "google_maps_api_key", "google_translate_api_key",
    "vertex_ai_index_id", "vertex_ai_index_endpoint_id",
    "firebase_project_id", "firebase_service_account_path",
    "document_ai_processor_id", "gcs_bucket_name",
}


class Settings(BaseSettings):
    # Google Cloud
    gcp_project_id: str
    gcp_location: str = "asia-south1"
    google_application_credentials: str = ""

    # Vertex AI
    vertex_ai_index_id: str = "dummy"
    vertex_ai_index_endpoint_id: str = "dummy"

    # Google APIs
    google_maps_api_key: str = "dummy"
    mapbox_token: str = "dummy"
    google_translate_api_key: str = "dummy"

    # Mapbox
    mapbox_access_token: str = "dummy"

    # Firebase
    firebase_project_id: str = "dummy"
    firebase_service_account_path: str = "dummy"

    # Document AI
    document_ai_processor_id: str = "dummy"
    document_ai_location: str = "us"

    # App
    redis_url: str = "redis://localhost:6379"
    fernet_key: str
    frontend_url: str = "http://localhost:3000"
    gcs_bucket_name: str = "dummy"
    environment: str = "development"
    log_level: str = "INFO"

    @validator("fernet_key")
    def validate_fernet(cls, v):
        if not v or v.strip() == "":
            key = Fernet.generate_key().decode()
            raise ValueError(
                f"FERNET_KEY is missing. Add this line to your .env:\n"
                f"FERNET_KEY={key}"
            )
        try:
            Fernet(v.encode())
        except Exception:
            raise ValueError(
                "FERNET_KEY is invalid. Generate one with:\n"
                "python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        return v

    @validator("gcp_project_id")
    def validate_project_id(cls, v):
        if not v or v.strip() == "" or v == "dummy":
            raise ValueError(
                "GCP_PROJECT_ID is required. "
                "Find it at: console.cloud.google.com"
            )
        return v

    @property
    def is_dev(self) -> bool:
        return self.environment == "development"

    def check_api_available(self, api_name: str) -> bool:
        """
        Returns True if an API key is set to a real value.
        Use this in service files before making real API calls.
        """
        key_map = {
            "maps":        self.mapbox_token,
            "translate":   self.google_translate_api_key,
            "vertex":      self.vertex_ai_index_id,
            "firebase":    self.firebase_project_id,
            "document_ai": self.document_ai_processor_id,
        }
        val = key_map.get(api_name, "dummy")
        return val not in ("dummy", "", None)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

# Log which APIs are available at startup
if settings.is_dev:
    available = [k for k in ["maps","translate","vertex","firebase","document_ai"]
                 if settings.check_api_available(k)]
    missing   = [k for k in ["maps","translate","vertex","firebase","document_ai"]
                 if not settings.check_api_available(k)]
    if available:
        logger.info(f"APIs available: {available}")
    if missing:
        logger.warning(
            f"APIs not yet configured (using dummy): {missing}. "
            f"These routes will return a clear error if called."
        )
