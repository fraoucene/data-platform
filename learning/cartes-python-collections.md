---
title: "Cartes · Collections Python"
type: cartes
langage: Python
chapitre: Bases du langage
cours: Collections
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Collections Python
Python · Collections : copies, outils, set, tuple (format spec v3 de revision-pwa).

## 1. tuple : une séquence figée
- Id : collections-tuple-fige
- Sous-thème : tuple
- Type : concept
- Niveau : 1
- Profils : débutant
- Mots-clés : set, NamedTuple, dataclass
- Définition : `tuple` est une séquence ordonnée **non modifiable** : on la lit comme une liste, sans pouvoir ajouter ni remplacer (≈ `readonly [a, b]`).
- Contexte : Un tuple regroupe quelques valeurs liées dont la position a un sens (code, SIREN, date). Comme il est figé, il peut servir de clé de dict ou d'élément de set, ce que la liste ne peut pas. Les parenthèses sont souvent facultatives : c'est la virgule qui fabrique le tuple.
- Usage : ✅ enregistrement fixe (ligne CSV, coordonnées), plusieurs valeurs de retour, clé composée · ❌ collection qui grandit : `list` ; champs nommés : `NamedTuple` ou `dataclass`.

```python
# Exemple 1 : lire, mais pas modifier
annonce = ("A1", "483609327", "2026-10-21")
annonce[1]           # → "483609327"
len(annonce)         # → 3
annonce[0] = "B1"    # ❌ TypeError
annonce.append("x")  # ❌ AttributeError
```

```python
# Exemple 2 : clé composée de dict
par_jour = {}
par_jour[("483609327", "2026-10-21")] = 2
cle = ("483609327", "2026-10-21")
par_jour[cle]        # → 2
```

- Quiz : Avec `t = (1, [2])`, que fait `t[1].append(3)` ?
- [ ] `TypeError` : un tuple est figé
- [x] Ça marche : `t` vaut `(1, [2, 3])`
- [ ] `AttributeError`
- [ ] `t` vaut `(1, [2], 3)`
- Réponse : ça marche, `t` vaut `(1, [2, 3])` : le tuple est figé (il garde les mêmes objets), mais une liste qu'il contient reste modifiable.

## 2. tuple : renvoyer et déballer
- Id : collections-tuple-deballer
- Sous-thème : tuple
- Type : concept
- Niveau : 1
- Profils : débutant
- Prérequis : collections-tuple-fige
- Voir aussi : listes-deballer-etoile, tests-destructurer-un-element
- Mots-clés : tuple, dataclass
- Définition : Le déballage affecte chaque élément d'une séquence à une variable (≈ déstructuration `const [a, b] = t`).
- Contexte : Une fonction qui fait `return a, b` renvoie en réalité un tuple, que l'appelant déballe. Le nombre de variables doit correspondre exactement, sinon `ValueError`. Une variable étoilée ramasse le surplus. `_` désigne par convention une valeur ignorée. Échanger deux variables s'écrit `a, b = b, a`, sans variable temporaire.
- Usage : ✅ récupérer plusieurs valeurs de retour, parcourir des paires (`for k, v in d.items()`) · ❌ plus de 3 ou 4 valeurs : renvoyer une `dataclass` aux champs nommés.

```python
# Exemple 1 : renvoyer plusieurs valeurs
def decouper(numero):
    return numero[:2], numero[2:]  # un tuple

prefixe, suite = decouper("A1234")
prefixe        # → "A1"
suite          # → "234"
```

```python
# Exemple 2 : échanger, ignorer
a, b = 1, 2
a, b = b, a    # échange sans temporaire
(a, b)         # → (2, 1)
siren, _, date = ("483609327", "X", "2026-10-21")
date           # → "2026-10-21"
x, y = (1, 2, 3)  # ❌ ValueError
```

- Quiz : Que vaut `reste` après `premier, *reste = (1, 2, 3)` ?
- [ ] `(2, 3)`
- [x] `[2, 3]`
- [ ] `3`
- [ ] `ValueError`
- Réponse : `[2, 3]` : l'étoile ramasse toujours le surplus dans une **liste**, même quand la source est un tuple.

