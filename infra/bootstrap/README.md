# infra/bootstrap — bucket d'état Terraform et bucket des artefacts

Root Terraform indépendant, à **état local** (`terraform.tfstate` ici, gitignoré).
Il gère ce qui doit exister avant `infra/` et survivre à son `make down` :
- le bucket S3 qui stocke l'état du root principal `infra/` (`main.tf`) ;
- le bucket des artefacts de déploiement, `data-platform-artifacts-<account_id>` (`artifacts.tf`, ajouté en S1-07) :
  zips de Lambda sous `lambdas/<name>/<sha256>.zip` et pointeur `lambdas/<name>/current.json`.
Appliqué une fois par compte AWS, quasi jamais modifié.

## Pourquoi un root séparé

Le bucket d'état ne peut pas être géré par l'état qu'il contient : il devrait exister avant son propre `apply`.
Donc un mini-root à part, avec un état local minuscule (2 buckets et leurs réglages : 9 ressources).

## Verrou d'état

Lockfile natif S3 (`use_lockfile = true` dans `infra/envs/<env>/backend.hcl`, Terraform ≥ 1.10).
Pendant un `plan`/`apply`, Terraform pose un objet `dev/terraform.tfstate.tflock` à côté de l'état et le retire à la fin.
Pas de table DynamoDB : l'option `dynamodb_table` est dépréciée depuis Terraform 1.11.

## Commandes

```bash
# depuis la racine du dépôt
cp infra/bootstrap/local.auto.tfvars.example infra/bootstrap/local.auto.tfvars   # profile, account_id
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap apply
terraform -chdir=infra/bootstrap output -raw state_bucket
terraform -chdir=infra/bootstrap output -raw artifacts_bucket
```

## Si l'état local du bootstrap est perdu

Les ressources existent toujours dans AWS. Les réimporter (remplacer `<account_id>`) :

```bash
B=data-platform-tfstate-<account_id>
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap import aws_s3_bucket.tfstate $B
terraform -chdir=infra/bootstrap import aws_s3_bucket_versioning.tfstate $B
terraform -chdir=infra/bootstrap import aws_s3_bucket_server_side_encryption_configuration.tfstate $B
terraform -chdir=infra/bootstrap import aws_s3_bucket_public_access_block.tfstate $B
A=data-platform-artifacts-<account_id>
terraform -chdir=infra/bootstrap import aws_s3_bucket.artifacts $A
terraform -chdir=infra/bootstrap import aws_s3_bucket_versioning.artifacts $A
terraform -chdir=infra/bootstrap import aws_s3_bucket_server_side_encryption_configuration.artifacts $A
terraform -chdir=infra/bootstrap import aws_s3_bucket_public_access_block.artifacts $A
terraform -chdir=infra/bootstrap import aws_s3_bucket_lifecycle_configuration.artifacts $A
terraform -chdir=infra/bootstrap plan   # doit afficher « No changes »
```
