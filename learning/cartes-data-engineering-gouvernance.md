---
title: "Cartes · Gouvernance des données"
type: cartes
langage: Data engineering
chapitre: Fiabiliser
cours: Gouvernance
created: 2026-10-26
updated: 2026-10-26
---

# Cartes · Gouvernance des données
Data engineering · Gouvernance : vocabulaire, propriété, référentiels, lignage, données personnelles (format spec v4 de revision-pwa).

## 1. vocabulaire contrôlé : un terme, une définition
- Id : gouvernance-vocabulaire-controle
- Sous-thème : vocabulaire
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : gouvernance-index-alias
- Mots-clés : vocabulaire contrôlé
- Source : revision-pwa · pwa-parcours
- Définition : Un vocabulaire contrôlé fixe la liste des termes admis : chaque notion a un terme officiel, une définition et ses écritures acceptées (alias).
- Contexte : Sans lui, « S3 », « s3 », « Amazon S3 » et « bucket S3 » deviennent quatre valeurs distinctes : filtres, comptages et jointures se trompent sans erreur. Le vocabulaire ramène chaque écriture au terme officiel. Même idée que les mots-clés d'une carte de révision, qui doivent tous exister dans un glossaire, ou qu'un `enum` TS au lieu d'une `string` libre.
- Usage : ✅ étiquettes, catégories, mots-clés, statuts partagés par plusieurs équipes ou fichiers · ❌ texte libre destiné à être lu (description, commentaire) : rien à contrôler.

```python
# Exemple 1 : vocabulaire libre
tags = ["S3", "s3", "Amazon S3",
        "bucket S3"]
len(set(tags))  # → 4
```

```python
# Exemple 2 : vocabulaire contrôlé
tags = ["S3", "s3", "Amazon S3",
        "bucket S3"]
ALIAS = {"s3": "S3", "amazon s3": "S3",
         "bucket s3": "S3"}
{ALIAS[t.casefold()] for t in tags}
# → {"S3"}
```

- Quiz : Le glossaire définit « idempotent » sans alias ; la recherche ignore casse et accents. « Idempotence » est-il trouvé ?
- [ ] Oui : la casse est ignorée
- [ ] Oui : le début du mot suffit
- [x] Non : il faut un alias
- [ ] Oui, si on normalise en NFD
- Réponse : non : c'est un autre mot, pas une autre écriture ; un vocabulaire contrôlé ne devine rien, on ajoute `idempotence` aux alias.

## 2. propriétaire unique : un seul endroit où écrire
- Id : gouvernance-proprietaire-unique
- Sous-thème : propriété
- Type : concept
- Niveau : 1
- Profils : débutant, data, ops
- Voir aussi : gouvernance-citer-pas-copier
- Mots-clés : propriétaire de donnée, source de vérité
- Source : revision-pwa · pwa-parcours
- Définition : Une donnée partagée a un seul propriétaire, qui seul l'écrit ; les autres la lisent ou la citent, sans la redéfinir.
- Contexte : Dans revision-pwa, chaque terme vit dans le glossaire du domaine auquel il appartient (OIDC dans AWS, idempotent dans Data engineering) ; une carte DevOps qui parle d'OIDC le cite. Un propriétaire désigné sait qui corrige une erreur et à qui demander un changement. Deux écrivains, c'est deux versions qui divergent et un arbitrage impossible.
- Usage : ✅ glossaire, référentiel de codes, table de dimension, schéma d'un dataset : un propriétaire nommé · ❌ « tout le monde peut l'éditer » sur une donnée lue par d'autres.

```python
# Exemple 1 : qui possède quoi
proprio = {"OIDC": "AWS",
           "idempotent": "Data engineering",
           "décorateur": "Python"}
proprio["OIDC"]  # → "AWS"
```

