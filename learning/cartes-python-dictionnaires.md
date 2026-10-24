---
title: "Cartes · Dictionnaires Python"
type: cartes
langage: Python
cours: Dictionnaires
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Dictionnaires Python
Python · Dictionnaires : construire, lire, modifier, outils, parcourir (format spec v3 de revision-pwa).

## 1. dict : lire sans planter
- Sous-thème : lire
- Niveau : 1
- Définition : `dict` associe des clés uniques à des valeurs ; `d[k]` lit une clé obligatoire, `d.get(k, défaut)` une clé facultative (≈ objet ou `Map`).
- Contexte : Contrairement à JS, lire une clé absente avec `d[k]` ne renvoie pas `undefined` : ça lève `KeyError`. `get` renvoie `None`, ou la valeur par défaut donnée. `k in d` teste la présence d'une **clé**, pas d'une valeur. Les clés sont souvent des chaînes, mais tout objet hashable convient (nombre, tuple).
- Usage : ✅ `d[k]` pour un champ obligatoire (échoue tôt), `get` pour un champ facultatif d'une donnée externe (JSON, annonce BODACC) · ❌ `get` partout : masque les vraies erreurs de données.

```python
# Exemple 1 : clé obligatoire ou facultative
annonce = {"siren": "483609327",
           "ville": "Lyon"}
annonce["siren"]           # → "483609327"
annonce.get("capital")     # → None
annonce.get("capital", 0)  # → 0
annonce["capital"]         # ❌ KeyError
```

```python
# Exemple 2 : tester la présence
annonce = {"siren": "483609327"}
"siren" in annonce        # → True
"483609327" in annonce    # → False  (clés seulement)
"483609327" in annonce.values()  # → True
```

- Quiz : Avec `annonce = {"tribunal": None}`, que vaut `annonce.get("tribunal", "?")` ?
- [ ] `"?"`
- [x] `None`
- [ ] `KeyError`
- [ ] `""`
- Réponse : `None` : la clé existe (sa valeur est `None`), donc la valeur par défaut n'est pas utilisée ; elle ne sert que si la clé manque.

## 2. dict : pas d'accès par point
- Sous-thème : lire
- Niveau : 1
- Définition : Les clés d'un dict se lisent avec `d["k"]`, jamais `d.k` : un dict n'est pas un objet JS, ses clés ne sont pas des attributs.
- Contexte : `d.siren` lève `AttributeError` : le point accède aux attributs et aux méthodes (`d.get`, `d.items`), pas aux clés. Les clés gardent leur type : `"1"` et `1` sont deux clés différentes, alors qu'en JS toute clé d'objet devient une chaîne. Pour un accès par point et l'autocomplétion, une `dataclass` ou un modèle pydantic.
- Usage : ✅ `d["siren"]` sur des données JSON brutes · ❌ dict passé partout dans le code métier : le convertir en `dataclass` ou en modèle pydantic.

```python
# Exemple 1 : crochets, pas point
a = {"siren": "483609327"}
a["siren"]     # → "483609327"
a.siren        # ❌ AttributeError
```

```python
# Exemple 2 : 1 et "1" sont distincts
d = {1: "int", "1": "str"}
len(d)         # → 2
d["1"]         # → "str"
d[1]           # → "int"
```

- Quiz : Que renvoie `{"items": 3}.items` ?
- [ ] `3`
- [x] La méthode `items` du dict
- [ ] `KeyError`
- [ ] `AttributeError`
- Réponse : la méthode `items` : le point lit toujours un attribut, jamais une clé ; la clé `"items"` se lit avec `d["items"]`.

## 3. dict : créer
- Sous-thème : construire
- Niveau : 1
- Définition : Un dict se crée par littéral `{"k": v}`, par `dict(k=v)`, depuis des paires avec `dict(paires)`, ou avec `dict.fromkeys(cles)`.
- Contexte : Dans un littéral, la clé est une expression : `{"siren": s}` utilise la chaîne, `{siren: s}` la valeur de la variable `siren` ; pas de raccourci `{ siren }` comme en TS. `dict(ville="Lyon")` est pratique mais limité aux clés qui sont des noms Python valides. `dict(zip(cles, valeurs))` associe deux listes.
- Usage : ✅ littéral pour un enregistrement, `dict(paires)` pour convertir, `fromkeys` pour initialiser des clés · ❌ `dict(k=v)` avec des clés qui ne sont pas des identifiants (`"code-postal"`).

