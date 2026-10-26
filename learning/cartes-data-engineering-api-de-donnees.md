---
title: "Cartes · API de données"
type: cartes
langage: Data engineering
chapitre: Ingérer
cours: API de données
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · API de données
Data engineering · API de données : requêtes, pagination, erreurs, cache, contrat (format spec v3 de revision-pwa).

## 1. total_count : mesurer avant d'ingérer
- Id : api-de-donnees-total-count-mesurer
- Sous-thème : requêtes
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Voir aussi : ingestion-mesurer-vraie-source
- Mots-clés : OpenDataSoft, streaming, HyperLogLog
- Source : data-platform · S1-05
- Définition : Avant d'écrire l'ingestion, on mesure la source : lignes par jour (`total_count`), répartition (`group_by`), poids moyen d'une ligne.
- Contexte : `limit=0` renvoie le total exact sans aucune donnée : une requête, quelques octets. Un `group_by` donne la répartition par famille. Ces chiffres décident de tout : 32 373 lignes par jour excluent l'offset (plafond 10 000), 59 Mo imposent le streaming, un tiers utile justifie un filtre. Mesurer sur une journée complète, jamais sur une fixture de 25 lignes.
- Usage : ✅ avant de choisir pagination, mémoire Lambda ou partitions ; contrôle de complétude (lus = `total_count`) · ❌ dimensionner d'après la doc ou un échantillon : les cas rares n'y sont pas.

```bash
# Exemple 1 : le total, sans les données
curl -s -G --compressed "$BODACC/records" \
  --data-urlencode \
  "where=dateparution=date'2026-10-20'" \
  --data-urlencode "limit=0"
# → {"total_count": 32373, "results": []}
```

```bash
# Exemple 2 : la répartition par famille
curl -s -G --compressed "$BODACC/records" \
  --data-urlencode \
  "where=dateparution=date'2026-10-20'" \
  --data-urlencode \
  "select=familleavis, count(*) as n" \
  --data-urlencode "group_by=familleavis"
# → {"total_count": 8, "results": [
#   {"familleavis": "collective",
#    "n": 937}, …, dpc 15310, …]}
```

```python
# Exemple 3 : du volume aux choix
import math

lignes, octets = 32_373, 59_432_342
octets // lignes  # → 1835  (o / annonce)
math.ceil(lignes / 100)
# → 324  (pages de 100)
lignes > 10_000  # → True  (offset exclu)
```

- Quiz : Sur cette journée, `count(distinct id)` renvoie 34 299 pour 32 373 lignes. Pourquoi ?
- [ ] Des ids en double dans la source
- [x] Un comptage approché
- [ ] Les annulations comptées deux fois
- [ ] Un cache périmé de 60 s
- Réponse : un comptage approché (HyperLogLog) : `count(distinct)` d'OpenDataSoft est une estimation ; pour la complétude, comparer à `total_count`, exact.

## 2. where : filtrer côté serveur
- Id : api-de-donnees-filtrer-cote-serveur
- Sous-thème : requêtes
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Mots-clés : ODSQL, dataset, lakehouse, BODACC
- Source : data-platform · S1-05
- Définition : Filtrer dans la requête (`where`, `select`) fait trier la source avant l'envoi : on ne télécharge que les lignes et colonnes utiles.
- Contexte : Sur BODACC, une journée compte 32 373 annonces dont 15 310 dépôts de comptes (`dpc`, 47 %) inutiles au projet. `familleavis in (…)` dans `where` divise le téléchargement par 3, `select` retire les colonnes. Le langage de filtre d'une API (ODSQL ici) est typé et limité : un seul dataset, pas de jointure, champs imbriqués vus comme du texte. Le reste se fait ensuite, dans le lakehouse.
- Usage : ✅ réduire volume, durée et quota : jour, famille, colonnes · ❌ logique métier complexe ou filtre sur un champ imbriqué : filtrer après le parsing, côté pipeline.

```bash
# Exemple 1 : seulement les familles utiles
W="dateparution=date'2026-10-20'"
W="$W and familleavis in"
W="$W ('creation','collective','radiation')"
curl -s -G --compressed "$BODACC/records" \
  --data-urlencode "where=$W" \
  --data-urlencode "limit=0"
# → {"total_count": 10854, "results": []}
```

```python
# Exemple 2 : ce que le filtre économise
jour = {"dpc": 15310, "creation": 6813,
        "modification": 5363,
        "radiation": 3104,
        "collective": 937,
        "immatriculation": 475,
        "vente": 370, "conciliation": 1}
utiles = ("creation", "collective",
          "radiation")
gardees = sum(jour[f] for f in utiles)
total = sum(jour.values())
gardees, total   # → (10854, 32373)
round(total / gardees, 1)  # → 3.0
```

- Quiz : Que renvoie `where=dateparution='2026-10-20'` (une chaîne, sans le mot `date`) ?
- [ ] Les 32 373 annonces du jour
- [ ] 0 annonce, sans erreur
- [x] Un HTTP 400
- [ ] Toutes les annonces, filtre ignoré
- Réponse : un HTTP 400 `IncompatibleTypesInComparisonFilter` : le champ est typé `date`, il se compare au littéral `date'2026-10-20'`, jamais à une chaîne.

## 3. métadonnées : le schéma avant les données
- Id : api-de-donnees-metadonnees-schema
- Sous-thème : requêtes
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Voir aussi : ingestion-evolution-de-schema
- Mots-clés : OpenDataSoft, dataset, ODSQL
- Définition : L'endpoint de métadonnées d'un dataset décrit ses champs, leurs types et sa date de mise à jour, sans renvoyer une seule ligne.
- Contexte : Sur OpenDataSoft, `GET <base>` (sans `/records`) renvoie `fields` (nom, type) et `metas.default` (`records_count`, `data_processed`). C'est la première lecture d'une source : les types disent comment filtrer (`date'…'` pour un champ `date`), la mise à jour dit quand planifier. Le type déclaré ne dit pas tout : sur BODACC, 11 champs `text` contiennent du JSON sérialisé.
- Usage : ✅ découvrir une source, détecter un changement de schéma à chaque run, planifier d'après `data_processed` · ❌ deviner les types depuis trois lignes d'exemple.

