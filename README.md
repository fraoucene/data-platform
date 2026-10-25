# data-platform

Plateforme data serverless sur AWS : ingestion quotidienne des annonces BODACC dans S3, puis (à venir) normalisation
PySpark en tables Iceberg et agent d'interrogation. Monorepo Python géré par `uv`, infrastructure en Terraform.

## Architecture

```
EventBridge Scheduler (06:00 Europe/Paris, event {})
   │ endosse le rôle …-ingest-bodacc-scheduler
   ▼
Lambda ingest-bodacc ── API BODACC (export JSONL de la veille à Paris)
   │ écrit, dans cet ordre (idempotent : un rejeu réécrit les mêmes octets)
   ▼
S3 raw : bodacc/date=YYYY-MM-DD/part-0001.jsonl.gz  puis  _MANIFEST.json (count, sha256)
   │                                     échec → CloudWatch Errors → alarme → SNS → mail
   ▼
(S2) Step Functions → PySpark sur EMR Serverless → tables Iceberg → (S4) agent
```

Rattraper ou remplir l'historique : `make replay FROM=… TO=…` (une invocation par jour). Détail de la Lambda,
de son exploitation et du calendrier de la source : [lambdas/ingest_bodacc/README.md](lambdas/ingest_bodacc/README.md) ;
infrastructure : [infra/README.md](infra/README.md) ; source : [docs/source-bodacc.md](docs/source-bodacc.md).

## Prérequis

| Outil | Version | Sert à |
|---|---|---|
| Python | 3.12 (`.python-version`) | runtime du code et de la Lambda |
| [uv](https://docs.astral.sh/uv/) | récent | dépendances et environnement (≈ pnpm) |
| make, git | | toutes les commandes passent par le `Makefile` |
| [Terraform](https://developer.hashicorp.com/terraform/install) | ≥ 1.10 | infrastructure (verrou d'état natif S3) |
| [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) | v2 | identifiants, vérifications, invocations |
| jq | | lit les outputs Terraform (`make replay`, `make duckdb`) |
| [DuckDB](https://duckdb.org/docs/installation/) | testé en 2.0.0, facultatif | interroger le bucket raw (`make duckdb`) |

### Compte AWS et identité

Un compte AWS dédié (ou de bac à sable) et une identité qui peut créer des ressources S3, KMS, IAM, Lambda,
CloudWatch, SNS, EventBridge Scheduler et Budgets. Sur un compte neuf, ne pas travailler avec le root :

1. Console, en root : IAM Identity Center → activer → créer un utilisateur → lui attribuer le compte avec le
   permission set `AdministratorAccess` (compte personnel de développement ; en entreprise, un rôle plus étroit).
2. Poste : `aws configure sso --profile data-platform` (région `eu-west-3`), puis
   `aws sso login --profile data-platform` (à refaire quand la session expire).
3. `aws sts get-caller-identity --profile data-platform` → le numéro de compte, à reporter dans les fichiers des
   étapes 2 et 3 du démarrage (`account_id`). Ne jamais le commiter.

Si `make up` échoue sur `aws_budgets_budget` avec `AccessDenied` alors que l'identité est administrateur : en root,
Compte → « IAM user and role access to Billing information » → activer.

Coût : quelques dollars par mois en dev (clé KMS ~1 USD, le reste à l'usage) ; un budget de 35 USD (`dev.tfvars`)
envoie un mail d'alerte avant dépassement.

## Démarrer de zéro

```bash
# 0. Le dépôt (un clone git, pas une archive : le build des Lambdas lit `git rev-parse HEAD`)
git clone https://github.com/fraoucene/data-platform.git && cd data-platform

# 1. Dépendances de tout le workspace (pas `uv sync` seul : il n'installe pas les Lambdas et les packages)
make sync
uv run pre-commit install          # hooks git (ruff, uv-lock, gros fichiers)
make check                         # → lint vert, N passed

# 2. Bootstrap, une fois par compte AWS : bucket d'état Terraform + bucket des artefacts
cp infra/bootstrap/local.auto.tfvars.example infra/bootstrap/local.auto.tfvars   # profile, account_id
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap apply

# 3. Configuration de l'environnement (fichiers gitignorés)
cp infra/envs/dev/backend.hcl.example infra/envs/dev/backend.hcl     # bucket = output state_bucket du bootstrap
cp infra/envs/dev/local.tfvars.example infra/envs/dev/local.tfvars   # profile, account_id, alert_email

# 4. Publier les zips des Lambdas AVANT le premier `make up` : Terraform lit le pointeur current.json
make lambdas-publish

# 5. Déployer
make plan                          # → Plan: N to add, 0 violation(s) de tags
make up                            # apply -auto-approve : pas de confirmation, relire le plan avant

# 6. Confirmer les 2 mails « AWS Notification - Subscription Confirmation » (budget, alertes) :
#    sans le clic, les alarmes ne livrent rien.

# 7. Remplir l'historique (facultatif), puis vérifier
make replay FROM=2026-10-01 TO=2026-10-19   # → 19/19 jours ingérés
make duckdb                                  # SELECT date, count FROM manifests('bodacc') ORDER BY date;
```

Ensuite, la planification ingère chaque matin la veille sans intervention. Reconstruction de l'infrastructure,
état Terraform, ce que `make down` détruit : [infra/README.md](infra/README.md).

## Commandes du quotidien

| Groupe | Commande | Effet |
|---|---|---|
| Python | `make sync` | `uv sync --all-packages` |
| | `make check` | `lint` (ruff check + format --check) puis `test` (pytest) |
| | `make fmt` | corrige formatage et imports |
| | `make test-integration` | tests qui appellent la vraie API BODACC (réseau) |
| | `make cov` | couverture |
| Lambdas | `make lambdas-build [LAMBDA=…]` | zip reproductible dans `build/` |
| | `make lambdas-publish [LAMBDA=…]` | envoi du zip (clé = hash) + pointeur dans le bucket artefacts |
| | `make deploy` | `lambdas-publish` puis `up` (ce que fera la CI) |
| | `make replay FROM=… TO=… [LAMBDA=…]` | rejoue une plage de jours, code 1 si un jour échoue |
| Terraform | `make plan [ENV=…]` | init + plan + audit des tags (`ENV=dev` par défaut) |
| | `make up` / `make down` | apply / destroy (`down` : dev uniquement) |
| Données | `make duckdb` | session DuckDB sur le bucket raw : `raw('bodacc')`, `manifests('bodacc')` |
| Révision | `make cards-validate` / `make cards-publish` | cartes de `learning/` vers l'app revision-pwa |

## Arborescence

```
.
├── packages/   # libs Python partagées (src layout) : dp-common, bodacc-client
├── lambdas/    # fonctions AWS Lambda, une par dossier (membre uv), ex. ingest_bodacc
├── jobs/       # jobs batch (Spark / Python), à partir de S2
├── steps/      # définitions des étapes de pipeline (Step Functions, S2)
├── infra/      # Terraform : bootstrap/, modules/, envs/<env>/, scripts/ (build, rejeu, audit des tags)
├── evals/      # jeux de test et scénarios d'évaluation de l'agent (S6)
├── docs/       # architecture, étude de la source, décisions
├── tools/      # outillage local (init DuckDB)
├── learning/   # cours par carte Trello et cartes de révision (source du miroir Notion)
├── AGENTS.md   # règles pour les agents de code (Claude Code lit CLAUDE.md, qui l'importe)
├── Makefile
├── pyproject.toml   # racine du workspace uv : members, ruff, pytest, deps de dev
└── uv.lock     # résolution unique pour tout le workspace
```
