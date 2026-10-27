# bodacc-normalize

Job Spark qui transforme les annonces BODACC de `raw` en événements normalisés : un événement par SIREN visé, au
format `platform_schema.Event`. Exécuté sur EMR Serverless à partir de S2-04 ; développé et testé en local.

## Entrée

Une partition `raw` (ou un dossier de partitions), écrite par `ingest-bodacc` : JSONL, gzip ou non.

```
spark-submit main.py --input s3://<raw>/bodacc/date=YYYY-MM-DD/
```

Lue avec un schéma explicite (`schemas.py`), jamais inféré : une journée vide garde ses colonnes, un champ ajouté
par la source est ignoré, une ligne illisible fait échouer le run (`FAILFAST`).

Limite actuelle : le job lit le chemin qu'on lui donne, sans vérifier `_MANIFEST.json`. Le contrat de `raw`
(« une partition n'est lisible que si son manifest existe ») sera tenu par l'orchestration (S2-06), qui ne
lancera le job que sur une partition complète.

## Sortie

Un DataFrame au schéma de `platform_schema.Event` (noms, ordre, types). Écriture dans une table Iceberg en S2-03.

| Champ | Règle actuelle (affinée en S2-02) |
|---|---|
| `siren` | un événement par SIREN distinct des personnes (RCS, sinon Répertoire des Métiers) ; `null` si aucun |
| `event_type` | `familleavis` |
| `event_date` | `dateparution` |
| `tribunal`, `company_name` | `tribunal`, `commercant` |
| `persons` | toutes les personnes de l'annonce (`personne` objet ou liste), jamais `null` |
| `source_id` | `id` de l'annonce |
| `ingested_at` | horodatage du run, injecté par `main.py` |

Nullabilité : relâchée dans le DataFrame (Spark ne sait pas rendre non nullable une colonne calculée) ; le contrat
complet est vérifié par Pydantic dans les tests et le sera par les colonnes `NOT NULL` de la table Iceberg.

## Code

| Module | Rôle |
|---|---|
| `schemas.py` | forme de la source : `RAW_SCHEMA` (la ligne), `PERSONNE_*` (le JSON dans `listepersonnes`) |
| `raw.py` | lecture de `raw` |
| `transform.py` | `normalize` : cœur pur, sans I/O ni horloge |
| `main.py` | point d'entrée `spark-submit` : arguments, session, lecture, normalisation |

## Tests

```bash
make spark-jars                       # une fois par poste : jar Iceberg dans build/jars/
uv run pytest jobs/normalize          # session Spark locale partagée (jobs/conftest.py)
```

Sans JDK 17 ou sans le jar, les tests Spark sont ignorés (`skip`) avec la commande à lancer. Fixture :
`tests/fixtures/raw_3.jsonl`, 3 annonces réelles du 2026-10-20 (dont une à `personne` en liste), adresses des
personnes physiques tronquées. Critère d'acceptation : `tests/test_acceptance.py`.
