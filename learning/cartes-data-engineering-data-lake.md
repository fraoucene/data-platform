---
title: "Cartes · Data lake"
type: cartes
langage: Data engineering
chapitre: Stocker
cours: Data lake
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Data lake
Data engineering · Data lake : zones, partitions, fichiers, tables (format spec v3 de revision-pwa).

## 1. data lake : trois zones
- Id : data-lake-trois-zones
- Sous-thème : zones
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Mots-clés : Athena, Spark, partition
- Définition : Un data lake range les données par étape : `raw` brut et immuable, `processed` nettoyé et typé, `out` prêt à consommer.
- Contexte : Chaque zone a ses droits et sa rétention (sur AWS : un bucket par zone). `raw` garde la réponse de la source telle quelle : on rejoue n'importe quel traitement sans la rappeler. `processed` est typé et partitionné, lu par Athena et Spark ; `out` porte les exports métier. Contrairement à une base, on ne corrige jamais une ligne en place : on régénère la zone aval depuis l'amont.
- Usage : ✅ toute ingestion de source externe (BODACC), droits et rétentions distincts par zone · ❌ écrire le nettoyé par-dessus le brut : plus rien à rejouer après un bug.

```bash
# Exemple 1 : un jour BODACC, 3 zones
raw/bodacc/dt=2026-10-23/
  part-0001.jsonl.gz  # brut, 90 j
processed/annonces/dt=2026-10-23/
  part-0000.parquet   # typé
out/exports/2026-10-23.csv  # métier
```

```python
# Exemple 2 : corriger = rejouer raw
import json

raw = {"2026-10-23":
       '{"siren": " 483609327"}'}

def normaliser(txt):
    # v2 du job : strip() corrige
    # l'espace laissé par la v1
    return json.loads(txt)["siren"].strip()

# processed est régénéré, pas patché
processed = {dt: normaliser(t)
             for dt, t in raw.items()}
processed["2026-10-23"]  # → "483609327"
```

- Quiz : `raw` expire à 90 jours. Un bug de `processed` vieux de 120 jours est découvert : d'où rejouer les 30 plus anciens ?
- [ ] De `raw`, comme pour les autres jours
- [ ] De `processed`, en le corrigeant en place
- [x] De la source (API BODACC) : `raw` les a supprimés
- [ ] De `out`, qui garde tout l'historique
- Réponse : de la source : au-delà de la rétention, `raw` n'a plus ces jours ; la source doit alors être rejouable, sinon la rétention de `raw` doit être plus longue.

## 2. raw : brut et immuable
- Id : data-lake-raw-immuable
- Sous-thème : zones
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : data-lake-trois-zones
- Voir aussi : ingestion-idempotence-ecraser
- Mots-clés : zone processed, versioning S3
- Définition : La zone `raw` garde les octets reçus tels quels, écrits une seule fois, pour pouvoir tout rejouer depuis la source.
- Contexte : Si un bug de parsing corrompt `processed`, on recalcule à partir de `raw` sans rappeler l'API (quota, données qui ont pu changer). Pour que ce soit possible, `raw` n'est jamais réécrit ni « nettoyé » : on y stocke les octets exacts, plus quelques métadonnées (date de réception, URL). En S3, on le protège avec le versioning ou une politique qui interdit l'écrasement.
- Usage : ✅ toute source externe, surtout payante ou limitée en débit · ❌ y corriger ou reformater les données : ça se fait en aval, dans `processed`.

```python
# Exemple 1 : écrire une seule fois
recu = '{"ville":"Sète","id":7}'.encode()
s3 = {}                 # S3 simulé

def ecrire_raw(k, octets):
    if k in s3:         # immuable
        raise FileExistsError(k)
    s3[k] = octets

k = "dt=2026-10-23/0.json"
ecrire_raw(k, recu)
s3[k] == recu        # → True
ecrire_raw(k, recu)  # ❌ FileExistsError
```

```python
# Exemple 2 : les métadonnées à côté
recu = b'{"id": 7}'
meta = {
    "source": "bodacc",
    "recu_le": "2026-10-23T06:00:00Z",
    "octets": len(recu),
}
meta["octets"]       # → 9
```

- Quiz : Avec `recu` de l'exemple 1, que vaut `json.dumps(json.loads(recu)).encode() == recu` ?
- [ ] `True`
- [ ] `UnicodeDecodeError`
- [x] `False`
- Réponse : `False` : `dumps` ajoute des espaces et échappe `è` en `\u00e8` ; re-sérialiser, ce n'est plus du brut.

