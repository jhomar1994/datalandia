variable "api_image" {
  description = "Imagen construida para la API; null prepara solo el repositorio y los permisos."
  type        = string
  default     = null

  validation {
    condition     = var.api_image == null || can(regex("^us-central1-docker\\.pkg\\.dev/", var.api_image))
    error_message = "Usa una imagen de Artifact Registry en us-central1."
  }
}

resource "google_artifact_registry_repository" "images" {
  project       = local.project_id
  location      = var.region
  repository_id = "${var.resource_prefix}-images"
  description   = "Imagen de la API y consumidor de Lumina"
  format        = "DOCKER"
  labels        = local.labels

  depends_on = [google_project_service.required["artifactregistry.googleapis.com"]]
}

resource "google_artifact_registry_repository_iam_member" "builder" {
  project    = local.project_id
  location   = var.region
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.runtime["build"].email}"
}

resource "google_storage_bucket_iam_member" "build_source" {
  bucket = google_storage_bucket.pipeline["staging"].name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.runtime["build"].email}"
}

resource "google_cloud_run_v2_service" "api" {
  count = var.api_image == null ? 0 : 1

  project             = local.project_id
  name                = "${var.resource_prefix}-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true
  labels              = local.labels

  scaling {
    min_instance_count = 0
    max_instance_count = 1
  }

  template {
    service_account                  = google_service_account.runtime["api"].email
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN1"
    max_instance_request_concurrency = 1
    timeout                          = "30s"

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = var.api_image
      resources {
        limits = {
          cpu    = "0.25"
          memory = "256Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = false
      }
      ports {
        container_port = 8080
      }
      env {
        name  = "LUMINA_PROJECT_ID"
        value = local.project_id
      }
      env {
        name  = "LUMINA_DATASET"
        value = var.dataset_id
      }
      env {
        name  = "LUMINA_REGION"
        value = var.region
      }
      env {
        name  = "LUMINA_MAX_BYTES_BILLED"
        value = "134217728"
      }
      startup_probe {
        period_seconds    = 5
        timeout_seconds   = 2
        failure_threshold = 20
        http_get {
          path = "/health"
        }
      }
    }
  }

  # Sin binding allUsers: las invocaciones requieren IAM.
  depends_on = [
    google_project_service.required["run.googleapis.com"],
    google_bigquery_dataset_iam_member.runtime,
    google_project_iam_member.runtime,
  ]
}

output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${local.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "api_url" {
  value = try(google_cloud_run_v2_service.api[0].uri, null)
}
