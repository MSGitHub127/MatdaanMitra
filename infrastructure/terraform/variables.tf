# Variables for Matdaan Mitra deployment

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region for deployment"
  type        = string
  default     = "asia-south1"
}

variable "image_tag" {
  description = "Docker image tag for the backend service"
  type        = string
  default     = "gcr.io/${var.project_id}/matdaan-mitra-backend:latest"
}

variable "frontend_image_tag" {
  description = "Docker image tag for the frontend service"
  type        = string
  default     = "gcr.io/${var.project_id}/matdaan-mitra-frontend:latest"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "frontend_url" {
  description = "Frontend URL for CORS configuration"
  type        = string
  default     = "https://matdaan-mitra.web.app"
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 2
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 100
}
