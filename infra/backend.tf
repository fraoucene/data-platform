# Backend S3 : configuration PARTIELLE, volontairement vide de tout ce qui
# dépend de l'environnement ou du compte. Le reste (bucket, key, region,
# profile, use_lockfile) vient de infra/envs/<env>/backend.hcl (gitignoré) :
#   make tf-init ENV=dev
# Le bloc backend n'accepte ni variable ni expression.
terraform {
  backend "s3" {
    encrypt = true
  }
}
