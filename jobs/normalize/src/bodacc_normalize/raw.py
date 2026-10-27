"""Lecture des partitions `raw` : JSONL (gzip ou non) écrits par la Lambda `ingest-bodacc`."""

from pyspark.sql import DataFrame, SparkSession

from bodacc_normalize.schemas import RAW_SCHEMA


def read_raw(spark: SparkSession, path: str) -> DataFrame:
    """Lit un fichier ou un dossier de partitions `raw` avec `RAW_SCHEMA`. Une ligne illisible fait échouer la lecture.

    `FAILFAST` plutôt que `PERMISSIVE` (défaut) : une annonce illisible doit faire échouer le run (alarme), pas
    devenir en silence une ligne de `null` dans `processed`. L'erreur n'apparaît qu'à la première action.
    """
    return spark.read.schema(RAW_SCHEMA).option("mode", "FAILFAST").json(path)
