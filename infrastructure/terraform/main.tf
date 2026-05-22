# Terraform configuration for Matdaan Mitra deployment to GCP

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.0"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud Run service for the backend API
resource "google_cloud_run_service" "matdaan_mitra_backend" {
  name     = "matdaan-mitra-backend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.image_tag}"

        # Environment variables
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        env {
          name  = "LOG_LEVEL"
          value = var.log_level
        }
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "GCP_LOCATION"
          value = var.region
        }
        env {
          name  = "FRONTEND_URL"
          value = var.frontend_url
        }

        # Resource limits
        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
          requests = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }

        # Port configuration
        ports {
          container_port = 8000
        }
      }

      # Scaling configuration
      scaling {
        min_instance_count = var.min_instances
        max_instance_count = var.max_instances
      }

      # Timeout configuration
      timeout_seconds = 300
    }
  }

  # IAM configuration
  traffic {
    percent = 100
  }

  # Deployment policy
  autogenerate_revision_name = true
}

# Allow unauthenticated access to the Cloud Run service
# In production, you would use IAM authentication
resource "google_cloud_run_service_iam_policy" "noauth" {
  location = google_cloud_run_service.matdaan_mitra_backend.location
  project  = google_cloud_run_service.matdaan_mitra_backend.project
  service  = google_cloud_run_service.matdaan_mitra_backend.name

  policy_data = jsonencode({
    bindings = [
      {
        role = "roles/run.invoker",
        members = ["allUsers"]
      }
    ]
  })
}

# Cloud Run service for the frontend (optional, if not using Firebase Hosting)
resource "google_cloud_run_service" "matdaan_mitra_frontend" {
  name     = "matdaan-mitra-frontend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.frontend_image_tag}"

        env {
          name  = "NEXT_PUBLIC_BACKEND_URL"
          value = "https://${google_cloud_run_service.matdaan_mitra_backend.status[0].url}"
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
          requests = {
            cpu    = "250m"
            memory = "256Mi"
          }
        }

        ports {
          container_port = 3000
        }
      }

      scaling {
        min_instance_count = 1
        max_instance_count = 10
      }

      timeout_seconds = 300
    }
  }

  traffic {
    percent = 100
  }

  autogenerate_revision_name = true
}

# Allow unauthenticated access to the frontend
resource "google_cloud_run_service_iam_policy" "frontend_noauth" {
  location = google_cloud_run_service.matdaan_mitra_frontend.location
  project  = google_cloud_run_service.matdaan_mitra_frontend.project
  service  = google_cloud_run_service.matdaan_mitra_frontend.name

  policy_data = jsonencode({
    bindings = [
      {
        role = "roles/run.invoker",
        members = ["allUsers"]
      }
    ]
  })
}