```python
# Exemple 1 : lire les types déclarés
import json

meta = json.loads('''{"fields": [
 {"name": "id", "type": "text"},
 {"name": "dateparution", "type": "date"},
 {"name": "numeroannonce", "type": "int"}]}''')
types = {f["name"]: f["type"]
         for f in meta["fields"]}
types["dateparution"]  # → "date"
```

```bash
# Exemple 2 : la date de mise à jour
curl -s --compressed "$BODACC" \
  | jq -r '.metas.default.data_processed'
# → 2026-10-23T06:16:32.439000+00:00
```

- Quiz : Parmi les champs de l'exemple 1, lesquels acceptent `>` dans un `where` ODSQL ?
- [ ] `id` seulement
- [x] `dateparution` et `numeroannonce`
- [ ] Les trois
- [ ] Aucun : ODSQL n'a que `=`
- Réponse : `dateparution` et `numeroannonce` : `>` et `<` ne s'appliquent qu'aux types `date` et `int` ; sur un `text` comme `id`, HTTP 400.

## 4. codes HTTP : retenter ou lever
- Id : api-de-donnees-codes-http-retenter-ou-lever
- Sous-thème : erreurs
- Type : concept
- Niveau : 1
- Profils : débutant, data, web
- Voir aussi : ingestion-retry-backoff-exponentiel, api-de-donnees-retry-after-deux-formes
- Mots-clés : retry, quota
- Définition : Seuls les échecs transitoires se retentent (429, 502, 503, 504, coupure réseau) ; les autres 4xx signalent une requête fausse, à corriger.
- Contexte : Un 400, 401, 403 ou 404 renverra la même réponse : réessayer brûle du quota et retarde l'alerte. 429 et 503 disent « plus tard », 502 et 504 viennent d'une passerelle. Le 500 est ambigu (bug durable ou incident passager) : le client BODACC ne le retente pas (`RETRYABLE_STATUS = {429, 502, 503, 504}`). Un timeout ou une connexion refusée se retente aussi.
- Usage : ✅ une liste explicite des statuts à retenter, dans une constante testée · ❌ `if statut >= 400: retry` : un 404 boucle jusqu'à épuiser les essais.

```python
# Exemple 1 : la décision par statut
RETRY = frozenset({429, 502, 503, 504})

def decision(statut):
    if statut < 400:
        return "ok"
    if statut in RETRY:
        return "retenter"
    return "lever"

[decision(s) for s in (200, 404, 503)]
# → ["ok", "lever", "retenter"]
```

```python
# Exemple 2 : httpx ne lève pas seul
import httpx

req = httpx.Request("GET", "https://x")
r = httpx.Response(404, request=req)
r.is_success  # → False
r.raise_for_status()  # ❌ HTTPStatusError
```

- Quiz : Avec `decision` de l'exemple 1, que donne `decision(304)` ?
- [ ] `"lever"`
- [x] `"ok"`
- [ ] `"retenter"`
- Réponse : `"ok"` : 304 Not Modified n'est pas une erreur (< 400), mais son corps est vide ; il se traite à part (requête conditionnelle), jamais comme des données.

## 5. GET : sûr à retenter, POST non
- Id : api-de-donnees-get-vs-post-retry
- Sous-thème : erreurs
- Type : comparaison
- Niveau : 1
- Profils : débutant, data, web
- Voir aussi : ingestion-idempotence-ecraser
- Mots-clés : retry, UUID
- Définition : Une méthode idempotente (GET, PUT, DELETE) se rejoue sans changer le résultat ; un POST rejoué peut créer deux fois la même chose.
- Contexte : Une API de données se lit en GET : après un timeout, on ignore si le serveur a répondu, mais réessayer ne crée rien. Un POST (création, envoi) dont la réponse se perd a peut-être réussi : le rejouer duplique. Les API sérieuses acceptent une clé d'idempotence (`Idempotency-Key`, chez Stripe) : même clé, même effet. urllib3, sous `requests`, ne retente par défaut que les méthodes idempotentes.
- Usage : ✅ retries automatiques sur GET ; POST avec une `Idempotency-Key` générée une fois par opération · ❌ retenter un POST sans clé : commandes, messages ou lignes en double.

```python
# Exemple 1 : un POST rejoué après timeout
serveur = []

def post(annonce):
    serveur.append(annonce)  # créé...
    raise TimeoutError       # réponse perdue

for _ in range(2):           # retry naïf
    try:
        post("A1")
    except TimeoutError:
        pass
len(serveur)  # → 2
```

```python
# Exemple 2 : la clé d'idempotence
serveur = {}

def post(cle, annonce):
    serveur.setdefault(cle, annonce)
    raise TimeoutError

for _ in range(2):
    try:
        post("cle-7f3a", "A1")
    except TimeoutError:
        pass
len(serveur)  # → 1
```

- Quiz : Exemple 2 : la clé vaut `str(uuid.uuid4())`, générée dans la boucle à chaque essai. Que vaut `len(serveur)` ?
- [ ] 1
- [x] 2
- [ ] 0
- Réponse : 2 : chaque essai porte une clé neuve, le serveur y voit deux opérations ; la clé se génère une fois, avant la boucle de retries.

