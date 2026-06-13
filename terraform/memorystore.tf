resource "google_redis_instance" "cache" {
  name           = "photoai-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  authorized_network = google_compute_network.vpc.id
  connect_mode       = "DIRECT_PEERING"

  redis_version = "REDIS_7_0"

  depends_on = [google_project_service.apis["redis.googleapis.com"]]
}
