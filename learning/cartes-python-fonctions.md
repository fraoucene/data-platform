---
title: "Cartes · Fonctions Python"
type: cartes
langage: Python
cours: Fonctions
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Fonctions Python
Python · Fonctions : lambda, ordre supérieur, closures (format spec v3 de revision-pwa).

## 1. lambda : une seule expression
- Sous-thème : lambda
- Niveau : 1
- Définition : `lambda params: expr` crée une fonction anonyme dont le corps, une seule expression, est renvoyé implicitement (≈ `(s) => expr` en TS).
- Contexte : Pas d'équivalent au corps entre accolades des arrow functions : une lambda ne contient ni instruction, ni `return`, ni affectation `=`, ni bloc `if:` ou `for:`. Elle produit un objet fonction ordinaire, du même type qu'un `def`, qu'on passe surtout en argument (`key=`, `map`). Dès qu'il faut deux lignes, on écrit un `def`.
- Usage : ✅ petite fonction jetable passée en argument (`key=`, `map`, `defaultdict`) · ❌ logique sur plusieurs lignes, ou fonction réutilisée : `def`.

```python
# Exemple 1 : définir et appeler
pad = lambda s: s.zfill(9)
pad("12345678")   # → "012345678"
# appel immédiat, 2 paramètres
(lambda a, b: a + b)(2, 3)   # → 5
```

```python
# Exemple 2 : une fonction comme une autre
pad = lambda s: s.zfill(9)
def pad2(s):
    return s.zfill(9)

type(pad) is type(pad2)   # → True
pad("7") == pad2("7")     # → True
```

- Quiz : Avec `f = lambda s: print(s)`, que fait `f("A1")` ?
- [ ] `SyntaxError` : `print` est une instruction
- [x] Affiche `A1` et renvoie `None`
- [ ] Renvoie `"A1"` sans rien afficher
- [ ] Affiche `A1` et renvoie `"A1"`
- Réponse : Affiche `A1` et renvoie `None` : un appel de fonction est une expression, la lambda renvoie ce que renvoie `print`, soit `None`.

## 2. lambda : condition ternaire
- Sous-thème : lambda
- Niveau : 1
- Définition : Une lambda choisit entre deux valeurs avec `x if cond else y`, seule condition possible dans une expression (≈ `c ? x : y`).
- Contexte : L'instruction `if:` est interdite dans une lambda, mais l'expression conditionnelle est permise. L'ordre diffère de TS : la valeur « vraie » d'abord, la condition au milieu, l'alternative à la fin. Les ternaires se chaînent (`a if c1 else b if c2 else c`), mais au-delà de deux cas un dict de correspondance ou un `def` se lit mieux.
- Usage : ✅ choisir entre deux valeurs dans une clé de tri ou un `map` · ❌ trois cas ou plus : dict de correspondance (`LIBELLES.get(f, "autre")`) ou `def`.

```python
# Exemple 1 : deux cas
libelle = lambda f: (
    "radiation" if f == "R" else "autre")
libelle("R")   # → "radiation"
libelle("A")   # → "autre"
```

```python
# Exemple 2 : trois cas, ternaires chaînés
libelle = lambda f: (
    "radiation" if f == "R"
    else "création" if f == "C"
    else "autre")
libelle("C")   # → "création"
libelle("X")   # → "autre"
```

- Quiz : Que fait `lambda a: "radiation" if a["famille"] == "R"`, sans `else` ?
- [ ] Renvoie `None` si la famille n'est pas `R`
- [ ] Renvoie `False` si la famille n'est pas `R`
- [x] `SyntaxError` à la définition
- [ ] `TypeError` à l'appel
- Réponse : `SyntaxError` (expected 'else' after 'if' expression) : une expression doit toujours produire une valeur, le `else` est obligatoire.

## 3. sorted : key=lambda
- Sous-thème : ordre supérieur
- Niveau : 1
- Définition : `sorted(it, key=lambda x: …)` trie selon la valeur que la lambda renvoie pour chaque élément.
- Contexte : Contrairement à `Array.sort` en JS, on ne passe pas de comparateur `(a, b) => a - b` : la clé reçoit un seul élément et renvoie la valeur à comparer. Un tuple trie sur plusieurs critères, dans l'ordre ; `-` inverse un critère numérique. `sorted` renvoie une nouvelle liste ; `liste.sort(key=…)` trie sur place et renvoie `None`. Le tri est stable.
- Usage : ✅ trier des annonces par date, capital, puis SIREN · ❌ clé qui lit juste un champ : `operator.itemgetter`, plus court.

