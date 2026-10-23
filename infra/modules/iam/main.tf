# Trois rôles de service, un par type d'exécutant de la plateforme.
# Un rôle = (1) une trust policy : QUI peut l'endosser (ici un service AWS),
#         + (2) des permissions : CE QU'IL peut faire une fois endossé.
# Moindre privilège S3 : deux ARN par bucket, le bucket lui-même pour
# ListBucket, et `<arn>/*` pour les objets (GetObject, PutObject).

locals {
  # ARN "objets" dérivés des ARN de buckets.
  objects = { for k, arn in var.bucket_arns : k => "${arn}/*" }

  kms_actions = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
}

# ---------------------------------------------------------------------------
# Trust policies : qui peut assumer chaque rôle.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "assume_emr" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["elasticmapreduce.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "assume_sfn" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

# ---------------------------------------------------------------------------
# Rôle Lambda : lit raw, écrit processed, logs CloudWatch.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "lambda" {
  name               = "${var.prefix}-lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

# Policy managée AWS : écrire dans CloudWatch Logs, rien d'autre.
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda" {
  statement {
    sid       = "ListBuckets"
    actions   = ["s3:ListBucket"]
    resources = [var.bucket_arns["raw"], var.bucket_arns["processed"]]
  }

  statement {
    sid       = "ReadRaw"
    actions   = ["s3:GetObject"]
    resources = [local.objects["raw"]]
  }

  statement {
    sid       = "WriteProcessed"
    actions   = ["s3:PutObject"]
    resources = [local.objects["processed"]]
  }

  statement {
    sid       = "UseProjectKey"
    actions   = local.kms_actions
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "s3-kms"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda.json
}

# ---------------------------------------------------------------------------
# Rôle EMR (service role) : lit raw + processed, écrit processed + out + logs.
# L'instance profile EC2 viendra avec le premier cluster.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "emr" {
  name               = "${var.prefix}-emr"
  assume_role_policy = data.aws_iam_policy_document.assume_emr.json
}

data "aws_iam_policy_document" "emr" {
  statement {
    sid     = "ListBuckets"
    actions = ["s3:ListBucket"]
    resources = [
      var.bucket_arns["raw"], var.bucket_arns["processed"],
      var.bucket_arns["out"], var.bucket_arns["logs"],
    ]
  }

  statement {
    sid       = "Read"
    actions   = ["s3:GetObject"]
    resources = [local.objects["raw"], local.objects["processed"]]
  }

  statement {
    sid       = "Write"
    actions   = ["s3:PutObject"]
    resources = [local.objects["processed"], local.objects["out"], local.objects["logs"]]
  }

  statement {
    sid       = "UseProjectKey"
    actions   = local.kms_actions
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "emr" {
  name   = "s3-kms"
  role   = aws_iam_role.emr.id
  policy = data.aws_iam_policy_document.emr.json
}

# ---------------------------------------------------------------------------
# Rôle Step Functions : invoque les Lambdas du projet, rien d'autre.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "sfn" {
  name               = "${var.prefix}-sfn"
  assume_role_policy = data.aws_iam_policy_document.assume_sfn.json
}

data "aws_iam_policy_document" "sfn" {
  statement {
    sid       = "InvokeProjectLambdas"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.region}:${var.account_id}:function:${var.prefix}-*"]
  }
}

resource "aws_iam_role_policy" "sfn" {
  name   = "invoke-lambda"
  role   = aws_iam_role.sfn.id
  policy = data.aws_iam_policy_document.sfn.json
}
