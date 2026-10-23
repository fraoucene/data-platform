# Cycle de vie : ce que S3 fait tout seul avec le temps.
# Trois règles par bucket :
#   1. expire-current   : supprime l'objet courant après N jours (seulement si N est défini
#                         pour ce bucket dans var.expiration_days : raw = 90, logs = 30)
#   2. expire-noncurrent: supprime les anciennes versions après noncurrent_days
#                         (sinon, avec le versioning, rien n'est jamais vraiment supprimé)
#   3. abort-mpu        : nettoie les uploads multipart abandonnés, invisibles et facturés
resource "aws_s3_bucket_lifecycle_configuration" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  # Règle 1 : bloc conditionnel. for_each sur [] = pas de bloc, sur [N] = un bloc.
  dynamic "rule" {
    for_each = lookup(var.expiration_days, each.key, null) == null ? [] : [var.expiration_days[each.key]]

    content {
      id     = "expire-current"
      status = "Enabled"

      filter {}

      expiration {
        days = rule.value
      }
    }
  }

  # Règle 2 : sur tous les buckets.
  rule {
    id     = "expire-noncurrent"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_days
    }
  }

  # Règle 3 : sur tous les buckets.
  rule {
    id     = "abort-mpu"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Le versioning doit être actif avant de parler de versions non courantes.
  depends_on = [aws_s3_bucket_versioning.this]
}
