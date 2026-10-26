---
title: "Cartes · Glue et Athena"
type: cartes
langage: AWS
chapitre: Données et analytique
cours: Glue et Athena
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Glue et Athena
AWS · Glue et Athena : catalogue, coût, choisir, partitions, iceberg, gouvernance (format spec v4 de revision-pwa).

## 1. table Glue : des métadonnées
- Id : glue-athena-table-metadonnees
- Sous-thème : catalogue
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Mots-clés : Athena, EMR, ETL, schema-on-read
- Définition : Une table du Glue Data Catalog décrit schéma, format, partitions et emplacement S3 ; elle ne contient aucune donnée.
- Contexte : Athena, Glue ETL, EMR et Redshift Spectrum lisent le même catalogue : une table déclarée une fois sert à tous les moteurs. Le schéma est appliqué à la lecture (schema-on-read) : un fichier qui ne colle pas n'échoue pas à l'écriture, mais donne des `NULL` ou une erreur à la requête. En Terraform : `aws_glue_catalog_table`.
- Usage : ✅ déclarer `processed/annonces` une fois, l'interroger depuis Athena et Spark · ❌ attendre du catalogue une validation des données : contrôler au job (pydantic, tests).

```sql
-- Exemple 1 : table externe Parquet
CREATE EXTERNAL TABLE annonces (
  siren string,
  tribunal string,
  date_parution date
)
PARTITIONED BY (dt string)
STORED AS PARQUET
LOCATION
  's3://dp-dev-processed/annonces/';
```

- Quiz : Que devient le contenu de `s3://dp-dev-processed/annonces/` après `DROP TABLE annonces` ?
- [ ] Supprimé avec la table
- [ ] Déplacé dans une corbeille 30 jours
- [x] Intact, seul le schéma disparaît
- [ ] Supprimé, sauf si le bucket est versionné
- Réponse : intact : une table `EXTERNAL` ne supprime que ses métadonnées ; on la recrée et les données réapparaissent.

## 2. Athena : payer au scanné
- Id : glue-athena-cout-au-scanne
- Sous-thème : coût
- Type : concept
- Niveau : 1
- Profils : débutant, data, ops
- Voir aussi : Data engineering/formats-parquet-vs-csv, Data engineering/data-lake-partitionnement-hive
- Mots-clés : Parquet, partition, data lake
- Définition : Athena facture les octets lus dans S3 par requête : Parquet et le filtre sur la partition `dt` réduisent ce qui est scanné.
- Contexte : En eu-west-3, Athena coûte 7 $ par To scanné, avec un minimum de 10 Mo par requête. Sur du JSON ou du CSV, chaque requête relit les fichiers en entier ; sur Parquet, Athena ne lit que les colonnes citées et saute des blocs grâce aux min / max ; avec `dt` dans le `WHERE`, il ne lit que le préfixe du jour. La console affiche « Data scanned » après chaque requête : c'est la facture.
- Usage : ✅ `processed` en Parquet partitionné, colonnes nommées, `WHERE dt = …` · ❌ `SELECT *` sans filtre de partition sur tout le lake ; `raw` en JSON requêté tous les jours.

```sql
-- Exemple 1 : 2 colonnes, 1 jour
SELECT tribunal, count(*) AS n
FROM annonces
WHERE dt = '2026-10-23'
GROUP BY tribunal;
-- → lit tribunal + dt du 23
--   quelques Mo, pas tout le lake
```

```python
# Exemple 2 : prix d'une requête
prix_to = 7          # $ / To, Paris
scanne_mo = 40
facture_mo = max(scanne_mo, 10)
cout = facture_mo / 1_000_000 * prix_to
round(cout, 6)       # → 0.00028
```

- Quiz : Une requête sur un petit jour ne scanne que 200 Ko : combien de données Athena facture-t-elle ?
- [ ] 200 Ko
- [ ] 1 Mo
- [x] 10 Mo
- [ ] Rien sous 1 Go
- Réponse : 10 Mo : Athena arrondit chaque requête à 10 Mo minimum ; mille petites requêtes coûtent donc au moins 10 Go scannés.

