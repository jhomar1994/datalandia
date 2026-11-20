variable "project_id" {
  description = "Project ID de GCP donde se crearán los recursos."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Usa un Project ID válido, no el nombre visible ni el número del proyecto."
  }
}

variable "expected_project_number" {
  description = "Número del proyecto autorizado, contrastado con Google Cloud durante el plan."
  type        = string
  default     = "637872675138"

  validation {
    condition     = can(regex("^[0-9]+$", var.expected_project_number))
    error_message = "El número de proyecto debe contener únicamente dígitos."
  }
}

variable "region" {
  description = "Región común a buckets, BigQuery y subred de la demostración."
  type        = string
  default     = "us-central1"

  validation {
    condition     = var.region == "us-central1"
    error_message = "Esta configuración de demostración está dimensionada para us-central1."
  }
}

variable "bucket_name" {
  description = "Nombre global único del bucket principal; staging y temp usan ese nombre como prefijo."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,53}[a-z0-9]$", var.bucket_name))
    error_message = "Usa entre 3 y 55 caracteres en minúsculas, números y guiones; se reserva espacio para sufijos."
  }
}

variable "dataset_id" {
  description = "Dataset BigQuery de la demostración."
  type        = string
  default     = "lumina_demo"

  validation {
    condition     = can(regex("^[A-Za-z_][A-Za-z0-9_]*$", var.dataset_id)) && length(var.dataset_id) <= 1024
    error_message = "El dataset debe usar letras, números y guiones bajos."
  }
}

variable "resource_prefix" {
  description = "Prefijo de red, mensajería y cuentas de servicio."
  type        = string
  default     = "lumina"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,15}[a-z0-9]$", var.resource_prefix))
    error_message = "Usa entre 3 y 17 caracteres en minúsculas, números y guiones."
  }
}

variable "subnet_cidr" {
  description = "Rango privado reservado para futuros workers de Dataflow."
  type        = string
  default     = "10.42.0.0/24"

  validation {
    condition     = can(cidrnetmask(var.subnet_cidr)) && can(regex("^(10\\.|192\\.168\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.)", var.subnet_cidr)) && can(regex("/(1[6-9]|2[0-8])$", var.subnet_cidr))
    error_message = "Usa una subred IPv4 privada RFC1918 con prefijo entre /16 y /28."
  }
}