## 3. set : unicité et appartenance
- Id : collections-set-unicite
- Sous-thème : set
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : collections-set-vide-dict, collections-hashable
- Mots-clés : hashable, temps constant
- Définition : `set` est une collection sans doublons ni ordre, au test d'appartenance très rapide (≈ `Set` en TS).
- Contexte : Un set garde un seul exemplaire de chaque valeur, comparée par égalité et par hash. `x in s` est en temps constant, alors que `x in liste` parcourt tout : sur 100 000 SIREN, la différence est énorme. Les éléments doivent être hashables (nombres, chaînes, tuples, pas de listes). Un set n'a pas d'index : `s[0]` n'existe pas.
- Usage : ✅ dédoublonner, tester « déjà vu ? » dans une boucle, comparer deux extractions · ❌ garder l'ordre ou les doublons : `list` ; associer une valeur : `dict`.

```python
# Exemple 1 : dédoublonner, tester
sirens = ["483609327", "552100554",
          "483609327"]
uniques = set(sirens)
len(uniques)              # → 2
"552100554" in uniques    # → True
uniques.add("830024215")
len(uniques)              # → 3
```

```python
# Exemple 2 : repérer les doublons
vus = set()
doublons = []
for s in ["A", "B", "A", "C", "B"]:
    if s in vus:          # temps constant
        doublons.append(s)
    vus.add(s)
doublons                  # → ["A", "B"]
```

- Quiz : Que vaut `{1, True}` ?
- [ ] `{1, True}`
- [x] `{1}`
- [ ] `{True}`
- [ ] `TypeError`
- Réponse : `{1}` : `True == 1` avec le même hash, donc un seul élément ; le premier inséré est gardé.

## 4. statistics : moyenne et médiane
- Id : collections-statistics-moyenne-mediane
- Sous-thème : outils
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Mots-clés : pandas, DuckDB, Lambda
- Définition : Le module `statistics` calcule moyenne, médiane, mode et écart-type sur une liste de nombres, sans dépendance externe.
- Contexte : `mean` est tirée par les valeurs extrêmes, `median` non : sur des comptes d'annonces par jour, une journée exceptionnelle fausse la moyenne. Sur une liste de taille paire, `median` renvoie la moyenne des deux valeurs du milieu, donc souvent un float. `mode` donne la valeur la plus fréquente. Pas de `Math.mean` en JS : ici c'est fourni.
- Usage : ✅ indicateurs rapides dans un script ou une Lambda (volume moyen par jour) · ❌ millions de valeurs ou calcul par groupe : numpy, pandas, DuckDB.

```python
# Exemple 1 : moyenne contre médiane
import statistics as st

nb = [1, 2, 2, 40]
st.mean(nb)       # → 11.25
st.median(nb)     # → 2.0
```

```python
# Exemple 2 : mode et taille impaire
import statistics as st

villes = ["Lyon", "Paris", "Lyon"]
st.mode(villes)       # → "Lyon"
st.median([3, 1, 2])  # → 2  (int)
round(st.stdev([2, 4, 6]), 1)  # → 2.0
```

- Quiz : Que fait `st.mean([])` ?
- [ ] Renvoie `0`
- [ ] Renvoie `nan`
- [ ] `ZeroDivisionError`
- [x] `StatisticsError`
- Réponse : `StatisticsError` : pas de `NaN` silencieux sur une liste vide ; tester la liste avant ou capturer l'exception (sous-classe de `ValueError`).

## 5. tuple : le piège de la virgule
- Id : collections-tuple-virgule
- Sous-thème : tuple
- Type : piège
- Niveau : 2
- Profils : débutant
- Prérequis : collections-tuple-fige
- Voir aussi : fonctions-lambda-renvoyer-tuple
- Mots-clés : tuple
- Définition : C'est la virgule, pas les parenthèses, qui crée un tuple : `x = 1,` est un tuple, `(1)` un simple nombre.
- Contexte : Les parenthèses ne servent qu'à grouper ; un tuple d'un seul élément exige une virgule finale : `(1,)`. Le piège classique est une virgule restée en fin de ligne après avoir copié un argument de fonction : la variable devient un tuple, et l'erreur apparaît plus loin, loin de sa cause.
- Usage : ✅ écrire `(x,)` quand une API attend un tuple d'un élément (paramètres SQL) · ❌ virgule finale hors d'un appel ou d'une collection : à traquer en relecture.