```python
# Exemple 2 : refuser l'écriture d'un tiers
proprio = {"OIDC": "AWS"}

def definir(terme, domaine):
    if proprio.get(terme, domaine) != domaine:
        raise PermissionError(terme)
    proprio[terme] = domaine

definir("OIDC", "AWS")     # accepté
definir("OIDC", "DevOps")  # ❌ PermissionError
```

- Quiz : Une carte DevOps a besoin d'OIDC, déjà défini dans le glossaire AWS : que fait-on ?
- [ ] On le redéfinit dans le glossaire DevOps
- [x] On cite « OIDC » dans ses Mots-clés
- [ ] On ajoute l'alias « OIDC (DevOps) »
- [ ] On copie la définition dans la carte
- Réponse : on le cite : le terme reste défini une fois, chez son propriétaire ; une seconde définition serait refusée comme doublon.

## 3. citer plutôt que copier
- Id : gouvernance-citer-pas-copier
- Sous-thème : propriété
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Prérequis : gouvernance-proprietaire-unique
- Mots-clés : source de vérité
- Source : revision-pwa · pwa-parcours
- Définition : Copier une donnée de référence crée une seconde vérité qui rate les corrections ; la citer par sa clé la lit toujours à jour.
- Contexte : La copie est tentante (pas de dépendance, lecture plus simple), mais chaque correction chez le propriétaire doit alors être reportée partout, et rien ne signale l'oubli. Une carte qui liste des mots-clés et laisse l'app chercher la définition au moment de l'affichage ne peut pas être en retard. Même logique qu'un `import` plutôt qu'un copier-coller de code.
- Usage : ✅ stocker la clé (terme, code, id) et résoudre à la lecture · ❌ dupliquer libellés ou définitions dans chaque fichier qui s'en sert ; si une copie est inévitable (cache), lui donner une date et une source.

```python
# Exemple 1 : la copie reste en arrière
aws = {"OIDC": "identité par jeton"}
devops = dict(aws)          # copie
aws["OIDC"] += " signé (JWT)"
devops["OIDC"] == aws["OIDC"]  # → False
```

```python
# Exemple 2 : la citation suit
aws = {"OIDC": "identité par jeton"}
carte = {"mots_cles": ["OIDC"]}
aws["OIDC"] += " signé (JWT)"
[aws[m] for m in carte["mots_cles"]]
# → ["identité par jeton signé (JWT)"]
```

- Quiz : Trois équipes gardent chacune une copie de la liste des tribunaux ; un tribunal ferme. Qu'est-ce qui garantit la cohérence ?
- [ ] La source : une mise à jour suffit
- [ ] Une erreur à la prochaine jointure
- [x] Rien : trois mises à jour à ne pas oublier
- [ ] La synchronisation automatique des copies
- Réponse : rien : chaque copie est une vérité de plus, l'oubli passe en silence ; lire la liste chez son propriétaire supprime le problème.

## 4. index d'alias : retrouver le terme
- Id : gouvernance-index-alias
- Sous-thème : vocabulaire
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : gouvernance-vocabulaire-controle
- Voir aussi : Python/unicode-cle-de-recherche
- Mots-clés : clé de recherche, temps constant
- Source : revision-pwa · pwa-parcours
- Définition : Un index associe la clé normalisée de chaque écriture (terme et alias) à l'entrée du vocabulaire : une recherche, quelle que soit l'écriture.
- Contexte : C'est `indexGlossaire` dans l'app : pour chaque terme, `[terme, ...alias]` passe par `termKey` (sans casse, sans accents, espaces réduits) et pointe vers l'entrée complète. La recherche applique la même clé au mot cherché. Construit une fois au chargement, l'index répond en temps constant.
- Usage : ✅ résoudre les mots-clés d'une carte, les libellés d'une source vers un référentiel · ❌ comparer à chaque recherche toutes les définitions une par une (lent, et chaque appelant normalise à sa façon).

