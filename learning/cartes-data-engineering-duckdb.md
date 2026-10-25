---
title: "Cartes · DuckDB"
type: cartes
langage: Data engineering
cours: DuckDB
created: 2026-10-25
updated: 2026-10-25
---

# Cartes · DuckDB
Data engineering · DuckDB : lire, s3, sql, session, choisir (format spec v3 de revision-pwa).

## 1. read_json_auto : un .jsonl.gz lu tel quel
- Sous-thème : lire
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `read_json_auto('f.jsonl.gz')` lit un fichier JSON Lines comme une table, en devinant colonnes et types ; le gzip est détecté par l'extension.
- Contexte : Pas de décompression préalable, pas de schéma à déclarer : DuckDB échantillonne les lignes pour typer les colonnes. C'est un moteur SQL embarqué, sans serveur (≈ SQLite pour l'analytique). Un chemin seul dans le `FROM` marche aussi (`FROM 'f.jsonl.gz'`) : DuckDB choisit le lecteur d'après l'extension.
- Usage : ✅ ouvrir un fichier du data lake pour vérifier un compte, une valeur, un schéma · ❌ fichier sans extension reconnue : préciser `format` et `compression`.

```sql
-- Exemple 1 : compter les annonces
SELECT count(*)
FROM read_json_auto(
  'bodacc/date=2026-10-20/part-0001.jsonl.gz');
-- → 3
```

```sql
-- Exemple 2 : le chemin seul suffit
SELECT familleavis, count(*) AS n
FROM 'bodacc/date=2026-10-20/part-0001.jsonl.gz'
GROUP BY 1 ORDER BY 1;
-- → creation 1
--   dpc      2
```

- Quiz : Que fait `read_json_auto('part-0001.jsonl')` si le fichier est gzippé mais nommé sans `.gz` ?
- [ ] Le lit normalement : gzip détecté au contenu
- [x] Échoue : il le lit comme du texte
- [ ] Renvoie une table vide
- Réponse : échoue (mesuré : `Malformed JSON … at byte 1`) : la compression se déduit de l'extension ; sans `.gz`, préciser `compression = 'gzip'`.

## 2. glob : plusieurs fichiers dans un FROM
- Sous-thème : lire
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Un motif `*`, `**` ou `[..]` dans le chemin lit tous les fichiers qui correspondent comme une seule table.
- Contexte : `date=*/part-*.jsonl.gz` couvre toutes les partitions et tous les parts : c'est ce qui rend la convention du bucket raw interrogeable d'un coup. `**` descend dans tous les sous-dossiers. Une liste explicite `['a.gz', 'b.gz']` est aussi acceptée. Le motif doit viser le bon suffixe : `*.json` ne prend pas les `.jsonl.gz`, mais attrape les `_MANIFEST.json`.
- Usage : ✅ lire une source entière ou une plage de dates par motif · ❌ motif trop large (`**/*`) qui mélange données et manifests : viser `part-*.jsonl.gz`.

```sql
-- Exemple 1 : toutes les journées
SELECT count(*)
FROM read_json_auto(
  'bodacc/date=*/part-*.jsonl.gz');
-- → 4   (3 + 1, deux journées)
```

```sql
-- Exemple 2 : deux jours précis
SELECT count(*)
FROM read_json_auto(
  'bodacc/date=2026-10-2[01]/part-*.jsonl.gz');
-- → 4
```

- Quiz : Même arborescence : que compte `read_json_auto('bodacc/*/*.json')` ?
- [ ] Les 4 annonces
- [ ] Rien : erreur, aucun fichier
- [x] Le seul manifest : 1 ligne
- [ ] Les annonces et le manifest : 5
- Réponse : 1 ligne (mesuré) : `*.json` ne correspond qu'à `_MANIFEST.json` ; les parts finissent par `.jsonl.gz`.

## 3. No files found : le motif ne trouve rien
- Sous-thème : lire
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Un motif qui ne correspond à aucun fichier lève `IO Error: No files found that match the pattern`, au lieu de rendre une table vide.
- Contexte : C'est ce qui arrive avec une source pas encore ingérée (`raw('inpi')`) ou une faute dans le suffixe. L'erreur est utile : une table vide ferait croire à une journée sans annonce. Lire le motif affiché, il montre le chemin réellement construit (bucket, source, suffixe).
- Usage : ✅ lire le motif du message pour trouver la faute · ❌ conclure « pas de données » : vérifier d'abord le chemin avec `aws s3 ls`.

