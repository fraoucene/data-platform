"""Fixture `spark` partagée par les tests des jobs : une SparkSession locale avec Iceberg, sans réseau."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

# Téléchargé par `make spark-jars` (version fixée dans le Makefile, alignée sur Spark 3.5 d'EMR 7.14).
JARS_DIR = Path(__file__).resolve().parents[1] / "build" / "jars"


@pytest.fixture(scope="session")
def spark(tmp_path_factory: pytest.TempPathFactory) -> Iterator[SparkSession]:
    """Une session pour tout le run : démarrer la JVM coûte quelques secondes, pas question de le faire par test.

    Catalogue Iceberg `local` de type `hadoop` : les tables vivent dans un dossier temporaire du run (Glue en prod).
    Le jar Iceberg est chargé depuis le disque (`spark.jars`), jamais depuis Maven (`spark.jars.packages`).
    """
    jars = sorted(JARS_DIR.glob("iceberg-spark-runtime-*.jar"))
    if not jars:
        pytest.skip(f"jar Iceberg absent de {JARS_DIR} : lancer `make spark-jars`")
    warehouse = tmp_path_factory.mktemp("iceberg-warehouse")

    session = (
        SparkSession.builder.master("local[1]")
        .appName("data-platform-tests")
        .config("spark.jars", ",".join(str(jar) for jar in jars))
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.local.type", "hadoop")
        .config("spark.sql.catalog.local.warehouse", str(warehouse))
        # 200 partitions de shuffle par défaut : des centaines de tâches vides pour 3 lignes de test.
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        # Les timestamps ne doivent pas dépendre du fuseau du poste.
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()