```python
# Exemple 1 : l'index, comme indexGlossaire
import unicodedata as u

def cle(s):
    d = u.normalize("NFD", s.casefold())
    s = "".join(c for c in d
                if not u.combining(c))
    return " ".join(s.split())

termes = [
    {"terme": "rôle IAM", "alias": ["rôles IAM"]},
    {"terme": "OIDC", "alias": ["OpenID Connect"]}]
index = {cle(a): t for t in termes
         for a in [t["terme"], *t["alias"]]}
index[cle("Role  IAM")]["terme"]  # → "rôle IAM"
index[cle("openid connect")]["terme"]
# → "OIDC"
```

- Quiz : Deux entrées déclarent le même alias. Que fait la compréhension qui construit l'index ?
- [ ] `KeyError`
- [ ] Elle garde la première entrée
- [x] La dernière écrase la première, sans erreur
- [ ] Elle associe une liste des deux
- Réponse : la dernière écrase : un `dict` réaffecte la clé sans prévenir ; d'où le contrôle d'unicité avant de construire l'index.

## 5. unicité : vérifier sur la clé normalisée
- Id : gouvernance-unicite-cle-normalisee
- Sous-thème : vocabulaire
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : gouvernance-index-alias
- Mots-clés : clé de recherche, CI
- Source : revision-pwa · pwa-parcours
- Définition : Un terme n'est défini qu'une fois : le contrôle compare les clés normalisées de tous les termes et alias, dans tous les fichiers, avant publication.
- Contexte : Comparer les textes bruts laisse passer « Rôle IAM » et « role IAM » : deux définitions, et la recherche (qui, elle, normalise) tombe sur l'une ou l'autre selon l'ordre de chargement. Le contrôle doit utiliser exactement la clé de la recherche. Dans revision-pwa, `parseGlossaireFile` le fait dans un fichier et `buildGlossaire` entre fichiers.
- Usage : ✅ un `Counter` des clés en CI, avant toute publication · ❌ vérifier seulement l'intérieur d'un fichier : les doublons naissent entre deux producteurs.

```python
# Exemple 1 : doublons entre deux glossaires
from collections import Counter
import unicodedata as u

def cle(s):
    d = u.normalize("NFD", s.casefold())
    return "".join(c for c in d
                   if not u.combining(c))

aws = ["Rôle IAM", "OIDC"]
devops = ["role IAM", "CI"]
n = Counter(cle(t) for t in aws + devops)
[k for k, v in n.items() if v > 1]
# → ["role iam"]
```

- Quiz : Le contrôle d'unicité compare les termes tels qu'écrits. « Rôle IAM » (AWS) et « role IAM » (DevOps) : que se passe-t-il ?
- [ ] Le contrôle les signale
- [x] Ils passent ; la recherche en trouve un seul
- [ ] La recherche renvoie les deux
- [ ] La publication échoue plus tard
- Réponse : ils passent : textes différents ; mais la recherche normalise, les deux ont la même clé et l'index n'en garde qu'un.

