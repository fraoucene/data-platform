variable "prefix" {
  description = "Préfixe des noms de rôles, ex. data-platform-dev."
  type        = string
}

variable "bucket_arns" {
  description = "Map nom logique → ARN des buckets (sortie du module s3-buckets). Clés attendues : raw, processed, out, logs."
  type        = map(string)

  validation {
    condition     = alltrue([for k in ["raw", "processed", "out", "logs"] : contains(keys(var.bucket_arns), k)])
    error_message = "bucket_arns doit contenir les clés raw, processed, out et logs."
  }
}

variable "kms_key_arn" {
  description = "ARN de la clé KMS qui chiffre les buckets : les rôles qui lisent ou écrivent doivent pouvoir l'utiliser."
  type        = string
}

variable "region" {
  description = "Région, pour construire les ARN des fonctions Lambda invocables par Step Functions."
  type        = string
}

variable "account_id" {
  description = "Account id, pour construire les ARN des fonctions Lambda."
  type        = string
}
