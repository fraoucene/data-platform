output "state_bucket" {
  description = "Nom du bucket S3 qui stocke l'état Terraform de infra/."
  value       = aws_s3_bucket.tfstate.bucket
}

output "region" {
  description = "Région du bucket d'état, à reporter dans infra/backend.hcl."
  value       = var.region
}

output "artifacts_bucket" {
  description = "Nom du bucket des artefacts de déploiement (zips de Lambda), partagé par les environnements du compte."
  value       = aws_s3_bucket.artifacts.bucket
}