## 6. homonymes : qualifier le terme
- Id : gouvernance-homonymes-qualifier
- Sous-thème : vocabulaire
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : gouvernance-vocabulaire-controle
- Mots-clés : partition, clé de partition DynamoDB, vocabulaire contrôlé
- Source : revision-pwa · pwa-parcours
- Définition : Un mot qui a deux sens (partition d'un lake, partition DynamoDB) devient deux termes qualifiés, jamais un seul terme à deux définitions.
- Contexte : Le vocabulaire contrôlé garantit un sens par terme ; un homonyme casse cette règle. On garde le terme nu pour le sens le plus courant chez son propriétaire (« partition » en Data engineering) et on qualifie l'autre (« clé de partition DynamoDB » en AWS). Les cartes citent la forme qualifiée quand le contexte l'exige.
- Usage : ✅ « partition » / « clé de partition DynamoDB », « run » / « run Glue » · ❌ un seul terme dont la définition dit « selon le contexte » : la fiche n'aide personne.

```python
# Exemple 1 : deux sens, deux termes
glossaire = {
    "partition": "Data engineering",
    "clé de partition DynamoDB": "AWS"}
sorted(glossaire)
# → ["clé de partition DynamoDB",
#    "partition"]
```

- Quiz : Les glossaires AWS et Data engineering définissent tous deux `## partition`. Que fait le contrôle d'unicité ?
- [ ] Il accepte : domaines différents
- [ ] Il fusionne les deux définitions
- [x] Il refuse : même clé dans le catalogue
- [ ] Il garde la plus courte
- Réponse : il refuse : un terme est unique dans tout le catalogue, domaines confondus ; l'un des deux doit être qualifié.

## 7. glossaire, dictionnaire, catalogue
- Id : gouvernance-glossaire-dictionnaire-catalogue
- Sous-thème : référentiels
- Type : comparaison
- Niveau : 2
- Profils : data
- Prérequis : gouvernance-vocabulaire-controle
- Voir aussi : AWS/glue-athena-table-metadonnees
- Mots-clés : dictionnaire de données, catalogue de données, BODACC
- Source : revision-pwa · pwa-parcours
- Définition : Le glossaire définit les mots du métier ; le dictionnaire de données décrit les colonnes d'un dataset ; le catalogue recense les datasets.
- Contexte : Trois niveaux : le sens (« date de parution » = jour où le BODACC paraît), la colonne (`dateparution`, `DATE`, non nulle), la table (où elle est, son propriétaire, sa fraîcheur). Le catalogue Glue est un catalogue technique ; des outils comme DataHub y relient glossaire et dictionnaire. Les mélanger donne un document que personne ne tient à jour.
- Usage : ✅ glossaire pour le jargon, dictionnaire à côté du schéma (versionné avec lui), catalogue pour trouver les tables · ❌ définir les mots métier dans les commentaires de colonnes : chaque table les redéfinit.

```text
# Exemple 1 : « date de parution »
Glossaire   : jour où paraît le
              bulletin BODACC
Dictionnaire: annonces.dateparution,
              DATE, non nulle
Catalogue   : table annonces, zone
              processed, maj chaque jour
```

- Quiz : Où documenter que la colonne `dateparution` est de type `DATE` et jamais nulle ?
- [ ] Dans le glossaire
- [x] Dans le dictionnaire de données
- [ ] Dans le catalogue de données
- [ ] Dans le README du dépôt
- Réponse : le dictionnaire de données : il décrit les colonnes (type, contraintes, unité) ; le glossaire définit le mot, le catalogue situe la table.

## 8. données de référence : valider contre le référentiel
- Id : gouvernance-donnees-de-reference
- Sous-thème : référentiels
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : gouvernance-proprietaire-unique
- Voir aussi : qualite-quarantaine-lignes-invalides
- Mots-clés : données de référence, quarantaine, propriétaire de donnée
- Source : revision-pwa · pwa-parcours
- Définition : Une colonne codée (tribunal, pays) se valide contre une table de référence tenue par son propriétaire ; un code inconnu ne passe jamais en silence.
- Contexte : Les données de référence changent peu mais changent : un tribunal ferme, un code est créé. La table est versionnée, a un propriétaire, et le pipeline la lit (sans la copier). Une valeur absente est mise en quarantaine et signalée au propriétaire du référentiel, qui décide : faute de saisie ou nouveau code à ajouter.
- Usage : ✅ contrôle d'appartenance à l'ingestion, quarantaine des lignes inconnues, alerte · ❌ ajouter automatiquement au référentiel tout code inconnu : le référentiel n'est plus contrôlé.

```python
# Exemple 1 : codes inconnus (codes fictifs)
TRIBUNAUX = {"7501": "Paris",
             "9401": "Créteil"}
lignes = [{"tribunal": "7501"},
          {"tribunal": "9999"}]
[l for l in lignes
 if l["tribunal"] not in TRIBUNAUX]
# → [{"tribunal": "9999"}]
```

- Quiz : Un nouveau tribunal apparaît dans la source avant d'entrer au référentiel : que deviennent ses lignes ?
- [ ] Supprimées : code invalide
- [ ] Acceptées ; le code est ajouté au référentiel
- [x] Quarantaine, et alerte au propriétaire
- [ ] Acceptées sans signal
- Réponse : quarantaine et alerte : le propriétaire ajoute le code, puis on rejoue les lignes ; rien n'est perdu, rien n'entre sans contrôle.

## 9. référence inconnue : avertir ou refuser
- Id : gouvernance-avertir-ou-refuser
- Sous-thème : vocabulaire
- Type : choisir
- Niveau : 2
- Profils : data, ops
- Prérequis : gouvernance-vocabulaire-controle
- Mots-clés : CI, lecteur tolérant, Lambda
- Source : revision-pwa · pwa-parcours
- Définition : Un mot-clé hors vocabulaire est une erreur avant publication (on peut corriger), un avertissement à la lecture (on ne bloque pas les lecteurs).
- Contexte : revision-pwa applique les deux : `make cards` refuse un mot-clé sans définition, la Lambda du catalogue le publie quand même et journalise un avertissement. Refuser côté Lambda retirerait des cartes justes pour un glossaire en retard ; tolérer côté CI laisserait les trous s'accumuler. Même règle qu'un lecteur tolérant face à un producteur strict.
- Usage : ✅ strict en CI et dans l'outil de l'auteur, tolérant et journalisé au runtime · ❌ la même sévérité partout : soit rien ne passe, soit tout passe.

```python
# Exemple 1 : un contrôle, deux sévérités
def verifier(mots, glossaire, strict):
    inconnus = [m for m in mots
                if m not in glossaire]
    if inconnus and strict:
        raise ValueError(inconnus)
    return inconnus

g = {"OIDC"}
verifier(["OIDC", "STS"], g, False)
# → ["STS"]
verifier(["OIDC", "STS"], g, True)  # ❌ ValueError
```

- Quiz : Si la Lambda refusait tout fichier de cartes contenant un mot-clé inconnu, que donnerait un seul oubli ?
- [ ] Rien : la carte s'affiche sans pastille
- [x] Toutes les cartes du fichier disparaissent
- [ ] La publication échoue chez le producteur
- [ ] La Lambda réessaie jusqu'à la correction
- Réponse : tout le fichier disparaît : un fichier en erreur est écarté en entier ; d'où l'avertissement au runtime et l'erreur en amont, dans `make cards`.

## 10. lignage : d'où vient la ligne
- Id : data-lake-lignage
- Sous-thème : lignage
- Type : recette
- Niveau : 2
- Profils : data, ops
- Voir aussi : duckdb-filename-origine-ligne
- Mots-clés : zone raw, zone processed, run, log structuré
- Définition : Le lignage relie chaque donnée à sa source : une ligne de `processed` porte le fichier `raw` lu, l'heure d'ingestion et l'id du run.
- Contexte : Une valeur fausse dans un export : sans lignage, on ne sait ni quel fichier brut la contient ni quel run l'a produite. Avec trois colonnes techniques (`_source`, `_ingere_le`, `_run_id`), on remonte en une requête au fichier `raw` et aux logs du run (le même `run_id` dans les logs JSON). Le `run_id` permet aussi de retirer tout ce qu'un run défectueux a écrit. À l'échelle, OpenLineage trace les dépendances entre tables.
- Usage : ✅ colonnes techniques sur chaque ligne de `processed`, `run_id` partagé avec les logs · ❌ heure d'ingestion recalculée à la lecture : elle date la requête, pas l'écriture.

```python
# Exemple 1 : les colonnes techniques
from datetime import datetime, timezone

def enrichir(a, cle, run_id, now):
    return a | {"_source": cle,
                "_run_id": run_id,
                "_ingere_le": now.isoformat()}

now = datetime(2026, 10, 24, 7,
               tzinfo=timezone.utc)
l = enrichir({"siren": "483609327"},
             "raw/bodacc/dt=2026-10-23/p0",
             "r42", now)
l["_ingere_le"]
# → "2026-10-24T07:00:00+00:00"
```

```python
# Exemple 2 : retrouver ce qu'un run a écrit
lignes = [{"siren": "1", "_run_id": "r1"},
          {"siren": "2", "_run_id": "r2"},
          {"siren": "3", "_run_id": "r2"}]
[l["siren"] for l in lignes
 if l["_run_id"] == "r2"]  # → ["2", "3"]
```

- Quiz : `run_id = str(uuid.uuid4())` est calculé dans `enrichir`, à chaque ligne : combien de `run_id` distincts pour un run de 3 annonces ?
- [ ] 1
- [x] 3
- [ ] 0
- Réponse : 3 : un uuid par appel ; le `run_id` se génère une fois au début du run et se passe à chaque ligne et à chaque log.

## 11. pseudonymiser : HMAC plutôt que SHA-256
- Id : data-lake-pseudonymiser-hmac
- Sous-thème : données personnelles
- Type : recette
- Niveau : 2
- Profils : data, ops
- Voir aussi : Python/hachage-sha256-empreinte, IA/extraction-masquer-donnees-personnelles
- Mots-clés : HMAC, SHA-256, RGPD, Secrets Manager
- Définition : Pour joindre des données personnelles sans les exposer, on remplace l'identifiant par un HMAC à clé secrète, pas par un simple hash.
- Contexte : Les annonces BODACC citent des personnes physiques (5 983 le 20 octobre). Le SHA-256 d'un nom se renverse par force brute : on hache tous les candidats et on compare. Le HMAC mélange une clé gardée hors du lake (Secrets Manager) : même entrée, même jeton, donc les jointures marchent, mais impossible à recalculer sans la clé. Au sens du RGPD, c'est une pseudonymisation : les données restent personnelles, la clé est la protection.
- Usage : ✅ colonnes de personnes physiques dans `processed` et `out`, une clé par environnement · ❌ SHA-256 sans clé d'un nom ou d'un numéro court ; clé stockée dans le même bucket que les données.

```python
# Exemple 1 : un hash se renverse
import hashlib

def h(s):
    return hashlib.sha256(s.encode()).hexdigest()

fuite = h("MARTIN Paul")
candidats = ["DUPONT Léa", "MARTIN Paul"]
[c for c in candidats if h(c) == fuite]
# → ["MARTIN Paul"]
```

```python
# Exemple 2 : HMAC, stable mais secret
import hashlib, hmac

cle = b"lue-dans-secrets-manager"
def jeton(s):
    return hmac.new(cle, s.encode(),
                    hashlib.sha256).hexdigest()

jeton("MARTIN Paul") == jeton("MARTIN Paul")
# → True
sha = hashlib.sha256(b"MARTIN Paul")
jeton("MARTIN Paul") == sha.hexdigest()
# → False
```

- Quiz : Même clé HMAC des deux côtés, mais `"Martin Paul"` dans une source et `"MARTIN Paul"` dans l'autre : la jointure marche-t-elle ?
- [ ] Oui : même clé, même jeton
- [x] Non : deux jetons différents
- [ ] Oui, HMAC ignore la casse
- Réponse : non : un octet différent donne un jeton sans rapport ; normaliser (casse, espaces, accents) avant de pseudonymiser.

## 12. conflit de propriété : une règle déterministe
- Id : gouvernance-conflit-regle-deterministe
- Sous-thème : propriété
- Type : concept
- Niveau : 3
- Profils : data, expert
- Prérequis : gouvernance-proprietaire-unique, gouvernance-unicite-cle-normalisee
- Mots-clés : déterministe
- Source : revision-pwa · pwa-parcours
- Définition : Quand deux sources revendiquent la même donnée, une règle fixe (ordre des sources) désigne le gagnant et l'autre est rejetée et journalisée.
- Contexte : « Le dernier publié gagne » dépend de l'ordre d'arrivée : deux reconstructions du catalogue donneraient deux résultats. `buildGlossaire` trie les fichiers par nom, garde le premier qui définit un terme et écarte en entier le fichier qui le redéfinit, avec une erreur qui nomme le propriétaire. Le résultat ne dépend que des entrées : on peut tout reconstruire à l'identique.
- Usage : ✅ tri explicite des sources, rejet journalisé, reconstruction complète à chaque changement · ❌ fusionner silencieusement, ou laisser l'ordre de traitement des événements décider.

```python
# Exemple 1 : premier dans l'ordre trié
fichiers = {
    "p2/glossaire-aws.md": ["OIDC", "STS"],
    "p1/glossaire-aws.md": ["OIDC", "ARN"]}
vus, gardes = {}, []
for f in sorted(fichiers):
    if any(t in vus for t in fichiers[f]):
        continue                # écarté en entier
    vus |= {t: f for t in fichiers[f]}
    gardes.append(f)
gardes  # → ["p1/glossaire-aws.md"]
```

- Quiz : Le second producteur ne redéfinit qu'un terme sur cinquante. Que perd le catalogue (règle de revision-pwa) ?
- [ ] Ce seul terme
- [ ] Rien : sa définition remplace l'ancienne
- [x] Les cinquante termes de son fichier
- [ ] Le terme chez les deux producteurs
- Réponse : les cinquante : le fichier qui redéfinit un terme est écarté en entier, avec une erreur ; l'auteur cite le terme existant et republie.

## 13. golden record : une entité, plusieurs sources
- Id : gouvernance-golden-record
- Sous-thème : référentiels
- Type : concept
- Niveau : 3
- Profils : data, expert
- Prérequis : gouvernance-donnees-de-reference
- Mots-clés : golden record, SIREN, INSEE
- Source : revision-pwa · pwa-parcours
- Définition : Le golden record est la fiche maître d'une entité (une entreprise par SIREN), construite champ par champ depuis plusieurs sources selon des règles de priorité.
- Contexte : BODACC et INSEE décrivent la même entreprise, chacun avec ses forces : l'INSEE fait foi pour la dénomination, le BODACC pour les procédures. Les règles de survie disent, par champ, quelle source l'emporte et quand passer à la suivante (valeur vide). C'est le cœur du MDM (gestion des données de référence) : les applications lisent la fiche maître, pas les sources.
- Usage : ✅ entités partagées vues par plusieurs sources (entreprises, clients, produits) · ❌ « la source la plus récente gagne » pour tous les champs : une valeur vide ou moins fiable écrase une bonne.

```python
# Exemple 1 : priorité par champ
src = {
    "insee": {"nom": "ACME SAS",
              "statut": None},
    "bodacc": {"nom": "ACME",
               "statut": "liquidation"}}
prio = {"nom": ["insee", "bodacc"],
        "statut": ["bodacc", "insee"]}
def maitre(champ):
    for s in prio[champ]:
        if src[s][champ] is not None:
            return src[s][champ]
{c: maitre(c) for c in prio}
# → {"nom": "ACME SAS", "statut": "liquidation"}
```

- Quiz : Règle unique « la source mise à jour en dernier gagne », et le BODACC vient d'arriver avec `nom = "ACME"` : quel nom garde la fiche ?
- [ ] `"ACME SAS"`, l'INSEE fait foi
- [x] `"ACME"`, même si l'INSEE fait foi
- [ ] Les deux, en liste
- [ ] Aucun : conflit à arbitrer
- Réponse : `"ACME"` : une règle globale par date ignore la fiabilité de chaque source ; les règles de survie se fixent par champ.
