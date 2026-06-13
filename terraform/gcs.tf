resource "google_storage_bucket" "photos" {
  name                        = "${var.project_id}-photoai-photos"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  cors {
    origin          = ["*"]
    method          = ["GET", "PUT", "POST"]
    response_header = ["Content-Type", "Content-Disposition"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365
      with_state = "ARCHIVED"
    }
  }
}

resource "google_storage_bucket" "thumbnails" {
  name                        = "${var.project_id}-photoai-thumbnails"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  cors {
    origin          = ["*"]
    method          = ["GET"]
    response_header = ["Content-Type"]
    max_age_seconds = 86400
  }
}
