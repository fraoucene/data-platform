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
├── alerts.tf budget.tf # budget mensuel + topic SNS (S1-02) ; topic d'alertes par env + alarmes Lambda (S1-08)
├── lambdas.tf          # local.lambdas : une entrée = une Lambda (module lambda-python)
├── schedules.tf        # local.schedules : planifications EventBridge Scheduler + rôle d'invocation
├── modules/
│   ├── kms/            # clé symétrique du projet + alias, rotation annuelle
│   ├── s3-buckets/     # 4 buckets chiffrés KMS, versionnés, privés, lifecycle, logs d'accès
│   └── iam/            # rôles lambda / emr / sfn, moindre privilège
├── envs/
│   └── dev/            # dev.tfvars (commité), backend.hcl + local.tfvars (gitignorés, .example commités)
└── scripts/
    ├── check_tags.py   # audit des tags sur le plan JSON (make plan)
    ├── build_lambda.py # zip reproductible + publication (make lambdas-publish)
    └── replay.py       # rejeu d'une plage de jours (make replay)
```

## Reconstruire de zéro sur une machine vierge

```bash
# 0. Prérequis : terraform >= 1.10, aws cli, uv, make ; profil AWS « data-platform » configuré.

# 1. Bootstrap (une fois par compte AWS) : crée le bucket d'état et le bucket des artefacts.
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

Détruit (60 ressources gérées en dev au 2026-10-25, `terraform -chdir=infra state list | grep -vc '^data\.'`) :
les 4 buckets et leur contenu (`force_destroy`), les 5 rôles (lambda, emr, sfn, rôle de la Lambda d'ingestion, rôle
du scheduler) et leurs policies, la Lambda et son log group, la planification, l'alarme, la clé KMS (planifiée,
7 jours) et son alias, le budget, les 2 topics SNS et leurs abonnements.

Survit : le bootstrap (bucket d'état et bucket des artefacts, donc les zips publiés), l'état `dev/terraform.tfstate`
lui-même (vide, versions précédentes conservées), les autres environnements.

Après `make up` : nouvelle clé KMS (nouvel ARN, même alias) et 2 nouveaux abonnements SNS à confirmer par mail.
Les objets chiffrés par l'ancienne clé seraient illisibles après 7 jours : `down` est réservé à dev.

## Buckets

| Nom logique | Rôle | Lifecycle |
|---|---|---|
| `raw` | données brutes BODACC, telles que reçues, immuables | expiration 90 j |
| `processed` | données nettoyées, Parquet partitionné | aucune expiration |
| `out` | exports et résultats pour les consommateurs | aucune expiration |
| `logs` | logs d'accès S3 des trois autres (`s3/<nom>/`) | expiration 30 j |

Tous : nom `data-platform-<env>-<logique>-<account_id>`, chiffrement `aws:kms` (clé du projet,
`bucket_key_enabled`), versioning, accès public bloqué, versions non courantes expirées à 30 j,
multipart abandonnés nettoyés à 7 j.

Les artefacts de déploiement (zips de Lambda, puis jars et scripts de jobs) ne sont **pas** ici : ils vivent dans
`data-platform-artifacts-<account_id>`, créé par `infra/bootstrap/`, pour survivre à `make down`
(corrigé en S1-07 : en S1-04, `artifacts` était un bucket de l'environnement, détruit avec lui).

## Lambdas

Une Lambda = un membre uv `lambdas/<dossier>/` + une entrée de `local.lambdas` dans `lambdas.tf`, déployée par le module
générique `modules/lambda-python` (rôle propre, log group 14 j, arm64, code lu dans le bucket artefacts).

```bash
make lambdas-publish   # build reproductible + envoi lambdas/<name>/<sha256>.zip + pointeur current.json
make deploy           # lambdas-publish puis up : ce que lancera la CI
```

`make up` seul déploie la version désignée par le pointeur ; il échoue si une Lambda n'a jamais été publiée.

### Planification, alertes, rejeu (S1-08)

| Fichier | Contenu |
|---|---|
| `schedules.tf` | `local.schedules` (expression, fuseau, event) ; par entrée : un rôle `…-<lambda>-scheduler` limité à `lambda:InvokeFunction` sur sa fonction, et une `aws_scheduler_schedule` avec `retry_policy` (3 tentatives, 1 h) |
| `modules/lambda-python` | `async_retry` (2 tentatives, 1 h) → `aws_lambda_function_event_invoke_config` pour toute Lambda |
| `alerts.tf` | topic `data-platform-<env>-alerts` + abonnement email + politique `cloudwatch.amazonaws.com` ; une alarme `Errors` (15 min, `notBreaching`) par entrée de `local.lambdas` |

```bash
make replay FROM=2026-10-01 TO=2026-10-19             # une invocation synchrone par jour, bilan, code 1 si échec
make replay FROM=2026-10-20 TO=2026-10-20 LAMBDA=…    # une autre Lambda de local.lambdas
```

Après `make down` puis `make up` : l'abonnement email est recréé, donc à reconfirmer (sinon alarmes muettes).

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