## 6. offset : la fenêtre plafonnée
- Id : api-de-donnees-offset-fenetre-plafonnee
- Sous-thème : pagination
- Type : piège
- Niveau : 2
- Profils : data
- Voir aussi : api-de-donnees-keyset-derniere-cle, api-de-donnees-export-en-flux
- Mots-clés : OpenDataSoft, keyset, streaming
- Source : data-platform · S1-05
- Définition : L'offset (« saute N, donne 100 ») est plafonné par l'API : `offset + limit ≤ 10 000` et `limit ≤ 100`, sinon HTTP 400.
- Contexte : Pour servir `offset=9000`, le serveur trie puis saute 9 000 lignes à chaque appel : le coût croît avec la page, d'où le plafond (10 000 chez OpenDataSoft comme chez Elasticsearch). Mesuré sur BODACC : `offset=9999&limit=1` → 200, `offset=10000` → 400. Une journée de 32 373 lignes ne se lit donc qu'au premier tiers. L'offset glisse aussi quand des lignes arrivent pendant la lecture.
- Usage : ✅ afficher une page à un humain, jeu de moins de 10 000 lignes · ❌ ingérer un volume complet : export en flux, ou keyset.

```python
# Exemple 1 : ce qu'on peut atteindre
FENETRE = 10_000

def accessibles(total):
    return min(total, FENETRE)

accessibles(32_373)  # → 10000
32_373 - accessibles(32_373)
# → 22373  (jamais lues)
```

```python
# Exemple 2 : la règle du serveur
def statut(offset, limit):
    if limit > 100:
        return 400
    if offset + limit > 10_000:
        return 400
    return 200

statut(9_999, 1)    # → 200
statut(10_000, 1)   # → 400
statut(0, 101)      # → 400
```

- Quiz : Que répond l'API à `offset=9950&limit=100` ?
- [ ] 200 avec 100 lignes
- [ ] 200 avec les 50 dernières lignes
- [x] 400
- [ ] 200 avec une page vide
- Réponse : 400 : 9 950 + 100 dépasse 10 000, l'API refuse au lieu de tronquer ; la dernière page complète part de `offset=9900`.

## 7. keyset : reprendre après la dernière clé
- Id : api-de-donnees-keyset-derniere-cle
- Sous-thème : pagination
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : api-de-donnees-offset-fenetre-plafonnee
- Voir aussi : api-de-donnees-curseur-jeton-opaque
- Mots-clés : ODSQL, BODACC
- Source : data-platform · S1-05
- Définition : La pagination keyset demande les N lignes après la dernière clé reçue (`where cle > dernière`, `order_by cle`) : coût constant, sans plafond (≈ `?after=<cursor>`).
- Contexte : Il faut une clé unique, triée et que l'API sait comparer. Sur BODACC, `id` est un `text` : ODSQL refuse `>` dessus (400), et un texte de longueur variable ne suit pas l'ordre numérique. `numeroannonce` entier convient, mais il repart à 1 dans chaque bulletin : un curseur par bulletin A, B, C, soit 325 appels par journée. Chaque page est une requête indépendante, réessayable sans doublon. Arrêt sur une page incomplète.
- Usage : ✅ volume au-delà de la fenêtre d'offset, reprise après coupure depuis la dernière clé · ❌ clé non unique ou texte de longueur variable : pages qui sautent ou répètent des lignes ; petit volume : offset ou export.

```python
# Exemple 1 : après la dernière clé
TABLE = list(range(1, 251))  # numéros
def page(apres, limit=100):  # WHERE n > ?
    return [n for n in TABLE
            if n > apres][:limit]
def tout(limit=100):
    dernier = 0
    while True:
        p = page(dernier, limit)
        yield from p
        if len(p) < limit:   # incomplète
            break
        dernier = p[-1]      # curseur
len(list(tout()))  # → 250
```

```python
# Exemple 2 : un curseur par bulletin
TABLE = {"A": [1, 2, 3], "B": [1, 2]}

def page(b, apres, limit=2):
    return [n for n in TABLE[b]
            if n > apres][:limit]

def tout():
    for b in ("A", "B"):
        dernier = 0          # repart à 0
        while True:
            p = page(b, dernier)
            yield from ((b, n) for n in p)
            if len(p) < 2:
                break
            dernier = p[-1]

len(list(tout()))  # → 5
```

```python
# Exemple 3 : une clé texte ment sur l'ordre
cles = ["A202602019", "A2026020110"]
sorted(cles)
# → ["A2026020110", "A202602019"]
# 10e caractère : "1" < "9"
max(cles)  # → "A202602019"
```

- Quiz : Exemple 1 : si `page` filtre `n >= apres` au lieu de `n > apres`, que vaut `len(list(tout()))` ?
- [ ] `250`
- [x] `252`
- [ ] Boucle infinie
- [ ] `248`
- Réponse : `252` : chaque page recommence par la dernière clé de la précédente ; deux pages suivantes, deux doublons.

## 8. curseur : renvoyer le jeton tel quel
- Id : api-de-donnees-curseur-jeton-opaque
- Sous-thème : pagination
- Type : recette
- Niveau : 2
- Profils : data, web
- Voir aussi : api-de-donnees-keyset-derniere-cle, Python/generateurs-pagination-api
- Mots-clés : générateur, S3
- Définition : Avec un curseur opaque, chaque page renvoie un jeton (`next`) à repasser tel quel pour la page suivante ; plus de jeton, plus de page.
- Contexte : Le serveur encode lui-même sa position (souvent la dernière clé, en base64) : le client n'a ni tri ni offset à gérer. C'est le modèle des API AWS (`NextToken`, `ContinuationToken` de S3) et de beaucoup d'API REST (`next` en lien). Règles : ne jamais décoder ni fabriquer le jeton, s'arrêter sur son absence et non sur une page vide ou courte, savoir qu'il expire souvent.
- Usage : ✅ API qui le propose (AWS, GitHub, Stripe) : boucle `while token` dans un générateur · ❌ réutiliser un vieux jeton le lendemain pour reprendre : il a souvent expiré.

```python
# Exemple 1 : boucler tant qu'il y a un jeton
PAGES = {None: (["A1", "A2"], "t1"),
         "t1": (["A3"], "t2"),
         "t2": (["A4"], None)}

def lister():
    token = None
    while True:
        items, token = PAGES[token]
        yield from items
        if token is None:
            break

len(list(lister()))  # → 4
```

