variable "name" {
  description = "Nom de la fonction, du rôle et du log group, ex. data-platform-dev-ingest-bodacc."
  type        = string
}

variable "handler" {
  description = "Chemin Python du handler dans le zip, ex. ingest_bodacc.handler.lambda_handler."
  type        = string
}

variable "artifact" {
  description = "Zip publié par make lambdas-publish : bucket, clé et base64sha256 (lus dans le pointeur current.json)."
  type = object({
    bucket       = string
    key          = string
    base64sha256 = string
  })
}

variable "policy_json" {
  description = "Politique IAM propre à la fonction (ce qu'elle lit et écrit), en JSON. Les logs sont ajoutés par le module."
  type        = string
}

variable "environment" {
  description = "Variables d'environnement de la fonction."
  type        = map(string)
  default     = {}
}

variable "runtime" {
  description = "Runtime Lambda : doit correspondre à PYTHON_VERSION de infra/scripts/build_lambda.py."
  type        = string
  default     = "python3.12"
}

variable "architecture" {
  description = "arm64 (Graviton, ~20 % moins cher) : doit correspondre à PLATFORM de infra/scripts/build_lambda.py."
  type        = string
  default     = "arm64"

  validation {
    condition     = contains(["arm64", "x86_64"], var.architecture)
    error_message = "architecture doit valoir arm64 ou x86_64."
  }
}

variable "timeout" {
  description = "Durée maximale d'une invocation, en secondes (défaut Lambda : 3 s)."
  type        = number
  default     = 60
}

variable "memory_size" {
  description = "Mémoire en Mo ; le CPU alloué est proportionnel."
  type        = number
  default     = 512
}

variable "log_retention_days" {
  description = "Rétention des logs CloudWatch, en jours."
  type        = number
  default     = 14
}