```python
# Exemple 1 : quatre écritures
dict(siren="483609327", nb=2)
# → {"siren": "483609327", "nb": 2}
dict([("A1", "Lyon"), ("B2", "Nice")])
# → {"A1": "Lyon", "B2": "Nice"}
dict.fromkeys(["A1", "B2"], 0)
# → {"A1": 0, "B2": 0}
```

```python
# Exemple 2 : la clé est une expression
siren = "483609327"
d = {siren: 1}
list(d)        # → ["483609327"]
{"siren": siren}["siren"]
# → "483609327"
```

- Quiz : Que vaut `dict([("a", 1), ("a", 2)])` ?
- [ ] `{"a": 1}`
- [ ] `ValueError`
- [x] `{"a": 2}`
- [ ] `{"a": [1, 2]}`
- Réponse : `{"a": 2}` : chaque paire est affectée dans l'ordre, la seconde écrase la première ; aucune erreur sur une clé en double.

## 4. dict : modifier et fusionner
- Sous-thème : modifier
- Niveau : 1
- Définition : `d[k] = v` ajoute ou remplace, `|` fusionne deux dicts, `pop` et `del` retirent une clé.
- Contexte : `d[k] = v` crée la clé si elle manque, sinon remplace la valeur. `d1 | d2` (Python 3.9+) renvoie un nouveau dict où `d2` gagne en cas de conflit (≈ `{...d1, ...d2}`) ; `d1 |= d2` et `update` modifient `d1` sur place. `setdefault(k, v)` n'écrit que si la clé manque, et renvoie la valeur en place.
- Usage : ✅ construire un enregistrement champ par champ, appliquer des valeurs par défaut avec `|` · ❌ compter ou grouper : `Counter`, `defaultdict`.

```python
# Exemple 1 : ajouter, remplacer, retirer
a = {"siren": "483609327"}
a["ville"] = "Lyon"    # ajoute
a["ville"] = "Paris"   # remplace
del a["ville"]
a                      # → {"siren": "483609327"}
a.pop("siren")         # → "483609327"
a                      # → {}
```

```python
# Exemple 2 : valeurs par défaut avec |
defaut = {"pays": "FR", "actif": True}
lu = {"actif": False, "ville": "Lyon"}
complet = defaut | lu  # lu gagne
complet["actif"]       # → False
complet["pays"]        # → "FR"
defaut["actif"]        # → True  (intact)
```

- Quiz : Que valent `{}.pop("x")` et `{}.pop("x", None)` ?
- [x] `KeyError`, puis `None`
- [ ] `None` et `None`
- [ ] `KeyError` et `KeyError`
- [ ] `undefined`, puis `None`
- Réponse : `KeyError` pour le premier, `None` pour le second : comme `get`, `pop` accepte une valeur par défaut qui évite l'erreur.

## 5. dict : parcourir
- Sous-thème : parcourir
- Niveau : 1
- Définition : `items()` donne les paires `(clé, valeur)`, `keys()` et `values()` l'un ou l'autre ; l'ordre d'insertion est conservé.
- Contexte : Boucler sur un dict parcourt ses clés. `items()` évite de relire `d[k]` à chaque tour (≈ `Object.entries`). Depuis Python 3.7, l'ordre d'insertion est garanti. Ces méthodes renvoient des **vues**, pas des copies : elles reflètent les changements ultérieurs du dict.
- Usage : ✅ `items()` dès qu'on utilise clé et valeur, `values()` pour agréger (`sum`, `max`) · ❌ `for k in d: d[k]` : relit chaque valeur pour rien.