## 3. processed : typé et normalisé
- Id : data-lake-processed-type
- Sous-thème : zones
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : data-lake-trois-zones
- Voir aussi : formats-parquet-vs-csv
- Mots-clés : pydantic, SIREN
- Définition : La zone `processed` stocke des enregistrements validés et typés (dates en `date`, SIREN en `str`), prêts à requêter.
- Contexte : L'API renvoie du JSON : tout y est chaîne ou nombre, et certains champs BODACC contiennent même du JSON sérialisé. Un modèle pydantic (≈ un schéma `zod`) valide chaque annonce et convertit les types une fois pour toutes. En aval, personne ne re-parse une date. Ce qui ne passe pas la validation ne va pas dans `processed`.
- Usage : ✅ données requêtées ou jointes ensuite (Athena, Spark), schéma connu · ❌ copier le brut sans valider : on reporte les erreurs sur chaque consommateur.

```python
# Exemple 1 : la chaîne devient une date
from datetime import date
from pydantic import BaseModel

class Annonce(BaseModel):
    siren: str
    jour: date

a = Annonce(siren="483609327",
            jour="2026-10-23")
a.jour  # → date(2026, 10, 23)
```

```python
# Exemple 2 : resérialiser pour l'écriture
from datetime import date
from pydantic import BaseModel

class Annonce(BaseModel):
    siren: str
    jour: date

a = Annonce(siren="483609327",
            jour=date(2026, 10, 23))
a.model_dump(mode="json")
# → {"siren": "483609327", "jour": "2026-10-23"}
```

- Quiz : Que fait `Annonce(siren="483609327", jour="23/10/2026")` ?
- [x] `ValidationError`
- [ ] `jour` vaut `date(2026, 10, 23)`
- [ ] `jour` reste la chaîne `"23/10/2026"`
- Réponse : `ValidationError` : pydantic ne lit une date qu'en ISO 8601 (`AAAA-MM-JJ`) ; convertir le format français avant.

## 4. out : l'export consommateur
- Id : data-lake-out-export-consommateur
- Sous-thème : zones
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : data-lake-trois-zones
- Mots-clés : zone processed
- Définition : La zone `out` publie des exports figés pour un consommateur (CSV, colonnes choisies), découplés du schéma interne de `processed`.
- Contexte : `processed` évolue avec le pipeline (nouveaux champs, renommages). Un consommateur (équipe métier, Excel, autre service) veut un contrat stable : colonnes fixes, ordre fixe, format simple. `out` est ce contrat. `csv.DictWriter` impose la liste des colonnes (`fieldnames`) et écrit les lignes dans cet ordre, quel que soit l'ordre des clés du dict.
- Usage : ✅ export vers un outil externe ou une autre équipe, avec un contrat de colonnes · ❌ y faire lire le pipeline lui-même : il lit `processed`.

```python
# Exemple 1 : colonnes imposées
import csv, io

buf = io.StringIO()
w = csv.DictWriter(buf,
    fieldnames=["siren", "tribunal"])
w.writeheader()
w.writerow({"tribunal": "Lyon",
            "siren": "483609327"})
buf.getvalue()
# → "siren,tribunal\r\n483609327,Lyon\r\n"
```

```python
# Exemple 2 : colonne manquante = vide
import csv, io

buf = io.StringIO()
w = csv.DictWriter(buf,
    fieldnames=["siren", "tribunal"])
w.writerow({"siren": "483609327"})
buf.getvalue()  # → "483609327,\r\n"
```

- Quiz : Que fait `w.writerow({"siren": "1", "tribunal": "Lyon", "type": "A"})` ?
- [ ] Écrit `1,Lyon,A`
- [ ] Écrit `1,Lyon` sans rien dire
- [x] `ValueError`
- [ ] `KeyError`
- Réponse : `ValueError` (dict contains fields not in fieldnames) : passer `extrasaction="ignore"` pour filtrer les colonnes en trop.

## 5. data lake : stockage et calcul séparés
- Id : data-lake-stockage-calcul-separes
- Sous-thème : architecture
- Type : comparaison
- Niveau : 1
- Profils : débutant, data
- Mots-clés : S3, Athena, Spark, Iceberg
- Définition : Un data lake garde des fichiers ouverts (JSON, Parquet) dans un stockage objet, lus par des moteurs indépendants, payés à la lecture.
- Contexte : Dans une base (PostgreSQL), stockage et moteur sont liés : le serveur tourne en permanence et lui seul lit ses fichiers. Dans le lake, S3 garde les fichiers ; Athena, Spark ou une Lambda les lisent chacun leur tour, sans copie ni serveur allumé. Le prix : ni transactions ni index natifs, pas de mise à jour de ligne sans format de table (Iceberg), et une structure (partitions, formats) à concevoir soi-même.
- Usage : ✅ gros volumes en ajout, lectures analytiques, plusieurs moteurs sur les mêmes données · ❌ lecture par clé en millisecondes, mises à jour fréquentes de lignes : une base (DynamoDB, PostgreSQL).

