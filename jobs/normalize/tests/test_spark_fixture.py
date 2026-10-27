"""La fixture `spark` (jobs/conftest.py) démarre une session locale et sait écrire une table Iceberg."""

from pyspark.sql import SparkSession


def test_session_locale(spark: SparkSession) -> None:
    assert spark.sparkContext.master == "local[1]"
    assert spark.range(3).count() == 3


def test_table_iceberg_aller_retour(spark: SparkSession) -> None:
    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.db")
    spark.sql("CREATE OR REPLACE TABLE local.db.t (id BIGINT, nom STRING) USING iceberg")
    spark.sql("INSERT INTO local.db.t VALUES (1, 'a'), (2, 'b')")

    rows = spark.table("local.db.t").orderBy("id").collect()

    assert [(r.id, r.nom) for r in rows] == [(1, "a"), (2, "b")]
    # Une table Iceberg a un historique de snapshots : l'INSERT en a créé un.
    assert spark.sql("SELECT count(*) AS n FROM local.db.t.snapshots").first().n == 1
