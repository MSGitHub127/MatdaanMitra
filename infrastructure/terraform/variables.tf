variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "firebase_project_id" {
  description = "Firebase Project ID (may differ from GCP project ID)"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "asia-south1"
}

# NOTE: image tags are intentionally left without defaults so Terraform
# errors clearly if CI/CD forgets to pass them.
variable "backend_image" {
  description = "Fully-qualified Docker image URI for the backend service"
  type        = string
  # e.g. asia-south1-docker.pkg.dev/my-project/matdaan-mitra/backend:abc1234
}

variable "frontend_image" {
  description = "Fully-qualified Docker image URI for the frontend service"
  type        = string
  # e.g. asia-south1-docker.pkg.dev/my-project/matdaan-mitra/frontend:abc1234
}

variable "environment" {
  description = "Deployment environment label"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "environment must be one of: development, staging, production"
  }
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "frontend_url" {
  description = "Public frontend URL — used in CORS allow-list"
  type        = string
  default     = "https://matdaan-mitra.web.app"
}

variable "min_instances" {
  description = "Minimum Cloud Run instances (0 = scale to zero, 1+ = always warm)"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum Cloud Run instances"
  type        = number
  default     = 50
}

# ── Secrets (stored in Secret Manager, not in state) ─────────────────────────

variable "sarvam_api_key" {
  description = "Sarvam AI API key (translation + TTS)"
  type        = string
  sensitive   = true
}

variable "mapbox_access_token" {
  description = "Mapbox public access token"
  type        = string
  sensitive   = true
}

variable "fernet_key" {
  description = "Fernet encryption key for EPIC number encryption"
  type        = string
  sensitive   = true
}

variable "firebase_service_account_json" {
  description = "Firebase Admin SDK service account JSON (full file contents)"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis connection URL (Upstash or Memorystore)"
  type        = string
  sensitive   = true
  default     = "redis://localhost:6379"
}

variable "vertex_ai_index_id" {
  description = "Vertex AI Matching Engine index ID"
  type        = string
  default     = ""
}

variable "vertex_ai_index_endpoint_id" {
  description = "Vertex AI Matching Engine index endpoint resource name"
  type        = string
  default     = ""
}
