locals {
  buckets = {
    data = {
      name                = var.bucket_name
      temporary           = false
      soft_delete_seconds = 604800
    }
    staging = {
      name                = "${var.bucket_name}-staging"
      temporary           = true
      soft_delete_seconds = 0
    }
    temp = {
      name                = "${var.bucket_name}-temp"
      temporary           = true
      soft_delete_seconds = 0
    }
  }
}

resource "google_storage_bucket" "pipeline" {
  for_each = local.buckets

  project                     = local.project_id
  name                        = each.value.name
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels

  soft_delete_policy {
    retention_duration_seconds = each.value.soft_delete_seconds
  }

  dynamic "lifecycle_rule" {
    for_each = each.value.temporary ? [1] : []
    content {
      condition {
        age = 7
      }
      action {
        type = "Delete"
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.required["storage.googleapis.com"]]
}
