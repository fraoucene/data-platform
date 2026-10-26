---
type: glossaire
langage: Data engineering
updated: 2026-10-26
---

# Glossaire Data engineering

## _SUCCESS
- Définition : Fichier vide écrit en dernier dans une partition par un job (Spark, Hadoop) pour signaler aux lecteurs qu'elle est complète.
- Exemple : Un job aval attend `_SUCCESS` sous `dt=2026-10-20/` avant de lire les fichiers de la journée.
- Carte : ingestion-success-partition-complete

## Airflow
- Définition : Apache Airflow : orchestrateur open source où l'on décrit en Python un graphe de tâches, qu'il planifie, relance sur erreur et historise.
- Exemple : `extraire >> charger` déclare dans Airflow que la tâche `charger` attend la fin d'`extraire`.
- Alias : Apache Airflow
- Carte : dag-orchestrateur

## algorithme de Kahn
- Définition : Méthode de tri topologique : placer à chaque tour un élément dont tous les prérequis sont déjà placés ; si aucun n'est prêt, le graphe contient un cycle.
- Exemple : `graphlib` de Python suit cet algorithme : il trie sans récursion une chaîne de 5 000 prérequis.
- Alias : Kahn
- Carte : dag-algorithme-de-kahn

## backfill
- Définition : Rejeu d'un job sur une plage de dates passées, jour par jour, pour combler un trou ou recalculer après un correctif.
- Exemple : Après un bug de parsing, on relance l'ingestion BODACC du 1er au 19 octobre, une partition par jour.
- Alias : backfills
- Carte : ingestion-backfill-plage

## backoff exponentiel
- Définition : Attente entre deux tentatives qui double à chaque échec (1 s, 2 s, 4 s…), avec un plafond, pour ne pas accabler un service déjà surchargé.
- Exemple : Refusé par l'API BODACC pour quota dépassé, le client attend 1 s, puis 2 s, puis 4 s avant d'abandonner.
- Alias : backoff
- Carte : ingestion-retry-backoff-exponentiel

## BI
- Définition : Business Intelligence : tableaux de bord et analyses qui aident à décider, à partir de données consolidées dans un entrepôt.
- Exemple : QuickSight branché sur Athena est un outil de BI : par exemple, les annonces BODACC par département et par mois.
- Alias : Business Intelligence, informatique décisionnelle
- Carte : AWS/glue-athena-quicksight-ou-react

## BODACC
- Définition : Bulletin officiel des annonces civiles et commerciales : journal légal des ventes, procédures collectives et radiations d'entreprises ; la source ingérée par data-platform.
- Exemple : Une journée de BODACC compte environ 32 000 annonces, exportées par l'API OpenDataSoft puis rangées dans la zone raw.

## cardinalité
- Définition : Nombre de valeurs distinctes d'une colonne : faible pour une date (365 par an), très forte pour un identifiant.
- Exemple : Partitionner par `siren` créerait des millions de dossiers minuscules : sa cardinalité est bien trop forte.
- Carte : data-lake-cardinalite-partitions

## CDC
- Définition : Change Data Capture : capture de chaque insertion, modification et suppression d'une base, lues dans son journal de transactions, pour les rejouer ailleurs dans l'ordre.
- Exemple : Debezium lit le journal de PostgreSQL et envoie chaque changement vers le data lake, suppressions comprises.
- Alias : Change Data Capture
- Carte : ingestion-cdc-journal-des-changements

## changement parallèle
- Définition : Façon de modifier un format partagé en trois temps : accepter l'ancien et le nouveau (expand), migrer les producteurs, puis retirer l'ancien (contract).
- Exemple : La Lambda du catalogue a accepté les cartes v3 et v4 ensemble, le temps que tous les fichiers passent en v4.
- Alias : expand / contract, expand-contract
- Carte : evolution-de-schema-changement-parallele

## chargement incrémental
- Définition : Ingestion qui ne lit que les données nouvelles depuis le dernier run, au lieu de relire toute la source à chaque fois.
- Exemple : Chaque matin, l'ingestion ne lit que la parution BODACC de la veille (59 Mo), pas les 51 millions d'annonces.
- Alias : incrémental, ingestion incrémentale
- Carte : ingestion-full-ou-incremental

