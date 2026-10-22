# lambdas/

Fonctions AWS Lambda, un dossier par fonction, chacune membre du workspace `uv` avec son `pyproject.toml`.
Dépendent de `packages/` ; packagées en zip et déployées par Terraform depuis `infra/`.
Exemple : `lambdas/bodacc-ingest` (appel API BODACC → écriture S3 brute).