```python
# Exemple 1 : un fichier, deux lecteurs
import json

s3 = {"processed/a.jsonl":
      b'{"t": "Lyon"}\n{"t": "Paris"}\n'}
f = s3["processed/a.jsonl"]
len(f.splitlines())  # → 2  (moteur 1)
[json.loads(l)["t"]
 for l in f.splitlines()]
# → ["Lyon", "Paris"]  (moteur 2)
```

- Quiz : Aucune requête Athena pendant un mois sur 10 Go posés dans S3 : que paie-t-on ?
- [ ] Rien du tout
- [x] Le stockage seulement
- [ ] Le stockage et une instance Athena
- [ ] Le stockage et le scan des 10 Go
- Réponse : le stockage seulement : Athena facture les octets scannés par requête, sans serveur au repos ; zéro requête, zéro calcul.

## 6. dt= : partitionnement Hive
- Id : data-lake-partitionnement-hive
- Sous-thème : partitions
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : duckdb-hive-partitioning-date, AWS/glue-athena-partition-projection
- Mots-clés : Athena, Glue, Spark, cardinalité
- Définition : Un segment `cle=valeur` dans la clé (`raw/bodacc/dt=AAAA-MM-JJ/`) déclare une partition, qu'Athena, Glue et Spark lisent comme une colonne filtrable (style Hive).
- Contexte : Le stockage objet n'a pas de dossiers : `dt=…/` est un préfixe de chaîne qui sert de répertoire virtuel. `WHERE dt = '2026-10-23'` ne lit que ce préfixe : moins d'octets scannés, donc moins cher. La valeur est une chaîne : format fixe et triable (ISO `AAAA-MM-JJ`, zéros compris), jamais `23/10/2026`. On partitionne par la colonne filtrée dans presque toutes les requêtes, à faible cardinalité.
- Usage : ✅ données qui arrivent par jour (annonces BODACC, logs), requêtes filtrées sur une date · ❌ partition trop fine (par heure pour 10 lignes) ou à forte cardinalité (`siren`) : des milliers de petits fichiers ralentissent la lecture.

```python
# Exemple 1 : construire la clé du jour
from datetime import date

def cle(jour, n):
    return (f"raw/bodacc/dt={jour}"
            f"/part-{n:03d}.json")

cle(date(2026, 10, 5), 7)
# → "raw/bodacc/dt=2026-10-05/part-007.json"
```

```python
# Exemple 2 : relire la partition
from datetime import date

k = "raw/bodacc/dt=2026-10-05/p.json"
seg = k.split("/")[2]  # "dt=2026-10-05"
nom, valeur = seg.split("=")
(nom, valeur)  # → ("dt", "2026-10-05")
date.fromisoformat(valeur)
# → date(2026, 10, 5)
```

```python
# Exemple 3 : un datetime garde l'heure
from datetime import datetime

jour = datetime(2026, 10, 23, 6, 0)
f"dt={jour}"
# → "dt=2026-10-23 06:00:00"
f"dt={jour:%Y-%m-%d}"
# → "dt=2026-10-23"
```

- Quiz : Que vaut `sorted(["dt=2026-9-30", "dt=2026-10-01"])[0]` ?
- [ ] `"dt=2026-9-30"`
- [x] `"dt=2026-10-01"`
- [ ] `TypeError`
- Réponse : `"dt=2026-10-01"` : le tri des clés est lexical (`"1" < "9"`) ; sans zéro devant le mois, l'ordre des partitions casse.

## 7. schéma à la lecture : le fichier ne contrôle rien
- Id : data-lake-schema-a-la-lecture
- Sous-thème : tables
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Voir aussi : qualite-contrat-de-donnees, duckdb-describe-schema
- Mots-clés : Glue, zone raw, zone processed, pydantic
- Définition : Dans un lake, le schéma s'applique à la lecture (schema-on-read) : les fichiers s'écrivent sans contrôle, la table dit comment les interpréter.
- Contexte : Une base refuse une ligne qui ne respecte pas sa table (schema-on-write). Le lake accepte tout : un JSON avec un champ en trop ou en moins est déposé sans erreur, et c'est la définition de table (Glue) qui choisit colonnes et types. Souplesse bienvenue dans `raw`, où l'on garde tout ; danger dans `processed`, où un fichier mal formé ne casse qu'au moment de la requête, chez le consommateur.
- Usage : ✅ `raw` : tout accepter, interpréter plus tard · ❌ compter sur la lecture pour détecter les erreurs de `processed` : valider à l'écriture (pydantic) avant de publier.

```python
# Exemple 1 : l'écriture ne contrôle rien
import json

fichier = ['{"siren": "483609327"}',
           '{"SIREN": 552100554}']  # déposé
schema = ["siren"]                   # table
[{c: json.loads(l).get(c) for c in schema}
 for l in fichier]
# → [{"siren": "483609327"}, {"siren": None}]
```

