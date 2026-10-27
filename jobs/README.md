# jobs/

Jobs de traitement batch (Spark / Python), un dossier par job, membres du workspace `uv`.
Dépendent de `packages/` ; orchestrés par les définitions de `steps/` et l'infra Terraform.
Exemple : `jobs/normalize` (membre `bodacc-normalize`) : `raw` → événements normalisés (`platform_schema.Event`).
Un job = `schemas.py` (forme de la source), `raw.py` (lecture), `transform.py` (cœur pur), `main.py` (point d'entrée
`spark-submit`). Fixture `spark` commune : `jobs/conftest.py`.
