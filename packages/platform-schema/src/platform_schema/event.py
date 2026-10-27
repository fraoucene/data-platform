"""L'événement normalisé : une annonce BODACC ramenée à un fait sur une entreprise.

Écrit une fois en Pydantic ; `sparkdantic` en dérive le schéma Spark (`Event.model_spark_schema()`), que le job
`bodacc-normalize` doit produire exactement. Correspondance mesurée (sparkdantic 2.9) : `X | None` → colonne
nullable, tout autre champ → non nullable ; `Annotated[str, …]` et `Literal[…]` → `string`, la contrainte reste
côté Pydantic (vérifiée par `model_validate`, pas par Spark). Type que sparkdantic ne connaît pas (`AwareDatetime`) :
override `spark_type` lu par sparkdantic dans `json_schema_extra` (son helper `SparkField` passe par un argument
libre de `Field`, déprécié par Pydantic 2).
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StringConstraints
from sparkdantic import SparkModel

# SIREN : 9 chiffres, espaces déjà retirés (voir `bodacc_client.models._clean_siren`).
Siren = Annotated[str, StringConstraints(pattern=r"^\d{9}$")]


class Person(SparkModel):
    """Une personne de `listepersonnes` : morale (`pm`) ou physique (`pp`)."""

    kind: Literal["pm", "pp"]
    # RCS, sinon Répertoire des Métiers ; absent pour un non-inscrit.
    siren: Siren | None = None
    # Dénomination (pm), prénom + nom (pp).
    name: str | None = None


class Event(SparkModel):
    """Un événement par SIREN visé : une annonce qui vise deux sociétés donne deux événements."""

    # Absent pour une annonce qui ne vise que des non-inscrits (~74 par journée) : gardée, pas perdue.
    siren: Siren | None
    # `familleavis` (creation, collective, radiation…), précisé en S2-02 par `jugement.nature`.
    event_type: str
    # Date du fait (jugement, début d'activité), sinon `dateparution` : toujours renseignée.
    event_date: date
    tribunal: str | None
    company_name: str | None
    # Vide pour une annonce sans personne, jamais null.
    persons: list[Person]
    # `id` BODACC de l'annonce source (ex. `A202602018167`).
    source_id: str
    # Horodatage du run de normalisation, injecté par le job (pas d'horloge dans la transformation).
    ingested_at: Annotated[AwareDatetime, Field(json_schema_extra={"spark_type": "timestamp"})]
