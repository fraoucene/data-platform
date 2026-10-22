# data-platform

Plateforme data serverless sur AWS : ingestion des annonces BODACC, stockage S3, jobs de normalisation, agent d'interrogation. Monorepo Python géré par `uv`.

## Arborescence

```
.
├── packages/   # libs Python partagées (src layout), ex. dp-common
├── lambdas/    # fonctions AWS Lambda, une par dossier, dépendent de packages/
├── jobs/       # jobs batch (Spark / Python), dépendent de packages/
├── steps/      # définitions JSON des étapes de pipeline, consommées par infra/
├── infra/      # Terraform (ressources AWS, tags, state)
├── evals/      # jeux de test et scénarios d'évaluation de l'agent
├── docs/       # architecture, décisions (ADR)
├── Makefile    # sync / lint / fmt / test / check
├── pyproject.toml   # racine du workspace uv : members, ruff, pytest, deps de dev
└── uv.lock     # résolution unique pour tout le workspace
```

## Commandes

```bash
uv sync                               # crée .venv et installe les dépendances
make lint                             # ruff check + ruff format --check
make test                             # pytest sur packages/, lambdas/, jobs/
uv run pre-commit run --all-files     # tous les hooks sur tous les fichiers suivis
```

`make fmt` corrige le formatage et les imports. `make check` enchaîne `lint` puis `test`.

## Prérequis

- Python 3.12 (`.python-version`), `uv`, `make`.
- `uv run pre-commit install` une fois après le clone pour activer les hooks git.
