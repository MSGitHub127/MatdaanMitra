from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Literal
import os


class Settings(BaseSettings):
    """Application settings with environment variable validation."""

    # Google Cloud
    gcp_project_id: str = Field(..., description="GCP Project ID")
    gcp_location: str = Field(default="asia-south1", description="GCP Region")
    google_application_credentials: str = Field(
        ..., description="Path to service account JSON"
    )

    # Vertex AI
    vertex_ai_index_id: str = Field(..., description="Vector Search Index ID")
    vertex_ai_index_endpoint_id: str = Field(..., description="Vector Search Endpoint ID")

    # Mapbox GL
    mapbox_access_token: str = Field(..., description="Mapbox Access Token")

    # Google Translate
    google_translate_api_key: str = Field(..., description="Google Translate API Key")

    # Firebase Admin
    firebase_project_id: str = Field(..., description="Firebase Project ID")
    firebase_service_account_path: str = Field(
        ..., description="Path to Firebase service account JSON"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")

    # Encryption
    fernet_key: str = Field(..., description="Fernet encryption key")

    # CORS
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend URL for CORS")

    # ECI Corpus
    gcs_bucket_name: str = Field(default="matdaan-eci-corpus", description="GCS bucket for ECI corpus")

    # App
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Log level"
    )

    @validator("google_application_credentials", "firebase_service_account_path")
    def validate_credential_paths(cls, v):
        if not os.path.exists(v):
            raise ValueError(f"Credential file not found: {v}")
        return v

    @validator("fernet_key")
    def validate_fernet_key(cls, v):
        from cryptography.fernet import Fernet
        try:
            Fernet(v.encode())
        except Exception:
            raise ValueError("Invalid Fernet key")
        return v

    @validator("mapbox_access_token")
    def validate_mapbox_token(cls, v):
        if not v.startswith("pk."):
            raise ValueError("Invalid Mapbox token: must start with 'pk.'")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
