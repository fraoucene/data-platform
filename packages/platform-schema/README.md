# platform-schema

Contrat de données partagé : l'événement normalisé (`Event`, `Person`) écrit en Pydantic, et son schéma Spark
dérivé par `sparkdantic` (`Event.model_spark_schema()`). Produit par `jobs/normalize`, lu par l'agent (S4).
Un champ ajouté ici change le schéma Spark attendu du job : le test d'acceptation de `bodacc-normalize` le signale.
