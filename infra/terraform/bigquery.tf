resource "google_bigquery_dataset" "lumina" {
  project                    = local.project_id
  dataset_id                 = var.dataset_id
  friendly_name              = "Lumina demo"
  description                = "Datos procesados de DataLandia; homologaciones académicas simuladas."
  location                   = var.region
  delete_contents_on_destroy = false
  max_time_travel_hours      = 48
  labels                     = local.labels

  # Sin expiración automática: preservar los resultados entre pruebas y demo.
  lifecycle {
    prevent_destroy = true
  }

  depends_on = [
    google_project_service.required["bigquery.googleapis.com"],
    google_project_service.required["cloudresourcemanager.googleapis.com"],
  ]
}
