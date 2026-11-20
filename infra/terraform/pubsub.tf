resource "google_pubsub_topic" "events" {
  project = local.project_id
  name    = "${var.resource_prefix}-eventos"
  labels  = local.labels

  depends_on = [google_project_service.required["pubsub.googleapis.com"]]
}

resource "google_pubsub_subscription" "streaming" {
  project                    = local.project_id
  name                       = "${var.resource_prefix}-streaming"
  topic                      = google_pubsub_topic.events.id
  ack_deadline_seconds       = 60
  message_retention_duration = "86400s"
  retain_acked_messages      = false
  labels                     = local.labels

  expiration_policy {
    ttl = ""
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "60s"
  }
}
