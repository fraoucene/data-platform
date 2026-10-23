# Bootstrap : le bucket qui stockera l'état Terraform du root infra/.
# Ce root a un état LOCAL (infra/bootstrap/terraform.tfstate, gitignoré) et
# ne doit quasiment jamais changer. Verrou d'état : lockfile natif S3
# (use_lockfile = true côté backend), donc pas de table DynamoDB.

data "aws_caller_identity" "current" {}

locals {
  account_id   = data.aws_caller_identity.current.account_id
  state_bucket = "data-platform-tfstate-${local.account_id}"
}

resource "aws_s3_bucket" "tfstate" {
  bucket = local.state_bucket

  # L'état ne doit jamais être détruit par accident.
  lifecycle {
    prevent_destroy = true
  }
}

# Versioning : chaque apply écrit une nouvelle version de l'état,
# les précédentes restent récupérables.
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Chiffrement AES256 géré par S3 (pas KMS : la clé KMS du projet sera
# créée PAR l'état que ce bucket stocke, dépendance circulaire sinon).
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Aucun accès public possible, quelle que soit la policy ou l'ACL.
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