```python
# Exemple 2 : une page vide n'est pas la fin
PAGES = {None: (["A1"], "t1"),
         "t1": ([], "t2"),      # filtrée
         "t2": (["A9"], None)}
token, vus = None, []
while True:
    items, token = PAGES[token]
    if not items:
        break                   # trop tôt
    vus += items
vus  # → ["A1"]   (A9 jamais lu)
```

- Quiz : Exemple 1 avec `limit=2` : un client qui s'arrête dès qu'une page compte moins de 2 éléments lit combien d'annonces ?
- [ ] 2
- [x] 3
- [ ] 4
- Réponse : 3 : la page `t1` n'a qu'un élément mais porte un jeton ; avec un curseur, seule l'absence de jeton marque la fin.

## 9. export : un flux au lieu de 325 pages
- Id : api-de-donnees-export-en-flux
- Sous-thème : pagination
- Type : recette
- Niveau : 2
- Profils : data
- Voir aussi : ingestion-generateurs-pipeline-en-flux
- Mots-clés : keyset, streaming, JSON Lines, idempotent
- Source : data-platform · S1-05
- Définition : L'endpoint d'export renvoie tout le résultat filtré en une requête, une ligne JSON par enregistrement, sans plafond : on le lit en streaming.
- Contexte : Une journée BODACC : 1 appel, 32 373 lignes, 59 Mo en 5 s, contre 325 pages en keyset. Contreparties : une connexion longue (timeout de lecture de 60 s, le défaut httpx est 5 s), une lecture ligne par ligne (`iter_lines`) pour ne jamais tenir 59 Mo en mémoire, et un en-tête qui ment : `content-type: application/json` pour du JSONL, donc pas de `r.json()`.
- Usage : ✅ ingérer une journée ou un lot complet en un appel · ❌ besoin de reprendre au milieu, ou export instable : keyset en plan B.

```bash
# Exemple 1 : la journée en une requête
curl -s -G --compressed \
  "$BODACC/exports/jsonl" \
  --data-urlencode \
  "where=dateparution=date'2026-10-20'" \
  --data-urlencode "select=id" | wc -l
# → 32373   (2 à 4 s)
```

```python
# Exemple 2 : lire en flux, ligne à ligne
import io
import json

corps = io.BytesIO(b'{"id": "A1"}\n'
                   b'{"id": "B7"}\n')

def annonces(flux):
    for ligne in flux:  # ≈ iter_lines()
        if ligne.strip():
            yield json.loads(ligne)

[a["id"] for a in annonces(corps)]
# → ["A1", "B7"]
```

- Quiz : La connexion coupe à 80 % de l'export : que faut-il relancer ?
- [x] Toute la journée
- [ ] Les 20 % restants
- [ ] La dernière ligne lue
- Réponse : toute la journée : un export n'a pas de curseur ; seul un keyset repart de la dernière clé, et l'ingestion idempotente rend ce rejeu sûr.

## 10. pagination : choisir la stratégie
- Id : api-de-donnees-pagination-choisir
- Sous-thème : pagination
- Type : choisir
- Niveau : 2
- Profils : data
- Prérequis : api-de-donnees-offset-fenetre-plafonnee, api-de-donnees-keyset-derniere-cle, api-de-donnees-curseur-jeton-opaque
- Voir aussi : api-de-donnees-export-en-flux
- Mots-clés : BODACC
- Définition : Quatre façons de lire un gros résultat : offset (sauter N lignes), keyset (après la dernière clé), curseur (jeton du serveur), export (un flux).
- Contexte : Le choix suit le volume et ce que l'API offre. Offset : simple, mais plafonné et instable si les données bougent. Keyset : coût constant, il faut une clé unique et triable. Curseur : le serveur garde la position, on renvoie son jeton. Export : un seul appel, mais une coupure fait tout relancer. Sur BODACC, 32 373 lignes par jour excluent l'offset : export, keyset en plan B.
- Usage : ✅ mesurer le volume (`total_count`) puis choisir : export s'il existe, sinon curseur ou keyset · ❌ offset au-delà de quelques milliers de lignes.

```python
# Exemple 1 : la stratégie selon l'API
def choisir(total, export, cle_triee):
    if export:
        return "export"
    if total <= 10_000:
        return "offset"
    return "keyset" if cle_triee else "?"

choisir(32_373, True, True)   # → "export"
choisir(32_373, False, True)  # → "keyset"
choisir(800, False, False)    # → "offset"
```

- Quiz : Ni export ni clé triable, 32 373 lignes par jour, offset plafonné à 10 000 : comment tout lire ?
- [ ] Offset jusqu'à 32 373, page par page
- [x] Découper le `where` en tranches de moins de 10 000
- [ ] `limit=32373` en une seule page
- [ ] C'est impossible avec cette API
- Réponse : découper le filtre (par famille, par département) pour que chaque tranche tienne sous la fenêtre, puis paginer chaque tranche par offset.

## 11. erreur d'API : lire avant de parser
- Id : api-de-donnees-erreur-lire-avant-parser
- Sous-thème : erreurs
- Type : piège
- Niveau : 2
- Profils : data, web
- Prérequis : api-de-donnees-codes-http-retenter-ou-lever
- Mots-clés : HTTP 429
- Source : data-platform · S1-05
- Définition : On teste le statut HTTP et on lit le corps d'erreur (`error_code`) avant d'accéder aux données : une erreur arrive souvent en JSON valide.
- Contexte : Une API de données répond 400 avec `{"error_code", "message"}` : du JSON parfaitement valide, mais sans `results`. Parser sans tester le statut donne `KeyError: 'results'`, loin de la cause. Réflexe d'exploration : afficher la réponse brute (`python3 -m json.tool`). Dans le client : lever sur le statut, décider sur `error_code` (stable), jamais sur le texte de `message`, qui peut changer.
- Usage : ✅ tout client HTTP : statut d'abord, 4xx = lever, 429 et 5xx = réessayer · ❌ `r.json()["results"]` sans test : l'erreur réelle est masquée par un `KeyError`.

