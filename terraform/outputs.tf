output "api_url" {
  value       = google_cloud_run_v2_service.api.uri
  description = "API service URL"
}

output "frontend_url" {
  value       = google_cloud_run_v2_service.frontend.uri
  description = "Frontend service URL"
}

output "db_connection_name" {
  value       = google_sql_database_instance.main.connection_name
  description = "Cloud SQL connection name"
}

output "redis_host" {
  value       = google_redis_instance.cache.host
  description = "Redis host"
}

output "photos_bucket" {
  value       = google_storage_bucket.photos.name
  description = "Photos storage bucket"
}

output "thumbnails_bucket" {
  value       = google_storage_bucket.thumbnails.name
  description = "Thumbnails storage bucket"
}

output "artifact_registry" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/photoai"
  description = "Artifact Registry path"
}
