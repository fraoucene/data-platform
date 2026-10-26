---
title: "Cartes · DynamoDB"
type: cartes
langage: AWS
chapitre: Stockage et bases
cours: DynamoDB
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · DynamoDB
AWS · DynamoDB : choisir, modèle, clés, index, lecture, écriture, transactions, capacité, exploitation, sécurité (format spec v4 de revision-pwa).

## 1. DynamoDB : lookup par clé
- Id : dynamodb-quand-choisir
- Sous-thème : choisir
- Type : choisir
- Niveau : 1
- Profils : débutant, web
- Voir aussi : dynamodb-acces-inconnus-sql, dynamodb-motifs-acces
- Définition : Pour lire un enregistrement par sa clé en quelques ms, à n'importe quel débit, on choisit DynamoDB (≈ une `Map` géante managée).
- Contexte : On conçoit la table à partir des requêtes : clé de partition (`siren`), éventuellement clé de tri (`date`), index secondaires pour les autres accès prévus. En mode à la demande, on paie à la requête et au Go, rien au repos. Un item fait 400 Ko au plus. Ce qui n'a pas été prévu dans les clés coûte un `Scan` complet de la table.
- Usage : ✅ API « fiche entreprise » par SIREN, état d'un traitement, déduplication · ❌ requêtes ad hoc, agrégats, jointures : Athena ou une base SQL.

```
# Exemple 1 : la décision
Besoin  : API « fiche entreprise »,
          GET /siren/483609327 < 20 ms
→ Choix : DynamoDB, PK = siren,
          à la demande (on-demand)
Pourquoi: accès par clé, payé à
          la requête, 0 $ au repos
Écarté  : Aurora (instance qui
          tourne sans trafic)
```

```python
# Exemple 2 : get par clé (simulé)
table = {"483609327": {"nom": "ACME",
                       "procedures": 2}}
table["483609327"]["procedures"]  # → 2
# un get = la clé exacte, rien d'autre
```

- Quiz : Le métier veut « procédures par tribunal et par mois, croisées avec le secteur » : quel service ?
- [ ] DynamoDB, avec un index secondaire
- [ ] DynamoDB, avec un `Scan` filtré
- [x] Athena sur `processed`
- [ ] S3 Select sur chaque fichier
- Réponse : Athena : DynamoDB n'a ni jointure ni `GROUP BY` ; il sert des accès prévus par clé, pas des questions ad hoc, et un `Scan` relit toute la table.

## 2. S3 : dix ans d'annonces brutes
- Id : dynamodb-s3-pour-archives
- Sous-thème : choisir
- Type : choisir
- Niveau : 1
- Profils : débutant, data
- Voir aussi : dynamodb-gros-objets-dans-s3
- Source : data-platform · pwa-sync
- Définition : Pour garder des années d'annonces BODACC brutes, relues en bloc par Spark ou Athena, on choisit S3 et non une table DynamoDB.
- Contexte : Le brut se lit par journée entière, jamais par clé : c'est un fichier, pas une ligne. Prix Paris (liste de prix AWS, octobre 2026) : S3 Standard 0,024 $ par Go-mois, DynamoDB 0,29715 $ par Go-mois au-delà de 25 Go offerts, plus 100 octets de surcoût par item. Spark et Athena lisent S3 directement ; une table DynamoDB demanderait un export ou un `Scan` complet.
- Usage : ✅ données brutes et historiques en S3, partitionnées par date · ❌ DynamoDB comme archive : plus cher au Go, et illisible en bloc sans export.

```
# Exemple 1 : la décision
Besoin  : 10 ans d'annonces brutes,
          relues par journée
→ Choix : S3, date=YYYY-MM-DD/,
          JSONL gzip + _MANIFEST
Écarté  : DynamoDB (lecture par clé,
          12 fois plus cher au Go)
```

```python
# Exemple 2 : 10 ans, Paris (USD/mois)
jour = 59_432_342   # octets JSONL, mesuré
go = jour * 260 * 10 / 1e9
round(go)                       # → 155
s3 = go * 0.024
ddb = (go - 25) * 0.29715
round(s3, 1), round(ddb, 1)     # → (3.7, 38.5)
```

- Quiz : Le brut de plus d'un an n'est relu qu'en cas de rejeu. Comment baisser encore son coût ?
- [ ] Le copier dans une table DynamoDB Standard-IA
- [x] Une règle de cycle de vie S3 vers Standard-IA
- [ ] Le passer en mode `PAY_PER_REQUEST`
- [ ] Une table DynamoDB par année
- Réponse : cycle de vie vers S3 Standard-IA : 0,0131 $ par Go-mois à Paris, contre 0,11886 $ pour la classe Standard-IA de DynamoDB.

## 3. verrou de job : PutItem conditionnel
- Id : dynamodb-verrou-de-job
- Sous-thème : choisir
- Type : choisir
- Niveau : 1
- Profils : data, ops
- Voir aussi : dynamodb-creer-si-absent
- Source : data-platform · pwa-sync
- Définition : Pour un verrou de job ou l'idempotence d'une ingestion, on choisit DynamoDB : un `PutItem` avec `attribute_not_exists(pk)` n'écrit que si la clé est libre.
- Contexte : La condition est vérifiée et appliquée en une seule opération atomique : de deux Lambda lancées en même temps pour la journée `2026-10-24`, une seule écrit, l'autre reçoit `ConditionalCheckFailedException` (mesuré avec moto). En TS, c'est la classe d'erreur du même nom de `@aws-sdk/client-dynamodb`. Aurora ferait aussi bien, mais avec une instance qui tourne au repos.
- Usage : ✅ verrou de traitement, « déjà ingéré ? », dédoublonnage d'événements · ❌ lire puis écrire (`GetItem` puis `PutItem`) : deux runs passent entre les deux.

```
# Exemple 1 : la décision
Besoin  : une seule ingestion par
          journée, même si rejouée
→ Choix : DynamoDB, pk = LOCK#<date>,
          PutItem conditionnel
Pourquoi: test et écriture atomiques,
          0 $ au repos
```

```python
# Exemple 2 : deux runs, un seul gagne
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="jobs",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk",
    "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName":
    "pk", "AttributeType": "S"}])
v = {"pk": "LOCK#bodacc#2026-10-24"}
c = "attribute_not_exists(pk)"
t.put_item(Item=v, ConditionExpression=c)
t.put_item(Item=v,
  ConditionExpression=c)  # ❌ ConditionalCheckFailedException
m.stop()
```

- Quiz : La Lambda qui tient le verrou plante avant de le supprimer. Le lendemain, on rejoue la même date. Que se passe-t-il ?
- [ ] Le verrou a été libéré au timeout de la Lambda
- [x] Refusé : il faut une date d'expiration dans la condition
- [ ] DynamoDB libère seul les verrous après 15 min
- [ ] La condition ignore les lignes de la veille
- Réponse : refusé, indéfiniment : rien ne supprime la ligne ; on stocke `expire` et on écrit `attribute_not_exists(pk) OR expire < :now`.

## 4. plein texte : OpenSearch, pas DynamoDB
- Id : dynamodb-recherche-plein-texte
- Sous-thème : choisir
- Type : choisir
- Niveau : 1
- Profils : web, data
- Prérequis : dynamodb-quand-choisir
- Source : data-platform · pwa-sync
- Définition : Pour chercher des mots dans le texte des annonces (« liquidation boulangerie »), on choisit OpenSearch : DynamoDB n'a pas d'index plein texte.
- Contexte : Dans DynamoDB, `contains(texte, :mot)` n'est qu'un filtre : il sert dans un `Scan`, relit toute la table, respecte la casse et ne classe rien par pertinence. OpenSearch découpe le texte en mots, gère accents et pluriels selon l'analyseur, et trie par score. Selon la doc, une intégration zero-ETL (OpenSearch Ingestion) alimente un index depuis une table DynamoDB. OpenSearch a un coût au repos.
- Usage : ✅ recherche par mots, tolérance aux fautes, tri par pertinence · ❌ `Scan` + `contains` sur une grosse table : lent, cher, et sensible à la casse.

```python
# Exemple 1 : contains respecte la casse
texte = "Liquidation judiciaire"
"liquidation" in texte    # → False
# contains(texte, :m) fait de même
# et relit chaque ligne (Scan)
```

```python
# Exemple 2 : 1 trouvé, 3 relus (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="annonces",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk",
    "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName":
    "pk", "AttributeType": "S"}])
for i, x in enumerate(["vente", "RJ",
                       "liquidation"]):
    t.put_item(Item={"pk": str(i), "t": x})
r = t.scan(FilterExpression="contains(t, :m)",
  ExpressionAttributeValues={":m": "liq"})
r["Count"], r["ScannedCount"]  # → (1, 3)
m.stop()
```

- Quiz : Peut-on chercher un mot dans `texte` en créant un GSI dont `texte` est la clé ?
- [ ] Oui, avec `contains` dans la condition de clé
- [x] Non : une clé se compare entière, pas mot à mot
- [ ] Oui, si `texte` est déclaré dans un bloc `attribute`
- [ ] Non : une clé d'index ne peut être qu'un nombre
- Réponse : non : une condition de clé n'accepte que l'égalité, les comparaisons, `BETWEEN` et `begins_with` sur la valeur entière ; `contains` n'y est pas permis.

