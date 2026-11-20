resource "google_compute_network" "dataflow" {
  project                 = local.project_id
  name                    = "${var.resource_prefix}-dataflow-net"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  description             = "Red de workers Dataflow de la demostración Lumina."

  depends_on = [google_project_service.required["compute.googleapis.com"]]
}

resource "google_compute_subnetwork" "dataflow" {
  project                  = local.project_id
  name                     = "${var.resource_prefix}-dataflow-subnet"
  region                   = var.region
  network                  = google_compute_network.dataflow.id
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true
}

resource "google_compute_firewall" "worker_internal" {
  project                 = local.project_id
  name                    = "${var.resource_prefix}-dataflow-workers"
  network                 = google_compute_network.dataflow.name
  direction               = "INGRESS"
  description             = "Comunicación Dataflow entre workers de la misma identidad."
  source_service_accounts = [google_service_account.runtime["dataflow"].email]
  target_service_accounts = [google_service_account.runtime["dataflow"].email]

  allow {
    protocol = "tcp"
    ports    = ["12345", "12346"]
  }
}
