# Architecture cible (brouillon)

Flux : BODACC → S3 raw → jobs → S3 curated → agent.

1. **Source** : API BODACC (annonces légales), appel quotidien.
2. **Ingestion** : Lambda `bodacc-ingest` écrit le JSON brut, immuable, dans S3 `raw/bodacc/dt=YYYY-MM-DD/`.
3. **Normalisation** : job `bodacc-normalize` lit `raw/`, écrit du Parquet partitionné dans S3 `curated/`.
4. **Orchestration** : Step Functions, définitions JSON dans `steps/`, déployées par Terraform.
5. **Code partagé** : `packages/dp-common` (schémas Pydantic, tags, clients S3, logging).
6. **Agent** : interroge `curated/`, jeux de test et scores dans `evals/`.
7. **Infra** : Terraform dans `infra/`, tags obligatoires vérifiés par `infra/scripts/check_tags.py`.
8. **À préciser** : format exact des annonces BODACC, fréquence, rétention, partitionnement.

Complété au fil des cartes S1-06 (client BODACC), S2 (jobs), S8 (agent).