```python
# Exemple 1 : parenthèses ou virgule
type((1)).__name__    # → "int"
type((1,)).__name__   # → "tuple"
t = 1, 2              # tuple sans parenthèses
t                     # → (1, 2)
```

```python
# Exemple 2 : la virgule oubliée
siren = "483609327",  # virgule en trop
type(siren).__name__  # → "tuple"
siren.upper()         # ❌ AttributeError
```

- Quiz : Que vaut `len(("483609327"))` ?
- [ ] `1`
- [x] `9`
- [ ] `TypeError`
- [ ] `2`
- Réponse : `9` : sans virgule, les parenthèses ne font que grouper ; c'est une chaîne de 9 caractères, pas un tuple d'un élément.

## 6. alias : b = a ne copie pas
- Id : collections-alias-pas-de-copie
- Sous-thème : copies
- Type : piège
- Niveau : 2
- Profils : débutant, web
- Prérequis : listes-modifier-sur-place
- Voir aussi : collections-copie-superficielle-profonde
- Mots-clés : référence
- Définition : `b = a` ne copie pas : `a` et `b` désignent la même liste, et toute modification se voit des deux côtés (comme en JS).
- Contexte : En Python, une variable est une étiquette posée sur un objet. Affecter, passer en argument ou ranger dans une autre liste partage l'objet, sans copie. `is` teste si deux noms désignent le même objet, `==` si les valeurs sont égales. Pour une liste indépendante : `a.copy()`, `list(a)` ou `a[:]`.
- Usage : ✅ partager volontairement un état (accumulateur passé à une fonction) · ❌ modifier une donnée reçue en argument : copier d'abord, ou renvoyer une nouvelle liste.

```python
# Exemple 1 : un objet, deux noms
a = [1, 2]
b = a           # pas de copie
b.append(3)
a               # → [1, 2, 3]
a is b          # → True
c = a.copy()
c is a          # → False
c == a          # → True
```

```python
# Exemple 2 : une fonction modifie l'appelant
def ajouter(liste, x):
    liste.append(x)   # mute l'original

sirens = ["483609327"]
ajouter(sirens, "552100554")
len(sirens)     # → 2
```

- Quiz : Que vaut `m` après `m = [[0]] * 3` puis `m[0].append(1)` ?
- [ ] `[[0, 1], [0], [0]]`
- [x] `[[0, 1], [0, 1], [0, 1]]`
- [ ] `[[0], [0], [0], 1]`
- [ ] `TypeError`
- Réponse : `[[0, 1], [0, 1], [0, 1]]` : `* 3` répète 3 fois la **même** liste ; écrire `[[0] for _ in range(3)]`.

## 7. copy : superficielle ou profonde
- Id : collections-copie-superficielle-profonde
- Sous-thème : copies
- Type : comparaison
- Niveau : 2
- Profils : data, web
- Prérequis : collections-alias-pas-de-copie
- Mots-clés : référence
- Définition : `copy()` copie le conteneur mais partage ses éléments ; `copy.deepcopy()` copie aussi tout ce qu'il contient.
- Contexte : Une copie superficielle suffit pour une liste de chaînes ou de nombres, qui ne se modifient pas. Dès que les éléments sont eux-mêmes modifiables (listes, dicts), copie et original partagent ces éléments. `deepcopy` duplique récursivement : plus sûr, mais plus lent sur de gros volumes (≈ `structuredClone` en JS).
- Usage : ✅ `copy()` pour une liste ou un dict de valeurs simples, `deepcopy` pour une config imbriquée qu'on va modifier · ❌ `deepcopy` par réflexe dans une boucle sur des milliers d'annonces : coûteux.

```python
# Exemple 1 : superficielle, éléments partagés
a = [["x"], ["y"]]
b = a.copy()
b[0].append("z")
a[0]            # → ["x", "z"]  (partagé)
b.append(["w"])
len(a)          # → 2  (conteneurs distincts)
```