```sql
-- Exemple 1 : source absente
SELECT * FROM raw('inpi');
-- → IO Error: No files found that
--   match the pattern "s3://$RAW_BUCKET
--   /inpi/date=*/part-*.jsonl.gz"
```

- Quiz : Les fichiers sont des `.jsonl.gz`. Que donne `read_json_auto('bodacc/date=*/part-*.jsonl')` ?
- [ ] Les 4 annonces
- [ ] Une table vide
- [x] `No files found that match the pattern`
- Réponse : `No files found` (mesuré) : le motif est comparé au nom complet ; `part-*.jsonl` ne correspond pas à `part-0001.jsonl.gz`.

## 4. DESCRIBE : le schéma deviné
- Sous-thème : sql
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `DESCRIBE SELECT …` affiche les colonnes et les types que DuckDB a déduits, sans renvoyer les lignes.
- Contexte : Premier réflexe sur un fichier inconnu : vérifier qu'un SIREN est bien lu en `VARCHAR` (en nombre, un zéro initial serait perdu), qu'une date est une `DATE`. Une colonne absente de certains fichiers apparaît quand même, à `NULL` là où elle manque. `DESCRIBE` s'applique aussi à une table, une vue ou une macro.
- Usage : ✅ contrôler les types avant d'écrire une requête ou un job · ❌ deviner les types à partir de quelques lignes affichées : `DESCRIBE`.

```sql
-- Exemple 1 : colonnes et types
DESCRIBE SELECT * FROM read_json_auto(
  'bodacc/date=*/part-*.jsonl.gz');
-- → id          varchar
--   familleavis varchar
--   siren       varchar
--   tribunal    varchar
--   date        date
```

- Quiz : `tribunal` n'existe que dans le part du 21. Que vaut `tribunal` pour les annonces du 20 ?
- [ ] La colonne n'existe pas pour elles
- [x] `NULL`
- [ ] Une chaîne vide
- [ ] Erreur : schémas différents
- Réponse : `NULL` (mesuré) : DuckDB réunit les colonnes de tous les fichiers échantillonnés et complète par `NULL`.

## 5. SUMMARIZE : le profil des colonnes
- Sous-thème : sql
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `SUMMARIZE SELECT …` calcule pour chaque colonne min, max, nombre approché de valeurs distinctes, quartiles et pourcentage de `NULL`.
- Contexte : Un profil de qualité en une ligne : `null_percentage` montre une colonne à moitié vide, `approx_unique` un identifiant qui devrait être unique et ne l'est pas, min et max une date hors plage. Les distincts sont approchés (HyperLogLog) : pour un contrôle exact, `count(DISTINCT …)`.
- Usage : ✅ premier coup d'œil sur une nouvelle journée ou une nouvelle source · ❌ preuve d'unicité : `count(*) = count(DISTINCT id)`.

```sql
-- Exemple 1 : profil des annonces
SUMMARIZE SELECT * FROM read_json_auto(
  'bodacc/date=*/part-*.jsonl.gz');
-- → id       approx_unique 4  null 0.00
--   siren    approx_unique 2  null 0.00
--   tribunal approx_unique 1  null 75.00
```

- Quiz : Pourquoi `tribunal` a-t-il `null_percentage` à 75 ?
- [ ] 3 tribunaux sur 4 sont inconnus de l'API
- [x] 3 annonces sur 4 n'ont pas le champ
- [ ] SUMMARIZE n'échantillonne que 25 % des lignes
- Réponse : 3 sur 4 sans le champ : seules les annonces du 21 portent `tribunal`, les autres sont complétées par `NULL`.

## 6. filename = true : d'où vient la ligne
- Sous-thème : lire
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `filename = true` ajoute une colonne `filename` avec le chemin du fichier qui a fourni chaque ligne.
- Contexte : Indispensable dès qu'un glob lit plusieurs fichiers : retrouver le part d'une ligne suspecte, compter par fichier, repérer un part orphelin d'un ancien run. Sur S3, la colonne contient l'URL `s3://…` complète.
- Usage : ✅ déboguer une lecture multi-fichiers, vérifier qu'aucun part inattendu n'est lu · ❌ `filename` dans une table finale : la date de partition suffit.

