---
title: "Cartes · Générateurs Python"
type: cartes
langage: Python
chapitre: Python idiomatique
cours: Générateurs
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Générateurs Python
Python · Générateurs : bases, composer, paresse, pièges (format spec v3 de revision-pwa).

## 1. yield : la fonction génératrice
- Id : generateurs-yield-a-la-demande
- Sous-thème : yield
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Mots-clés : générateur
- Définition : Une fonction contenant `yield` renvoie un générateur, dont le corps s'exécute à la demande, une valeur à la fois (≈ `function*` en TS).
- Contexte : L'appel `lots()` n'exécute aucune ligne du corps : il crée un objet générateur. Chaque `next(g)` reprend le corps là où il s'était arrêté, jusqu'au `yield` suivant, et rend sa valeur. Les variables locales sont conservées entre deux reprises. Différence avec TS : pas d'astérisque, c'est la seule présence de `yield` dans le corps qui change la nature de la fonction.
- Usage : ✅ produire une suite de valeurs sans la stocker (lignes d'un fichier, annonces d'une API) · ❌ petit résultat relu plusieurs fois : renvoyer une `list`.

```python
# Exemple 1 : le corps tourne à la demande
def lots():
    yield "A1"   # pause ici
    yield "A2"
g = lots()       # rien ne s'exécute
next(g)          # → "A1"
next(g)          # → "A2"
```

```python
# Exemple 2 : l'état local survit
def compteur():
    n = 0
    while True:
        n += 1   # repris au next suivant
        yield n

c = compteur()
next(c)   # → 1
next(c)   # → 2
```

- Quiz : Avec `def f():` / `print("go")` / `yield 1`, qu'affiche `g = f()` seul ?
- [ ] `go`
- [ ] `go` puis `1`
- [x] Rien
- [ ] `1`
- Réponse : Rien : l'appel crée le générateur sans exécuter le corps ; `go` ne s'affiche qu'au premier `next(g)`.

## 2. next : la fin du flux
- Id : generateurs-next-stopiteration
- Sous-thème : itérateurs
- Type : concept
- Niveau : 1
- Profils : débutant
- Prérequis : generateurs-yield-a-la-demande
- Mots-clés : générateur, yield, exception
- Définition : `next(g)` reprend le générateur jusqu'au prochain `yield` ; quand le corps se termine, il lève `StopIteration`.
- Contexte : `for` appelle `next` en boucle et s'arrête proprement sur `StopIteration` : on ne voit jamais l'exception. Appelé à la main, `next` la laisse remonter. Son second argument est une valeur par défaut renvoyée à la place de l'exception : l'idiome « le premier élément ou rien », sans `try`. En TS, `it.next()` renvoie `{ done: true }` au lieu de lever.
- Usage : ✅ lire le premier élément d'un flux (`next(g, None)`), avancer pas à pas dans un test · ❌ parcourir tout le flux : une boucle `for`.

```python
# Exemple 1 : après le dernier yield
def lots():
    yield "A1"
g = lots()
next(g)   # → "A1"
next(g)   # ❌ StopIteration
```

```python
# Exemple 2 : le premier qui correspond
sirens = ["552100554", "483609327"]
g = (s for s in sirens
     if s.startswith("4"))
next(g, None)   # → "483609327"
next(g, None)   # → None  (épuisé)
```

- Quiz : Avec `def f():` / `return` / `yield 1`, que fait `next(f())` ?
- [ ] Renvoie `None`
- [ ] Renvoie `1`
- [ ] `SyntaxError`
- [x] `StopIteration`
- Réponse : `StopIteration` : le `yield`, même inatteignable, fait de `f` un générateur, et `return` le termine avant tout `yield`.

## 3. Générateur : une seule passe
- Id : generateurs-une-seule-passe
- Sous-thème : itérateurs
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Prérequis : generateurs-iterable-ou-iterateur
- Voir aussi : generateurs-in-consomme
- Mots-clés : générateur
- Définition : Un générateur se parcourt une seule fois : `for`, `list` ou une compréhension le consomment jusqu'au bout.
- Contexte : Un générateur ne garde pas ses valeurs : une fois émise, une valeur est perdue. Un deuxième parcours ne lève aucune erreur, il ne produit simplement rien, ce qui rend le bug silencieux (une somme à 0, une boucle qui ne tourne pas). Pour relire, rappeler la fonction pour obtenir un générateur neuf, ou matérialiser une fois avec `list(g)`.
- Usage : ✅ un seul parcours (écrire les annonces dans S3, agréger) · ❌ données lues deux fois (compter puis traiter) : `list(g)` d'abord, ou rappeler la fonction.

```python
# Exemple 1 : le second parcours est vide
def sirens():
    yield "483609327"
    yield "552100554"
g = sirens()
len(list(g))   # → 2
list(g)        # → []  (épuisé, sans erreur)
```