## 5. item de 400 Ko : S3 et un pointeur
- Id : dynamodb-gros-objets-dans-s3
- Sous-thème : choisir
- Type : choisir
- Niveau : 1
- Profils : débutant, data, web
- Prérequis : dynamodb-taille-item-400ko
- Source : data-platform · pwa-sync
- Définition : Ce qui dépasse 400 Ko (PDF d'annonce, gros JSON) va dans S3 ; l'item DynamoDB garde seulement la clé de l'objet, comme un pointeur.
- Contexte : Au-delà de 400 Ko (noms et valeurs des attributs comptés), l'écriture échoue en `ValidationException` (selon la doc, mesuré avec moto). La doc propose trois sorties : compresser l'attribut (gzip en binaire), découper en plusieurs items sous la même `pk`, ou S3 + pointeur. Aucune transaction ne couvre S3 et DynamoDB ensemble : l'application gère les échecs et nettoie les objets orphelins.
- Usage : ✅ objets lourds dans S3, métadonnées et clé S3 dans l'item · ❌ découper un PDF en morceaux de 400 Ko dans la table : cher et fragile.

```python
# Exemple 1 : l'item garde le pointeur
item = {"pk": "ANNONCE#A202602011",
  "pdf": "s3://raw/pdf/A202602011.pdf",
  "octets": 1_250_000}
len(str(item)) < 400 * 1024   # → True
```

```python
# Exemple 2 : 500 000 caractères (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="annonces",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk",
    "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName":
    "pk", "AttributeType": "S"}])
t.put_item(Item={"pk": "A202602011",
  "pdf": "x" * 500_000})  # ❌ ClientError
m.stop()
```

- Quiz : Dans quel ordre écrire le PDF et l'item qui le référence ?
- [x] L'objet S3, puis l'item
- [ ] L'item, puis l'objet S3
- [ ] Les deux dans un `TransactWriteItems`
- [ ] En parallèle, l'ordre est indifférent
- Réponse : S3 d'abord : si l'item échoue, on a un objet orphelin à nettoyer, jamais un item qui pointe vers un objet absent ; aucune transaction ne couvre les deux.

## 6. accès inconnus : partir sur SQL
- Id : dynamodb-acces-inconnus-sql
- Sous-thème : choisir
- Type : choisir
- Niveau : 1
- Profils : débutant, web
- Prérequis : dynamodb-motifs-acces
- Source : data-platform · pwa-sync
- Définition : Requêtes encore inconnues : on part sur une base SQL (RDS, Aurora), car DynamoDB exige de connaître les accès avant de dessiner les clés.
- Contexte : En SQL, une nouvelle question est une nouvelle requête, avec au besoin un index ajouté après coup. En DynamoDB, une lecture non prévue par les clés devient un `Scan`, ou un index secondaire global à créer. Pour data-platform, l'analyse reste dans S3 + Athena : la question se pose pour un backend applicatif dont le modèle bouge encore (prototype, back-office).
- Usage : ✅ SQL pour un modèle qui change chaque semaine, DynamoDB une fois les accès stabilisés · ❌ DynamoDB « parce que serverless » sur un prototype aux écrans mouvants.

```
# Exemple 1 : la décision
Besoin  : back-office de suivi des
          dossiers, écrans qui
          changent chaque semaine
→ Choix : PostgreSQL (RDS, Aurora)
Pourquoi: requêtes ad hoc, index
          ajoutés au fil de l'eau
```

```python
# Exemple 2 : nouvelle question = SQL
import sqlite3
db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE a(siren, trib)")
db.execute("INSERT INTO a VALUES"
  " ('483609327', 'Lyon')")
db.execute("SELECT count(*) FROM a"
  " WHERE trib = 'Lyon'").fetchone()
# → (1,)
```

- Quiz : Table DynamoDB en production, nouveau besoin : lire par `tribunal`, hors clés. Comment, sans `Scan` ?
- [ ] Ajouter un LSI sur `tribunal` à la table existante
- [x] Ajouter un GSI sur `tribunal` à la table existante
- [ ] Changer la clé de partition de la table
- [ ] `Query` avec `tribunal` dans la `FilterExpression`
- Réponse : un GSI : selon la doc, il s'ajoute à une table existante et se remplit seul ; un LSI ne se crée qu'avec la table, et la clé primaire ne change pas.

## 7. item : des attributs propres à chaque ligne
- Id : dynamodb-item-sans-schema
- Sous-thème : modèle
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Source : data-platform · pwa-sync
- Définition : Un item est une ligne identifiée par sa clé ; chacun porte ses propres attributs, sans colonne commune imposée hors clés.
- Contexte : Image TS : un `Record<string, unknown>` par ligne, pas une ligne de tableau SQL. Un attribut absent n'existe pas sur l'item : ce n'est pas `NULL` (type explicite `{"NULL": true}`), il n'apparaît pas dans la réponse et ne coûte rien en stockage. Ajouter un attribut à un seul item ne demande aucune migration ; en échange, le code lecteur doit tolérer l'absence.
- Usage : ✅ attributs optionnels (date de clôture d'une procédure), modèle qui évolue sans migration · ❌ supposer qu'un attribut existe partout : lire avec `.get()` et une valeur par défaut.

```python
# Exemple 1 : deux items, deux formes
mac = {"pk": "u1", "sk": "V#mac",
       "vues": 12}
ios = {"pk": "u1", "sk": "V#ios"}
"vues" in ios        # → False
ios.get("vues", 0)   # → 0
```

```python
# Exemple 2 : mesuré avec moto
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
t.put_item(Item={"pk": "u1", "sk": "V#ios"})
t.get_item(Key={"pk": "u1",
  "sk": "V#ios"})["Item"]
# → {'pk': 'u1', 'sk': 'V#ios'}
m.stop()
```

- Quiz : Sur l'item `ios` lu par `get_item`, que fait `ios["vues"]` ?
- [ ] Renvoie `None`
- [ ] Renvoie `0`
- [x] Lève `KeyError`
- [ ] Renvoie `{'NULL': True}`
- Réponse : `KeyError` : l'attribut n'existe pas sur cet item, boto3 ne l'ajoute pas ; un dict Python lève sur une clé absente, d'où `.get()`.

## 8. types : set → SS, list → L
- Id : dynamodb-types-boto3
- Sous-thème : modèle
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : dynamodb-valeurs-typees, dynamodb-ensembles
- Source : data-platform · pwa-sync
- Définition : DynamoDB a 10 types : scalaires `S N B BOOL NULL`, documents `M L`, ensembles `SS NS BS` ; boto3 choisit d'après le type Python.
- Contexte : Correspondance de boto3 : `str` → S, `int`/`Decimal` → N, `bytes` → B, `bool` → BOOL, `None` → NULL, `dict` → M, `list`/`tuple` → L, `set` → SS, NS ou BS selon son contenu. Une liste est ordonnée, accepte doublons et types mêlés ; un ensemble non. En TS, `marshall` fait la même traduction depuis les types JS (`Set` → ensemble).
- Usage : ✅ choisir le type Python d'après la sémantique voulue (ordre, unicité) · ❌ laisser un `list` quand on veut des valeurs uniques : rien ne dédoublonne.

```python
# Exemple 1 : le type suit Python
from boto3.dynamodb.types import TypeSerializer
s = TypeSerializer().serialize
s(None)        # → {'NULL': True}
s(b"ab")       # → {'B': b'ab'}
s({"IAM"})     # → {'SS': ['IAM']}
s({"a": 1})    # → {'M': {'a': {'N': '1'}}}
```

- Quiz : Que vaut `s(["IAM", "IAM"])` ?
- [ ] `{'SS': ['IAM']}`
- [ ] `{'SS': ['IAM', 'IAM']}`
- [x] `{'L': [{'S': 'IAM'}, {'S': 'IAM'}]}`
- [ ] `TypeError` : doublon
- Réponse : `{'L': [{'S': 'IAM'}, {'S': 'IAM'}]}` (mesuré) : une `list` Python devient une liste DynamoDB, doublons gardés ; seul un `set` donne `SS`.

## 9. item : 400 Ko, noms compris
- Id : dynamodb-taille-item-400ko
- Sous-thème : modèle
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Source : data-platform · pwa-sync
- Définition : Un item pèse au plus 400 Ko (409 600 octets), en comptant la longueur UTF-8 des noms d'attributs et des valeurs.
- Contexte : Selon la doc, l'item `{"shirt-color": "R", "shirt-size": "M"}` pèse 23 octets : les noms comptent. Ils comptent aussi dans la facturation (lecture par tranche de 4 Ko, écriture par 1 Ko) : sur des millions d'items, `nb_procedures` répété coûte plus que `np`. Au-delà de 400 Ko, `PutItem` lève `ValidationException` (mesuré avec moto). Un gros document va dans S3, l'item garde sa clé S3.
- Usage : ✅ noms courts sur les gros volumes, contenu lourd dans S3 avec un pointeur · ❌ stocker le JSONL brut d'une journée BODACC dans un item.

```python
# Exemple 1 : la taille, comme la doc
def taille(item):
    return sum(len(k.encode())
      + len(v.encode())
      for k, v in item.items())
taille({"shirt-color": "R",
        "shirt-size": "M"})  # → 23
400 * 1024                   # → 409600
```

- Quiz : Un attribut `texte` contient 210 000 fois le caractère `é`. `PutItem` ?
- [ ] Accepté : 210 000 < 409 600
- [x] Refusé : 420 000 octets en UTF-8
- [ ] Accepté, valeur tronquée à 400 Ko
- [ ] Refusé : 4 octets par caractère
- Réponse : refusé (mesuré avec moto) : `é` fait 2 octets en UTF-8 ; la limite compte des octets, pas des caractères.

## 10. mots réservés : l'alias #n
- Id : dynamodb-mots-reserves
- Sous-thème : modèle
- Type : piège
- Niveau : 1
- Profils : débutant, web, data
- Voir aussi : dynamodb-updateexpression-clauses
- Source : data-platform · pwa-sync
- Définition : Un nom d'attribut qui est un mot réservé (`date`, `status`, `name`…) doit passer par un alias `#n` déclaré dans `ExpressionAttributeNames`.
- Contexte : DynamoDB n'interdit pas d'appeler un attribut `date`, mais `SET date = :v` échoue : « Attribute name is a reserved keyword » (mesuré avec moto). La liste compte des centaines de mots anglais (`views`, `count`, `type`, `size`, `ttl`…) ; `statut` ou `vues` n'en sont pas. Dans une expression, `#` introduit un alias de nom, `:` une valeur. Le `Key`/`Attr` de boto3 génère ces alias tout seul.
- Usage : ✅ un alias `#x` systématique pour chaque nom dans une expression écrite à la main · ❌ renommer tous les attributs pour éviter la liste : on finit toujours par en croiser un.

```python
# Exemple 1 : l'alias #d
kw = dict(
  UpdateExpression="SET #d = :v",
  ExpressionAttributeNames={"#d": "date"},
  ExpressionAttributeValues={
    ":v": "2026-10-23"})
kw["ExpressionAttributeNames"]["#d"]  # → 'date'
```

```python
# Exemple 2 : sans alias, refusé (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
t.update_item(Key={"pk": "u1", "sk": "V"},
  UpdateExpression="SET date = :v",
  ExpressionAttributeValues={":v": "x"})  # ❌ ClientError
m.stop()
```

- Quiz : `ExpressionAttributeNames={"#d": "date"}` mais l'expression est `SET vues = :v`. Résultat ?
- [ ] `vues` mis à jour, `#d` ignoré
- [ ] `date` mis à jour à la place
- [x] `ValidationException` : alias inutilisé
- [ ] `vues` et `date` mis à jour
- Réponse : `ValidationException` (mesuré avec moto : « Value provided in ExpressionAttributeNames unused in expressions ») : tout alias déclaré doit servir.

## 11. table : clé de partition et clé de tri
- Id : dynamodb-cle-partition-et-tri
- Sous-thème : clés
- Type : concept
- Niveau : 1
- Profils : débutant
- Voir aussi : dynamodb-cle-simple-ou-composite
- Source : data-platform · pwa-sync
- Définition : La clé primaire d'une table est soit la clé de partition seule (`pk`), soit le couple `pk` + clé de tri (`sk`), unique par ligne.
- Contexte : `pk` regroupe les lignes (toutes celles d'un utilisateur), `sk` les ordonne dans le groupe et les distingue. Image : un `Map<pk, SortedMap<sk, ligne>>`. Deux lignes peuvent partager `pk` ou `sk`, jamais les deux. Le choix des clés se fait à partir des requêtes prévues : on ne pourra lire efficacement que par `pk`, puis par plage de `sk`.
- Usage : ✅ `pk` = qui (utilisateur, SIREN), `sk` = quoi ou quand (date, type) · ❌ `pk` constante pour toutes les lignes : une seule partition, pas d'isolation possible.

```python
# Exemple 1 : le modèle, en dict
table = {
  "eu-west-3:1b2c": {
    "R#2026-10-01#IAM/3": {"ok": True},
    "V#mac#IAM": {"vues": 12},
  },
}
len(table["eu-west-3:1b2c"])  # → 2
```

```hcl
# Exemple 2 : la table progress
resource "aws_dynamodb_table" "progress" {
  name         = "${local.prefix}-progress"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"   # partition
  range_key    = "sk"   # tri
}
```

- Quiz : Deux `PutItem` avec le même `pk` et la même `sk`, contenus différents. Combien de lignes ?
- [ ] 2 : DynamoDB garde l'historique
- [x] 1 : la seconde remplace la première
- [ ] 1 : la seconde est refusée (doublon)
- [ ] 2 : une par appareil
- Réponse : 1 : (`pk`, `sk`) identifie la ligne ; `PutItem` sur une clé existante la remplace, sans erreur.

## 12. attribute : seulement les clés
- Id : dynamodb-terraform-attribute-cles
- Sous-thème : clés
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : dynamodb-item-sans-schema
- Source : data-platform · pwa-sync
- Définition : Dans `aws_dynamodb_table`, les blocs `attribute` ne déclarent que les attributs de clé (table, index) ; les autres colonnes n'ont pas de schéma.
- Contexte : DynamoDB est sans schéma hors clés : chaque ligne porte ses propres attributs (`ok`, `vues`, `secondes`). Déclarer un attribut qui n'est utilisé par aucune clé fait échouer le plan ou l'apply (« all attributes must be indexed »). Types : `S` (chaîne), `N` (nombre), `B` (binaire).
- Usage : ✅ un `attribute` par attribut de clé de table ou d'index secondaire · ❌ décrire toutes les colonnes comme en SQL : erreur, et inutile.

```hcl
# Exemple 1 : deux clés, deux attributs
attribute {
  name = "pk"
  type = "S"
}
attribute {
  name = "sk"
  type = "S"
}
# pas d'attribute "ok" ni "vues"
```

- Quiz : On ajoute `attribute { name = "vues" type = "N" }` sans index qui l'utilise. Résultat ?
- [ ] Colonne `vues` typée pour toutes les lignes
- [x] Erreur : attribut déclaré mais pas indexé
- [ ] Ignoré sans message
- [ ] Index créé automatiquement
- Réponse : erreur (selon la doc du provider) : tout `attribute` doit servir à une clé de table ou d'index.

## 13. clé simple ou composite : quand
- Id : dynamodb-cle-simple-ou-composite
- Sous-thème : clés
- Type : choisir
- Niveau : 1
- Profils : débutant
- Source : data-platform · pwa-sync
- Définition : Clé simple (`pk` seule) : un item par entité ; clé composite (`pk` + `sk`) : une collection d'items triés sous la même `pk`.
- Contexte : Fiche entreprise lue par SIREN, un seul état par SIREN : la clé simple suffit, lue par `GetItem`. Plusieurs faits par entité (annonces d'un SIREN, réponses d'un utilisateur) : clé composite, lue par `Query` et plage de `sk`. Le choix se fait avant la création de la table, à partir des lectures prévues ; la clé simple n'offre aucune plage.
- Usage : ✅ simple pour « 1 clé → 1 objet », composite dès qu'apparaît « les X de Y » · ❌ clé simple puis tout entasser dans une liste de l'item : 400 Ko et réécriture complète.

```python
# Exemple 1 : les deux formes
simple = {"483609327": {"nom": "ACME"}}
compo = {"483609327": {
  "ANNONCE#2026-10-01": {"t": "vente"},
  "ANNONCE#2026-10-23": {"t": "RJ"}}}
len(compo["483609327"])  # → 2
```

- Quiz : Table en prod à clé simple `pk`. Peut-on lui ajouter une clé de tri ?
- [ ] Oui, par `UpdateTable`
- [ ] Oui, si la table est vide
- [x] Non : nouvelle table, puis copie
- [ ] Oui, en mode à la demande
- Réponse : non : `UpdateTable` n'accepte pas de `KeySchema` pour la table (doc de l'API) ; changer de clé = créer une table et y copier les items.

## 14. clés immuables : supprimer puis recréer
- Id : dynamodb-cles-immuables
- Sous-thème : clés
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Source : data-platform · pwa-sync
- Définition : On ne modifie jamais `pk` ou `sk` d'un item : `UpdateItem` sur un attribut de clé est refusé, il faut supprimer puis recréer.
- Contexte : La clé est l'adresse de l'item : la changer, c'est le déplacer, donc deux opérations. `SET sk = :v` lève « Cannot update attribute sk. This attribute is part of the key » (mesuré avec moto). Pour ne rien perdre ni dupliquer entre les deux, on groupe `Delete` et `Put` dans un `TransactWriteItems`. Conséquence de conception : ne pas mettre dans une clé une donnée qui change (statut, nom).
- Usage : ✅ clés faites d'identifiants stables (SIREN, id d'annonce, date de l'événement) · ❌ `sk = STATUT#ouverte`, qu'il faudra déplacer à la clôture.

```
# Exemple 1 : la réponse de DynamoDB
UpdateItem Key={pk: u1, sk: R#2026-10-01}
  UpdateExpression="SET sk = :v"
→ ValidationException : Cannot
  update attribute sk. This
  attribute is part of the key
```

```python
# Exemple 2 : mesuré avec moto
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
t.update_item(Key={"pk": "u1", "sk": "R#1"},
  UpdateExpression="SET sk = :v",
  ExpressionAttributeValues={":v": "R#2"})  # ❌ ClientError
m.stop()
```

- Quiz : Pour corriger `R#2026-10-01` en `R#2026-10-02`, on fait seulement un `PutItem` avec la nouvelle `sk`. Combien d'items ?
- [ ] 1 : le `PutItem` déplace l'item
- [x] 2 : l'ancien item reste
- [ ] 1 : le `PutItem` est refusé
- [ ] 0 : conflit, les deux sont rejetés
- Réponse : 2 (mesuré avec moto) : une autre `sk`, c'est un autre item ; l'ancien n'est supprimé que par un `DeleteItem` explicite.

## 15. motifs d'accès : avant les clés
- Id : dynamodb-motifs-acces
- Sous-thème : clés
- Type : concept
- Niveau : 1
- Profils : débutant, web, data
- Voir aussi : dynamodb-cle-partition-et-tri, dynamodb-single-table-limites
- Source : data-platform · pwa-sync
- Définition : En DynamoDB, on liste d'abord les lectures et écritures de l'application, puis on choisit `pk`, `sk` et index qui les servent toutes.
- Contexte : C'est l'inverse du SQL, où l'on normalise puis on écrit les requêtes. Chaque motif doit tenir dans un `GetItem` ou une `Query` (égalité sur `pk`, plage sur `sk`) ; un motif oublié se paie en `Scan` ou en nouvel index. La doc AWS demande de déterminer motifs d'accès et débits de chaque table et index avant de concevoir les clés.
- Usage : ✅ un tableau « motif → clé → opération » relu avant de créer la table · ❌ créer la table puis découvrir les requêtes : migration de toutes les données.

```
# Exemple 1 : motifs → clés (BODACC)
Fiche d'un SIREN
  pk = SIREN#…   sk = META
  → GetItem
Annonces d'un SIREN, par date
  pk = SIREN#…   sk = ANNONCE#<date>
  → Query + begins_with(sk, "ANNONCE#")
```

- Quiz : Nouveau motif « annonces du jour, tous SIREN confondus ». Avec ces clés, quelle opération ?
- [ ] Une `Query` sur la `sk` seule
- [ ] `begins_with(pk, "SIREN#")`
- [ ] Un `GetItem` par date
- [x] Un `Scan`, ou un index par date
- Réponse : un `Scan`, ou un index par date : la `pk` est obligatoire et en égalité dans une `Query` ; un motif non prévu demande un index ou relit toute la table.

## 16. faible cardinalité : date, statut
- Id : dynamodb-faible-cardinalite
- Sous-thème : clés
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Voir aussi : dynamodb-debit-par-partition, dynamodb-write-sharding
- Source : data-platform · pwa-sync
- Définition : Une clé de partition à peu de valeurs distinctes (statut, date du jour, pays) concentre le trafic sur quelques partitions : piège classique.
- Contexte : DynamoDB répartit les items par hachage de la `pk`, et chaque partition a un débit maximal. `pk = statut` (ouverte, close) ne donne que deux adresses, quelle que soit la taille de la table. `pk = date du jour` envoie toutes les écritures du jour sur la même valeur. Bonne `pk` : beaucoup de valeurs, sollicitées à peu près également (SIREN, identité Cognito).
- Usage : ✅ `pk` = identifiant à forte cardinalité (SIREN, id utilisateur) · ❌ `pk` = booléen, statut, type ou date du jour pour un trafic soutenu.

```python
# Exemple 1 : valeurs distinctes de pk
annonces = [("483609327", "ouverte"),
  ("552100554", "close"),
  ("732829320", "ouverte")]
len({s for s, _ in annonces})    # → 3
len({st for _, st in annonces})  # → 2
# 32 000 annonces/jour : statut → 2 pk
```

- Quiz : Table d'état de l'ingestion : un item par journée, `pk = date`, une écriture par jour. Verdict ?
- [ ] Interdit : faible cardinalité
- [ ] À sharder obligatoirement
- [x] Acceptable : trafic minime par `pk`
- [ ] Interdit : une date n'est pas unique
- Réponse : acceptable : chaque date est une `pk` distincte écrite une fois par jour ; le piège est un trafic soutenu sur peu de valeurs, pas la date en soi.

## 17. GSI : lire par une autre clé
- Id : dynamodb-gsi-autre-cle
- Sous-thème : index
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Source : data-platform · pwa-sync
- Définition : Un index secondaire global (GSI) réorganise les items de la table sous une autre clé, interrogée par `Query` avec `IndexName`.
- Contexte : La table `annonces` est rangée par SIREN ; lire « les annonces du tribunal de Paris » demanderait un `Scan`. Un GSI de clé `tribunal` est une copie maintenue par DynamoDB, qu'on lit comme une table, sans jamais y écrire directement. On ne passe que `IndexName` en plus : la `KeyConditionExpression` porte alors sur les clés de l'index, plus sur celles de la table.
- Usage : ✅ un accès prévu sur un attribut hors clé (tribunal, date, statut) · ❌ une recherche ponctuelle d'admin : un `Scan` coûte moins qu'un index entretenu à chaque écriture.

```python
# Exemple 1 : la même Query, un IndexName
req = {"TableName": "annonces",
  "IndexName": "par-tribunal",
  "KeyConditionExpression": "tribunal = :t"}
req["IndexName"]  # → 'par-tribunal'
# la condition porte sur la clé de l'index
```

```python
# Exemple 2 : Query sur le GSI (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
S = lambda *n: [{"AttributeName": a, "AttributeType": "S"} for a in n]
H = lambda a, k="HASH": {"AttributeName": a, "KeyType": k}
t = boto3.resource("dynamodb", region_name="eu-west-3").create_table(
  TableName="annonces", BillingMode="PAY_PER_REQUEST",
  KeySchema=[H("pk"), H("sk", "RANGE")],
  AttributeDefinitions=S("pk", "sk", "tribunal"),
  GlobalSecondaryIndexes=[{"IndexName": "par-tribunal",
    "KeySchema": [H("tribunal")], "Projection": {"ProjectionType": "ALL"}}])
t.put_item(Item={"pk": "483609327", "sk": "A#1", "tribunal": "Paris"})
t.put_item(Item={"pk": "552100554", "sk": "A#1", "tribunal": "Lyon"})
r = t.query(IndexName="par-tribunal",
  KeyConditionExpression=Key("tribunal").eq("Paris"))
[i["pk"] for i in r["Items"]]  # → ['483609327']
m.stop()
```

- Quiz : On connaît `tribunal` et `pk`, `sk` d'une annonce. Peut-on faire un `GetItem` sur l'index `par-tribunal` ?
- [ ] Oui, avec `IndexName` et la clé de l'index
- [ ] Oui, si la projection est `ALL`
- [x] Non : `GetItem` ne lit que la table
- [ ] Non, sauf avec `ConsistentRead=True`
- Réponse : non : selon la doc, `GetItem` et `BatchGetItem` ne s'utilisent pas sur un index ; on y lit avec `Query` ou `Scan`, ou on fait le `GetItem` sur la table.

## 18. LSI ou GSI : quand on peut les créer
- Id : dynamodb-lsi-ou-gsi-creation
- Sous-thème : index
- Type : comparaison
- Niveau : 1
- Profils : débutant, ops
- Prérequis : dynamodb-gsi-autre-cle
- Source : data-platform · pwa-sync
- Définition : Un LSI (index secondaire local) se déclare seulement à la création de la table ; un GSI s'ajoute ou se supprime à tout moment.
- Contexte : Le LSI garde la clé de partition de la table et ne change que la clé de tri ; il vit et meurt avec la table (`CreateTable` seulement). Le GSI choisit librement sa clé de partition et sa clé de tri, et `UpdateTable` le crée ou le supprime sur une table remplie : DynamoDB le remplit en arrière-plan. Oublier un LSI au départ, c'est recréer la table et migrer les données.
- Usage : ✅ GSI par défaut, ajouté quand un nouvel accès apparaît · ❌ compter ajouter un LSI plus tard : impossible sans nouvelle table.

```python
# Exemple 1 : ajouter un GSI après coup
gsi_update = [{"Create": {
  "IndexName": "par-tribunal",
  "KeySchema": [{"AttributeName": "tribunal",
                 "KeyType": "HASH"}],
  "Projection": {"ProjectionType": "ALL"}}}]
next(iter(gsi_update[0]))  # → 'Create'
```

```python
# Exemple 2 : UpdateTable n'a pas de LSI (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
c = boto3.client("dynamodb", region_name="eu-west-3")
c.create_table(TableName="annonces", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
c.update_table(TableName="annonces", LocalSecondaryIndexes=[])  # ❌ ParamValidationError
m.stop()
```

- Quiz : Table `annonces` (pk = SIREN) en prod. On veut ses annonces triées par `date`, même SIREN. Que fait-on ?
- [ ] On ajoute un LSI `date` par `UpdateTable`
- [x] Un GSI pk = SIREN, sk = `date`
- [ ] On change la clé de tri de la table
- [ ] Un LSI, via un `terraform apply` sans recréation
- Réponse : un GSI : il peut reprendre la même clé de partition avec une autre clé de tri, et s'ajoute sur une table existante ; un LSI exigerait une nouvelle table.

## 19. projection : ce que l'index recopie
- Id : dynamodb-projection-index
- Sous-thème : index
- Type : concept
- Niveau : 1
- Profils : web, data
- Prérequis : dynamodb-gsi-autre-cle
- Source : data-platform · pwa-sync
- Définition : La projection fixe les attributs copiés dans l'index : `KEYS_ONLY` (les clés), `INCLUDE` (clés + liste choisie), `ALL` (tout l'item).
- Contexte : Les clés de la table et de l'index sont toujours projetées. Plus la projection est large, plus l'index coûte en stockage et en écritures (chaque modification d'un attribut projeté réécrit l'entrée d'index), mais moins on a besoin de revenir à la table. `INCLUDE` est le compromis : on copie seulement ce que l'écran affiche (`nom`, `type`).
- Usage : ✅ `INCLUDE` avec les attributs que la requête renvoie vraiment · ❌ `ALL` par réflexe sur un gros item : stockage doublé, écritures plus chères.

```python
# Exemple 1 : INCLUDE ["nom"] (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
S = lambda *n: [{"AttributeName": a, "AttributeType": "S"} for a in n]
H = lambda a, k="HASH": {"AttributeName": a, "KeyType": k}
t = boto3.resource("dynamodb", region_name="eu-west-3").create_table(
  TableName="annonces", BillingMode="PAY_PER_REQUEST",
  KeySchema=[H("pk"), H("sk", "RANGE")],
  AttributeDefinitions=S("pk", "sk", "tribunal"),
  GlobalSecondaryIndexes=[{"IndexName": "par-tribunal", "KeySchema": [H("tribunal")],
    "Projection": {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["nom"]}}])
t.put_item(Item={"pk": "483609327", "sk": "A#1",
  "tribunal": "Paris", "nom": "ACME", "capital": 10000})
r = t.query(IndexName="par-tribunal", KeyConditionExpression=Key("tribunal").eq("Paris"))
sorted(r["Items"][0])  # → ['nom', 'pk', 'sk', 'tribunal']
m.stop()
```

- Quiz : GSI `KEYS_ONLY`, clés `tribunal` et `date`, sur la table (`pk`, `sk`). Que contient une entrée d'index ?
- [ ] `tribunal` et `date` seulement
- [x] `tribunal`, `date`, `pk` et `sk`
- [ ] `pk` et `sk` seulement
- [ ] Tout l'item, sans les valeurs
- Réponse : les quatre : les clés de la table sont toujours projetées en plus des clés de l'index, même en `KEYS_ONLY`.

## 20. global_secondary_index : en Terraform
- Id : dynamodb-gsi-terraform
- Sous-thème : index
- Type : recette
- Niveau : 1
- Profils : ops
- Prérequis : dynamodb-gsi-autre-cle, dynamodb-projection-index
- Source : data-platform · pwa-sync
- Définition : Un bloc `global_secondary_index` décrit un GSI dans `aws_dynamodb_table` : nom, clés (`key_schema`), `projection_type`, `non_key_attributes` pour `INCLUDE`.
- Contexte : Chaque clé d'index doit aussi avoir son bloc `attribute` (type `S`, `N` ou `B`) ; les `non_key_attributes`, non. Depuis le provider AWS 6.x récent, `hash_key` / `range_key` dans le GSI sont dépréciés au profit de `key_schema` (mesuré en 6.69.1 : avertissement au `validate`). Ajouter un GSI est une mise à jour en place.
- Usage : ✅ un `attribute` par clé d'index, `INCLUDE` pour les attributs affichés · ❌ déclarer `siren` en `attribute` parce qu'il est projeté : il n'est pas une clé.

```hcl
# Exemple 1 : GSI par tribunal et date
global_secondary_index {
  name               = "par-tribunal"
  projection_type    = "INCLUDE"
  non_key_attributes = ["siren", "type"]
  key_schema {
    attribute_name = "tribunal"
    key_type       = "HASH"
  }
  key_schema {
    attribute_name = "date"
    key_type       = "RANGE"
  }
}
# + attribute "tribunal" et "date" (type S)
```

- Quiz : On écrit ce GSI sans bloc `attribute { name = "tribunal" }`. Que se passe-t-il ?
- [ ] Rien : le type `S` est déduit
- [ ] `terraform validate` échoue
- [x] Le plan échoue : index sans attribut défini
- [ ] L'apply crée un index vide
- Réponse : le plan échoue (mesuré, provider 6.69.1 : « all indexes must match a defined attribute ») ; `validate` passe, l'erreur vient au plan.

## 21. Query : une seule partition
- Id : dynamodb-query-une-partition
- Sous-thème : lecture
- Type : concept
- Niveau : 1
- Profils : débutant, web, data
- Voir aussi : dynamodb-scan-toute-la-table
- Source : data-platform · pwa-sync
- Définition : `Query` lit les lignes d'une seule clé de partition (`pk = :pk`), éventuellement restreintes à une plage de `sk`, triées par `sk`.
- Contexte : C'est la lecture efficace : DynamoDB va directement à la partition, on ne paie que ce qui est lu. Le `pk` est obligatoire et toujours en égalité ; sans lui, la requête est refusée (`Query condition missed key schema element`, mesuré avec moto). Pour lire plusieurs utilisateurs, il faut plusieurs `Query`.
- Usage : ✅ toute lecture « les lignes de X » prévue par le modèle · ❌ chercher par un attribut hors clé : il faut un index secondaire, ou repenser les clés.

```bash
# Exemple 1 : sa partition, compte seul
aws dynamodb query --table-name "$table" \
  --key-condition-expression "pk = :pk" \
  --expression-attribute-values \
  '{":pk":{"S":"eu-west-3:1b2c…"}}' \
  --select COUNT --query Count
# → 0   (mesuré, partition vide)
```

```python
# Exemple 2 : Query réelle (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
t.put_item(Item={"pk": "u1", "sk": "V#mac"})
t.put_item(Item={"pk": "u2", "sk": "V#mac"})
r = t.query(KeyConditionExpression=Key("pk").eq("u1"))
r["Count"]  # → 1
m.stop()
```

- Quiz : `--key-condition-expression "sk = :sk"`, sans `pk`. Résultat ?
- [ ] Toutes les lignes de cette `sk`, tous utilisateurs
- [ ] Un `Scan` filtré automatiquement
- [x] `ValidationException` : `pk` manquant
- [ ] Une liste vide
- Réponse : `ValidationException` (mesuré avec moto : « Query condition missed key schema element: pk ») : une `Query` exige l'égalité sur la clé de partition.

## 22. Scan : toute la table
- Id : dynamodb-scan-toute-la-table
- Sous-thème : lecture
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : dynamodb-query-une-partition
- Source : data-platform · pwa-sync
- Définition : `Scan` lit toutes les lignes de la table, toutes partitions confondues, et facture tout ce qu'il lit.
- Contexte : Pas de clé : DynamoDB parcourt la table entière, page par page (1 Mo). Un `FilterExpression` ne réduit pas le coût, il trie après lecture. C'est l'équivalent d'un `SELECT *` sans `WHERE` : acceptable pour un export ou un script d'admin, jamais dans le chemin d'une app. Pour un utilisateur de l'app, il doit être refusé par IAM.
- Usage : ✅ export ponctuel, migration, petite table d'admin · ❌ lecture courante de l'app : `Query` sur la partition.

```python
# Exemple 1 : Query ou Scan, en dict
table = {"u1": ["V#mac", "T#mac"],
         "u2": ["V#ios"]}
len(table["u1"])                   # → 2
sum(len(v) for v in table.values())  # → 3
# Query lit 2 lignes, Scan en lit 3
```

- Quiz : Table de 10 Go, `Scan` avec un `FilterExpression` qui ne garde qu'une ligne. Que paie-t-on ?
- [ ] Une ligne
- [ ] Rien : le filtre évite la lecture
- [x] Les 10 Go lus
- [ ] La moitié, grâce au filtre
- Réponse : les 10 Go : le filtre s'applique après la lecture ; la facture compte ce qui est lu, pas ce qui est renvoyé.

## 23. GetItem : la clé complète
- Id : dynamodb-getitem-cle-complete
- Sous-thème : lecture
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Source : data-platform · pwa-sync
- Définition : `GetItem` lit une seule ligne par sa clé primaire complète : `pk` seule sur une table simple, `pk` **et** `sk` sur une table composite.
- Contexte : C'est un accès direct, pas une recherche : DynamoDB calcule où vit la ligne à partir de la clé exacte. Ce n'est pas un `find()` sur un préfixe ni « la première ligne de la partition » : pour ça, il faut `Query`. Une clé en trop (attribut hors schéma) est refusée aussi (mesuré avec moto : « key element does not match the schema »).
- Usage : ✅ relire une ligne connue (`pk` + `sk` exactes), fiche d'un SIREN sur une table à clé simple · ❌ lire « les lignes d'un SIREN » : `Query` sur la partition.

```python
# Exemple 1 : pk + sk exactes (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="annonces",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
t.put_item(Item={"pk": "483609327",
  "sk": "A#2026-10-01", "tribunal": "Lyon"})
k = {"pk": "483609327", "sk": "A#2026-10-01"}
t.get_item(Key=k)["Item"]["tribunal"]  # → 'Lyon'
m.stop()
```

- Quiz : Même table : `t.get_item(Key={"pk": "483609327"})`, sans `sk`. Résultat ?
- [ ] La première annonce de la partition
- [ ] Toutes les annonces du SIREN
- [x] `ValidationException` : clé incomplète
- [ ] Une réponse sans `Item`
- Réponse : `ValidationException` (selon la doc, mesuré avec moto) : sur une table composite, `GetItem` exige `pk` et `sk` ; pour une partition entière, c'est `Query`.

## 24. GetItem : ligne absente, pas d'erreur
- Id : dynamodb-getitem-ligne-absente
- Sous-thème : lecture
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Prérequis : dynamodb-getitem-cle-complete
- Source : data-platform · pwa-sync
- Définition : Si aucune ligne n'a cette clé, `GetItem` répond `200` sans clé `Item` dans la réponse : ni exception, ni `Item` vide.
- Contexte : En TS, `GetCommand` renvoie `Item: undefined` ; en Python, la clé `Item` manque tout simplement, donc `r["Item"]` lève `KeyError`. On teste donc `r.get("Item")`. Ce n'est pas `ResourceNotFoundException`, réservée à une table ou un index inexistant. La lecture d'une clé absente reste facturée comme une lecture.
- Usage : ✅ `item = r.get("Item")` puis `if item is None` · ❌ `r["Item"]` sans test, ou attendre une exception pour détecter l'absence.

```python
# Exemple 1 : clé absente (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
r = t.get_item(Key={"pk": "u1", "sk": "V#mac"})
"Item" in r                  # → False
r.get("Item")                # → None
r["ResponseMetadata"]["HTTPStatusCode"]  # → 200
m.stop()
```

- Quiz : Un `GetItem` éventuel sur une clé absente (table à la demande) : que facture AWS ?
- [ ] Rien : aucune ligne lue
- [x] 0,5 unité de lecture, comme une ligne de 4 Ko
- [ ] Une erreur `ResourceNotFoundException`, gratuite
- [ ] 1 unité de lecture : lecture forte forcée
- Réponse : 0,5 unité : selon la doc, lire un item inexistant consomme quand même la lecture minimale (éventuelle = demi-unité).

## 25. Query : ordre croissant par défaut
- Id : dynamodb-query-ordre-croissant
- Sous-thème : lecture
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Prérequis : dynamodb-query-une-partition
- Source : data-platform · pwa-sync
- Définition : `ScanIndexForward` vaut `True` par défaut : une `Query` renvoie la partition dans l'ordre croissant de la `sk`, donc `Limit=1` donne la plus petite.
- Contexte : L'ordre n'est jamais celui d'insertion : les lignes sont rangées par `sk` à l'écriture. Une `sk` de type `S` se trie octet par octet (UTF-8), une `sk` de type `N` dans l'ordre numérique, selon la doc. Avec des dates ISO dans la `sk`, l'ordre par défaut va de la plus ancienne à la plus récente.
- Usage : ✅ `Limit=1` sans option pour « la première annonce d'un SIREN » · ❌ trier en Python après coup : DynamoDB rend déjà la partition triée.

```python
# Exemple 1 : la plus ancienne (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="annonces",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
for d in ["10-03", "10-01", "10-02"]:
    t.put_item(Item={"pk": "483609327",
                     "sk": f"A#2026-{d}"})
r = t.query(KeyConditionExpression=Key("pk").eq("483609327"), Limit=1)
r["Items"][0]["sk"]  # → 'A#2026-10-01'
m.stop()
```

- Quiz : `sk` de type `N` (numérique), valeurs écrites dans l'ordre 9, 10, 2. Que renvoie `Limit=1` sans option ?
- [ ] 9 : l'ordre d'insertion
- [ ] 10 : `"10"` est avant `"2"` en chaîne
- [x] 2 : tri numérique sur une `sk` `N`
- [ ] 10 : le plus grand d'abord
- Réponse : 2 (mesuré avec moto, conforme à la doc) : une `sk` de type `N` se trie numériquement ; le piège des chaînes ne vaut que pour le type `S`.

## 26. ConsistentRead : lire sa propre écriture
- Id : dynamodb-lecture-forte
- Sous-thème : lecture
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Source : data-platform · pwa-sync
- Définition : Les lectures sont éventuellement cohérentes par défaut ; `ConsistentRead=True` garantit de voir toutes les écritures réussies avant la lecture, pour un coût double.
- Contexte : En éventuel, un `GetItem` juste après un `PutItem` peut rendre l'ancienne valeur (ou rien) ; relu peu après, il rend la nouvelle. La lecture forte coûte 1 unité par 4 Ko au lieu de 0,5. Selon la doc, elle n'existe que sur la table et les index locaux : pas sur un GSI ni un stream, et une table globale en mode par défaut reste éventuelle entre régions.
- Usage : ✅ relire juste après avoir écrit (compteur affiché après `UpdateItem`, contrôle avant une décision) · ❌ partout par réflexe : double coût pour un écran qui tolère une seconde de retard.

```python
# Exemple 1 : le coût, en unités de lecture
import math
def rcu(octets, forte=False):
    u = math.ceil(octets / 4096)
    return u if forte else u / 2
rcu(1200)              # → 0.5  (défaut)
rcu(1200, forte=True)  # → 1
```

```python
# Exemple 2 : l'option dans l'appel
appel = {"TableName": "progress",
  "Key": {"pk": {"S": "u1"},
          "sk": {"S": "V#mac#IAM"}},
  "ConsistentRead": True}
appel.get("ConsistentRead", False)  # → True
```

- Quiz : `Query` sur un index secondaire global (GSI) avec `ConsistentRead=True`. Résultat ?
- [ ] Lecture forte, au double du prix
- [ ] Option ignorée, lecture éventuelle
- [x] `ValidationException`
- [ ] Lecture forte, mais sur la table de base
- Réponse : `ValidationException` (selon la doc, mesuré avec moto : « Consistent reads are not supported on global secondary indexes ») : un GSI est toujours éventuel.

## 27. BatchGetItem : plusieurs tables, un appel
- Id : dynamodb-batchgetitem
- Sous-thème : lecture
- Type : concept
- Niveau : 1
- Profils : web, data
- Prérequis : dynamodb-getitem-cle-complete
- Source : data-platform · pwa-sync
- Définition : `BatchGetItem` lit jusqu'à 100 items par clé exacte, dans une ou plusieurs tables, en un seul appel réseau.
- Contexte : C'est N `GetItem` regroupés, pas une `Query` : chaque clé est complète (`pk` et `sk`). La réponse est rangée par table dans `Responses`. La lecture est éventuellement cohérente par défaut ; `ConsistentRead` se règle table par table, pas pour tout l'appel. Au-delà de 100 clés, ou si une clé apparaît deux fois, tout l'appel est refusé (`ValidationException`, selon la doc et mesuré avec moto).
- Usage : ✅ fiches de plusieurs SIREN connus, une carte et son tribunal dans deux tables · ❌ « toutes les lignes de u1 » : c'est une `Query` sur la partition.

```python
# Exemple 1 : deux tables, un appel (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
db = boto3.resource("dynamodb", region_name="eu-west-3")
for n in ("annonces", "tribunaux"):
  db.create_table(TableName=n,
    BillingMode="PAY_PER_REQUEST",
    KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
    AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
  db.Table(n).put_item(Item={"pk": "A1"})
r = db.meta.client.batch_get_item(RequestItems={
  "annonces": {"Keys": [{"pk": "A1"}]},
  "tribunaux": {"Keys": [{"pk": "A1"}],
                "ConsistentRead": True}})
sorted(r["Responses"])  # → ['annonces', 'tribunaux']
r["UnprocessedKeys"]    # → {}
m.stop()
```

- Quiz : `BatchGetItem` sur 3 clés dont une n'existe pas dans la table. Que se passe-t-il ?
- [ ] `ResourceNotFoundException` pour tout l'appel
- [ ] La clé absente revient dans `UnprocessedKeys`
- [x] 2 items dans `Responses`, rien pour la troisième
- [ ] 3 items, dont un `None`
- Réponse : 2 items : une clé absente n'est simplement pas renvoyée (selon la doc, mesuré avec moto) ; `UnprocessedKeys` ne sert qu'aux lectures non faites.

## 28. PutItem : remplace toute la ligne
- Id : dynamodb-putitem-remplace
- Sous-thème : écriture
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Voir aussi : dynamodb-updateitem-partiel
- Source : data-platform · pwa-sync
- Définition : `PutItem` écrit la ligne entière : si la clé existe, l'ancienne ligne est remplacée, attributs absents compris.
- Contexte : Pas de fusion : un `PutItem` avec `{pk, sk, m}` efface `n` qui était là. Pour modifier un attribut sans toucher aux autres, c'est `UpdateItem` (`SET n = :v`). Pour refuser l'écrasement, `ConditionExpression="attribute_not_exists(pk)"`. Dans pwa-sync, chaque ligne porte toute sa valeur (dernier état), donc le remplacement est voulu et idempotent.
- Usage : ✅ ligne qui porte tout son état (rejeu = même résultat) · ❌ modifier un compteur ou un champ isolé : `UpdateItem`.

```python
# Exemple 1 : le 2e put efface n (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
t.put_item(Item={"pk": "u1", "sk": "V#mac", "n": 5})
t.put_item(Item={"pk": "u1", "sk": "V#mac", "m": 7})
k = {"pk": "u1", "sk": "V#mac"}
"n" in t.get_item(Key=k)["Item"]  # → False
m.stop()
```

- Quiz : `put_item(Item={"pk": "u1", "sk": "V#mac", "vues": 12})` est rejoué 3 fois après des timeouts. Résultat ?
- [x] 1 ligne, `vues` = 12
- [ ] 1 ligne, `vues` = 36
- [ ] 3 lignes identiques
- [ ] `ConditionalCheckFailedException` au 2e envoi
- Réponse : 1 ligne, `vues` = 12 : même clé, chaque `PutItem` remplace la ligne par le même contenu ; écrire un état complet est idempotent, contrairement à `ADD`.

## 29. UpdateItem : modifier sans réécrire
- Id : dynamodb-updateitem-partiel
- Sous-thème : écriture
- Type : concept
- Niveau : 1
- Profils : débutant, web
- Voir aussi : dynamodb-putitem-remplace
- Source : data-platform · pwa-sync
- Définition : `UpdateItem` modifie certains attributs d'une ligne par une `UpdateExpression` (`SET`, `REMOVE`…) et laisse les autres intacts.
- Contexte : C'est le `PATCH` de DynamoDB, là où `PutItem` est un `PUT`. Les valeurs passent par des jetons `:v` dans `ExpressionAttributeValues`, jamais en clair dans l'expression. Les attributs de clé (`pk`, `sk`) ne se modifient pas : mesuré avec moto, `SET sk = :v` lève `ValidationException` (« Cannot update attribute sk »). Changer de clé = supprimer puis recréer la ligne.
- Usage : ✅ changer un ou deux champs d'une ligne existante sans la relire · ❌ réécrire toute la ligne à chaque fois : `PutItem` suffit et reste idempotent.

```python
# Exemple 1 : SET a, REMOVE b (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "V#mac"}
t.put_item(Item={**k, "a": 1, "b": 2, "c": 3})
r = t.update_item(Key=k,
  UpdateExpression="SET a = :v REMOVE b",
  ExpressionAttributeValues={":v": 9},
  ReturnValues="ALL_NEW")["Attributes"]
(r["a"], "b" in r, r["c"])  # → (9, False, 3)
m.stop()
```

- Quiz : `UpdateExpression="REMOVE vues"` sur une ligne qui n'a pas d'attribut `vues`. Résultat ?
- [ ] `ValidationException` : attribut inconnu
- [ ] `ConditionalCheckFailedException`
- [x] Rien ne change, pas d'erreur
- [ ] La ligne entière est supprimée
- Réponse : rien ne change : selon la doc (et mesuré avec moto), `REMOVE` d'un attribut absent ne fait rien ; seule la ligne est touchée, jamais supprimée.

## 30. UpdateItem : crée la ligne si absente
- Id : dynamodb-updateitem-upsert
- Sous-thème : écriture
- Type : piège
- Niveau : 1
- Profils : débutant, web
- Prérequis : dynamodb-updateitem-partiel
- Voir aussi : dynamodb-creer-si-absent
- Source : data-platform · pwa-sync
- Définition : Sur une clé qui n'existe pas, `UpdateItem` crée la ligne avec la clé et les attributs posés par l'expression (upsert).
- Contexte : Pas besoin d'un `PutItem` d'initialisation avant le premier incrément : `UpdateItem` fait « insérer ou mettre à jour » en un appel (≈ `INSERT … ON CONFLICT DO UPDATE`). Revers : une faute de frappe dans la clé crée une ligne fantôme, sans erreur. Pour ne modifier qu'une ligne existante, ajouter `ConditionExpression="attribute_exists(pk)"`.
- Usage : ✅ compteurs et états créés au premier passage (`V#mac#IAM`) · ❌ « modifier seulement si elle existe » sans condition : ligne créée en silence.

```python
# Exemple 1 : la ligne n'existait pas
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "V#mac#IAM"}
t.update_item(Key=k,
  UpdateExpression="SET vues = :un",
  ExpressionAttributeValues={":un": 1})
t.get_item(Key=k)["Item"]["vues"]  # → 1
m.stop()
```

- Quiz : La Lambda écrit `SET ok = :t` avec `sk = "R#2026-1O-25"` (lettre O au lieu du zéro). Que se passe-t-il ?
- [ ] `ValidationException` : clé introuvable
- [ ] `ConditionalCheckFailedException`
- [x] Une nouvelle ligne `R#2026-1O-25` est créée
- [ ] La ligne `R#2026-10-25` est modifiée
- Réponse : une nouvelle ligne : sans `ConditionExpression`, `UpdateItem` crée toute clé absente ; la faute passe inaperçue.

## 31. ADD : un attribut absent part de 0
- Id : dynamodb-add-compteur
- Sous-thème : écriture
- Type : recette
- Niveau : 1
- Profils : débutant, web
- Prérequis : dynamodb-updateitem-partiel
- Source : data-platform · pwa-sync
- Définition : `ADD n :x` sur un attribut `n` absent le crée avec la valeur `:x`, comme si `n` valait 0.
- Contexte : Pratique : un compteur n'a pas besoin d'être initialisé, le premier `ADD` le crée (la ligne aussi, grâce à l'upsert). Une valeur négative décrémente. La doc recommande pourtant `SET` quand on veut l'idempotence : rejouer un `ADD` (réessai après un timeout) compte deux fois.
- Usage : ✅ compteur de vues ou de réponses sans lecture préalable · ❌ écriture rejouée par une file (SQS, outbox) : `SET` d'une valeur absolue, idempotent.

```python
# Exemple 1 : premier ADD = la valeur
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "V#mac#IAM"}
def vue():
    return t.update_item(Key=k,
      UpdateExpression="ADD vues :un",
      ExpressionAttributeValues={":un": 1},
      ReturnValues="UPDATED_NEW")["Attributes"]
vue()["vues"]  # → 1
vue()["vues"]  # → 2
m.stop()
```

- Quiz : `ADD solde :x` avec `:x = -3` sur une ligne sans attribut `solde`. Valeur de `solde` ?
- [ ] `0` : un compteur absent ne descend pas
- [x] `-3`
- [ ] `ValidationException` : attribut absent
- [ ] `3` : valeur absolue
- Réponse : `-3` (mesuré avec moto) : l'attribut absent vaut 0 pour `ADD`, et une valeur négative est soustraite.

## 32. attribute_not_exists(pk) : créer si absent
- Id : dynamodb-creer-si-absent
- Sous-thème : écriture
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Prérequis : dynamodb-putitem-remplace
- Source : data-platform · pwa-sync
- Définition : `ConditionExpression="attribute_not_exists(pk)"` fait échouer un `PutItem` si une ligne existe déjà avec cette clé : écriture « créer seulement ».
- Contexte : La condition est évaluée sur la ligne de même clé, côté serveur, de façon atomique avec l'écriture : pas de course entre « vérifier » et « écrire » comme avec un `GetItem` préalable. On teste la clé de partition parce que toute ligne existante la porte forcément. Refus : `ConditionalCheckFailedException`, la ligne reste intacte.
- Usage : ✅ enregistrer une annonce BODACC une seule fois, réserver un identifiant · ❌ `GetItem` puis `PutItem` : deux écrivains passent le test en même temps.

```python
# Exemple 1 : le 2e put est refusé
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
L = {"pk": "u1", "sk": "R#2026-10-25#IAM/3"}
c = "attribute_not_exists(pk)"
t.put_item(Item={**L, "ok": True}, ConditionExpression=c)
t.put_item(Item={**L, "ok": False}, ConditionExpression=c)  # ❌ ClientError
t.get_item(Key=L)["Item"]["ok"]  # → True
m.stop()
```

- Quiz : On écrit `attribute_not_exists(ok)` au lieu de `pk` ; la ligne existe déjà, sans attribut `ok`. Résultat ?
- [ ] Refusé : la ligne existe
- [x] Accepté : la ligne est remplacée
- [ ] `ValidationException` : `ok` n'est pas une clé
- [ ] Accepté, mais `ok` seul est ajouté
- Réponse : accepté et remplacé (mesuré avec moto) : la condition porte sur `ok`, absent, donc vraie ; seul un attribut que toute ligne porte (la clé) teste l'existence.

## 33. ConditionalCheckFailedException : l'attraper
- Id : dynamodb-condition-echouee-exception
- Sous-thème : écriture
- Type : recette
- Niveau : 1
- Profils : débutant, web
- Prérequis : dynamodb-creer-si-absent
- Source : data-platform · pwa-sync
- Définition : Une condition fausse lève `ConditionalCheckFailedException`, à attraper par sa classe (`client.exceptions.…`) ou par le code de `ClientError`.
- Contexte : boto3 génère ses classes d'exception à l'exécution : pas d'import `from botocore… import ConditionalCheckFailedException`. On les trouve sur le client (`t.meta.client.exceptions` depuis une `Table`). Toutes héritent de `ClientError`, dont `e.response["Error"]["Code"]` porte le nom. En TS, `err.name === "ConditionalCheckFailedException"` (ou `instanceof`).
- Usage : ✅ attraper ce cas précis et le traiter comme « déjà fait » · ❌ `except Exception` : avale aussi le throttling et les erreurs de droits.

```python
# Exemple 1 : par la classe du client
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
E = t.meta.client.exceptions
try:
    t.update_item(Key={"pk": "u1", "sk": "V#mac"},
      UpdateExpression="REMOVE x",
      ConditionExpression="attribute_exists(pk)")
except E.ConditionalCheckFailedException as e:
    code = e.response["Error"]["Code"]
code  # → 'ConditionalCheckFailedException'
m.stop()
```

- Quiz : `except ClientError as e:` attrape un refus de condition. Comment le distinguer d'un `AccessDenied` ?
- [ ] `e.response["ResponseMetadata"]["HTTPStatusCode"] == 409`
- [x] `e.response["Error"]["Code"] == "ConditionalCheckFailedException"`
- [ ] `type(e) is ClientError`
- [ ] `str(e) == "ConditionalCheckFailed"`
- Réponse : le code d'erreur : les deux sont des `ClientError` en HTTP 400 (selon la doc de l'API) ; seul `Error.Code` les sépare.

## 34. DeleteItem : idempotent
- Id : dynamodb-deleteitem-idempotent
- Sous-thème : écriture
- Type : concept
- Niveau : 1
- Profils : web, data
- Voir aussi : Data engineering/ingestion-idempotence-ecraser
- Source : data-platform · pwa-sync
- Définition : `DeleteItem` sur une clé absente réussit sans rien faire : supprimer deux fois donne le même résultat qu'une fois.
- Contexte : Comme `DELETE` HTTP, l'appel est idempotent : un réessai après timeout est sans danger. La réponse est la même dans les deux cas : pour savoir si une ligne a vraiment été supprimée, demander `ReturnValues="ALL_OLD"` (présence de `Attributes`), ou exiger son existence avec `ConditionExpression="attribute_exists(pk)"`.
- Usage : ✅ purge rejouable (effacer les `V#…` d'un appareil retiré) · ❌ compter les suppressions sur le seul succès de l'appel : il réussit aussi sur une clé absente.

```python
# Exemple 1 : clé absente, pas d'erreur
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "V#ipad#IAM"}
r = t.delete_item(Key=k)
list(r)  # → ['ResponseMetadata']
m.stop()
```

- Quiz : Comment savoir si `delete_item(Key=k)` a effacé une ligne qui existait, sans erreur si elle n'existait pas ?
- [ ] Lire `r["Count"]` dans la réponse
- [ ] `ReturnValues="ALL_NEW"`, vide si supprimée
- [x] `ReturnValues="ALL_OLD"`, puis `"Attributes" in r`
- [ ] Attraper `ResourceNotFoundException`
- Réponse : `ALL_OLD` : `Attributes` revient seulement si une ligne a été supprimée (mesuré avec moto) ; `ALL_NEW` est refusé sur `DeleteItem` (`ValidationException`).

## 35. TransactWriteItems : quatre actions
- Id : dynamodb-transactwriteitems
- Sous-thème : transactions
- Type : concept
- Niveau : 1
- Profils : web, data
- Voir aussi : dynamodb-transaction-cout-double, dynamodb-transaction-annulee-raisons
- Source : data-platform · pwa-sync
- Définition : `TransactWriteItems` regroupe jusqu'à 100 actions `Put`, `Update`, `Delete` ou `ConditionCheck`, appliquées toutes ou aucune.
- Contexte : Chaque action porte sa clé, sa table et une `ConditionExpression` facultative ; si une seule condition échoue, rien n'est écrit. Contrairement à `BatchWriteItem`, `Update` est permis (incrément, `SET` partiel). Limites selon la doc : 100 actions, 4 Mo au total, jamais deux actions sur le même item. La doc déconseille les transactions pour l'ingestion en masse : coût double, `BatchWriteItem` y suffit.
- Usage : ✅ créer une annonce et incrémenter le compteur de son tribunal ensemble · ❌ charger 32 000 annonces du jour : `BatchWriteItem` (ou `batch_writer`).

```python
# Exemple 1 : Put + Update, tout ou rien
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
db = boto3.resource("dynamodb", region_name="eu-west-3")
t = db.create_table(TableName="bodacc",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
db.meta.client.transact_write_items(TransactItems=[
  {"Put": {"TableName": "bodacc",
    "Item": {"pk": "ANNONCE#A1"}}},
  {"Update": {"TableName": "bodacc",
    "Key": {"pk": "TRIB#Paris"},
    "UpdateExpression": "ADD n :un",
    "ExpressionAttributeValues": {":un": 1}}}])
t.get_item(Key={"pk": "TRIB#Paris"})["Item"]["n"]  # → 1
m.stop()
```

- Quiz : Une transaction peut-elle écrire dans `bodacc` et dans `progress` à la fois ?
- [ ] Non : une transaction = une table
- [x] Oui, si les deux tables sont dans le même compte et la même région
- [ ] Oui, même dans deux régions différentes
- [ ] Seulement avec `BatchWriteItem`
- Réponse : oui, même compte et même région : selon la doc, les actions peuvent viser plusieurs tables, jamais un autre compte ni une autre région.

## 36. PAY_PER_REQUEST : payer à la requête
- Id : dynamodb-mode-a-la-demande
- Sous-thème : capacité
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : dynamodb-mode-provisionne, dynamodb-prix-a-la-demande
- Source : data-platform · pwa-sync
- Définition : `billing_mode = "PAY_PER_REQUEST"` (à la demande) facture chaque lecture et écriture, sans capacité à réserver ni coût de débit au repos.
- Contexte : L'autre mode, `PROVISIONED`, réserve des unités de lecture et d'écriture par seconde : moins cher sous charge stable, payé même à vide, et limité (throttling) au-delà. À la demande s'adapte seul aux pics. Le stockage est facturé dans les deux modes. Pour une app de révision personnelle (quelques requêtes par session), c'est quelques centimes par mois.
- Usage : ✅ trafic faible, irrégulier ou inconnu, environnements de dev · ❌ trafic massif et stable : provisionné avec auto scaling, moins cher.

```hcl
# Exemple 1 : à la demande
resource "aws_dynamodb_table" "progress" {
  name         = "${local.prefix}-progress"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"
  # pas de read_capacity / write_capacity
}
```

- Quiz : Table à la demande, aucune requête pendant un mois, 1 Mo stocké. Que coûte-t-elle ?
- [ ] Rien du tout
- [x] Le stockage seulement (quasi nul)
- [ ] Un minimum de capacité réservée
- [ ] Le prix d'une instance arrêtée
- Réponse : le stockage seulement : à la demande, pas de requête = pas de frais de débit ; le Go stocké reste facturé.

## 37. PROVISIONED : read_capacity et write_capacity
- Id : dynamodb-mode-provisionne
- Sous-thème : capacité
- Type : concept
- Niveau : 1
- Profils : ops
- Voir aussi : dynamodb-provisionne-rentable
- Source : data-platform · pwa-sync
- Définition : En `billing_mode = "PROVISIONED"`, on réserve un débit : `read_capacity` (RCU) et `write_capacity` (WCU) par seconde, payés même sans trafic.
- Contexte : Une WCU = une écriture par seconde d'un item jusqu'à 1 Ko ; une RCU = une lecture forte par seconde jusqu'à 4 Ko (ou deux lectures éventuelles). Au-delà, les requêtes sont limitées (throttling). Chaque GSI d'une table provisionnée a ses propres capacités. Le mode par défaut du provider est `PROVISIONED` : l'omettre sans capacités est un oubli courant.
- Usage : ✅ charge régulière et connue, avec auto scaling · ❌ trafic faible ou imprévisible : `PAY_PER_REQUEST`.

```python
# Exemple 1 : WCU pour 10 écritures/s de 2,5 Ko
import math
ko = 2.5
math.ceil(ko) * 10  # → 30   (arrondi au Ko)
```

```hcl
# Exemple 2 : table provisionnée
resource "aws_dynamodb_table" "annonces" {
  name           = "${local.prefix}-annonces"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 30
  hash_key       = "pk"
}
```

- Quiz : Cette table provisionnée reçoit un `global_secondary_index`. Que faut-il y ajouter ?
- [ ] Rien : il partage les capacités de la table
- [x] Ses propres `read_capacity` et `write_capacity`
- [ ] `billing_mode = "PAY_PER_REQUEST"` dans le bloc
- [ ] Seulement `read_capacity`
- Réponse : ses propres capacités : selon la doc du provider, elles sont à fixer pour chaque GSI en `PROVISIONED` ; ses lectures et écritures consomment celles de l'index.

## 38. à la demande : le prix par million
- Id : dynamodb-prix-a-la-demande
- Sous-thème : capacité
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Source : data-platform · pwa-sync
- Définition : À la demande, on paie par million d'unités de requête : en us-east-1, 0,625 $ l'écriture, 0,125 $ la lecture (classe Standard).
- Contexte : Prix relevés sur aws.amazon.com/dynamodb/pricing (us-east-1, N. Virginia, octobre 2026) ; pour Paris (eu-west-3), relire l'onglet de la région sur la page. Une unité d'écriture couvre 1 Ko, une unité de lecture 4 Ko en lecture forte (deux lectures éventuelles). Le stockage (0,25 $ par Go-mois en us-east-1) s'ajoute. Pour pwa-sync, quelques milliers de requêtes par mois : moins d'un centime.
- Usage : ✅ estimer le coût d'un usage : requêtes × unités × prix · ❌ comparer au mode provisionné sans le taux d'utilisation (voir la carte « provisionné : rentable »).

```python
# Exemple 1 : pwa-sync, un mois (us-east-1)
ecritures = 200 * 30      # 200 par jour
lectures = 50 * 30
cout = (ecritures * 0.625
        + lectures * 0.125) / 1e6
round(cout, 5)  # → 0.00394  (dollar)
```

- Quiz : Un million d'écritures d'items de 3 Ko chacun, à la demande en us-east-1. Combien ?
- [ ] 0,625 $
- [ ] 0,375 $
- [x] 1,875 $
- [ ] 0,125 $
- Réponse : 1,875 $ : une unité d'écriture couvre 1 Ko, un item de 3 Ko en consomme 3, soit 3 millions d'unités à 0,625 $.

## 39. throttling : deux exceptions
- Id : dynamodb-throttling-exceptions
- Sous-thème : capacité
- Type : concept
- Niveau : 1
- Profils : ops, web
- Voir aussi : dynamodb-debit-par-partition
- Source : data-platform · pwa-sync
- Définition : Une requête refusée faute de débit lève `ProvisionedThroughputExceededException` (capacité provisionnée dépassée) ou `ThrottlingException` (plafond à la demande, quota).
- Contexte : Les deux signifient « trop vite, réessaie plus tard », pas « requête invalide ». Le champ `ThrottlingReasons` de l'erreur dit pourquoi (table, index, partition) selon la doc. Les SDK AWS réessaient eux-mêmes ces erreurs avec un délai croissant : l'application ne les voit qu'une fois les réessais épuisés. Pour les lots, le throttling partiel passe par `UnprocessedItems` / `UnprocessedKeys`, sans exception.
- Usage : ✅ traiter les deux codes comme « réessayable », alerter sur la métrique `ThrottledRequests` · ❌ les traiter comme une erreur de données et abandonner l'écriture.

```python
# Exemple 1 : classer l'erreur (forme boto3)
REESSAYABLES = {
  "ProvisionedThroughputExceededException",
  "ThrottlingException"}
err = {"Error": {"Code": "ThrottlingException"},
  "ResponseMetadata": {"HTTPStatusCode": 400}}
err["Error"]["Code"] in REESSAYABLES  # → True
```

- Quiz : Côté HTTP, quel code renvoie DynamoDB pour une requête limitée en débit ?
- [ ] 429 Too Many Requests
- [ ] 503 Service Unavailable
- [x] 400, avec le nom de l'exception dans le corps
- [ ] 500 Internal Server Error
- Réponse : 400 : selon la doc de l'API, les deux exceptions de throttling sont des erreurs 400 ; c'est le code dans le corps qui dit « réessayable », pas le statut HTTP.

## 40. TTL : un nombre en secondes epoch
- Id : dynamodb-ttl-epoch-secondes
- Sous-thème : exploitation
- Type : piège
- Niveau : 1
- Profils : débutant, web, data
- Source : data-platform · pwa-sync
- Définition : Le TTL supprime seul un item dont l'attribut désigné (`expire_at`) contient une date passée, en secondes epoch, de type nombre (`N`).
- Contexte : On active le TTL une fois par table en nommant l'attribut (sensible à la casse) ; chaque item porte ensuite sa propre date. Selon la doc : une chaîne (`"2026-11-24"`) ou tout autre format est ignoré sans erreur, et une date de plus de cinq ans dans le passé n'est jamais traitée. En JS, `Date.now()` donne des millisecondes : diviser par 1000.
- Usage : ✅ sessions, jetons, données temporaires qui doivent disparaître seules · ❌ purge à heure fixe exigée : la suppression est différée, faire un `DeleteItem`.

```python
# Exemple 1 : expirer dans 30 jours
from datetime import datetime, timezone
now = datetime(2026, 10, 25,
               tzinfo=timezone.utc)
expire_at = int(now.timestamp()) + 30 * 86400
expire_at  # → 1795478400
len(str(expire_at))  # → 10   (secondes)
```

```python
# Exemple 2 : activer et vérifier (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
c = boto3.client("dynamodb", region_name="eu-west-3")
c.create_table(TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk",
    "AttributeType": "S"}])
c.update_time_to_live(TableName="progress",
  TimeToLiveSpecification={"Enabled": True,
    "AttributeName": "expire_at"})
d = c.describe_time_to_live(TableName="progress")
d["TimeToLiveDescription"]["TimeToLiveStatus"]
# → 'ENABLED'
m.stop()
```

- Quiz : Le front écrit `expire_at = Date.now() + 86400000` (un jour en ms). Quand l'item est-il supprimé ?
- [ ] Dans un jour, DynamoDB convertit les ms
- [ ] Jamais : l'écriture est refusée
- [x] En pratique jamais : la date tombe vers l'an 58 000
- [ ] Tout de suite : valeur hors plage
- Réponse : en pratique jamais : lue en secondes, `1 793 000 000 000` est une date très lointaine ; l'écriture passe, le TTL attend.

## 41. jointures : Aurora, pas DynamoDB
- Id : dynamodb-jointures-aurora
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-acces-inconnus-sql
- Source : data-platform · pwa-sync
- Définition : Jointures et transactions relationnelles sur plusieurs tables : on choisit Aurora ou RDS ; DynamoDB ne joint pas, il faudrait joindre dans le code.
- Contexte : Cas type : relier annonces, entreprises et dirigeants, et modifier un dossier et ses pièces dans une même transaction, avec clés étrangères. DynamoDB n'a ni `JOIN` ni intégrité référentielle : selon la doc, le `SELECT` PartiQL lit une seule table (`FROM table[.index]`). Ses transactions sont atomiques mais ne vérifient aucun lien entre tables. Aurora a un coût au repos, sauf pause à 0 ACU.
- Usage : ✅ modèle relationnel riche, contraintes, requêtes multi-tables en ligne · ❌ DynamoDB et des jointures à la main dans chaque Lambda.

```python
# Exemple 1 : un JOIN, une requête
import sqlite3
db = sqlite3.connect(":memory:")
db.executescript("""
CREATE TABLE ent(siren, nom);
CREATE TABLE ann(siren, type);
INSERT INTO ent VALUES ('483609327','ACME');
INSERT INTO ann VALUES ('483609327','RJ');
""")
db.execute("SELECT nom, type FROM ent"
  " JOIN ann USING (siren)").fetchall()
# → [("ACME", "RJ")]
```

- Quiz : Les deux tables sont dans DynamoDB. Comment obtenir le résultat de ce `JOIN` ?
- [ ] Un `SELECT … JOIN` en PartiQL
- [x] Deux lectures, puis la jointure dans le code
- [ ] Un GSI qui couvre les deux tables
- [ ] Une `FilterExpression` qui lit l'autre table
- Réponse : deux lectures et une jointure côté code : PartiQL ne lit qu'une table, un index n'appartient qu'à sa table, un filtre ne voit que la ligne lue.

## 42. cache : ElastiCache ou DynamoDB
- Id : dynamodb-cache-elasticache
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : web, ops
- Voir aussi : dynamodb-dax-cache
- Source : data-platform · pwa-sync
- Définition : Pour un cache à la microseconde devant une base, on choisit ElastiCache ; DynamoDB répond en millisecondes et suffit comme cache simple.
- Contexte : Prix Paris (liste de prix AWS, octobre 2026) : ElastiCache Serverless Valkey 0,098 $ par Go-heure, avec 100 Mo facturés au minimum par cache, soit environ 7 $ par mois sans aucune requête. DynamoDB à la demande : 0 $ au repos, et un attribut TTL pour purger. DAX, cache dédié à DynamoDB, existe aussi (nœuds à l'heure). Pour quelques centaines d'appels par jour, une table suffit.
- Usage : ✅ ElastiCache pour un fort trafic sous la milliseconde ; DynamoDB + TTL pour un petit cache d'API · ❌ un cluster ElastiCache pour 200 appels par jour.

```python
# Exemple 1 : coût au repos, Paris (USD)
go_h = 0.098         # Valkey Serverless
mini = 0.1           # 100 Mo facturés
round(mini * go_h * 730, 2)   # → 7.15
ddb_repos = 0        # à la demande
```

```
# Exemple 2 : la décision, data-platform
Besoin  : garder 24 h les réponses
          d'une API externe à quota,
          300 appels par jour
→ Choix : DynamoDB + attribut TTL
Écarté  : ElastiCache (~7 $/mois
          au repos, µs inutiles)
```

- Quiz : Une API sert 50 000 lectures/s sur les mêmes 1 000 SIREN, avec une latence visée sous la milliseconde. Quel choix ?
- [ ] DynamoDB à la demande, seul
- [x] ElastiCache devant la base
- [ ] DynamoDB avec plus de GSI
- [ ] Athena avec réutilisation des résultats
- Réponse : ElastiCache : DynamoDB répond en millisecondes ; sous la milliseconde à ce débit, il faut un cache en mémoire devant (ou DAX).

## 43. coût au repos : table ou RDS, chiffré
- Id : dynamodb-cout-au-repos-rds
- Sous-thème : choisir
- Type : choisir
- Niveau : 2
- Profils : ops
- Voir aussi : couts-cout-au-repos
- Source : data-platform · pwa-sync
- Définition : À faible trafic, une table à la demande coûte des centimes par mois ; la plus petite base RDS PostgreSQL, environ 16 $ sans requête.
- Contexte : Prix Paris (liste de prix AWS, octobre 2026) : RDS `db.t4g.micro` PostgreSQL mono-AZ 0,018 $ de l'heure, stockage gp3 0,133 $ par Go-mois avec 20 Go au minimum. DynamoDB à la demande : 0,1487 $ par million de lectures, 0,7423 $ par million d'écritures, 25 Go de stockage offerts. Le point d'équilibre se compte en dizaines de millions de requêtes par mois.
- Usage : ✅ chiffrer les deux options au trafic réel avant de choisir · ❌ juger sur « une micro, c'est gratuit » : elle tourne 730 h par mois.

```python
# Exemple 1 : un mois, Paris (USD)
rds = 730 * 0.018 + 20 * 0.133
round(rds, 2)              # → 15.8
lec, ecr = 100_000, 10_000
ddb = (lec * 0.1487
       + ecr * 0.7423) / 1e6
round(ddb, 3)              # → 0.022
```

- Quiz : Avec seulement des écritures d'items de 1 Ko, à partir de combien par mois DynamoDB dépasse-t-il ces 15,80 $ ?
- [ ] Environ 2 millions
- [x] Environ 21 millions
- [ ] Environ 210 millions
- [ ] Environ 21 000
- Réponse : environ 21 millions : 15,80 / 0,7423 $ par million ≈ 21,3 millions d'écritures, soit 8 par seconde en continu.

## 44. chaîne vide : oui, sauf dans une clé
- Id : dynamodb-chaine-vide
- Sous-thème : modèle
- Type : piège
- Niveau : 2
- Profils : web, data
- Source : data-platform · pwa-sync
- Définition : Une chaîne ou un binaire vide est permis dans un attribut ordinaire, refusé dans un attribut de clé de table ou d'index.
- Contexte : Les valeurs de clé font au moins 1 octet (doc). `pk = ""` lève `ValidationException` : « An AttributeValue may not contain an empty string. Key: pk » (mesuré avec moto). Hors clé, `""` est stocké tel quel et relu `""`, distinct d'un attribut absent et de `NULL`. Un attribut qui sert de clé à un index secondaire est soumis à la même règle.
- Usage : ✅ `commentaire = ""` saisi vide par l'utilisateur · ❌ `sk = ""` pour dire « pas de tri » : une valeur sentinelle (`META`), ou une clé simple.

```
# Exemple 1 : réponses de DynamoDB
{"pk": "u1", "sk": "V#mac",
 "note": ""}            → OK
{"pk": "", "sk": "V#mac"}
→ ValidationException :
  An AttributeValue may not
  contain an empty string. Key: pk
```

```python
# Exemple 2 : mesuré avec moto
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
t.put_item(Item={"pk": "u1", "sk": "V",
  "note": ""})  # accepté
t.put_item(Item={"pk": "u1", "sk": ""})  # ❌ ClientError
m.stop()
```

- Quiz : `t.put_item(Item={"pk": "u1", "sk": "L", "tags": ["", "x"]})`. Résultat ?
- [x] Accepté, relu `['', 'x']`
- [ ] Refusé : chaîne vide
- [ ] Accepté, `""` retiré de la liste
- [ ] Accepté, `""` converti en `NULL`
- Réponse : accepté, relu `['', 'x']` (doc et mesuré avec moto) : les chaînes vides sont permises dans les listes, maps et ensembles.

## 45. une ligne par fait : pas d'écrasement
- Id : dynamodb-une-ligne-par-fait
- Sous-thème : modèle
- Type : choisir
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-putitem-remplace
- Voir aussi : dynamodb-sk-prefixee
- Source : data-platform · pwa-sync
- Définition : Stocker chaque fait dans sa ligne (`R#<date>#<carte>`, `V#<appareil>#<thème>`) évite que deux appareils qui écrivent en même temps s'écrasent.
- Contexte : Un document unique par utilisateur (JSON dans S3 ou une seule ligne) impose lire, fusionner, réécrire avec un contrôle de version et des réessais. Avec une ligne par fait et l'appareil dans la `sk` des compteurs, l'iPhone et le Mac n'écrivent jamais la même clé : pas de conflit à gérer, les écritures sont idempotentes. La fusion se fait à la lecture.
- Usage : ✅ données qui s'accumulent depuis plusieurs sources (appareils, événements) · ❌ un document unique modifié par plusieurs écrivains sans `ConditionExpression`.

```python
# Exemple 1 : deux appareils, deux lignes
lignes = {}
lignes["T#ios#IAM"] = 120    # iPhone
lignes["T#mac#IAM"] = 300    # Mac, même instant
sum(lignes.values())  # → 420  (fusion à la lecture)
```

- Quiz : Temps stocké sous `T#IAM` (sans appareil) : l'iPhone écrit 120, le Mac 300 en même temps. Résultat ?
- [ ] 420 : DynamoDB additionne
- [x] 120 ou 300 : le dernier `PutItem` gagne
- [ ] Conflit : la seconde écriture échoue
- [ ] Deux versions de la ligne
- Réponse : le dernier gagne : même clé, `PutItem` remplace ; mettre l'appareil dans la `sk` sépare les écritures.

## 46. Decimal : json.dumps échoue
- Id : dynamodb-decimal-json-dumps
- Sous-thème : modèle
- Type : piège
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-decimal-lecture
- Voir aussi : dynamodb-decimal-depuis-float
- Source : data-platform · pwa-sync
- Définition : boto3 rend chaque nombre en `Decimal` ; `json.dumps` le refuse, il faut un convertisseur avant de renvoyer l'item en JSON.
- Contexte : Piège typique d'une Lambda derrière API Gateway : `get_item` puis `json.dumps(item)` lève `TypeError: Object of type Decimal is not JSON serializable` (mesuré). Le paramètre `default=` de `json.dumps` reçoit chaque objet inconnu et rend sa version sérialisable. En TS, `unmarshall` rend directement des `number`, d'où la surprise côté Python.
- Usage : ✅ un `default=` explicite au moment de sérialiser la réponse HTTP · ❌ convertir en `float` avant d'écrire en base : boto3 refuse les `float`.

```python
# Exemple 1 : l'item lu, puis JSON
import json
from decimal import Decimal
item = {"siren": "483609327",
        "vues": Decimal("12")}
json.dumps(item)  # ❌ TypeError
```

```python
# Exemple 2 : convertisseur explicite
import json
from decimal import Decimal
def num(d):
    if d == d.to_integral_value():
        return int(d)
    return float(d)
json.dumps({"vues": Decimal("12"),
  "note": Decimal("2.5")}, default=num)
# → '{"vues": 12, "note": 2.5}'
```

- Quiz : Que rend `json.dumps({"vues": Decimal("12")}, default=str)` ?
- [ ] `'{"vues": 12}'`
- [x] `'{"vues": "12"}'`
- [ ] `TypeError`
- [ ] `'{"vues": 12.0}'`
- Réponse : `'{"vues": "12"}'` (mesuré) : `str` transforme le nombre en chaîne JSON ; le front recevra `"12"`, pas `12`.

## 47. ensembles : uniques, jamais vides
- Id : dynamodb-ensembles
- Sous-thème : modèle
- Type : concept
- Niveau : 2
- Profils : data, web
- Source : data-platform · pwa-sync
- Définition : Un ensemble (`SS`, `NS`, `BS`) contient des valeurs uniques d'un seul type, sans ordre garanti, et ne peut pas être vide.
- Contexte : Un `set` Python devient ensemble, les doublons disparaissent, l'ordre n'est pas conservé (doc). Piège : écrire `set()` est refusé par DynamoDB (« may not be empty », mesuré avec moto) alors que `TypeSerializer` le laisse passer en `{'NS': []}`. Pour vider un ensemble : `REMOVE` de l'attribut. `ADD` et `DELETE` d'une `UpdateExpression` modifient un ensemble sans le relire.
- Usage : ✅ thèmes vus, SIREN liés, tags sans doublon · ❌ historique ordonné ou avec répétitions : liste `L`.

```python
# Exemple 1 : set Python → SS
from boto3.dynamodb.types import TypeSerializer
s = TypeSerializer().serialize
s({"IAM", "IAM"})  # → {'SS': ['IAM']}
s(set())           # → {'NS': []}
# accepté par boto3, refusé ensuite
```

```python
# Exemple 2 : ensemble vide (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
t.put_item(Item={"pk": "u1", "sk": "V",
  "themes": set()})  # ❌ ClientError
m.stop()
```

- Quiz : Que fait `s({1, "IAM"})` ?
- [ ] `{'SS': ['1', 'IAM']}`
- [ ] `{'L': [{'N': '1'}, {'S': 'IAM'}]}`
- [ ] `{'NS': ['1']}`
- [x] `TypeError`
- Réponse : `TypeError` (mesuré : « Unsupported type ») : un ensemble n'a qu'un seul type ; pour mêler nombre et chaîne, une liste.

## 48. Decimal : ce que rend la lecture
- Id : dynamodb-decimal-lecture
- Sous-thème : modèle
- Type : piège
- Niveau : 2
- Profils : data
- Source : data-platform · pwa-sync
- Définition : `TypeDeserializer` (et `boto3.resource`) rend tout `N` en `Decimal`, même un entier : `{"N": "5"}` devient `Decimal('5')`.
- Contexte : Le nombre voyage en chaîne et `Decimal` garde sa valeur décimale exacte, sans l'arrondi binaire des `float`. Un `Decimal` se compare bien à un `int`, et les ensembles `NS` reviennent en `set` de `Decimal`. Les tests qui comparent un item lu à un dict littéral doivent donc écrire `Decimal("…")` ou des entiers, jamais des `float`.
- Usage : ✅ calculer en `Decimal` côté Python (montants, notes) · ❌ comparer un nombre lu à un littéral `float` dans un test ou un `if`.

```python
# Exemple 1 : ce que rend boto3
from decimal import Decimal
from boto3.dynamodb.types import TypeDeserializer
d = TypeDeserializer().deserialize
d({"N": "5"})        # → Decimal('5')
d({"N": "5"}) == 5   # → True
d({"NS": ["1", "2"]})
# → {Decimal('1'), Decimal('2')}
```

- Quiz : Que vaut `d({"N": "0.1"}) == 0.1` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- [ ] `True`, après arrondi à 38 chiffres
- Réponse : `False` (mesuré) : le `float` 0.1 vaut en réalité 0.1000000000000000055…, que `Decimal("0.1")` ne vaut pas ; comparer à `Decimal("0.1")`.

## 49. N : 38 chiffres, pas d'identifiant
- Id : dynamodb-nombre-38-chiffres
- Sous-thème : modèle
- Type : piège
- Niveau : 2
- Profils : data
- Source : data-platform · pwa-sync
- Définition : Un nombre `N` a au plus 38 chiffres de précision ; au-delà, DynamoDB lève une exception (doc) et boto3 refuse déjà côté client.
- Contexte : Plage selon la doc : de `1E-130` à `9.99…E+125`, en positif comme en négatif. boto3 sérialise avec un contexte décimal à 38 chiffres qui lève `Inexact` au lieu d'arrondir en silence (mesuré). Pour une précision supérieure, la doc conseille une chaîne. Un identifiant (SIREN, numéro d'annonce) se stocke en `S`, même s'il n'a que des chiffres.
- Usage : ✅ compteurs, montants, horodatages epoch (TTL) · ❌ identifiants faits de chiffres : `S`.

```python
# Exemple 1 : 38 passe, 39 casse
from decimal import Decimal
from boto3.dynamodb.types import TypeSerializer
s = TypeSerializer().serialize
n38 = Decimal("9" * 38)
s(n38)["N"] == "9" * 38  # → True
s(Decimal("9" * 39))  # ❌ Inexact
```

- Quiz : Un code postal `"01000"` stocké en `N` via `Decimal("01000")`. Que relit-on ?
- [ ] `Decimal('01000')`
- [x] `Decimal('1000')`
- [ ] `Inexact`
- [ ] `'01000'`
- Réponse : `Decimal('1000')` (mesuré : sérialisé `{'N': '1000'}`) : les zéros de tête sont supprimés, la doc le dit ; un code se stocke en `S`.

## 50. M et L : chemin de document
- Id : dynamodb-chemin-document
- Sous-thème : modèle
- Type : concept
- Niveau : 2
- Profils : web
- Source : data-platform · pwa-sync
- Définition : Une `M` ou une `L` en contient d'autres (32 niveaux selon la doc) ; `SET stats.IAM = :v` modifie un élément sans réécrire l'item.
- Contexte : Le chemin de document (`stats.IAM`, `tags[0]`) cible un élément imbriqué : on met à jour un compteur sans relire la map, comme un `obj.stats.IAM = 4` en TS. Pas de limite de nombre d'éléments, seulement les 400 Ko de l'item. La limite de 32 niveaux vient de la doc ; moto ne l'applique pas (40 niveaux acceptés, mesuré).
- Usage : ✅ petite map de compteurs par thème dans un item · ❌ map qui grossit sans fin (une entrée par jour) : un item par fait.

```python
# Exemple 1 : SET sur un chemin (moto)
import boto3; from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "V#mac"}
t.put_item(Item={**k, "stats": {}})
r = t.update_item(Key=k,
  UpdateExpression="SET stats.IAM = :v",
  ExpressionAttributeValues={":v": 3},
  ReturnValues="ALL_NEW")["Attributes"]
r["stats"]["IAM"] == 3  # → True
m.stop()
```

- Quiz : Item `{"stats": {"IAM": 3}}`, puis `SET stats.S3.vues = :v`. Résultat ?
- [ ] `stats.S3` créé, avec `vues`
- [x] `ValidationException` : `stats.S3` absent
- [ ] Attribut racine nommé `stats.S3.vues`
- [ ] `stats` remplacé par `{"S3": …}`
- Réponse : `ValidationException` (mesuré avec moto : « document path … invalid for update ») : chaque parent du chemin doit exister ; créer `stats.S3` d'abord.

## 51. taille des clés : 2048 et 1024 octets
- Id : dynamodb-taille-des-cles
- Sous-thème : clés
- Type : concept
- Niveau : 2
- Profils : expert
- Source : data-platform · pwa-sync
- Définition : Une valeur de `pk` fait de 1 à 2048 octets, une valeur de `sk` de 1 à 1024 octets, comptés en UTF-8.
- Contexte : Limites de la doc (« Partition keys and sort keys »). Une `sk` composée (`R#<date>#<thème>/<n>`) grandit avec chaque segment : un texte libre dedans peut dépasser. Au-delà, `ValidationException` (« Aggregated size of all range keys has exceeded the size limit of 1024 bytes », mesuré avec moto). Les clés comptent aussi dans les 400 Ko de l'item et sont recopiées dans chaque index secondaire.
- Usage : ✅ identifiants courts et bornés dans les clés (SIREN, date ISO, id) · ❌ un texte libre (titre d'annonce) dans la `sk` : le mettre en attribut.

```python
# Exemple 1 : mesurer avant d'écrire
sk = "R#2026-10-23#IAM/3"
len(sk.encode())             # → 18
titre = "é" * 600
len(titre.encode())          # → 1200
len(titre.encode()) <= 1024  # → False
```

- Quiz : Clé composite, `pk` de 2 000 octets et `sk` de 1 000 octets (3 000 au total). `PutItem` ?
- [ ] Refusé : 3 000 > 2 048
- [ ] Refusé : 3 000 > 1 024
- [x] Accepté : limites séparées
- [ ] Accepté, `sk` tronquée
- Réponse : accepté (doc, et mesuré avec moto) : 2 048 octets valent pour la `pk` seule, 1 024 pour la `sk` seule ; aucun plafond sur leur somme.

## 52. sk préfixée : plusieurs types par partition
- Id : dynamodb-sk-prefixee
- Sous-thème : clés
- Type : recette
- Niveau : 2
- Profils : web, data
- Source : data-platform · pwa-sync
- Définition : Une `sk` préfixée (`R#…`, `V#…`, `T#…`) range plusieurs types de lignes dans la même partition et permet de lire un seul type avec `begins_with`.
- Contexte : C'est le modèle « une table » : réponses, vues et temps d'un utilisateur vivent ensemble sous son `pk`, distingués par le préfixe. `begins_with(sk, :p)` lit un type, `BETWEEN` une plage de dates (`R#2026-10-01` à `R#2026-10-31`). Le `#` n'a rien de spécial pour DynamoDB : c'est une convention lisible, triée comme n'importe quel caractère.
- Usage : ✅ plusieurs faits liés au même `pk`, lus par type ou par période · ❌ un type par table : plus de tables, plus de droits IAM, plus de requêtes.

```python
# Exemple 1 : begins_with, en Python
sks = ["R#2026-10-01#IAM/3",
       "R#2026-10-20#S3/1",
       "V#mac#IAM", "T#mac#IAM"]
[s for s in sks if s.startswith("R#")]
# → ['R#2026-10-01#IAM/3', 'R#2026-10-20#S3/1']
```

```bash
# Exemple 2 : les réponses depuis le 1er
aws dynamodb query --table-name "$table" \
  --key-condition-expression \
  "pk = :pk AND sk BETWEEN :a AND :b" \
  --expression-attribute-values \
  '{":pk":{"S":"eu-west-3:1b2c…"},
    ":a":{"S":"R#2026-10-01"},
    ":b":{"S":"R#2026-10-32"}}'
```

- Quiz : `begins_with(sk, "R#2026-10")` ou `sk BETWEEN "R#2026-10-01" AND "R#2026-10-31"` pour tout octobre ?
- [ ] `BETWEEN` : seul opérateur sur la clé de tri
- [x] `begins_with` : `BETWEEN` rate `R#2026-10-31#IAM/3`
- [ ] Équivalents : même résultat
- [ ] `BETWEEN` : `begins_with` est interdit avec `Query`
- Réponse : `begins_with` : `R#2026-10-31#IAM/3` est après `R#2026-10-31` dans l'ordre des chaînes, donc hors de la plage ; d'où `R#2026-10-32` en borne haute.

## 53. attribut type : nommer l'entité
- Id : dynamodb-attribut-type
- Sous-thème : clés
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-sk-prefixee
- Source : data-platform · pwa-sync
- Définition : Dans une table aux clés surchargées, chaque item porte un attribut `type` (`entreprise`, `annonce`) qui dit quelle entité il représente.
- Contexte : Le préfixe de `sk` suffit à un `begins_with`, mais le code lecteur, un export ou un index ont besoin d'un attribut explicite : une `Query` sur `SIREN#…` ramène la fiche et les annonces mêlées, et `type` dit vers quelle classe désérialiser chacune. Il sert aussi à filtrer un export. Le reste de l'item suit le schéma de son type, contrôlé par le code, pas par la table.
- Usage : ✅ un `type` écrit à chaque `PutItem`, lu pour router · ❌ déduire l'entité en découpant la `sk` partout dans le code.

```python
# Exemple 1 : router par type
items = [
  {"sk": "META", "type": "entreprise"},
  {"sk": "ANNONCE#2026-10-23",
   "type": "annonce"}]
[i["type"] for i in items]
# → ['entreprise', 'annonce']
```

- Quiz : `FilterExpression="type = :t"` dans une `Query` écrite à la main. Résultat ?
- [ ] Filtre appliqué normalement
- [x] `ValidationException` : `type` est réservé
- [ ] Filtre sur le type DynamoDB (`S`, `N`)
- [ ] Ignoré : `type` est un attribut système
- Réponse : `ValidationException` (mesuré avec moto) : `type` est un mot réservé ; écrire `#t = :t` avec `ExpressionAttributeNames={"#t": "type"}`.

## 54. partition : 3 000 lectures, 1 000 écritures
- Id : dynamodb-debit-par-partition
- Sous-thème : clés
- Type : concept
- Niveau : 2
- Profils : data, ops
- Source : data-platform · pwa-sync
- Définition : Chaque partition sert au plus 3 000 unités de lecture et 1 000 unités d'écriture par seconde, quel que soit le mode de capacité.
- Contexte : Selon la doc, une unité d'écriture = 1 écriture/s d'un item ≤ 1 Ko ; une unité de lecture = 1 lecture fortement cohérente/s (ou 2 éventuellement cohérentes) d'un item ≤ 4 Ko. Les items d'une même `pk` sont rangés ensemble : une `pk` très sollicitée devient une partition chaude, freinée (throttling) même si la table est à la demande et calme ailleurs.
- Usage : ✅ estimer le débit par valeur de `pk` au pic, pas seulement par table · ❌ charger une journée entière sous une seule `pk` en quelques secondes.

```python
# Exemple 1 : une journée en 10 s
import math
annonces, secondes = 32_000, 10
wcu = math.ceil(900 / 1024)  # 900 o
annonces * wcu / secondes  # → 3200.0
# pk = "2026-10-23" : 3 200 > 1 000
```

- Quiz : Items de 20 Ko, lectures fortement cohérentes sur un seul item. Combien par seconde au plus ?
- [ ] 3 000
- [ ] 1 000
- [x] 600
- [ ] 150
- Réponse : 600 (exemple de la doc) : 20 Ko = 5 unités de lecture par lecture forte ; 3 000 ÷ 5 = 600.

## 55. adaptive capacity : la partition chaude
- Id : dynamodb-adaptive-capacity
- Sous-thème : clés
- Type : concept
- Niveau : 2
- Profils : ops, expert
- Prérequis : dynamodb-debit-par-partition
- Source : data-platform · pwa-sync
- Définition : L'adaptive capacity augmente automatiquement, sans frais, le débit d'une partition chaude et peut isoler un item très sollicité sur sa propre partition.
- Contexte : Active sur toute table, rien à configurer (doc). Elle redonne aux partitions chargées la capacité inutilisée ailleurs, et déplace les items chauds pour qu'ils ne partagent plus une partition. Limites : ni plus que la capacité de la table, ni plus que le maximum d'une partition (1 000 écritures/s pour un item isolé). Pas de découpage d'une collection si la table a un index local (LSI).
- Usage : ✅ compter dessus pour un déséquilibre modéré entre `pk` · ❌ compter dessus pour un compteur global écrit 1 500 fois par seconde : sharder.

```python
# Exemple 1 : ce qu'elle ne dépasse pas
MAX_WCU_PARTITION = 1_000
def tient(wcu_item):
    return wcu_item <= MAX_WCU_PARTITION
tient(800)   # → True  (item isolé)
tient(1500)  # → False (même isolé)
```

- Quiz : Table provisionnée à 400 WCU, 4 partitions de 100. L'une reçoit 150 WCU/s, les autres 50. Throttling durable ?
- [ ] Oui : 150 > 100 par partition
- [ ] Oui, sauf en mode à la demande
- [ ] Seulement après 300 s de burst
- [x] Non : la capacité inutilisée est redonnée
- Réponse : non (exemple de la doc) : 150 + 3 × 50 = 300 < 400 WCU de la table ; l'adaptive capacity monte la partition chaude à 150.

## 56. write sharding : suffixe aléatoire
- Id : dynamodb-write-sharding
- Sous-thème : clés
- Type : recette
- Niveau : 2
- Profils : data, expert
- Prérequis : dynamodb-debit-par-partition
- Source : data-platform · pwa-sync
- Définition : Le write sharding ajoute un suffixe (`2026-10-23.1` à `.N`) à une `pk` chaude pour répartir ses écritures sur plusieurs valeurs, donc plusieurs partitions.
- Contexte : Exemple de la doc : `pk` = date, suffixe aléatoire de 1 à 200 ; les écritures du jour se répartissent, le débit total monte. Prix côté lecture : relire la journée demande une `Query` par suffixe, puis une fusion dans l'application. N se choisit d'après le pic : 3 200 écritures/s pour 1 000 par partition, au moins 4 suffixes, avec marge.
- Usage : ✅ flux d'écritures massif sur une clé naturelle chaude (date, compteur global) · ❌ table peu sollicitée : N lectures pour rien.

```python
# Exemple 1 : N suffixes
import random
N = 8
def pk(date):
    return f"{date}.{random.randint(1, N)}"
pk("2026-10-23")[:11]  # → '2026-10-23.'
lire = [f"2026-10-23.{i}"
        for i in range(1, N + 1)]
len(lire)  # → 8  (8 Query à fusionner)
```

- Quiz : Avec ce suffixe aléatoire, comment relire l'annonce `A123` du 23 octobre ?
- [ ] `GetItem` sur `pk = 2026-10-23`
- [x] Jusqu'à N lectures : suffixe inconnu
- [ ] `GetItem` sur `pk = 2026-10-23.*`
- [ ] `Query` avec `begins_with(pk, …)`
- Réponse : jusqu'à N lectures : le suffixe tiré au hasard n'est noté nulle part ; `pk` n'accepte que l'égalité, sans joker ni `begins_with`.

## 57. compteur chaud : 1 000 écritures/s par partition
- Id : dynamodb-compteur-eclate
- Sous-thème : clés
- Type : recette
- Niveau : 2
- Profils : web, expert
- Prérequis : dynamodb-debit-par-partition, dynamodb-add-compteur
- Source : data-platform · pwa-sync
- Définition : Un compteur de vues très sollicité (`ADD vues :1`) sur une seule clé est plafonné par sa partition : 1 000 unités d'écriture par seconde.
- Contexte : Selon la doc, chaque partition sert au plus 3 000 unités de lecture et 1 000 unités d'écriture par seconde, à la demande comme en provisionné. Un compteur unique (`VUES#483609327`) devient une clé chaude, limitée au-delà. Solution : l'éclater en N items de `pk` différentes (`…#0` à `…#N-1`), écrire sur l'un au hasard, sommer les N à la lecture. Garder ces items petits.
- Usage : ✅ compteur éclaté pour un pic connu, DynamoDB reste le bon choix · ❌ une seule ligne compteur pour un trafic de plusieurs milliers d'incréments par seconde.

```python
# Exemple 1 : combien d'éclats ?
import math
pic = 4_500              # incréments/s
math.ceil(pic / 1_000)   # → 5
# pk = f"VUES#483609327#{n}", n de 0 à 4
```

```python
# Exemple 2 : écrire au hasard, lire tout
import random
n = random.randrange(5)
pk = f"VUES#483609327#{n}"
pk[:15]            # → "VUES#483609327#"
eclats = [120, 98, 131, 110, 101]
sum(eclats)        # → 560 (5 éclats lus)
```

- Quiz : Compteur éclaté en 5 items (`VUES#483609327#0` à `#4`). Comment lire le total en un appel ?
- [ ] `GetItem` sur `VUES#483609327`
- [ ] `Query` avec `begins_with(pk, "VUES#483609327#")`
- [x] `BatchGetItem` des 5 clés, puis la somme
- [ ] `Scan` avec un filtre sur le préfixe
- Réponse : `BatchGetItem` des 5 clés : chaque éclat a sa propre `pk`, et une condition de clé n'accepte que l'égalité sur `pk` ; la somme se fait dans le code.

## 58. surcharge des clés : SIREN#, ANNONCE#
- Id : dynamodb-surcharge-des-cles
- Sous-thème : clés
- Type : concept
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-sk-prefixee
- Source : data-platform · pwa-sync
- Définition : Surcharger les clés, c'est ranger plusieurs entités dans des attributs génériques `pk`/`sk` dont la valeur commence par le type : `SIREN#…`, `ANNONCE#…`.
- Contexte : Les noms `pk`/`sk` ne disent rien de l'entité, la valeur le dit. Une partition `SIREN#483609327` regroupe la fiche (`sk = META`) et ses annonces (`sk = ANNONCE#<date>#<id>`) : une seule `Query` ramène l'entreprise et son historique. Le préfixe évite aussi la collision entre deux entités qui auraient le même identifiant brut.
- Usage : ✅ entités lues ensemble (entreprise et annonces) dans une table unique · ❌ nommer la clé `siren` : la table ne peut plus accueillir d'autres entités sans contresens.

```python
# Exemple 1 : une partition, 2 entités
part = {"META": {"nom": "ACME"},
  "ANNONCE#2026-10-01#A1": {},
  "ANNONCE#2026-10-23#A7": {}}
sorted(part)[0]
# → 'ANNONCE#2026-10-01#A1'
sorted(part)[-1]  # → 'META'
```

- Quiz : Quelle `sk` pour que la fiche sorte en tête de la `Query` (ordre croissant) ?
- [ ] `META`
- [ ] `meta`
- [x] `#META`
- [ ] `ZMETA`
- Réponse : `#META` : les chaînes se comparent octet par octet, et `#` (0x23) précède `A` (0x41) ; `meta` (0x6D) passe même après `META`.

## 59. sk en chaîne : tri caractère par caractère
- Id : dynamodb-tri-chaine-sk
- Sous-thème : clés
- Type : piège
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-sk-prefixee
- Source : data-platform · pwa-sync
- Définition : Une `sk` de type `S` se trie comme une chaîne, octet par octet : dates ISO bien triées, nombres sans zéros devant mal triés.
- Contexte : `"T#10"` passe avant `"T#2"` : le caractère `1` est avant `2`. Les dates `AAAA-MM-JJ` sont sûres parce que leur longueur est fixe et que l'année vient d'abord. Pour un numéro, on complète de zéros (`0002`, `0010`). `ScanIndexForward=False` renvoie la partition en ordre décroissant (les plus récents d'abord).
- Usage : ✅ dates ISO et numéros complétés de zéros dans la `sk` · ❌ `R#25/10/2026` ou `#2`, `#10` : ordre faux, plages `BETWEEN` fausses.

```python
# Exemple 1 : l'ordre des chaînes
sorted(["T#9", "T#10", "T#2"])
# → ['T#10', 'T#2', 'T#9']
sorted(["T#0009", "T#0010", "T#0002"])
# → ['T#0002', 'T#0009', 'T#0010']
"R#2026-09-30" < "R#2026-10-01"  # → True
```

- Quiz : `sk` = `R#25/10/2026` et `R#01/11/2026`. Que renvoie `sk > "R#25/10/2026"` ?
- [ ] `R#01/11/2026`, qui est après
- [x] Rien : `R#01…` est avant `R#25…` en chaîne
- [ ] Les deux lignes
- [ ] `ValidationException` : format de date
- Réponse : rien : `0` est avant `2`, donc `R#01/11/2026` est « avant » ; DynamoDB compare des chaînes, pas des dates.

## 60. hash_key et range_key : remplacement de la table
- Id : dynamodb-terraform-cle-remplacement
- Sous-thème : clés
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : dynamodb-cles-immuables
- Voir aussi : dynamodb-protection-suppression
- Source : data-platform · pwa-sync
- Définition : Dans `aws_dynamodb_table`, `hash_key` et `range_key` sont « Forces new resource » : les changer détruit la table et en crée une neuve, vide.
- Contexte : DynamoDB ne sait pas changer la clé primaire d'une table : le provider ne peut que remplacer. Avec `deletion_protection_enabled`, l'apply échoue à la destruction ; sans, les données disparaissent. Pour changer de clé : nouvelle table (autre nom), copie (export S3 puis import, ou script), bascule, puis suppression de l'ancienne. Ajouter un GSI, lui, se fait en place.
- Usage : ✅ lire chaque `forces replacement` du plan avant un apply · ❌ « renommer » `sk` en `date` dans le `.tf` d'une table en service.

```bash
# Exemple 1 : forme du plan (doc provider)
# aws_dynamodb_table.annonces must be replaced
-/+ resource "aws_dynamodb_table" "annonces" {
  ~ range_key = "sk" -> "date" # forces replacement
}
# Plan: 1 to add, 0 to change, 1 to destroy.
```

- Quiz : On ajoute plutôt un `global_secondary_index` de clé de tri `date`. Que montre le plan ?
- [ ] `-/+` : remplacement de la table
- [x] `~` : mise à jour en place
- [ ] Une erreur : une table n'a qu'une clé de tri
- [ ] `+` : une seconde table créée
- Réponse : `~` en place : un GSI se crée par `UpdateTable` sur la table existante, sans toucher aux données ; seuls `hash_key`, `range_key` et les LSI forcent un remplacement.

## 61. index creux : seuls les items qui ont l'attribut
- Id : dynamodb-index-creux
- Sous-thème : index
- Type : recette
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-gsi-autre-cle
- Source : data-platform · pwa-sync
- Définition : Un item sans l'attribut de clé d'un index n'y figure pas : l'index ne contient que les items qui portent cet attribut (index creux, *sparse*).
- Contexte : On s'en sert comme d'une liste filtrée gratuite : `en_cours` n'est posé que sur les procédures ouvertes, et le GSI `ouvertes` (clé `en_cours`) ne contient qu'elles. Le lire coûte la taille de la liste, pas de la table, contrairement à un `FilterExpression`. Un item sans l'attribut ne consomme aucune écriture d'index.
- Usage : ✅ marqueur posé seulement sur une minorité d'items (ouvert, à traiter, en erreur) · ❌ attribut présent partout avec `"0"` ou `"1"` : l'index recopie toute la table.

```python
# Exemple 1 : 2 procédures, 1 dans l'index (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
S = lambda *n: [{"AttributeName": a, "AttributeType": "S"} for a in n]
H = lambda a, k="HASH": {"AttributeName": a, "KeyType": k}
t = boto3.resource("dynamodb", region_name="eu-west-3").create_table(
  TableName="procedures", BillingMode="PAY_PER_REQUEST",
  KeySchema=[H("pk"), H("sk", "RANGE")],
  AttributeDefinitions=S("pk", "sk", "en_cours"),
  GlobalSecondaryIndexes=[{"IndexName": "ouvertes",
    "KeySchema": [H("en_cours")], "Projection": {"ProjectionType": "ALL"}}])
t.put_item(Item={"pk": "483609327", "sk": "P#1", "en_cours": "1"})
t.put_item(Item={"pk": "552100554", "sk": "P#1"})  # clôturée
t.scan()["Count"]                       # → 2
t.scan(IndexName="ouvertes")["Count"]   # → 1
m.stop()
```

- Quiz : La procédure 483609327 est clôturée. Comment la sortir de l'index `ouvertes` ?
- [ ] `SET en_cours = :zero` (valeur `"0"`)
- [ ] Un `DeleteItem` sur l'index `ouvertes`
- [x] `REMOVE en_cours` sur l'item de la table
- [ ] Rien : l'index se met à jour à la date de clôture
- Réponse : `REMOVE en_cours` : sans l'attribut, l'item quitte l'index ; avec `"0"`, il y reste (sous une autre clé), et on n'écrit jamais dans un index.

## 62. quotas : 20 GSI, 5 LSI, 100 attributs projetés
- Id : dynamodb-quotas-index
- Sous-thème : index
- Type : concept
- Niveau : 2
- Profils : ops, expert
- Prérequis : dynamodb-gsi-autre-cle
- Source : data-platform · pwa-sync
- Définition : Par table : 20 GSI (quota par défaut, ajustable), 5 LSI au plus, et 100 attributs `INCLUDE` cumulés sur tous les index.
- Contexte : Chiffres de la page Quotas de la doc DynamoDB. Le plafond de 100 ne compte que les `NonKeyAttributes` des projections `INCLUDE` ; `KEYS_ONLY` et `ALL` n'en consomment pas. Un index par accès finit par buter sur ces limites, d'où la surcharge d'index (un GSI générique pour plusieurs accès) dans le modèle « une table ».
- Usage : ✅ compter les index et les attributs projetés dès la conception · ❌ un GSI `INCLUDE` par écran, chacun avec sa liste de 20 attributs.

```python
# Exemple 1 : compter les attributs INCLUDE
include = {
  "par-tribunal": ["nom", "type"],
  "par-date": ["nom", "tribunal", "type"],
}
sum(len(a) for a in include.values())  # → 5
# plafond : 100 pour toute la table
```

- Quiz : `nom` est projeté (`INCLUDE`) dans 3 index différents. Combien compte-t-il pour le plafond de 100 ?
- [ ] 1 : c'est le même attribut
- [x] 3 : un par index
- [ ] 0 : un attribut commun est gratuit
- [ ] 1, plus 1 par LSI seulement
- Réponse : 3 : selon la doc, projeter le même nom dans deux index compte deux attributs distincts.

## 63. GSI : lecture toujours éventuelle
- Id : dynamodb-gsi-lecture-eventuelle
- Sous-thème : index
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-gsi-autre-cle, dynamodb-lecture-forte
- Voir aussi : dynamodb-lsi-lecture-forte
- Source : data-platform · pwa-sync
- Définition : Un GSI est mis à jour de façon asynchrone : sa lecture est toujours éventuellement cohérente, et `ConsistentRead=True` y est refusé.
- Contexte : L'écriture dans la table répond avant que le GSI soit à jour ; la propagation prend en général une fraction de seconde (selon la doc), plus en cas de panne. Une `Query` sur l'index juste après un `PutItem` peut donc ne pas voir l'item. Sur la table et sur un LSI, `ConsistentRead=True` donne une lecture forte, au double du coût en RCU.
- Usage : ✅ GSI pour des listes où un léger retard est acceptable · ❌ relire son écriture par le GSI : `GetItem` sur la table, avec `ConsistentRead=True`.

```python
# Exemple 1 : ConsistentRead sur un GSI (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
S = lambda *n: [{"AttributeName": a, "AttributeType": "S"} for a in n]
H = lambda a, k="HASH": {"AttributeName": a, "KeyType": k}
t = boto3.resource("dynamodb", region_name="eu-west-3").create_table(
  TableName="annonces", BillingMode="PAY_PER_REQUEST",
  KeySchema=[H("pk"), H("sk", "RANGE")],
  AttributeDefinitions=S("pk", "sk", "tribunal"),
  GlobalSecondaryIndexes=[{"IndexName": "par-tribunal",
    "KeySchema": [H("tribunal")], "Projection": {"ProjectionType": "ALL"}}])
t.query(IndexName="par-tribunal", ConsistentRead=True,
  KeyConditionExpression=Key("tribunal").eq("Paris"))  # ❌ ClientError
m.stop()
```

- Quiz : L'ingestion écrit une annonce, puis la `Query` sur `par-tribunal` lancée aussitôt ne la renvoie pas. Pourquoi ?
- [ ] Le `PutItem` a échoué sans lever d'erreur
- [x] Le GSI n'a pas encore reçu la copie
- [ ] Il fallait `ConsistentRead=True` sur la `Query`
- [ ] Le GSI n'est rempli qu'une fois par heure
- Réponse : la copie n'est pas encore arrivée : le GSI est alimenté de façon asynchrone ; `ConsistentRead=True` y lève une `ValidationException` (mesuré avec moto, conforme à la doc).

## 64. LSI : même partition, autre tri, lecture forte
- Id : dynamodb-lsi-lecture-forte
- Sous-thème : index
- Type : concept
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-lsi-ou-gsi-creation
- Source : data-platform · pwa-sync
- Définition : Un LSI garde la clé de partition de la table, remplace la clé de tri, et accepte `ConsistentRead=True`.
- Contexte : Il trie autrement les items d'une même partition : la table `procedures` (pk = SIREN, sk = `P#<num>`) avec un LSI `par-date` lit les procédures d'un SIREN par date. Comme il est stocké avec la partition, il est cohérent avec elle et autorise la lecture forte. La clé de tri de la table y est projetée comme attribut ordinaire.
- Usage : ✅ second ordre de tri dans une partition, avec lecture forte, prévu dès la création · ❌ autre clé de partition : c'est un GSI.

```python
# Exemple 1 : lecture forte sur un LSI (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
S = lambda *n: [{"AttributeName": a, "AttributeType": "S"} for a in n]
H = lambda a, k="HASH": {"AttributeName": a, "KeyType": k}
t = boto3.resource("dynamodb", region_name="eu-west-3").create_table(
  TableName="procedures", BillingMode="PAY_PER_REQUEST",
  KeySchema=[H("pk"), H("sk", "RANGE")],
  AttributeDefinitions=S("pk", "sk", "date"),
  LocalSecondaryIndexes=[{"IndexName": "par-date",
    "KeySchema": [H("pk"), H("date", "RANGE")],
    "Projection": {"ProjectionType": "ALL"}}])
t.put_item(Item={"pk": "483609327", "sk": "P#2", "date": "2026-10-01"})
t.put_item(Item={"pk": "483609327", "sk": "P#1", "date": "2026-10-20"})
r = t.query(IndexName="par-date", ConsistentRead=True,
  KeyConditionExpression=Key("pk").eq("483609327"))
[i["sk"] for i in r["Items"]]  # → ['P#2', 'P#1']
m.stop()
```

- Quiz : On déclare un LSI de clé `tribunal` (partition) et `date` (tri) sur cette table. Résultat selon la doc ?
- [ ] Accepté : un LSI choisit ses clés
- [ ] Accepté si `tribunal` est déclaré en attribut
- [x] Refusé : la partition d'un LSI est celle de la table
- [ ] Accepté, mais en lecture éventuelle seulement
- Réponse : refusé : un LSI partage la clé de partition de sa table (moto l'accepte pourtant, la doc fait foi) ; une autre partition demande un GSI.

## 65. GSI : clé d'index non unique
- Id : dynamodb-gsi-cle-non-unique
- Sous-thème : index
- Type : piège
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-gsi-autre-cle
- Voir aussi : dynamodb-unicite-item-garde
- Source : data-platform · pwa-sync
- Définition : Dans un GSI, plusieurs items peuvent avoir la même clé d'index : seule la clé primaire de la table est unique.
- Contexte : Une `Query` sur `tribunal = Paris AND date = 2026-10-01` renvoie toutes les annonces de ce jour, dans un ordre quelconque entre elles. Le GSI ne refuse jamais une écriture pour doublon : c'est une copie, pas une contrainte. Même chose pour la clé de tri d'un LSI. Pour l'unicité d'un autre attribut, il faut une ligne dédiée dont la clé primaire est cet attribut.
- Usage : ✅ GSI pour regrouper (par tribunal, par jour) · ❌ GSI pour garantir l'unicité d'un numéro d'annonce : il l'accepte en double.

```python
# Exemple 1 : deux items, même clé d'index (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
S = lambda *n: [{"AttributeName": a, "AttributeType": "S"} for a in n]
H = lambda a, k="HASH": {"AttributeName": a, "KeyType": k}
t = boto3.resource("dynamodb", region_name="eu-west-3").create_table(
  TableName="annonces", BillingMode="PAY_PER_REQUEST",
  KeySchema=[H("pk"), H("sk", "RANGE")],
  AttributeDefinitions=S("pk", "sk", "tribunal", "date"),
  GlobalSecondaryIndexes=[{"IndexName": "par-tribunal",
    "KeySchema": [H("tribunal"), H("date", "RANGE")],
    "Projection": {"ProjectionType": "KEYS_ONLY"}}])
for siren in ["483609327", "552100554"]:
    t.put_item(Item={"pk": siren, "sk": "A#1", "tribunal": "Paris", "date": "2026-10-01"})
k = Key("tribunal").eq("Paris") & Key("date").eq("2026-10-01")
t.query(IndexName="par-tribunal", KeyConditionExpression=k)["Count"]  # → 2
m.stop()
```

- Quiz : Comment refuser une 2e annonce avec le même `numero` (hors clé de la table) ?
- [ ] Un GSI de clé `numero` : il rejette le doublon
- [ ] `ConditionExpression` sur l'index `par-numero`
- [ ] Un `Scan` sur `numero` avant chaque écriture
- [x] Une ligne `pk = NUM#<numero>` écrite avec `attribute_not_exists(pk)`
- Réponse : la ligne dédiée : seule une clé primaire est unique ; on l'écrit avec `attribute_not_exists` dans la même transaction que l'annonce.

## 66. attribut non projeté : fetch sur LSI, rien sur GSI
- Id : dynamodb-attribut-non-projete
- Sous-thème : index
- Type : comparaison
- Niveau : 2
- Profils : web, expert
- Prérequis : dynamodb-projection-index
- Source : data-platform · pwa-sync
- Définition : Demander un attribut non projeté : un LSI va le chercher dans la table (lecture en plus), un GSI ne le peut pas.
- Contexte : Selon la doc, sur un LSI ce « fetch » est automatique mais facture la lecture de **l'item entier** de la table, arrondie à 4 Ko par item, en plus de l'index, et ajoute de la latence. Une requête GSI ne voit que sa projection : l'attribut manque à la réponse (mesuré avec moto). Il faut alors une 2e lecture sur la table, ou l'ajouter à la projection.
- Usage : ✅ projeter ce que la requête lit souvent ; accepter un fetch LSI rare · ❌ un GSI `KEYS_ONLY` pour un écran qui affiche `nom` : N `GetItem` en plus.

```python
# Exemple 1 : GSI KEYS_ONLY, on demande nom (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
S = lambda *n: [{"AttributeName": a, "AttributeType": "S"} for a in n]
H = lambda a, k="HASH": {"AttributeName": a, "KeyType": k}
t = boto3.resource("dynamodb", region_name="eu-west-3").create_table(
  TableName="annonces", BillingMode="PAY_PER_REQUEST",
  KeySchema=[H("pk"), H("sk", "RANGE")],
  AttributeDefinitions=S("pk", "sk", "tribunal"),
  GlobalSecondaryIndexes=[{"IndexName": "par-tribunal",
    "KeySchema": [H("tribunal")], "Projection": {"ProjectionType": "KEYS_ONLY"}}])
t.put_item(Item={"pk": "483609327", "sk": "A#1", "tribunal": "Paris", "nom": "ACME"})
r = t.query(IndexName="par-tribunal", ProjectionExpression="nom",
  KeyConditionExpression=Key("tribunal").eq("Paris"))
r["Items"]  # → [{}]   (nom n'est pas dans l'index)
m.stop()
```

- Quiz : Même requête sur un **LSI** `KEYS_ONLY` : 4 items de 300 octets, `ProjectionExpression="nom"`. Que se passe-t-il ?
- [ ] `nom` absent, comme sur un GSI
- [ ] `ValidationException` : attribut non projeté
- [x] `nom` renvoyé, 4 items lus en plus dans la table
- [ ] `nom` renvoyé sans coût supplémentaire
- Réponse : renvoyé, lu dans la table : selon la doc, le LSI va chercher chaque item complet (arrondi à 4 Ko), facturé en plus de la lecture d'index.

## 67. écriture : chaque GSI touché est facturé
- Id : dynamodb-cout-ecriture-index
- Sous-thème : index
- Type : concept
- Niveau : 2
- Profils : ops, data
- Prérequis : dynamodb-gsi-autre-cle
- Source : data-platform · pwa-sync
- Définition : Une écriture qui modifie un index est facturée à la table **et** à chaque index concerné ; changer une clé d'index coûte deux écritures d'index.
- Contexte : Règles de la doc : nouvel item avec l'attribut indexé = 1 écriture d'index ; clé d'index qui change (Paris → Lyon) = 2 (suppression de l'ancienne entrée, ajout de la nouvelle) ; attribut indexé supprimé = 1 ; attribut ni clé ni projeté modifié = 0. Chaque Ko d'entrée d'index au-delà du premier ajoute une unité. Trois GSI `ALL` peuvent quadrupler le coût d'écriture.
- Usage : ✅ projections étroites et index creux sur les tables très écrites · ❌ un GSI `ALL` par accès sur la table d'ingestion BODACC (~32 000 annonces par jour).

```python
# Exemple 1 : ingestion d'une annonce neuve
table = 1                   # l'item, ≤ 1 Ko
gsi = {"par-tribunal": 1,   # tribunal présent
       "par-date": 1,       # date présente
       "ouvertes": 0}       # en_cours absent
table + sum(gsi.values())   # → 3   (unités)
```

- Quiz : Un `UpdateItem` change `tribunal` de « Paris » à « Lyon ». Combien d'écritures sur `par-tribunal` ?
- [ ] 0 : seul l'item de la table change
- [ ] 1 : l'entrée est mise à jour en place
- [x] 2 : suppression de l'ancienne, ajout de la nouvelle
- [ ] 3 : lecture, suppression, ajout
- Réponse : 2 : selon la doc, quand une clé d'index change, DynamoDB supprime l'ancienne entrée et écrit la nouvelle.

## 68. local_secondary_index : à la création seulement
- Id : dynamodb-lsi-terraform-remplacement
- Sous-thème : index
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : dynamodb-lsi-ou-gsi-creation
- Source : data-platform · pwa-sync
- Définition : Le bloc `local_secondary_index` (nom, `range_key`, `projection_type`) est « Forces new resource » : le modifier recrée la table.
- Contexte : Pas de clé de partition dans le bloc : c'est celle de la table. Comme DynamoDB n'accepte un LSI qu'au `CreateTable`, le provider ne peut que détruire et recréer : la table repart vide. `range_key` doit avoir son bloc `attribute`. Le plan l'annonce par `-/+` et `# forces replacement` : à lire avant tout apply sur une table de données.
- Usage : ✅ LSI décidé dans le premier `apply` de la table · ❌ LSI ajouté sur une table remplie : préférer un GSI (mise à jour en place).

```hcl
# Exemple 1 : LSI par date (validate OK)
local_secondary_index {
  name            = "par-date"
  range_key       = "date"
  projection_type = "KEYS_ONLY"
}
# + attribute { name = "date" type = "S" }
# partition : hash_key de la table
```

- Quiz : On ajoute ce bloc à la table `annonces` déjà remplie, puis `make plan`. Qu'annonce le plan ?
- [ ] `~ update in-place` : l'index est créé à côté
- [x] `-/+` : table détruite puis recréée, vide
- [ ] Une erreur : LSI interdit en Terraform
- [ ] Rien : le bloc est ignoré après la création
- Réponse : `-/+` remplacement : selon la doc du provider, `local_secondary_index` force une nouvelle ressource ; les données sont perdues sans sauvegarde.

## 69. condition de clé : égalité puis plage
- Id : dynamodb-condition-de-cle
- Sous-thème : lecture
- Type : concept
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-query-une-partition
- Source : data-platform · pwa-sync
- Définition : Une `KeyConditionExpression` accepte `pk = :v` obligatoire, puis au plus une condition sur `sk` : `=`, `<`, `<=`, `>`, `>=`, `BETWEEN`, `begins_with`.
- Contexte : Pas de `OR`, pas de `IN`, pas de `contains`, rien sur un attribut hors clé : ces filtres vont dans `FilterExpression` (payé quand même). `begins_with` ne marche que sur `sk`, jamais sur `pk` (mesuré avec moto : « Query key condition not supported »). Avec boto3, `Key("pk").eq(…) & Key("sk").begins_with(…)` construit l'expression.
- Usage : ✅ prévoir les clés pour que chaque lecture tienne dans cette forme · ❌ espérer `pk IN (:a, :b)` : deux `Query`, ou un autre modèle.

```python
# Exemple 1 : boto3 construit l'expression
from boto3.dynamodb.conditions import Key
c = (Key("pk").eq("u1")
     & Key("sk").begins_with("R#"))
type(c).__name__  # → 'And'
```

- Quiz : `KeyConditionExpression="begins_with(pk, :p)"` pour lire tous les utilisateurs `eu-west-3:…`. Résultat ?
- [ ] Toutes les partitions de la région
- [x] `ValidationException`
- [ ] Les partitions triées par `pk`
- [ ] Un `Scan` implicite
- Réponse : `ValidationException` (mesuré avec moto) : la clé de partition n'accepte que l'égalité ; les partitions ne sont pas triées entre elles.

## 70. valeurs typées : {"S": …}
- Id : dynamodb-valeurs-typees
- Sous-thème : lecture
- Type : concept
- Niveau : 2
- Profils : web, data
- Source : data-platform · pwa-sync
- Définition : L'API bas niveau de DynamoDB type chaque valeur : `{"S": "u1"}`, `{"N": "5"}` (nombre en chaîne), `{"BOOL": true}`, `{"M": {…}}`, `{"L": […]}`.
- Contexte : La CLI, `fetch` signé et `boto3.client` parlent ce format ; `boto3.resource` (et `DynamoDBDocumentClient` en TS) convertit pour vous. Les nombres voyagent en chaîne pour garder leur précision. Oublier le type (`{":pk": "u1"}`) fait échouer la validation des paramètres côté client (mesuré : `ParamValidationError`).
- Usage : ✅ `TypeSerializer` ou `resource` en Python, `marshall` en TS · ❌ construire les `{"S": …}` à la main partout : verbeux et source d'erreurs.

```python
# Exemple 1 : la conversion de boto3
from boto3.dynamodb.types import TypeSerializer
s = TypeSerializer()
s.serialize("u1")   # → {'S': 'u1'}
s.serialize(5)      # → {'N': '5'}
s.serialize(True)   # → {'BOOL': True}
```

- Quiz : Que vaut `TypeSerializer().serialize(1.5)` ?
- [ ] `{'N': '1.5'}`
- [ ] `{'S': '1.5'}`
- [x] `TypeError` : il faut un `Decimal`
- [ ] `{'N': 1.5}`
- Réponse : `TypeError` (mesuré : « Float types are not supported. Use Decimal types instead. ») : boto3 refuse les `float`, imprécis ; `Decimal("1.5")` passe.

## 71. Select COUNT : compter sans rapatrier
- Id : dynamodb-select-count
- Sous-thème : lecture
- Type : recette
- Niveau : 2
- Profils : ops, data
- Prérequis : dynamodb-query-une-partition
- Source : data-platform · pwa-sync
- Définition : `--select COUNT` renvoie seulement `Count` et `ScannedCount`, sans les lignes : utile pour tester un accès ou compter.
- Contexte : La lecture est facturée pareil (DynamoDB lit les lignes pour les compter), mais la réponse est minuscule. Le script d'isolation s'en sert : un nombre prouve que la partition est lisible, sans afficher de données. `Count` est par page : au-delà de 1 Mo lu, il faut additionner les pages.
- Usage : ✅ vérifier un accès, compter une petite partition · ❌ compter une grosse table à chaque affichage : maintenir un compteur.

```bash
# Exemple 1 : un nombre, rien d'autre
aws dynamodb query --table-name "$table" \
  --key-condition-expression "pk = :pk" \
  --expression-attribute-values \
  '{":pk":{"S":"eu-west-3:1b2c…"}}' \
  --select COUNT --query Count --output text
# → 0   (mesuré)
```

- Quiz : Le script teste `[[ $count =~ ^[0-9]+$ ]]` après la `Query`. Pourquoi pas seulement « pas d'erreur » ?
- [ ] Pour vérifier que la partition est vide
- [x] Une sortie vide passait le test sans prouver la lecture
- [ ] `Count` peut être négatif
- [ ] Pour éviter le pager de la CLI
- Réponse : la sortie vide : au 1er run, la ligne était vide et le script disait « OK » (erreur vue) ; exiger un nombre prouve que la lecture a réussi.

## 72. FilterExpression : filtré après lecture
- Id : dynamodb-filterexpression-apres-lecture
- Sous-thème : lecture
- Type : piège
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-query-une-partition
- Voir aussi : dynamodb-condition-de-cle, dynamodb-rcu-arrondi-4ko
- Source : data-platform · pwa-sync
- Définition : `FilterExpression` retire des lignes **après** leur lecture : `Count` baisse, `ScannedCount` et la facture non.
- Contexte : La `KeyConditionExpression` choisit ce qui est lu (et payé) ; le filtre ne fait que trier la réponse, comme un `.filter()` côté serveur. Mesuré avec moto : 3 lignes lues, 1 renvoyée (`Count = 1`, `ScannedCount = 3`). Un filtre très sélectif sur une grosse partition est le signe d'une clé de tri mal choisie.
- Usage : ✅ écarter quelques lignes d'une plage déjà étroite · ❌ remplacer une bonne clé de tri : mettre le critère dans la `sk`.

```python
# Exemple 1 : Count et ScannedCount (moto)
import boto3
from boto3.dynamodb.conditions import Attr, Key
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
for i, ok in enumerate([True, False, False]):
    t.put_item(Item={"pk": "u1", "sk": f"R#{i}", "ok": ok})
r = t.query(KeyConditionExpression=Key("pk").eq("u1"),
            FilterExpression=Attr("ok").eq(True))
(r["Count"], r["ScannedCount"])  # → (1, 3)
m.stop()
```

- Quiz : `Limit=2` et un filtre qui ne garde que `ok = true` : combien de lignes au plus dans la page ?
- [ ] 2 lignes `ok`, quoi qu'il arrive
- [x] 2 au plus, et peut-être 0
- [ ] Toutes les lignes `ok` de la partition
- [ ] `ValidationException` : `Limit` et filtre incompatibles
- Réponse : 2 au plus, peut-être 0 : `Limit` borne les lignes **lues** avant filtre ; une page peut revenir vide avec un `LastEvaluatedKey`.

## 73. Query : la dernière annonce d'un SIREN
- Id : dynamodb-derniere-ligne-partition
- Sous-thème : lecture
- Type : recette
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-query-ordre-croissant
- Source : data-platform · pwa-sync
- Définition : `ScanIndexForward=False` + `Limit=1` lit une seule ligne : la plus grande `sk` de la partition, donc la plus récente avec une date ISO.
- Contexte : DynamoDB parcourt la partition à l'envers et s'arrête après une ligne : une seule ligne lue et facturée, au lieu de rapatrier toute la partition pour prendre le `max()` en Python. Restreindre la `sk` avec `begins_with` garde le bon type de ligne. Ne pas y ajouter de `FilterExpression` : `Limit` compte avant le filtre.
- Usage : ✅ dernière annonce d'un SIREN, dernière réponse d'une carte, état courant d'un traitement · ❌ lire toute la partition pour garder la dernière ligne : coût proportionnel à l'historique.

```python
# Exemple 1 : la plus récente (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="annonces",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
for d in ["10-01", "10-03", "10-02"]:
    t.put_item(Item={"pk": "483609327", "sk": f"A#2026-{d}"})
c = Key("pk").eq("483609327") & Key("sk").begins_with("A#")
r = t.query(KeyConditionExpression=c, ScanIndexForward=False, Limit=1)
(r["Count"], r["Items"][0]["sk"])  # → (1, 'A#2026-10-03')
m.stop()
```

- Quiz : La partition contient aussi `P#profil`. `ScanIndexForward=False, Limit=1` avec seulement `pk = :siren`. Résultat ?
- [ ] `A#2026-10-03`, la dernière annonce
- [x] `P#profil` : `P` est après `A`
- [ ] `ValidationException` : `sk` obligatoire
- [ ] Deux lignes, une par préfixe
- Réponse : `P#profil` (mesuré avec moto) : sans condition sur la `sk`, la plus grande `sk` de la partition gagne ; `begins_with(sk, "A#")` restreint aux annonces.

## 74. ProjectionExpression : moins de réseau, même coût
- Id : dynamodb-projectionexpression-cout
- Sous-thème : lecture
- Type : piège
- Niveau : 2
- Profils : web, ops
- Prérequis : dynamodb-rcu-arrondi-4ko
- Source : data-platform · pwa-sync
- Définition : `ProjectionExpression` ne renvoie que les attributs listés : la réponse rétrécit, mais la lecture est facturée sur la taille de la ligne entière.
- Contexte : DynamoDB lit toujours l'item complet sur disque puis découpe la réponse ; les unités de lecture se calculent sur l'item, pas sur ce qui revient (selon la doc). On gagne en octets transférés et en mémoire Lambda, pas en facture. Un attribut demandé mais absent n'apparaît simplement pas. Pour vraiment lire moins, il faut des items plus petits ou un index qui projette moins.
- Usage : ✅ alléger la réponse d'une API, ne garder que `sk` et `date` pour une liste · ❌ espérer baisser la facture d'un item de 300 Ko : découper l'item ou passer le gros contenu dans S3.

```python
# Exemple 1 : deux attributs sur trois (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="annonces",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
k = {"pk": "483609327", "sk": "A#1"}
t.put_item(Item={**k, "texte": "x" * 9000})
r = t.get_item(Key=k, ProjectionExpression="sk")
r["Item"]  # → {'sk': 'A#1'}
m.stop()
```

- Quiz : Item de 12 Ko, `ProjectionExpression` sur un attribut de 50 octets, `ConsistentRead=True`. Unités de lecture ?
- [ ] 0,5 : 50 octets tiennent dans 4 Ko
- [ ] 1 : une lecture forte minimale
- [ ] 1,5 : la moitié de 3
- [x] 3 : 12 Ko lus en lecture forte
- Réponse : 3 : la projection n'entre pas dans le calcul ; 12 Ko = 3 tranches de 4 Ko, à 1 unité chacune en lecture forte.

## 75. Select : ALL_ATTRIBUTES ou SPECIFIC_ATTRIBUTES
- Id : dynamodb-select-et-projection
- Sous-thème : lecture
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-projection-index
- Source : data-platform · pwa-sync
- Définition : `Select` choisit la forme de la réponse : `ALL_ATTRIBUTES` (défaut sur une table), `SPECIFIC_ATTRIBUTES` (ceux de `ProjectionExpression`), `COUNT`, `ALL_PROJECTED_ATTRIBUTES` (index seulement).
- Contexte : Donner une `ProjectionExpression` sans `Select` revient à `SPECIFIC_ATTRIBUTES`. Les deux paramètres sont liés : `SPECIFIC_ATTRIBUTES` sans projection est refusé, et toute autre valeur avec une projection aussi (selon la doc, mesuré avec moto). Sur un GSI, le défaut est `ALL_PROJECTED_ATTRIBUTES` : seuls les attributs copiés dans l'index sont lisibles.
- Usage : ✅ omettre `Select` et ne passer que `ProjectionExpression`, plus simple · ❌ empiler `Select` et projection en pensant combiner deux effets.

```python
# Exemple 1 : SPECIFIC + projection (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="annonces",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
t.put_item(Item={"pk": "483609327", "sk": "A#1", "ville": "Lyon"})
q = {"KeyConditionExpression": Key("pk").eq("483609327")}
t.query(**q, Select="SPECIFIC_ATTRIBUTES", ProjectionExpression="ville")["Items"]
# → [{'ville': 'Lyon'}]
sorted(t.query(**q)["Items"][0])  # → ['pk', 'sk', 'ville']
m.stop()
```

- Quiz : `Select="ALL_ATTRIBUTES"` avec `ProjectionExpression="ville"`. Résultat ?
- [ ] Tous les attributs : `Select` l'emporte
- [ ] `ville` seulement : la projection l'emporte
- [x] `ValidationException`
- [ ] `ville` en premier, puis le reste
- Réponse : `ValidationException` (selon la doc, mesuré avec moto : « Cannot specify the ProjectionExpression when choosing to get ALL_ATTRIBUTES ») : avec une projection, seul `SPECIFIC_ATTRIBUTES` est permis.

## 76. RCU : arrondi à 4 Ko par item
- Id : dynamodb-rcu-arrondi-4ko
- Sous-thème : lecture
- Type : concept
- Niveau : 2
- Profils : ops
- Source : data-platform · pwa-sync
- Définition : Une unité de lecture (RCU) = une lecture forte de 4 Ko ou deux éventuelles ; `GetItem` arrondit l'item au multiple de 4 Ko supérieur.
- Contexte : Selon la doc : 3,5 Ko comptent comme 4 Ko, 10 Ko comme 12 Ko. Lecture forte = 1 unité par tranche, éventuelle (défaut) = 0,5, transactionnelle (`TransactGetItems`) = 2. À la demande, on paie ces mêmes unités, appelées unités de requête de lecture. Garder les items petits est le premier levier de coût.
- Usage : ✅ estimer le coût d'une lecture avant de choisir la taille des items · ❌ raisonner en nombre de requêtes seulement : un item de 40 Ko coûte 10 fois un item de 4 Ko.

```python
# Exemple 1 : arrondi, forte ou éventuelle
import math
def rcu(octets, mode="eventuelle"):
    u = math.ceil(octets / 4096)
    return {"forte": u, "eventuelle": u / 2,
            "transaction": 2 * u}[mode]
rcu(3500, "forte")         # → 1
rcu(3500)                  # → 0.5
rcu(10 * 1024, "forte")    # → 3
rcu(8 * 1024, "transaction")  # → 4
```

- Quiz : `GetItem` par défaut sur un item de 4,1 Ko (4 200 octets). Combien d'unités de lecture ?
- [ ] 0,5 : un seul item
- [x] 1 : deux tranches de 4 Ko, à 0,5
- [ ] 1,025 : proportionnel à la taille
- [ ] 2 : deux tranches en lecture forte
- Réponse : 1 : 4 200 octets dépassent 4 Ko, donc 2 tranches ; par défaut la lecture est éventuelle, 0,5 par tranche.

## 77. ReturnConsumedCapacity : mesurer une lecture
- Id : dynamodb-consumed-capacity
- Sous-thème : lecture
- Type : recette
- Niveau : 2
- Profils : ops, expert
- Prérequis : dynamodb-rcu-arrondi-4ko
- Source : data-platform · pwa-sync
- Définition : `ReturnConsumedCapacity="TOTAL"` ajoute `ConsumedCapacity` à la réponse : les unités réellement consommées par cet appel (`INDEXES` détaille table et index).
- Contexte : Par défaut (`NONE`), la réponse ne dit rien du coût. Activé, il sert à vérifier une estimation, comparer deux modèles de clés, ou journaliser le coût d'une Lambda. Pour `GetItem`, `INDEXES` ne montre que la table : il ne lit jamais d'index (selon la doc). moto renvoie le champ, mais ses valeurs ne suivent pas toutes les règles d'AWS.
- Usage : ✅ mesurer en dev le coût réel d'une `Query` ou d'un `Scan` avant de choisir · ❌ se fier à une estimation de tête, ou aux chiffres de moto comme s'ils étaient ceux d'AWS.

```python
# Exemple 1 : le coût dans la réponse (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "V#mac"}
t.put_item(Item=k)
"ConsumedCapacity" in t.get_item(Key=k)  # → False
r = t.get_item(Key=k, ReturnConsumedCapacity="TOTAL")
r["ConsumedCapacity"]["CapacityUnits"]  # → 0.5
m.stop()
```

- Quiz : Dans un test moto, `get_item(…, ConsistentRead=True, ReturnConsumedCapacity="TOTAL")` sur un petit item. `CapacityUnits` ?
- [ ] 1 : lecture forte, comme sur AWS
- [x] 0,5 : moto ne double pas la lecture forte
- [ ] 2 : moto compte une transaction
- [ ] Absent : moto ne gère pas ce paramètre
- Réponse : 0,5 (mesuré avec moto) alors qu'AWS facture 1 : un test moto vérifie la forme de la réponse, pas le coût réel.

## 78. BatchGetItem : UnprocessedKeys et ordre libre
- Id : dynamodb-batchgetitem-unprocessedkeys
- Sous-thème : lecture
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : dynamodb-batchgetitem
- Voir aussi : dynamodb-backoff-jitter
- Source : data-platform · pwa-sync
- Définition : `BatchGetItem` peut rendre une partie des clés dans `UnprocessedKeys` et renvoie les items dans un ordre quelconque, à réassocier par clé.
- Contexte : Réponse partielle, toujours en `200`, si la réponse dépasse 16 Mo, si le débit est dépassé ou si plus de 1 Mo est demandé à une partition (selon la doc). `UnprocessedKeys` a la forme de `RequestItems` : on le renvoie tel quel, avec un délai croissant. Les items arrivent sans ordre garanti : la doc conseille de projeter les attributs de clé pour les reconnaître. En TS, même logique : construire une `Map` par clé.
- Usage : ✅ boucle « renvoyer `UnprocessedKeys` » puis index par clé · ❌ supposer que `Responses[i]` correspond à `Keys[i]`.

```python
# Exemple 1 : réassocier par clé
rep = {"Responses": {"annonces": [
  {"siren": "552100554", "type": "BODA"},
  {"siren": "483609327", "type": "BODB"}]},
  "UnprocessedKeys": {}}
par_siren = {i["siren"]: i
  for i in rep["Responses"]["annonces"]}
par_siren["483609327"]["type"]  # → 'BODB'
```

```python
# Exemple 2 : renvoyer ce qui reste
rep = {"Responses": {}, "UnprocessedKeys": {
  "annonces": {"Keys": [{"siren": "552100554"}]}}}
demande = rep["UnprocessedKeys"]   # même forme
bool(demande)  # → True  (re-appel, avec délai)
```

- Quiz : 100 clés demandées, chaque item fait 300 Ko. Que renvoie un seul `BatchGetItem` ?
- [ ] 100 items : la limite est en nombre de clés
- [ ] `ValidationException` : réponse trop grosse
- [x] 52 items et le reste dans `UnprocessedKeys`
- [ ] 100 items tronqués à 160 Ko
- Réponse : 52 items (exemple de la doc) : la réponse est plafonnée à 16 Mo, le reste revient dans `UnprocessedKeys` à redemander.

## 79. Query : pages de 1 Mo, LastEvaluatedKey
- Id : dynamodb-pagination-query
- Sous-thème : lecture
- Type : piège
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-query-une-partition
- Voir aussi : s3-pagination-1000
- Source : data-platform · pwa-sync
- Définition : Une `Query` renvoie au plus 1 Mo (ou `Limit` lignes) ; `LastEvaluatedKey` indique où reprendre avec `ExclusiveStartKey`.
- Contexte : Pas de `LastEvaluatedKey` : c'est la dernière page. Lire une seule page d'une grosse partition donne un résultat silencieusement incomplet, sans erreur. La CLI pagine seule (désactivable avec `--no-paginate`) ; boto3 a `get_paginator("query")` côté client. Même logique que `ContinuationToken` de S3.
- Usage : ✅ boucler tant que `LastEvaluatedKey` existe, ou utiliser un paginator · ❌ supposer qu'une `Query` renvoie tout.

```python
# Exemple 1 : 3 lignes, pages de 2 (moto)
import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
for d in "123": t.put_item(Item={"pk": "u1", "sk": f"R#2026-10-0{d}"})
q = {"KeyConditionExpression": Key("pk").eq("u1"), "Limit": 2}
p1 = t.query(**q)
p1["LastEvaluatedKey"]["sk"]  # → 'R#2026-10-02'
"LastEvaluatedKey" in t.query(**q, ExclusiveStartKey=p1["LastEvaluatedKey"])  # → False
m.stop()
```

- Quiz : Avec `boto3.resource`, `table.query(…)` sur une partition de 5 Mo, sans boucle. Combien de lignes reviennent ?
- [ ] Toutes : `resource` pagine seul
- [x] Environ le premier Mo seulement
- [ ] Aucune : erreur de taille
- [ ] 100 lignes par défaut
- Réponse : le premier Mo : ni `Table.query` ni `client.query` ne paginent ; il faut boucler sur `LastEvaluatedKey` ou un paginator.

## 80. BatchWriteItem : 25 par lot, UnprocessedItems
- Id : dynamodb-batchwriteitem-25
- Sous-thème : écriture
- Type : concept
- Niveau : 2
- Profils : data
- Source : data-platform · pwa-sync
- Définition : `BatchWriteItem` envoie jusqu'à 25 `PutRequest` ou `DeleteRequest` en une requête ; ce qui n'a pas été traité revient dans `UnprocessedItems`.
- Contexte : Le lot n'est pas transactionnel : une partie peut réussir, l'autre revenir dans `UnprocessedItems`, sans erreur HTTP (limitation de débit). Il faut renvoyer ces éléments, idéalement avec un délai croissant. Au-delà de 25 éléments, la requête entière est refusée (`ValidationException`, selon la doc). Côté pwa-sync, les non traités retournent dans l'outbox.
- Usage : ✅ envoyer l'outbox par paquets de 25, réinjecter `UnprocessedItems` · ❌ traiter un `200` comme « tout est écrit » sans lire `UnprocessedItems`.

```python
# Exemple 1 : découper l'outbox par 25
outbox = [{"sk": f"R#2026-10-25#{i}"}
          for i in range(60)]
lots = [outbox[i:i + 25]
        for i in range(0, len(outbox), 25)]
[len(l) for l in lots]  # → [25, 25, 10]
```

```python
# Exemple 2 : réinjecter les non traités
rep = {"UnprocessedItems": {"progress": [
  {"PutRequest": {"Item": {"sk": "R#…#7"}}}]}}
reste = rep["UnprocessedItems"].get(
    "progress", [])
len(reste)  # → 1   (à renvoyer plus tard)
```

- Quiz : Lot de 25, réponse `200` avec 3 éléments dans `UnprocessedItems`. Combien de lignes écrites ?
- [ ] 25 : la réponse est un succès
- [ ] 0 : le lot est annulé
- [x] 22 : les 3 autres sont à renvoyer
- [ ] 25, les 3 sont écrits en différé
- Réponse : 22 : `BatchWriteItem` n'est pas atomique ; les éléments de `UnprocessedItems` ne sont pas écrits tant qu'on ne les renvoie pas.

## 81. batch_writer : les lots de 25 sans y penser
- Id : dynamodb-batch-writer
- Sous-thème : écriture
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : dynamodb-batchwriteitem-25
- Voir aussi : dynamodb-batchwrite-cle-en-double
- Source : data-platform · pwa-sync
- Définition : `table.batch_writer()` de boto3 met les `put_item` en tampon, envoie des `BatchWriteItem` de 25 et renvoie seul les `UnprocessedItems`.
- Contexte : Gestionnaire de contexte (`with`) : à la sortie, il vide le tampon jusqu'au dernier élément. Pas d'équivalent dans le SDK JS v3 (`BatchWriteCommand` à découper soi-même). Lu dans le source de boto3 : les non traités sont remis dans le lot suivant sans délai propre ; le backoff ne vient que des réessais de botocore sur exception. `overwrite_by_pkeys` dédoublonne le tampon par clé, le dernier gagne.
- Usage : ✅ charger des milliers de lignes complètes depuis un script ou une Lambda · ❌ écritures conditionnelles ou incréments : `UpdateItem` ou transaction.

```python
# Exemple 1 : 60 lignes, 3 appels (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
with t.batch_writer(overwrite_by_pkeys=["pk", "sk"]) as b:
  for i in range(60):
    b.put_item(Item={"pk": "u1", "sk": f"R#{i:02d}"})
  b.put_item(Item={"pk": "u1", "sk": "R#00", "ok": True})
t.scan()["Count"]  # → 60  (doublon R#00 fusionné)
m.stop()
```

- Quiz : Dans le `with`, 30 `put_item`, puis une exception est levée. Combien de lignes sont écrites ?
- [ ] 0 : le `with` annule le lot
- [ ] 25 : seul le premier lot plein est parti
- [x] 30 : la sortie du `with` vide quand même le tampon
- [ ] 5 : seul le reste du tampon est envoyé
- Réponse : 30 (mesuré avec moto, et `__exit__` du source boto3 vide le tampon sans regarder l'exception) : ce n'est pas une transaction.

## 82. BatchWriteItem : la même clé deux fois
- Id : dynamodb-batchwrite-cle-en-double
- Sous-thème : écriture
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : dynamodb-batchwriteitem-25
- Source : data-platform · pwa-sync
- Définition : Un `BatchWriteItem` qui vise deux fois la même clé est refusé en entier, comme un lot de plus de 16 Mo.
- Contexte : Selon la doc, tout le lot est rejeté (`ValidationException`) si deux requêtes visent le même item, si un item dépasse 400 Ko, si le lot dépasse 16 Mo ou 25 requêtes. Piège : moto accepte deux `Put` de la même clé (mesuré) ; le test passe, la prod échoue. Une outbox pwa-sync qui a enregistré deux fois la même réponse doit être dédoublonnée avant le découpage en lots.
- Usage : ✅ dédoublonner par (`pk`, `sk`) avant de découper par 25, le dernier état gagne · ❌ faire confiance à moto pour valider les limites de `BatchWriteItem`.

```python
# Exemple 1 : dédoublonner l'outbox
outbox = [
  {"pk": "u1", "sk": "V#mac#IAM", "vues": 3},
  {"pk": "u1", "sk": "V#ios#IAM", "vues": 1},
  {"pk": "u1", "sk": "V#mac#IAM", "vues": 4}]
dernier = {(e["pk"], e["sk"]): e
           for e in outbox}   # le dernier gagne
len(dernier)  # → 2
dernier[("u1", "V#mac#IAM")]["vues"]  # → 4
```

- Quiz : Un lot contient un `PutRequest` et un `DeleteRequest` sur la même clé. Résultat selon la doc ?
- [ ] Le `Put` puis le `Delete` : la ligne disparaît
- [ ] Le dernier de la liste gagne
- [x] Tout le lot est refusé
- [ ] Le `Delete` revient dans `UnprocessedItems`
- Réponse : tout le lot est refusé : la doc interdit plusieurs opérations sur le même item dans un `BatchWriteItem`, même un `Put` et un `Delete`.

## 83. UnprocessedItems : backoff exponentiel et jitter
- Id : dynamodb-backoff-jitter
- Sous-thème : écriture
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : dynamodb-batchwriteitem-25
- Voir aussi : dynamodb-reessais-botocore, step-functions-retry-backoff
- Source : data-platform · pwa-sync
- Définition : On renvoie `UnprocessedItems` après un délai qui double à chaque tentative (backoff exponentiel), tiré au hasard sous ce plafond (jitter), avec un nombre d'essais borné.
- Contexte : La doc « recommande fortement » le backoff : renvoyé tout de suite, le lot retombe sur la même table saturée. Le jitter évite que plusieurs Lambdas, limitées au même instant, réessaient toutes ensemble et recréent le pic. Plafonner le délai (`cap`) et le nombre d'essais, puis remonter une erreur : sinon la Lambda tourne jusqu'à son timeout. En TS, même schéma avec `setTimeout`.
- Usage : ✅ boucle `while reste and essai < max` avec délai `uniform(0, min(cap, base * 2**n))` · ❌ `while reste:` sans délai ni limite.

```python
# Exemple 1 : plafonds de délai, en s
base, cap = 0.05, 1.0
[min(cap, base * 2 ** n) for n in range(6)]
# → [0.05, 0.1, 0.2, 0.4, 0.8, 1.0]
```

```python
# Exemple 2 : full jitter
import random
plafond = min(1.0, 0.05 * 2 ** 4)   # 0.8
d = random.uniform(0, plafond)
0 <= d <= 0.8  # → True  (délai tiré au hasard)
```

- Quiz : Une Lambda renvoie ses `UnprocessedItems` en boucle, sans délai, 50 fois en une seconde. Effet probable ?
- [ ] Tout passe : DynamoDB priorise les réessais
- [x] Les envois restent limités, la capacité est gaspillée
- [ ] DynamoDB passe la table à la demande
- [ ] Le lot devient atomique au 2e essai
- Réponse : toujours limités : la table est encore saturée ; la doc explique que sans backoff les requêtes du lot échouent de nouveau par throttling.

## 84. ADD et DELETE : sur un ensemble
- Id : dynamodb-ensemble-add-delete
- Sous-thème : écriture
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-ensembles, dynamodb-updateexpression-clauses
- Source : data-platform · pwa-sync
- Définition : Sur un ensemble (`SS`, `NS`), `ADD` ajoute des éléments sans doublon et `DELETE` en retire ; `DELETE` n'accepte que les ensembles.
- Contexte : Un `set` Python devient un `SS` (équivalent d'un `Set<string>` en TS). `ADD`/`DELETE` modifient l'ensemble côté serveur, sans relire : deux appareils peuvent ajouter chacun un thème en même temps. `ADD` accepte un nombre ou un ensemble, jamais une liste (`L`) ni une chaîne ; `DELETE` sur un nombre lève `ValidationException` (mesuré avec moto).
- Usage : ✅ étiquettes, thèmes vus, SIREN cités, sans ordre ni doublon · ❌ historique ordonné ou avec répétitions : une liste et `list_append`.

```python
# Exemple 1 : ADD puis DELETE (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "P#themes"}
def maj(e, s):
    return t.update_item(Key=k, UpdateExpression=e,
      ExpressionAttributeValues={":s": s},
      ReturnValues="ALL_NEW")["Attributes"]
maj("ADD vus :s", {"IAM", "S3"})
maj("ADD vus :s", {"S3", "KMS"})["vus"]  # → {"IAM", "S3", "KMS"}
maj("DELETE vus :s", {"IAM"})["vus"]  # → {"S3", "KMS"}
m.stop()
```

- Quiz : L'ensemble vaut `{"S3", "KMS"}` ; on fait `DELETE vus :s` avec `{"S3", "KMS"}`. Que devient `vus` ?
- [ ] Un ensemble vide `set()`
- [ ] `ValidationException` : ensemble vide interdit
- [x] L'attribut `vus` disparaît de la ligne
- [ ] La ligne entière est supprimée
- Réponse : l'attribut disparaît (mesuré avec moto) : un ensemble ne peut pas être vide (selon la doc), donc vider le set retire l'attribut, la ligne reste.

## 85. UpdateExpression : plusieurs clauses
- Id : dynamodb-updateexpression-clauses
- Sous-thème : écriture
- Type : concept
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-updateitem-partiel
- Source : data-platform · pwa-sync
- Définition : Une `UpdateExpression` combine `SET`, `REMOVE`, `ADD`, `DELETE` dans n'importe quel ordre, chaque mot-clé une seule fois, ses actions séparées par des virgules.
- Contexte : Tout s'applique en une seule écriture atomique : pas d'état intermédiaire visible. Plusieurs affectations vont dans le même `SET` (`SET a = :a, b = :b`). Un même attribut ne peut pas apparaître dans deux actions (`SET a … REMOVE a`) : mesuré avec moto, `ValidationException` (« Two document paths overlap »).
- Usage : ✅ marquer une réponse : `SET ok = :t, le = :d ADD essais :un` en un appel · ❌ trois `UpdateItem` successifs : trois écritures payées, états intermédiaires visibles.

```python
# Exemple 1 : SET, REMOVE et ADD ensemble
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "R#2026-10-25#IAM/3"}
t.put_item(Item={**k, "brouillon": "x"})
r = t.update_item(Key=k, UpdateExpression=
  "SET ok = :t, le = :d REMOVE brouillon ADD essais :un",
  ExpressionAttributeValues={":t": True,
    ":d": "2026-10-25", ":un": 1},
  ReturnValues="ALL_NEW")["Attributes"]
sorted(r)  # → ['essais', 'le', 'ok', 'pk', 'sk']
m.stop()
```

- Quiz : `UpdateExpression="SET ok = :t SET le = :d"`. Résultat ?
- [ ] Les deux attributs sont posés
- [ ] Seul le second `SET` est appliqué
- [x] `ValidationException`
- [ ] Deux écritures successives
- Réponse : `ValidationException` (mesuré avec moto) : chaque mot-clé apparaît une fois ; on écrit `SET ok = :t, le = :d`.

## 86. SET a = a + :n : lu avant la mise à jour
- Id : dynamodb-set-arithmetique
- Sous-thème : écriture
- Type : piège
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-updateexpression-clauses
- Voir aussi : dynamodb-add-compteur
- Source : data-platform · pwa-sync
- Définition : `SET a = a + :n` (ou `- :n`) calcule côté serveur à partir de la valeur actuelle ; l'attribut doit exister.
- Contexte : Contrairement à `ADD`, `SET a = a + :n` échoue si `a` est absent (mesuré avec moto : `ValidationException`, « attribute that does not exist »). Toutes les actions d'une expression lisent les valeurs **d'avant** la mise à jour (selon la doc) : l'ordre d'écriture des actions ne change rien. On peut ainsi décaler des valeurs (`SET b = a, c = b`).
- Usage : ✅ ajouter ou retirer une quantité à un attribut qui existe à coup sûr · ❌ compteur peut-être absent : `ADD`, ou `if_not_exists(a, :zero) + :n`.

```python
# Exemple 1 : a existe, puis absent
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "T#mac#IAM"}
t.put_item(Item={**k, "s": 120})
def plus(attr):
    return t.update_item(Key=k, ReturnValues="UPDATED_NEW",
      UpdateExpression=f"SET {attr} = {attr} + :n",
      ExpressionAttributeValues={":n": 30})
plus("s")["Attributes"]["s"]  # → 150
plus("z")  # ❌ ClientError
m.stop()
```

- Quiz : Ligne `{a: 1}`, expression `SET a = a + :n, b = a` avec `:n = 10`. Que vaut `b` ?
- [ ] `11` : `a` est déjà mis à jour
- [x] `1` : la valeur de `a` avant l'appel
- [ ] `ValidationException` : `a` utilisé deux fois
- [ ] `10`
- Réponse : `1` : selon la doc (et mesuré avec moto), chaque action lit l'état d'avant la mise à jour, pas le résultat de l'action voisine.

## 87. if_not_exists : valeur seulement si absente
- Id : dynamodb-if-not-exists
- Sous-thème : écriture
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-updateexpression-clauses
- Source : data-platform · pwa-sync
- Définition : `if_not_exists(a, :v)` vaut `a` s'il existe, sinon `:v` ; il sert à initialiser un compteur ou à figer une « date de première vue ».
- Contexte : `SET vu = if_not_exists(vu, :d)` pose la date au premier passage et la garde ensuite : les appels suivants réécrivent la même valeur. `SET n = if_not_exists(n, :zero) + :un` est un compteur qui démarre seul, comme `ADD`, mais combinable avec d'autres `SET`. La fonction n'existe que dans une `UpdateExpression`, côté `SET` (selon la doc).
- Usage : ✅ `premiere_vue`, `cree_le`, compteur initialisé dans un `SET` · ❌ test d'existence avant écriture : `attribute_not_exists` dans `ConditionExpression`.

```python
# Exemple 1 : la première date reste
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "siren#483609327", "sk": "VU"}
for d in ["2026-10-01", "2026-10-25"]:
    t.update_item(Key=k, UpdateExpression=
      "SET vu = if_not_exists(vu, :d), der = :d",
      ExpressionAttributeValues={":d": d})
r = t.get_item(Key=k)["Item"]
(r["vu"], r["der"])  # → ('2026-10-01', '2026-10-25')
m.stop()
```

- Quiz : `ConditionExpression="if_not_exists(ok, :f) = :f"` pour tester un attribut. Résultat selon la doc ?
- [ ] Vrai si `ok` est absent
- [ ] Vrai si `ok` vaut `:f`
- [x] Expression refusée : réservée à `SET`
- [ ] Équivalent de `attribute_not_exists(ok)`
- Réponse : refusée : selon la doc, `if_not_exists` n'existe que dans une `UpdateExpression` ; une condition utilise `attribute_not_exists`.

## 88. list_append : en fin ou en tête
- Id : dynamodb-list-append
- Sous-thème : écriture
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-chemin-document, dynamodb-updateexpression-clauses
- Source : data-platform · pwa-sync
- Définition : `SET h = list_append(h, :x)` ajoute la liste `:x` en fin de `h` ; `list_append(:x, h)` l'ajoute en tête.
- Contexte : `list_append(l1, l2)` concatène `l2` après `l1` (≈ `[...l1, ...l2]` en TS) : l'ordre des arguments décide du côté. Les deux arguments sont des listes : `:x` vaut `["c"]`, pas `"c"`. Sur une liste absente, l'appel échoue (mesuré avec moto) : on écrit `list_append(if_not_exists(h, :vide), :x)` avec `:vide = []`.
- Usage : ✅ historique ordonné court (dernières réponses d'une carte) · ❌ liste qui grossit sans fin : la ligne approche 400 Ko, et chaque écriture paie toute sa taille.

```python
# Exemple 1 : fin, puis tête (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "H#IAM/3"}
t.put_item(Item={**k, "h": ["b"]})
def maj(e, x):
    return t.update_item(Key=k, UpdateExpression=e,
      ExpressionAttributeValues={":x": x},
      ReturnValues="UPDATED_NEW")["Attributes"]["h"]
maj("SET h = list_append(h, :x)", ["c"])  # → ['b', 'c']
maj("SET h = list_append(:x, h)", ["a"])  # → ['a', 'b', 'c']
m.stop()
```

- Quiz : `SET hist = list_append(hist, :x)` sur une ligne qui n'a pas encore `hist`. Résultat ?
- [ ] `hist` vaut `:x`
- [ ] `hist` vaut `[None] + :x`
- [x] `ValidationException` : attribut absent
- [ ] La ligne est ignorée
- Réponse : `ValidationException` (mesuré avec moto) : `hist` n'existe pas ; `list_append(if_not_exists(hist, :vide), :x)` couvre le premier ajout.

## 89. ReturnValues : récupérer l'avant ou l'après
- Id : dynamodb-returnvalues
- Sous-thème : écriture
- Type : recette
- Niveau : 2
- Profils : web
- Prérequis : dynamodb-updateitem-partiel
- Source : data-platform · pwa-sync
- Définition : `ReturnValues` renvoie la ligne dans `Attributes` : `ALL_OLD`/`ALL_NEW` (toute la ligne), `UPDATED_OLD`/`UPDATED_NEW` (attributs modifiés), `NONE` par défaut.
- Contexte : Évite un `GetItem` après l'écriture : le compteur incrémenté revient dans la même réponse. Selon la doc, aucune RCU n'est consommée pour ces valeurs. `PutItem` et `DeleteItem` n'acceptent que `NONE` et `ALL_OLD` ; les quatre variantes sont pour `UpdateItem`. `UPDATED_OLD` sur un attribut qui n'existait pas ne renvoie pas `Attributes` (mesuré avec moto).
- Usage : ✅ `UPDATED_NEW` pour lire le compteur après `ADD` · ❌ `GetItem` juste après l'écriture : un appel de plus, et une autre écriture a pu passer entre-temps.

```python
# Exemple 1 : avant / après, même appel
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "V#mac#IAM"}
t.put_item(Item={**k, "vues": 4, "theme": "IAM"})
def add(rv):
    return t.update_item(Key=k, ReturnValues=rv,
      UpdateExpression="ADD vues :un",
      ExpressionAttributeValues={":un": 1})["Attributes"]
add("UPDATED_OLD")  # → {"vues": 4}
add("UPDATED_NEW")  # → {"vues": 6}
m.stop()
```

- Quiz : `put_item(Item=…, ReturnValues="ALL_NEW")` pour récupérer la ligne écrite. Résultat ?
- [ ] La ligne écrite dans `Attributes`
- [ ] `Attributes` vide : rien n'a changé
- [ ] L'ancienne ligne, comme `ALL_OLD`
- [x] `ValidationException`
- Réponse : `ValidationException` (selon la doc et mesuré avec moto) : `PutItem` ne reconnaît que `NONE` et `ALL_OLD` ; la ligne écrite, on l'a déjà côté client.

## 90. ConditionExpression : attribut absent, comparaison fausse
- Id : dynamodb-condition-attribut-absent
- Sous-thème : écriture
- Type : piège
- Niveau : 2
- Profils : web, expert
- Prérequis : dynamodb-creer-si-absent
- Source : data-platform · pwa-sync
- Définition : Une `ConditionExpression` combine comparaisons (`=`, `<>`, `<`, `BETWEEN`, `IN`), fonctions (`attribute_exists`, `size`, `begins_with`…) et `AND`/`OR`/`NOT`.
- Contexte : Elle s'évalue sur la ligne actuelle, avant l'écriture. `size(h)` donne la longueur d'une chaîne, d'une liste ou d'un ensemble : `size(h) < :max` borne un historique. Piège : une comparaison sur un attribut absent est fausse, donc `NOT a > :m` est **vraie** quand `a` manque (mesuré avec moto). Pour exiger la présence, ajouter `attribute_exists(a) AND …`.
- Usage : ✅ invariants métier (`stock >= :q`, `size(h) < :max`, `statut = :attendu`) · ❌ condition sur un attribut parfois absent sans `attribute_exists` : résultat surprenant.

```python
# Exemple 1 : borner une liste avec size()
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "H#IAM/3"}
t.put_item(Item={**k, "h": ["a", "b", "c"]})
t.update_item(Key=k,
  UpdateExpression="SET h = list_append(h, :x)",
  ConditionExpression="size(h) < :max",
  ExpressionAttributeValues={":x": ["d"], ":max": 3})  # ❌ ClientError
m.stop()
```

- Quiz : Ligne sans attribut `essais`. La condition `NOT essais >= :max` (`:max = 3`) est-elle vraie ?
- [ ] Non : `essais` absent, donc condition fausse
- [x] Oui : `essais >= :max` est faux, `NOT` le rend vrai
- [ ] `ValidationException` : attribut absent
- [ ] Oui, car `essais` vaut 0 par défaut
- Réponse : oui (mesuré avec moto) : la comparaison sur un attribut absent est fausse, et `NOT` l'inverse ; il n'y a pas de 0 par défaut hors `ADD`.

## 91. BatchWriteItem : ni Update ni condition
- Id : dynamodb-batchwrite-sans-condition
- Sous-thème : écriture
- Type : comparaison
- Niveau : 2
- Profils : data
- Prérequis : dynamodb-batchwriteitem-25
- Voir aussi : dynamodb-transactwriteitems
- Source : data-platform · pwa-sync
- Définition : `BatchWriteItem` n'accepte que `PutRequest` et `DeleteRequest` : ni `UpdateItem`, ni `ConditionExpression`, ni lecture de l'ancienne valeur.
- Contexte : Chaque élément est un remplacement ou une suppression brute. Pour une mise à jour partielle ou conditionnelle, il faut `UpdateItem` un par un, ou `TransactWriteItems` (100 éléments au plus, tout ou rien, coût double). pwa-sync s'en accommode : chaque ligne porte sa dernière valeur complète, un `Put` suffit. Mesuré : `UpdateRequest` refusé dès la validation des paramètres de boto3.
- Usage : ✅ écritures en masse de lignes complètes, suppressions de partition · ❌ incréments, « écrire si absent » : `UpdateItem` ou transaction.

```python
# Exemple 1 : seules deux formes
lot = [
  {"PutRequest": {"Item": {"pk": {"S": "u1"},
                           "sk": {"S": "V#mac"}}}},
  {"DeleteRequest": {"Key": {"pk": {"S": "u1"},
                             "sk": {"S": "T#mac"}}}},
]
sorted(next(iter(e)) for e in lot)
# → ['DeleteRequest', 'PutRequest']
```

- Quiz : Il faut écrire 30 lignes « tout ou rien ». Quel appel ?
- [ ] `BatchWriteItem` : atomique par lot de 25
- [x] `TransactWriteItems`, qui accepte jusqu'à 100 éléments
- [ ] Deux `BatchWriteItem` avec `ConditionExpression`
- [ ] `PutItem` avec `ReturnValues`
- Réponse : `TransactWriteItems` : tout ou rien, jusqu'à 100 actions ; `BatchWriteItem` n'est pas atomique et n'a pas de condition.

## 92. TransactGetItems : un instantané cohérent
- Id : dynamodb-transactgetitems
- Sous-thème : transactions
- Type : concept
- Niveau : 2
- Profils : web
- Source : data-platform · pwa-sync
- Définition : `TransactGetItems` lit jusqu'à 100 items en une fois et garantit qu'ils viennent du même instant, jamais d'une transaction à moitié appliquée.
- Contexte : Plusieurs `GetItem` (ou un `BatchGetItem`) lancés pendant une transaction d'écriture peuvent voir l'ancien état d'un item et le nouvel état d'un autre : la doc parle d'isolation « read-committed ». `TransactGetItems` est sérialisable : tout avant, ou tout après. `Responses` suit l'ordre de la requête, case vide pour un item absent. Limites selon la doc : 100 items, 4 Mo.
- Usage : ✅ relire ensemble l'annonce et le compteur du tribunal écrits par une même transaction · ❌ lire en masse sans besoin de cohérence : `BatchGetItem`, moins cher (pas de double lecture).

```python
# Exemple 1 : réponses dans l'ordre demandé
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
db = boto3.resource("dynamodb", region_name="eu-west-3")
t = db.create_table(TableName="bodacc",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
t.put_item(Item={"pk": "TRIB#Paris", "n": 3})
get = lambda k: {"Get": {"TableName": "bodacc",
                         "Key": {"pk": k}}}
r = db.meta.client.transact_get_items(
  TransactItems=[get("TRIB#Lyon"), get("TRIB#Paris")])
r["Responses"][0]          # → {}   (absent)
r["Responses"][1]["Item"]["n"]  # → 3
m.stop()
```

- Quiz : `TransactGetItems` pour lire 3 lignes d'un index secondaire global (GSI). Résultat ?
- [ ] Lecture cohérente des 3 lignes de l'index
- [ ] Lecture de l'index, sans garantie d'instantané
- [x] Impossible : les transactions ne lisent que des tables
- [ ] Possible avec `ConsistentRead=True`
- Réponse : impossible : selon la doc, `TransactGetItems` lit des tables, « pas des index » ; il faut viser les clés de la table.

## 93. TransactionCanceledException : CancellationReasons
- Id : dynamodb-transaction-annulee-raisons
- Sous-thème : transactions
- Type : recette
- Niveau : 2
- Profils : web
- Source : data-platform · pwa-sync
- Définition : Une transaction annulée lève `TransactionCanceledException`, dont `CancellationReasons` donne un code par action, dans l'ordre de `TransactItems`.
- Contexte : Codes possibles selon la doc : `None` (cette action allait bien, la chaîne littérale `"None"`), `ConditionalCheckFailed`, `TransactionConflict`, `ThrottlingError`, `ValidationError`… Il faut lire la liste pour savoir quelle action a bloqué : la condition métier ou un conflit passager. En boto3, la liste est dans `e.response["CancellationReasons"]`.
- Usage : ✅ `ConditionalCheckFailed` → erreur métier (409) ; `TransactionConflict` → réessayer · ❌ un message générique « transaction échouée » sans regarder la raison.

```python
# Exemple 1 : quelle action a bloqué ? (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
db = boto3.resource("dynamodb", region_name="eu-west-3")
t = db.create_table(TableName="bodacc",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
t.put_item(Item={"pk": "ANNONCE#A1"})
put = lambda k: {"Put": {"TableName": "bodacc",
  "Item": {"pk": k},
  "ConditionExpression": "attribute_not_exists(pk)"}}
c = db.meta.client
try:
  c.transact_write_items(TransactItems=[put("ANNONCE#A2"), put("ANNONCE#A1")])
except c.exceptions.TransactionCanceledException as e:
  codes = [r["Code"] for r in e.response["CancellationReasons"]]
codes  # → ['None', 'ConditionalCheckFailed']
m.stop()
```

- Quiz : Le SDK (boto3, JS v3) réessaie-t-il seul une `TransactionCanceledException` ?
- [ ] Oui, comme le throttling, avec backoff
- [ ] Oui, une seule fois
- [x] Non : c'est au code de décider selon la raison
- [ ] Oui, si un `ClientRequestToken` est fourni
- Réponse : non : selon la doc, quand une transaction est annulée « les SDK AWS ne réessaient pas » ; seul le code sait si la raison est métier ou passagère.

## 94. ConditionCheck : vérifier sans écrire
- Id : dynamodb-conditioncheck
- Sous-thème : transactions
- Type : concept
- Niveau : 2
- Profils : web
- Voir aussi : dynamodb-unicite-item-garde
- Source : data-platform · pwa-sync
- Définition : Une action `ConditionCheck` pose une condition sur un item que la transaction ne modifie pas : si elle est fausse, toute la transaction est annulée.
- Contexte : Équivalent d'une contrainte de clé étrangère, vérifiée au moment de l'écriture : « le tribunal existe » avant d'enregistrer une annonce qui le référence. Lire le tribunal avant puis écrire laisse une fenêtre où il peut être supprimé ; dans la transaction, la vérification et l'écriture sont atomiques. L'action ne coûte qu'en capacité, l'item vérifié n'est pas modifié.
- Usage : ✅ garantir qu'une référence existe ou qu'un statut vaut une valeur au moment de l'écriture · ❌ vérifier un attribut de l'item qu'on écrit : `ConditionExpression` sur le `Put` lui-même.

```python
# Exemple 1 : annonce si le tribunal existe
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
db = boto3.resource("dynamodb", region_name="eu-west-3")
t = db.create_table(TableName="bodacc",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
t.put_item(Item={"pk": "TRIB#Paris"})
tx = lambda trib: db.meta.client.transact_write_items(TransactItems=[
  {"ConditionCheck": {"TableName": "bodacc",
    "Key": {"pk": f"TRIB#{trib}"},
    "ConditionExpression": "attribute_exists(pk)"}},
  {"Put": {"TableName": "bodacc",
    "Item": {"pk": f"ANNONCE#{trib}", "tribunal": trib}}}])
tx("Paris")
tx("Atlantis")  # ❌ TransactionCanceledException
t.scan()["Count"]  # → 2  (tribunal + annonce Paris)
m.stop()
```

- Quiz : Même transaction, mais avec un `ConditionCheck` et un `Update` sur `TRIB#Paris` (incrémenter son compteur). Résultat ?
- [ ] Vérifie puis incrémente, dans cet ordre
- [ ] L'`Update` seul est appliqué
- [x] Requête refusée : deux actions sur le même item
- [ ] Le `ConditionCheck` est ignoré
- Réponse : refusée : selon la doc, deux actions ne peuvent viser le même item (mesuré avec moto : `ValidationException`) ; mettre la condition dans l'`Update` lui-même.

## 95. mode de capacité : changer de mode
- Id : dynamodb-changer-mode-capacite
- Sous-thème : capacité
- Type : concept
- Niveau : 2
- Profils : ops
- Source : data-platform · pwa-sync
- Définition : Une table passe de provisionné à la demande au plus 4 fois par 24 h glissantes ; en Terraform, on change `billing_mode`.
- Contexte : Limite relevée dans la doc DynamoDB (on-demand capacity mode). Le changement ne recrée pas la table et ne coupe pas le trafic. En passant en `PROVISIONED`, il faut fournir `read_capacity` et `write_capacity` (requis par le provider en `PROVISIONED`). Idée courante : chargement initial en provisionné avec forte capacité, puis retour à la demande ; la limite empêche de basculer à chaque heure.
- Usage : ✅ changer de mode quand le profil de trafic change durablement · ❌ basculer plusieurs fois par jour pour suivre la charge : auto scaling ou rester à la demande.

```hcl
# Exemple 1 : passer en provisionné
resource "aws_dynamodb_table" "progress" {
  name           = "${local.prefix}-progress"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5   # RCU, obligatoires
  write_capacity = 5   # WCU, obligatoires
  hash_key       = "pk"
  range_key      = "sk"
}
# plan : ~ update in-place
# (billing_mode ne force pas la recréation)
```

- Quiz : Et dans l'autre sens, de la demande vers provisionné : combien de fois par jour ?
- [ ] 4 fois aussi, même fenêtre de 24 h
- [ ] Une fois par jour
- [x] À tout moment, sans limite de ce type
- [ ] Une fois tous les 30 jours
- Réponse : à tout moment : selon la doc, seule la bascule provisionné → à la demande est limitée (4 fois par 24 h glissantes).

## 96. auto scaling : une cible d'utilisation
- Id : dynamodb-auto-scaling
- Sous-thème : capacité
- Type : concept
- Niveau : 2
- Profils : ops
- Source : data-platform · pwa-sync
- Définition : En mode provisionné, Application Auto Scaling ajuste RCU et WCU entre un minimum et un maximum pour viser un taux d'utilisation (20 à 90 %).
- Contexte : C'est un service à part (Application Auto Scaling), configuré par deux ressources Terraform : la cible (`min`, `max`) et la politique (`target_value`, 70 % recommandé par la doc). Il pilote des alarmes CloudWatch : selon la doc, il se déclenche après 2 minutes consécutives au-dessus de la cible, réduit après 15 points sous la cible, et la mise à jour prend plusieurs minutes. Il suit des tendances, pas des pics de secondes.
- Usage : ✅ trafic provisionné qui varie lentement (jour / nuit) · ❌ pics brefs et imprévisibles : mode à la demande.

```hcl
# Exemple 1 : écritures entre 5 et 100 WCU
resource "aws_appautoscaling_target" "w" {
  service_namespace  = "dynamodb"
  resource_id        = "table/${aws_dynamodb_table.progress.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  min_capacity       = 5
  max_capacity       = 100
}
resource "aws_appautoscaling_policy" "w" {
  name               = "progress-w"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.w.service_namespace
  resource_id        = aws_appautoscaling_target.w.resource_id
  scalable_dimension = aws_appautoscaling_target.w.scalable_dimension
  target_tracking_scaling_policy_configuration {
    target_value = 70   # %, entre 20 et 90
    predefined_metric_specification { predefined_metric_type = "DynamoDBWriteCapacityUtilization" }
  }
}
```

- Quiz : Table à 10 WCU, auto scaling actif ; pic de 30 secondes à 50 écritures/s. Que fait l'auto scaling ?
- [ ] Il monte à 50 WCU en quelques secondes
- [x] Rien à temps : le pic est fini avant qu'il réagisse
- [ ] Il bascule la table en mode à la demande
- [ ] Il met les écritures en file d'attente
- Réponse : rien à temps : il attend 2 minutes au-dessus de la cible puis met plusieurs minutes à appliquer ; le pic est absorbé par la burst capacity ou limité (throttling).

## 97. ignore_changes : capacité gérée par l'auto scaling
- Id : dynamodb-ignore-changes-autoscaling
- Sous-thème : capacité
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : dynamodb-auto-scaling
- Source : data-platform · pwa-sync
- Définition : Avec l'auto scaling (Application Auto Scaling) sur une table provisionnée, `lifecycle { ignore_changes = [read_capacity, write_capacity] }` empêche Terraform d'annuler ses ajustements.
- Contexte : L'auto scaling modifie la capacité de la table hors de Terraform. Sans `ignore_changes`, le plan suivant voit l'écart avec le `.tf` et remet la valeur écrite, en pleine charge. La doc du provider recommande donc d'ignorer ces deux attributs dès qu'une politique d'auto scaling est attachée. La valeur du `.tf` ne sert plus que de point de départ.
- Usage : ✅ `ignore_changes` sur les capacités pilotées par une politique `aws_appautoscaling_policy` · ❌ sur une table sans auto scaling : on ne verrait plus les modifications manuelles.

```hcl
# Exemple 1 : capacité laissée à l'auto scaling
resource "aws_dynamodb_table" "annonces" {
  billing_mode   = "PROVISIONED"
  read_capacity  = 5   # point de départ
  write_capacity = 5
  # ...
  lifecycle {
    ignore_changes = [read_capacity, write_capacity]
  }
}
```

- Quiz : Sans `ignore_changes`, l'auto scaling a monté `write_capacity` à 40 pendant l'ingestion. Que fait le `terraform apply` suivant ?
- [ ] Rien : Terraform lit la valeur courante
- [x] Il la remet à 5, la valeur du `.tf`
- [ ] Il écrit 40 dans le `.tf`
- [ ] Il échoue : conflit avec l'auto scaling
- Réponse : il remet 5 : Terraform ramène la ressource à sa configuration ; l'auto scaling remontera ensuite, après un épisode de limitation.

## 98. provisionné : à partir de quand c'est rentable
- Id : dynamodb-provisionne-rentable
- Sous-thème : capacité
- Type : choisir
- Niveau : 2
- Profils : ops
- Prérequis : dynamodb-prix-a-la-demande
- Source : data-platform · pwa-sync
- Définition : Le provisionné devient moins cher que la demande quand la capacité réservée est utilisée en moyenne à plus de 29 % environ (prix us-east-1).
- Contexte : Prix us-east-1 (aws.amazon.com/dynamodb/pricing, octobre 2026) : 0,00065 $ par WCU-heure ; à la demande, 1 écriture/s pendant une heure = 3 600 unités à 0,625 $ le million. Le provisionné se paie même à vide : sous 29 % d'utilisation, la demande gagne. La capacité réservée (blocs de 100 WCU ou RCU, 1 ou 3 ans, jusqu'à 54 % ou 77 % de remise selon la page de prix) baisse encore le seuil, contre un engagement.
- Usage : ✅ trafic stable et mesuré (métrique `ConsumedWriteCapacityUnits`) au-dessus du seuil · ❌ dev, trafic inconnu ou en rafales : à la demande.

```python
# Exemple 1 : 1 écriture/s pendant 1 h
provisionne = 0.00065          # 1 WCU-heure
a_la_demande = 3600 * 0.625 / 1e6
round(a_la_demande, 5)  # → 0.00225
round(provisionne / a_la_demande, 2)  # → 0.29
# rentable si utilisation moyenne > 29 %
```

- Quiz : La capacité réservée (engagement d'un an) s'applique-t-elle à une table `PAY_PER_REQUEST` ?
- [ ] Oui, en remise sur chaque million de requêtes
- [x] Non : elle porte sur des WCU et RCU provisionnées
- [ ] Oui, si la table dépasse 100 requêtes/s
- [ ] Seulement pour les lectures
- Réponse : non : selon la page de prix, la capacité réservée s'achète en blocs de 100 WCU ou RCU, des unités du mode provisionné.

## 99. botocore : les réessais automatiques
- Id : dynamodb-reessais-botocore
- Sous-thème : capacité
- Type : concept
- Niveau : 2
- Profils : ops, data
- Prérequis : dynamodb-throttling-exceptions
- Source : data-platform · pwa-sync
- Définition : boto3 réessaie seul le throttling et les erreurs 5xx ; pour DynamoDB, le mode par défaut `legacy` va jusqu'à 10 tentatives à délai exponentiel.
- Contexte : Mesuré dans botocore 1.43 (`data/_retry.json`) : section `dynamodb`, `max_attempts` 10, base 0,05 s, facteur 2. Le guide boto3 donne 5 tentatives par défaut (legacy, autres services) et 3 en mode `standard`. On règle par `Config(retries=…)`. Une Lambda courte peut préférer moins d'essais et rendre la main ; `UnprocessedItems` d'un lot, elles, ne sont jamais réessayées par botocore.
- Usage : ✅ `Config(retries={"mode": "standard", "total_max_attempts": 5})` explicite · ❌ empiler sa propre boucle de réessais sur le throttling par-dessus celle du SDK.

```python
# Exemple 1 : le mode par défaut (mesuré)
import boto3
c = boto3.client("dynamodb", region_name="eu-west-3")
c.meta.config.retries  # → {'mode': 'legacy'}
```

```python
# Exemple 2 : DynamoDB, 10 tentatives
import json, pathlib, botocore
p = pathlib.Path(botocore.__file__).parent
d = json.loads((p / "data/_retry.json").read_text())
d["retry"]["dynamodb"]["__default__"]["max_attempts"]  # → 10
```

- Quiz : `Config(retries={"max_attempts": 3})` : combien de requêtes au plus pour un appel limité ?
- [ ] 3 en tout
- [x] 4 : l'appel initial plus 3 réessais
- [ ] 10 : la valeur DynamoDB prime
- [ ] 1 : `max_attempts` désactive les réessais
- Réponse : 4 : selon le guide boto3, dans un objet `Config`, `max_attempts` compte les réessais sans l'appel initial ; `total_max_attempts` compte le total.

## 100. burst capacity : 300 secondes en réserve
- Id : dynamodb-burst-capacity
- Sous-thème : capacité
- Type : concept
- Niveau : 2
- Profils : ops, expert
- Source : data-platform · pwa-sync
- Définition : DynamoDB garde jusqu'à 300 secondes de capacité provisionnée inutilisée et la dépense lors d'un pic bref, au-delà du débit par seconde.
- Contexte : Selon la doc (burst and adaptive capacity), cette réserve n'est pas garantie : DynamoDB peut la consommer pour sa maintenance, et les détails peuvent changer. C'est elle qui absorbe les pics de quelques secondes que l'auto scaling ne voit pas. Ne pas dimensionner sur elle : un pic régulier la vide et le throttling revient.
- Usage : ✅ expliquer pourquoi un pic bref passe sans throttling · ❌ compter dessus pour un traitement batch quotidien : provisionner ou passer à la demande.

```python
# Exemple 1 : réserve d'une table à 10 WCU
wcu = 10
reserve_max = wcu * 300
reserve_max  # → 3000  (unités d'écriture)
# pic à 30 écritures/s : 20 de plus par s
reserve_max // (30 - wcu)  # → 150  (secondes tenues)
```

- Quiz : Table à 10 WCU restée inactive une heure. Quelle réserve au plus pour le pic suivant ?
- [ ] 36 000 unités : 3 600 s × 10
- [x] 3 000 unités : 300 s × 10
- [ ] 600 unités : 60 s × 10
- [ ] Aucune : la réserve expire après 5 minutes
- Réponse : 3 000 : la réserve est plafonnée à 300 secondes de capacité inutilisée, quelle que soit la durée d'inactivité.

## 101. Streams : quatre vues
- Id : dynamodb-streams-vues
- Sous-thème : exploitation
- Type : concept
- Niveau : 2
- Profils : data, web
- Source : data-platform · pwa-sync
- Définition : Un flux DynamoDB Streams publie chaque modification d'item ; sa vue fixe le contenu : `KEYS_ONLY`, `NEW_IMAGE`, `OLD_IMAGE` ou `NEW_AND_OLD_IMAGES`.
- Contexte : Chaque enregistrement porte `eventName` (`INSERT`, `MODIFY`, `REMOVE`) et les clés ; les images dépendent de la vue. Avec `NEW_AND_OLD_IMAGES`, un `INSERT` n'a pas d'`OldImage` et un `REMOVE` pas de `NewImage` (mesuré avec moto). Le flux est asynchrone : aucun impact sur la latence de la table (doc). On lit par un client séparé, `dynamodbstreams`, ou par un event source mapping Lambda.
- Usage : ✅ `NEW_AND_OLD_IMAGES` pour un audit ou un calcul de différence, `KEYS_ONLY` pour un simple signal · ❌ vue complète par défaut si le consommateur ne lit que la clé.

```python
# Exemple 1 : put puis delete (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
c = boto3.client("dynamodb", region_name="eu-west-3")
c.create_table(TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
  StreamSpecification={"StreamEnabled": True, "StreamViewType": "NEW_AND_OLD_IMAGES"})
k = {"pk": {"S": "u1"}}
c.put_item(TableName="progress", Item=k)
c.delete_item(TableName="progress", Key=k)
arn = c.describe_table(TableName="progress")["Table"]["LatestStreamArn"]
s = boto3.client("dynamodbstreams", region_name="eu-west-3")
sh = s.describe_stream(StreamArn=arn)["StreamDescription"]["Shards"][0]
it = s.get_shard_iterator(StreamArn=arn, ShardId=sh["ShardId"],
  ShardIteratorType="TRIM_HORIZON")["ShardIterator"]
[(r["eventName"], "OldImage" in r["dynamodb"]) for r in s.get_records(ShardIterator=it)["Records"]]  # → [('INSERT', False), ('REMOVE', True)]
m.stop()
```

- Quiz : Le flux est en `KEYS_ONLY` ; on veut passer à `NEW_IMAGE`. Comment ?
- [ ] `UpdateTable` avec la nouvelle vue, le flux garde son ARN
- [x] Désactiver le flux puis en créer un nouveau (nouvel ARN)
- [ ] Impossible : il faut recréer la table
- [ ] Changer la vue dans l'event source mapping Lambda
- Réponse : désactiver puis réactiver : la doc interdit de modifier la vue d'un flux existant ; le nouveau flux a un autre ARN, à rebrancher sur les consommateurs.

## 102. sauvegarde à la demande : gardée jusqu'à suppression
- Id : dynamodb-sauvegarde-a-la-demande
- Sous-thème : exploitation
- Type : concept
- Niveau : 2
- Profils : ops
- Voir aussi : dynamodb-pitr-restauration
- Source : data-platform · pwa-sync
- Définition : `CreateBackup` prend un instantané complet de la table, conservé jusqu'à ce qu'on le supprime, sans impact sur ses performances.
- Contexte : Contrairement au PITR (fenêtre glissante de 35 jours au plus), une sauvegarde à la demande sert à l'archivage long : avant une migration, pour une exigence réglementaire. Elle est facturée au Go et au mois de conservation. La restauration crée toujours une nouvelle table. La sauvegarde survit à la suppression de la table (mesuré avec moto). AWS Backup sait aussi les planifier.
- Usage : ✅ instantané nommé avant une migration de schéma, archivage long · ❌ protection contre une erreur d'hier : le PITR rejoue à la seconde.

```python
# Exemple 1 : sauvegarde, puis table supprimée (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
c = boto3.client("dynamodb", region_name="eu-west-3")
c.create_table(TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk",
    "AttributeType": "S"}])
b = c.create_backup(TableName="progress",
  BackupName="avant-migration-v2")["BackupDetails"]
b["BackupStatus"]  # → 'AVAILABLE'
c.delete_table(TableName="progress")
[x["BackupName"] for x in c.list_backups()["BackupSummaries"]]
# → ['avant-migration-v2']
m.stop()
```

- Quiz : La table `progress` existe encore. `RestoreTableFromBackup` avec `TargetTableName="progress"` ?
- [ ] Les items sont remis à l'état de la sauvegarde
- [ ] Les items absents sont ajoutés, les autres gardés
- [x] `TableAlreadyExistsException`
- [ ] La table est renommée `progress-1`
- Réponse : `TableAlreadyExistsException` (mesuré avec moto) : une restauration crée toujours une nouvelle table ; on restaure sous un autre nom, puis on rebranche l'app.

## 103. export vers S3 : PITR requis, zéro RCU
- Id : dynamodb-export-s3
- Sous-thème : exploitation
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : dynamodb-pitr-restauration
- Voir aussi : dynamodb-import-s3
- Source : data-platform · pwa-sync
- Définition : `ExportTableToPointInTime` écrit la table dans S3 (DynamoDB JSON ou Ion), à un instant de la fenêtre PITR, sans consommer de capacité de lecture.
- Contexte : L'export lit les sauvegardes continues, pas la table : aucune RCU, aucun impact sur l'app (doc). D'où le prérequis : PITR actif, sinon `PointInTimeRecoveryUnavailableException`. Il est asynchrone, facturé au Go de la table. Un export incrémental (15 min à 24 h) ne sort que les changements de la période, compactés au dernier état. Ensuite Athena ou Glue lisent les fichiers : c'est la voie analytique propre.
- Usage : ✅ alimenter le data lake, analyses Athena sur la table · ❌ `Scan` paginé dans un script pour exporter : RCU consommées, code à maintenir.

```python
# Exemple 1 : sans PITR, refusé (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
c = boto3.client("dynamodb", region_name="eu-west-3")
arn = c.create_table(TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}]
  )["TableDescription"]["TableArn"]
boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="exports")
exp = dict(TableArn=arn, S3Bucket="exports",
  S3Prefix="progress/", ExportFormat="DYNAMODB_JSON")
c.export_table_to_point_in_time(**exp)  # ❌ PointInTimeRecoveryUnavailableException
c.update_continuous_backups(TableName="progress",
  PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True})
d = c.export_table_to_point_in_time(**exp)
"ExportArn" in d["ExportDescription"]  # → True (suivi : describe_export)
m.stop()
```

- Quiz : Table à la demande de 10 Go, export complet à 9 h, en plein trafic. Combien de RCU l'export consomme-t-il ?
- [ ] 10 Go de lecture, comme un `Scan`
- [ ] La moitié : lectures à cohérence éventuelle
- [x] Aucune : l'export lit les sauvegardes continues
- [ ] Aucune, mais l'app est ralentie pendant l'export
- Réponse : aucune : l'export lit les données du PITR, pas la table ; il est facturé au Go exporté, sans effet sur les performances (doc).

## 104. DAX : cache en mémoire devant DynamoDB
- Id : dynamodb-dax-cache
- Sous-thème : exploitation
- Type : concept
- Niveau : 2
- Profils : web, expert
- Voir aussi : dynamodb-cache-elasticache
- Source : data-platform · pwa-sync
- Définition : DAX est un cache en mémoire compatible avec l'API DynamoDB, qui ramène les lectures éventuellement cohérentes de quelques millisecondes à des microsecondes.
- Contexte : C'est un cluster à démarrer dans un VPC, payé à l'heure par nœud, avec son propre client SDK. Il écrit en write-through vers la table. Il est utile pour des lectures répétées sur les mêmes clés (taux de succès > 90 %, doc), pas pour une charge d'écriture lourde. Le cache des `Query` n'est pas invalidé par les écritures : il attend son TTL. Une app Lambda à faible trafic n'en a aucun besoin.
- Usage : ✅ clé chaude lue des milliers de fois par seconde, latence en µs exigée · ❌ faible trafic, écritures massives, lecture forte exigée : DynamoDB seul.

```
# Exemple 1 : la décision
Besoin : fiche SIREN lue 50 000 fois/s
         pendant une campagne, < 1 ms
→ DAX : même API, item cache en µs
Besoin : pwa-sync, 10 requêtes/session
→ pas de DAX : quelques ms suffisent,
  et un cluster tournerait 24 h/24
```

- Quiz : Via le client DAX, `GetItem(..., ConsistentRead=True)`. Que se passe-t-il ?
- [ ] DAX sert l'item depuis son cache
- [x] DAX transmet à DynamoDB et ne met pas en cache
- [ ] `ValidationException` : non supporté par DAX
- [ ] DAX vide son cache puis relit l'item
- Réponse : transmis sans cache : DAX ne sert que des lectures éventuellement cohérentes ; une lecture forte va à la table et son résultat n'est pas stocké (doc).

## 105. global tables : le dernier écrivain gagne
- Id : dynamodb-global-tables-mrec
- Sous-thème : exploitation
- Type : concept
- Niveau : 2
- Profils : ops, expert
- Source : data-platform · pwa-sync
- Définition : Une global table réplique une table dans plusieurs régions, toutes lisibles et écrivables ; en cas de conflit sur un item, la dernière écriture gagne.
- Contexte : Mode par défaut (MREC, version 2019.11.21) : réplication asynchrone, en général en moins d'une seconde (doc). Deux régions qui écrivent le même item en même temps : DynamoDB garde celle de l'horodatage interne le plus récent, l'autre est perdue sans erreur. Les flux sont actifs d'office sur les réplicas. SLA 99,999 % contre 99,99 % pour une table d'une région.
- Usage : ✅ app multi-région avec bascule, lectures proches des utilisateurs · ❌ app d'une seule région : coût de réplication pour rien ; compteur écrit partout : conflits perdus.

```python
# Exemple 1 : last writer wins, simulé
ecritures = [
  {"region": "eu-west-3", "ts": 10.2, "vues": 5},
  {"region": "eu-central-1", "ts": 10.1, "vues": 7},
]
gagnant = max(ecritures, key=lambda e: e["ts"])
gagnant["vues"]  # → 5   (partout, à terme)
```

- Quiz : MREC, `TransactWriteItems` de 2 items à Paris. Que peut voir un lecteur à Francfort ?
- [ ] Les deux ou aucun : la transaction est répliquée d'un bloc
- [x] Un seul des deux items, pendant la réplication
- [ ] Rien : les transactions sont refusées sur une global table
- [ ] Les deux, avant même la fin à Paris
- Réponse : un seul des deux, un temps : en MREC, une transaction n'est atomique que dans sa région ; les écritures se répliquent séparément (doc).

## 106. deletion_protection_enabled : bloquer la suppression
- Id : dynamodb-protection-suppression
- Sous-thème : exploitation
- Type : concept
- Niveau : 2
- Profils : ops
- Voir aussi : dynamodb-pitr-restauration
- Source : data-platform · pwa-sync
- Définition : `deletion_protection_enabled = true` fait refuser `DeleteTable` par DynamoDB, que la demande vienne de Terraform, de la console ou de la CLI.
- Contexte : En dev, la table doit pouvoir disparaître avec `make down` ; en prod, une suppression par erreur serait définitive, données comprises. La protection se lève par une mise à jour de la table (un apply qui la passe à `false`), après quoi la suppression redevient possible. D'où `var.environment == "prod"` : un code, deux comportements.
- Usage : ✅ en prod, dès qu'une table contient des données d'utilisateurs · ❌ en dev : `make down` bloqué sans intérêt.

```hcl
# Exemple 1 : prod protégée, dev jetable
resource "aws_dynamodb_table" "progress" {
  # …
  deletion_protection_enabled = (
    var.environment == "prod")
}
```

- Quiz : En prod, `terraform destroy` sur la table protégée. Résultat ?
- [ ] Table supprimée, restaurable par PITR
- [x] Erreur AWS : protection contre la suppression active
- [ ] Terraform ignore la table et continue
- [ ] Table vidée mais conservée
- Réponse : erreur : DynamoDB refuse `DeleteTable` tant que la protection est active ; il faut d'abord la désactiver (un apply).

## 107. point_in_time_recovery : restaurer à la seconde
- Id : dynamodb-pitr-restauration
- Sous-thème : exploitation
- Type : concept
- Niveau : 2
- Profils : ops
- Source : data-platform · pwa-sync
- Définition : `point_in_time_recovery` garde un historique continu de la table : on la restaure à n'importe quelle seconde des 35 derniers jours (par défaut).
- Contexte : Il protège d'une erreur de données (script qui écrase ou supprime des items), pas seulement de la suppression de la table. La restauration crée toujours une **nouvelle** table, à rebrancher ou à relire pour recopier ; l'originale reste en place. Facturé au Go de la table. En dev, inutile : `enabled = var.environment == "prod"`.
- Usage : ✅ toute table de prod dont les données ne se regénèrent pas · ❌ archivage long ou instantané avant migration : sauvegarde à la demande.

```hcl
# Exemple 1 : PITR en prod seulement
resource "aws_dynamodb_table" "progress" {
  # …
  point_in_time_recovery {
    enabled = var.environment == "prod"
  }
}
```

- Quiz : Un script a écrasé 1 000 items à 14 h 05. Comment retrouver l'état de 14 h 04 ?
- [ ] Restaurer `progress` sur place, à 14 h 04
- [x] Restaurer à 14 h 04 dans une nouvelle table, puis recopier
- [ ] Rejouer le flux DynamoDB Streams à l'envers
- [ ] Impossible : le PITR ne couvre que la suppression de la table
- Réponse : une nouvelle table : `RestoreTableToPointInTime` ne restaure jamais sur place ; on relit les 1 000 items dans la table restaurée pour les recopier, ou on rebranche l'app dessus.

## 108. stream_view_type : détecter un changement
- Id : dynamodb-stream-terraform
- Sous-thème : exploitation
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : dynamodb-streams-vues
- Source : data-platform · pwa-sync
- Définition : `stream_enabled = true` publie chaque modification d'item dans un flux (Streams) ; `stream_view_type` choisit le contenu : `KEYS_ONLY`, `NEW_IMAGE`, `OLD_IMAGE`, `NEW_AND_OLD_IMAGES`.
- Contexte : Les enregistrements sont gardés 24 h, dans l'ordre des modifications de chaque item, sans effet sur les performances de la table. Selon la doc, le type de vue ne se modifie pas sur un flux existant : il faut le désactiver puis en créer un nouveau (nouvel ARN, `stream_arn`). `stream_view_type` sans `stream_enabled` échoue au `validate` (mesuré). Un `PutItem` qui ne change rien n'émet aucun enregistrement.
- Usage : ✅ déclencher une Lambda sur les changements, choisir la vue la plus étroite suffisante · ❌ `NEW_AND_OLD_IMAGES` par défaut quand la clé suffit.

```hcl
# Exemple 1 : seulement les clés modifiées
stream_enabled   = true
stream_view_type = "KEYS_ONLY"
# sortie utile : aws_dynamodb_table.x.stream_arn
```

- Quiz : Une Lambda doit alerter quand le `statut` d'une procédure **change** (ancien → nouveau). Quel `stream_view_type` ?
- [ ] `KEYS_ONLY`, puis un `GetItem`
- [ ] `NEW_IMAGE`
- [x] `NEW_AND_OLD_IMAGES`
- [ ] `OLD_IMAGE`
- Réponse : `NEW_AND_OLD_IMAGES` : seul ce type contient l'avant et l'après ; un `GetItem` ne lit que l'état actuel, l'ancien est perdu.

## 109. TTL : expiré mais encore lu
- Id : dynamodb-ttl-expire-encore-lu
- Sous-thème : exploitation
- Type : piège
- Niveau : 2
- Profils : web, data
- Prérequis : dynamodb-ttl-epoch-secondes
- Voir aussi : dynamodb-filterexpression-apres-lecture
- Source : data-platform · pwa-sync
- Définition : Un item expiré reste lisible tant que le TTL ne l'a pas supprimé, en général sous quelques jours : les lectures doivent le filtrer.
- Contexte : La suppression est un processus de fond, sans délai garanti (doc : « typically within a few days »). Entre-temps, `GetItem`, `Query` et `Scan` renvoient l'item, qui compte encore dans le stockage et les lectures facturées. On ajoute donc `expire_at > :now` en `FilterExpression`. La suppression elle-même est gratuite : aucune WCU. moto ne supprime jamais : l'exemple montre l'état « expiré, pas encore supprimé ».
- Usage : ✅ filtre `expire_at > now` sur toute lecture de données à durée de vie · ❌ se fier au TTL pour une règle métier à la minute (session expirée) : vérifier la date à la lecture.

```python
# Exemple 1 : expiré, toujours là (moto)
import boto3
from boto3.dynamodb.conditions import Attr, Key
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a,
    "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a,
    "AttributeType": "S"} for a in K])
now = 1792886400  # 2026-10-25
t.put_item(Item={"pk": "u1", "sk": "S#1", "expire_at": now - 3600})
t.put_item(Item={"pk": "u1", "sk": "S#2", "expire_at": now + 3600})
r = t.query(KeyConditionExpression=Key("pk").eq("u1"), FilterExpression=Attr("expire_at").gt(now))
[i["sk"] for i in r["Items"]]  # → ['S#2']
m.stop()
```

- Quiz : Un item a expiré hier, pas encore supprimé. On le met à jour avec `expire_at` dans un mois. Résultat ?
- [ ] Supprimé quand même : il était déjà marqué
- [x] Gardé : il n'est plus considéré comme expiré
- [ ] `ConditionalCheckFailedException`
- [ ] Mis à jour, puis supprimé au prochain passage
- Réponse : gardé : selon la doc, un item expiré reste modifiable avant suppression ; une date future le retire du TTL (d'où une condition `expire_at > :now` conseillée).

## 110. TTL dans le flux : userIdentity
- Id : dynamodb-ttl-dans-le-flux
- Sous-thème : exploitation
- Type : concept
- Niveau : 2
- Profils : data, expert
- Prérequis : dynamodb-ttl-epoch-secondes, dynamodb-streams-vues
- Source : data-platform · pwa-sync
- Définition : Une suppression par le TTL arrive dans le flux comme un `REMOVE` portant `userIdentity` : `type` = `Service`, `principalId` = `dynamodb.amazonaws.com`.
- Contexte : C'est ce qui distingue une expiration d'un effacement voulu. Usage type : flux + Lambda qui archive les items expirés dans S3, avec un filtre d'event source mapping sur `userIdentity` pour n'invoquer la fonction que pour eux. Selon la doc, la suppression TTL ne consomme pas de WCU ; en global table, le `userIdentity` n'est présent que dans la région où le TTL a agi.
- Usage : ✅ archiver ou compter les expirations sans invoquer Lambda pour chaque écriture · ❌ traiter tout `REMOVE` comme une expiration : confond avec les suppressions de l'app.

```json
# Exemple 1 : filtre de l'event source mapping
{"Filters": [{"Pattern":
  "{\"userIdentity\":{\"type\":[\"Service\"],
   \"principalId\":[\"dynamodb.amazonaws.com\"]}}"}]}
# → Lambda invoquée pour les seuls TTL
```

```python
# Exemple 2 : trier dans le handler
def est_ttl(rec):
    u = rec.get("userIdentity", {})
    return (u.get("type") == "Service" and
        u.get("principalId") == "dynamodb.amazonaws.com")

ttl = {"eventName": "REMOVE", "userIdentity": {
  "type": "Service", "principalId": "dynamodb.amazonaws.com"}}
est_ttl(ttl)  # → True
```

- Quiz : L'app fait `DeleteItem` sur un item. Que contient `userIdentity` dans l'enregistrement ?
- [ ] `type` = `User` et l'ARN du rôle appelant
- [ ] `type` = `Service`, comme le TTL
- [x] Rien : le champ est absent
- [ ] `principalId` = l'identité Cognito
- Réponse : absent (mesuré avec moto, conforme à la doc) : seul le TTL renseigne `userIdentity` ; l'appelant d'un `DeleteItem` se trouve dans CloudTrail, pas dans le flux.

## 111. PITR : restaurer sans les réglages
- Id : dynamodb-pitr-reglages-perdus
- Sous-thème : exploitation
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : dynamodb-pitr-restauration
- Source : data-platform · pwa-sync
- Définition : Une restauration PITR crée une nouvelle table avec données, index et chiffrement, mais sans TTL, flux, alarmes, auto scaling, tags ni PITR.
- Contexte : La table source reste disponible pendant la restauration, dont la durée dépend du volume et du nombre d'index (exclure des index l'accélère). Après coup, tout ce qui vit autour de la table est à reposer : c'est le travail de Terraform (importer la table restaurée ou la recopier). Oublier le TTL fait grossir la table ; oublier le PITR la laisse sans filet. On peut aussi restaurer dans une autre région.
- Usage : ✅ une procédure écrite : restaurer, réappliquer TTL, flux, PITR, tags, alarmes, puis basculer · ❌ croire qu'une restauration rend une table prête pour la prod.

```python
# Exemple 1 : TTL et PITR perdus (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
c = boto3.client("dynamodb", region_name="eu-west-3")
c.create_table(TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
c.update_continuous_backups(TableName="progress",
  PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True})
c.update_time_to_live(TableName="progress", TimeToLiveSpecification={
  "Enabled": True, "AttributeName": "expire_at"})
c.restore_table_to_point_in_time(SourceTableName="progress",
  TargetTableName="progress-restore", UseLatestRestorableTime=True)
ttl = c.describe_time_to_live(TableName="progress-restore")
ttl["TimeToLiveDescription"]["TimeToLiveStatus"]  # → 'DISABLED'
cb = c.describe_continuous_backups(TableName="progress-restore")
cb["ContinuousBackupsDescription"]["PointInTimeRecoveryDescription"]["PointInTimeRecoveryStatus"]  # → 'DISABLED'
m.stop()
```

- Quiz : Lequel de ces éléments la restauration PITR remet-elle sur la nouvelle table ?
- [ ] Les alarmes CloudWatch
- [ ] La règle d'auto scaling
- [x] Les index secondaires globaux
- [ ] Les tags de coût
- Réponse : les index secondaires globaux : la doc liste données, GSI, LSI, capacité provisionnée et chiffrement ; alarmes, auto scaling et tags sont à recréer.

## 112. PITR : fenêtre de 1 à 35 jours, même prix
- Id : dynamodb-pitr-fenetre
- Sous-thème : exploitation
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : dynamodb-pitr-restauration
- Source : data-platform · pwa-sync
- Définition : `RecoveryPeriodInDays` règle la fenêtre du PITR, de 1 à 35 jours (35 par défaut) ; le prix dépend seulement de la taille de la table.
- Contexte : Le point le plus récent restaurable est environ 5 minutes avant maintenant. Réduire la fenêtre efface tout de suite les points plus anciens ; l'augmenter ne les fait pas revenir, la fenêtre se remplit avec le temps. Supprimer une table avec PITR crée une sauvegarde système `<table>$DeletedTableBackup` gardée 35 jours, sans frais (doc). Côté Terraform : `recovery_period_in_days` dans `point_in_time_recovery`.
- Usage : ✅ fenêtre courte si une règle impose de ne pas garder les données au-delà · ❌ la réduire pour payer moins : aucun effet sur la facture.

```python
# Exemple 1 : fenêtre de 7 jours (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
c = boto3.client("dynamodb", region_name="eu-west-3")
c.create_table(TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
spec = {"PointInTimeRecoveryEnabled": True,
        "RecoveryPeriodInDays": 7}
c.update_continuous_backups(TableName="progress",
  PointInTimeRecoverySpecification=spec)
d = c.describe_continuous_backups(TableName="progress")
d["ContinuousBackupsDescription"]["PointInTimeRecoveryDescription"]["RecoveryPeriodInDays"]
# → 7
spec["RecoveryPeriodInDays"] = 0
c.update_continuous_backups(TableName="progress", PointInTimeRecoverySpecification=spec)  # ❌ ParamValidationError
m.stop()
```

- Quiz : Table de 20 Go, on passe la fenêtre PITR de 35 à 7 jours. Effet sur la facture PITR ?
- [ ] Divisée par 5, comme la fenêtre
- [x] Aucun : le PITR est facturé au Go de la table
- [ ] Baisse de moitié : seuls les deltas sont gardés
- [ ] Hausse : une fenêtre personnalisée est une option
- Réponse : aucun : selon la doc, le prix ne dépend que de la taille de la table (données + LSI), quelle que soit la fenêtre.

## 113. Streams + Lambda : un item empoisonné
- Id : dynamodb-streams-item-empoisonne
- Sous-thème : exploitation
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : dynamodb-streams-vues, lambda-event-source-mapping
- Voir aussi : sqs-eventbridge-echec-partiel-lot
- Source : data-platform · pwa-sync
- Définition : Sur un flux DynamoDB, une erreur de la fonction rejoue tout le lot ; sans réglage, le shard reste bloqué jusqu'à expiration (24 h).
- Contexte : Par défaut, `MaximumRetryAttempts` et `MaximumRecordAgeInSeconds` valent -1 (infini, jusqu'à expiration du flux). On borne les retries, on active `BisectBatchOnFunctionError` (coupe le lot en deux pour isoler l'item fautif, sans compter de retry) et une destination en cas d'échec (SQS, SNS, S3). `ReportBatchItemFailures` permet de ne rejouer que depuis l'item en échec. Lambda traite au moins une fois : handler idempotent.
- Usage : ✅ retries bornés, bisect et destination d'échec sur tout mapping de flux · ❌ réglages par défaut : un seul item invalide gèle le shard un jour.

```hcl
# Exemple 1 : mapping défensif
resource "aws_lambda_event_source_mapping" "s" {
  event_source_arn  = aws_dynamodb_table.progress.stream_arn
  function_name     = aws_lambda_function.archive.arn
  starting_position = "TRIM_HORIZON"
  batch_size        = 100
  maximum_retry_attempts         = 3
  maximum_record_age_in_seconds  = 3600
  bisect_batch_on_function_error = true
  function_response_types = ["ReportBatchItemFailures"]
  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.echecs.arn
    }
  }
}
```

- Quiz : Après 3 échecs, le lot part vers la file SQS d'échec. Que contient le message ?
- [ ] Les enregistrements complets du lot
- [x] Des métadonnées : shard, numéros de séquence, ARN
- [ ] Seulement les clés des items fautifs
- [ ] L'exception levée et sa trace
- Réponse : des métadonnées : pour SQS et SNS, pas les enregistrements (seule une destination S3 reçoit le lot) ; il faut les relire dans le flux avant 24 h (doc).

## 114. Streams : ordre par item, 24 h
- Id : dynamodb-streams-ordre-24h
- Sous-thème : exploitation
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : dynamodb-streams-vues
- Source : data-platform · pwa-sync
- Définition : Un flux DynamoDB garde 24 h de modifications, chacune une seule fois, dans l'ordre réel pour un même item, sans ordre garanti entre items.
- Contexte : Les enregistrements vivent dans des shards (un par partition de la table) ; deux items peuvent tomber dans deux shards lus en parallèle. Au-delà de 24 h, ils disparaissent : un consommateur arrêté plus d'un jour perd des données. La doc recommande au plus deux lecteurs simultanés par shard (un seul pour une global table), sinon throttling. Une écriture qui ne change rien ne produit pas d'enregistrement (doc ; moto en produit un).
- Usage : ✅ logique par item (dernier état d'une carte), consommateur supervisé (`IteratorAge`) · ❌ supposer un ordre global entre utilisateurs ; brancher trois Lambdas sur le même flux.

```python
# Exemple 1 : ordre par item, pas global
shard_a = [("u1", "MODIFY", 1), ("u1", "MODIFY", 3)]
shard_b = [("u2", "INSERT", 2)]
# lus en parallèle : u2 peut arriver avant u1
vu = shard_b + shard_a
[e[2] for e in vu if e[0] == "u1"]  # → [1, 3]
[e[2] for e in vu]  # → [2, 1, 3]
```

- Quiz : Trois Lambdas différentes branchées sur le même flux d'une table d'une région. Risque ?
- [ ] Aucun : chaque mapping a son propre flux
- [ ] Chaque enregistrement n'est livré qu'à une seule des trois
- [x] Throttling des lectures du shard
- [ ] L'ordre par item est perdu
- Réponse : throttling : la doc conseille deux lecteurs simultanés par shard au plus ; au-delà, passer par Kinesis Data Streams (fan-out) ou une seule Lambda qui répartit.

## 115. import depuis S3 : une nouvelle table
- Id : dynamodb-import-s3
- Sous-thème : exploitation
- Type : recette
- Niveau : 2
- Profils : data
- Voir aussi : dynamodb-export-s3
- Source : data-platform · pwa-sync
- Définition : `ImportTable` charge des fichiers S3 (CSV, DynamoDB JSON ou Ion, gzip ou zstd possibles) dans une table qu'il crée, sans consommer de capacité d'écriture.
- Contexte : Pas d'import dans une table existante : la table naît avec l'import (GSI possibles, pas de LSI). Facturé au Go non compressé de la source, y compris les lignes rejetées. Plus rapide et moins cher qu'un `BatchWriteItem` en boucle pour un chargement initial. Les clés doivent être uniques : sinon la dernière écrase les autres. CloudTrail trace l'opération.
- Usage : ✅ chargement initial d'une table (historique SIREN), migration depuis un export · ❌ alimenter chaque jour une table déjà en service : écritures classiques.

```bash
# Exemple 1 : import d'un CSV gzip
aws dynamodb import-table \
  --s3-bucket-source S3Bucket=$PROCESSED,KeyPrefix=sirens/ \
  --input-format CSV \
  --input-compression-type GZIP \
  --table-creation-parameters '{
    "TableName": "data-platform-dev-sirens",
    "BillingMode": "PAY_PER_REQUEST",
    "KeySchema": [{"AttributeName": "siren", "KeyType": "HASH"}],
    "AttributeDefinitions": [{"AttributeName": "siren",
      "AttributeType": "S"}]}'
# → ImportTableDescription.ImportStatus: IN_PROGRESS
```

- Quiz : Le CSV a 1 000 lignes ; 10 d'entre elles répètent un SIREN déjà présent. Combien d'items ?
- [ ] 1 000 : un item par ligne
- [x] 990 : chaque doublon écrase le précédent
- [ ] 0 : l'import échoue sur la clé dupliquée
- [ ] 980 : les doublons sont rejetés tous les deux
- Réponse : 990 : selon la doc, une clé répétée écrase l'item précédent ; le nombre traité (1 000) ne correspond plus au nombre d'items.

## 116. Standard-IA : quand le stockage domine
- Id : dynamodb-standard-ia
- Sous-thème : exploitation
- Type : choisir
- Niveau : 2
- Profils : ops
- Voir aussi : s3-classe-de-stockage
- Source : data-platform · pwa-sync
- Définition : La classe Standard-IA réduit le prix du Go stocké mais renchérit lectures et écritures : rentable quand le stockage domine la facture.
- Contexte : us-east-1 (doc de prix) : stockage 0,25 → 0,10 $/Go-mois (−60 %), mais écritures 0,625 → 0,78 $ et lectures 0,125 → 0,155 $ par million (≈ +25 %). Seuil de la doc : quand le stockage dépasse 50 % du coût débit en Standard. Même API, mêmes performances, TTL et PITR compris. Au plus deux changements de classe par 30 jours glissants.
- Usage : ✅ historique rarement lu (annonces BODACC anciennes, journaux) · ❌ table petite et très sollicitée : Standard, moins chère au débit.

```python
# Exemple 1 : 100 Go, 10 M écritures, 50 M lectures
go, w, r = 100, 10, 50     # par mois
std = go*0.25 + w*0.625 + r*0.125
ia  = go*0.10 + w*0.78  + r*0.155
round(std, 2), round(ia, 2)  # → (37.5, 25.55)
stock = go*0.25; debit = w*0.625 + r*0.125
stock > 0.5 * debit  # → True  (IA rentable)
```

- Quiz : Table pwa-sync : 1 Go, 100 millions de lectures par mois. Quelle classe ?
- [x] Standard : le débit domine largement
- [ ] Standard-IA : 60 % d'économie sur le stockage
- [ ] Standard-IA : moins chère dès 1 Go
- [ ] Indifférent : même prix total
- Réponse : Standard : 0,25 $ de stockage contre 12,50 $ de lectures ; en IA, on gagnerait 0,15 $ et paierait 3 $ de plus.

## 117. ARN d'index : Query sur un GSI
- Id : dynamodb-iam-arn-index
- Sous-thème : sécurité
- Type : piège
- Niveau : 2
- Profils : ops, web
- Prérequis : dynamodb-gsi-autre-cle
- Voir aussi : iam-jokers-actions-arn
- Source : data-platform · pwa-sync
- Définition : Un index secondaire a son propre ARN, `…:table/<table>/index/<index>` : l'accorder en plus de la table pour lire par l'index.
- Contexte : Une `Query` avec `IndexName` vise la ressource index, pas la table : une politique qui ne nomme que `table/progress` la refuse (`AccessDeniedException`). L'exemple officiel de la doc (« table et ses index ») liste les deux ARN. Côté TS, rien ne change dans `QueryCommand` : seul le rôle IAM est en cause, d'où la surprise après l'ajout d'un GSI.
- Usage : ✅ ajouter `table/<nom>/index/*` dès qu'un GSI est lu · ❌ `Resource: "*"` pour « régler » le refus : toutes les tables du compte s'ouvrent.

```json
# Exemple 1 : table + ses index (doc)
"Action": ["dynamodb:Query"],
"Resource": [
  "arn:aws:dynamodb:eu-west-3:
   123456789012:table/progress",
  "arn:aws:dynamodb:eu-west-3:
   123456789012:table/progress/index/*"]
```

```python
# Exemple 2 : ce que couvre chaque ARN
from fnmatch import fnmatchcase as m
t = "table/progress"
gsi = t + "/index/par-date"
m(gsi, t)               # → False
m(gsi, t + "/index/*")  # → True
```

- Quiz : La politique accorde `Query` sur `…:table/progress*` (sans `/index/*`). `Query` sur le GSI `par-date` ?
- [ ] Refusée : l'index n'est pas nommé
- [x] Autorisée : `*` couvre aussi `/index/par-date`
- [ ] Autorisée seulement en lecture cohérente à terme
- [ ] Refusée : `*` ne traverse pas les `/`
- Réponse : autorisée : dans un ARN IAM, `*` remplace n'importe quels caractères, `/` compris ; mais il ouvre aussi `table/progress-old`.

## 118. transaction : pas d'action TransactWriteItems
- Id : dynamodb-iam-transactions
- Sous-thème : sécurité
- Type : piège
- Niveau : 2
- Profils : ops
- Source : data-platform · pwa-sync
- Définition : Une transaction s'autorise par les actions de ses éléments : `PutItem`, `UpdateItem`, `DeleteItem`, `GetItem`, et `ConditionCheckItem` pour un `ConditionCheck`.
- Contexte : Selon la doc (Service Authorization Reference), l'API `TransactWriteItems` n'a pas d'action IAM à son nom : elle exige `ConditionCheckItem`, `DeleteItem`, `PutItem` ou `UpdateItem` selon les éléments envoyés. Écrire `dynamodb:TransactWriteItems` dans une politique n'accorde donc rien d'utile. Chaque élément est jugé sur sa propre table : une transaction qui touche `jobs` et `audit` demande des droits sur les deux.
- Usage : ✅ lister les actions unitaires des éléments réellement envoyés · ❌ chercher une action `Transact*` ou passer à `dynamodb:*` pour débloquer.

```python
# Exemple 1 : actions exigées (doc)
ACTION = {"Put": "PutItem",
  "Update": "UpdateItem",
  "Delete": "DeleteItem",
  "ConditionCheck": "ConditionCheckItem"}
tx = [{"Put": {}}, {"Update": {}}]
sorted(ACTION[k] for e in tx for k in e)
# → ["PutItem", "UpdateItem"]
```

- Quiz : Rôle avec `PutItem` et `UpdateItem` sur `jobs`. Transaction : un `Put` et un `ConditionCheck` sur `jobs`. Résultat ?
- [ ] Acceptée : un `ConditionCheck` ne demande aucun droit
- [ ] Refusée : il manque `dynamodb:GetItem`
- [ ] Refusée : il manque `dynamodb:TransactWriteItems`
- [x] Refusée : il manque `dynamodb:ConditionCheckItem`
- Réponse : il manque `ConditionCheckItem` : selon la doc, l'élément `ConditionCheck` se contrôle avec cette action, distincte de `GetItem`.

## 119. server_side_encryption : quelle clé KMS
- Id : dynamodb-chiffrement-kms
- Sous-thème : sécurité
- Type : concept
- Niveau : 2
- Profils : ops
- Voir aussi : kms-cle-aws-ou-client
- Source : data-platform · pwa-sync
- Définition : Une table est toujours chiffrée au repos ; `server_side_encryption` choisit la clé : détenue par AWS, gérée par AWS (`aws/dynamodb`) ou la sienne (`kms_key_arn`).
- Contexte : Sans le bloc, ou avec `enabled = false` : clé détenue par AWS, gratuite, invisible dans le compte. `enabled = true` sans ARN : clé gérée `alias/aws/dynamodb`, frais KMS. Avec `kms_key_arn` : clé client, frais KMS, et sa politique de clé contrôle qui peut déchiffrer (la Lambda qui lit la table a besoin de `kms:Decrypt`). On peut changer de clé sur une table existante.
- Usage : ✅ clé client quand l'audit ou la révocation l'exigent (comme pour le bucket raw en SSE-KMS) · ❌ clé client « par principe » : coût et droits IAM en plus.

```hcl
# Exemple 1 : clé client du projet
server_side_encryption {
  enabled     = true
  kms_key_arn = aws_kms_key.ddb.arn
}
# la politique de la clé décide qui lit
```

- Quiz : Que donne `server_side_encryption { enabled = false }` ?
- [ ] Une table non chiffrée
- [x] Une table chiffrée avec une clé détenue par AWS
- [ ] Une erreur : le chiffrement est obligatoire
- [ ] La clé gérée `alias/aws/dynamodb`
- Réponse : chiffrée quand même : selon la doc, toutes les données DynamoDB sont chiffrées au repos ; `false` choisit la clé détenue par AWS (DEFAULT dans la console).

## 120. dynamodb:ReturnValues : écrire sans relire
- Id : dynamodb-iam-returnvalues
- Sous-thème : sécurité
- Type : piège
- Niveau : 2
- Profils : ops, expert
- Prérequis : dynamodb-returnvalues
- Source : data-platform · pwa-sync
- Définition : La condition `dynamodb:ReturnValues` borne ce qu'une écriture renvoie : à `NONE`, `PutItem` ou `UpdateItem` ne peut plus rendre l'ancienne ligne.
- Contexte : Selon la doc, une écriture fait une lecture implicite : `ReturnValues = ALL_OLD` rend la ligne remplacée, `ALL_NEW` la ligne entière après mise à jour. Un rôle d'écriture sans `GetItem` lit donc des colonnes par ce biais. La doc pose `StringEqualsIfExists` sur `ReturnValues`, à côté de `dynamodb:Select` pour les lectures. `IfExists` : la règle ne joue que si la clé est présente dans la requête.
- Usage : ✅ rôle d'écriture seule, ou colonnes bornées par `dynamodb:Attributes` · ❌ croire qu'un rôle sans `GetItem` ne lit jamais rien : `ALL_OLD` renvoie la ligne.

```json
# Exemple 1 : écrire sans relire (doc)
"Action": ["dynamodb:PutItem",
           "dynamodb:UpdateItem"],
"Condition": {"StringEqualsIfExists": {
  "dynamodb:ReturnValues": "NONE"}}
# PutItem, ReturnValues=ALL_OLD → refusé
# PutItem sans ReturnValues     → permis
```

```python
# Exemple 2 : ALL_OLD rend l'ancienne ligne
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk",
    "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName":
    "pk", "AttributeType": "S"}])
t.put_item(Item={"pk": "u1", "note": "x"})
r = t.put_item(Item={"pk": "u1"},
  ReturnValues="ALL_OLD")
r["Attributes"]  # → {"pk": "u1", "note": "x"}
m.stop()
```

- Quiz : Même instruction, mais `StringEquals` (sans `IfExists`) et `dynamodb:GetItem` ajouté aux actions. Un `GetItem` ?
- [ ] Permis : un `GetItem` ne renvoie aucune ancienne valeur
- [x] Refusé : la clé est absente, `StringEquals` est faux
- [ ] Permis : la condition ne vise que les écritures
- [ ] Rejeté à l'enregistrement de la politique
- Réponse : refusé (selon la doc) : `GetItem` ne porte pas `dynamodb:ReturnValues` ; une clé absente rend `StringEquals` faux, d'où le `IfExists`.

## 121. dynamodb:EnclosingOperation : transactions seulement
- Id : dynamodb-iam-enclosing-operation
- Sous-thème : sécurité
- Type : concept
- Niveau : 2
- Profils : ops, expert
- Prérequis : dynamodb-iam-transactions
- Source : data-platform · pwa-sync
- Définition : `dynamodb:EnclosingOperation` vaut `TransactWriteItems` ou `TransactGetItems` dans une transaction : de quoi autoriser ou bloquer les transactions.
- Contexte : Une transaction demande les mêmes actions qu'un appel simple (`PutItem`…) : sans cette clé, IAM ne distingue pas les deux. Selon la doc, deux usages : n'autoriser que des transactions (chaque écriture dans `jobs` va avec sa ligne `audit`), ou les interdire en gardant les appels simples (`Deny` avec la clé). La doc l'emploie avec `ForAnyValue:StringEquals` : hors transaction, la clé est absente, la condition est fausse.
- Usage : ✅ imposer l'écriture atomique d'un état et de sa trace · ❌ compter sur la discipline du code : un `PutItem` isolé contourne l'audit.

```json
# Exemple 1 : écrire seulement en transaction
"Action": ["dynamodb:PutItem",
  "dynamodb:UpdateItem",
  "dynamodb:ConditionCheckItem"],
"Condition": {"ForAnyValue:StringEquals": {
  "dynamodb:EnclosingOperation":
    ["TransactWriteItems"]}}
# TransactWriteItems [Put, Update] → permis
# PutItem seul                  → refusé
```

```python
# Exemple 2 : la logique ForAnyValue
permis = {"TransactWriteItems"}
seul = []   # PutItem hors transaction
tx = ["TransactWriteItems"]
any(v in permis for v in seul)  # → False
any(v in permis for v in tx)    # → True
```

- Quiz : Avec cette politique, un `TransactWriteItems` qui ne contient qu'un seul `Put`. Décision ?
- [ ] Refusé : une transaction exige au moins 2 éléments
- [ ] Refusé : il manque l'action `TransactWriteItems`
- [x] Permis : un seul élément reste une transaction
- [ ] Permis seulement avec un `ConditionCheck` en plus
- Réponse : permis : selon la doc, `TransactItems` accepte de 1 à 100 éléments ; le `Put` porte `EnclosingOperation = TransactWriteItems`.

## 122. politique de ressource : sur la table
- Id : dynamodb-politique-de-ressource
- Sous-thème : sécurité
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : iam-politique-de-ressource
- Source : data-platform · pwa-sync
- Définition : Depuis mars 2024, une table DynamoDB accepte une politique de ressource : qui peut faire quoi sur la table, ses index et son stream.
- Contexte : Selon la doc : 20 Ko au plus (espaces comptés), la politique de la table couvre aussi ses index. Dans le même compte, elle suffit seule ; entre deux comptes, il faut un `Allow` des deux côtés (identité et ressource). Terraform : `aws_dynamodb_resource_policy` (`resource_arn`, `policy`). Cas typique : laisser le rôle d'un compte d'analyse lire une table, sans lui créer de rôle chez nous.
- Usage : ✅ accès inter-comptes, garde-fous posés sur la table elle-même · ❌ y dupliquer les droits de nos propres rôles : deux endroits à relire.

```hcl
# Exemple 1 : lecture pour un autre compte
data "aws_iam_policy_document" "lect" {
  statement {
    actions   = ["dynamodb:Query"]
    resources = [aws_dynamodb_table.t.arn]
    principals {
      type        = "AWS"
      identifiers = [var.role_analyse]
    }
  }
}
resource "aws_dynamodb_resource_policy" "t" {
  resource_arn = aws_dynamodb_table.t.arn
  policy = data.aws_iam_policy_document.lect.json
}
```

- Quiz : Le rôle a `GetItem` sans condition ; la politique de la table accorde `GetItem` avec une condition `dynamodb:Attributes`. Le rôle est-il borné aux colonnes ?
- [ ] Oui : la politique de la table prime
- [ ] Oui : les deux conditions s'additionnent
- [x] Non : l'`Allow` sans condition suffit, il faut un `Deny`
- [ ] Non : la politique de ressource est ignorée dans le compte
- Réponse : non (selon la doc) : l'`Allow` inconditionnel de l'identité suffit, la condition d'un autre `Allow` ne restreint rien ; seul un `Deny` explicite borne.

## 123. politique d'endpoint : nos tables seulement
- Id : dynamodb-politique-endpoint
- Sous-thème : sécurité
- Type : concept
- Niveau : 2
- Profils : ops
- Voir aussi : couts-nat-gateway-endpoint
- Source : data-platform · pwa-sync
- Définition : La politique d'un endpoint Gateway DynamoDB filtre ce qui passe par lui : on la borne aux tables `data-platform-*` (défaut : tout).
- Contexte : Selon la doc, la politique par défaut autorise tout ; elle s'ajoute aux droits IAM (il faut les deux) et ne vise que le trafic qui emprunte l'endpoint. Sur un compte partagé avec d'autres projets, une Lambda du VPC ne joint plus une table d'un autre projet, même avec un rôle trop large. Un changement prend quelques minutes. L'endpoint ne sert que dans sa région.
- Usage : ✅ VPC partagé, défense en profondeur contre un rôle trop large · ❌ la prendre pour un contrôle global : le trafic hors endpoint ne la voit pas.

```hcl
# Exemple 1 : l'endpoint ne voit que nos tables
data "aws_iam_policy_document" "vpce" {
  statement {
    actions   = ["dynamodb:*"]
    resources = [local.arn_tables_prefixe]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }
}
# local.arn_tables_prefixe =
#   "arn:aws:dynamodb:eu-west-3:<id>:
#    table/data-platform-*"
```

```hcl
# Exemple 2 : posée sur l'endpoint Gateway
resource "aws_vpc_endpoint" "ddb" {
  vpc_id       = aws_vpc.data.id
  service_name = "com.amazonaws.eu-west-3.dynamodb"
  policy = data.aws_iam_policy_document.vpce.json
}
```

- Quiz : Un dev lance, depuis son poste hors VPC, une lecture sur `autre-projet-x` avec ses droits IAM. Effet de cette politique ?
- [ ] Refusée : la table n'est pas `data-platform-*`
- [x] Aucun : la requête ne passe pas par l'endpoint
- [ ] Refusée seulement pour les écritures
- [ ] Aucun, sauf si le dev a assumé un rôle
- Réponse : aucun : la politique d'endpoint ne filtre que le trafic qui l'emprunte ; pour forcer le passage par l'endpoint, c'est `aws:sourceVpce` côté table.

## 124. Aurora Serverless v2 : 0 ACU et pause
- Id : dynamodb-aurora-pause
- Sous-thème : choisir
- Type : choisir
- Niveau : 3
- Profils : ops, expert
- Prérequis : dynamodb-cout-au-repos-rds
- Source : data-platform · pwa-sync
- Définition : Avec un minimum à 0 ACU, Aurora Serverless v2 se met en pause après un temps sans connexion : plus de frais d'instance.
- Contexte : Selon la doc : délai avant pause de 300 s (défaut et minimum) à 86 400 s ; reprise typique d'environ 15 s à la connexion suivante, plus longue après 24 h de pause ; le stockage reste facturé. Une tentative de connexion, même aux identifiants faux, réveille l'instance. Minimum à 0,5 ACU : jamais de pause. Prix Paris : 0,14 $ par ACU-heure (Aurora PostgreSQL).
- Usage : ✅ SQL pour un outil interne peu utilisé, qui tolère 15 s au réveil · ❌ API qui doit répondre vite au premier appel : minimum au-dessus de 0, ou DynamoDB.

```python
# Exemple 1 : minimum 0,5 ou 0, Paris
acu_h = 0.14                  # USD
round(0.5 * acu_h * 730, 1)   # → 51.1
# minimum 0 : 2 h d'activité par jour
round(0.5 * acu_h * 2 * 30, 1)  # → 4.2
```

```hcl
# Exemple 2 : pause après 10 min
serverlessv2_scaling_configuration {
  min_capacity             = 0
  max_capacity             = 2
  seconds_until_auto_pause = 600
}
```

- Quiz : Minimum 0 ACU, pause après 300 s. Une Lambda de supervision se connecte toutes les 2 minutes. Que coûte l'instance ?
- [ ] Rien : pause entre deux connexions
- [x] Comme sans pause : elle n'est jamais inactive 300 s
- [ ] Seulement les 15 s de chaque réveil
- [ ] Rien, si la Lambda ne fait que des lectures
- Réponse : comme sans pause : il faut 300 s sans connexion pour s'endormir ; une sonde toutes les 2 min la garde éveillée en permanence.

## 125. Decimal(0.1) : passer par str
- Id : dynamodb-decimal-depuis-float
- Sous-thème : modèle
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : dynamodb-decimal-lecture
- Source : data-platform · pwa-sync
- Définition : Pour écrire un `float` Python, on le convertit avec `Decimal(str(x))` ; `Decimal(x)` direct reprend l'erreur binaire du float.
- Contexte : `Decimal(0.1)` vaut exactement la valeur binaire du float : 0.1000000000000000055511151231257827021181583404541015625. `str(0.1)` donne la représentation courte `'0.1'`, que `Decimal` reprend telle quelle. Pour un corps JSON entrant (API Gateway), `json.loads(s, parse_float=Decimal)` produit directement des `Decimal` exacts, sans passer par le float.
- Usage : ✅ `parse_float=Decimal` à l'entrée de la Lambda, `Decimal(str(x))` pour un float isolé · ❌ `Decimal(x)` sur un float venu d'un calcul.

```python
# Exemple 1 : float → Decimal
from decimal import Decimal
Decimal(str(0.1))  # → Decimal('0.1')
Decimal(0.1) == Decimal("0.1")  # → False
```

```python
# Exemple 2 : corps JSON d'une API
import json
from decimal import Decimal
b = json.loads('{"note": 0.1}',
  parse_float=Decimal)
b["note"]  # → Decimal('0.1')
```

- Quiz : Que fait `TypeSerializer().serialize(Decimal(0.1))` ?
- [ ] `{'N': '0.1'}`
- [ ] `{'N': '0.1000000000000000055511151231257827021'}`
- [x] Lève `Inexact`
- [ ] Lève `TypeError` : float déguisé
- Réponse : `Inexact` (mesuré) : 55 chiffres significatifs, au-delà des 38 de DynamoDB ; boto3 refuse d'arrondir en silence.

## 126. sharding calculé : suffixe déterministe
- Id : dynamodb-sharding-calcule
- Sous-thème : clés
- Type : recette
- Niveau : 3
- Profils : data, expert
- Prérequis : dynamodb-write-sharding
- Source : data-platform · pwa-sync
- Définition : Le suffixe calculé dérive le numéro de shard d'un attribut connu (id d'annonce) par un hachage stable, pour retrouver un item par `GetItem`.
- Contexte : Variante de la doc : suffixe calculé depuis l'`OrderId`, modulo 200, plus 1. Les écritures restent réparties, et qui connaît l'id recalcule la `pk` exacte : un seul `GetItem`. Relire toute la journée exige toujours N `Query`. Le hachage doit donner le même résultat partout (Lambda Python, front TS, demain un autre langage) : CRC32, SHA-256.
- Usage : ✅ écritures massives sur une clé chaude et lecture unitaire par id · ❌ suffixe aléatoire quand on doit relire un item précis.

```python
# Exemple 1 : même id, même shard
import zlib
N = 8
def pk(date, id_annonce):
    h = zlib.crc32(id_annonce.encode())
    return f"{date}.{h % N + 1}"
pk("2026-10-23", "A123")
# → '2026-10-23.5'
```

- Quiz : Et si on calcule le suffixe avec `hash(id_annonce) % N` de Python ?
- [ ] Équivalent, en plus rapide
- [ ] Refusé par DynamoDB
- [x] Shard différent d'un processus à l'autre
- [ ] Tout tombe sur le même shard
- Réponse : shard différent d'un processus à l'autre (mesuré : 3 puis 6 pour le même SIREN) : `hash()` des chaînes est salé à chaque démarrage (`PYTHONHASHSEED`) ; l'item écrit devient introuvable.

## 127. adjacency list : entreprise ↔ tribunal
- Id : dynamodb-adjacency-list
- Sous-thème : clés
- Type : recette
- Niveau : 3
- Profils : web, expert
- Prérequis : dynamodb-surcharge-des-cles
- Voir aussi : dynamodb-gsi-surcharge
- Source : data-platform · pwa-sync
- Définition : L'adjacency list modélise un plusieurs-à-plusieurs : chaque entité a sa partition, chaque relation est un item dont la `sk` est l'id de l'autre entité.
- Contexte : Patron de la doc (factures ↔ lignes de facture). Ici `pk = SIREN#…`, `sk = TRIBUNAL#…` : les tribunaux d'une entreprise sont une `Query` sur sa partition. Le sens inverse (entreprises d'un tribunal) passe par un index secondaire global dont la clé de partition est la `sk` de la table : l'arête n'est écrite qu'une fois. Parcours à plusieurs sauts en temps réel : la doc oriente vers Neptune.
- Usage : ✅ relation plusieurs-à-plusieurs lue dans les deux sens · ❌ parcours de graphe profond en temps réel : base orientée graphe.

```python
# Exemple 1 : arêtes, puis index inversé
aretes = [
  ("SIREN#4836", "TRIBUNAL#7501"),
  ("SIREN#5521", "TRIBUNAL#7501"),
  ("SIREN#4836", "TRIBUNAL#6901")]
[s for p, s in aretes if p == "SIREN#4836"]
# → ['TRIBUNAL#7501', 'TRIBUNAL#6901']
gsi = [(s, p) for p, s in aretes]
[s for p, s in gsi
 if p == "TRIBUNAL#7501"]
# → ['SIREN#4836', 'SIREN#5521']
```

- Quiz : Un tribunal de commerce est lié à 300 000 entreprises. Risque sur l'index inversé ?
- [ ] Aucun : l'index se répartit seul
- [ ] Item de 400 Ko dépassé
- [ ] Index refusé au-delà de 10 Go
- [x] Partition chaude sur `TRIBUNAL#…`
- Réponse : partition chaude : toutes ces arêtes partagent une seule `pk` dans l'index ; la doc conseille de sharder les grosses agrégations. Le plafond de 10 Go ne vise que les index locaux.

## 128. single-table : ce qu'on y perd
- Id : dynamodb-single-table-limites
- Sous-thème : clés
- Type : choisir
- Niveau : 3
- Profils : ops, expert
- Prérequis : dynamodb-surcharge-des-cles
- Source : data-platform · pwa-sync
- Définition : Une table unique impose les mêmes réglages à toutes ses entités : sauvegarde, chiffrement, classe de stockage et flux de changements valent pour tout.
- Contexte : Inconvénients listés par la doc AWS : sauvegardes tout ou rien ; une seule clé de chiffrement ; la classe Standard-IA profite peu si historique et données vives sont mêlés ; DynamoDB Streams émet les changements de toutes les entités ; courbe d'apprentissage, et code client qui reçoit plusieurs classes dans un résultat. En face : localité des lectures, moins de tables, d'alarmes et de politiques IAM.
- Usage : ✅ entités lues ensemble, mêmes exigences de sauvegarde et de chiffrement · ❌ données critiques et jetables mêlées, ou chiffrement par client : tables séparées.

```
# Exemple 1 : trancher pour data-platform
Entreprise + annonces : lues ensemble
  → même table (pk SIREN#…)
Cache de réponses d'API : jetable,
  PITR inutile, classe différente
  → table séparée
```

- Quiz : Seules les annonces doivent déclencher une Lambda via DynamoDB Streams, en single-table. Comment ?
- [ ] Un stream par type d'entité
- [x] Filtre d'événements sur le mapping
- [ ] Impossible : passer en multi-table
- [ ] Un index secondaire par entité
- Réponse : filtre d'événements : le flux porte les changements de toutes les entités ; le filtre de l'event source mapping écarte les autres, sans surcoût Lambda selon la doc.

## 129. LSI : 10 Go par valeur de clé de partition
- Id : dynamodb-lsi-10-go
- Sous-thème : index
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : dynamodb-lsi-lecture-forte
- Source : data-platform · pwa-sync
- Définition : Dès qu'une table a un LSI, une valeur de `pk` (item collection : items de la table et des LSI) ne peut dépasser 10 Go.
- Contexte : Avec un LSI, toute la collection d'une `pk` vit dans une seule partition. Au-delà de 10 Go, DynamoDB peut renvoyer `ItemCollectionSizeLimitExceededException` : plus d'ajout ni d'agrandissement pour cette `pk`, les autres restent libres. `ReturnItemCollectionMetrics="SIZE"` sur les écritures renvoie une estimation ; la doc conseille d'alerter avant (8 Go). Les GSI et les tables sans LSI n'ont pas cette limite.
- Usage : ✅ LSI sur des partitions bornées (un SIREN, un utilisateur) · ❌ LSI sur une `pk` qui grossit sans fin (`pk = "BODACC"`) : un GSI.

```python
# Exemple 1 : surveiller la collection
rep = {"ItemCollectionMetrics": {
  "ItemCollectionKey": {"pk": "483609327"},
  "SizeEstimateRangeGB": [7.5, 8.5]}}
haut = rep["ItemCollectionMetrics"][
    "SizeEstimateRangeGB"][1]
haut >= 8  # → True   (alerte avant 10 Go)
```

- Quiz : Table **sans** LSI, mais avec un GSI. Une `pk` atteint 15 Go. Que se passe-t-il ?
- [ ] `ItemCollectionSizeLimitExceededException`
- [ ] Les écritures de cette `pk` passent par le GSI
- [x] Rien : la limite ne vise que les tables avec LSI
- [ ] La `pk` est découpée en deux tables
- Réponse : rien : selon la doc, les 10 Go par collection ne s'appliquent qu'aux tables qui ont au moins un LSI, ni aux GSI ni aux tables sans LSI.

## 130. GSI limité : il freine les écritures de la table
- Id : dynamodb-gsi-freine-table
- Sous-thème : index
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : dynamodb-cout-ecriture-index
- Source : data-platform · pwa-sync
- Définition : Si un GSI manque de capacité d'écriture, DynamoDB limite (throttle) les écritures de la table elle-même, pas seulement l'index.
- Contexte : Selon la doc, une écriture de table ne réussit que si la table **et** chaque GSI touché ont la capacité nécessaire ; sinon c'est la requête sur la table qui reçoit `ProvisionedThroughputExceededException`. D'où la règle : en provisionné, `write_capacity` d'un GSI au moins égale à celle de la table. La création d'un GSI sur une table chargée peut aussi freiner la production.
- Usage : ✅ GSI dimensionné comme la table, surveiller ses métriques de throttling · ❌ GSI à 1 WCU « parce qu'on le lit peu » : on n'économise pas, on bloque l'ingestion.

```python
# Exemple 1 : qui limite ? (provisionné)
wcu = {"table": 100, "par-tribunal": 20}
besoin = 50   # écritures/s, toutes indexées
[k for k, v in wcu.items() if v < besoin]
# → ['par-tribunal']   (table freinée)
```

- Quiz : Même table, 50 écritures/s qui ne modifient ni `tribunal` ni un attribut projeté. Sont-elles freinées par `par-tribunal` ?
- [ ] Oui : toute écriture passe par chaque GSI
- [x] Non : elles ne consomment rien sur l'index
- [ ] Oui, à moitié : 0,5 WCU d'index par écriture
- [ ] Non, mais elles sont mises en file d'attente
- Réponse : non : selon la doc, une écriture qui ne demande pas de mise à jour du GSI ne consomme aucune capacité de l'index ; seule la table compte.

## 131. GSI surchargé : un index, plusieurs accès
- Id : dynamodb-gsi-surcharge
- Sous-thème : index
- Type : recette
- Niveau : 3
- Profils : web, expert
- Prérequis : dynamodb-surcharge-des-cles, dynamodb-gsi-autre-cle
- Source : data-platform · pwa-sync
- Définition : En modèle « une table », un GSI sur attributs génériques (`gsi1pk`, `gsi1sk`) sert plusieurs accès : chaque type d'item y met sa valeur.
- Contexte : Procédures et annonces vivent dans la même table ; la procédure écrit `gsi1pk = "TRIB#Paris"`, l'annonce `gsi1pk = "DATE#2026-10-01"`. Un seul index répond aux deux requêtes, sous le quota de 20 GSI et avec un seul index à payer. La doc AWS appelle cela *overloading*. Contrepartie : un seul type de clé (`S`) pour toutes les valeurs, et une lisibilité qui repose sur des préfixes documentés.
- Usage : ✅ beaucoup d'accès sur une table multi-types · ❌ une table à un seul type d'item : des noms explicites (`tribunal`) sont plus clairs.

```python
# Exemple 1 : un index, deux accès
items = [
  {"sk": "P#1", "gsi1pk": "TRIB#Paris"},
  {"sk": "A#7", "gsi1pk": "DATE#2026-10-01"},
  {"sk": "A#8", "gsi1pk": "DATE#2026-10-01"},
]
q = lambda v: [i["sk"] for i in items if i["gsi1pk"] == v]
q("DATE#2026-10-01")  # → ['A#7', 'A#8']
q("TRIB#Paris")       # → ['P#1']
```

- Quiz : `gsi1sk` est de type `S`. Il faut aussi trier les entreprises par capital (5 000, 40 000, 120 000). On écrit quoi ?
- [ ] `gsi1sk = 40000` (nombre) pour ces items
- [ ] `"CAP#40000"` : DynamoDB trie les nombres dans les chaînes
- [x] `"CAP#000040000"` : complété de zéros
- [ ] Un second type `N` pour `gsi1sk`
- Réponse : complété de zéros : le type de clé d'index est unique pour tous les items, ici `S`, trié caractère par caractère ; un nombre écrit sur l'attribut serait refusé.

## 132. RCU : Query arrondit le total, pas chaque item
- Id : dynamodb-rcu-query-cumulee
- Sous-thème : lecture
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Prérequis : dynamodb-rcu-arrondi-4ko
- Source : data-platform · pwa-sync
- Définition : Une `Query` additionne la taille de tous les items lus puis arrondit **une fois** au multiple de 4 Ko ; `GetItem` arrondit chaque item séparément.
- Contexte : Selon la doc : 10 items totalisant 40,8 Ko comptent 44 Ko ; 1 500 items de 64 octets, 96 Ko. Lire 100 petites lignes d'une partition en une `Query` coûte donc bien moins que 100 `GetItem`, qui paient chacun une tranche de 4 Ko entière. Un `Scan` compte de même la taille des items évalués, pas celle des items renvoyés.
- Usage : ✅ ranger les lignes lues ensemble sous le même `pk` et les lire par `Query` · ❌ boucler sur des `GetItem` pour relire une partition de petites lignes.

```python
# Exemple 1 : cumul puis arrondi
import math
tailles = [4180] * 10   # 10 items ≈ 4 Ko
math.ceil(sum(tailles) / 4096)  # → 11
# Query forte : 11 RCU
sum(math.ceil(s / 4096) for s in tailles)
# → 20   (10 GetItem forts : 2 chacun)
```

- Quiz : 100 lignes de 200 octets dans une partition, lecture éventuelle. 100 `GetItem` contre une `Query` : combien d'unités ?
- [ ] 50 contre 50
- [x] 50 contre 2,5
- [ ] 2,5 contre 2,5
- [ ] 100 contre 5
- Réponse : 50 contre 2,5 : chaque `GetItem` paie une tranche (0,5) ; la `Query` cumule 20 000 octets, soit 5 tranches, à 0,5 en éventuel.

## 133. Scan parallèle : Segment et TotalSegments
- Id : dynamodb-scan-parallele
- Sous-thème : lecture
- Type : recette
- Niveau : 3
- Profils : data, expert
- Prérequis : dynamodb-scan-toute-la-table
- Source : data-platform · pwa-sync
- Définition : Un `Scan` parallèle découpe la table en `TotalSegments` segments ; chaque worker lit le sien (`Segment` de 0 à `TotalSegments - 1`) et pagine seul.
- Contexte : Un `Scan` séquentiel lit une partition physique à la fois ; plusieurs workers (threads, Lambdas) vont plus vite. Les deux paramètres vont ensemble, et le `LastEvaluatedKey` d'un segment se rejoue avec le même `Segment`. Les items sont répartis par hachage du `pk` (selon la doc) : segments inégaux. Coût identique, mais consommé plus vite : risque de limitation pour les autres lecteurs.
- Usage : ✅ export ou migration d'une grosse table, un worker par segment · ❌ dans le chemin d'une app, ou sur une table déjà sous forte charge.

```python
# Exemple 1 : 10 SIREN, 4 segments (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="entreprises",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk",
              "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk",
                         "AttributeType": "S"}])
for i in range(10):
    t.put_item(Item={"pk": f"48360932{i}"})
n = [t.scan(Segment=s, TotalSegments=4)["Count"] for s in range(4)]
sum(n)  # → 10   (chaque ligne une seule fois)
t.scan(Segment=4, TotalSegments=4)  # ❌ ClientError
m.stop()
```

- Quiz : Table où toutes les lignes partagent le même `pk` (un seul SIREN). Scan avec `TotalSegments=4` : que se passe-t-il ?
- [ ] 4 segments d'un quart chacun, 4 fois plus vite
- [x] Un segment a tout, les 3 autres sont vides
- [ ] `ValidationException` : trop de segments
- [ ] Chaque segment relit toute la partition
- Réponse : un segment a tout (selon la doc, mesuré avec moto) : le segment dépend du hachage du `pk` ; même `pk`, même segment, aucun gain.

## 134. Scan paginé : la seule condition d'arrêt
- Id : dynamodb-scan-pagine-fin
- Sous-thème : lecture
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : dynamodb-pagination-query
- Voir aussi : dynamodb-scan-parallele
- Source : data-platform · pwa-sync
- Définition : Un `Scan` complet boucle en repassant `LastEvaluatedKey` comme `ExclusiveStartKey` ; seule l'absence de `LastEvaluatedKey` signifie la fin.
- Contexte : Chaque page s'arrête à 1 Mo lu ou à `Limit` items évalués. Selon la doc, une page peut revenir vide avec un `LastEvaluatedKey` (filtre), et un `LastEvaluatedKey` présent ne garantit pas qu'il reste des données. En boto3, `client.get_paginator("scan")` fait la boucle ; `Table.scan` du `resource` n'en a pas. Côté CLI, `--max-items` rend un `NextToken`, `--limit` un `LastEvaluatedKey`.
- Usage : ✅ `while` sur `LastEvaluatedKey`, ou paginator, avec les mêmes paramètres à chaque page · ❌ s'arrêter sur `Count == 0` ou sur une page plus petite que `Limit`.

```python
# Exemple 1 : boucle jusqu'au bout (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="entreprises",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk",
                         "AttributeType": "S"}])
for i in range(5):
    t.put_item(Item={"pk": f"48360932{i}"})
lus, kw = [], {"Limit": 2}
while True:
    r = t.scan(**kw); lus += r["Items"]
    if "LastEvaluatedKey" not in r: break
    kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]
len(lus)  # → 5   (pages de 2, 2, 1)
m.stop()
```

- Quiz : Une page renvoie `LastEvaluatedKey` ; la suivante revient avec 0 item et sans `LastEvaluatedKey`. Diagnostic ?
- [ ] Bug : une ligne a été perdue entre les pages
- [ ] Limitation de débit : il faut réessayer
- [x] Normal : le scan est terminé
- [ ] La table a été vidée pendant le scan
- Réponse : normal (selon la doc) : `LastEvaluatedKey` présent ne promet pas de données ; seule son absence marque la fin.

## 135. version : verrou optimiste
- Id : dynamodb-verrou-optimiste
- Sous-thème : écriture
- Type : recette
- Niveau : 3
- Profils : web, expert
- Prérequis : dynamodb-condition-echouee-exception
- Source : data-platform · pwa-sync
- Définition : Le verrou optimiste lit `version`, puis écrit avec `ConditionExpression="version = :lue"` et `SET version = version + :un` : la seconde écriture concurrente échoue.
- Contexte : Pas de verrou tenu : on suppose qu'il n'y aura pas de conflit, et la condition le vérifie au moment d'écrire. Celui qui perd reçoit `ConditionalCheckFailedException`, relit la ligne, refait sa fusion et réessaie. Indispensable pour un document unique modifié par plusieurs appareils (préférences), inutile avec une ligne par fait.
- Usage : ✅ document partagé lu-modifié-écrit (préférences, panier) · ❌ simple compteur : `ADD`, atomique sans version ni réessai.

```python
# Exemple 1 : deux appareils lisent v1
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
k = {"pk": "u1", "sk": "P#prefs"}
t.put_item(Item={**k, "theme": "dark", "version": 1})
def save(lue, theme):
    t.update_item(Key=k, ConditionExpression="version = :lue",
      UpdateExpression="SET theme = :t, version = version + :un",
      ExpressionAttributeValues={":t": theme, ":lue": lue, ":un": 1})
save(1, "light")   # Mac : passe, version 2
save(1, "blue")  # ❌ ClientError
m.stop()
```

- Quiz : Première sauvegarde : la ligne n'existe pas encore, l'appareil envoie `version = :lue` avec `:lue = 0`. Résultat ?
- [ ] Passe : `version` absente vaut 0
- [ ] Passe : `UpdateItem` crée la ligne
- [x] `ConditionalCheckFailedException`
- [ ] `ValidationException` : `version` inconnue
- Réponse : refus (mesuré avec moto) : la comparaison sur un attribut absent est fausse ; écrire `attribute_not_exists(version) OR version = :lue`.

## 136. ReturnValuesOnConditionCheckFailure : voir ce qui bloque
- Id : dynamodb-condition-echec-valeurs
- Sous-thème : écriture
- Type : recette
- Niveau : 3
- Profils : web, expert
- Prérequis : dynamodb-condition-echouee-exception
- Source : data-platform · pwa-sync
- Définition : `ReturnValuesOnConditionCheckFailure="ALL_OLD"` joint à l'exception la ligne qui a fait échouer la condition, dans `e.response["Item"]`.
- Contexte : Évite le `GetItem` de diagnostic après un refus (et la course qu'il ouvre) : on sait tout de suite quelle `version` ou quel état bloque. Selon la doc, valeurs `ALL_OLD` ou `NONE`, sans RCU consommée. Piège mesuré avec moto : même avec `boto3.resource`, `Item` arrive au format typé (`{"BOOL": True}`), il faut le désérialiser (`TypeDeserializer`).
- Usage : ✅ verrou optimiste : récupérer la version gagnante pour refusionner sans relire · ❌ supposer `Item` désérialisé comme `get_item` de la `Table`.

```python
# Exemple 1 : la ligne qui a bloqué
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
K = {"pk": "HASH", "sk": "RANGE"}
t = boto3.resource("dynamodb",
  region_name="eu-west-3").create_table(
  TableName="progress", BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": a, "KeyType": k} for a, k in K.items()],
  AttributeDefinitions=[{"AttributeName": a, "AttributeType": "S"} for a in K])
L = {"pk": "u1", "sk": "R#2026-10-25#IAM/3"}
t.put_item(Item={**L, "ok": True})
try:
    t.put_item(Item={**L, "ok": False},
      ConditionExpression="attribute_not_exists(pk)",
      ReturnValuesOnConditionCheckFailure="ALL_OLD")
except t.meta.client.exceptions.ConditionalCheckFailedException as e:
    e.response["Item"]["ok"]  # → {"BOOL": True}
m.stop()
```

- Quiz : Sans `ReturnValuesOnConditionCheckFailure`, que contient `e.response.get("Item")` après le refus ?
- [ ] La ligne existante, désérialisée
- [ ] La ligne qu'on voulait écrire
- [x] `None` : rien n'est joint
- [ ] La clé seule
- Réponse : `None` (mesuré avec moto) : la valeur par défaut est `NONE` ; l'item n'est joint que sur demande explicite `ALL_OLD`.

## 137. WCU : taille arrondie au Ko, avant ou après
- Id : dynamodb-wcu-arrondi
- Sous-thème : écriture
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Prérequis : dynamodb-rcu-arrondi-4ko
- Source : data-platform · pwa-sync
- Définition : Une écriture coûte 1 WCU par Ko de la ligne, arrondi au Ko supérieur ; une écriture transactionnelle coûte le double.
- Contexte : Selon la doc, `UpdateItem` facture la plus grande des tailles avant et après, même si un seul attribut change : modifier un booléen d'une ligne de 3,5 Ko coûte 4 WCU. `PutItem` aussi prend la plus grande des deux ; `DeleteItem` la taille de la ligne supprimée. En mode à la demande, même calcul en unités de requête d'écriture. Garder les lignes souvent écrites petites.
- Usage : ✅ séparer un compteur chaud de la grosse fiche (`SIREN#…` / `SIREN#…#compteurs`) · ❌ incrémenter un compteur dans une ligne de 50 Ko : 50 WCU par `+1`.

```python
# Exemple 1 : calculer les WCU
import math
def wcu(avant_o, apres_o, tx=False):
    ko = math.ceil(max(avant_o, apres_o) / 1024)
    return ko * (2 if tx else 1)
wcu(300, 310)            # → 1
wcu(3500, 3510)          # → 4   (1 attribut changé)
wcu(3500, 3510, tx=True)  # → 8
wcu(1100, 900)           # → 2   (avant > après)
```

- Quiz : `UpdateItem` conditionnel sur une ligne de 2,5 Ko ; la condition est fausse, rien n'est écrit. WCU consommées ?
- [ ] 0 : aucune écriture n'a eu lieu
- [x] 3 : la condition refusée consomme quand même
- [ ] 1 : un minimum forfaitaire
- [ ] 1,5 : la moitié d'une écriture
- Réponse : 3 : selon la doc, une écriture conditionnelle refusée consomme des WCU selon la taille de la ligne (2,5 Ko arrondi à 3).

## 138. unicité : un item garde EMAIL#
- Id : dynamodb-unicite-item-garde
- Sous-thème : transactions
- Type : recette
- Niveau : 3
- Profils : web, expert
- Prérequis : dynamodb-creer-si-absent
- Source : data-platform · pwa-sync
- Définition : Pour qu'un attribut non clé soit unique (e-mail), on écrit dans la même transaction l'utilisateur et un item garde `EMAIL#<valeur>` avec `attribute_not_exists`.
- Contexte : DynamoDB n'a pas de contrainte `UNIQUE` hors clé primaire ; un index secondaire global ne l'impose pas non plus. L'item garde fait de l'e-mail une clé : son `Put` conditionnel échoue s'il existe, et la transaction annule aussi la création de l'utilisateur. Un `BatchWriteItem` ne peut pas le faire : ni condition ni atomicité. Lire d'abord « l'e-mail existe-t-il ? » laisse une course entre deux inscriptions.
- Usage : ✅ e-mail, pseudo, SIREN déclaré une seule fois · ❌ une `Query` sur un GSI avant d'écrire : deux inscriptions simultanées passent toutes les deux.

```python
# Exemple 1 : la 2e inscription échoue (moto)
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
db = boto3.resource("dynamodb", region_name="eu-west-3")
t = db.create_table(TableName="comptes",
  BillingMode="PAY_PER_REQUEST",
  KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
  AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
neuf = "attribute_not_exists(pk)"
put = lambda pk: {"Put": {"TableName": "comptes",
  "Item": {"pk": pk}, "ConditionExpression": neuf}}
tx = lambda u, mail: db.meta.client.transact_write_items(
  TransactItems=[put(f"USER#{u}"), put(f"EMAIL#{mail}")])
tx("u1", "mail-ana")
tx("u2", "mail-ana")  # ❌ TransactionCanceledException
t.scan()["Count"]  # → 2  (USER#u2 non créé)
m.stop()
```

- Quiz : `u1` change d'e-mail. Combien d'actions dans la transaction, au minimum ?
- [ ] 1 : `Update` de `USER#u1`
- [ ] 2 : `Update` de l'utilisateur et `Put` du nouvel `EMAIL#`
- [x] 3 : `Update` utilisateur, `Delete` ancien `EMAIL#`, `Put` conditionnel du nouveau
- [ ] 4 : avec un `ConditionCheck` sur `USER#u1`
- Réponse : 3 : sans supprimer l'ancien garde, l'ancien e-mail resterait réservé ; le `Put` du nouveau porte `attribute_not_exists`.

## 139. ClientRequestToken : idempotent 10 minutes
- Id : dynamodb-client-request-token
- Sous-thème : transactions
- Type : concept
- Niveau : 3
- Profils : expert
- Source : data-platform · pwa-sync
- Définition : `ClientRequestToken` (36 caractères au plus) rend un `TransactWriteItems` idempotent : renvoyé avec le même jeton dans les 10 minutes, il n'est pas rejoué.
- Contexte : Cas typique : timeout réseau, on ne sait pas si la transaction est passée ; on la renvoie avec le même jeton. Selon la doc, le jeton vaut 10 minutes après la fin de la première requête ; même jeton avec d'autres paramètres dans la fenêtre : `IdempotentParameterMismatchException`. Mesuré : moto ignore le jeton (un `ADD` renvoyé deux fois compte 2), donc ce comportement ne se teste pas en local.
- Usage : ✅ un jeton généré une fois par opération métier, réutilisé à chaque réessai · ❌ un nouveau `uuid4()` à chaque tentative : l'idempotence disparaît.

```python
# Exemple 1 : un jeton par opération
import uuid
jeton = str(uuid.uuid4())   # hors boucle
len(jeton)  # → 36  (le maximum accepté)
appels = [{"ClientRequestToken": jeton}
          for essai in range(3)]
len({a["ClientRequestToken"] for a in appels})
# → 1   (3 essais, un seul jeton)
```

- Quiz : Transaction `ADD vues 1`, renvoyée avec le même jeton 15 minutes après la première réussite. Résultat ?
- [ ] Ignorée : le jeton est déjà connu
- [ ] `IdempotentParameterMismatchException`
- [x] Rejouée : `vues` augmente une seconde fois
- [ ] `TransactionCanceledException`
- Réponse : rejouée : passé 10 minutes, la doc dit que la requête est traitée comme nouvelle ; l'idempotence ne vaut que dans la fenêtre.

## 140. transactions : coût double
- Id : dynamodb-transaction-cout-double
- Sous-thème : transactions
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Source : data-platform · pwa-sync
- Définition : Une transaction consomme le double : 2 WCU par Ko écrit, 2 RCU par 4 Ko lus, même annulée.
- Contexte : Selon la doc, DynamoDB fait deux opérations par item : préparer, puis valider. Exemple de la doc : 3 items de 500 octets par seconde = 6 WCU. Une transaction annulée (`ConditionalCheckFailed`) consomme la même capacité qu'une réussie. Mesuré avec moto : `TransactGetItems` d'un item renvoie `CapacityUnits` 2.0. D'où le conseil de la doc : petites transactions, et `BatchWriteItem` pour la masse.
- Usage : ✅ transactions courtes, seulement quand l'atomicité est nécessaire · ❌ transaction de 100 actions pour un chargement : capacité doublée sans besoin.

```python
# Exemple 1 : WCU d'une transaction
import math
tailles = [500, 500, 500]   # octets
simple = sum(math.ceil(s / 1024) for s in tailles)
tx = 2 * simple
(simple, tx)  # → (3, 6)
```

- Quiz : Une transaction de 3 `Put` est annulée par un `ConditionCheck` faux. Combien de capacité consommée ?
- [ ] 0 : rien n'a été écrit
- [ ] Seulement celle du `ConditionCheck`
- [x] Comme une transaction réussie
- [ ] La moitié : préparation sans validation
- Réponse : comme une réussie : selon la doc, une transaction annulée consomme la capacité de lecture ou d'écriture des items tentés.

## 141. à la demande : doubler le pic en 30 minutes
- Id : dynamodb-a-la-demande-double-pic
- Sous-thème : capacité
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Source : data-platform · pwa-sync
- Définition : Une table à la demande absorbe aussitôt le double de son pic précédent ; dépasser ce double en moins de 30 minutes peut être limité.
- Contexte : Selon la doc, une table neuve à la demande tient 4 000 écritures/s et 12 000 lectures/s ; la capacité monte ensuite avec le trafic. Pour aller au-delà du double, étaler la montée sur 30 minutes ou préchauffer (warm throughput). Autre limite, indépendante du mode : une partition sert au plus 1 000 WCU et 3 000 RCU par seconde ; une `pk` chaude est limitée même à la demande.
- Usage : ✅ montée progressive ou préchauffage avant un import massif · ❌ croire qu'« à la demande » veut dire « jamais de throttling ».

```python
# Exemple 1 : ce qui passe tout de suite
pic_precedent = 50_000       # lectures/s
instantane = 2 * pic_precedent
instantane  # → 100000
demande = 80_000
demande <= instantane  # → True  (sans throttling)
```

- Quiz : Toutes les écritures d'un import vont sur `pk = "BODACC#2026-10-24"`, 5 000 écritures/s de 1 Ko, table à la demande. Résultat ?
- [ ] Tout passe : le mode à la demande s'adapte
- [ ] Tout passe après 30 minutes de montée
- [x] Limité : une partition plafonne à 1 000 WCU/s
- [ ] Refusé : 4 000 écritures/s par table au maximum
- Réponse : limité : une seule `pk` = une partition, plafonnée à 1 000 WCU/s selon la doc ; répartir sur plusieurs `pk` (par SIREN).

## 142. on_demand_throughput : plafonner une table
- Id : dynamodb-plafond-a-la-demande
- Sous-thème : capacité
- Type : recette
- Niveau : 3
- Profils : ops
- Source : data-platform · pwa-sync
- Définition : `on_demand_throughput` fixe un maximum de lectures et d'écritures par seconde sur une table à la demande ; au-delà, `ThrottlingException`.
- Contexte : Garde-fou de coût : une boucle folle dans une Lambda ne peut plus écrire sans limite. Selon la doc, la valeur minimale est 1 unité/s, le plafond est appliqué « au mieux » (la burst capacity peut le dépasser un moment) et se modifie à tout moment. Sans réglage, seul le quota du compte (40 000 unités/s par table par défaut) borne le débit. Existe aussi par index secondaire global.
- Usage : ✅ tables de dev, tables d'apprentissage, protection d'un service en aval · ❌ un plafond sous le pic réel de prod : throttling permanent.

```hcl
# Exemple 1 : au plus 50 écritures/s
resource "aws_dynamodb_table" "progress" {
  name         = "${local.prefix}-progress"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"
  on_demand_throughput {
    max_write_request_units = 50
    max_read_request_units  = 200
  }
}
```

- Quiz : Pour retirer le plafond d'écriture sans recréer la table, quelle valeur dans Terraform ?
- [ ] `0`
- [x] `-1`
- [ ] `null` sur `on_demand_throughput`
- [ ] `40000`
- Réponse : `-1` : selon la doc du provider (`aws_dynamodb_table`), on le fixe avec une valeur ≥ 1 et on le retire avec `-1`.

## 143. warm throughput : préchauffer avant un pic
- Id : dynamodb-warm-throughput
- Sous-thème : capacité
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Prérequis : dynamodb-a-la-demande-double-pic
- Source : data-platform · pwa-sync
- Définition : Le warm throughput est le débit qu'une table supporte instantanément ; on peut l'augmenter d'avance (préchauffage) avant un pic prévu, sans changer de mode.
- Contexte : Selon la doc, chaque table a des valeurs par défaut gratuites, relevées avec l'usage ; les augmenter soi-même est facturé. Une fois augmenté, le warm throughput d'une table ne peut plus baisser (celui d'un index secondaire global, si, selon la doc du provider). Minimums Terraform : 12 000 lectures/s, 4 000 écritures/s. Il évite le throttling de la règle « double du pic en 30 min ».
- Usage : ✅ import massif ou lancement prévu, sur une table neuve · ❌ préchauffer « au cas où » : payé, et irréversible pour la table.

```hcl
# Exemple 1 : prêt pour 20 000 écritures/s
resource "aws_dynamodb_table" "annonces" {
  name         = "${local.prefix}-annonces"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  warm_throughput {
    write_units_per_second = 20000
    read_units_per_second  = 12000
  }
}
```

- Quiz : Après l'import, on remet `write_units_per_second = 4000` sur la table. Résultat ?
- [ ] Retour à 4 000, facturation arrêtée
- [ ] Retour à 4 000 au bout de 24 h
- [x] Impossible : la valeur d'une table ne baisse pas
- [ ] La table est recréée avec 4 000
- Réponse : impossible : selon la doc, une fois augmenté, le warm throughput d'une table ne peut plus être réduit (un GSI, lui, peut baisser).

## 144. Kinesis Data Streams : l'autre flux de changements
- Id : dynamodb-kinesis-data-streams
- Sous-thème : exploitation
- Type : comparaison
- Niveau : 3
- Profils : data, expert
- Prérequis : dynamodb-streams-vues
- Source : data-platform · pwa-sync
- Définition : Une table peut publier ses changements dans Kinesis Data Streams, plus long et partageable que DynamoDB Streams, sans ordre garanti ni dédoublonnage.
- Contexte : Rétention Kinesis de 24 h à 365 jours, fan-out amélioré pour plusieurs consommateurs, Firehose vers S3 sans code. En échange (doc) : des enregistrements peuvent arriver dans le désordre ou en double ; on compare `ApproximateCreationDateTime` pour ordonner et dédoublonner. Un seul flux Kinesis par table, même compte et même région. Facturation : Kinesis + unités de capture DynamoDB (1 Ko de changement par unité).
- Usage : ✅ plusieurs consommateurs, rejeu sur plusieurs jours, Firehose vers le data lake · ❌ logique qui suppose l'ordre par item sans dédoublonner : DynamoDB Streams.

```python
# Exemple 1 : dédoublonner, garder le plus récent
recs = [
  {"k": "u1#V#mac", "t": 1002, "vues": 7},
  {"k": "u1#V#mac", "t": 1001, "vues": 6},
  {"k": "u1#V#mac", "t": 1002, "vues": 7},  # doublon
]
dernier = {}
for r in recs:
    if r["k"] not in dernier or r["t"] > dernier[r["k"]]["t"]:
        dernier[r["k"]] = r
dernier["u1#V#mac"]["vues"]  # → 7
```

- Quiz : Le consommateur ajoute `vues` à un total à chaque enregistrement Kinesis reçu. Risque ?
- [ ] Aucun : Kinesis livre chaque changement une fois
- [ ] Total trop bas : Kinesis échantillonne
- [x] Total faux : doublons possibles, ordre non garanti
- [ ] Erreur : les images ne contiennent pas `vues`
- Réponse : total faux : la doc prévient que les enregistrements peuvent être dupliqués ou désordonnés ; il faut un traitement idempotent (dernier état par clé).

## 145. MRSC : cohérence forte entre régions
- Id : dynamodb-global-tables-mrsc
- Sous-thème : exploitation
- Type : comparaison
- Niveau : 3
- Profils : ops, expert
- Prérequis : dynamodb-global-tables-mrec
- Source : data-platform · pwa-sync
- Définition : Une global table en MRSC réplique chaque écriture de façon synchrone : une lecture forte renvoie la dernière version dans n'importe quelle région (RPO zéro).
- Contexte : Choisi à la création, non modifiable. Exactement trois régions : trois réplicas, ou deux réplicas et un témoin (sans lecture ni écriture). Table vide à la conversion. Pas de TTL, pas de transactions, pas de LSI. Écritures et lectures fortes plus lentes (aller-retour entre régions) ; écriture concurrente du même item : `ReplicatedWriteConflictException`, à réessayer. Disponible dans une liste de régions, dont Paris.
- Usage : ✅ RPO zéro exigé, lecture forte multi-région (soldes, stocks) · ❌ données expirées par TTL, transactions, ou latence d'écriture minimale : MREC.

```
# Exemple 1 : MREC ou MRSC
                MREC (défaut)   MRSC
Réplication     asynchrone      synchrone
Régions         autant que voulu  exactement 3
Conflit         dernier gagne   ReplicatedWrite-
                                ConflictException
TTL / transac.  oui / locale    non / non
RPO             ~ secondes      0
```

- Quiz : MREC, item écrit à Paris il y a 200 ms ; lecture `ConsistentRead=True` à Francfort. Résultat ?
- [ ] Toujours la nouvelle version : lecture forte
- [x] Peut-être l'ancienne version
- [ ] `ValidationException` : lecture forte interdite
- [ ] La requête attend la fin de la réplication
- Réponse : peut-être l'ancienne : en MREC, une lecture forte n'est forte que pour les écritures faites dans sa région (doc) ; seul MRSC garantit la dernière version partout.

## 146. clé client désactivée : table inaccessible
- Id : dynamodb-cle-kms-desactivee
- Sous-thème : sécurité
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : dynamodb-chiffrement-kms
- Voir aussi : kms-cle-desactivee
- Source : data-platform · pwa-sync
- Définition : Si la clé KMS client d'une table est désactivée ou programmée pour suppression, la table devient inaccessible : plus aucune lecture ni écriture.
- Contexte : DynamoDB envoie un e-mail et laisse sept jours pour rendre l'accès à la clé (doc). Au-delà, la table est archivée : DynamoDB crée une sauvegarde facturée, restaurable seulement si la dernière clé est réactivée. La clé n'est pas appelée à chaque requête : rafraîchie toutes les 5 minutes par appelant actif. C'est le risque propre à la clé client, absent avec la clé détenue par AWS.
- Usage : ✅ alarme sur la désactivation ou la suppression programmée de la clé, droits KMS bornés · ❌ clé client partagée par des tables de projets différents : un geste coupe tout.

```bash
# Exemple 1 : constater l'état
aws dynamodb describe-table \
  --table-name "$table" \
  --query Table.TableStatus
# → "INACCESSIBLE_ENCRYPTION_CREDENTIALS"
#   (après désactivation de la clé)
# au-delà de 7 jours : ARCHIVING, ARCHIVED
aws kms enable-key --key-id "$key_id"
# → la table redevient ACTIVE
```

- Quiz : Clé client désactivée par erreur il y a 10 jours. État de la table ?
- [ ] `ACTIVE` : DynamoDB garde une copie de la clé
- [ ] Supprimée définitivement avec ses données
- [x] Archivée : sauvegarde à restaurer, clé réactivée
- [ ] Inaccessible jusqu'à réactivation, sans limite
- Réponse : archivée : après sept jours sans accès à la clé, la table est archivée et une sauvegarde facturée est créée ; la restaurer exige la clé réactivée (doc).

## 147. aws:sourceVpce : Deny et IfExists
- Id : dynamodb-iam-source-vpce
- Sous-thème : sécurité
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : dynamodb-politique-endpoint
- Voir aussi : iam-condition-null
- Source : data-platform · pwa-sync
- Définition : Dans la politique de ressource d'une table, un `Deny` si `aws:sourceVpce` diffère de notre endpoint force tout accès à passer par le VPC.
- Contexte : Exemple de la doc : `Effect: Deny`, `Principal: *`, `StringNotEquals` sur `aws:sourceVpce`. C'est un `Deny` explicite : il gagne sur tout `Allow`, administrateur compris. Piège : une requête hors VPC n'a pas de `sourceVpce`, la condition est vraie, donc refus ; avec `dynamodb:*`, la console, la CI et `terraform plan` depuis un poste sont bloqués. Les Lambda de data-platform, hors VPC, le seraient aussi.
- Usage : ✅ table sensible lue seulement depuis un VPC, Deny limité aux actions de données · ❌ `dynamodb:*` sans exempter le rôle de déploiement : Terraform ne lit plus la table.

```json
# Exemple 1 : hors endpoint, refus (doc)
{"Effect": "Deny", "Principal": "*",
 "Action": "dynamodb:*",
 "Resource": "<arn de la table>",
 "Condition": {"StringNotEquals": {
   "aws:sourceVpce": "vpce-11aa22bb"}}}
# Lambda du VPC via vpce-11aa22bb → OK
# poste du dev, CI hors VPC → refusé
```

```python
# Exemple 2 : la condition, en Python
def refuse(src):     # src : vpce ou None
    return src != "vpce-11aa22bb"
refuse("vpce-11aa22bb")   # → False
refuse(None)              # → True
```

- Quiz : On remplace `StringNotEquals` par `StringNotEqualsIfExists`. Une requête venue d'Internet, sans `sourceVpce` ?
- [ ] Permise : la clé est absente, la condition est ignorée
- [x] Refusée : clé absente, `IfExists` rend la condition vraie
- [ ] Permise : `IfExists` exempte les requêtes publiques
- [ ] Rejetée à l'enregistrement : opérateur invalide en `Deny`
- Réponse : refusée (selon la doc IAM) : avec `…IfExists`, une clé absente rend la condition vraie ; un `Deny` à opérateur négatif refuse donc quand même.