- Quiz : Un Parquet écrit avec `siren` en entier, une table qui le déclare `string` : quand l'erreur apparaît-elle ?
- [ ] À l'écriture du fichier dans S3
- [ ] Au `CREATE TABLE` dans Glue
- [x] À la requête qui lit ce fichier
- [ ] Jamais : Athena convertit
- Réponse : à la requête : S3 et le catalogue ne lisent pas le contenu ; Athena découvre l'incompatibilité de type en ouvrant le fichier.

## 8. dt= : la publication, pas l'événement
- Id : data-lake-partition-par-publication
- Sous-thème : partitions
- Type : choisir
- Niveau : 2
- Profils : data
- Prérequis : data-lake-partitionnement-hive
- Voir aussi : data-lake-jour-de-partition-utc
- Mots-clés : partition, run, BODACC
- Source : data-platform · S1-05
- Définition : Une source datée porte deux dates : quand le fait a eu lieu (événement) et quand on l'apprend (publication) ; on partitionne par la seconde.
- Contexte : Sur BODACC, `dateparution` est la publication, `jugement.date` la décision du tribunal, souvent dix jours plus tôt. L'ingestion du 20 octobre apporte des jugements de tout le mois : partitionner par événement réécrirait des partitions passées à chaque run et casserait la règle « un run = une partition ». On partitionne `dt=` par publication et on garde la date d'événement en colonne, pour filtrer et agréger.
- Usage : ✅ `dt=` = date de publication ou de réception ; date d'événement en colonne · ❌ partitionner par date d'événement une source qui publie en retard : des partitions jamais closes.

```python
# Exemple 1 : 11 jours d'écart
from datetime import date

parution = date(2026, 10, 20)
jugement = date(2026, 10, 9)
(parution - jugement).days  # → 11
```

```python
# Exemple 2 : un run, combien de partitions ?
from datetime import date

lot = [  # ingestion du 2026-10-20
    {"parution": date(2026, 10, 20),
     "jugement": date(2026, 10, 9)},
    {"parution": date(2026, 10, 20),
     "jugement": date(2026, 9, 30)},
    {"parution": date(2026, 10, 20),
     "jugement": date(2026, 10, 14)},
]
len({a["parution"] for a in lot})  # → 1
len({a["jugement"] for a in lot})  # → 3
```

- Quiz : Partitions par date de jugement : rejouer le 20/10 en écrasant `dt=2026-10-09` fait perdre quoi ?
- [ ] Rien : le rejeu est idempotent
- [x] Les jugements du 9 publiés un autre jour
- [ ] Les annonces publiées le 20 octobre
- [ ] Seulement les rectificatifs
- Réponse : les jugements du 9 publiés un autre jour : la partition mélange plusieurs parutions, l'écraser avec un seul run efface les autres.

## 9. cardinalité : compter les partitions
- Id : data-lake-cardinalite-partitions
- Sous-thème : partitions
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : data-lake-partitionnement-hive
- Voir aussi : data-lake-petits-fichiers
- Mots-clés : partition, SIREN
- Définition : La cardinalité d'une colonne de partition (son nombre de valeurs distinctes) fixe le nombre de dossiers : à garder entre quelques dizaines et quelques milliers.
- Contexte : `dt` donne 365 partitions par an : lisible et filtrable. `siren` en donnerait des millions de quelques lignes chacune : le catalogue et le planificateur passent plus de temps à lister qu'à lire. Combiner deux colonnes multiplie les cardinalités : `dt` × département ≈ 37 000 partitions par an. Règle : partitionner par ce qui est filtré presque toujours, et viser au moins quelques dizaines de Mo par partition.
- Usage : ✅ `dt` seul, ou `dt` + une colonne à faible cardinalité (bulletin A, B, C) · ❌ identifiant (`siren`, `id`) ou horodatage précis en partition : des millions de minuscules dossiers.

```python
# Exemple 1 : le nombre de partitions par an
jours, depts = 365, 101
jours          # → 365    (dt)
jours * depts  # → 36865  (dt + dept)
jours * 3      # → 1095   (dt + bulletin)
```

```python
# Exemple 2 : la taille par partition
mo_jour = 59              # export du jour
round(mo_jour / 101, 2)   # → 0.58  (Mo)
```

- Quiz : Partitions `dt` + `familleavis` (8 familles) sur 3 ans : combien de partitions au plus ?
- [ ] 1 095
- [ ] 2 920
- [x] 8 760
- [ ] 24
- Réponse : 8 760 : 365 × 3 jours × 8 familles ; chaque colonne ajoutée multiplie le nombre de dossiers.

