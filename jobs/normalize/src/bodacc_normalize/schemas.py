"""Forme de la source : les annonces telles que `raw` les stocke, réduites aux champs lus par le job.

Deux niveaux, car BODACC encode du JSON dans des chaînes (docs/source-bodacc.md §5) :
- `RAW_SCHEMA` : une ligne JSONL de `raw`, lue par `spark.read.json` ; `listepersonnes` et `jugement` y sont des
  chaînes ;
- `PERSONNE_OBJET` / `PERSONNE_LISTE` : le contenu de la chaîne `listepersonnes`, décodé par `from_json`.

Schémas explicites, jamais inférés : les colonnes existent même sur une journée vide, leurs types ne dépendent pas
des annonces du jour, et un champ ajouté par la source est ignoré. Le contrat de sortie, lui, est
`platform_schema.Event` (package partagé avec l'agent).
"""

from pyspark.sql.types import ArrayType, DateType, StringType, StructField, StructType

RAW_SCHEMA = StructType(
    [
        StructField("id", StringType()),
        StructField("dateparution", DateType()),
        StructField("familleavis", StringType()),
        StructField("typeavis", StringType()),
        StructField("tribunal", StringType()),
        StructField("commercant", StringType()),
        StructField("listepersonnes", StringType()),
        StructField("jugement", StringType()),
    ]
)

# Une personne de `listepersonnes`.
PERSONNE = StructType(
    [
        StructField("typePersonne", StringType()),
        StructField("denomination", StringType()),
        StructField("nom", StringType()),
        StructField("prenom", StringType()),
        StructField("numeroImmatriculation", StructType([StructField("numeroIdentification", StringType())])),
        StructField("inscriptionRM", StructType([StructField("numeroIdentificationRM", StringType())])),
    ]
)

# `personne` est un objet, ou une liste quand l'annonce vise plusieurs personnes (5 annonces sur 32 373 le
# 2026-10-20). Le type d'une colonne Spark est fixé d'avance : la transformation décode les deux formes, une seule
# réussit pour une ligne donnée.
PERSONNE_OBJET = StructType([StructField("personne", PERSONNE)])
PERSONNE_LISTE = StructType([StructField("personne", ArrayType(PERSONNE))])