```sql
-- Exemple 1 : lignes par fichier
SELECT filename, count(*) AS n
FROM read_json_auto(
  'bodacc/date=*/part-*.jsonl.gz',
  filename = true)
GROUP BY 1 ORDER BY 1;
-- → …date=2026-10-20/part-0001.jsonl.gz  3
--   …date=2026-10-21/part-0001.jsonl.gz  1
```

- Quiz : Un rejeu a laissé un `part-0003` orphelin. Quelle requête le révèle le plus vite ?
- [ ] `SUMMARIZE` sur la partition
- [x] `count(*)` par `filename`
- [ ] `DESCRIBE` sur la partition
- [ ] `count(DISTINCT id)` sur la partition
- Réponse : `count(*)` par `filename` : le part orphelin apparaît comme une ligne de plus, avec son nom.

## 7. duckdb : en mémoire ou dans un fichier
- Sous-thème : session
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `duckdb` sans argument ouvre une base en mémoire, perdue en sortant ; `duckdb lab.duckdb` ouvre ou crée une base persistante dans ce fichier.
- Contexte : En mémoire, tables, vues, macros et secrets disparaissent à la fermeture : d'où un fichier `-init` qui les recrée à chaque `make duckdb`. Un fichier `.duckdb` garde tout, mais ne s'ouvre en écriture que par un processus à la fois. `-c "…"` lance une requête puis quitte, pratique dans un script.
- Usage : ✅ en mémoire pour explorer le lake (rien à nettoyer) · ❌ base persistante commitée dans le repo : la recréer par script.

```bash
# Exemple 1 : la vue ne survit pas
duckdb -c "CREATE VIEW v AS SELECT 1 x"
duckdb -c "SELECT * FROM v"
# → Catalog Error: Table with name v
#   does not exist!
```

```bash
# Exemple 2 : dans un fichier, elle reste
duckdb lab.duckdb -c "CREATE VIEW v AS
  SELECT 1 AS x"
duckdb lab.duckdb -c "SELECT * FROM v"
# → 1
```

- Quiz : Que fait `echo "SELECT 2;" | duckdb -c "SELECT 1"` ?
- [ ] Affiche 1 puis 2
- [x] Affiche 1, ignore l'entrée standard
- [ ] Affiche 2 seulement
- [ ] Erreur : deux sources de requêtes
- Réponse : affiche 1 (mesuré) : `-c` exécute sa requête et quitte, sans lire stdin.

## 8. httpfs : lire s3:// directement
- Sous-thème : s3
- Niveau : 1
- Source : data-platform · S1-07
- Définition : L'extension `httpfs` fait lire à DuckDB des chemins `s3://` et `https://` comme des fichiers locaux, globs compris.
- Contexte : `INSTALL httpfs` télécharge l'extension une fois (dans `~/.duckdb/extensions`) ; `LOAD httpfs` l'active pour la session. Pour un glob, DuckDB liste le préfixe (`ListObjectsV2`) puis lit chaque objet par requêtes HTTP `Range`. Rien n'est copié en local : chaque requête relit S3, et les octets lus sont facturés en transfert hors d'AWS.
- Usage : ✅ interroger le bucket raw depuis le poste, sans téléchargement · ❌ relire 50 fois la même grosse table : la copier une fois en local (`COPY … TO`).

```sql
-- Exemple 1 : une journée sur S3
INSTALL httpfs; LOAD httpfs;
SELECT count(*)
FROM read_json_auto('s3://'
  || getenv('RAW_BUCKET')
  || '/bodacc/date=2026-10-20/'
  || 'part-0001.jsonl.gz');
-- → 32373
```

