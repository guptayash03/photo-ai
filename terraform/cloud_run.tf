locals {
  image_base = "${var.region}-docker.pkg.dev/${var.project_id}/photoai"
  db_url     = "postgresql+asyncpg://${var.db_user}:${var.db_password}@/${var.db_name}?host=/cloudsql/${google_sql_database_instance.main.connection_name}"
  redis_url  = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
}

resource "google_cloud_run_v2_service" "api" {
  name     = "photoai-api"
  location = var.region

  template {
    service_account = google_service_account.api.email

    containers {
      image = "${local.image_base}/api:latest"

      ports {
        container_port = 8000
      }

      env {
        name  = "DATABASE_URL"
        value = local.db_url
      }
      env {
        name  = "REDIS_URL"
        value = local.redis_url
      }
      env {
        name  = "STORAGE_BACKEND"
        value = "gcs"
      }
      env {
        name  = "GCS_BUCKET_PHOTOS"
        value = google_storage_bucket.photos.name
      }
      env {
        name  = "GCS_BUCKET_THUMBNAILS"
        value = google_storage_bucket.thumbnails.name
      }
      env {
        name  = "EMBEDDING_BACKEND"
        value = "vertex_ai"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "ALLOWED_ORIGINS"
        value = "*"
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  depends_on = [google_project_service.apis["run.googleapis.com"]]
}

resource "google_cloud_run_v2_service" "worker" {
  name     = "photoai-worker"
  location = var.region

  template {
    service_account = google_service_account.worker.email

    containers {
      image = "${local.image_base}/worker:latest"

      env {
        name  = "DATABASE_URL"
        value = local.db_url
      }
      env {
        name  = "REDIS_URL"
        value = local.redis_url
      }
      env {
        name  = "STORAGE_BACKEND"
        value = "gcs"
      }
      env {
        name  = "GCS_BUCKET_PHOTOS"
        value = google_storage_bucket.photos.name
      }
      env {
        name  = "GCS_BUCKET_THUMBNAILS"
        value = google_storage_bucket.thumbnails.name
      }
      env {
        name  = "EMBEDDING_BACKEND"
        value = "vertex_ai"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }

      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
        }
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 5
    }
  }

  depends_on = [google_project_service.apis["run.googleapis.com"]]
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = "photoai-frontend"
  location = var.region

  template {
    containers {
      image = "${local.image_base}/frontend:latest"

      ports {
        container_port = 3000
      }

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = google_cloud_run_v2_service.api.uri
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
  }

  depends_on = [google_project_service.apis["run.googleapis.com"]]
}

resource "google_cloud_run_service_iam_member" "api_public" {
  location = google_cloud_run_v2_service.api.location
  service  = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "frontend_public" {
  location = google_cloud_run_v2_service.frontend.location
  service  = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
