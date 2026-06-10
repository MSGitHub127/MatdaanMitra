# Secret Manager secrets for MatdaanMitra
# All secrets are created here and referenced from main.tf via secret_key_ref.
# Secret VALUES are populated from Terraform variables (never hardcoded).

# ── Sarvam AI (translation + TTS) — replaces Google Translate ────────────────

resource "google_secret_manager_secret" "sarvam_api_key" {
  secret_id = "sarvam-api-key"
  replication {
  auto {}
}
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "sarvam_api_key" {
  secret      = google_secret_manager_secret.sarvam_api_key.id
  secret_data = var.sarvam_api_key
}

# ── Mapbox ────────────────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "mapbox_access_token" {
  secret_id = "mapbox-access-token"
  replication {
  auto {}
}
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "mapbox_access_token" {
  secret      = google_secret_manager_secret.mapbox_access_token.id
  secret_data = var.mapbox_access_token
}

# ── Firebase service account (mounted as /app/secrets/firebase-admin.json) ───

resource "google_secret_manager_secret" "firebase_service_account" {
  secret_id = "firebase-service-account"
  replication {
  auto {}
}
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "firebase_service_account" {
  secret      = google_secret_manager_secret.firebase_service_account.id
  secret_data = var.firebase_service_account_json
}

# ── Fernet encryption key ─────────────────────────────────────────────────────

resource "google_secret_manager_secret" "fernet_key" {
  secret_id = "fernet-encryption-key"
  replication {
  auto {}
}
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "fernet_key" {
  secret      = google_secret_manager_secret.fernet_key.id
  secret_data = var.fernet_key
}

# ── Redis URL ─────────────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "redis-url"
  replication {
  auto {}
}
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = var.redis_url
}

# ── Vertex AI ─────────────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "vertex_ai_index_id" {
  secret_id = "vertex-ai-index-id"
  replication {
  auto {}
}
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "vertex_ai_index_id" {
  secret      = google_secret_manager_secret.vertex_ai_index_id.id
  secret_data = var.vertex_ai_index_id
}

resource "google_secret_manager_secret" "vertex_ai_index_endpoint_id" {
  secret_id = "vertex-ai-index-endpoint-id"
  replication {
  auto {}
}
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "vertex_ai_index_endpoint_id" {
  secret      = google_secret_manager_secret.vertex_ai_index_endpoint_id.id
  secret_data = var.vertex_ai_index_endpoint_id
}