## clé de Luhn
- Définition : Chiffre de contrôle calculé à partir des autres chiffres d'un numéro (SIREN, carte bancaire) : il détecte une faute de frappe, pas un numéro inventé.
- Exemple : `552100554` a une clé de Luhn correcte : le numéro est bien formé, rien ne prouve qu'il figure dans l'annonce.
- Alias : Luhn, algorithme de Luhn

## clé étrangère
- Définition : Colonne d'une table qui contient la clé primaire d'une ligne d'une autre table, pour les relier ; une base relationnelle en garantit la validité.
- Exemple : `annonce.siren` pointe vers `entreprise.siren` ; DynamoDB n'a pas de clé étrangère, d'où `ConditionCheck` dans une transaction.
- Alias : clés étrangères, foreign key
- Carte : AWS/dynamodb-conditioncheck

## clé métier
- Définition : Identifiant qui a un sens dans le domaine (numéro d'annonce, SIREN), par opposition à un identifiant technique inventé par le système.
- Exemple : Dans le BODACC, la paire (bulletin, numéro d'annonce) est la clé métier qui sert à dédoublonner.
- Alias : clés métier
- Carte : ingestion-dedoublonnage-derniere-version

## clé primaire
- Définition : Colonne ou ensemble de colonnes dont la valeur identifie une ligne de façon unique dans une table.
- Exemple : Dans DynamoDB, la clé primaire est la clé de partition seule, ou le couple clé de partition + clé de tri.
- Alias : clés primaires, primary key

## CSV
- Définition : Comma-Separated Values : format texte tabulaire, une ligne par enregistrement, champs séparés par une virgule (souvent un point-virgule en France).
- Exemple : Les exports data.gouv sont souvent des CSV à `;` : `csv.DictReader(f, delimiter=";")`.
- Alias : Comma-Separated Values
- Carte : Python/fichiers-formats-csv-point-virgule

## cycle
- Définition : Dans un graphe de dépendances, chemin qui revient à son point de départ (A avant B, B avant A) : aucun ordre d'exécution n'est alors possible.
- Exemple : Deux cartes prérequises l'une de l'autre forment un cycle : la validation refuse de les publier.
- Alias : cycles
- Carte : dag-cycle-ordre-impossible

## DAG
- Définition : Directed Acyclic Graph, graphe orienté acyclique : des éléments reliés par des flèches « A avant B », sans boucle ; il décrit des dépendances entre tâches.
- Exemple : Les tâches d'un pipeline, les cibles d'un Makefile et les prérequis des cartes forment des DAG.
- Alias : graphe orienté acyclique, Directed Acyclic Graph
- Carte : dag-graphe-de-dependances

## data lake
- Définition : Ensemble de fichiers posés dans un stockage d'objets (S3), rangés par zones, que plusieurs moteurs de requête lisent sans serveur de base de données.
- Exemple : Le data lake de data-platform : un bucket raw pour le BODACC brut, puis processed pour les données typées.
- Alias : lake, lac de données
- Carte : data-lake-trois-zones

## dataset
- Définition : Jeu de données publié par une source sous un nom, avec son schéma (champs, types) et sa date de mise à jour.
- Exemple : Les métadonnées du dataset BODACC d'OpenDataSoft listent ses 32 champs typés et l'heure de sa dernière mise à jour.
- Alias : jeu de données, datasets
- Carte : api-de-donnees-metadonnees-schema

## date logique
- Définition : Date que traite un run planifié (souvent la veille), reçue en paramètre plutôt que lue sur l'horloge : rejouer un jour passé reste possible.
- Exemple : Le déclencheur du 24 passe `jour = 2026-10-23` à la Lambda ; un rejeu le 26 repasse la même date.
- Alias : logical_date
- Carte : ingestion-date-logique-pas-horloge

## DFS
- Définition : Depth-First Search, parcours en profondeur : suivre chaque chemin d'un graphe jusqu'au bout avant de revenir en arrière ; sert notamment à détecter les cycles.
- Exemple : `checkLinks` de l'app de révision parcourt les prérequis en profondeur et affiche le cycle trouvé, `a → b → a`.
- Alias : parcours en profondeur, Depth-First Search
- Carte : dag-dfs-trois-etats

## donnée personnelle
- Définition : Information qui permet d'identifier une personne physique, directement ou non (nom, date de naissance, adresse) ; son traitement est encadré par le RGPD.
- Exemple : Une annonce BODACC cite nom et date de naissance des dirigeants : des données personnelles à masquer avant un appel au LLM.
- Alias : données personnelles, PII
- Carte : IA/extraction-masquer-donnees-personnelles

## DuckDB
- Définition : Base de données analytique embarquée, sans serveur, qui exécute du SQL directement sur des fichiers CSV, JSON ou Parquet, locaux ou sur S3.
- Exemple : `select count(*) from read_json_auto('s3://…/part-0001.jsonl.gz')` compte les annonces d'une partition BODACC.
- Carte : duckdb-ou-athena

## ETL
- Définition : Extract, Transform, Load : chaîne qui extrait des données d'une source, les transforme, puis les charge dans une cible.
- Exemple : Un job Glue ETL lit le JSONL brut de BODACC, le nettoie et écrit du Parquet en zone processed.
- Alias : Extract Transform Load
- Carte : AWS/glue-athena-glue-ou-emr

## exactly-once
- Définition : Garantie qu'un message ou une étape est traité exactement une fois, sans perte ni doublon ; rare et coûteuse, on vise plutôt la livraison au moins une fois plus l'idempotence.
- Exemple : Un workflow Step Functions Standard exécute chaque étape exactly-once ; un workflow Express, at-least-once.
- Alias : exactement une fois
- Carte : AWS/step-functions-standard-ou-express

## fan-out
- Définition : Diffusion d'un même message à plusieurs consommateurs, chacun le traitant de son côté.
- Exemple : Un topic SNS abonné à deux files SQS : chaque événement part à la fois vers l'indexation et vers l'alerte.
- Alias : fanout
- Carte : AWS/sns-topic-fan-out

## HyperLogLog
- Définition : Algorithme qui estime le nombre de valeurs distinctes d'une colonne avec très peu de mémoire, au prix d'une erreur de quelques pour cent.
- Exemple : `count(distinct id)` d'OpenDataSoft renvoie 34 299 pour 32 373 lignes : une estimation HyperLogLog, pas un compte exact.
- Carte : duckdb-summarize-profil

## Iceberg
- Définition : Apache Iceberg : format de table ouvert qui tient la liste versionnée des fichiers d'une table, pour des écritures tout-ou-rien, des mises à jour et la relecture d'états passés.
- Exemple : Les tables `processed` de data-platform seront des tables Iceberg sur S3, écrites par PySpark.
- Alias : Apache Iceberg
- Carte : data-lake-format-de-table

## idempotent
- Définition : Se dit d'une opération qui donne le même résultat qu'on l'exécute une ou plusieurs fois (comme un PUT HTTP, contrairement à un POST).
- Exemple : Rejouer l'ingestion du 20 octobre réécrit les mêmes clés S3 avec les mêmes octets : le job est idempotent.
- Alias : idempotence, idempotente, idempotents
- Carte : ingestion-idempotence-ecraser

## ingestion
- Définition : Étape qui fait entrer des données d'une source externe dans la plateforme, sans les transformer ou presque.
- Exemple : La Lambda `ingest-bodacc` télécharge chaque jour les annonces BODACC et les écrit en JSONL dans la zone raw.
- Alias : ingérer, ingéré
- Carte : ingestion-pull-ou-push

## INSEE
- Définition : Institut national de la statistique et des études économiques : attribue les numéros SIREN et publie des données publiques, dont le répertoire Sirene.
- Exemple : Le répertoire Sirene de l'INSEE relie chaque SIREN cité dans une annonce BODACC à une entreprise.

## isolation
- Définition : Propriété d'une transaction : ses écritures à moitié faites restent invisibles aux autres lectures, qui voient tout ou rien.
- Exemple : `TransactGetItems` ne renvoie jamais l'état d'une `TransactWriteItems` à moitié appliquée.
- Alias : isolation des transactions
- Carte : AWS/dynamodb-transactgetitems

## jitter
- Définition : Part aléatoire ajoutée au délai entre deux tentatives, pour que des clients en échec ne réessaient pas tous au même instant.
- Exemple : 50 Lambdas refusées attendent chacune un délai tiré entre 0 et 4 s au lieu de 4 s pile : leurs appels s'étalent.
- Carte : ingestion-retry-backoff-exponentiel

## jointure
- Définition : Opération SQL qui assemble les lignes de deux tables selon une colonne commune (`JOIN … ON`).
- Exemple : Joindre les annonces BODACC à la table des entreprises par `siren` : Athena sait le faire, DynamoDB non.
- Alias : jointures, JOIN
- Carte : AWS/dynamodb-jointures-aurora

## JSON Lines
- Définition : Format texte qui contient un objet JSON complet par ligne : on le lit et l'écrit ligne à ligne, sans charger tout le fichier.
- Exemple : `part-0001.jsonl.gz` de la zone raw contient une annonce BODACC par ligne.
- Alias : JSONL, NDJSON
- Carte : formats-json-lines-un-objet-par-ligne

## JSON Schema
- Définition : Standard qui décrit en JSON la forme attendue d'un document : champs, types, champs requis, valeurs permises ; des outils valident ou contraignent un document avec lui.
- Exemple : `model_json_schema()` de pydantic produit le JSON Schema envoyé à Bedrock pour imposer la forme de la réponse.
- Alias : schéma JSON
- Carte : IA/extraction-sortie-structuree-schema

## JSONPath
- Définition : Syntaxe de chemin qui désigne une valeur dans un document JSON : `$` pour la racine, puis les champs imbriqués (`$.detail.object.key`).
- Exemple : `input_paths = { key = "$.detail.object.key" }` extrait la clé S3 d'un événement EventBridge.
- Carte : AWS/sqs-eventbridge-input-transformer

## keyset
- Définition : Pagination qui demande les N lignes situées après la dernière clé reçue, triées sur cette clé : coût constant et pas de plafond.
- Exemple : `where numeroannonce > 1200 order by numeroannonce limit 100` lit la page suivante de l'API BODACC.
- Alias : pagination keyset
- Carte : api-de-donnees-keyset-derniere-cle

## lakehouse
- Définition : Data lake auquel un format de table (Iceberg, Delta Lake) ajoute ce qu'offrait une base : mises à jour, transactions, schéma et historique.
- Exemple : Après l'ingestion brute, data-platform passe au lakehouse : tables Iceberg sur S3, écrites par PySpark.

## lecteur tolérant
- Définition : Programme qui lit les champs qu'il connaît et ignore les autres : un producteur peut ajouter un champ sans le casser.
- Exemple : Le handler d'ingestion lit `event.get("date")` et ignore les clés `source` ou `execution_id` ajoutées par le déclencheur.
- Alias : lecture tolérante
- Carte : ingestion-evenement-cles-inconnues

## lignage
- Définition : Lien entre chaque donnée et son origine (fichier source lu, run qui l'a produite, heure d'ingestion), pour remonter d'une valeur fausse à sa cause.
- Exemple : Chaque ligne de `processed` porte `_source`, `_ingere_le` et `_run_id` : on retrouve en une requête le fichier brut fautif.
- Alias : lineage
- Carte : data-lake-lignage

## livraison au moins une fois
- Définition : Garantie qu'un message n'est jamais perdu mais peut arriver plusieurs fois ; le consommateur doit donc être idempotent.
- Exemple : Une file SQS standard livre au moins une fois : la Lambda qui la lit réécrit la même partition sans dommage.
- Alias : at-least-once, au moins une fois
- Carte : ingestion-at-least-once-doublon-normal

## log structuré
- Définition : Ligne de log écrite en JSON, avec des champs nommés qu'un outil peut filtrer et agréger, au lieu d'une phrase en texte libre.
- Exemple : `{"run": "r42", "lus": 32373}` se filtre ensuite dans CloudWatch Logs Insights par la valeur de `run`.
- Alias : logs structurés, log JSON, logs JSON
- Carte : qualite-logs-json-filtrables

## manifest
- Définition : Petit fichier JSON écrit après les données d'une partition : il la déclare complète et décrit son contenu (nombre de lignes, empreinte, format).
- Exemple : `_MANIFEST.json` sous `date=2026-10-20/` annonce `count: 32373` et le sha256 du JSONL non compressé.
- Alias : manifests, _MANIFEST.json
- Carte : ingestion-manifest-success-qui-decrit

## micro-batch
- Définition : Traitement par petits lots déclenchés à intervalle court (quelques minutes) : des données presque fraîches, avec la simplicité d'un traitement par lot.
- Exemple : Un job déclenché toutes les 5 minutes traite les fichiers arrivés depuis le passage précédent.
- Alias : micro-batches
- Carte : ingestion-batch-ou-streaming

## migration
- Définition : Changement planifié du schéma ou des données d'une base existante (ajout de colonne, renommage, conversion), appliqué de façon contrôlée.
- Exemple : Donner un nouvel attribut aux anciens items DynamoDB demande une migration : la table, elle, n'a pas de schéma à changer.
- Alias : migrations, migration de schéma

## normalisation
- Définition : Organisation d'une base relationnelle en tables sans redondance, reliées par des clés ; DynamoDB fait souvent l'inverse et copie les données utiles.
- Exemple : En SQL, annonces et entreprises sont deux tables normalisées ; en DynamoDB, on recopie le nom de l'entreprise dans chaque annonce.
- Alias : base normalisée, tables normalisées

## ODSQL
- Définition : Langage de requête de l'API OpenDataSoft, proche de SQL, passé dans l'URL (`where`, `select`, `order_by`) : typé, limité à un dataset, sans jointure.
- Exemple : `where=dateparution=date'2026-10-20'` fait filtrer par le serveur la parution du 20 octobre.
- Carte : api-de-donnees-filtrer-cote-serveur

## OpenDataSoft
- Définition : Plateforme de publication de données ouvertes qui sert le BODACC par une API web : métadonnées, enregistrements paginés et export complet.
- Exemple : L'ingestion appelle `/api/explore/v2.1/` d'OpenDataSoft pour exporter une journée BODACC en JSON Lines.
- Alias : ODS
- Carte : api-de-donnees-metadonnees-schema

## orchestrateur
- Définition : Outil qui exécute un graphe de tâches : il lance chacune quand ses prérequis ont réussi et gère reprises, rejeux, planification et historique.
- Exemple : Airflow, Dagster et AWS Step Functions sont des orchestrateurs.
- Alias : orchestrateurs, orchestration
- Carte : dag-orchestrateur

## outbox
- Définition : Motif où l'événement à publier est écrit dans la même transaction que la donnée, puis envoyé par un processus séparé : ni perte ni envoi fantôme.
- Exemple : `TransactWriteItems` écrit l'item et une entrée outbox ; un consommateur de DynamoDB Streams publie ensuite l'événement.
- Alias : transactional outbox, motif outbox

## pagination
- Définition : Lecture d'un gros résultat d'API en plusieurs réponses successives (pages), en sautant N lignes, en repartant d'une clé ou d'un jeton fourni par le serveur.
- Exemple : L'API BODACC plafonne la pagination par décalage à 10 000 lignes : une journée de 32 373 annonces passe par l'export.
- Alias : paginer
- Carte : api-de-donnees-pagination-choisir

## Parquet
- Définition : Apache Parquet : format de fichier binaire qui range les données par colonne, typées et compressées ; un moteur ne lit que les colonnes demandées.
- Exemple : Passer `processed` du JSON Lines au Parquet réduit fortement les octets scannés, donc payés, par Athena.
- Alias : Apache Parquet
- Carte : formats-parquet-vs-csv

## partition
- Définition : Partie d'une table rangée sous son propre préfixe (une journée : `dt=2026-10-20/`) : une requête filtrée sur cette valeur ne lit qu'elle.
- Exemple : Chaque run d'ingestion réécrit entièrement sa partition `date=…/` du bucket raw, et rien d'autre.
- Alias : partitions, partitionner, partitionnement, partitionné, partitionnée
- Carte : data-lake-partitionnement-hive

## partitionnement Hive
- Définition : Convention héritée d'Apache Hive : un segment `cle=valeur` dans le chemin (`date=2026-10-20/`) devient une colonne filtrable pour Athena, Spark ou DuckDB.
- Exemple : `WHERE date = '2026-10-20'` ne lit que le dossier `date=2026-10-20/` du bucket raw.
- Alias : Hive, convention Hive, style Hive, partitions Hive
- Carte : data-lake-partitionnement-hive

## percentile
- Définition : Valeur sous laquelle tombe un pourcentage donné des mesures : p99 = 99 % des valeurs sont inférieures.
- Exemple : Une alarme sur le p99 de `Duration` voit les invocations lentes que la moyenne masque.
- Alias : percentiles, p99, p95, p50

## pipeline de données
- Définition : Chaîne d'étapes automatiques qui lit des données d'une source, les transforme et les écrit vers une destination.
- Exemple : data-platform : export BODACC vers la zone raw, puis typage vers processed, puis exports vers out.
- Alias : pipelines de données
- Carte : data-lake-trois-zones

## quarantaine
- Définition : Zone où un pipeline range les lignes invalides avec leur erreur, au lieu de faire échouer tout le lot.
- Exemple : Une annonce sans SIREN lisible part dans `rejets/dt=…` avec le message de validation ; les 32 000 autres continuent.
- Alias : rejets
- Carte : qualite-quarantaine-lignes-invalides

## quota
- Définition : Nombre maximal d'appels qu'un service accepte par période (seconde, minute, jour) ; au-delà, il refuse avec une erreur « trop de requêtes ».
- Exemple : L'API BODACC accorde 5 millions d'appels par jour, partagés par tous ses clients, remis à zéro à minuit UTC.
- Alias : quotas, rate limit
- Carte : api-de-donnees-quota-partage

## rejeu
- Définition : Nouvelle exécution d'un job sur une entrée déjà traitée (même date), après un échec ou un correctif ; sans risque seulement si le job est idempotent.
- Exemple : `make replay` relance l'ingestion d'une date passée : la partition et son manifest sont réécrits aux mêmes clés.
- Alias : rejeux, rejouer, rejoué
- Carte : ingestion-rejeu-memes-cles

## réplication
- Définition : Copie automatique et continue des données d'un emplacement vers un autre (autre région, autre base), pour la résilience ou la proximité.
- Exemple : La réplication S3 copie chaque nouvel objet d'un bucket vers un bucket d'une autre région.
- Alias : répliquer, répliqué
- Carte : AWS/s3-replication-nouveaux

## retry
- Définition : Nouvelle tentative automatique d'un appel en échec, réservée aux erreurs passagères (surcharge, coupure réseau), avec un délai entre les essais.
- Exemple : Le client BODACC retente un HTTP 503 avec backoff, mais jamais un HTTP 400 : la requête elle-même serait fausse.
- Alias : retries, réessai, réessayer
- Carte : ingestion-retry-backoff-exponentiel

## RGPD
- Définition : Règlement général sur la protection des données : loi européenne qui encadre la collecte et le traitement des données personnelles (minimisation, durée, sécurité).
- Exemple : Les dirigeants cités dans le BODACC sont des personnes physiques : leurs noms ne partent pas tels quels vers un service externe.
- Alias : GDPR
- Carte : data-lake-pseudonymiser-hmac

## run
- Définition : Une exécution d'un job ou d'un pipeline, souvent identifiée par un `run_id` partagé par ses données et ses logs.
- Exemple : Le run du 24 octobre ingère la parution du 23 et écrit son `run_id` dans chaque ligne de log.
- Alias : runs, run_id
- Carte : data-lake-lignage

## schema-on-read
- Définition : Approche où le schéma s'applique à la lecture, pas à l'écriture : les fichiers bruts restent tels quels et chaque requête les interprète.
- Exemple : Une table Glue décrit le JSONL déjà dans S3 ; Athena applique ce schéma au moment de la requête.
- Alias : schéma à la lecture
- Carte : data-lake-schema-a-la-lecture

## SIREN
- Définition : Numéro à 9 chiffres qui identifie une entreprise française, dont le dernier est une clé de contrôle ; il se garde en texte pour ne perdre aucun zéro initial.
- Exemple : Les annonces BODACC citent le SIREN de l'entreprise concernée, par exemple `483609327`.
- Alias : numéro SIREN

## snapshot
- Définition : Version figée d'une table Iceberg, créée à chaque écriture : la liste exacte de ses fichiers à cet instant, relisible plus tard (time travel).
- Exemple : `FOR TIMESTAMP AS OF` dans Athena relit la table telle qu'elle était avant le `MERGE` d'hier.
- Alias : snapshots, time travel
- Carte : data-lake-snapshot-time-travel

## Spark
- Définition : Apache Spark : moteur de calcul qui découpe un traitement de données en tâches exécutées en parallèle sur plusieurs machines ; PySpark est son interface Python.
- Exemple : Un job PySpark lit les partitions JSON Lines du bucket raw et écrit des tables Parquet ou Iceberg.
- Alias : Apache Spark, PySpark

## transaction
- Définition : Groupe d'écritures appliquées toutes ou aucune : si l'une échoue, aucune n'est conservée.
- Exemple : `TransactWriteItems` crée l'utilisateur et son item `EMAIL#` ensemble ; S3, lui, n'offre aucune transaction.
- Alias : transactions
- Carte : AWS/dynamodb-transactwriteitems

## tri topologique
- Définition : Mise en liste des éléments d'un graphe de dépendances où chacun vient après tous ses prérequis.
- Exemple : `graphlib.TopologicalSorter(g).static_order()` range les tâches d'un pipeline dans un ordre exécutable.
- Alias : ordre topologique
- Carte : dag-tri-topologique

## Trino
- Définition : Moteur SQL distribué open source qui interroge les données là où elles sont (S3, bases) ; le moteur actuel d'Athena en dérive.
- Exemple : Une requête Athena sur le JSONL BODACC est exécutée par un moteur issu de Trino, qui ne lit que les partitions filtrées.

## upsert
- Définition : Écriture qui met à jour la ligne si sa clé existe déjà et l'insère sinon (`MERGE` en SQL) : rejouer la même ligne ne la duplique pas.
- Exemple : Un rectificatif BODACC remplace, par upsert sur l'id de l'annonce visée, la version précédente.
- Carte : ingestion-idempotence-ecraser

## verrou optimiste
- Définition : Contrôle de concurrence sans verrou posé : on écrit seulement si la donnée n'a pas changé depuis sa lecture, sinon on relit et on recommence.
- Exemple : `ConditionExpression: version = :lue` refuse la mise à jour si un autre processus a incrémenté `version` entre-temps.
- Alias : verrouillage optimiste, optimistic locking
- Carte : AWS/dynamodb-verrou-optimiste

## watermark
- Définition : Repère conservé du dernier élément traité avec succès (jour, clé) ; le run suivant reprend juste après lui.
- Exemple : Le watermark vaut `2026-10-22` : le prochain run traite le 23, puis tous les jours manqués jusqu'à hier.
- Alias : watermarks
- Carte : ingestion-watermark-reprendre

## zone processed
- Définition : Zone du data lake qui contient les données validées et typées (dates en date, SIREN en texte), prêtes à être requêtées.
- Exemple : Une annonce BODACC passe de `raw` à `processed` après validation par un modèle pydantic.
- Alias : processed
- Carte : data-lake-processed-type

## zone raw
- Définition : Zone du data lake qui garde les données reçues de la source octet pour octet, écrites une fois et jamais modifiées.
- Exemple : `s3://$RAW_BUCKET/bodacc/date=2026-10-20/part-0001.jsonl.gz` garde l'export BODACC tel que reçu.
- Alias : raw
- Carte : data-lake-raw-immuable