```python
# Exemple 2 : profonde, tout est dupliqué
import copy
a = [["x"], ["y"]]
b = copy.deepcopy(a)
b[0].append("z")
a[0]            # → ["x"]
```

- Quiz : Avec `a = {"tags": ["x"]}` et `b = dict(a)`, que vaut `a["tags"]` après `b["tags"].append("y")` ?
- [ ] `["x"]`
- [x] `["x", "y"]`
- [ ] `["y"]`
- Réponse : `["x", "y"]` : `dict(a)` est une copie superficielle, la liste `tags` est partagée entre `a` et `b`.

## 8. set vide : {} est un dict
- Id : collections-set-vide-dict
- Sous-thème : set
- Type : piège
- Niveau : 2
- Profils : débutant
- Prérequis : collections-set-unicite
- Mots-clés : set, annotation de type
- Définition : `{}` crée un dict vide, pas un set : un set vide s'écrit `set()`.
- Contexte : Les accolades servent aux deux types : `{1, 2}` est un set, `{"a": 1}` un dict, et `{}` est réservé au dict, plus ancien. L'erreur ne se voit qu'au premier appel d'une méthode de set. Même confusion possible dans les annotations : `set[str]` pour le type, `set()` pour la valeur.
- Usage : ✅ `set()` pour tout set vide, `{…}` seulement avec des éléments · ❌ `{}` en pensant « collection vide » : c'est toujours un dict.

```python
# Exemple 1 : les quatre écritures
type({}).__name__        # → "dict"
type(set()).__name__     # → "set"
type({1, 2}).__name__    # → "set"
type({"a": 1}).__name__  # → "dict"
```

```python
# Exemple 2 : accumuler des codes vus
vus = set()              # et non {}
for code in ["A1", "B2", "A1"]:
    vus.add(code)
sorted(vus)              # → ["A1", "B2"]
```

- Quiz : Que fait `s = {}` puis `s.add("A1")` ?
- [ ] `s` vaut `{"A1"}`
- [x] `AttributeError`
- [ ] `TypeError`
- [ ] `s` vaut `{"A1": None}`
- Réponse : `AttributeError` : `s` est un dict, qui n'a pas de `.add` ; il fallait `s = set()`.

## 9. set : opérations ensemblistes
- Id : collections-set-operations
- Sous-thème : set
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : collections-set-unicite
- Voir aussi : dictionnaires-vues-ensemblistes
- Mots-clés : set, itérable, Counter
- Définition : `|` union, `&` intersection, `-` différence et `^` différence symétrique comparent deux ensembles en une opération.
- Contexte : Ces opérateurs renvoient un nouveau set ; les méthodes `union`, `intersection`… font pareil et acceptent en plus n'importe quel itérable. Bien plus rapides et lisibles qu'une double boucle pour comparer deux extractions : SIREN apparus, disparus, communs. `<=` teste l'inclusion.
- Usage : ✅ comparer deux jours d'annonces, vérifier que des champs obligatoires sont présents · ❌ besoin des doublons ou de l'ordre : passer par des listes et `Counter`.

```python
# Exemple 1 : comparer deux extractions
hier = {"483609327", "552100554"}
auj = {"552100554", "830024215"}
auj - hier       # → {"830024215"}  (nouveaux)
auj & hier       # → {"552100554"}  (communs)
len(auj | hier)  # → 3  (tous)
```

```python
# Exemple 2 : inclusion
requis = {"siren", "date"}
champs = {"siren", "date", "ville"}
requis <= champs     # → True
requis.issubset(["siren", "date"])  # → True
```

- Quiz : Que valent `{1, 2} - {2, 3}` et `{2, 3} - {1, 2}` ?
- [x] `{1}` et `{3}`
- [ ] `{1}` et `{1}`
- [ ] `{1, 3}` et `{1, 3}`
- [ ] `{3}` et `{1}`
- Réponse : `{1}` et `{3}` : la différence n'est pas symétrique ; pour « ce qui diffère des deux côtés », `^`.