```python
# Exemple 1 : clés et valeurs
capitaux = {"A1": 1000, "B2": 5000}
for code, capital in capitaux.items():
    print(code, capital)
# affiché : A1 1000
# affiché : B2 5000
list(capitaux)          # → ["A1", "B2"]
sum(capitaux.values())  # → 6000
```

```python
# Exemple 2 : une vue suit le dict
d = {"a": 1}
cles = d.keys()
d["b"] = 2
list(cles)              # → ["a", "b"]
```

- Quiz : Avec `d = {"a": 1}`, que fait `for k in d: d[k + "_bis"] = 0` ?
- [ ] Ajoute `"a_bis"` et s'arrête
- [ ] Boucle à l'infini
- [x] `RuntimeError`
- [ ] `KeyError`
- Réponse : `RuntimeError` (dictionary changed size during iteration) : on n'ajoute pas de clé pendant le parcours ; boucler sur `list(d)`.

## 6. dict : comparer
- Sous-thème : lire
- Niveau : 1
- Définition : `==` compare deux dicts par leurs paires clé-valeur, sans tenir compte de l'ordre d'insertion des clés.
- Contexte : En JS, deux objets ne sont égaux que s'ils sont le même objet ; en Python, `==` compare les contenus, récursivement. L'ordre des clés est conservé par le dict mais ignoré par `==`. Pour vérifier qu'un dict en contient un autre : `petit.items() <= grand.items()`. `is` teste l'identité.
- Usage : ✅ assert dans les tests (`assert parse(ligne) == attendu`), détecter qu'un enregistrement a changé · ❌ comparer des dicts sérialisés en chaîne : l'ordre des clés change la chaîne.

```python
# Exemple 1 : l'ordre ne compte pas
a = {"siren": "48", "nb": 2}
b = {"nb": 2, "siren": "48"}
a == b               # → True
list(a) == list(b)   # → False
```

```python
# Exemple 2 : inclusion de paires
attendu = {"siren": "48"}
lu = {"siren": "48", "ville": "Lyon"}
attendu.items() <= lu.items()  # → True
lu == attendu                  # → False
```

- Quiz : Que vaut `{"nb": 1} == {"nb": 1.0}` ?
- [x] `True`
- [ ] `False`
- [ ] `TypeError`
- Réponse : `True` : les valeurs se comparent avec `==`, et `1 == 1.0` ; le type différent ne compte pas.

## 7. get imbriqué : lire en profondeur
- Sous-thème : lire
- Niveau : 2
- Définition : `d.get("a", {}).get("b")` lit une clé imbriquée sans `KeyError` quand un niveau manque (≈ `d.a?.b` en TS).
- Contexte : Python n'a pas d'opérateur `?.`. Le chaînage de `get` avec `{}` par défaut fonctionne tant que le niveau intermédiaire est absent ou est un dict. En JSON, un niveau vaut souvent `null`, donc `None` : il faut alors `(d.get("a") or {}).get("b")`. Au-delà de deux niveaux, une petite fonction ou un modèle pydantic.
- Usage : ✅ champs facultatifs d'une annonce BODACC (`jugement`, `depot`) · ❌ niveaux obligatoires : `d["a"]["b"]`, pour échouer tôt.

```python
# Exemple 1 : un niveau manque
a = {"siren": "48"}
a.get("jugement", {}).get("nature")
# → None
a["jugement"]["nature"]   # ❌ KeyError
```

```python
# Exemple 2 : un niveau à None
a = {"jugement": None}
(a.get("jugement") or {}).get("nature")
# → None
```

- Quiz : Avec `a = {"jugement": None}`, que fait `a.get("jugement", {}).get("nature")` ?
- [ ] Renvoie `None`
- [ ] Renvoie `{}`
- [ ] `KeyError`
- [x] `AttributeError`
- Réponse : `AttributeError` : la clé existe, donc `get` renvoie `None` et pas `{}` ; `None.get` n'existe pas.

