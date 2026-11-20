locals {
  service_accounts = {
    dataflow  = "Workers Dataflow de Lumina"
    api       = "Consulta de indicadores de Lumina"
    workflow  = "Orquestación y verificación de Lumina"
    publisher = "Productor de eventos de Lumina"
    build     = "Construcción de la API de Lumina"
  }
  project_roles = {
    worker            = { account = "dataflow", role = "roles/dataflow.worker" }
    worker_queries    = { account = "dataflow", role = "roles/bigquery.jobUser" }
    worker_logs       = { account = "dataflow", role = "roles/logging.logWriter" }
    worker_metrics    = { account = "dataflow", role = "roles/monitoring.metricWriter" }
    api_queries       = { account = "api", role = "roles/bigquery.jobUser" }
    workflow_queries  = { account = "workflow", role = "roles/bigquery.jobUser" }
    workflow_dataflow = { account = "workflow", role = "roles/dataflow.developer" }
    build_logs        = { account = "build", role = "roles/logging.logWriter" }
  }
  dataset_roles = {
    dataflow = "roles/bigquery.dataEditor"
    api      = "roles/bigquery.dataViewer"
    workflow = "roles/bigquery.dataViewer"
  }
}

resource "google_service_account" "runtime" {
  for_each = local.service_accounts

  project      = local.project_id
  account_id   = "${var.resource_prefix}-${each.key}"
  display_name = each.value

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

# Recursos IAM aditivos: no reemplazan las políticas completas del proyecto.
resource "google_project_iam_member" "runtime" {
  for_each = local.project_roles

  project = local.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.runtime[each.value.account].email}"

  depends_on = [google_project_service.required]
}

resource "google_bigquery_dataset_iam_member" "runtime" {
  for_each = local.dataset_roles

  project    = local.project_id
  dataset_id = google_bigquery_dataset.lumina.dataset_id
  role       = each.value
  member     = "serviceAccount:${google_service_account.runtime[each.key].email}"
}

resource "google_storage_bucket_iam_member" "worker" {
  for_each = local.buckets

  bucket = google_storage_bucket.pipeline[each.key].name
  role   = each.key == "data" ? "roles/storage.objectViewer" : "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime["dataflow"].email}"
}

resource "google_storage_bucket_iam_member" "workflow_templates" {
  bucket = google_storage_bucket.pipeline["staging"].name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.runtime["workflow"].email}"
}

resource "google_pubsub_subscription_iam_member" "worker" {
  project      = local.project_id
  subscription = google_pubsub_subscription.streaming.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.runtime["dataflow"].email}"
}

# Subscriber permite consumir, pero Dataflow también consulta la configuración.
resource "google_pubsub_subscription_iam_member" "worker_metadata" {
  project      = local.project_id
  subscription = google_pubsub_subscription.streaming.name
  role         = "roles/pubsub.viewer"
  member       = "serviceAccount:${google_service_account.runtime["dataflow"].email}"
}

resource "google_pubsub_topic_iam_member" "publisher" {
  project = local.project_id
  topic   = google_pubsub_topic.events.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.runtime["publisher"].email}"
}

resource "google_service_account_iam_member" "workflow_worker" {
  service_account_id = google_service_account.runtime["dataflow"].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.runtime["workflow"].email}"
}

resource "google_compute_subnetwork_iam_member" "runtime" {
  for_each = toset(["dataflow", "workflow"])

  project    = local.project_id
  region     = var.region
  subnetwork = google_compute_subnetwork.dataflow.name
  role       = "roles/compute.networkUser"
  member     = "serviceAccount:${google_service_account.runtime[each.value].email}"
}
