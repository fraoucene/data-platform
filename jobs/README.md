# jobs/

Jobs de traitement batch (Spark / Python), un dossier par job, membres du workspace `uv`.
Dépendent de `packages/` ; orchestrés par les définitions de `steps/` et l'infra Terraform.
Exemple : `jobs/bodacc-normalize` (S3 brut → Parquet partitionné).
