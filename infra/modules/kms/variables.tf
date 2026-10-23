variable "name" {
  description = "Nom logique de la clé, utilisé pour l'alias (alias/<name>)."
  type        = string
}

variable "description" {
  description = "Description affichée dans la console KMS."
  type        = string
  default     = "Clé de chiffrement data-platform"
}

variable "deletion_window_in_days" {
  description = "Délai entre la demande de suppression et la suppression effective (7 à 30 jours)."
  type        = number
  default     = 7

  validation {
    condition     = var.deletion_window_in_days >= 7 && var.deletion_window_in_days <= 30
    error_message = "deletion_window_in_days doit être compris entre 7 et 30."
  }
}
