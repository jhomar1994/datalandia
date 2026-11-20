locals {
  tables = {
    viajes_staging = {
      partition  = "processed_at"
      clustering = ["batch_id", "origin_id"]
    }
    viajes_validos = {
      partition  = "pickup_local"
      clustering = ["trip_id", "origin_id"]
    }
    sensores_validos = {
      partition  = "event_ts"
      clustering = ["zone_id", "node_id", "sensor", "parameter"]
    }
    rechazados_raw = {
      partition  = "processed_at"
      clustering = ["source", "reason"]
    }
    puente_batch    = { partition = null, clustering = [] }
    puente_stream   = { partition = null, clustering = [] }
    referencia_zona = { partition = null, clustering = [] }
  }
  base_views    = toset(["conflictos_sensores", "rechazados", "gold_movilidad_5min"])
  sql_directory = "${path.module}/../../sql/bigquery"
}

resource "google_bigquery_table" "data" {
  for_each = local.tables

  project             = local.project_id
  dataset_id          = google_bigquery_dataset.lumina.dataset_id
  table_id            = each.key
  schema              = file("${path.module}/../../schemas/bigquery/${each.key}.json")
  clustering          = each.value.clustering
  deletion_protection = true
  labels              = local.labels

  dynamic "time_partitioning" {
    for_each = each.value.partition == null ? [] : [each.value.partition]
    content {
      type  = "DAY"
      field = time_partitioning.value
    }
  }
}

resource "google_bigquery_table" "base_view" {
  for_each = local.base_views

  project             = local.project_id
  dataset_id          = google_bigquery_dataset.lumina.dataset_id
  table_id            = each.key
  deletion_protection = true
  labels              = local.labels

  view {
    use_legacy_sql = false
    query = replace(replace(file("${local.sql_directory}/${each.key}.sql"),
    "__PROJECT__", local.project_id), "__DATASET__", var.dataset_id)
  }

  depends_on = [google_bigquery_table.data]
}

resource "google_bigquery_table" "sensor_gold" {
  project             = local.project_id
  dataset_id          = google_bigquery_dataset.lumina.dataset_id
  table_id            = "gold_sensores_5min"
  deletion_protection = true
  labels              = local.labels

  view {
    use_legacy_sql = false
    query = replace(replace(file("${local.sql_directory}/gold_sensores_5min.sql"),
    "__PROJECT__", local.project_id), "__DATASET__", var.dataset_id)
  }

  depends_on = [google_bigquery_table.base_view]
}

resource "google_bigquery_table" "zone_gold" {
  project             = local.project_id
  dataset_id          = google_bigquery_dataset.lumina.dataset_id
  table_id            = "gold_zona_5min"
  deletion_protection = true
  labels              = local.labels

  view {
    use_legacy_sql = false
    query = replace(replace(file("${local.sql_directory}/gold_zona_5min.sql"),
    "__PROJECT__", local.project_id), "__DATASET__", var.dataset_id)
  }

  depends_on = [google_bigquery_table.sensor_gold]
}
