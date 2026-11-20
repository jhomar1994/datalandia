terraform {
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }

  # Primera etapa: estado local excluido de Git. Migrar a GCS antes de trabajar
  # desde varios equipos, una vez creado y protegido el bucket del backend.
  backend "local" {
    path = "terraform.tfstate"
  }
}