## 3. Athena : ou un entrepôt Redshift
- Id : glue-athena-athena-ou-redshift
- Sous-thème : choisir
- Type : choisir
- Niveau : 1
- Profils : débutant, data
- Prérequis : glue-athena-cout-au-scanne
- Voir aussi : couts-cout-au-repos
- Mots-clés : Redshift, Trino, BI
- Définition : Athena exécute du SQL directement sur S3, payé au To scanné ; Redshift est un entrepôt pour une BI lourde, concurrente et répétitive.
- Contexte : Athena (moteur Trino) n'a rien à démarrer : 0 $ sans requête, ce qui colle à un usage ponctuel. Chaque requête rescanne S3 : la même requête lancée 100 fois est payée 100 fois. Redshift Serverless garde les données chargées et optimisées, facture le calcul (RPU-heure) pendant les requêtes, et amortit une charge répétitive sur les mêmes tables.
- Usage : ✅ Athena pour l'exploration, quelques requêtes par jour, jobs d'export · ❌ dizaines de dashboards rafraîchis en continu sur les mêmes To : Redshift.

```
# Exemple 1 : la décision
Besoin  : 3 analystes, quelques
          requêtes par jour sur S3
→ Choix : Athena
Pourquoi: rien à provisionner,
          0 $ sans requête
Écarté  : Redshift (chargement,
          capacité, pour peu d'usage)
```

```python
# Exemple 2 : coût mensuel Athena
prix_to = 7             # $ / To, Paris
requetes = 20 * 30      # 20 par jour
go_par_requete = 2
to = requetes * go_par_requete / 1000
round(to * prix_to, 2)  # → 8.4  ($/mois)
```

- Quiz : 60 dashboards rafraîchis toutes les 5 min sur les mêmes 2 To : Athena reste-t-elle le bon choix ?
- [ ] Oui : Athena facture à l'heure, pas au scan
- [ ] Oui : 0 $ au repos, donc toujours moins cher
- [ ] Non : DynamoDB pour les dashboards
- [x] Non : un entrepôt (Redshift) amortit la charge
- Réponse : non, plutôt Redshift (Serverless) : Athena rescanne et refacture à chaque rafraîchissement ; un entrepôt amortit une charge répétitive et concurrente.

## 4. Glue : partition non déclarée
- Id : glue-athena-partition-non-declaree
- Sous-thème : partitions
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : glue-athena-table-metadonnees
- Mots-clés : partition, catalogue Glue, crawler, partition projection
- Définition : Athena ne lit que les partitions enregistrées dans le catalogue Glue ; un nouveau préfixe `dt=` doit y être ajouté.
- Contexte : Écrire des fichiers dans S3 ne met pas le catalogue à jour. Trois façons d'ajouter une partition : `ALTER TABLE ADD PARTITION` (ciblé, rapide), `MSCK REPAIR TABLE` (liste tout le préfixe, lent sur un gros lake, seulement pour les clés au format Hive), un crawler Glue (payant à la DPU-heure). La partition projection supprime le besoin.
- Usage : ✅ `ADD PARTITION` en fin de job d'écriture, quand on connaît le jour écrit · ❌ `MSCK REPAIR` à chaque run sur des années de partitions.

```sql
-- Exemple 1 : déclarer le jour écrit
ALTER TABLE annonces
ADD IF NOT EXISTS
PARTITION (dt = '2026-10-23')
LOCATION
 's3://dp-dev-processed/annonces/dt=2026-10-23/';

SELECT count(*) FROM annonces
WHERE dt = '2026-10-23';
-- → 32 104
```

- Quiz : Le job écrit `dt=2026-10-24/` sans `ADD PARTITION` : que renvoie le `count(*)` du 24 ?
- [ ] `HIVE_PARTITION_SCHEMA_MISMATCH`
- [ ] Le bon total : Athena liste S3
- [ ] `TABLE_NOT_FOUND`
- [x] `0`, sans erreur
- Réponse : `0`, sans erreur : la partition est inconnue du catalogue, Athena ne lit pas ce préfixe ; un pipeline « vert » mais vide.