```python
# Exemple 1 : trier sur un champ
a = [("A1", 500), ("B2", 9000),
     ("C3", 100)]
sorted(a, key=lambda x: x[1])
# → [("C3", 100), ("A1", 500), ("B2", 9000)]
```

```python
# Exemple 2 : plusieurs critères, - inverse
annonces = [
    {"siren": "552100554", "capital": 500},
    {"siren": "483609327", "capital": 9000},
    {"siren": "830024215", "capital": 500},
]
tri = sorted(annonces, key=lambda a: (
    -a["capital"], a["siren"]))
[a["siren"] for a in tri]
# → ["483609327", "552100554", "830024215"]
```

- Quiz : Avec `date = "2026-10-20"`, que fait `key=lambda a: (-a["date"], a["siren"])` ?
- [ ] Trie par date décroissante
- [ ] Trie par date croissante
- [ ] `ValueError`
- [x] `TypeError`
- Réponse : `TypeError` (bad operand type for unary -: 'str') : `-` ne marche que sur des nombres ; utiliser `reverse=True` ou deux tris successifs.

## 4. map : appliquer à chaque élément
- Sous-thème : ordre supérieur
- Niveau : 1
- Définition : `map(lambda, it)` applique la fonction à chaque élément et renvoie un itérateur paresseux (≈ `arr.map`, mais paresseux).
- Contexte : En Python 3, `map` ne calcule rien à l'appel : il renvoie un objet `map`, évalué au parcours, à matérialiser avec `list(...)`. La compréhension `[f(x) for x in it]` est souvent préférée : plus lisible, sans lambda. `map` accepte plusieurs itérables (`map(f, a, b)`), parcourus en parallèle jusqu'au plus court.
- Usage : ✅ appliquer une fonction existante (`map(str.strip, lignes)`) · ❌ `map(lambda …)` qui se lit mal : compréhension de liste.

```python
# Exemple 1 : normaliser des SIREN
sirens = ["12345678", "483609327"]
pads = map(lambda s: s.zfill(9), sirens)
list(pads)
# → ["012345678", "483609327"]
```

```python
# Exemple 2 : deux itérables en parallèle
sirens = ["483609327", "552100554"]
dates = ["2026-10-20", "2026-10-22"]
cles = map(lambda s, d: f"{s}@{d}",
           sirens, dates)
next(cles)   # → "483609327@2026-10-20"
```

- Quiz : Dans l'exemple 1, que vaut un second `list(pads)` ?
- [x] `[]`
- [ ] `["012345678", "483609327"]`
- [ ] `StopIteration`
- [ ] `TypeError`
- Réponse : `[]` : un `map` est un itérateur, il s'épuise au premier parcours ; une liste se relit autant de fois que voulu.

## 5. filter : garder ce qui est vrai
- Sous-thème : ordre supérieur
- Niveau : 1
- Définition : `filter(lambda, it)` garde les éléments pour lesquels la fonction renvoie une valeur vraie (≈ `arr.filter`, paresseux).
- Contexte : Comme `map`, `filter` renvoie un itérateur paresseux, à matérialiser avec `list`. La fonction n'a pas à renvoyer un booléen : toute valeur vraie (chaîne non vide, nombre non nul) garde l'élément. La compréhension `[x for x in it if cond]` fait la même chose et se lit souvent mieux, surtout combinée à une transformation.
- Usage : ✅ filtrer avec une fonction existante (`filter(str.isdigit, codes)`) · ❌ filtre et transformation ensemble : compréhension `[f(x) for x in it if cond]`.

```python
# Exemple 1 : garder les gros capitaux
capitaux = [500, 9000, 0, 1200]
gros = filter(lambda c: c > 1000,
              capitaux)
list(gros)   # → [9000, 1200]
```

```python
# Exemple 2 : la compréhension équivalente
capitaux = [500, 9000, 0, 1200]
[c for c in capitaux if c > 1000]
# → [9000, 1200]
```

- Quiz : Que vaut `list(filter(None, ["A1", "", None, "A2"]))` ?
- [ ] `TypeError`
- [ ] `["A1", "", None, "A2"]`
- [x] `["A1", "A2"]`
- [ ] `[]`
- Réponse : `["A1", "A2"]` : avec `None` à la place de la fonction, `filter` garde les éléments vrais, comme `.filter(Boolean)`.

