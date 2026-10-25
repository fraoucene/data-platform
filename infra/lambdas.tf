# Les Lambdas du projet. Une entrée de local.lambdas = une fonction ; sa clé est le `name` du membre uv
# (lambdas/<dossier>/pyproject.toml), le même que celui du zip dans le bucket artefacts.
# Ajouter une Lambda : créer le membre, `make lambdas-publish LAMBDA=<name>`, puis une entrée ici.

locals {
  artifacts_bucket = "data-platform-artifacts-${data.aws_caller_identity.current.account_id}"

  lambdas = {
    ingest-bodacc = {
      handler     = "ingest_bodacc.handler.lambda_handler"
      timeout     = 300  # une journée se lit en < 10 s ; marge pour les retries du client (jusqu'à ~1 min)
      memory_size = 1024 # mémoire = CPU : la compression gzip va deux fois plus vite qu'à 512 Mo
      environment = { RAW_BUCKET = module.s3.bucket_names["raw"] }
      policy_json = data.aws_iam_policy_document.ingest_bodacc.json
    }
  }
}

# Pointeur publié par make lambdas-publish : quelle version de chaque zip déployer.
data "aws_s3_object" "lambda_pointer" {
  for_each = local.lambdas

  bucket = local.artifacts_bucket
  key    = "lambdas/${each.key}/current.json"
}

module "lambda" {
  source   = "./modules/lambda-python"
  for_each = local.lambdas

  name        = "${local.prefix}-${each.key}"
  handler     = each.value.handler
  timeout     = each.value.timeout
  memory_size = each.value.memory_size
  environment = each.value.environment
  policy_json = each.value.policy_json

  artifact = {
    bucket       = local.artifacts_bucket
    key          = jsondecode(data.aws_s3_object.lambda_pointer[each.key].body).key
    base64sha256 = jsondecode(data.aws_s3_object.lambda_pointer[each.key].body).base64sha256
  }
}

# ---------------------------------------------------------------------------
# Droits propres à chaque Lambda
# ---------------------------------------------------------------------------

# ingest-bodacc : écrit une journée sous raw/bodacc/, rien d'autre (ni lecture, ni liste, ni suppression).
data "aws_iam_policy_document" "ingest_bodacc" {
  statement {
    sid       = "WriteBodaccPartitions"
    actions   = ["s3:PutObject"]
    resources = ["${module.s3.bucket_arns["raw"]}/bodacc/*"]
  }

  # SSE-KMS : GenerateDataKey pour chiffrer chaque objet, Decrypt en plus pour un envoi multipart
  # (upload_file découpe au-delà de 8 Mo et S3 relit les parts chiffrées pour les assembler).
  statement {
    sid       = "UseProjectKey"
    actions   = ["kms:GenerateDataKey", "kms:Decrypt"]
    resources = [module.kms.key_arn]
  }
}