- Quiz : Base neuve, sans `INSTALL` ni `LOAD` : que fait `SELECT … FROM read_json_auto('s3://…')` ?
- [ ] `Catalog Error` : extension non chargée
- [x] Charge `httpfs` tout seul et lit
- [ ] Lit le chemin comme un fichier local
- Réponse : charge `httpfs` tout seul (mesuré : l'erreur renvoyée est un vrai `HTTP 404` de S3) ; l'autochargement couvre les extensions connues.

## 9. installer : le binaire officiel
- Sous-thème : session
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Le CLI DuckDB est un seul exécutable : le binaire de la release GitHub, posé dans `~/.local/bin`, suffit, sans compilation.
- Contexte : Erreur vue : `brew install duckdb` a voulu compiler sur un Mac Intel et s'est arrêté sur `Your Xcode (15.2) is too outdated`. Le binaire officiel évite toute chaîne de build. En v2, les noms d'assets ont changé (`duckdb-cli-osx-amd64.tar.gz`) : un lien deviné sur l'ancien nom renvoie `Not Found` ; lister les assets avec `gh release view`.
- Usage : ✅ poste sans Xcode récent, CI, conteneur : télécharger le binaire de la release · ❌ deviner l'URL d'un asset : la lire dans la release.

```bash
# Exemple 1 : lister puis télécharger
gh release view v2.0.0 \
  --repo duckdb/duckdb \
  --json assets -q '.assets[].name' \
  | grep cli-osx
# → duckdb-cli-osx-amd64.tar.gz …
duckdb --version
# → v2.0.0 (Cyanoptera)
```

- Quiz : Pourquoi Homebrew a-t-il demandé Xcode pour installer DuckDB ?
- [ ] DuckDB exige Xcode pour fonctionner
- [x] Pas de binaire précompilé pour ce Mac : il compilait
- [ ] Les extensions sont compilées à l'installation
- Réponse : il compilait : sans bouteille (bottle) adaptée à la machine, Homebrew construit depuis les sources, avec la chaîne Xcode.

## 10. hive_partitioning : la date vient du chemin
- Sous-thème : lire
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Les dossiers `clé=valeur` du chemin deviennent des colonnes : `date=2026-10-20/` ajoute une colonne `date`, typée `DATE`.
- Contexte : La valeur n'est pas dans le fichier, seulement dans le chemin : c'est la convention Hive, lue aussi par Athena et Spark. DuckDB détecte ces dossiers tout seul ; `hive_partitioning = true` l'écrit explicitement, `false` retire la colonne. Le type est deviné (`DATE`, entier, texte) : comparer avec une date, pas avec un nombre.
- Usage : ✅ filtrer et grouper par journée sans champ date dans les annonces · ❌ dupliquer la date dans chaque ligne du fichier pour pouvoir filtrer.

```sql
-- Exemple 1 : la colonne date
SELECT date, typeof(date) AS t,
       count(*) AS n
FROM read_json_auto(
  'bodacc/date=*/part-*.jsonl.gz',
  hive_partitioning = true)
GROUP BY 1, 2 ORDER BY 1;
-- → 2026-10-20  DATE  3
--   2026-10-21  DATE  1
```

- Quiz : Même lecture sans écrire `hive_partitioning` : la colonne `date` existe-t-elle ?
- [x] Oui : détectée dans le chemin
- [ ] Non : l'option vaut `false` par défaut
- [ ] Oui, mais en `VARCHAR`
- Réponse : oui (mesuré, v2.0.0) : la détection est automatique ; l'option explicite documente l'intention.

## 11. secret credential_chain : les identifiants AWS
- Sous-thème : s3
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `CREATE SECRET (TYPE s3, PROVIDER credential_chain)` fait chercher à DuckDB les identifiants comme le SDK AWS : variables d'environnement, puis profil `~/.aws`.
- Contexte : Rien n'est écrit dans le SQL : le profil vient de `AWS_PROFILE`, posé par le Makefile. `CHAIN 'env;config'` limite la recherche à ces deux sources. Un secret créé sans `PERSISTENT` vit le temps de la session. `duckdb_secrets()` liste les secrets actifs, valeurs masquées. Il faut l'extension `aws` en plus de `httpfs`.
- Usage : ✅ poste de dev avec profils SSO ou clés dans `~/.aws` · ❌ `KEY_ID` et `SECRET` en clair dans un fichier SQL commité.

```sql
-- Exemple 1 : le secret de tools/duckdb_init.sql
INSTALL aws; LOAD aws;
CREATE OR REPLACE SECRET s3_data_platform (
  TYPE s3, PROVIDER credential_chain,
  CHAIN 'env;config', REGION 'eu-west-3');
SELECT name, provider, persistent
FROM duckdb_secrets();
-- → s3_data_platform credential_chain false
```

- Quiz : Le secret est créé dans une session `duckdb` en mémoire. Qu'en reste-t-il à la session suivante ?
- [ ] Il est enregistré dans `~/.duckdb`
- [x] Rien : il faut le recréer
- [ ] Il est copié dans `~/.aws/config`
- Réponse : rien : sans `PERSISTENT`, un secret est temporaire ; le fichier `-init` le recrée à chaque `make duckdb`.

## 12. HTTP 403 : pas d'identifiants
- Sous-thème : s3
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Sans identifiants valides, DuckDB lit S3 en anonyme : un bucket privé répond `HTTP 403 Forbidden` dès le listage du glob.
- Contexte : Le message cite le préfixe listé (`listing 's3://…/bodacc/date='`), pas un fichier : c'est le `ListObjectsV2` du glob qui est refusé. Causes : secret non créé, `AWS_PROFILE` vide, jeton SSO expiré, rôle sans `s3:ListBucket`. Un bucket inexistant répond `404` : 403 dit « il existe, mais pas pour toi ».
- Usage : ✅ lire 403 comme un problème d'identité ou de droits · ❌ chercher une faute dans le motif : c'est l'accès, pas le chemin.

```sql
-- Exemple 1 : sans secret ni profil
SELECT count(*)
FROM read_json_auto('s3://'
  || getenv('RAW_BUCKET')
  || '/bodacc/date=*/_MANIFEST.json');
-- → HTTP Error: HTTP GET error listing
--   's3://$RAW_BUCKET/bodacc/date='
--   (HTTP 403 Forbidden)
```

- Quiz : Même requête sur un bucket qui n'existe pas : quelle erreur ?
- [ ] `HTTP 403 Forbidden`
- [x] `HTTP 404 Not Found`
- [ ] `No files found that match the pattern`
- Réponse : `404 Not Found` (mesuré) : le listage échoue avant même de chercher des fichiers.

## 13. vue de session : rien n'est copié
- Sous-thème : sql
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `CREATE VIEW bodacc AS SELECT … FROM read_json_auto('s3://…')` nomme une requête ; chaque `SELECT` sur la vue relit les fichiers.
- Contexte : Une vue ne stocke aucune donnée : c'est l'équivalent local et temporaire d'une table Glue, qui elle aussi ne fait que pointer vers S3. Avantage : toujours à jour, une journée ingérée apparaît sans rien faire. Coût : chaque requête relit S3. Pour enchaîner beaucoup de requêtes, `CREATE TABLE t AS SELECT …` copie une fois en mémoire.
- Usage : ✅ nommer une source du lake pour la session · ❌ dizaines de requêtes lourdes sur la même vue S3 : `CREATE TABLE … AS` une fois.

```sql
-- Exemple 1 : la vue relit les fichiers
CREATE VIEW v AS
SELECT * FROM read_json_auto(
  'bodacc/date=*/part-*.jsonl.gz');
SELECT count(*) FROM v;
-- → 4
```

- Quiz : Une nouvelle journée arrive dans le bucket pendant la session. Que donne `SELECT count(*) FROM v` ?
- [ ] L'ancien total : la vue a figé les fichiers
- [x] Le nouveau total
- [ ] Une erreur : vue périmée
- Réponse : le nouveau total : le glob est réévalué à chaque requête ; une vue ne garde que le texte de la requête.

## 14. macro table : la source en paramètre
- Sous-thème : sql
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `CREATE MACRO raw(source) AS TABLE SELECT …` crée une fonction qui renvoie une table, appelée dans un `FROM` : `FROM raw('bodacc')`.
- Contexte : Une vue par source obligerait à modifier le fichier d'init à chaque nouvelle source. La macro construit le chemin à partir du paramètre et de la convention `<source>/date=*/part-*.jsonl.gz` : une source ajoutée n'ajoute rien. Elle s'appelle toujours avec ses parenthèses et ses arguments, comme une fonction.
- Usage : ✅ même lecture répétée pour plusieurs sources ou préfixes · ❌ requête unique sans paramètre : une vue suffit.

```sql
-- Exemple 1 : une macro par convention
CREATE MACRO raw(source) AS TABLE
SELECT * FROM read_json_auto(
  source || '/date=*/part-*.jsonl.gz');
SELECT familleavis, count(*) AS n
FROM raw('bodacc')
GROUP BY 1 ORDER BY 1;
-- → creation 1
--   dpc      2
--   vente    1
```

- Quiz : Que donne `SELECT * FROM raw` (sans parenthèses) avec la macro de l'exemple ?
- [ ] Toutes les sources
- [ ] La macro appelée avec `NULL`
- [x] `Catalog Error` : table `raw` introuvable
- Réponse : `Catalog Error` (mesuré) : sans parenthèses, DuckDB cherche une table ou une vue nommée `raw`.

## 15. getenv : une chaîne vide, pas NULL
- Sous-thème : session
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `getenv('RAW_BUCKET')` lit une variable d'environnement du processus `duckdb` ; une variable absente donne une chaîne vide.
- Contexte : C'est ce qui garde le numéro de compte hors du repo : le Makefile pose `RAW_BUCKET` depuis les outputs Terraform, le SQL ne contient que `getenv`. Piège : variable oubliée → `''`, pas `NULL` ; le chemin devient `s3:///bodacc/…` et l'erreur parle de S3, pas de la variable.
- Usage : ✅ injecter bucket, région ou préfixe dans un SQL commité · ❌ tester l'absence avec `IS NULL` : comparer à `''`.

```bash
# Exemple 1 : présente et absente
RAW_BUCKET=dp-raw duckdb -csv -c "
  SELECT getenv('RAW_BUCKET') AS b,
         getenv('NOPE') = '' AS vide"
# → dp-raw,true
```

- Quiz : Que vaut `getenv('NOPE') IS NULL` quand `NOPE` n'est pas définie ?
- [ ] `true`
- [x] `false`
- [ ] Erreur : variable inconnue
- Réponse : `false` (mesuré) : `getenv` renvoie `''` pour une variable absente, jamais `NULL`.

## 16. -init s'exécute avant -cmd
- Sous-thème : session
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Au lancement, le CLI exécute le fichier `-init`, puis les commandes `-cmd`, puis ce qui arrive sur l'entrée standard ou au clavier.
- Contexte : Erreur vue : passer le bucket par `-cmd "SET VARIABLE b = …"` pour l'utiliser dans `-init` ne marche pas, l'init a déjà tourné et `getvariable('b')` y vaut `NULL`. D'où une variable d'environnement, lue par `getenv`, qui existe avant le démarrage. `-cmd` sert à ce qui doit suivre l'init (réglage d'affichage, première requête).
- Usage : ✅ configuration dans l'environnement ou dans le fichier d'init lui-même · ❌ `-cmd` pour préparer une valeur que l'init utilise.

