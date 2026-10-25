# Bucket des artefacts de déploiement : zips de Lambda (S1-07), puis jars et scripts de jobs.
# Ici et non dans infra/ : ce qui sert à reconstruire un environnement ne doit pas être détruit
# avec lui. `make down` détruit infra/ ; les zips doivent survivre pour que `make up` redéploie.
# Un bucket par compte, partagé par les environnements de ce compte.
# Chiffrement SSE-S3 et non KMS : la clé KMS du projet vit dans infra/ (détruite au `make down`),
# et Lambda lit le zip avec les droits de celui qui déploie, sans passer par une clé à autoriser.

locals {
  artifacts_bucket = "data-platform-artifacts-${local.account_id}"
}

resource "aws_s3_bucket" "artifacts" {
  bucket = local.artifacts_bucket

  tags = { component = "artifacts" }

  lifecycle {
    prevent_destroy = true
  }
}

# Les clés sont adressées par leur contenu (lambdas/<nom>/<sha256>.zip) : un zip n'est jamais réécrit.
# Seul le pointeur current.json change ; le versioning garde ses valeurs précédentes (retour arrière).
resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Pas d'expiration des objets courants : un zip encore déployé ne doit jamais disparaître.
# Seules les anciennes versions du pointeur et les envois multipart abandonnés sont nettoyés.
resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "expire-noncurrent"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  rule {
    id     = "abort-mpu"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.artifacts]
}