## 10. dt= : une colonne ou year/month/day
- Id : data-lake-dt-une-colonne
- Sous-thème : partitions
- Type : choisir
- Niveau : 2
- Profils : data
- Prérequis : data-lake-partitionnement-hive
- Mots-clés : partition, partitionnement Hive
- Définition : Une date se partitionne en une colonne (`dt=2026-10-23`) ou en trois (`year=2026/month=10/day=23`) ; une seule colonne rend les plages de dates simples.
- Contexte : Avec trois colonnes, « du 25 septembre au 5 octobre » s'écrit avec des `OR` imbriqués sur année, mois et jour, faciles à rater. Avec `dt` au format ISO, c'est `dt BETWEEN '2026-09-25' AND '2026-10-05'` : l'ordre des chaînes est celui des dates. Le découpage en trois sert surtout à lister un mois par préfixe, ce qu'on obtient aussi avec `dt LIKE '2026-10-%'`.
- Usage : ✅ `dt=AAAA-MM-JJ` pour des données quotidiennes, plages en `BETWEEN` · ❌ `year/month/day` pour des requêtes par plage : filtres illisibles et fragiles.

```python
# Exemple 1 : une plage avec dt
dts = ["2026-09-24", "2026-09-25",
       "2026-10-05", "2026-10-06"]
[d for d in dts
 if "2026-09-25" <= d <= "2026-10-05"]
# → ["2026-09-25", "2026-10-05"]
```

```python
# Exemple 2 : la même plage sur 3 colonnes
p = [(2026, 9, 24), (2026, 9, 25),
     (2026, 10, 5), (2026, 10, 6)]
[x for x in p
 if (x[1] == 9 and x[2] >= 25)
 or (x[1] == 10 and x[2] <= 5)]
# → [(2026, 9, 25), (2026, 10, 5)]
```

- Quiz : Exemple 1 : la valeur `"2026-10-05T06:00"` est-elle gardée par le filtre `"2026-09-25" <= d <= "2026-10-05"` ?
- [ ] Oui : c'est le 5 octobre
- [x] Non : la chaîne est plus grande
- [ ] `TypeError`
- Réponse : non : `"2026-10-05T06:00" > "2026-10-05"` (une chaîne prolongée est plus grande) ; d'où des `dt` toujours au format `AAAA-MM-JJ`, sans heure.

## 11. UTC : choisir le jour de partition
- Id : data-lake-jour-de-partition-utc
- Sous-thème : partitions
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : data-lake-partitionnement-hive
- Voir aussi : ingestion-deux-fuseaux-deux-roles, ingestion-veille-fuseau-source
- Mots-clés : partition, UTC, fuseau horaire, Lambda
- Définition : On choisit le jour de partition dans un fuseau fixe, en général UTC, pour qu'un horodatage tombe toujours dans le même `dt=`.
- Contexte : Paris est à UTC+2 en été et UTC+1 en hiver : un même instant n'a pas la même date selon le fuseau, et les changements d'heure créent des heures doublées ou manquantes. Un `datetime` sans `tzinfo` (naïf) est interprété dans le fuseau de la machine : celui d'une Lambda est UTC, celui d'un poste de dev Paris. Toujours convertir en UTC avant de calculer `dt=`.
- Usage : ✅ horodatages d'événements (réception, logs) · ❌ date métier déjà sans heure (`dateparution` BODACC) : la garder telle quelle, sans conversion.

```python
# Exemple 1 : Paris vers UTC
from datetime import datetime
from zoneinfo import ZoneInfo

paris = ZoneInfo("Europe/Paris")
utc = ZoneInfo("UTC")
t = datetime(2026, 10, 23, 14, 0,
             tzinfo=paris)
t.astimezone(utc).hour  # → 12
```

```python
# Exemple 2 : la clé calculée en UTC
from datetime import datetime, timezone

t = datetime(2026, 10, 23, 12, 0,
             tzinfo=timezone.utc)
f"dt={t:%Y-%m-%d}"  # → "dt=2026-10-23"
t.utcoffset().total_seconds()  # → 0.0
```

- Quiz : Que vaut `datetime(2026, 10, 23, 1, 30, tzinfo=paris).astimezone(utc).date()` ?
- [ ] `date(2026, 10, 23)`
- [ ] `date(2026, 10, 24)`
- [x] `date(2026, 10, 22)`
- Réponse : `date(2026, 10, 22)` : 1 h 30 à Paris en heure d'été = 23 h 30 UTC la veille ; l'annonce tombe dans `dt=2026-10-22`.

