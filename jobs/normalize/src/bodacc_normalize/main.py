"""Point d'entrée du job, lancé par `spark-submit` (EMR Serverless en S2-04) : session, lecture, normalisation.

Seule couche qui crée la `SparkSession`, lit l'horloge et parle aux stockages ; la logique est dans `transform.py`.
L'écriture dans la table Iceberg arrive en S2-03.

    spark-submit main.py --input s3://<raw>/bodacc/date=2026-10-20/
"""

import argparse
import logging
from datetime import UTC, datetime

from pyspark.sql import SparkSession

from bodacc_normalize.raw import read_raw
from bodacc_normalize.transform import normalize

logger = logging.getLogger("bodacc_normalize")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="bodacc-normalize", description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True, help="fichier ou dossier de partitions raw (local ou s3://)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    spark = SparkSession.builder.appName("bodacc-normalize").getOrCreate()
    events = normalize(read_raw(spark, args.input), ingested_at=datetime.now(UTC))
    logger.info("événements normalisés : %d (%s)", events.count(), args.input)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    main()
