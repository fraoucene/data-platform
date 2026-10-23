output "budget_topic_arn" {
  description = "ARN du topic SNS recevant les alertes de budget."
  value       = aws_sns_topic.budget_alerts.arn
}

output "budget_name" {
  description = "Nom du budget mensuel AWS Budgets."
  value       = aws_budgets_budget.monthly_cost.name
}

output "budget_subscription_arn" {
  description = "ARN de l'abonnement email (\"PendingConfirmation\" tant que le lien du mail n'est pas cliqué)."
  value       = aws_sns_topic_subscription.budget_alerts_email.arn
}

output "kms_key_arn" {
  description = "ARN de la clé KMS du projet (module kms)."
  value       = module.kms.key_arn
}

output "kms_alias" {
  description = "Alias de la clé KMS du projet."
  value       = module.kms.alias_name
}

output "bucket_names" {
  description = "Map nom logique → nom réel des buckets (module s3-buckets)."
  value       = module.s3.bucket_names
}

output "bucket_arns" {
  description = "Map nom logique → ARN des buckets (module s3-buckets)."
  value       = module.s3.bucket_arns
}

output "lambda_role_arn" {
  description = "ARN du rôle d'exécution Lambda (module iam)."
  value       = module.iam.lambda_role_arn
}

output "emr_role_arn" {
  description = "ARN du service role EMR (module iam)."
  value       = module.iam.emr_role_arn
}

output "sfn_role_arn" {
  description = "ARN du rôle Step Functions (module iam)."
  value       = module.iam.sfn_role_arn
}
