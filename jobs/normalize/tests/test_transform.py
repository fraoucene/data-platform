"""Normalisation sur les 3 annonces réelles de fixtures/raw_3.jsonl, plus des cas limites construits à la main."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

from bodacc_normalize.raw import read_raw
from bodacc_normalize.transform import normalize
from platform_schema import Event

RAW_3 = Path(__file__).parent / "fixtures" / "raw_3.jsonl"
INGESTED_AT = datetime(2026, 10, 27, 5, 0, tzinfo=UTC)


def _raw(spark: SparkSession, tmp_path: Path, *personnes: object) -> DataFrame:
    """Une annonce minimale par valeur de `personne` (objet, liste…), au format de `raw`."""
    path = tmp_path / "part-0001.jsonl"
    lines = [
        {
            "id": f"T{i}",
            "dateparution": "2026-10-20",
            "familleavis": "collective",
            "listepersonnes": json.dumps({"personne": personne}),
        }
        for i, personne in enumerate(personnes)
    ]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    return read_raw(spark, str(path))


def test_normalize_schema_noms_ordre_types(spark: SparkSession) -> None:
    df = normalize(read_raw(spark, str(RAW_3)), INGESTED_AT)

    # simpleString ignore la nullabilité : relâchée côté Spark, voir le docstring de job.py.
    assert df.schema.simpleString() == Event.model_spark_schema().simpleString()


def test_normalize_trois_annonces(spark: SparkSession) -> None:
    rows = normalize(read_raw(spark, str(RAW_3)), INGESTED_AT).orderBy("source_id").collect()

    assert [(r.source_id, r.siren, r.event_type, len(r.persons)) for r in rows] == [
        ("A2026020111", "483609327", "creation", 1),
        ("A202602017920", "849264015", "collective", 2),
        ("A202602018167", "919917435", "collective", 1),
    ]


def test_normalize_personne_en_liste(spark: SparkSession) -> None:
    rows = normalize(read_raw(spark, str(RAW_3)), INGESTED_AT).where("source_id = 'A202602017920'").collect()

    (row,) = rows
    assert [(p.kind, p.siren) for p in row.persons] == [("pp", None), ("pm", "849264015")]
    assert row.persons[1].name == "Groupement Agricole d'exploitation en Commun de SAINT JEAN"


def test_normalize_personne_physique_nom_complet(spark: SparkSession) -> None:
    (row,) = normalize(read_raw(spark, str(RAW_3)), INGESTED_AT).where("source_id = 'A2026020111'").collect()

    assert row.persons[0].name == "MOHAMED BEN SDIRA"


def test_normalize_deux_siren_deux_evenements(spark: SparkSession, tmp_path: Path) -> None:
    raw = _raw(
        spark,
        tmp_path,
        [
            {
                "typePersonne": "pm",
                "denomination": "A",
                "numeroImmatriculation": {"numeroIdentification": "111 111 111"},
            },
            {
                "typePersonne": "pm",
                "denomination": "B",
                "numeroImmatriculation": {"numeroIdentification": "222 222 222"},
            },
        ],
    )

    rows = normalize(raw, INGESTED_AT).orderBy("siren").collect()

    assert [r.siren for r in rows] == ["111111111", "222222222"]
    assert all(len(r.persons) == 2 for r in rows)


def test_normalize_non_inscrit_garde_un_evenement(spark: SparkSession, tmp_path: Path) -> None:
    raw = _raw(spark, tmp_path, {"typePersonne": "pp", "nom": "DUPONT", "prenom": "JEAN", "nonInscrit": "N"})

    (row,) = normalize(raw, INGESTED_AT).collect()

    assert row.siren is None
    assert row.persons[0].name == "JEAN DUPONT"


def test_normalize_artisan_siren_du_repertoire_des_metiers(spark: SparkSession, tmp_path: Path) -> None:
    raw = _raw(
        spark, tmp_path, {"typePersonne": "pp", "nom": "X", "inscriptionRM": {"numeroIdentificationRM": "333 333 333"}}
    )

    (row,) = normalize(raw, INGESTED_AT).collect()

    assert row.siren == "333333333"