## 8. get : or ou valeur par défaut
- Sous-thème : lire
- Niveau : 2
- Définition : `d.get(k, défaut)` ne remplace qu'une clé absente ; `d.get(k) or défaut` remplace aussi toute valeur fausse : `None`, `""`, `0`.
- Contexte : Le choix dépend de la donnée. Pour un libellé, `or` traite pareil absent, `None` et chaîne vide, ce qu'on veut souvent avec un JSON externe. Pour un nombre ou un booléen, `or` transforme une vraie valeur `0` ou `False` en défaut. Même piège qu'avec `||` en JS, et Python n'a pas de `??` : on teste `is None`.
- Usage : ✅ `or` pour des chaînes affichées, `is None` pour des nombres et des booléens · ❌ `or` sur un champ où `0` ou `False` sont des valeurs valides (capital, actif).

```python
# Exemple 1 : None et chaîne vide
a = {"ville": "", "cp": None}
a.get("ville", "?")       # → ""
a.get("ville") or "?"     # → "?"
a.get("cp") or "?"        # → "?"
```

```python
# Exemple 2 : l'équivalent de ??
a = {"capital": 0}
v = a.get("capital")
v if v is not None else -1   # → 0
```

- Quiz : Que vaut `{"nb": 0}.get("nb") or 5` ?
- [ ] `0`
- [x] `5`
- [ ] `None`
- [ ] `KeyError`
- Réponse : `5` : `get` renvoie bien `0`, mais `0` est faux, donc `or` passe au défaut ; un comptage nul est perdu.

## 9. KeyError : tester ou capturer
- Sous-thème : lire
- Niveau : 2
- Définition : Une clé obligatoire se lit avec `d[k]` dans un `try/except KeyError`, ou après un test `k in d` ; Python préfère souvent essayer d'abord.
- Contexte : Le style Python « EAFP » (plus facile de demander pardon que la permission) tente l'accès et capture l'erreur, au lieu de tout tester avant. Le message d'une `KeyError` n'est pas une phrase : c'est la clé. `e.args[0]` donne la clé brute, de quoi écrire une erreur métier claire. `raise … from None` masque la `KeyError` d'origine dans la trace.
- Usage : ✅ transformer un champ manquant en erreur métier explicite (« A1 sans siren ») · ❌ `except Exception` large, qui avale aussi les vraies erreurs.

```python
# Exemple 1 : essayer, puis capturer
a = {"id": "A1"}
try:
    s = a["siren"]
except KeyError as e:
    s, cle = None, e.args[0]
s        # → None
cle      # → "siren"
```

```python
# Exemple 2 : erreur métier explicite
def siren(a):
    try:
        return a["siren"]
    except KeyError:
        raise ValueError(
            f"{a['id']} sans siren") from None

siren({"id": "A1"})   # ❌ ValueError
```

- Quiz : Avec `e` capturée sur `{}["capital"]`, que vaut `str(e)` ?
- [ ] `"capital"`
- [x] `"'capital'"`
- [ ] `"KeyError: capital"`
- [ ] `""`
- Réponse : `"'capital'"` : `str` d'une `KeyError` affiche la clé avec ses guillemets (son `repr`) ; utiliser `e.args[0]` pour la clé brute.

## 10. dict : filtrer et inverser
- Sous-thème : construire
- Niveau : 2
- Définition : Une compréhension `{k: v for k, v in d.items() if …}` filtre ou transforme un dict en un nouveau dict.
- Contexte : On parcourt `items()` pour avoir clé et valeur, on filtre avec `if`, on transforme l'une ou l'autre (≈ `Object.fromEntries(Object.entries(d).filter(…))`). Inverser un dict (`{v: k …}`) perd des entrées quand plusieurs clés ont la même valeur. Retirer les `None` d'un enregistrement avant de l'écrire est un usage typique.
- Usage : ✅ retirer les champs vides, renommer des clés, inverser une table de codes · ❌ modifier le dict pendant qu'on le parcourt : construire le nouveau à côté.

```python
# Exemple 1 : retirer les None
a = {"siren": "48", "ville": None,
     "nb": 0}
{k: v for k, v in a.items()
 if v is not None}
# → {"siren": "48", "nb": 0}
```