## 5. Spark : Glue ou EMR
- Id : glue-athena-glue-ou-emr
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : data
- Voir aussi : step-functions-sync-attendre-job
- Mots-clés : Spark, DPU, EMR, ETL
- Définition : Au-delà de ce qu'une machine traite, on passe à Spark : Glue ETL serverless d'abord, EMR (Serverless) quand il faut régler finement le moteur.
- Contexte : Glue facture 0,44 $ par DPU-heure à Paris (0,308 $ à partir de Glue 6.0), à la seconde avec une minute minimum, et ajoute catalogue, crawlers et signets de reprise. EMR Serverless facture vCPU et mémoire, laisse choisir la version de Spark et sa configuration, et revient moins cher à grande échelle. Sous quelques Go par jour, Spark est surdimensionné : Lambda ou Fargate suffisent.
- Usage : ✅ Glue pour des jobs ETL standards sur des dizaines de Go · ❌ Spark pour 50 Mo par jour : Lambda avec Python (pyarrow) ; besoin de réglages fins : EMR.

```python
# Exemple 1 : faut-il Spark ?
go_par_jour = 0.05     # BODACC
go_par_jour < 10       # → True
# → 50 Mo/jour : Lambda suffit

dpu_h = 0.44           # $ (Glue, Paris)
dpus, minutes = 10, 1  # job court
glue = dpus * dpu_h * max(minutes, 1) / 60
round(glue, 3)         # → 0.073
```

- Quiz : 2 To à joindre chaque nuit, une équipe experte en Spark qui veut ses versions et ses réglages : quel service ?
- [ ] Glue : seul service Spark serverless
- [x] EMR (Serverless ou cluster)
- [ ] Lambda en parallèle avec `Map`
- [ ] Athena avec des `JOIN`
- Réponse : EMR : plus de contrôle (versions, configuration Spark) et moins cher à grande échelle ; EMR Serverless est lui aussi serverless, Glue gagne en simplicité sur des jobs standards.

## 6. dashboards : QuickSight ou React
- Id : glue-athena-quicksight-ou-react
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : data, web
- Voir aussi : glue-athena-cout-au-scanne
- Mots-clés : BI, Redshift, API Gateway
- Définition : QuickSight sert des dashboards BI managés sur Athena ou Redshift ; une appli React se justifie quand l'écran est un produit.
- Contexte : QuickSight donne filtres, exports et nouveaux graphes sans développement, facturé par utilisateur (auteurs et lecteurs) ; son cache SPICE évite de rescanner Athena à chaque ouverture. Une appli React sur une API (API Gateway, Lambda) coûte du développement pour chaque écran, mais maîtrise l'UX, la marque et les droits. Le critère : qui consomme, et qui fait évoluer l'écran.
- Usage : ✅ QuickSight pour des analystes internes et des KPI qui changent souvent · ❌ QuickSight pour un écran vendu à des clients externes dans le produit : React + API.

```
# Exemple 1 : la décision
Besoin  : 5 analystes internes,
          filtres, exports, tous
          les mois de nouveaux KPI
→ Choix : QuickSight sur Athena
Pourquoi: self-service, pas de
          dev à chaque nouveau KPI
Écarté  : React + API (chaque
          graphe = une demande dev)
```

- Quiz : L'écran « procédures du secteur » est vendu à des clients externes dans le produit : quel choix ?
- [x] React + une API maison
- [ ] QuickSight, un compte par client
- [ ] Athena en accès direct pour les clients
- [ ] Un export CSV quotidien dans S3
- Réponse : React + API (Lambda, Athena ou DynamoDB derrière) : UX, marque et droits maîtrisés dans le produit ; QuickSight embarqué existe, mais avec un coût par session et une UX contrainte.

## 7. catalogue : crawler ou projection
- Id : glue-athena-crawler-ou-projection
- Sous-thème : partitions
- Type : choisir
- Niveau : 2
- Profils : data
- Prérequis : glue-athena-partition-non-declaree
- Mots-clés : crawler, partition, DPU, partition projection
- Définition : Pour qu'Athena voie les nouvelles partitions, on choisit entre crawler Glue, `ADD PARTITION` en fin de job ou partition projection.
- Contexte : Trois options, trois coûts. Le crawler relit S3 et infère schéma et partitions, facturé à la DPU-heure (10 min minimum par exécution) : pratique pour découvrir une source, imprévisible en production. `ADD PARTITION` est exact, gratuit et vu par tous les moteurs, mais ajoute une étape au job. La projection n'a rien à maintenir, mais seul Athena la voit.
- Usage : ✅ projection pour des partitions `dt` régulières lues par Athena, `ADD PARTITION` si Spark lit aussi · ❌ crawler planifié chaque jour sur une table au schéma déjà connu.

