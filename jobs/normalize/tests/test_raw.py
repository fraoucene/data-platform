"""Lecture de `raw` avec le schéma explicite : 3 annonces réelles du 2026-10-20 (fixtures/raw_3.jsonl).

Fixture : lignes extraites de la partition `raw` du 2026-10-20, adresses des personnes physiques tronquées par
`packages/bodacc-client/tests/fixtures/sanitize_fixtures.py`. Choisies pour couvrir : personne physique (création),
personne morale (procédure collective), et `listepersonnes.personne` en liste (5 annonces sur 32 373 ce jour-là).
"""

from datetime import date
from pathlib import Path

import pytest
from py4j.protocol import Py4JJavaError
from pyspark.sql import SparkSession

from bodacc_normalize.raw import read_raw
from bodacc_normalize.schemas import RAW_SCHEMA

RAW_3 = Path(__file__).parent / "fixtures" / "raw_3.jsonl"


def test_raw_trois_annonces_typees(spark: SparkSession) -> None:
    df = read_raw(spark, str(RAW_3))

    rows = {r.id: r for r in df.collect()}

    assert df.schema == RAW_SCHEMA
    assert set(rows) == {"A2026020111", "A202602018167", "A202602017920"}
    assert rows["A202602018167"].dateparution == date(2026, 10, 20)
    assert rows["A2026020111"].jugement is None
    # Le JSON imbriqué reste une chaîne à ce stade : décodé par from_json dans la normalisation.
    assert rows["A202602017920"].listepersonnes.startswith('{"personne": [')


def test_raw_journee_vide_garde_les_colonnes(spark: SparkSession, tmp_path: Path) -> None:
    empty = tmp_path / "part-0001.jsonl"
    empty.write_text("")

    df = read_raw(spark, str(empty))

    assert df.count() == 0
    assert df.columns == RAW_SCHEMA.fieldNames()


def test_raw_ligne_illisible_echoue(spark: SparkSession, tmp_path: Path) -> None:
    broken = tmp_path / "part-0001.jsonl"
    broken.write_text(RAW_3.read_text(encoding="utf-8") + "{pas du json\n", encoding="utf-8")

    df = read_raw(spark, str(broken))  # transformation : rien n'est lu encore

    # Action : la lecture a lieu ici, et échoue. Spark 3.5 remonte l'exception Java telle quelle (Py4JJavaError) ;
    # le code d'erreur Spark dans le message est stable, le texte autour ne l'est pas.
    with pytest.raises(Py4JJavaError, match="MALFORMED_RECORD_IN_PARSING"):
        df.collect()
