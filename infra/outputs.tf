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
