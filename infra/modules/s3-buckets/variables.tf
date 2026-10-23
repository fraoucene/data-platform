variable "prefix" {
  description = "Préfixe des noms de buckets, ex. data-platform-dev."
  type        = string
}

variable "suffix" {
  description = "Suffixe garantissant l'unicité globale des noms S3 (account id), passé par le root."
  type        = string
}

variable "names" {
  description = "Noms logiques des buckets à créer. Nom final : <prefix>-<name>-<suffix>."
  type        = list(string)
  default     = ["raw", "processed", "out", "artifacts", "logs"]
}

variable "kms_key_arn" {
  description = "ARN de la clé KMS utilisée pour le chiffrement côté serveur (aws:kms)."
  type        = string
}

variable "expiration_days" {
  description = "Durée de vie (jours) des objets courants, par nom logique. Absent = pas d'expiration."
  type        = map(number)
  default = {
    raw  = 90
    logs = 30
  }
}

variable "noncurrent_days" {
  description = "Jours avant suppression des versions non courantes (bucket versionné)."
  type        = number
  default     = 30
}

variable "logs_bucket" {
  description = "Nom logique du bucket qui reçoit les logs d'accès des autres (doit être dans names)."
  type        = string
  default     = "logs"

  validation {
    condition     = contains(var.names, var.logs_bucket)
    error_message = "logs_bucket doit être l'un des noms de var.names."
  }
}

variable "force_destroy" {
  description = "Autorise terraform destroy à vider le bucket avant suppression. true en dev uniquement."
  type        = bool
  default     = false
}
