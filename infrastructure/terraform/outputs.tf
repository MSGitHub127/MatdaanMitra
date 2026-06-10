output "backend_url" {
  description = "Public URL of the Cloud Run backend service"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "Public URL of the Cloud Run frontend service"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "artifact_registry_url" {
  description = "Artifact Registry base URL for pushing Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.matdaan.repository_id}"
}

output "backend_service_account" {
  description = "Cloud Run service account email"
  value       = google_service_account.cloud_run_sa.email
}

output "backend_image_uri" {
  description = "Full Docker image URI pattern for backend CI/CD"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.matdaan.repository_id}/backend"
}

output "frontend_image_uri" {
  description = "Full Docker image URI pattern for frontend CI/CD"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.matdaan.repository_id}/frontend"
}

output "next_steps" {
  description = "Post-apply instructions"
  value       = <<-EOT
    ✅ Infrastructure deployed. Next steps:

    1. Update frontend/.firebaserc with project ID: ${var.firebase_project_id}

    2. Run corpus ingestion (from backend/):
         python -m corpus.ingest
         python -m corpus.embed

    3. Push your first images:
         docker build -t ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.matdaan.repository_id}/backend:latest backend/
         docker push ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.matdaan.repository_id}/backend:latest

    4. Deploy frontend to Firebase Hosting:
         cd frontend && firebase deploy --only hosting

    5. Verify health:
         curl ${google_cloud_run_v2_service.backend.uri}/health
  EOT
}
