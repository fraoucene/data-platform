output "state_bucket" {
  description = "Nom du bucket S3 qui stocke l'état Terraform de infra/."
  value       = aws_s3_bucket.tfstate.bucket
}

output "region" {
  description = "Région du bucket d'état, à reporter dans infra/backend.hcl."
  value       = var.region
}