```bash
# Exemple 1 : l'ordre réel
echo "SELECT 'init', getvariable('b');" \
  > init.sql
duckdb -init init.sql \
  -cmd "SET VARIABLE b = 'x';
        SELECT 'cmd', getvariable('b');"
# → init  NULL
#   cmd   x
```

- Quiz : Dans l'exemple, une requête tapée ensuite au clavier lit `getvariable('b')` : que vaut-il ?
- [x] `x`
- [ ] `NULL`
- [ ] Erreur : variable de `-cmd` perdue
- Réponse : `x` (mesuré, via stdin) : `-cmd` a tourné avant la saisie, la variable vit jusqu'à la fin de la session.

## 17. COPY TO : écrire du Parquet partitionné
- Sous-thème : sql
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `COPY (SELECT …) TO 'out' (FORMAT parquet, PARTITION_BY (date))` écrit le résultat en Parquet, un dossier `date=…/` par valeur.
- Contexte : Conversion JSON Lines vers Parquet en une commande, avec l'arborescence Hive que lisent Athena et Spark. DuckDB nomme lui-même les fichiers (`data_0.parquet`). Relire avec `read_parquet('out/*/*.parquet')` redonne la colonne `date` par le chemin. Utile pour prototyper la zone `processed` avant le job Spark.
- Usage : ✅ extraire un échantillon en Parquet, prototyper une transformation · ❌ alimenter la zone `processed` en production : le job orchestré (S2).

```sql
-- Exemple 1 : un dossier par journée
COPY (SELECT * FROM read_json_auto(
  'bodacc/date=*/part-*.jsonl.gz'))