## 6. lambda : renvoyer un tuple
- Sous-thème : lambda
- Niveau : 2
- Définition : Pour renvoyer plusieurs valeurs, une lambda entoure son tuple de parenthèses : elles délimitent le corps.
- Contexte : En TS, `(a) => [a.siren, a.date]` renvoie un tableau ; en Python, la lambda renvoie un tuple, construit par la virgule. Le corps d'une lambda s'arrête à la première virgule de premier niveau : seules des parenthèses autour du tuple le gardent entier. C'est la forme classique d'une clé de tri ou de regroupement composée.
- Usage : ✅ clé composée pour `sorted`, `max`, `groupby` · ❌ beaucoup de champs : `itemgetter("a", "b")`, plus court.

```python
# Exemple 1 : clé composée
cle = lambda a: (a["siren"], a["date"])
cle({"siren": "483609327",
     "date": "2026-10-20"})
# → ("483609327", "2026-10-20")
```

```python
# Exemple 2 : déballer le tuple renvoyé
cle = lambda a: (a["siren"], a["date"])
s, d = cle({"siren": "483609327",
            "date": "2026-10-20"})
d   # → "2026-10-20"
```

- Quiz : Dans un module neuf, que fait `cle = lambda a: a["siren"], a["date"]` ?
- [ ] Crée la même lambda que l'exemple 1
- [ ] Crée une lambda qui renvoie seulement le SIREN
- [ ] `SyntaxError`
- [x] `NameError`
- Réponse : `NameError` (name 'a' is not defined) : Python lit `(lambda a: a["siren"]), a["date"]` et évalue `a["date"]` tout de suite.

## 7. lambda : arguments par défaut
- Sous-thème : lambda
- Niveau : 2
- Définition : Une lambda accepte valeurs par défaut, arguments nommés et `*args`, comme un `def`.
- Contexte : La signature d'une lambda a toutes les possibilités d'un `def` : défauts, arguments nommés, `*args`, `**kwargs`, paramètres « keyword-only ». Les valeurs par défaut sont évaluées une seule fois, quand la lambda est créée, pas à chaque appel comme en TS : c'est sans effet pour un nombre ou une chaîne, mais à surveiller pour un objet modifiable.
- Usage : ✅ taux ou seuil par défaut dans un petit calcul (`ttc`, `seuil=1000`) · ❌ défaut modifiable (`[]`, `{}`) : `None` puis création dans un `def`.

```python
# Exemple 1 : un défaut et un nommé
ttc = lambda ht, t=0.2: round(
    ht * (1 + t), 2)
ttc(100)          # → 120.0
ttc(100, 0.055)   # → 105.5
ttc(ht=50)        # → 60.0
```

```python
# Exemple 2 : *args comme dans un def
total = lambda *caps: sum(caps)
total(500, 9000, 1200)   # → 10700
total()                  # → 0
```

- Quiz : Avec `f = lambda x, acc=[]: acc.append(x) or acc`, que vaut `f("B")` après `f("A")` ?
- [ ] `["B"]`
- [x] `["A", "B"]`
- [ ] `None`
- [ ] `["B", "A"]`
- Réponse : `["A", "B"]` : la liste par défaut est créée une seule fois et partagée entre appels, contrairement aux défauts TS.

## 8. max : l'élément, pas la clé
- Sous-thème : ordre supérieur
- Niveau : 2
- Définition : `max(it, key=lambda)` renvoie l'élément entier dont la clé est la plus grande, pas la valeur de la clé.
- Contexte : La lambda sert seulement à comparer : `max` renvoie l'annonce, pas la date. Même règle pour `min` et `sorted`. Les dates ISO (`2026-10-20`) se comparent correctement comme chaînes, sans conversion. En cas d'égalité, `max` garde le premier élément rencontré. Sur un dict, `max` parcourt les clés : la lambda reçoit une clé.
- Usage : ✅ dernière annonce d'une liste, entreprise au plus gros capital · ❌ besoin de la valeur seule : `max(a["date"] for a in annonces)`.

```python
# Exemple 1 : l'annonce la plus récente
annonces = [
    {"siren": "483609327", "date": "2026-10-20"},
    {"siren": "552100554", "date": "2026-10-22"},
]
derniere = max(annonces, key=lambda a: a["date"])
derniere["siren"]   # → "552100554"
```