```python
# Exemple 1 : le 400 est du JSON valide
import json

corps = ('{"error_code": "Incompatible'
         'TypesInComparisonFilter",'
         ' "message": "Left type: text"}')
r = json.loads(corps)   # aucune erreur
"results" in r          # → False
r["results"]            # ❌ KeyError
```

```python
# Exemple 2 : statut d'abord, puis le code
import json

class ApiError(Exception):
    pass

def results(statut, corps):
    r = json.loads(corps)
    if statut != 200:
        raise ApiError(r["error_code"])
    return r["results"]

results(200, '{"results": [1]}')  # → [1]
results(400, '{"error_code": "X"}')  # ❌ ApiError
```

- Quiz : Un pare-feu renvoie un 403 en page HTML : que fait `json.loads(corps)` dans `results` ?
- [ ] `KeyError: 'error_code'`
- [x] `JSONDecodeError`
- [ ] Renvoie un dict vide
- [ ] `ApiError("403")`
- Réponse : `JSONDecodeError` : toutes les erreurs ne sont pas en JSON (proxy, pare-feu, passerelle) ; tester le statut avant de parser, et garder un extrait du texte brut dans l'exception.

## 12. compression : httpx décompresse seul
- Id : api-de-donnees-httpx-decompresse-seul
- Sous-thème : requêtes
- Type : piège
- Niveau : 2
- Profils : data, web
- Voir aussi : formats-gzip-compresser-le-brut
- Mots-clés : httpx, gzip, Lambda
- Définition : Un client HTTP annonce `Accept-Encoding: gzip` et décompresse la réponse : avec httpx, `r.content` et `iter_lines()` rendent déjà le texte décodé.
- Contexte : L'export BODACC arrive en gzip : 59 Mo de JSON, quelques Mo sur le réseau. httpx envoie l'en-tête par défaut et décode à la lecture ; seul `iter_raw()` rend les octets compressés. curl, lui, ne décompresse qu'avec `--compressed`. Piège de mesure : `Content-Length` donne la taille compressée, pas celle du texte ; pour dimensionner mémoire et stockage, compter les octets décodés.
- Usage : ✅ laisser httpx gérer, mesurer le volume décodé · ❌ comparer `Content-Length` à la taille écrite dans S3, ou dimensionner la mémoire d'une Lambda sur la taille compressée.

```python
# Exemple 1 : la réponse arrive décodée
import gzip
import httpx

brut = b'{"id": "A1"}\n' * 1000
r = httpx.Response(200,
    headers={"content-encoding": "gzip"},
    content=gzip.compress(brut))
r.content == brut  # → True
len(brut)          # → 13000
```

```python
# Exemple 2 : la taille annoncée ment
import gzip

brut = b'{"id": "A1"}\n' * 1000
gz = gzip.compress(brut)  # Content-Length
len(gz) < len(brut) // 50  # → True
```