```
# Exemple 1 : la décision
Besoin  : 1 partition dt par jour,
          lue par Athena seulement
→ Choix : partition projection
Pourquoi: rien à maintenir, 0 $
Écarté  : crawler quotidien (payé
          à la DPU-heure, schéma
          déjà connu)
Si Spark lit aussi : ADD PARTITION
          en fin de job
```

- Quiz : Un crawler parcourt `processed/annonces/` où deux jours ont des colonnes différentes : quel risque ?
- [ ] Aucun : il fusionne toujours les schémas
- [ ] Il échoue et ne crée aucune table
- [x] Il peut créer une table par jour au lieu d'une
- [ ] Il supprime les fichiers incompatibles
- Réponse : il peut créer une table par dossier `dt=` au lieu d'une table partitionnée : schémas trop différents ; d'où un schéma déclaré (Terraform) et la projection.

## 8. Athena : partition projection
- Id : glue-athena-partition-projection
- Sous-thème : partitions
- Type : concept
- Niveau : 3
- Profils : data, expert
- Prérequis : glue-athena-crawler-ou-projection
- Mots-clés : partition, catalogue Glue, EMR
- Définition : La partition projection calcule les partitions depuis des règles posées sur la table, sans les enregistrer : plus de `ADD PARTITION` quotidien.
- Contexte : Athena déduit les valeurs possibles de `dt` (type `date`, plage, format) et construit les chemins S3 avec `storage.location.template`. Plus rapide qu'une table à des milliers de partitions, et rien à maintenir. Limites : la projection ne sert qu'à Athena (Glue ETL, EMR et Spectrum ne la voient pas), et un jour projeté sans fichier renvoie simplement 0 ligne.
- Usage : ✅ partitions régulières et prévisibles (une par jour) lues par Athena · ❌ table aussi lue par Spark ou Glue via le catalogue : déclarer les partitions.

```sql
-- Exemple 1 : dt projeté par Athena
ALTER TABLE annonces
SET TBLPROPERTIES (
 'projection.enabled'='true',
 'projection.dt.type'='date',
 'projection.dt.format'='yyyy-MM-dd',
 'projection.dt.range'='2026-01-01,NOW',
 'storage.location.template'=
 's3://dp-dev-processed/annonces/dt=${dt}/'
);
-- dt=2026-10-24 lisible sans ADD
```

- Quiz : Projection activée, un `MSCK REPAIR TABLE` ajoute des partitions au catalogue : Athena s'en sert-il ?
- [ ] Oui, en plus des partitions projetées
- [ ] Oui, elles remplacent la projection
- [x] Non, il ne suit que les règles de projection
- [ ] Erreur : `MSCK` est refusé sur la table
- Réponse : non : avec la projection activée, Athena ignore les partitions enregistrées dans le catalogue et ne suit que les `TBLPROPERTIES`.