```python
# Exemple 2 : sur un dict, la clé max
caps = {"483609327": 9000,
        "552100554": 500}
max(caps, key=lambda s: caps[s])
# → "483609327"
max(caps.values())   # → 9000
```

- Quiz : Que fait `max([], key=lambda a: a["date"])` ?
- [ ] Renvoie `None`
- [ ] Renvoie `[]`
- [x] `ValueError`
- [ ] `KeyError`
- Réponse : `ValueError` (max() iterable argument is empty) : passer `default=None` pour une journée sans annonce.

## 9. itemgetter : la lambda toute faite
- Sous-thème : ordre supérieur
- Niveau : 2
- Définition : `operator.itemgetter("cle")` remplace `lambda a: a["cle"]`, plus court et un peu plus rapide.
- Contexte : `itemgetter(k)` renvoie une fonction qui fait `obj[k]` : elle marche sur un dict (clé) comme sur un tuple ou une liste (index). Son cousin `attrgetter("date")` lit un attribut (objets, modèles pydantic). Écrit en C, il évite l'appel d'une fonction Python à chaque élément : léger gain sur de gros tris. Une clé absente lève `KeyError`, comme l'accès direct.
- Usage : ✅ `key=` de `sorted`, `max`, `groupby` qui lit simplement un champ · ❌ clé calculée (`len`, condition, conversion) : `lambda`.

```python
# Exemple 1 : trier par date
from operator import itemgetter
annonces = [
    {"siren": "552100554", "date": "2026-10-22"},
    {"siren": "483609327", "date": "2026-10-20"}]
tri = sorted(annonces, key=itemgetter("date"))
tri[0]["siren"]   # → "483609327"
```

```python
# Exemple 2 : extraire un champ de chaque annonce
from operator import itemgetter
annonces = [{"siren": "552100554"},
            {"siren": "483609327"}]
list(map(itemgetter("siren"), annonces))
# → ["552100554", "483609327"]
```

- Quiz : Avec `a = {"siren": "552100554", "date": "2026-10-22"}`, que vaut `itemgetter("siren", "date")(a)` ?
- [x] `("552100554", "2026-10-22")`
- [ ] `["552100554", "2026-10-22"]`
- [ ] `{"siren": "552100554", "date": "2026-10-22"}`
- [ ] `KeyError`
- Réponse : `("552100554", "2026-10-22")` : avec plusieurs clés, `itemgetter` renvoie un tuple, prêt pour un tri multi-critères.

## 10. defaultdict : une lambda comme fabrique
- Sous-thème : ordre supérieur
- Niveau : 2
- Définition : `defaultdict(lambda: valeur)` appelle la lambda pour fabriquer la valeur d'une clé absente ; elle ne prend aucun argument.
- Contexte : `defaultdict` attend une fonction sans argument, appelée à chaque clé manquante : `int`, `list`, ou une lambda pour toute autre valeur (une chaîne, un dict pré-rempli). La lambda ne reçoit pas la clé : impossible d'en déduire la valeur. Comme elle est rappelée à chaque fois, chaque clé reçoit un objet neuf, contrairement à `dict.fromkeys(cles, [])`.
- Usage : ✅ valeur par défaut composée (`{"nb": 0}`), libellé « inconnu » · ❌ valeur qui dépend de la clé : sous-classe de `dict` avec `__missing__`.

```python
# Exemple 1 : un libellé par défaut
from collections import defaultdict
tribunal = defaultdict(lambda: "inconnu")
tribunal["7501"] = "Paris"
tribunal["7501"]   # → "Paris"
tribunal["6901"]   # → "inconnu"
```

```python
# Exemple 2 : une valeur composée neuve
from collections import defaultdict
stats = defaultdict(lambda: {"nb": 0})
stats["Paris"]["nb"] += 1
stats["Paris"]["nb"] += 1
stats["Lyon"]["nb"] += 1
stats["Paris"]   # → {"nb": 2}
```

- Quiz : Dans l'exemple 1, que vaut `len(tribunal)` juste après ces deux lectures ?
- [ ] `1`
- [x] `2`
- [ ] `0`
- Réponse : `2` : lire une clé absente l'insère avec la valeur fabriquée ; utiliser `.get()` pour lire sans écrire.

