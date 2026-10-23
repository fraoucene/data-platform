# Logs d'accès S3 : chaque bucket (sauf `logs` lui-même) écrit ses logs
# d'accès dans le bucket `logs`, sous le préfixe s3/<nom>/.
# Deux ressources : la policy qui autorise le service de logging à écrire
# dans `logs`, puis l'activation du logging sur chaque bucket source.

data "aws_caller_identity" "current" {}

locals {
  logs_bucket   = aws_s3_bucket.this[var.logs_bucket]
  logged_bucket = { for k, b in aws_s3_bucket.this : k => b if k != var.logs_bucket }
}

# Qui a le droit d'écrire dans `logs` : le service de logging S3, uniquement
# pour des logs provenant de ce compte (condition aws:SourceAccount).
data "aws_iam_policy_document" "logs" {
  statement {
    sid     = "S3ServerAccessLogsPolicy"
    effect  = "Allow"
    actions = ["s3:PutObject"]

    principals {
      type        = "Service"
      identifiers = ["logging.s3.amazonaws.com"]
    }

    resources = ["${local.logs_bucket.arn}/s3/*"]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = local.logs_bucket.id
  policy = data.aws_iam_policy_document.logs.json

  # La policy ne peut être posée qu'une fois l'accès public bloqué configuré.
  depends_on = [aws_s3_bucket_public_access_block.this]
}

# Activation du logging sur chaque bucket source.
resource "aws_s3_bucket_logging" "this" {
  for_each = local.logged_bucket

  bucket        = each.value.id
  target_bucket = local.logs_bucket.id
  target_prefix = "s3/${each.key}/"

  # S3 vérifie les droits du bucket cible à l'activation : la policy d'abord.
  depends_on = [aws_s3_bucket_policy.logs]
}