```python
# Exemple 2 : un générateur neuf par appel
def sirens():
    yield "483609327"
    yield "552100554"

len(list(sirens()))   # → 2
len(list(sirens()))   # → 2  (nouveau)
sirens() is sirens()  # → False
```

- Quiz : Que fait `max(g)` sur un `g` déjà épuisé ?
- [ ] Renvoie `None`
- [x] `ValueError`
- [ ] `StopIteration`
- [ ] Renvoie `"552100554"`
- Réponse : `ValueError` (max() iterable argument is empty) : un générateur épuisé se comporte comme une séquence vide.

## 4. Expression génératrice : la syntaxe
- Id : generateurs-expression-syntaxe
- Sous-thème : expressions
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : listes-comprehensions
- Mots-clés : générateur, compréhension
- Définition : `(expr for x in it)` crée un générateur en une ligne, comme une compréhension de liste mais sans construire la liste.
- Contexte : Seule différence d'écriture avec `[...]` : les parenthèses. Rien n'est calculé à la création : chaque valeur l'est au moment où on la demande, alors que les crochets calculent tout de suite la liste entière. Le résultat se parcourt une seule fois mais occupe une mémoire constante, quel que soit le volume.
- Usage : ✅ transformer ou filtrer un flux qu'on parcourt une fois (`sum`, `join`, écriture) · ❌ résultat relu, indexé ou mesuré : compréhension de liste `[...]`.

```python
# Exemple 1 : parenthèses au lieu de crochets
sirens = ["12345678", "483609327"]
g = (s.zfill(9) for s in sirens)
next(g)   # → "012345678"
next(g)   # → "483609327"
```

```python
# Exemple 2 : avec un filtre
capitaux = [500, 9000, 1200]
g = (c * 2 for c in capitaux
     if c > 1000)
list(g)   # → [18000, 2400]
```

- Quiz : Avec `g = (s for s in sirens)`, que fait `g[0]` ?
- [ ] Renvoie `"12345678"`
- [ ] `IndexError`
- [x] `TypeError`
- [ ] Renvoie `None`
- Réponse : `TypeError` ('generator' object is not subscriptable) : pas d'index ; utiliser `next(g)`.

## 5. Expression génératrice : dans un appel
- Id : generateurs-expression-dans-un-appel
- Sous-thème : expressions
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Prérequis : generateurs-expression-syntaxe
- Voir aussi : listes-any-all
- Mots-clés : itérable, compréhension
- Définition : Seul argument d'un appel, une expression génératrice se passe de ses parenthèses : celles de l'appel suffisent.
- Contexte : `sum(c for c in capitaux)` est l'idiome : aucune liste intermédiaire, contrairement à `sum([c for c in capitaux])` qui construit la liste entière avant d'additionner. Marche avec toute fonction qui consomme un itérable : `sum`, `max`, `any`, `all`, `set`, `"".join`. Avec `any` et `all`, le parcours s'arrête dès que le résultat est connu.
- Usage : ✅ agréger un flux en une valeur (total, test, chaîne jointe) · ❌ résultat réutilisé ensuite : le matérialiser dans une variable `list`.

```python
# Exemple 1 : sum sans liste intermédiaire
capitaux = [500, 9000, 1200]
sum(c for c in capitaux if c > 1000)
# → 10200
```

```python
# Exemple 2 : any s'arrête au premier vrai
sirens = ["483609327", "12", "x"]
any(len(s) != 9 for s in sirens)
# → True  (arrêté sur "12")
",".join(s[:3] for s in sirens)
# → "483,12,x"
```

- Quiz : Que fait `sum(c for c in capitaux, 0)` ?
- [x] `SyntaxError`
- [ ] Renvoie `10700`
- [ ] `TypeError`
- [ ] Renvoie `0`
- Réponse : `SyntaxError` (Generator expression must be parenthesized) : avec un 2e argument, écrire `sum((c for c in capitaux), 0)`.