## 12. petits fichiers : le coût par objet
- Id : data-lake-petits-fichiers
- Sous-thème : fichiers
- Type : piège
- Niveau : 2
- Profils : data
- Voir aussi : data-lake-nombre-de-fichiers, data-lake-compaction
- Mots-clés : Parquet, partition, micro-batch, Spark
- Définition : Beaucoup de petits fichiers ralentissent et renchérissent la lecture : chaque objet coûte une requête, une ouverture et des métadonnées, quelle que soit sa taille.
- Contexte : Lire 1 Go en 8 fichiers de 128 Mo, c'est 8 GET ; en fichiers de 10 Ko, plus de 100 000 GET, facturés au millier, chacun avec sa latence et son en-tête Parquet à parser. Les causes : partitions trop fines, micro-batch qui écrit à chaque événement, job Spark avec trop de tâches en sortie. Les remèdes : écrire moins souvent et plus gros, puis compacter.
- Usage : ✅ viser 128 Mo à 1 Go par fichier Parquet, surveiller le nombre d'objets par partition · ❌ un fichier par annonce ou par message : la requête passe son temps à ouvrir des fichiers.

```python
# Exemple 1 : même volume, autre nombre
go = 1024 ** 3
go // (128 * 1024 ** 2)  # → 8
go // (10 * 1024)        # → 104857
```

```python
# Exemple 2 : la latence s'additionne
lat = 0.02                  # 20 ms par GET
round(8 * lat, 2)           # → 0.16  (s)
round(104_857 * lat / 60)   # → 35  (min)
```

- Quiz : Un job Spark écrit chaque jour 59 Mo avec 200 tâches en sortie : qu'obtient-on dans la partition ?
- [ ] 1 fichier de 59 Mo
- [x] 200 fichiers d'environ 0,3 Mo
- [ ] 59 fichiers de 1 Mo
- [ ] 8 fichiers de 128 Mo
- Réponse : 200 fichiers d'environ 0,3 Mo : chaque tâche écrit son propre fichier ; réduire avec `coalesce(n)` avant l'écriture.

## 13. taille de fichier : calculer le nombre
- Id : data-lake-nombre-de-fichiers
- Sous-thème : fichiers
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : data-lake-petits-fichiers
- Mots-clés : Spark, Parquet, gzip
- Définition : Le nombre de fichiers d'une écriture se calcule : volume divisé par la taille cible (128 Mo à 1 Go en Parquet), arrondi au supérieur.
- Contexte : Spark écrit un fichier par tâche : sans réglage, c'est le parallélisme du job, pas le volume, qui fixe le nombre de fichiers. On le fixe avec `coalesce(n)`, `repartition(n)` ou `maxRecordsPerFile`. Une journée BODACC en Parquet tient en un fichier. Trop gros nuit aussi : un `.json.gz` de 10 Go n'est pas découpable, un seul worker le lit, quel que soit le cluster.
- Usage : ✅ calculer `n` d'après le volume du jour, un seul fichier pour un petit jour · ❌ laisser le parallélisme décider ; un énorme gzip unique : lu par un seul worker.

```python
# Exemple 1 : n = volume / cible
import math

def n_fichiers(octets, cible=128 * 2**20):
    return max(1, math.ceil(octets / cible))

n_fichiers(6 * 2**20)  # → 1      (un jour)
n_fichiers(2 * 2**40)  # → 16384  (2 To)
```

- Quiz : Avec `n_fichiers`, combien de fichiers pour 129 Mo (`129 * 2**20`) ?
- [ ] 1
- [x] 2
- [ ] 0
- Réponse : 2 : l'arrondi est au supérieur, 1 Mo de plus que la cible ouvre un second fichier ; viser une cible avec de la marge (ou une fourchette) évite ce fichier minuscule.

## 14. format de table : la liste des fichiers fait foi
- Id : data-lake-format-de-table
- Sous-thème : tables
- Type : concept
- Niveau : 2
- Profils : data
- Voir aussi : data-lake-snapshot-time-travel, AWS/glue-athena-iceberg-modifier
- Mots-clés : partitionnement Hive, snapshot
- Définition : Un format de table (Iceberg, Delta, Hudi) tient la liste versionnée des fichiers d'une table : un fichier absent de la liste n'existe pas.
- Contexte : Une table Hive classique, c'est un préfixe : tout fichier présent est lu, y compris un fichier à moitié écrit ou laissé par un job planté. Avec Iceberg, une écriture ajoute ses fichiers puis publie un nouveau snapshot (la nouvelle liste) en une opération atomique : les lecteurs voient l'avant ou l'après, jamais l'entre-deux. Delta Lake fait de même avec son journal `_delta_log`.
- Usage : ✅ tables mises à jour, écritures concurrentes, lecteurs qui ne doivent jamais voir de partiel · ❌ zone `raw` en ajout seul : un préfixe et des fichiers suffisent.