## 10. dict.fromkeys : dédoublonner dans l'ordre
- Id : collections-dedoublonner-ordre
- Sous-thème : set
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : dictionnaires-creer
- Voir aussi : collections-set-unicite
- Mots-clés : hashable
- Définition : `list(dict.fromkeys(seq))` retire les doublons en gardant l'ordre de première apparition.
- Contexte : Un dict garde l'ordre d'insertion et ses clés sont uniques : `dict.fromkeys` crée une clé par élément (valeur `None`), puis `list` récupère les clés. C'est l'idiome standard, en temps linéaire. Les éléments doivent être hashables. Pour dédoublonner des enregistrements selon un champ, un dict `{champ: enregistrement}` garde le dernier vu.
- Usage : ✅ dédoublonner des SIREN dans l'ordre de lecture · ❌ ordre sans importance : `set` suffit.

```python
# Exemple 1 : garder l'ordre de lecture
sirens = ["552100554", "483609327",
          "552100554", "830024215"]
list(dict.fromkeys(sirens))
# → ["552100554", "483609327", "830024215"]
```

```python
# Exemple 2 : dédoublonner sur un champ
annonces = [{"siren": "A", "n": 1},
            {"siren": "B", "n": 2},
            {"siren": "A", "n": 3}]
# la dernière annonce par SIREN gagne,
# à la place de la première
derniere = {a["siren"]: a for a in annonces}
[a["n"] for a in derniere.values()]  # → [3, 2]
```

- Quiz : Pourquoi pas `list(set(sirens))` pour garder l'ordre ?
- [ ] C'est plus lent que `dict.fromkeys`
- [x] L'ordre d'un `set` n'est pas garanti
- [ ] Un `set` garde les doublons consécutifs
- [ ] `list(set(…))` lève `TypeError`
- Réponse : un `set` n'a pas d'ordre garanti : le résultat peut changer d'une exécution à l'autre ; `dict.fromkeys` garde l'ordre d'insertion.

