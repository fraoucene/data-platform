# ingest-bodacc

Lambda qui ingère une journée de parution BODACC dans le bucket raw. Premier maillon du pipeline quotidien
(appelée par Step Functions en S2).

## Entrée

| Event | Journée ingérée |
|---|---|
| `{}` | la veille, calculée en heure de Paris (la Lambda tourne en UTC) |
| `{"date": "YYYY-MM-DD"}` | ce jour-là (rejeu) |

Refusé (`ValueError`, l'invocation échoue) : date mal formée, date qui n'est pas une chaîne, jour courant ou futur
(sa parution peut être incomplète).

Configuration : variable d'environnement `RAW_BUCKET`, posée par Terraform (`infra/lambdas.tf`).

## Sortie

```
s3://<raw>/bodacc/date=YYYY-MM-DD/part-0001.jsonl.gz   une annonce par ligne, gzip, ContentType application/gzip
s3://<raw>/bodacc/date=YYYY-MM-DD/_MANIFEST.json       écrit en dernier : la partition est complète
```

Le manifest porte `count`, `sha256` (du JSONL non compressé), `raw_bytes`, `gz_bytes`, `fetched_at`,
`bodacc_client_version`. La valeur de retour de l'invocation : `{"date", "count", "sha256", "keys"}`.

Un lecteur (job PySpark, Athena) ne lit une partition que si `_MANIFEST.json` existe.

## Idempotence

Rejouer une date réécrit les deux mêmes clés :

- ordre de l'export fixé (`order_by=id`) et gzip déterministe (`mtime=0`, sans nom de fichier dans l'en-tête) :
  si la source n'a pas changé, le part est identique octet pour octet ;
- seul `fetched_at` change dans le manifest ;
- aucun envoi avant la fin de la lecture : une coupure en plein flux laisse la partition telle qu'elle était ;
- part puis manifest : un plantage entre les deux laisse une partition sans manifest, ignorée, que le rejeu complète.

Vérifier un rejeu : comparer le `sha256` des deux manifests, ou télécharger les deux versions du part
(`list-object-versions`) et les comparer avec `cmp`. **Pas l'`ETag`** : avec SSE-KMS, il change à chaque PUT,
même pour des octets identiques. Le versioning garde l'ancienne version, supprimée après 30 jours
(`expire-noncurrent`).

## Développer

```
uv run pytest lambdas/ingest_bodacc          # tests (respx pour l'API, moto pour S3)
make lambdas-build LAMBDA=ingest-bodacc      # zip reproductible dans build/, roues Linux aarch64
make lambdas-publish LAMBDA=ingest-bodacc    # publie le zip (clé = hash) + current.json dans le bucket artefacts
make up                                      # Terraform déploie la version pointée par current.json
```

Invoquer à la main :

```
aws lambda invoke --function-name data-platform-dev-ingest-bodacc --payload '{"date":"2026-10-20"}' \
  --cli-binary-format raw-in-base64-out --profile data-platform out.json
aws logs tail /aws/lambda/data-platform-dev-ingest-bodacc --since 10m --profile data-platform
```

Explorer le résultat : `make duckdb`, puis `SELECT … FROM raw('bodacc')` / `FROM manifests('bodacc')`.
