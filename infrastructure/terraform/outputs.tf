# Outputs for Matdaan Mitra deployment

output "cloud_run_url" {
  description = "URL of the deployed Cloud Run backend service"
  value       = google_cloud_run_service.matdaan_mitra_backend.status[0].url
}

output "frontend_url" {
  description = "URL of the deployed Cloud Run frontend service"
  value       = google_cloud_run_service.matdaan_mitra_frontend.status[0].url
}

output "service_name" {
  description = "Name of the Cloud Run backend service"
  value       = google_cloud_run_service.matdaan_mitra_backend.name
}

output "frontend_service_name" {
  description = "Name of the Cloud Run frontend service"
  value       = google_cloud_run_service.matdaan_mitra_frontend.name
}

output "region" {
  description = "GCP region where services are deployed"
  value       = var.region
}