## 6. Paresse : la mémoire
- Id : generateurs-paresse-memoire
- Sous-thème : paresse
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : generateurs-yield-a-la-demande
- Voir aussi : compression-lire-gros-gz-en-flux
- Mots-clés : générateur, évaluation paresseuse, BODACC, Lambda
- Définition : Un générateur ne stocke pas ses valeurs, il les calcule une à une : sa taille mémoire ne dépend pas du volume.
- Contexte : Une liste de 100 000 éléments garde tous ses éléments en mémoire ; le générateur équivalent ne garde que son état (position, variables locales), quelques centaines d'octets. C'est ce qui permet de traiter une journée de ~32 000 annonces BODACC, ou un fichier de plusieurs Go, ligne à ligne dans une Lambda à 128 Mo. Le prix : une seule passe, pas d'accès direct.
- Usage : ✅ gros volumes lus en flux (fichier, pages d'API, objets S3) · ❌ petit volume relu souvent : une `list` est plus simple et aussi rapide.

```python
# Exemple 1 : liste contre générateur
import sys
liste = [i for i in range(100_000)]
gen = (i for i in range(100_000))
sys.getsizeof(liste) > 800_000  # → True
sys.getsizeof(gen) < 300        # → True
```

```python
# Exemple 2 : un fichier se lit en flux
import io
f = io.StringIO("A1\nA2\nA3\n")
# chaque ligne est lue au next
lignes = (l.strip() for l in f)
next(lignes)   # → "A1"
next(lignes)   # → "A2"
```

- Quiz : Avec `r = range(3)`, que valent `list(r)` puis `list(r)` ?
- [ ] `[0, 1, 2]` puis `[]`
- [ ] `[0, 1, 2]` puis `TypeError`
- [x] `[0, 1, 2]` deux fois
- Réponse : `[0, 1, 2]` deux fois : `range` est paresseux mais réutilisable, c'est un itérable, pas un itérateur à usage unique.

## 7. yield from : déléguer
- Id : generateurs-yield-from
- Sous-thème : composer
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Mots-clés : générateur, itérable
- Définition : `yield from it` émet une à une les valeurs d'un autre itérable ou générateur (≈ `yield*` en TS).
- Contexte : Remplace la boucle `for x in it: yield x`. Il accepte tout itérable : liste, chaîne, `range`, autre générateur. Avec un sous-générateur, il récupère en plus sa valeur de `return` (`n = yield from sous()`). C'est la brique pour composer : un générateur par niveau (jour, page, annonce), assemblés par délégation.
- Usage : ✅ enchaîner plusieurs sources, déléguer à un sous-générateur par page ou par jour · ❌ une seule source sans transformation : la renvoyer telle quelle.

```python
# Exemple 1 : enchaîner deux sources
def pages():
    yield from ["A1", "A2"]
    yield from ["B1"]
list(pages())   # → ["A1", "A2", "B1"]
```

```python
# Exemple 2 : un sous-générateur par jour
def jour(d):
    yield f"{d}-A1"
    yield f"{d}-A2"

def semaine(jours):
    for d in jours:
        yield from jour(d)

list(semaine(["lun", "mar"]))[1:3]
# → ["lun-A2", "mar-A1"]
```

- Quiz : Dans l'exemple 1, si la 1re ligne devient `yield ["A1", "A2"]`, que vaut `list(pages())` ?
- [ ] `["A1", "A2", "B1"]`
- [x] `[["A1", "A2"], "B1"]`
- [ ] `[["A1", "A2"], ["B1"]]`
- [ ] `SyntaxError`
- Réponse : `[["A1", "A2"], "B1"]` : `yield` émet la liste entière comme une seule valeur, `yield from` la déroule.

## 8. itérateur : la différence avec un itérable
- Id : generateurs-iterable-ou-iterateur
- Sous-thème : itérateurs
- Type : comparaison
- Niveau : 2
- Profils : débutant, data
- Prérequis : generateurs-next-stopiteration
- Voir aussi : generateurs-une-seule-passe
- Mots-clés : générateur, méthode spéciale
- Définition : Un itérable (liste) fournit un itérateur via `iter()` ; seul un itérateur (générateur) accepte `next()` et s'épuise.
- Contexte : `for x in obj` appelle `iter(obj)` puis `next` en boucle. Une liste renvoie un itérateur neuf à chaque `iter` : on la relit autant de fois que voulu. Un générateur est son propre itérateur (`iter(g) is g`) : d'où l'usage unique. Une classe dont `__iter__` est un générateur donne un itérable réutilisable, qui produit un flux neuf à chaque parcours.
- Usage : ✅ exposer une collection relisible avec `__iter__` générateur · ❌ passer un générateur à du code qui le parcourt deux fois : passer l'itérable ou une liste.

```python
# Exemple 1 : tester l'un et l'autre
from collections.abc import Iterator
g = (s for s in ["A1"])
isinstance(g, Iterator)       # → True
isinstance(["A1"], Iterator)  # → False
iter(g) is g                  # → True
```

```python
# Exemple 2 : un itérable réutilisable
class Journee:
    def __init__(self, ids):
        self.ids = ids

    def __iter__(self):   # flux neuf
        yield from self.ids

j = Journee(["A1", "A2"])
list(j)   # → ["A1", "A2"]
list(j)   # → ["A1", "A2"]  (relu)
```

- Quiz : Que fait `next(["A1", "A2"])` ?
- [ ] Renvoie `"A1"`
- [x] `TypeError`
- [ ] `StopIteration`
- [ ] `AttributeError`
- Réponse : `TypeError` ('list' object is not an iterator) : une liste est itérable, pas itérateur ; passer par `iter()`.

## 9. islice : prélever dans un flux infini
- Id : generateurs-islice-flux-infini
- Sous-thème : paresse
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : generateurs-yield-a-la-demande
- Voir aussi : generateurs-batched-lots
- Mots-clés : générateur, évaluation paresseuse, itérateur
- Définition : `itertools.islice(g, n)` prélève les `n` premières valeurs d'un générateur, même infini, sans calculer la suite (≈ `take(n)`).
- Contexte : Un générateur peut ne jamais finir (`while True`, `itertools.count`) : `list(g)` bouclerait alors sans fin. Comme un générateur n'a ni longueur ni index, la tranche `g[:3]` est impossible : `islice` en est l'équivalent paresseux et accepte aussi `start, stop, step`. Il renvoie lui-même un itérateur, à matérialiser avec `list`.
- Usage : ✅ tester un générateur sur ses premières valeurs, sauter un en-tête, limiter un flux infini · ❌ sur une liste : une tranche `l[:n]` suffit.

```python
# Exemple 1 : 3 valeurs d'un flux infini
from itertools import count, islice
ids = (f"A{n:04d}" for n in count(1))
list(islice(ids, 3))
# → ["A0001", "A0002", "A0003"]
```

```python
# Exemple 2 : start, stop comme une tranche
from itertools import islice
lignes = iter(["entete", "A1",
               "A2", "A3"])
list(islice(lignes, 1, 3))
# → ["A1", "A2"]  (en-tête sauté)
```

- Quiz : Dans l'exemple 1, que donne un second `list(islice(ids, 3))` ?
- [ ] `["A0001", "A0002", "A0003"]`
- [ ] `[]`
- [x] `["A0004", "A0005", "A0006"]`
- [ ] `StopIteration`
- Réponse : `["A0004", "A0005", "A0006"]` : `islice` consomme `ids`, qui reprend là où il s'était arrêté.

## 10. batched : écrire par lots
- Id : generateurs-batched-lots
- Sous-thème : paresse
- Type : recette
- Niveau : 2
- Profils : data, ops
- Mots-clés : générateur, Kinesis, DynamoDB
- Définition : `itertools.batched(it, n)` (Python 3.12) découpe un flux en tuples de `n` éléments, le dernier pouvant être plus court.
- Contexte : L'outil des écritures groupées : `put_records` de Kinesis accepte 500 enregistrements au plus, `batch_write_item` de DynamoDB 25. Combiné à un générateur, il ne garde jamais plus d'un lot en mémoire. Les lots sont des tuples, pas des listes. Avant Python 3.12, on l'écrivait à la main avec `islice` dans une boucle.
- Usage : ✅ envoyer un flux par paquets (API batch, insertions en base, fichiers découpés) · ❌ Python < 3.12 : boucle avec `islice`.

```python
# Exemple 1 : lots de 2
from itertools import batched
sirens = ["A1", "A2", "A3", "A4", "A5"]
list(batched(sirens, 2))
# → [("A1", "A2"), ("A3", "A4"), ("A5",)]
```

```python
# Exemple 2 : un lot à la fois
from itertools import batched
def annonces():
    for n in range(5):
        yield f"A{n}"

for lot in batched(annonces(), 2):
    print(len(lot), lot[0])
# affiché : 2 A0
# affiché : 2 A2
# affiché : 1 A4
```

- Quiz : Avec `from itertools import count`, que fait `next(batched(count(), 2))` ?
- [x] Renvoie `(0, 1)`
- [ ] Ne rend jamais la main
- [ ] Renvoie `[0, 1]`
- [ ] `MemoryError`
- Réponse : Renvoie `(0, 1)` immédiatement : `batched` est paresseux, il ne lit que deux éléments, même d'une source infinie.

## 11. return : arrêter le flux
- Id : generateurs-return-arrete-flux
- Sous-thème : yield
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : generateurs-next-stopiteration
- Mots-clés : générateur, StopIteration
- Définition : `return` dans un générateur termine le flux ; sa valeur éventuelle part dans `StopIteration.value`, pas dans les valeurs émises.
- Contexte : `return` sans valeur suffit à finir le flux, comme la fin du corps : le `next` suivant lève `StopIteration`. Utile pour s'arrêter sur un marqueur sans parcourir le reste de la source. Une valeur `return x` n'est pas un `yield` : elle voyage dans l'exception de fin, et `n = yield from sous()` permet de la récupérer depuis un générateur appelant.
- Usage : ✅ couper le flux sur un marqueur (`FIN`, date dépassée, page vide) · ❌ renvoyer un résultat à l'appelant : l'émettre avec `yield`, ou le compter à part.

```python
# Exemple 1 : s'arrêter sur un marqueur
def lire(lignes):
    for l in lignes:
        if l == "FIN": return
        yield l
list(lire(["A1", "FIN", "A2"]))  # → ["A1"]
```

```python
# Exemple 2 : récupérer la valeur de return
def lire(lignes):
    for l in lignes:
        if l == "FIN":
            return "stop"
        yield l

def tout(lignes):
    r = yield from lire(lignes)
    yield r   # la valeur de return

list(tout(["A1", "FIN"]))
# → ["A1", "stop"]
```

- Quiz : Avec `return 99` dans `lire`, que vaut `list(lire(["A1", "FIN"]))` ?
- [ ] `["A1", 99]`
- [x] `["A1"]`
- [ ] `[99]`
- [ ] `99`
- Réponse : `["A1"]` : `list` et `for` ignorent la valeur de `return` ; seul `yield from` (ou un `except StopIteration`) la récupère.

## 12. Pipeline : une valeur à la fois
- Id : generateurs-pipeline
- Sous-thème : composer
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : generateurs-yield-a-la-demande
- Voir aussi : generateurs-paresse-memoire
- Mots-clés : générateur, pipeline de données
- Définition : Des générateurs chaînés forment un pipeline : chaque valeur traverse toutes les étapes avant que la suivante soit lue.
- Contexte : Chaque étape prend la précédente en entrée et ne demande une valeur qu'au moment où l'étape suivante en réclame une. Rien ne s'exécute avant le consommateur final (`list`, `for`, écriture S3). Contrairement à `.map().map()` sur un tableau JS, qui produit un tableau complet à chaque étape, aucune liste intermédiaire n'existe : la mémoire reste constante.
- Usage : ✅ lecture → nettoyage → validation → écriture sur un gros flux (annonces BODACC) · ❌ étape qui a besoin de tout voir (tri, déduplication globale) : elle matérialise de toute façon.

```python
# Exemple 1 : étapes chaînées
lignes = ["A1 ", " B2"]
propres = (l.strip() for l in lignes)
basses = (l.lower() for l in propres)
list(basses)   # → ["a1", "b2"]
```

```python
# Exemple 2 : un next = une seule lecture
lus = []
def lire():
    for l in ["A1", "A2", "A3"]:
        lus.append(l)   # trace la lecture
        yield l

g = (l.lower() for l in lire())
next(g)   # → "a1"
lus       # → ["A1"]
```

- Quiz : Dans l'exemple 2, si `g` lit `[l for l in lire()]` (crochets), que vaut `lus` après `next(g)` ?
- [ ] `["A1"]`
- [ ] `[]`
- [x] `["A1", "A2", "A3"]`
- Réponse : `["A1", "A2", "A3"]` : la compréhension de liste lit toute la source dès la création de `g`, le pipeline n'est plus paresseux.

## 13. pagination : un flux d'annonces
- Id : generateurs-pagination-api
- Sous-thème : composer
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : generateurs-yield-a-la-demande
- Voir aussi : generateurs-yield-from, http-params-query-string
- Mots-clés : générateur, pagination, BODACC
- Définition : Un générateur cache la pagination d'une API : l'appelant itère sur les annonces, les pages sont demandées au fil de l'eau.
- Contexte : C'est le patron du client BODACC : la boucle `offset`/`limit` vit dans le générateur, l'appelant ne voit qu'un flux d'annonces. Une page n'est demandée que lorsque la précédente est entièrement consommée : un appelant qui s'arrête tôt (`islice`, `break`) n'appelle jamais les pages suivantes. Une page vide (ou plus courte que `limit`) termine la boucle.
- Usage : ✅ client d'API paginée (BODACC, S3 `list_objects_v2`), lecture de grosses exports · ❌ besoin du total avant de commencer : lire `total_count` d'abord.

```python
# Exemple 1 : l'appelant ne voit pas les pages
PAGES = [["A1", "A2"], ["A3"]]
def annonces():
    for page in PAGES:   # 1 appel API
        yield from page
list(annonces())  # → ["A1", "A2", "A3"]
```

```python
# Exemple 2 : offset, arrêt sur page vide
PAGES = {0: ["A1", "A2"], 2: ["A3"], 3: []}
appels = []

def annonces():
    offset = 0
    while page := PAGES[offset]:
        appels.append(offset)  # 1 appel
        yield from page
        offset += len(page)

list(annonces())   # → ["A1", "A2", "A3"]
appels             # → [0, 2]
```

- Quiz : Dans l'exemple 2, avec `appels` vide, que vaut `appels` après un seul `next(annonces())` ?
- [x] `[0]`
- [ ] `[0, 2]`
- [ ] `[]`
- [ ] `[0, 2, 3]`
- Réponse : `[0]` : le générateur s'arrête au premier `yield` ; la page 2 n'est demandée qu'au troisième `next`.

## 14. in : ça consomme
- Id : generateurs-in-consomme
- Sous-thème : itérateurs
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : generateurs-une-seule-passe
- Mots-clés : générateur, set
- Définition : `x in g` parcourt le générateur jusqu'à trouver `x` et consomme tout ce qui précède, `x` compris.
- Contexte : Sur une liste, `in` est une lecture sans effet. Sur un générateur, c'est un parcours : il appelle `next` jusqu'à trouver la valeur, et ces valeurs sont perdues. Si `x` est absent, le générateur est entièrement épuisé. Deux tests `in` successifs sur le même générateur donnent donc des résultats faux sans erreur.
- Usage : ✅ un seul test « au moins un » sur un flux qu'on jette ensuite · ❌ tests d'appartenance répétés : construire un `set` une fois.

```python
# Exemple 1 : in avance le générateur
g = (s for s in ["A1", "A2", "A3"])
"A2" in g   # → True
```

```python
# Exemple 2 : tests répétés : un set
sirens = set(s for s in ["A1", "A2"])
"A2" in sirens   # → True
"A2" in sirens   # → True  (sans perte)
```

- Quiz : Dans l'exemple 1, que vaut `list(g)` juste après `"A2" in g` ?
- [ ] `["A1", "A2", "A3"]`
- [ ] `["A2", "A3"]`
- [x] `["A3"]`
- [ ] `[]`
- Réponse : `["A3"]` : `in` a avancé le générateur jusqu'à `"A2"` inclus ; il ne reste que la suite.

## 15. Générateur : toujours vrai
- Id : generateurs-toujours-vrai
- Sous-thème : itérateurs
- Type : piège
- Niveau : 2
- Profils : data
- Mots-clés : générateur, méthode spéciale, valeur fausse
- Définition : Une liste vide est fausse en booléen, mais un générateur reste vrai même s'il ne produira rien.
- Contexte : La vérité d'un objet vient de `__bool__`, ou à défaut de `__len__`. Un générateur n'a ni l'un ni l'autre : il est donc toujours vrai, et `if g:` passe même pour un flux vide. Pour savoir s'il produit quelque chose, il faut lire une valeur avec `next(g, None)`, et ne pas la perdre ensuite.
- Usage : ✅ tester un flux avec `next(g, None) is None` · ❌ `if g:` ou `if not g:` sur un générateur : toujours vrai, bug silencieux.

```python
# Exemple 1 : liste vide contre générateur
liste = [a for a in []]
gen = (a for a in [])
bool(liste)   # → False
bool(gen)     # → True  (même vide)
```

```python
# Exemple 2 : tester « vide » sans perdre
g = (a for a in ["A1", "A2"])
premier = next(g, None)
premier is None   # → False
premier           # → "A1"  (à traiter)
list(g)           # → ["A2"]
```

- Quiz : Que vaut `bool(range(0))` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : `range` est paresseux mais connaît sa longueur (`__len__`), donc un `range` vide est faux.

## 16. Iterator[T] : annoter un générateur
- Id : generateurs-annoter-iterator
- Sous-thème : itérateurs
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : generateurs-yield-a-la-demande
- Voir aussi : listes-annotation-non-controlee
- Mots-clés : annotation de type, générateur, mypy
- Définition : Une fonction génératrice s'annote `-> Iterator[T]`, où `T` est le type de chaque valeur émise (≈ `Generator<T>` en TS).
- Contexte : Ce que l'appel renvoie est un itérateur, pas une liste : `-> list[str]` serait faux, et Python ne le vérifie pas à l'exécution (seuls mypy ou pyright le signalent). `Iterator[T]` suffit dans 95 % des cas, comme pour `fetch_day(...) -> Iterator[dict[str, Any]]`. `Generator[Y, S, R]` précise en plus le type reçu par `send` et celui du `return` ; `Iterable[T]` convient pour un paramètre qu'on se contente de parcourir.
- Usage : ✅ `-> Iterator[T]` pour une génératrice, `Iterable[T]` pour un paramètre parcouru · ❌ `-> list[T]` sur un générateur ; `Generator[…]` complet quand ni `send` ni `return` ne servent.

```python
# Exemple 1 : Iterator[T] suffit
from collections.abc import Iterator
def sirens(rows) -> Iterator[str]:
    for r in rows:
        yield r["siren"]
g = sirens([{"siren": "483609327"}])
next(g)   # → "483609327"
```

```python
# Exemple 2 : Generator[Y, S, R]
from collections.abc import Generator

def lire(lignes) -> Generator[str, None, int]:
    n = 0
    for l in lignes:
        n += 1
        yield l          # Y = str
    return n             # R = int

g = lire(["A1", "A2"])
list(g)   # → ["A1", "A2"]
```

- Quiz : Une fonction génératrice annotée `-> list[str]` : que renvoie son appel à l'exécution ?
- [ ] Une `list`
- [x] Un générateur
- [ ] `TypeError` à l'appel
- [ ] `SyntaxError` à l'import
- Réponse : Un générateur : les annotations ne sont pas vérifiées à l'exécution ; seul un vérificateur de types (mypy, pyright) signale l'erreur.

## 17. Plage de dates : bornes incluses
- Id : generateurs-plage-de-dates
- Sous-thème : yield
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : generateurs-yield-a-la-demande, dates-timedelta-ecart
- Mots-clés : générateur, timedelta, backfill
- Source : data-platform · S1-08
- Définition : Un générateur `while day <= end: yield day; day += timedelta(days=1)` produit chaque jour d'une plage, fin incluse.
- Contexte : `range` ne connaît pas les dates. Le générateur ne garde qu'un jour à la fois et s'arrête à `end` compris : du 1er au 19, 19 jours. Valider `start <= end` avant la boucle évite une plage vide silencieuse. Le nombre de jours vaut `(end - start).days + 1`, pas `.days`.
- Usage : ✅ rejeu, backfill, partitions à parcourir · ❌ `range((end - start).days)` : oublie le dernier jour.

```python
# Exemple 1 : du 1er au 19 octobre
from datetime import date, timedelta

def days(start, end):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)

j = list(days(date(2026, 10, 1),
              date(2026, 10, 19)))
len(j)           # → 19
j[-1]            # → date(2026, 10, 19)
```

- Quiz : Que vaut `(date(2026, 10, 19) - date(2026, 10, 1)).days` ?
- [ ] `19`
- [x] `18`
- [ ] `20`
- Réponse : `18` : c'est l'écart entre les deux dates ; le nombre de jours de la plage, bornes incluses, est `18 + 1`.

## 18. close : exécuter les finally
- Id : generateurs-close-finally
- Sous-thème : yield
- Type : concept
- Niveau : 3
- Profils : data, expert
- Prérequis : generateurs-yield-a-la-demande, exceptions-else-finally
- Voir aussi : context-managers-with-dans-generateur
- Mots-clés : générateur, try/finally, ramasse-miettes, CPython
- Définition : `g.close()` arrête un générateur en cours et exécute ses blocs `finally` : le moyen de libérer un fichier ou une connexion.
- Contexte : `close` lève `GeneratorExit` à l'endroit du `yield` en pause : les `finally` et les `with` du corps se déroulent normalement. CPython l'appelle aussi quand le générateur est détruit (plus aucune référence), mais sans garantie de moment hors CPython. Un `with` à l'intérieur du générateur ne ferme donc sa ressource qu'à la fin du flux, à `close`, ou à la destruction.
- Usage : ✅ générateur qui tient une ressource (fichier, session HTTP) abandonné avant la fin · ❌ compter sur le ramasse-miettes pour fermer : `close()` explicite ou `contextlib.closing`.

```python
# Exemple 1 : close exécute le finally
def lire():
    try: yield "A1"; yield "A2"
    finally: print("fermé")
g = lire()
next(g)     # → "A1"
g.close()   # affiché : fermé
```

```python
# Exemple 2 : fin normale, finally aussi
def lire():
    try:
        yield "A1"
    finally:
        print("fermé")

list(lire())   # → ["A1"]
# affiché : fermé
```

- Quiz : Dans l'exemple 1, que fait `next(g)` après `g.close()` ?
- [ ] Renvoie `"A2"`
- [ ] Renvoie `None`
- [ ] `RuntimeError`
- [x] `StopIteration`
- Réponse : `StopIteration` : un générateur fermé est épuisé pour de bon, il ne reprend pas à `"A2"`.

## 19. expression génératrice : condition lue tard
- Id : generateurs-condition-evaluee-tard
- Sous-thème : expressions
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : generateurs-expression-syntaxe
- Voir aussi : fonctions-closure-capture-tardive
- Mots-clés : générateur, évaluation paresseuse
- Définition : Dans `(x for x in it if cond)`, seul `it` est évalué à la création ; `cond` est évaluée pendant la consommation.
- Contexte : Python évalue immédiatement le premier itérable pour détecter les erreurs tôt ; tout le reste (condition, expression, `for` imbriqués) est différé au parcours. Une variable lue dans la condition prend donc sa valeur au moment du `next`, pas de la création : bug classique quand le générateur est construit dans une fonction et consommé plus tard, après réaffectation.
- Usage : ✅ savoir pourquoi un filtre « change » entre création et lecture · ❌ dépendre d'une variable modifiée entre les deux : figer avant (`frozenset`, argument de fonction).

```python
# Exemple 1 : la condition lit la valeur tard
valides = {"483609327"}
sirens = ["483609327", "552100554"]
g = (s for s in sirens if s in valides)
valides = {"552100554"}
list(g)   # → ["552100554"]
```

```python
# Exemple 2 : la liste est figée tout de suite
valides = {"483609327"}
sirens = ["483609327", "552100554"]
l = [s for s in sirens if s in valides]
valides = {"552100554"}
l   # → ["483609327"]
```

- Quiz : Dans l'exemple 1, si on réaffecte `sirens = []` au lieu de `valides`, que vaut `list(g)` ?
- [x] `["483609327"]`
- [ ] `[]`
- [ ] `["483609327", "552100554"]`
- [ ] `NameError`
- Réponse : `["483609327"]` : le premier itérable est capturé dès la création, la réaffectation de `sirens` n'y change rien.

## 20. send : envoyer une valeur au générateur
- Id : generateurs-send
- Sous-thème : yield
- Type : concept
- Niveau : 3
- Profils : expert
- Prérequis : generateurs-next-stopiteration
- Mots-clés : générateur, coroutine, yield
- Définition : `g.send(v)` reprend le générateur comme `next`, mais `v` devient la valeur de l'expression `yield` en cours ; `next(g)` équivaut à `g.send(None)`.
- Contexte : `x = yield s` fait deux choses : émettre `s` vers l'appelant, puis recevoir dans `x` ce qu'il enverra. Le générateur doit d'abord être amorcé par un `next` pour atteindre ce premier `yield`. C'est la base historique des coroutines ; en pratique, on le croise surtout dans `@contextmanager` (qui renvoie l'exception au `yield`) et dans du code ancien.
- Usage : ✅ lire du code de coroutines anciennes ou de `contextlib` ; accumulateur piloté de l'extérieur · ❌ code neuf : une classe avec une méthode, ou `async def`, bien plus lisibles.

```python
# Exemple 1 : un total piloté de l'extérieur
def total():
    s = 0
    while True:
        x = yield s      # reçoit le send
        s += x
g = total()
next(g)        # → 0   (amorçage)
g.send(10)     # → 10
g.send(5)      # → 15
```

```python
# Exemple 2 : next = send(None)
def echo():
    recu = []
    while True:
        x = yield recu
        recu.append(x)

g = echo()
next(g)
g.send("A1")
next(g)        # → ["A1", None]
```

- Quiz : Que fait `total().send(10)` sur un générateur neuf, sans `next` d'abord ?
- [ ] Renvoie `10`
- [ ] Renvoie `0`
- [x] Lève `TypeError`
- [ ] Lève `StopIteration`
- Réponse : `TypeError` (can't send non-None value to a just-started generator) : aucun `yield` n'attend encore de valeur ; il faut amorcer par `next(g)`.

## 21. StopIteration : changée en RuntimeError
- Id : generateurs-stopiteration-runtimeerror
- Sous-thème : itérateurs
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : generateurs-next-stopiteration
- Voir aussi : generateurs-return-arrete-flux
- Mots-clés : générateur, StopIteration, PEP
- Définition : Une `StopIteration` qui s'échappe du corps d'un générateur, par un `next()` interne sur un itérateur vide, devient `RuntimeError` (PEP 479).
- Contexte : Avant Python 3.7, ce `StopIteration` terminait le générateur en silence : les données restantes disparaissaient sans erreur. Désormais, Python le transforme en `RuntimeError` pour rendre le bug visible. Le réflexe : `next(it, defaut)` dans un générateur, ou un `for` qui s'arrête proprement. Pour arrêter volontairement : `return`, jamais `raise StopIteration`.
- Usage : ✅ `next(iter(lot), None)` pour lire le premier élément d'un lot peut-être vide · ❌ `next(it)` sans défaut dans un générateur ; `raise StopIteration` pour terminer : `return`.

```python
# Exemple 1 : un lot vide au milieu
def premiers(lots):
    for lot in lots:
        yield next(iter(lot))  # lot vide ?
g = premiers([["A1"], []])
next(g)        # → "A1"
next(g)        # ❌ RuntimeError
```

```python
# Exemple 2 : next avec une valeur par défaut
def premiers(lots):
    for lot in lots:
        x = next(iter(lot), None)
        if x is not None:
            yield x

list(premiers([["A1"], [], ["B2"]]))
# → ["A1", "B2"]
```

- Quiz : Hors générateur, que lève `f()` avec `def f(): return next(iter([]))` ?
- [ ] `RuntimeError`
- [x] `StopIteration`
- [ ] `IndexError`
- [ ] Rien : renvoie `None`
- Réponse : `StopIteration` : la conversion en `RuntimeError` ne concerne que le corps d'un générateur ; une fonction ordinaire la laisse remonter telle quelle.
