resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "photoai"
  format        = "DOCKER"
  description   = "PhotoAI container images"

  depends_on = [google_project_service.apis["artifactregistry.googleapis.com"]]
}
