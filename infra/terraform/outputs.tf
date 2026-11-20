output "project" {
  description = "Destino contrastado con el número de proyecto autorizado."
  value = {
    id     = local.project_id
    number = data.google_project.target.number
    region = var.region
  }
}

output "buckets" {
  description = "Buckets de datos y archivos de ejecución, sin objetos cargados por Terraform."
  value       = { for name, bucket in google_storage_bucket.pipeline : name => bucket.url }
}

output "pubsub" {
  value = {
    topic        = google_pubsub_topic.events.id
    subscription = google_pubsub_subscription.streaming.id
  }
}

output "bigquery_dataset" {
  value = "${local.project_id}.${google_bigquery_dataset.lumina.dataset_id}"
}

output "service_accounts" {
  value = { for name, account in google_service_account.runtime : name => account.email }
}

output "dataflow_runtime" {
  description = "Opciones para futuros scripts; este output no inicia ni impone límites a jobs externos."
  value = {
    project               = local.project_id
    region                = var.region
    service_account_email = google_service_account.runtime["dataflow"].email
    network               = google_compute_network.dataflow.name
    subnetwork            = google_compute_subnetwork.dataflow.self_link
    staging_location      = "${google_storage_bucket.pipeline["staging"].url}/staging"
    temp_location         = "${google_storage_bucket.pipeline["temp"].url}/temp"
    num_workers           = 1
    max_num_workers       = 1
    use_public_ips        = false
  }
}
