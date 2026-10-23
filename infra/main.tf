# Composition du socle : modules appelés par le root, un seul code pour tous
# les environnements, différenciés par var.environment (envs/<env>/<env>.tfvars).

locals {
  prefix = "data-platform-${var.environment}"
}

module "kms" {
  source = "./modules/kms"

  name        = local.prefix
  description = "Clé de chiffrement ${local.prefix} (S3, artefacts, logs)"
}

module "s3" {
  source = "./modules/s3-buckets"

  prefix      = local.prefix
  suffix      = data.aws_caller_identity.current.account_id
  kms_key_arn = module.kms.key_arn

  # Seul dev autorise destroy à vider les buckets.
  force_destroy = var.environment == "dev"
}

module "iam" {
  source = "./modules/iam"

  prefix      = local.prefix
  bucket_arns = module.s3.bucket_arns
  kms_key_arn = module.kms.key_arn
  region      = var.region
  account_id  = data.aws_caller_identity.current.account_id
}
