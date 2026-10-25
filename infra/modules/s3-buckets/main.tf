# Quatre buckets identiques dans leur configuration, différents par leur nom :
# une seule déclaration par ressource, `for_each` sur le set des noms,
# `each.key` = le nom logique ("raw", "processed", ...).
# Provider AWS 6 : un bucket = plusieurs ressources (bucket, accès public,
# versioning, chiffrement), reliées par `bucket = aws_s3_bucket.this[each.key].id`.

resource "aws_s3_bucket" "this" {
  for_each = toset(var.names)

  bucket        = "${var.prefix}-${each.key}-${var.suffix}"
  force_destroy = var.force_destroy
}

# Aucun accès public possible, quelle que soit la policy ou l'ACL.
resource "aws_s3_bucket_public_access_block" "this" {
  for_each = aws_s3_bucket.this

  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning : chaque écrasement ou suppression garde la version précédente.
resource "aws_s3_bucket_versioning" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Chiffrement KMS avec la clé du projet. bucket_key_enabled : S3 demande une
# clé de données par bucket et non par objet, ce qui divise les appels KMS.
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  rule {
    bucket_key_enabled = true

    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
  }
}
