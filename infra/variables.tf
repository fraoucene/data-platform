variable "region" {
  description = "Région AWS de déploiement."
  type        = string
  default     = "eu-west-3"
}

variable "profile" {
  description = "Profil AWS CLI utilisé par le provider (null = chaîne de credentials par défaut, ex. CI)."
  type        = string
  default     = null
}

variable "environment" {
  description = "Environnement cible (dev, prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment doit valoir \"dev\" ou \"prod\"."
  }
}

variable "tags" {
  description = "Tags appliqués par défaut à toutes les ressources (default_tags du provider)."
  type        = map(string)
  default = {
    project = "data-platform"
  }

  validation {
    condition     = lookup(var.tags, "project", "") == "data-platform"
    error_message = "tags doit contenir la clé \"project\" avec la valeur \"data-platform\" (tag obligatoire pour le suivi des coûts et le budget)."
  }
}

variable "alert_email" {
  description = "Email destinataire des alertes (budget, alarmes). Pas de défaut : passer via -var ou TF_VAR_alert_email, ne jamais commiter."
  type        = string
  sensitive   = false

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email doit être une adresse email valide."
  }
}

variable "budget_limit_usd" {
  description = "Plafond mensuel du budget AWS en USD."
  type        = number
  default     = 35

  validation {
    condition     = var.budget_limit_usd > 0
    error_message = "budget_limit_usd doit être strictement positif."
  }
}
