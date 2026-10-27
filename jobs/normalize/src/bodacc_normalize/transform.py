"""Normalisation : annonces brutes → un événement par SIREN visé, au format `platform_schema.Event`.

Cœur pur du job : DataFrame en entrée, DataFrame en sortie, horodatage injecté ; ni lecture, ni écriture, ni
horloge (« functional core, imperative shell » : l'I/O est dans `raw.py` et `main.py`). Règles provisoires,
affinées en S2-02 : `event_type` = `familleavis`, `event_date` = `dateparution`, `company_name` = `commercant`.

Nullabilité : une colonne calculée par Spark est nullable, et `DataFrame.to(schema)` comme `cast` refusent de la
rendre non nullable (`NULLABLE_COLUMN_OR_FIELD`, mesuré sur Spark 3.5.8). La sortie a donc les noms, l'ordre et
les types d'`Event`, pas sa nullabilité : le contrat complet est vérifié par Pydantic dans les tests et par les
colonnes `NOT NULL` de la table Iceberg (S2-03).
"""

from datetime import datetime

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

from bodacc_normalize.schemas import PERSONNE_LISTE, PERSONNE_OBJET
from platform_schema import Event


def _siren(raw: Column) -> Column:
    """Espaces retirés ; gardé seulement s'il fait 9 chiffres (même règle que `bodacc_client.models._clean_siren`)."""
    digits = F.regexp_replace(raw, " ", "")
    return F.when(digits.rlike(r"^[0-9]{9}$"), digits)


def _person(p: Column) -> Column:
    """Une `Person` : SIREN du RCS, sinon du Répertoire des Métiers ; nom = dénomination, sinon prénom + nom."""
    full_name = F.when(p["nom"].isNotNull(), F.concat_ws(" ", p["prenom"], p["nom"]))
    return F.struct(
        p["typePersonne"].alias("kind"),
        F.coalesce(
            _siren(p["numeroImmatriculation"]["numeroIdentification"]),
            _siren(p["inscriptionRM"]["numeroIdentificationRM"]),
        ).alias("siren"),
        F.coalesce(p["denomination"], full_name).alias("name"),
    )


def normalize(raw: DataFrame, ingested_at: datetime) -> DataFrame:
    """Un événement par SIREN distinct de l'annonce ; une annonce sans SIREN donne un événement à `siren` null."""
    personnes = F.coalesce(
        F.from_json("listepersonnes", PERSONNE_LISTE)["personne"],
        F.array(F.from_json("listepersonnes", PERSONNE_OBJET)["personne"]),
    )
    persons = F.coalesce(F.transform(personnes, _person), F.array())
    sirens = F.array_distinct(F.filter(F.transform("persons", lambda p: p["siren"]), lambda s: s.isNotNull()))

    events = (
        raw.withColumn("persons", persons)
        # explode_outer, pas explode : un tableau vide donne une ligne (siren null) au lieu de faire disparaître
        # l'annonce (non-inscrits, ~74 par journée).
        .withColumn("siren", F.explode_outer(sirens))
        .select(
            "siren",
            F.col("familleavis").alias("event_type"),
            F.col("dateparution").alias("event_date"),
            "tribunal",
            F.col("commercant").alias("company_name"),
            "persons",
            F.col("id").alias("source_id"),
            F.lit(ingested_at).alias("ingested_at"),
        )
    )
    # Ordre des colonnes d'Event ; pas de `cast` vers son schéma (voir la nullabilité ci-dessus). Les types
    # produits sont déjà les bons : le test de schéma le vérifie.
    return events.select(Event.model_spark_schema().fieldNames())