- Quiz : Exemple 1 : que fait `gzip.decompress(r.content)` ?
- [ ] Renvoie `brut`
- [ ] Renvoie les octets compressés
- [x] `BadGzipFile`
- [ ] `UnicodeDecodeError`
- Réponse : `BadGzipFile` (sous-classe d'`OSError`) : `r.content` est déjà décodé ; le décompresser une seconde fois échoue.

## 13. quota : partagé, remis à zéro à minuit
- Id : api-de-donnees-quota-partage
- Sous-thème : quotas
- Type : concept
- Niveau : 2
- Profils : data
- Voir aussi : api-de-donnees-limiter-son-debit
- Mots-clés : BODACC, backoff exponentiel, UTC
- Source : data-platform · S1-05
- Définition : Une API annonce son quota dans les en-têtes `X-RateLimit-Limit`, `-Remaining` et `-Reset` ; au-delà, elle répond HTTP 429.
- Contexte : BODACC : 5 000 000 d'appels par jour pour toute l'instance, remis à zéro à minuit UTC. `remaining` a perdu 2 523 en 69 s sans aucun appel de notre part : le quota est partagé, un autre client peut l'épuiser avant notre passage. Une journée nous coûte 1 appel : inutile de sur-concevoir, mais le 429 reste possible. Sur 429 : backoff court, puis échec propre et relance après le reset.
- Usage : ✅ lire les en-têtes avant de dimensionner retries et parallélisme ; `User-Agent` explicite sur une instance partagée · ❌ réessayer en boucle sur 429 : on brûle le quota de tous.

```python
# Exemple 1 : ce que coûte une journée
h = {"x-ratelimit-limit": "5000000",
     "x-ratelimit-remaining": "2996594"}
reste = int(h["x-ratelimit-remaining"])
cout = {"export": 1, "keyset": 325}
{k: v <= reste for k, v in cout.items()}
# → {"export": True, "keyset": True}
f"{325 / 5_000_000:.4%}"  # → "0.0065%"
```

```python
# Exemple 2 : attendre le reset ou échouer
from datetime import datetime, timedelta

reset = datetime.fromisoformat(
    "2026-10-25 00:00:00+00:00")
now = datetime.fromisoformat(
    "2026-10-24 14:03:21+00:00")
attente = reset - now
round(attente.total_seconds() / 3600, 1)
# → 9.9  (heures)
attente > timedelta(minutes=15)
# → True : échouer, relancer demain
```

- Quiz : `x-ratelimit-reset` vaut `2026-10-25 00:00:00+00:00` : à quelle heure de Paris le quota revient-il ?
- [ ] 00:00
- [ ] 01:00
- [x] 02:00
- [ ] 03:00
- Réponse : 02:00 : à minuit UTC, Paris est encore à l'heure d'été (UTC+2) ; le passage à l'heure d'hiver n'a lieu qu'à 01:00 UTC ce jour-là.

## 14. Retry-After : secondes ou date HTTP
- Id : api-de-donnees-retry-after-deux-formes
- Sous-thème : quotas
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : api-de-donnees-codes-http-retenter-ou-lever
- Voir aussi : ingestion-retry-backoff-exponentiel
- Mots-clés : HTTP 429, backoff exponentiel, Lambda
- Définition : L'en-tête `Retry-After` d'un 429 ou 503 dit quand réessayer : un nombre de secondes (`120`) ou une date HTTP (`Sat, 24 Oct 2026 14:05:00 GMT`).
- Contexte : Le serveur sait mieux que le client quand son quota se libère : sa valeur prime sur le backoff. La RFC 9110 autorise les deux formes ; beaucoup de clients ne lisent que les secondes (`fetch_day` retombe sinon sur son backoff). Une date se convertit en attente avec `parsedate_to_datetime`, moins l'heure courante. Toujours plafonner : 9 heures d'attente dans une Lambda de 15 minutes, c'est échouer et relancer plus tard.
- Usage : ✅ lire les deux formes, plafonner, retomber sur le backoff si la valeur est illisible · ❌ dormir la valeur reçue sans plafond : `Retry-After: 36000` bloque le run ou dépasse le timeout.

```python
# Exemple 1 : les deux formes
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

def attente(h, now):
    if h.strip().isdigit():
        return float(h)
    d = parsedate_to_datetime(h)
    return (d - now).total_seconds()

now = datetime(2026, 10, 24, 14, 3,
               tzinfo=timezone.utc)
attente("120", now)  # → 120.0
h = "Sat, 24 Oct 2026 14:05:00 GMT"
attente(h, now)      # → 120.0
```

```python
# Exemple 2 : plafonner l'attente
def dormir(h, plafond=60):
    s = float(h)
    if s > plafond:
        raise RuntimeError("relancer après")
    return s

dormir("7")      # → 7.0
dormir("36000")  # ❌ RuntimeError
```

- Quiz : Exemple 1 : que fait `attente("1.5", now)` ?
- [ ] Renvoie `1.5`
- [x] `ValueError`
- [ ] Renvoie `0.0`
- [ ] `TypeError`
- Réponse : `ValueError` : `"1.5".isdigit()` est faux, la chaîne part dans `parsedate_to_datetime`, qui ne la lit pas ; prévoir un repli sur le backoff.

## 15. ETag : If-None-Match et 304
- Id : api-de-donnees-etag-if-none-match
- Sous-thème : cache
- Type : recette
- Niveau : 2
- Profils : data, web
- Voir aussi : api-de-donnees-last-modified, AWS/s3-etag-sse-kms
- Définition : L'ETag est l'empreinte d'une réponse ; renvoyé dans `If-None-Match`, il obtient `304 Not Modified`, sans corps, si rien n'a changé.
- Contexte : Une ingestion qui sonde une ressource (fichier de référence, métadonnées) n'a pas à la retélécharger si elle est identique. On stocke l'ETag reçu avec la donnée ; au run suivant on le renvoie : 304, rien à faire ; 200, nouveau contenu et nouvel ETag. Un ETag faible (`W/"…"`) signale une équivalence, pas une identité d'octets. Toutes les API n'en fournissent pas : `/records` de BODACC n'envoie ni ETag ni `Last-Modified`.
- Usage : ✅ sonder un fichier de référence, un catalogue, un objet S3 · ❌ traiter un 304 comme une réponse vide à ingérer : on écrase la donnée par rien.

```python
# Exemple 1 : le serveur compare l'ETag
import hashlib

corps = b'{"records_count": 51155363}'
h = hashlib.md5(corps).hexdigest()[:8]
etag = f'"{h}"'

def get(if_none_match=None):
    if if_none_match == etag:
        return 304, b""
    return 200, corps

get()[0]   # → 200
get(etag)  # → (304, b"")
```

```python
# Exemple 2 : le client garde l'ETag
etat = {"etag": '"a1b2"', "data": "v1"}

def run(statut, corps, etag):
    if statut == 304:
        return etat          # inchangé
    etat.update(etag=etag, data=corps)
    return etat

run(304, "", None)["data"]  # → "v1"
run(200, "v2", '"c3d4"')["etag"]
# → '"c3d4"'
```

- Quiz : Exemple 1 : le client renvoie l'ETag sans ses guillemets (`get(h)`). Que répond le serveur ?
- [ ] `304`, sans corps
- [x] `200`, avec le corps complet
- [ ] `400 Bad Request`
- [ ] `412 Precondition Failed`
- Réponse : `200` avec le corps : la comparaison porte sur la valeur exacte, guillemets compris ; renvoyer l'ETag tel qu'il a été reçu.

## 16. Last-Modified : If-Modified-Since
- Id : api-de-donnees-last-modified
- Sous-thème : cache
- Type : recette
- Niveau : 2
- Profils : data, web
- Voir aussi : api-de-donnees-etag-if-none-match
- Mots-clés : ETag, HTTP 304, UTC
- Définition : `Last-Modified` donne la date de dernière modification d'une ressource ; renvoyée dans `If-Modified-Since`, elle obtient un 304 si rien n'a bougé depuis.
- Contexte : Même principe que l'ETag, sur une date, à la seconde près au mieux : deux modifications dans la même seconde passent inaperçues. Si le serveur fournit les deux, `If-None-Match` prime (RFC 9110). La date est au format HTTP, toujours en GMT ; `format_datetime(d, usegmt=True)` la produit. Renvoyer la valeur reçue telle quelle plutôt que sa propre horloge, qui peut dériver.
- Usage : ✅ fichiers statiques, objets S3, sources sans ETag · ❌ envoyer l'heure du client à la place de la valeur reçue : décalage d'horloge, faux 304.

```python
# Exemple 1 : formater la date HTTP
from datetime import datetime, timezone
from email.utils import format_datetime

d = datetime(2026, 10, 22, 6, 17, 43,
             tzinfo=timezone.utc)
format_datetime(d, usegmt=True)
# → "Thu, 22 Oct 2026 06:17:43 GMT"
```

```python
# Exemple 2 : 304 si rien depuis
from email.utils import (
    parsedate_to_datetime as p)

modifie = p("Thu, 22 Oct 2026 06:17:43 GMT")

def get(ims):
    return 304 if p(ims) >= modifie else 200

get("Thu, 22 Oct 2026 06:17:43 GMT")
# → 304
get("Wed, 21 Oct 2026 07:00:00 GMT")
# → 200
```

- Quiz : Que fait `format_datetime(d, usegmt=True)` si `d` est naïf (sans `tzinfo`) ?
- [x] `ValueError`
- [ ] Renvoie l'heure locale suffixée `GMT`
- [ ] Renvoie la date suffixée `-0000`
- [ ] `TypeError`
- Réponse : `ValueError` (usegmt option requires a UTC datetime) : la date HTTP exige un `datetime` aware en UTC.

## 17. version d'API : figée dans l'URL
- Id : api-de-donnees-version-dans-url
- Sous-thème : contrat
- Type : concept
- Niveau : 2
- Profils : data, web
- Voir aussi : api-de-donnees-sunset-deprecation
- Définition : Une API publique versionne son contrat (`/api/explore/v2.1/`) : on code contre une version précise, jamais contre « la dernière ».
- Contexte : Une version majeure peut renommer des champs ou changer la pagination ; une mineure (v2.0 vers v2.1) ajoute sans casser. Fixer la version dans l'URL de base, une constante unique du client (`DEFAULT_BASE_URL`), rend la montée de version explicite, relue et testée. La version passe parfois par un en-tête (`X-GitHub-Api-Version`). Les ajouts de champs, eux, arrivent sans nouvelle version : le client doit tolérer l'inconnu.
- Usage : ✅ version dans une constante, suivie du journal des changements de la source · ❌ URL sans version ou alias `latest` : la source change sous un run de nuit.

```python
# Exemple 1 : la version dans la constante
BASE = ("https://bodacc-datadila"
        ".opendatasoft.com/api/explore"
        "/v2.1/catalog/datasets"
        "/annonces-commerciales")
BASE.split("/")[5]  # → "v2.1"
```

```python
# Exemple 2 : majeure = rupture possible
def majeure(v):
    return int(v.lstrip("v").split(".")[0])

def rupture(avant, apres):
    return majeure(apres) > majeure(avant)

rupture("v2.0", "v2.1")  # → False
rupture("v2.1", "v3.0")  # → True
```

- Quiz : Pour savoir si la v2.10 est plus récente que la v2.9, que vaut `"2.10" > "2.9"` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : comparaison de chaînes, caractère par caractère (`"1" < "9"`) ; comparer des tuples d'entiers, `(2, 10) > (2, 9)`.

## 18. offset : la page qui glisse
- Id : api-de-donnees-offset-page-qui-glisse
- Sous-thème : pagination
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : api-de-donnees-offset-fenetre-plafonnee
- Voir aussi : api-de-donnees-keyset-derniere-cle
- Mots-clés : keyset
- Définition : Si des lignes s'insèrent ou disparaissent pendant une lecture par offset, les pages se décalent : lignes lues deux fois, ou jamais.
- Contexte : L'offset désigne une position, pas une ligne. Une insertion en tête pendant la lecture pousse tout d'un cran : la première ligne de la page suivante a déjà été lue. Une suppression fait l'inverse : une ligne passe la frontière sans être lue. Le keyset n'a pas ce défaut (il repart d'une clé). Sur une journée de parution close, le risque est faible ; sur un jeu vivant, il est certain.
- Usage : ✅ offset sur des données figées (journée close, snapshot), triées sur une clé unique · ❌ offset sur une table qui reçoit des lignes pendant la lecture : keyset ou export.

```python
# Exemple 1 : une insertion pendant la lecture
table = ["A5", "A4", "A3", "A2"]
lus = table[0:2]          # page 1
table.insert(0, "A6")     # nouvelle
lus += table[2:4]         # page 2
lus  # → ["A5", "A4", "A4", "A3"]
# A4 lue deux fois, A2 jamais
```

```python
# Exemple 2 : une suppression pendant la lecture
table = ["A1", "A2", "A3", "A4"]
lus = table[0:2]          # A1, A2
table.remove("A1")        # annulée
lus += table[2:4]         # page 2
lus  # → ["A1", "A2", "A4"]  (A3 sautée)
```

- Quiz : Même insertion qu'à l'exemple 1, mais en keyset (page 2 = les 2 clés après `"A4"` en ordre décroissant) : que vaut `lus` ?
- [ ] `["A5", "A4", "A4", "A3"]`
- [x] `["A5", "A4", "A3", "A2"]`
- [ ] `["A6", "A5", "A4", "A3"]`
- Réponse : `["A5", "A4", "A3", "A2"]` : la page repart de la dernière clé lue, `A6` inséré au-dessus ne décale rien ; il sera lu au prochain run.

## 19. max-age : une réponse qui date
- Id : api-de-donnees-max-age-reponse-datee
- Sous-thème : cache
- Type : piège
- Niveau : 3
- Profils : data, expert
- Voir aussi : api-de-donnees-etag-if-none-match, AWS/cloudfront-cache-control-ttl
- Mots-clés : CDN, RFC
- Définition : `Cache-Control: max-age=60` autorise caches et CDN à resservir la même réponse pendant 60 s : ce qu'on lit peut dater d'une minute.
- Contexte : BODACC répond `cache-control: public, max-age=60` : un proxy entre nous et la source peut rendre une version vieille de 60 s, et l'en-tête `Age` (RFC 9111) dit depuis combien de temps elle est en cache. Pour une ingestion quotidienne, sans effet. Ça compte quand on enchaîne deux appels qui doivent être cohérents (`total_count` puis export) ou une relecture juste après une mise à jour de la source.
- Usage : ✅ lire `Age` et `Cache-Control` pour expliquer un écart entre deux appels proches · ❌ conclure à une perte de données parce qu'un comptage relu tout de suite est ancien.

```python
# Exemple 1 : âge restant d'une réponse
h = {"cache-control": "public, max-age=60",
     "age": "42"}
cc = h["cache-control"]
max_age = int(cc.split("max-age=")[1])
max_age - int(h["age"])  # → 18
# encore 18 s avant revalidation
```

```python
# Exemple 2 : lire les directives
cc = "public, max-age=60"
d = {}
for p in cc.split(", "):
    k, _, v = p.partition("=")
    d[k] = v or True
d  # → {"public": True, "max-age": "60"}
```

- Quiz : Exemple 1 avec `"max-age=60, public"` (ordre inversé) : que fait `int(cc.split("max-age=")[1])` ?
- [ ] Renvoie `60`
- [x] `ValueError`
- [ ] `IndexError`
- [ ] Renvoie `"60, public"`
- Réponse : `ValueError` : la fin de chaîne vaut `"60, public"`, que `int` refuse ; découper par directive (exemple 2), jamais par sous-chaîne.

## 20. débit : espacer ses appels
- Id : api-de-donnees-limiter-son-debit
- Sous-thème : quotas
- Type : recette
- Niveau : 3
- Profils : data, expert
- Prérequis : api-de-donnees-quota-partage
- Voir aussi : api-de-donnees-retry-after-deux-formes
- Mots-clés : keyset, quota, HTTP 429, backfill
- Définition : Un client limite lui-même son débit (N appels par seconde) pour rester sous le quota, au lieu d'attendre que le serveur réponde 429.
- Contexte : Paralléliser 325 pages keyset sur 20 threads crée un pic que le serveur coupe en 429, puis tous les threads attendent ensemble. Un limiteur côté client (intervalle minimal entre deux appels, ou seau à jetons qui tolère une rafale puis impose un débit moyen) lisse la charge. Avec un quota partagé comme celui de BODACC, c'est aussi ne pas prendre la part des autres. Le serveur reste juge : le 429 doit toujours être géré.
- Usage : ✅ pagination parallèle, backfill de centaines de jours, API à quota par seconde · ❌ `sleep` fixe après chaque appel quand l'appel est lent : on attend deux fois.

```python
# Exemple 1 : un intervalle minimal
class Limiteur:
    def __init__(self, par_s, horloge):
        self.pas = 1 / par_s
        self.t = horloge
        self.prochain = 0.0

    def attente(self):
        now = self.t()
        a = max(0.0, self.prochain - now)
        base = max(now, self.prochain)
        self.prochain = base + self.pas
        return a

temps = iter([0.0, 0.25, 1.5])
lim = Limiteur(2, lambda: next(temps))
[lim.attente() for _ in range(3)]
# → [0.0, 0.25, 0.0]
```

```python
# Exemple 2 : le temps d'un backfill
pages, debit = 325, 5   # appels par s
pages / debit           # → 65.0  (s)
```

- Quiz : Limiteur à 2 appels/s, quatre threads l'appellent tous à `t = 0` : quelles attentes renvoie-t-il ?
- [ ] `[0.0, 0.0, 0.0, 0.0]`
- [ ] `[0.0, 0.5, 0.5, 0.5]`
- [x] `[0.0, 0.5, 1.0, 1.5]`
- [ ] `[0.5, 1.0, 1.5, 2.0]`
- Réponse : `[0.0, 0.5, 1.0, 1.5]` : chaque appel réserve le créneau suivant, un pas de 0,5 s ; le premier part tout de suite.

## 21. Sunset : la fin annoncée d'un endpoint
- Id : api-de-donnees-sunset-deprecation
- Sous-thème : contrat
- Type : concept
- Niveau : 3
- Profils : data, ops
- Prérequis : api-de-donnees-version-dans-url
- Mots-clés : OpenDataSoft, RFC, httpx
- Définition : Les en-têtes `Deprecation` et `Sunset` annoncent qu'un endpoint est déprécié et la date où il cessera de répondre.
- Contexte : `Sunset` (RFC 8594) porte une date HTTP ; `Deprecation` (RFC 9745) une date `@<epoch>`. OpenDataSoft a le sien, `ODS-Explore-API-Deprecation`, listé dans `access-control-expose-headers`. Un client d'ingestion ne lit jamais les en-têtes : sans contrôle, on découvre la fin d'une version le jour où elle répond 410 Gone. Les journaliser en warning à chaque run, avec une alerte, laisse des semaines pour migrer.
- Usage : ✅ un warning (et une alarme) dès qu'un de ces en-têtes apparaît · ❌ compter sur eux seuls : beaucoup d'API ne les envoient pas, suivre aussi le journal des changements.

```python
# Exemple 1 : la date de fin
from email.utils import parsedate_to_datetime

h = {"sunset":
     "Sat, 31 Oct 2026 23:59:59 GMT"}
fin = parsedate_to_datetime(h["sunset"])
fin.date().isoformat()  # → "2026-10-31"
```

```python
# Exemple 2 : Deprecation, date en epoch
from datetime import datetime, timezone

dep = "@1793404800"
t = datetime.fromtimestamp(
    int(dep[1:]), tz=timezone.utc)
t.date().isoformat()  # → "2026-10-31"
```

- Quiz : La réponse httpx porte l'en-tête `sunset` en minuscules : que renvoie `r.headers["Sunset"]` ?
- [ ] `KeyError`
- [ ] `None`
- [x] La valeur de l'en-tête
- Réponse : la valeur : `httpx.Headers` ignore la casse des noms, comme HTTP ; un `dict` Python, lui, lèverait `KeyError`.
