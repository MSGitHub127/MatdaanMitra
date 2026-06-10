# ─────────────────────────────────────────────────────────────────────────────
# MatdaanMitra — GCP Infrastructure
# Deploys backend (Cloud Run v2) + enables Firebase Hosting for frontend.
# All secrets are stored in Secret Manager and mounted as env vars at runtime.
# ─────────────────────────────────────────────────────────────────────────────

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5"

  # Recommended: store state in GCS so team members share the same state
  # backend "gcs" {
  #   bucket = "matdaan-mitra-terraform-state"
  #   prefix = "terraform/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable required GCP APIs ──────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "firestore.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ── Artifact Registry for Docker images ───────────────────────────────────────

resource "google_artifact_registry_repository" "matdaan" {
  repository_id = "matdaan-mitra"
  format        = "DOCKER"
  location      = var.region
  description   = "MatdaanMitra application Docker images"

  depends_on = [google_project_service.apis]
}

# ── IAM Service Account for Cloud Run ─────────────────────────────────────────

resource "google_service_account" "cloud_run_sa" {
  account_id   = "matdaan-mitra-run"
  display_name = "MatdaanMitra Cloud Run Service Account"
  description  = "Minimal-privilege SA for Cloud Run backend pods"
}

# Allow Cloud Run SA to access Vertex AI
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Allow Cloud Run SA to access Firestore
resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Allow Cloud Run SA to access GCS
resource "google_project_iam_member" "storage_object_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Allow Cloud Run SA to read secrets from Secret Manager
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# ── Backend Cloud Run v2 service ──────────────────────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  name     = "matdaan-mitra-backend"
  location = var.region

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.matdaan,
  ]

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    timeout = "300s"

    containers {
      image = var.backend_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        startup_cpu_boost = true
      }

      # ── Static env vars ───────────────────────────────────────────────────
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
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.firebase_project_id
      }

      # ── Secret Manager env vars ───────────────────────────────────────────
      env {
        name = "SARVAM_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.sarvam_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "MAPBOX_ACCESS_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.mapbox_access_token.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "FERNET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.fernet_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.redis_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "VERTEX_AI_INDEX_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.vertex_ai_index_id.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "VERTEX_AI_INDEX_ENDPOINT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.vertex_ai_index_endpoint_id.secret_id
            version = "latest"
          }
        }
      }

      # Mount Firebase service account JSON as a volume from Secret Manager
      volume_mounts {
        name       = "firebase-sa"
        mount_path = "/app/secrets"
      }

      env {
        name  = "FIREBASE_SERVICE_ACCOUNT_PATH"
        value = "/app/secrets/firebase-admin.json"
      }
    }

    # Volume: Firebase service account secret → file
    volumes {
      name = "firebase-sa"
      secret {
        secret = google_secret_manager_secret.firebase_service_account.secret_id
        items {
          version = "latest"
          path    = "firebase-admin.json"
          mode    = 0444
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Allow unauthenticated invocations (auth handled by Firebase tokens in-app)
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = google_cloud_run_v2_service.backend.project
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Frontend Cloud Run v2 service ─────────────────────────────────────────────

resource "google_cloud_run_v2_service" "frontend" {
  name     = "matdaan-mitra-frontend"
  location = var.region

  depends_on = [google_project_service.apis]

  template {
    scaling {
      min_instance_count = 1
      max_instance_count = var.max_instances
    }

    containers {
      image = var.frontend_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        startup_cpu_boost = true
      }

      env {
        name  = "NODE_ENV"
        value = "production"
      }
      env {
        name  = "NEXT_PUBLIC_BACKEND_URL"
        value = "https://${google_cloud_run_v2_service.backend.uri}"
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = google_cloud_run_v2_service.frontend.project
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
