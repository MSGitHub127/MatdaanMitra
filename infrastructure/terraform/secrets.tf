# Secret Manager secrets for Matdaan Mitra

# Gemini API Key
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  replication {
    automatic = true
  }
}

# Secret version for Gemini API Key
resource "google_secret_manager_secret_version" "gemini_api_key_version" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
}

# Mapbox Access Token
resource "google_secret_manager_secret" "mapbox_access_token" {
  secret_id = "mapbox-access-token"
  replication {
    automatic = true
  }
}

# Secret version for Mapbox Access Token
resource "google_secret_manager_secret_version" "mapbox_access_token_version" {
  secret      = google_secret_manager_secret.mapbox_access_token.id
  secret_data = var.mapbox_access_token
}

# Google Translate API Key
resource "google_secret_manager_secret" "google_translate_api_key" {
  secret_id = "google-translate-api-key"
  replication {
    automatic = true
  }
}

# Secret version for Google Translate API Key
resource "google_secret_manager_secret_version" "google_translate_api_key_version" {
  secret      = google_secret_manager_secret.google_translate_api_key.id
  secret_data = var.google_translate_api_key
}

# Firebase Service Account Key (base64 encoded)
resource "google_secret_manager_secret" "firebase_service_account" {
  secret_id = "firebase-service-account"
  replication {
    automatic = true
  }
}

# Secret version for Firebase Service Account
resource "google_secret_manager_secret_version" "firebase_service_account_version" {
  secret      = google_secret_manager_secret.firebase_service_account.id
  secret_data = var.firebase_service_account
}

# Fernet Encryption Key
resource "google_secret_manager_secret" "fernet_key" {
  secret_id = "fernet-encryption-key"
  replication {
    automatic = true
  }
}

# Secret version for Fernet Key
resource "google_secret_manager_secret_version" "fernet_key_version" {
  secret      = google_secret_manager_secret.fernet_key.id
  secret_data = var.fernet_key
}

# Vertex AI Index ID
resource "google_secret_manager_secret" "vertex_ai_index_id" {
  secret_id = "vertex-ai-index-id"
  replication {
    automatic = true
  }
}

# Secret version for Vertex AI Index ID
resource "google_secret_manager_secret_version" "vertex_ai_index_id_version" {
  secret      = google_secret_manager_secret.vertex_ai_index_id.id
  secret_data = var.vertex_ai_index_id
}

# Vertex AI Index Endpoint ID
resource "google_secret_manager_secret" "vertex_ai_index_endpoint_id" {
  secret_id = "vertex-ai-index-endpoint-id"
  replication {
    automatic = true
  }
}

# Secret version for Vertex AI Index Endpoint ID
resource "google_secret_manager_secret_version" "vertex_ai_index_endpoint_id_version" {
  secret      = google_secret_manager_secret.vertex_ai_index_endpoint_id.id
  secret_data = var.vertex_ai_index_endpoint_id
}

# Firebase Project ID
resource "google_secret_manager_secret" "firebase_project_id" {
  secret_id = "firebase-project-id"
  replication {
    automatic = true
  }
}

# Secret version for Firebase Project ID
resource "google_secret_manager_secret_version" "firebase_project_id_version" {
  secret      = google_secret_manager_secret.firebase_project_id.id
  secret_data = var.firebase_project_id
}

# Redis URL
resource "google_secret_manager_secret" "redis_url" {
  secret_id = "redis-url"
  replication {
    automatic = true
  }
}

# Secret version for Redis URL
resource "google_secret_manager_secret_version" "redis_url_version" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = var.redis_url
}