TO 'out' (FORMAT parquet,
          PARTITION_BY (date));
-- → out/date=2026-10-20/data_0.parquet
--   out/date=2026-10-21/data_0.parquet
```

- Quiz : Que donne `SELECT date, count(*) FROM read_parquet('out/*/*.parquet') GROUP BY 1` ?
- [ ] Erreur : colonne `date` introuvable
- [x] `2026-10-20` 3, `2026-10-21` 1
- [ ] Une seule ligne : `NULL` 4
- Réponse : les deux journées (mesuré) : la colonne revient par le chemin, grâce à la détection Hive.

## 18. filtre de partition : seuls les fichiers utiles
- Sous-thème : lire
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Un `WHERE` sur une colonne de partition élimine les fichiers avant lecture : seuls les dossiers qui correspondent sont ouverts.
- Contexte : `EXPLAIN` le montre : `File Filters: date = …` et `Scanning Files: 1/2`. Sur S3, c'est la différence entre lire une journée et relire tout l'historique à chaque requête. Le filtre doit porter sur la colonne de partition elle-même ; une colonne du contenu oblige à ouvrir tous les fichiers. Même mécanisme que le partition pruning d'Athena et de Spark.
- Usage : ✅ toujours filtrer par `date` quand la requête porte sur une période · ❌ filtrer sur un champ interne (`dateparution`) en espérant le même gain.

```sql
-- Exemple 1 : un fichier sur deux
EXPLAIN SELECT count(*)
FROM read_json_auto(
  'bodacc/date=*/part-*.jsonl.gz')