## 11. Capture : la variable, pas la valeur
- Sous-thème : closures
- Niveau : 3
- Définition : Une lambda lit les variables extérieures au moment de l'appel, pas à sa création (même règle que les closures JS).
- Contexte : La lambda garde une référence à la variable, pas une copie de sa valeur : si la variable change entre création et appel, la lambda voit la nouvelle valeur. Le piège classique est la boucle qui crée des fonctions. En JS, `let` dans un `for` crée une variable par tour ; en Python, la variable de boucle est unique, partagée par tous les tours.
- Usage : ✅ lambda qui doit suivre un réglage modifiable (seuil global) · ❌ fonctions créées dans une boucle : figer la valeur avec `i=i` ou une fabrique.

```python
# Exemple 1 : le seuil est lu à l'appel
seuil = 1000
gros = lambda a: a["capital"] >= seuil
seuil = 10000
gros({"capital": 5000})   # → False
```

```python
# Exemple 2 : une fabrique fige la valeur
def plus_grand_que(seuil):
    return lambda c: c > seuil

gros = plus_grand_que(1000)
gros(5000)   # → True
```

- Quiz : Que vaut `[f() for f in [lambda: i for i in range(3)]]` ?
- [ ] `[0, 1, 2]`
- [ ] `NameError`
- [ ] `[3, 3, 3]`
- [x] `[2, 2, 2]`
- Réponse : `[2, 2, 2]` : les trois lambdas lisent le même `i`, qui vaut 2 à la fin de la boucle.

## 12. Figer la valeur : i=i
- Sous-thème : closures
- Niveau : 3
- Définition : Un argument par défaut `i=i` copie la valeur à la création de la lambda et contourne la capture tardive.
- Contexte : Les valeurs par défaut sont évaluées à la création de la lambda : `i=i` range donc la valeur courante de `i` dans un paramètre local. C'est l'idiome court, mais `i` reste un vrai paramètre, visible dans la signature. `functools.partial(f, valeur)` fige un argument sans l'exposer, et une fonction fabrique (`def make(i): return lambda: i`) aussi.
- Usage : ✅ callbacks créés dans une boucle (un par tribunal, par jour) · ❌ API publique : `functools.partial`, pour ne pas exposer un paramètre en trop.

```python
# Exemple 1 : une valeur par lambda
fs = [lambda i=i: i for i in range(3)]
[f() for f in fs]   # → [0, 1, 2]
```

```python
# Exemple 2 : partial, sans paramètre exposé
from functools import partial
def depasse(seuil, c):
    return c > seuil

tests = [partial(depasse, s)
         for s in (1000, 5000)]
[t(3000) for t in tests]
# → [True, False]
```

- Quiz : Dans l'exemple 1, que vaut `fs[0](9)` ?
- [x] `9`
- [ ] `0`
- [ ] `TypeError`
- [ ] `[0, 9]`
- Réponse : `9` : `i` reste un vrai paramètre, l'appelant peut l'écraser ; `functools.partial` fige sans exposer ce paramètre.

## 13. lambda nommée ou def ?
- Sous-thème : lambda
- Niveau : 3
- Définition : Une lambda n'a pas de nom propre (`<lambda>`) ; dès qu'on l'affecte à une variable, `def` est préférable.
- Contexte : `pad = lambda s: …` donne le nom de variable `pad`, mais l'objet fonction s'appelle toujours `<lambda>` : c'est ce nom qui apparaît dans les traces d'erreur et les profils. Un `def` a un vrai nom, une docstring, des annotations de type, et se teste mieux. Les linters (ruff, flake8) le signalent avec la règle E731.
- Usage : ✅ `lambda` en argument jetable (`key=`, `map`, `defaultdict`) · ❌ `nom = lambda …` : écrire `def nom(…)`.

```python
# Exemple 1 : le nom de l'objet fonction
pad = lambda s: s.zfill(9)
pad.__name__    # → "<lambda>"
def pad2(s):
    return s.zfill(9)
pad2.__name__   # → "pad2"
```

```python
# Exemple 2 : l'erreur pointe vers <lambda>
pad = lambda s: s.zfill(9)
pad(483609327)   # ❌ AttributeError
# trace : File …, in <lambda>
```

- Quiz : Selon PEP 8, `pad = lambda s: s.zfill(9)` ou `def pad(s): return s.zfill(9)` ?
- [ ] `lambda` : plus court, donc préférable
- [x] `def` : la lambda nommée est déconseillée
- [ ] Les deux : PEP 8 ne tranche pas
- Réponse : `def` : PEP 8 déconseille d'affecter une lambda à un nom ; `lambda` reste pour un argument jetable comme `key=`.
