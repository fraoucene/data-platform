output "lambda_role_arn" {
  description = "ARN du rôle d'exécution des Lambdas (lit raw, écrit processed)."
  value       = aws_iam_role.lambda.arn
}

output "emr_role_arn" {
  description = "ARN du service role EMR (lit raw/processed, écrit processed/out/logs)."
  value       = aws_iam_role.emr.arn
}

output "sfn_role_arn" {
  description = "ARN du rôle Step Functions (invoque les Lambdas du projet)."
  value       = aws_iam_role.sfn.arn
}
