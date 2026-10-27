from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError
from pyspark.sql.types import ArrayType, DateType, StringType, StructType, TimestampType

from platform_schema import Event, Person


def _event(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "siren": "919917435",
        "event_type": "collective",
        "event_date": date(2026, 10, 9),
        "tribunal": "Greffe du Tribunal de Commerce de Douai",
        "company_name": "JIM'HYDRO ENGINEERING PERF",
        "persons": [{"kind": "pm", "siren": "919917435", "name": "JIM'HYDRO ENGINEERING PERF"}],
        "source_id": "A202602018167",
        "ingested_at": datetime(2026, 10, 27, 5, 0, tzinfo=UTC),
    }
    return base | overrides


def test_schema_spark_champs_types_nullabilite() -> None:
    schema = Event.model_spark_schema()

    assert [(f.name, f.dataType, f.nullable) for f in schema.fields] == [
        ("siren", StringType(), True),
        ("event_type", StringType(), False),
        ("event_date", DateType(), False),
        ("tribunal", StringType(), True),
        ("company_name", StringType(), True),
        ("persons", ArrayType(Person.model_spark_schema(), containsNull=False), False),
        ("source_id", StringType(), False),
        ("ingested_at", TimestampType(), False),
    ]


def test_schema_spark_personne() -> None:
    schema = Person.model_spark_schema()

    assert isinstance(schema, StructType)
    assert [(f.name, f.nullable) for f in schema.fields] == [("kind", False), ("siren", True), ("name", True)]


def test_evenement_valide() -> None:
    event = Event.model_validate(_event())

    assert event.persons == [Person(kind="pm", siren="919917435", name="JIM'HYDRO ENGINEERING PERF")]


def test_non_inscrit_sans_siren_ni_personne() -> None:
    event = Event.model_validate(_event(siren=None, persons=[]))

    assert event.siren is None
    assert event.persons == []


@pytest.mark.parametrize("siren", ["91991743", "919 917 435", "91991743A"])
def test_siren_mal_forme_refuse(siren: str) -> None:
    with pytest.raises(ValidationError, match="siren"):
        Event.model_validate(_event(siren=siren))


def test_kind_inconnu_refuse() -> None:
    with pytest.raises(ValidationError, match="kind"):
        Event.model_validate(_event(persons=[{"kind": "xx"}]))


def test_ingested_at_sans_fuseau_refuse() -> None:
    with pytest.raises(ValidationError, match="ingested_at"):
        Event.model_validate(_event(ingested_at=datetime(2026, 10, 27, 5, 0)))
