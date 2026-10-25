output "function_name" {
  description = "Nom de la fonction (aws lambda invoke --function-name)."
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN de la fonction (Step Functions, EventBridge)."
  value       = aws_lambda_function.this.arn
}

output "role_arn" {
  description = "ARN du rôle d'exécution de la fonction."
  value       = aws_iam_role.this.arn
}

output "log_group" {
  description = "Log group CloudWatch (aws logs tail)."
  value       = aws_cloudwatch_log_group.this.name
}