```python
# Exemple 1 : préfixe contre liste publiée
s3 = ["t/part-0.parquet",
      "t/part-1.parquet",
      "t/part-2.parquet"]  # job planté
snapshot = ["t/part-0.parquet",
            "t/part-1.parquet"]
hive = [k for k in s3 if k.startswith("t/")]
len(hive), len(snapshot)  # → (3, 2)
```

- Quiz : Table Iceberg : on supprime à la main `part-1.parquet` dans S3. Que fait la lecture suivante ?
- [ ] Elle lit `part-0` seulement
- [x] Elle échoue : un fichier listé manque
- [ ] Elle lit les trois fichiers
- [ ] Elle reconstruit la liste seule
- Réponse : elle échoue : le snapshot référence un fichier absent ; on ne touche jamais aux fichiers d'une table hors de son moteur.

## 15. snapshot : lire la table d'hier
- Id : data-lake-snapshot-time-travel
- Sous-thème : tables
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : data-lake-format-de-table
- Mots-clés : Iceberg, Athena, RGPD
- Définition : Chaque écriture d'une table Iceberg crée un snapshot ; on relit la table telle qu'elle était à un snapshot ou une date (time travel).
- Contexte : La liste des fichiers étant versionnée, un état passé reste lisible tant que ses fichiers ne sont pas purgés : `FOR TIMESTAMP AS OF` dans Athena. Utile pour comparer avant et après un job, reproduire un rapport, revenir au snapshot précédent après une mauvaise écriture. Mais chaque snapshot retient ses fichiers : sans expiration (`expire_snapshots`, `VACUUM` dans Athena), le stockage grossit, et une ligne effacée pour le RGPD reste lisible dans le passé.
- Usage : ✅ audit, comparaison avant/après un `MERGE`, rollback · ❌ archive longue durée : les snapshots s'expirent, garder un export à part.

```python
# Exemple 1 : chaque écriture = un snapshot
snaps = [["p0"]]                  # v0
snaps.append(snaps[-1] + ["p1"])  # ajout
snaps.append(["p2"])              # overwrite
snaps[-1]  # → ["p2"]        (aujourd'hui)
snaps[1]   # → ["p0", "p1"]  (hier)
```

```sql
-- Exemple 2 : time travel dans Athena
SELECT count(*) FROM annonces
FOR TIMESTAMP AS OF
  TIMESTAMP '2026-10-23 07:00:00 UTC'
WHERE dt = '2026-10-22';
```

- Quiz : Snapshots expirés au-delà de 7 jours : peut-on relire la table telle qu'elle était il y a 10 jours ?
- [ ] Oui, comme hier
- [x] Non : snapshot expiré, fichiers purgés
- [ ] Oui, mais seulement en `SELECT *`
- [ ] Oui, depuis les fichiers `raw`
- Réponse : non : l'expiration retire le snapshot et ses fichiers devenus inutiles ; le time travel ne remonte qu'à la rétention choisie.

## 16. compaction : réécrire sans perdre
- Id : data-lake-compaction
- Sous-thème : fichiers
- Type : recette
- Niveau : 3
- Profils : data, expert
- Prérequis : data-lake-petits-fichiers, data-lake-format-de-table
- Mots-clés : partitionnement Hive, Iceberg, micro-batch, backfill
- Définition : La compaction relit les petits fichiers d'une partition, les réécrit en quelques gros, puis remplace l'ancienne version en une seule bascule.
- Contexte : Sur une table Hive, l'ordre sûr : écrire les gros fichiers sous un préfixe temporaire, vérifier le nombre de lignes, basculer (repointer la partition avec `ALTER TABLE … PARTITION … SET LOCATION`), puis seulement supprimer les petits. Écrire les gros au même préfixe fait lire les deux versions pendant un moment. Iceberg rend la bascule atomique (`OPTIMIZE` dans Athena). On compacte les partitions closes, jamais celle où un job écrit encore.
- Usage : ✅ partitions closes alimentées en micro-batch, après un backfill · ❌ compacter la partition du jour pendant l'écriture : fichiers perdus ou relus.

```python
# Exemple 1 : vérifier avant de basculer
petits = [["A1"], ["A2", "A3"], ["A4"]]
gros = [sum(petits, [])]      # réécrit
n_avant = sum(map(len, petits))
n_apres = sum(map(len, gros))
assert n_avant == n_apres     # sinon stop
len(petits), len(gros)        # → (3, 1)
```

```python
# Exemple 2 : réécrire au même préfixe
s3 = {"dt=1/p0": ["A1"], "dt=1/p1": ["A2"]}
s3["dt=1/compact"] = ["A1", "A2"]
lu = [x for k, v in s3.items()
      if k.startswith("dt=1/") for x in v]
len(lu)  # → 4  (doublons, avant nettoyage)
```

