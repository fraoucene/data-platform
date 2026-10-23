# Architecture cible

Flux : BODACC → S3 `raw` → jobs → S3 `processed` → S3 `out` → agent.

1. **Source** : API BODACC (annonces légales), appel quotidien.
2. **Ingestion** : Lambda `bodacc-ingest` (rôle `data-platform-<env>-lambda`) écrit le JSON brut, immuable,
   dans `raw/bodacc/dt=YYYY-MM-DD/`. Rétention 90 jours, rejouable depuis la source.
3. **Normalisation** : job Spark `bodacc-normalize` (rôle `data-platform-<env>-emr`) lit `raw`, écrit du
   Parquet partitionné dans `processed`, des exports dans `out`, ses logs dans `logs`.
4. **Orchestration** : Step Functions (rôle `data-platform-<env>-sfn`), définitions JSON dans `steps/`,
   déployées par Terraform.
5. **Code partagé** : `packages/dp-common` (schémas Pydantic, tags, clients S3, logging).
6. **Agent** : interroge `processed` / `out`, jeux de test et scores dans `evals/`.
7. **Artefacts** : zips de Lambda, jars et scripts de jobs publiés par la CI dans `artifacts`.
8. **Infra** : Terraform dans `infra/` (voir `infra/README.md`) : backend S3 verrouillé, clé KMS du projet,
   5 buckets chiffrés et versionnés, 3 rôles au moindre privilège, tags audités à chaque `plan`.
   Un code, une config par environnement (`infra/envs/<env>/`), `make plan|up|down ENV=<env>`.
9. **À préciser** : format exact des annonces BODACC, fréquence, partitionnement, stratégie de compte
   (un compte AWS par env, recommandé).

Complété au fil des cartes S1-06 (client BODACC), S2 (jobs), S8 (agent).