```python
# Exemple 2 : renommer, inverser
a = {"siren": "48", "ville": "Lyon"}
noms = {"siren": "id", "ville": "city"}
{noms[k]: v for k, v in a.items()}
# → {"id": "48", "city": "Lyon"}
{v: k for k, v in noms.items()}["id"]
# → "siren"
```

- Quiz : Que vaut `{v: k for k, v in {"A1": "Lyon", "B2": "Lyon"}.items()}` ?
- [ ] `{"Lyon": ["A1", "B2"]}`
- [ ] `{"Lyon": "A1"}`
- [x] `{"Lyon": "B2"}`
- [ ] `ValueError`
- Réponse : `{"Lyon": "B2"}` : les deux paires visent la clé `"Lyon"`, la dernière écrase la première ; pour grouper, `defaultdict(list)`.

## 11. ** : déballer un dict
- Sous-thème : construire
- Niveau : 2
- Définition : `{**a, **b}` fusionne des dicts dans un nouveau, et `f(**d)` passe chaque clé comme argument nommé (≈ spread `...` en TS).
- Contexte : Comme avec `|`, la dernière source gagne sur une clé commune ; `**` permet en plus d'ajouter des clés au milieu : `{**a, "nb": 0}`. Dans un appel, chaque clé doit correspondre à un paramètre de la fonction. C'est ainsi qu'on construit une `dataclass` depuis un dict JSON : `Annonce(**d)`.
- Usage : ✅ surcharger quelques champs d'une copie, construire un objet depuis un dict déjà validé · ❌ dict JSON brut aux champs inconnus vers `f(**d)` : filtrer d'abord, ou pydantic.

```python
# Exemple 1 : copie avec surcharge
a = {"siren": "48", "nb": 2}
b = {**a, "nb": 3, "ville": "Lyon"}
b["nb"], b["ville"]   # → (3, "Lyon")
a["nb"]               # → 2  (intact)
```

```python
# Exemple 2 : dict → arguments nommés
from dataclasses import dataclass

@dataclass
class Annonce:
    siren: str
    nb: int

Annonce(**{"siren": "48", "nb": 2}).nb
# → 2
```

- Quiz : Avec `def f(siren): return siren`, que fait `f(**{"siren": "48", "ville": "Lyon"})` ?
- [ ] Renvoie `"48"` et ignore `ville`
- [x] `TypeError`
- [ ] `KeyError`
- [ ] Renvoie `("48", "Lyon")`
- Réponse : `TypeError` (unexpected keyword argument 'ville') : chaque clé devient un argument nommé, et `f` n'a pas de paramètre `ville`.

## 12. Trier un dict
- Sous-thème : parcourir
- Niveau : 2
- Définition : `sorted(d.items(), key=…)` trie les paires d'un dict par clé ou par valeur ; `dict(...)` reconstruit un dict dans cet ordre.
- Contexte : Un dict n'a pas de méthode `sort` : on trie ses paires, puis on reconstruit un dict, qui garde l'ordre d'insertion. `kv[0]` est la clé, `kv[1]` la valeur. Pour un top N par valeur, `Counter.most_common` ou `heapq.nlargest` évitent de tout trier.
- Usage : ✅ rapport par volume décroissant, dict réordonné avant un export · ❌ trier à chaque lecture : trier une fois, au moment d'afficher ou d'écrire.

```python
# Exemple 1 : par valeur décroissante
nb = {"Lyon": 3, "Paris": 5, "Nice": 1}
sorted(nb.items(), reverse=True,
       key=lambda kv: kv[1])
# → [("Paris", 5), ("Lyon", 3), ("Nice", 1)]
```

```python
# Exemple 2 : reconstruire le dict
nb = {"Lyon": 3, "Paris": 5, "Nice": 1}
trie = dict(sorted(nb.items()))
list(trie)   # → ["Lyon", "Nice", "Paris"]
```

- Quiz : Que vaut `sorted({"Paris": 5, "Lyon": 3})` ?
- [ ] `[3, 5]`
- [x] `["Lyon", "Paris"]`
- [ ] `[("Lyon", 3), ("Paris", 5)]`
- [ ] `{"Lyon": 3, "Paris": 5}`
- Réponse : `["Lyon", "Paris"]` : parcourir un dict donne ses clés, et `sorted` renvoie toujours une liste.