- Quiz : On supprime d'abord les petits fichiers, puis on écrit le gros ; une requête Athena tombe entre les deux. Que renvoie-t-elle pour ce jour ?
- [ ] Les anciennes lignes
- [x] 0 ligne, sans erreur
- [ ] Une erreur de fichier absent
- [ ] Les lignes en double
- Réponse : 0 ligne, sans erreur : le préfixe est vide à cet instant, une table Hive n'a aucune liste pour s'en apercevoir.

## 17. overwrite : la partition, pas la table
- Id : data-lake-overwrite-partition
- Sous-thème : partitions
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : data-lake-partitionnement-hive
- Voir aussi : ingestion-idempotence-ecraser
- Mots-clés : Spark, partition, rejeu, backfill
- Définition : Réécrire un jour doit remplacer sa seule partition ; or en mode statique (défaut), `mode("overwrite")` de Spark efface toute la table avant d'écrire.
- Contexte : `df.write.mode("overwrite").partitionBy("dt")` avec `spark.sql.sources.partitionOverwriteMode=static` supprime toutes les partitions existantes, puis écrit celles du DataFrame : rejouer le 23 octobre efface deux ans d'historique. En mode `dynamic`, seules les partitions présentes dans le DataFrame sont remplacées. Sur Iceberg, `overwritePartitions()` se comporte en dynamique. À tester sur une copie avant le premier rejeu.
- Usage : ✅ `partitionOverwriteMode=dynamic`, ou écrire directement sous `dt=…/`, pour tout rejeu ou backfill · ❌ `overwrite` statique sur une table partitionnée : l'historique disparaît.

```python
# Exemple 1 : statique ou dynamique
table = {"2026-10-22": 3, "2026-10-23": 5}
rejeu = {"2026-10-23": 6}

statique = dict(rejeu)     # tout remplacé
dynamique = table | rejeu  # par partition
sorted(statique)  # → ["2026-10-23"]
dynamique["2026-10-22"]  # → 3  (gardée)
```

```text
# Exemple 2 : le réglage Spark
spark.conf.set(
  "spark.sql.sources.partitionOverwriteMode",
  "dynamic")
(df.write.mode("overwrite")
   .partitionBy("dt").parquet(PROCESSED))
```

- Quiz : Mode dynamique, mais le DataFrame du rejeu du 23 est vide (aucune annonce lue). Que devient `dt=2026-10-23` ?
- [ ] Vidée
- [x] Inchangée
- [ ] Supprimée, avec toute la table
- [ ] Erreur à l'écriture
- Réponse : inchangée : en dynamique, seules les partitions présentes dans le DataFrame sont remplacées ; un jour vide ne remplace rien, l'ancienne version reste.

## 18. commit optimiste : deux écrivains
- Id : data-lake-commit-optimiste
- Sous-thème : tables
- Type : concept
- Niveau : 3
- Profils : data, expert
- Prérequis : data-lake-format-de-table
- Voir aussi : AWS/dynamodb-verrou-optimiste
- Mots-clés : Iceberg, snapshot, upsert, Step Functions
- Définition : Deux jobs qui écrivent la même table Iceberg préparent leurs fichiers en parallèle ; au commit, le second constate un conflit et doit réessayer.
- Contexte : Iceberg ne verrouille pas pendant l'écriture : chaque écrivain part du snapshot courant, écrit ses fichiers, puis tente de publier le snapshot suivant par un échange atomique dans le catalogue (compare-and-swap). Si un autre a publié entre-temps, le commit échoue (`CommitFailedException`) ; le moteur réessaie si les changements ne se recouvrent pas (ajouts), sinon le job échoue. Deux `MERGE` sur les mêmes fichiers se contrarient : sérialiser les écrivains reste le plus simple.
- Usage : ✅ ajouts concurrents, compaction pendant les écritures · ❌ plusieurs `MERGE` simultanés sur une même partition : conflits répétés ; un seul job à la fois (Step Functions, concurrence de 1).

```python
# Exemple 1 : compare-and-swap du snapshot
catalogue = {"annonces": 7}  # courant

def commit(lu, nouveau):
    if catalogue["annonces"] != lu:
        raise RuntimeError("conflit")
    catalogue["annonces"] = nouveau

lu_a = lu_b = catalogue["annonces"]
commit(lu_a, 8)   # A publie
commit(lu_b, 8)   # ❌ RuntimeError
```

- Quiz : Le job B relit le snapshot courant puis réessaie : quel appel publie correctement son écriture ?
- [ ] `commit(7, 8)`
- [ ] `commit(7, 9)`
- [x] `commit(8, 9)`
- [ ] `commit(8, 8)`
- Réponse : `commit(8, 9)` : B repart du snapshot 8 publié par A et propose le 9 ; `commit(7, …)` échoue encore, `commit(8, 8)` n'ajoute rien.