## 11. hashable : clés de dict, éléments de set
- Id : collections-hashable
- Sous-thème : set
- Type : concept
- Niveau : 2
- Profils : data, expert
- Prérequis : collections-set-unicite
- Voir aussi : classes-dataclass-frozen, hachage-hash-builtin-instable
- Mots-clés : hash, frozenset
- Définition : Seuls les objets hashables (`str`, nombres, `tuple` d'objets hashables, `frozenset`) peuvent être clés de dict ou éléments de set.
- Contexte : Un dict et un set rangent leurs éléments selon leur hash, calculé une fois à l'insertion. Si l'objet pouvait changer, son hash changerait et on ne le retrouverait plus : listes, dicts et sets sont donc refusés avec `TypeError: unhashable type`. Pour une clé composée, on convertit en tuple ; pour un set dans un set, en `frozenset`.
- Usage : ✅ convertir une ligne (`list`) en `tuple` pour la dédoublonner ou l'utiliser comme clé · ❌ utiliser un objet modifiable comme clé « parce que ça marche » : c'est refusé, à juste titre.

```python
# Exemple 1 : clé composée en tuple
vus = set()
vus.add(("483609327", "2026-10-21"))
("483609327", "2026-10-21") in vus  # → True
vus.add(["483609327"])   # ❌ TypeError
```

```python
# Exemple 2 : convertir avant d'indexer
lignes = [["Lyon", "A1"], ["Lyon", "A1"],
          ["Nice", "B2"]]
uniques = {tuple(l) for l in lignes}
len(uniques)             # → 2
frozenset({1, 2}) in {frozenset({2, 1})}
# → True
```

- Quiz : Avec `t = (1, [2])`, que fait `{t}` ?
- [ ] `{(1, [2])}`
- [x] `TypeError`
- [ ] `{1, [2]}`
- [ ] `{(1,)}`
- Réponse : `TypeError: unhashable type: 'list'` : un tuple n'est hashable que si tous ses éléments le sont, et il contient une liste.
## 12. sorted : plusieurs clés
- Id : collections-sorted-plusieurs-cles
- Sous-thème : outils
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : listes-sorted-key
- Voir aussi : classes-dataclass-order
- Mots-clés : clé de tri, tri stable, heapq
- Définition : Une `key` qui renvoie un tuple trie sur plusieurs critères dans l'ordre ; un signe `-` inverse un critère numérique seul.
- Contexte : Les tuples se comparent élément par élément : le 2e critère ne départage qu'en cas d'égalité sur le 1er. Le `-` ne marche que sur un nombre ; pour inverser une chaîne seule, on trie en deux passes, car le tri de Python est stable. `sorted` renvoie une nouvelle liste, `list.sort` trie sur place et renvoie `None`. Pas de comparateur `(a, b) => …` comme en JS : une clé.
- Usage : ✅ classement par volume puis par nom, tri de lignes avant export · ❌ seulement les N premiers d'une grande liste : `heapq.nlargest`.

```python
# Exemple 1 : volume décroissant, nom
t = [("Lyon", 3), ("Paris", 5),
     ("Brest", 3)]
r = sorted(t, key=lambda x: (-x[1], x[0]))
[v for v, _ in r]
# → ["Paris", "Brest", "Lyon"]
```

```python
# Exemple 2 : deux passes (tri stable)
t = [("Lyon", 3), ("Paris", 5),
     ("Brest", 3)]
# 1. critère secondaire : nom ↓
r = sorted(t, key=lambda x: x[0],
           reverse=True)
# 2. critère principal : volume
r = sorted(r, key=lambda x: x[1])
[v for v, _ in r]
# → ["Lyon", "Brest", "Paris"]
```

- Quiz : `key=lambda x: (x[1], x[0])` et `reverse=True` : quel ordre des villes ?
- [ ] Paris, Brest, Lyon
- [ ] Brest, Lyon, Paris
- [x] Paris, Lyon, Brest
- [ ] Lyon, Brest, Paris
- Réponse : Paris, Lyon, Brest : `reverse` inverse tout le tuple, les villes à égalité passent aussi en ordre décroissant.

## 13. groupby : trier d'abord
- Id : collections-groupby-trier-dabord
- Sous-thème : outils
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : listes-sorted-key
- Voir aussi : dictionnaires-defaultdict-grouper
- Mots-clés : itérateur, Counter, defaultdict
- Définition : `itertools.groupby` regroupe les éléments **consécutifs** de même clé ; l'entrée doit donc être triée sur cette clé.
- Contexte : `groupby` renvoie des paires `(clé, groupe)` où le groupe est un itérateur, épuisé dès qu'on passe au groupe suivant : on le consomme tout de suite (`list(g)`). Le `key=` du tri et celui de `groupby` doivent être identiques. Pour seulement compter, `Counter` est plus simple ; `groupby` sert quand on veut les éléments de chaque groupe.
- Usage : ✅ regrouper des annonces triées par tribunal ou par jour · ❌ simple comptage : `Counter` ; données non triées et volumineuses : `defaultdict(list)` en un passage.

```python
# Exemple 1 : compter après tri
from itertools import groupby

v = ["Lyon", "Paris", "Lyon"]
[(k, len(list(g)))
 for k, g in groupby(sorted(v))]
# → [("Lyon", 2), ("Paris", 1)]
```

```python
# Exemple 2 : grouper des annonces
from itertools import groupby

ann = [{"trib": "Lyon", "s": "48"},
       {"trib": "Paris", "s": "55"},
       {"trib": "Lyon", "s": "83"}]
k = lambda a: a["trib"]
tri = sorted(ann, key=k)  # même clé
res = {t: [a["s"] for a in g]
       for t, g in groupby(tri, key=k)}
res["Lyon"]    # → ["48", "83"]
res["Paris"]   # → ["55"]
```

- Quiz : Exemple 1 avec `groupby(v)`, sans `sorted` : que donne l'expression ?
- [x] `[("Lyon", 1), ("Paris", 1), ("Lyon", 1)]`
- [ ] `[("Lyon", 2), ("Paris", 1)]`
- [ ] `[("Paris", 1), ("Lyon", 2)]`
- Réponse : `[("Lyon", 1), ("Paris", 1), ("Lyon", 1)]` : `groupby` n'est pas un `GROUP BY` SQL, il coupe à chaque changement de clé.
