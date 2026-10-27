"""Critère d'acceptation de S2-01 : les 3 annonces de fixtures/raw_3.jsonl donnent exactement ces 3 événements.

Garde-fou de S2-02 : une règle de normalisation ajoutée doit garder ce test vert ou le faire évoluer explicitement.
Valeurs attendues écrites depuis les champs de la source (tribunal, commercant, listepersonnes), pas recopiées de
la sortie du job. Comparaison avec chispa (référence des tests PySpark ; `pyspark.testing` 3.5 importe `distutils`,
absent de Python 3.12).
"""

from datetime import UTC, date, datetime
from pathlib import Path

from chispa import assert_df_equality
from pyspark.sql import Row, SparkSession

from bodacc_normalize.raw import read_raw
from bodacc_normalize.transform import normalize
from platform_schema import Event, Person

RAW_3 = Path(__file__).parent / "fixtures" / "raw_3.jsonl"
INGESTED_AT = datetime(2026, 10, 27, 5, 0, tzinfo=UTC)

EXPECTED = [
    Event(
        siren="483609327",
        event_type="creation",
        event_date=date(2026, 10, 20),
        tribunal="Greffe du Tribunal de Commerce de Bourg-en-Bresse",
        company_name="BEN SDIRA, MOHAMED",
        persons=[Person(kind="pp", siren="483609327", name="MOHAMED BEN SDIRA")],
        source_id="A2026020111",
        ingested_at=INGESTED_AT,
    ),
    Event(
        siren="919917435",
        event_type="collective",
        event_date=date(2026, 10, 20),
        tribunal="Greffe du Tribunal de Commerce de Douai",
        company_name="JIM'HYDRO ENGINEERING PERF",
        persons=[Person(kind="pm", siren="919917435", name="JIM'HYDRO ENGINEERING PERF")],
        source_id="A202602018167",
        ingested_at=INGESTED_AT,
    ),
    # `personne` en liste : une personne physique non inscrite (pas de SIREN) et le GAEC visé.
    Event(
        siren="849264015",
        event_type="collective",
        event_date=date(2026, 10, 20),
        tribunal="Greffe du Tribunal des Activités Economiques de Saint-Brieuc",
        company_name="MASSEMIN, Clément, Groupement Agricole d'exploitation en Commun de SAINT JEAN",
        persons=[
            Person(kind="pp", siren=None, name="Clément MASSEMIN"),
            Person(kind="pm", siren="849264015", name="Groupement Agricole d'exploitation en Commun de SAINT JEAN"),
        ],
        source_id="A202602017920",
        ingested_at=INGESTED_AT,
    ),
]


def _to_event(row: Row) -> Event:
    """Une ligne collectée → `Event`, validé par Pydantic.

    `collect()` rend un `timestamp` naïf converti à l'heure locale de Python, quel que soit
    `spark.sql.session.timeZone` (mesuré sur PySpark 3.5.8 : 05:00 UTC → `datetime(2026, 10, 27, 6, 0)` sur un
    poste en CET). `astimezone(UTC)` interprète la valeur naïve comme locale : juste sur tout poste et en CI.
    """
    values = row.asDict(recursive=True)
    values["ingested_at"] = values["ingested_at"].astimezone(UTC)
    return Event.model_validate(values)


def test_acceptance_trois_annonces(spark: SparkSession) -> None:
    actual = normalize(read_raw(spark, str(RAW_3)), INGESTED_AT)
    expected = spark.createDataFrame([e.model_dump() for e in EXPECTED], schema=Event.model_spark_schema())

    # ignore_nullable : nullabilité relâchée côté Spark, contrat complet vérifié par Pydantic (test suivant).
    assert_df_equality(actual, expected, ignore_nullable=True, ignore_row_order=True)


def test_acceptance_contrat_pydantic(spark: SparkSession) -> None:
    rows = normalize(read_raw(spark, str(RAW_3)), INGESTED_AT).collect()

    assert sorted((_to_event(r) for r in rows), key=lambda e: e.source_id) == sorted(
        EXPECTED, key=lambda e: e.source_id
    )
