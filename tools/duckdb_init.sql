-- Session DuckDB prête à interroger le data lake : chargée par `make duckdb`.
-- Le bucket arrive par la variable d'environnement RAW_BUCKET (posée par le Makefile depuis les outputs Terraform) :
-- l'identifiant de compte n'est jamais écrit dans le repo.
INSTALL httpfs; LOAD httpfs;  -- INSTALL ne télécharge que la première fois (~/.duckdb/extensions)
INSTALL aws; LOAD aws;

-- Identifiants de la chaîne AWS habituelle (profil du Makefile) ; secret de session, rien n'est stocké.
CREATE OR REPLACE SECRET s3_data_platform (
    TYPE s3, PROVIDER credential_chain, CHAIN 'env;config', REGION 'eu-west-3'
);

-- Convention du bucket raw, la même pour toutes les sources : <source>/date=YYYY-MM-DD/part-*.jsonl.gz
-- + _MANIFEST.json. Une nouvelle source n'ajoute donc rien ici :
--   SELECT * FROM raw('bodacc') WHERE date = '2026-10-20';
--   SELECT * FROM manifests('bodacc');
-- La colonne `date` vient du chemin (partitionnement Hive).
CREATE OR REPLACE MACRO raw(source) AS TABLE
SELECT *
FROM read_json_auto(
    's3://' || getenv('RAW_BUCKET') || '/' || source || '/date=*/part-*.jsonl.gz',
    hive_partitioning = true
);

CREATE OR REPLACE MACRO manifests(source) AS TABLE
SELECT *
FROM read_json_auto('s3://' || getenv('RAW_BUCKET') || '/' || source || '/date=*/_MANIFEST.json');
