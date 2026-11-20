provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "target" {
  project_id = var.project_id

  lifecycle {
    postcondition {
      condition     = tostring(self.number) == var.expected_project_number
      error_message = "El número del proyecto no coincide con el destino autorizado. Revisa project_id y expected_project_number."
    }
  }
}

locals {
  project_id = data.google_project.target.project_id
  labels = {
    project     = "datalandia"
    environment = "demo"
    managed_by  = "terraform"
  }
}
