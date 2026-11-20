resource "google_workflows_workflow" "verify" {
  project             = local.project_id
  region              = var.region
  name                = "${var.resource_prefix}-verificar"
  description         = "Conteos de calidad y cruces Gold de Lumina, bajo demanda."
  service_account     = google_service_account.runtime["workflow"].name
  source_contents     = file("${path.module}/../../workflows/verificar.yaml")
  deletion_protection = true
  labels              = local.labels

  depends_on = [
    google_project_service.required["workflows.googleapis.com"],
    google_bigquery_table.zone_gold,
    google_project_iam_member.runtime,
    google_bigquery_dataset_iam_member.runtime,
  ]
}
