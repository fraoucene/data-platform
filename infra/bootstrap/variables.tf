variable "region" {
  description = "Région AWS du bucket d'état (même région que infra/)."
  type        = string
  default     = "eu-west-3"
}

variable "profile" {
  description = "Profil AWS CLI (null = chaîne de credentials par défaut)."
  type        = string
  default     = null
}

variable "account_id" {
  description = "Account AWS cible (12 chiffres). Garde-fou allowed_account_ids. Dans local.auto.tfvars, jamais commité."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id doit être un identifiant de compte AWS à 12 chiffres."
  }
}

variable "tags" {
  description = "Tags appliqués à toutes les ressources du bootstrap."
  type        = map(string)
  default = {
    project    = "data-platform"
    component  = "tfstate"
    managed_by = "terraform"
  }
}