## 13. Counter : compter
- Sous-thème : outils
- Niveau : 2
- Définition : `Counter` compte les occurrences d'éléments : un dict valeur → nombre, avec `most_common` pour le classement.
- Contexte : `Counter(itérable)` compte en une ligne ce qu'on ferait avec un dict et des `get(k, 0) + 1`. Il s'utilise comme un dict, se met à jour avec `update`, et deux compteurs s'additionnent avec `+`. `most_common(n)` renvoie les `n` plus fréquents, triés du plus au moins fréquent.
- Usage : ✅ statistiques rapides (annonces par ville, par type), top N · ❌ agréger autre chose qu'un comptage (sommes, listes) : `defaultdict`.

```python
# Exemple 1 : compter et classer
from collections import Counter
villes = ["Lyon", "Paris", "Lyon",
          "Nice", "Lyon", "Paris"]
c = Counter(villes)
c["Lyon"]        # → 3
c.most_common(2)
# → [("Lyon", 3), ("Paris", 2)]
```

```python
# Exemple 2 : cumuler plusieurs jours
from collections import Counter
lundi = Counter({"A": 2, "B": 1})
mardi = Counter({"A": 1, "C": 4})
total = lundi + mardi
total["A"]       # → 3
total["C"]       # → 4
```

- Quiz : Que vaut `Counter("aab")["z"]` ?
- [ ] `KeyError`
- [ ] `None`
- [x] `0`
- [ ] `1`
- Réponse : `0` : une clé absente d'un `Counter` vaut 0, sans `KeyError` (et sans être ajoutée).

## 14. defaultdict : grouper
- Sous-thème : outils
- Niveau : 2
- Définition : `defaultdict(fabrique)` crée automatiquement la valeur d'une clé absente : idéal pour grouper sans tester la clé.
- Contexte : `defaultdict(list)` appelle `list()` quand on accède avec `d[k]` à une clé manquante, donc `d[k].append(x)` marche directement. Sans lui, on écrit `d.setdefault(k, []).append(x)` ou un `if k not in d`. La fabrique peut être `int` (compteur à 0), `set`, ou toute fonction sans argument.
- Usage : ✅ grouper des enregistrements par clé (annonces par ville), accumuler des sommes · ❌ dict renvoyé à l'extérieur : le convertir avec `dict(d)`, pour que les lectures ne créent plus de clés.

```python
# Exemple 1 : grouper par ville
from collections import defaultdict
annonces = [("A1", "Lyon"), ("B2", "Paris"),
            ("C3", "Lyon")]
par_ville = defaultdict(list)
for id_, ville in annonces:
    par_ville[ville].append(id_)
par_ville["Lyon"]   # → ["A1", "C3"]
```

```python
# Exemple 2 : la même chose avec setdefault
annonces = [("A1", "Lyon"), ("C3", "Lyon")]
par_ville = {}
for id_, ville in annonces:
    par_ville.setdefault(ville, []).append(id_)
par_ville   # → {"Lyon": ["A1", "C3"]}
```

- Quiz : Avec `d = defaultdict(list)`, que vaut `len(d)` après une simple lecture `d["x"]` ?
- [ ] `0`
- [x] `1`
- [ ] `KeyError`
- Réponse : `1` : lire une clé absente la crée (avec `[]`) ; `"x" in d` ou `d.get("x")` ne créent rien.