WHERE date = '2026-10-20';
-- → File Filters: date = '2026-10-20'::DATE
--   Scanning Files: 1/2
```

- Quiz : `WHERE date = DATE '2026-10-20' + 1` : le filtre de fichiers s'applique-t-il encore ?
- [x] Oui : l'expression est constante, calculée avant la lecture
- [ ] Non : seule une valeur littérale élague
- [ ] Non : le `+ 1` force la lecture de tout
- Réponse : oui (mesuré) : l'expression constante est calculée à la planification, `EXPLAIN` affiche `File Filters: date = '2026-10-21'` et `Scanning Files: 1/2`.

## 19. PARTITION_BY : la colonne sort des fichiers
- Sous-thème : sql
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Avec `PARTITION_BY (date)`, la colonne `date` n'est pas écrite dans les fichiers Parquet : elle n'existe que dans le nom du dossier.
- Contexte : Convention Hive : la valeur est la même pour tout le dossier, la répéter dans chaque ligne serait du stockage perdu. Conséquence : un fichier copié hors de son dossier perd sa date. Un lecteur sans détection Hive (outil, option `hive_partitioning = false`) ne voit plus la colonne. `parquet_schema()` montre ce que le fichier contient vraiment.
- Usage : ✅ garder l'arborescence intacte quand on déplace des partitions · ❌ copier `data_0.parquet` seul et compter sur sa colonne `date`.

```sql
-- Exemple 1 : le schéma réel du fichier
SELECT name FROM parquet_schema(
  'out/date=2026-10-20/*.parquet');
-- → duckdb_schema
--   id
--   familleavis
--   siren
--   tribunal       (pas de date)
```

- Quiz : On lit `out/date=2026-10-20/data_0.parquet` avec `hive_partitioning = false`. Combien de colonnes de données ?
- [ ] 5, dont `date`
- [x] 4, sans `date`
- [ ] 5, `date` à `NULL`
- Réponse : 4 : sans détection Hive, seule la colonne écrite dans le fichier compte, et `date` n'y est pas.

## 20. DuckDB ou Athena : choisir
- Sous-thème : choisir
- Niveau : 3
- Source : data-platform · S1-07
- Définition : DuckDB interroge le lake depuis un poste, gratuitement et sans infrastructure ; Athena l'interroge dans AWS, partagé, facturé au volume scanné.
- Contexte : DuckDB lit S3 par le réseau : parfait pour explorer quelques journées, un échantillon, un débogage ; limité par la machine et la bande passante pour des années d'historique. Athena tourne près des données, s'appuie sur le catalogue Glue partagé par l'équipe et les jobs, et s'automatise (Step Functions, QuickSight). Les deux lisent les mêmes partitions Hive : la convention du bucket sert aux deux.
- Usage : ✅ DuckDB pour explorer et prototyper, Athena pour les requêtes partagées, planifiées ou volumineuses · ❌ DuckDB sur un poste pour un rapport quotidien de production.

```sql
-- Exemple 1 : la même question, deux outils
-- DuckDB (poste, make duckdb)
SELECT count(*) FROM raw('bodacc')
WHERE date = '2026-10-20';
-- → 32373
-- Athena (S2, table Glue)
SELECT count(*) FROM raw.bodacc
WHERE date = DATE '2026-10-20';
```

- Quiz : Requête quotidienne, partagée par l'équipe, sur deux ans d'historique : quel outil ?
- [ ] DuckDB sur le poste de chacun
- [x] Athena, sur la table Glue
- [ ] DuckDB dans une Lambda de 128 Mo
- [ ] `aws s3 cp` puis `jq`
- Réponse : Athena : partagée, planifiable, exécutée près des données ; DuckDB reste l'outil d'exploration locale.
