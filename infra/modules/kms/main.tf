# Clé KMS symétrique du projet. Pas de `policy` custom : la politique par
# défaut délègue aux policies IAM du compte, ce qui suffit tant que tous les
# consommateurs (Lambda, EMR, S3) sont dans le même compte.
resource "aws_kms_key" "this" {
  description             = var.description
  deletion_window_in_days = var.deletion_window_in_days
  enable_key_rotation     = true
}

# L'alias est le nom stable : les humains et la CLI l'utilisent,
# les ressources référencent l'ARN de la clé.
resource "aws_kms_alias" "this" {
  name          = "alias/${var.name}"
  target_key_id = aws_kms_key.this.key_id
}
