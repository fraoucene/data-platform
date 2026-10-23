output "key_arn" {
  description = "ARN de la clé, à passer aux ressources qui chiffrent (S3, rôles IAM)."
  value       = aws_kms_key.this.arn
}

output "key_id" {
  description = "ID de la clé."
  value       = aws_kms_key.this.key_id
}

output "alias_name" {
  description = "Nom de l'alias (alias/<name>)."
  value       = aws_kms_alias.this.name
}