## 9. Iceberg : modifier des lignes
- Id : glue-athena-iceberg-modifier
- Sous-thème : iceberg
- Type : concept
- Niveau : 3
- Profils : data, expert
- Prérequis : glue-athena-table-metadonnees
- Mots-clés : data lake, Parquet, snapshot, RGPD
- Définition : Une table Apache Iceberg sur S3 ajoute `UPDATE`, `DELETE` et `MERGE` transactionnels au lake, utilisables depuis Athena, Glue et Spark.
- Contexte : Iceberg garde ses propres métadonnées (snapshots, manifestes) à côté des fichiers Parquet : une modification écrit de nouveaux fichiers et un nouveau snapshot, de façon atomique. On gagne aussi le time travel et l'évolution de schéma. Le prix : des petits fichiers et des fichiers de suppression s'accumulent, il faut compacter (`OPTIMIZE`) et purger les vieux snapshots (`VACUUM`).
- Usage : ✅ table mise à jour (statut d'entreprise), effacement RGPD, `MERGE` d'un delta quotidien · ❌ données en ajout seul, jamais modifiées : une table Parquet classique suffit.

```sql
-- Exemple 1 : effacer, fusionner
DELETE FROM annonces
WHERE siren = '483609327';
-- → réécrit seulement les fichiers
--   touchés, transaction atomique

MERGE INTO entreprises t
USING maj_du_jour s
ON t.siren = s.siren
WHEN MATCHED THEN UPDATE
  SET statut = s.statut;
```

- Quiz : Une demande RGPD impose d'effacer une personne d'une table Parquet classique (non Iceberg) : comment fait-on ?
- [ ] `DELETE FROM` dans Athena, comme sur Iceberg
- [ ] `UPDATE … SET nom = NULL` dans Athena
- [ ] `DROP PARTITION` sur la ligne concernée
- [x] On réécrit soi-même les fichiers concernés
- Réponse : on réécrit soi-même chaque fichier concerné : Athena refuse `DELETE` et `UPDATE` hors Iceberg, et Parquet est immuable ; d'où Iceberg dès qu'il y a des mises à jour.

## 10. DMS : copier une base
- Id : glue-athena-dms-cdc
- Sous-thème : choisir
- Type : choisir
- Niveau : 3
- Profils : data, expert
- Mots-clés : Iceberg, réplication, Transfer Family
- Définition : DMS copie une base vers une cible (S3, Aurora…) en chargement complet puis en continu (CDC), en lisant le journal de transactions.
- Contexte : Le CDC capte `INSERT`, `UPDATE` et `DELETE` au fil de l'eau, sans requêter les tables source ; côté Postgres, il faut activer la réplication logique. Vers S3, chaque ligne porte une colonne d'opération (`I`, `U`, `D`) : on reconstruit l'état avec un `MERGE`, typiquement dans une table Iceberg. DMS Serverless évite de dimensionner l'instance de réplication.
- Usage : ✅ base relationnelle d'un partenaire à garder à jour dans le lake · ❌ fichiers déposés (CSV, JSON) : Transfer Family ou dépôt S3 direct, puis le pipeline fichier.

```
# Exemple 1 : la décision
Besoin  : base Postgres d'un
          partenaire → lake, à jour
→ Choix : DMS full load + CDC
          → S3 en Parquet
Pourquoi: suit INSERT/UPDATE/DELETE
          sans requêter la source
Écarté  : export SQL nocturne (charge
          la base, perd les deletes)
```

- Quiz : Le partenaire envoie seulement un CSV par jour sur un serveur SFTP : quel service ?
- [ ] DMS, avec le CSV comme source
- [x] Transfer Family (SFTP vers S3)
- [ ] Kinesis Data Streams
- [ ] Glue crawler sur le serveur SFTP
- Réponse : Transfer Family : il expose un SFTP qui écrit dans S3, puis le pipeline fichier habituel ; DMS lit une base, pas des fichiers.

## 11. Lake Formation : accès par colonne
- Id : glue-athena-lake-formation-colonnes
- Sous-thème : gouvernance
- Type : concept
- Niveau : 3
- Profils : data, ops, expert
- Prérequis : glue-athena-table-metadonnees
- Voir aussi : iam-politique-de-ressource
- Mots-clés : catalogue Glue, IAM, Athena, Parquet
- Définition : Lake Formation accorde des droits par base, table, colonne ou ligne du catalogue, là où IAM ne voit que des objets S3 entiers.
- Contexte : Athena, Glue et EMR demandent à Lake Formation des identifiants temporaires limités à ce que l'utilisateur a le droit de voir, et filtrent colonnes et lignes à la lecture. Les droits se donnent en `GRANT` sur le catalogue, plus en politiques S3. Contrepartie : un modèle de permissions de plus à comprendre, et des moteurs non intégrés qui contournent le filtrage.
- Usage : ✅ données personnelles (dirigeants) à cacher à une partie des analystes · ❌ quelques utilisateurs qui voient tout : IAM et des buckets séparés suffisent.

```
# Exemple 1 : la décision
Besoin  : analystes sans accès aux
          noms de dirigeants
→ Choix : Lake Formation, colonne
          dirigeant exclue du grant
Pourquoi: filtrage colonne / ligne
          appliqué par Athena
Écarté  : politique IAM S3 (tout
          le fichier ou rien)
```

- Quiz : On refuse via IAM l'accès à un préfixe `dirigeant/` alors que la colonne est dans le même fichier Parquet : ça protège ?
- [ ] Oui : IAM masque la colonne à la lecture
- [x] Non : une colonne n'est pas un objet S3
- [ ] Oui, si la table est en Iceberg
- [ ] Oui, via une condition IAM par colonne
- Réponse : non : IAM autorise ou refuse des objets entiers ; soit on sort la colonne dans une autre table, soit on filtre avec Lake Formation.
