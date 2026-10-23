# infra/ — Terraform de la plateforme

Un seul code, une configuration par environnement, un état par environnement dans S3.

```
infra/
├── bootstrap/          # root n°1 : le bucket d'état (état LOCAL, appliqué une fois par compte AWS)
├── backend.tf          # root n°2 : backend S3 partiel (encrypt seul), complété par envs/<env>/backend.hcl
├── main.tf             # composition : module kms → module s3 → module iam
├── providers.tf        # provider AWS, allowed_account_ids, default_tags (project, environment, managed_by)
├── variables.tf        # region, profile, account_id, environment, tags, alert_email, budget_limit_usd
├── outputs.tf          # ARN et noms exposés aux cartes suivantes (Lambda, Step Functions, jobs)
├── alerts.tf budget.tf # socle S1-02 : budget mensuel + topic SNS
├── modules/
│   ├── kms/            # clé symétrique du projet + alias, rotation annuelle
│   ├── s3-buckets/     # 5 buckets chiffrés KMS, versionnés, privés, lifecycle, logs d'accès
│   └── iam/            # rôles lambda / emr / sfn, moindre privilège
├── envs/
│   └── dev/            # dev.tfvars (commité), backend.hcl + local.tfvars (gitignorés, .example commités)
└── scripts/
    └── check_tags.py   # audit des tags sur le plan JSON (make plan)
```

## Reconstruire de zéro sur une machine vierge

```bash
# 0. Prérequis : terraform >= 1.10, aws cli, uv, make ; profil AWS « data-platform » configuré.

# 1. Bootstrap (une fois par compte AWS) : crée le bucket d'état.
cp infra/bootstrap/local.auto.tfvars.example infra/bootstrap/local.auto.tfvars   # profile, account_id
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap apply

# 2. Config de l'environnement.
cp infra/envs/dev/backend.hcl.example infra/envs/dev/backend.hcl     # bucket = output state_bucket du bootstrap
cp infra/envs/dev/local.tfvars.example infra/envs/dev/local.tfvars   # profile, account_id, alert_email

# 3. Tout le reste passe par make (ENV=dev par défaut).
make plan        # init + plan -out=tfplan + audit des tags
make up          # apply -auto-approve
make down        # destroy -auto-approve (dev uniquement : force_destroy vide les buckets)
```

Aucun `-migrate-state` : sur une machine vierge, le backend S3 est configuré dès le premier `init`
(la migration n'a servi qu'une fois, pour passer l'état local historique vers S3).

Ajouter un environnement = créer `envs/<env>/` sur le même modèle et lancer `make plan ENV=<env>`.
Si l'env vit dans un autre compte AWS : appliquer `bootstrap/` sur ce compte d'abord.

## Où est l'état

| Root | État | Verrou |
|---|---|---|
| `infra/bootstrap/` | local, `infra/bootstrap/terraform.tfstate` (gitignoré) | aucun (un seul opérateur, une fois) |
| `infra/` | S3 `data-platform-tfstate-<account_id>`, clé `<env>/terraform.tfstate`, AES256, versionné | lockfile natif S3 (`use_lockfile = true`), objet `.tflock` à côté de l'état |

Décision verrou : `use_lockfile` plutôt que DynamoDB. Terraform ≥ 1.10 pose un `PutObject` conditionnel
(`If-None-Match`) ; un second `plan` concurrent échoue avec `412 PreconditionFailed`. Zéro ressource
supplémentaire ; `dynamodb_table` est déprécié depuis Terraform 1.11.

Si l'état local du bootstrap est perdu : voir `bootstrap/README.md` (4 `terraform import`).

## Ce que `make down` détruit, et ce qui survit

Détruit (43 ressources en dev) : les 5 buckets et leur contenu (`force_destroy`), les 3 rôles et leurs
policies, la clé KMS (planifiée, 7 jours) et son alias, le budget, le topic et l'abonnement SNS.

Survit : le bootstrap (bucket d'état, hors périmètre), l'état `dev/terraform.tfstate` lui-même (vide,
versions précédentes conservées), les autres environnements.

Après `make up` : nouvelle clé KMS (nouvel ARN, même alias) et nouvel abonnement SNS à confirmer par mail.
Les objets chiffrés par l'ancienne clé seraient illisibles après 7 jours : `down` est réservé à dev.

## Buckets

| Nom logique | Rôle | Lifecycle |
|---|---|---|
| `raw` | données brutes BODACC, telles que reçues, immuables | expiration 90 j |
| `processed` | données nettoyées, Parquet partitionné | aucune expiration |
| `out` | exports et résultats pour les consommateurs | aucune expiration |
| `artifacts` | zips de Lambda, jars, scripts de jobs | aucune expiration |
| `logs` | logs d'accès S3 des quatre autres (`s3/<nom>/`) | expiration 30 j |

Tous : nom `data-platform-<env>-<logique>-<account_id>`, chiffrement `aws:kms` (clé du projet,
`bucket_key_enabled`), versioning, accès public bloqué, versions non courantes expirées à 30 j,
multipart abandonnés nettoyés à 7 j.

## Rôles IAM

| Rôle | Endossé par | Lit | Écrit | Autre |
|---|---|---|---|---|
| `data-platform-<env>-lambda` | `lambda.amazonaws.com` | `raw` | `processed` | CloudWatch Logs, KMS |
| `data-platform-<env>-emr` | `elasticmapreduce.amazonaws.com` | `raw`, `processed` | `processed`, `out`, `logs` | KMS |
| `data-platform-<env>-sfn` | `states.amazonaws.com` | | | `lambda:InvokeFunction` sur `data-platform-<env>-*` |

Vérifier un droit sans rien déployer :

```bash
aws iam simulate-principal-policy --policy-source-arn $(terraform -chdir=infra output -raw lambda_role_arn) \
  --action-names s3:PutObject --resource-arns "$(terraform -chdir=infra output -json bucket_arns | jq -r .out)/x" \
  --query 'EvaluationResults[0].EvalDecision' --output text     # implicitDeny
```

## Tags

`default_tags` pose `project = data-platform`, `environment = <env>`, `managed_by = terraform` sur toute
ressource taggable. `make plan` termine par l'audit du plan JSON :
`N ressources taggables auditées, M ignorées (non taggables), V violation(s)`, code 1 si V > 0.
`managed_by = terraform` est une étiquette : toute modification passe par le code, la console sert à lire.
