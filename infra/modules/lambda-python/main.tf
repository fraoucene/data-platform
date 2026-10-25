# Une Lambda Python du projet : son rôle, son log group, la fonction.
# Le même module sert à toutes les Lambdas ; chacune est une entrée de local.lambdas (infra/lambdas.tf).
# Le code n'est jamais lu sur le poste : la fonction pointe vers le zip publié dans le bucket artefacts
# (make lambdas-publish), et source_code_hash déclenche le redéploiement quand le zip change.

# ---------------------------------------------------------------------------
# Rôle d'exécution : un par fonction, avec exactement les droits qu'elle déclare.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = var.name
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

# Logs : seulement dans son propre log group, créé ci-dessous.
# Pas de logs:CreateLogGroup (contrairement à AWSLambdaBasicExecutionRole) : un groupe
# créé par Lambda elle-même échapperait à Terraform (rétention infinie, survit à `make down`).
data "aws_iam_policy_document" "logs" {
  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }
}

resource "aws_iam_role_policy" "logs" {
  name   = "logs"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.logs.json
}

resource "aws_iam_role_policy" "app" {
  name   = "app"
  role   = aws_iam_role.this.id
  policy = var.policy_json
}

# ---------------------------------------------------------------------------
# Log group : créé avant la fonction, avec sa rétention.
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = var.log_retention_days
}

# ---------------------------------------------------------------------------
# Fonction
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "this" {
  function_name = var.name
  role          = aws_iam_role.this.arn
  handler       = var.handler
  runtime       = var.runtime
  architectures = [var.architecture]
  timeout       = var.timeout
  memory_size   = var.memory_size

  s3_bucket        = var.artifact.bucket
  s3_key           = var.artifact.key
  source_code_hash = var.artifact.base64sha256

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.this.name
  }

  environment {
    variables = var.environment
  }

  # Les droits doivent exister avant la première invocation, sinon les premiers logs sont perdus.
  depends_on = [aws_iam_role_policy.logs, aws_iam_role_policy.app]
}

# ---------------------------------------------------------------------------
# Invocations asynchrones : retries après une erreur du handler.
# ---------------------------------------------------------------------------

# Écrit explicitement plutôt que laissé au défaut (2 tentatives, 6 h) : une panne longue se rattrape
# par l'alarme puis `make replay`, pas par des heures de tentatives automatiques.
resource "aws_lambda_function_event_invoke_config" "this" {
  function_name                = aws_lambda_function.this.function_name
  maximum_retry_attempts       = var.async_retry.max_attempts
  maximum_event_age_in_seconds = var.async_retry.max_event_age
}