## 15. TypedDict : typer un dict JSON
- Sous-thème : lire
- Niveau : 2
- Définition : `TypedDict` décrit les clés et types attendus d'un dict pour l'éditeur et mypy (≈ `interface` TS), sans aucun contrôle à l'exécution.
- Contexte : C'est l'équivalent le plus proche d'une interface TS sur un objet JSON : la valeur reste un dict ordinaire, `type(a)` vaut `dict`, on la lit avec `a["siren"]`. `NotRequired[...]` ou `total=False` marquent les clés facultatives. Rien n'est vérifié à l'exécution : un JSON mal formé passe sans erreur.
- Usage : ✅ typer un dict transmis tel quel (réponse d'API, événement Lambda) · ❌ données externes à valider : pydantic ; objet métier avec attributs : `dataclass`.

```python
# Exemple 1 : une interface de dict
from typing import TypedDict

class Annonce(TypedDict):
    siren: str
    nb: int

a: Annonce = {"siren": "48", "nb": 2}
a["siren"]          # → "48"
type(a).__name__    # → "dict"
```

```python
# Exemple 2 : aucun contrôle
from typing import TypedDict

class Annonce(TypedDict):
    siren: str

a = Annonce(siren=483609327)  # un int
a["siren"]          # → 483609327
```

- Quiz : Avec `Annonce` de l'exemple 1, que fait `Annonce(siren="48")`, sans `nb` ?
- [ ] `TypeError` : `nb` manque
- [ ] Renvoie `{"siren": "48", "nb": 0}`
- [ ] `KeyError`
- [x] Renvoie `{"siren": "48"}`
- Réponse : renvoie `{"siren": "48"}` : `Annonce(...)` revient à appeler `dict(...)` ; seule la vérification statique (mypy) signalerait le champ manquant.

## 16. dict.fromkeys : une valeur partagée
- Sous-thème : construire
- Niveau : 3
- Définition : `dict.fromkeys(cles, valeur)` donne à toutes les clés le **même** objet valeur : avec `[]`, toutes partagent une seule liste.
- Contexte : La valeur est évaluée une fois, puis la même référence est posée sur chaque clé. Sans danger pour une valeur immuable (`0`, `None`, `""`), piège pour une liste ou un dict : un `append` via une clé apparaît sous toutes. Pour une liste par clé : la compréhension `{k: [] for k in cles}` ou `defaultdict(list)`.
- Usage : ✅ `fromkeys(cles, 0)` ou `fromkeys(cles)` pour initialiser ou dédoublonner · ❌ `fromkeys(cles, [])` pour grouper : compréhension ou `defaultdict`.

```python
# Exemple 1 : une seule liste partagée
d = dict.fromkeys(["Lyon", "Nice"], [])
d["Lyon"].append("A1")
d   # → {"Lyon": ["A1"], "Nice": ["A1"]}
d["Lyon"] is d["Nice"]   # → True
```

```python
# Exemple 2 : une liste par clé
d = {k: [] for k in ["Lyon", "Nice"]}
d["Lyon"].append("A1")
d   # → {"Lyon": ["A1"], "Nice": []}
```

- Quiz : Avec `d = dict.fromkeys(["a", "b"], 0)`, que vaut `d` après `d["a"] += 1` ?
- [ ] `{"a": 1, "b": 1}`
- [x] `{"a": 1, "b": 0}`
- [ ] `{"a": 0, "b": 0}`
- [ ] `TypeError`
- Réponse : `{"a": 1, "b": 0}` : un `int` est immuable, `+=` crée un nouvel objet et ne réaffecte que la clé `"a"`.

## 17. Ordre d'insertion : réaffecter ne déplace pas
- Sous-thème : modifier
- Niveau : 3
- Définition : Réaffecter une clé existante garde sa place ; la supprimer puis la réinsérer la met à la fin, et `popitem()` retire la dernière insérée.
- Contexte : L'ordre d'un dict est celui de la **première** insertion de chaque clé, garanti depuis Python 3.7. `d[k] = v` sur une clé présente change la valeur, pas la position ; pour déplacer, `d[k] = d.pop(k)`. `popitem()` suit l'ordre inverse (dernier entré, premier sorti). Cet ordre se retrouve dans `json.dumps`, donc dans les fichiers écrits.
- Usage : ✅ maîtriser l'ordre des champs d'un export JSON, petit cache LRU · ❌ logique qui dépend de l'ordre des clés : trier explicitement.

```python
# Exemple 1 : réaffecter ou réinsérer
d = {"a": 1, "b": 2}
d["a"] = 10            # garde sa place
list(d)                # → ["a", "b"]
d["a"] = d.pop("a")    # réinsère
list(d)                # → ["b", "a"]
```

```python
# Exemple 2 : popitem, dernier entré
d = {"A1": 1, "B2": 2, "C3": 3}
d.popitem()            # → ("C3", 3)
list(d)                # → ["A1", "B2"]
```

- Quiz : Que fait `{}.popitem()` ?
- [ ] Renvoie `None`
- [ ] Renvoie `()`
- [ ] `IndexError`
- [x] `KeyError`
- Réponse : `KeyError` (dictionary is empty) : comme une clé lue absente ; tester `if d:` avant.

## 18. Vues : keys et items comme des ensembles
- Sous-thème : parcourir
- Niveau : 3
- Définition : `keys()` et `items()` se comportent comme des sets : `&`, `|`, `-` comparent directement les clés de deux dicts.
- Contexte : Les vues de clés acceptent les opérations ensemblistes sans conversion : clés communes, clés en plus, clés disparues. `items()` aussi, tant que les valeurs sont hashables. `values()` non : ses valeurs peuvent se répéter et ne sont pas forcément hashables, elle n'a rien d'un set. Le résultat d'une opération est un vrai `set`.
- Usage : ✅ comparer le schéma de deux annonces (champs ajoutés, disparus), vérifier des champs requis · ❌ comparer des valeurs : `list(d.values())` ou `Counter`.

```python
# Exemple 1 : comparer deux schémas
v1 = {"siren": 1, "ville": 2}
v2 = {"siren": 1, "cp": 3}
v2.keys() - v1.keys()   # → {"cp"}
v1.keys() & v2.keys()   # → {"siren"}
```

```python
# Exemple 2 : champs requis présents ?
requis = {"siren", "date"}
a = {"siren": "48", "date": "2026-10-23",
     "ville": "Lyon"}
requis <= a.keys()      # → True
a.keys() - requis       # → {"ville"}
```

- Quiz : Avec `d = {"a": 1}`, que vaut `d.values() == d.values()` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- [ ] `None`
- Réponse : `False` : une vue `values()` ne définit pas d'égalité par contenu, `==` compare l'identité de deux vues distinctes ; comparer `list(d.values())`.

## 19. __missing__ : un défaut qui dépend de la clé
- Sous-thème : outils
- Niveau : 3
- Définition : Une sous-classe de `dict` qui définit `__missing__(self, clé)` décide de ce que renvoie `d[k]` pour une clé absente.
- Contexte : `defaultdict` appelle une fabrique sans argument ; `__missing__` reçoit la clé, ce qui permet un défaut calculé (« tribunal 6901 inconnu »). Il n'est appelé que par `d[k]`. Il peut renvoyer une valeur sans l'enregistrer, ou l'enregistrer avec `self[k] = v`, ce qui en fait un cache.
- Usage : ✅ table de correspondance avec repli lisible (codes tribunaux, libellés), petit cache · ❌ valeur par défaut fixe : `defaultdict(lambda: …)` ou `get(k, défaut)`.

```python
# Exemple 1 : défaut calculé
class Tribunaux(dict):
    def __missing__(self, code):
        return f"inconnu ({code})"

t = Tribunaux({"7501": "Paris"})
t["6901"]      # → "inconnu (6901)"
t["7501"]      # → "Paris"
len(t)         # → 1  (rien ajouté)
```

```python
# Exemple 2 : mémoriser le calcul
class Longueurs(dict):
    def __missing__(self, k):
        self[k] = len(k)   # enregistre
        return self[k]

c = Longueurs()
c["483609327"]   # → 9
list(c)          # → ["483609327"]
```

- Quiz : Avec `t` de l'exemple 1, que vaut `t.get("6901")` ?
- [ ] `"inconnu (6901)"`
- [x] `None`
- [ ] `KeyError`
- [ ] `""`
- Réponse : `None` : `get` ne passe pas par `__missing__`, réservé à `d[k]` ; `in` l'ignore aussi.
