---
title: "Cartes · Listes Python"
type: cartes
langage: Python
cours: Listes
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Listes Python
Python · Listes : construire, lire, modifier, parcourir, trier (format spec v3 de revision-pwa).

## 1. list : lire
- Sous-thème : lire
- Niveau : 1
- Définition : `list` est une séquence ordonnée et modifiable, indexée depuis 0, avec indices négatifs et tranches (≈ `Array` en TS).
- Contexte : Une tranche `l[début:fin]` prend de `début` inclus à `fin` exclu et renvoie une nouvelle liste. Les indices négatifs comptent depuis la fin : `l[-1]` est le dernier, sans calculer la longueur. Contrairement à JS, lire un index qui n'existe pas ne renvoie pas `undefined` : `l[10]` lève `IndexError`. Une tranche accepte aussi un pas : `l[::2]`, `l[::-1]`.
- Usage : ✅ collection ordonnée qu'on parcourt ou modifie (lignes lues, résultats) · ❌ données fixes : `tuple` ; tests d'appartenance fréquents : `set`.

```python
# Exemple 1 : lire par index et par tranche
sirens = ["483609327", "552100554",
          "830024215", "912345678"]

sirens[0]      # → "483609327"
sirens[-1]     # → "912345678"  (le dernier)
sirens[1:3]    # → ["552100554", "830024215"]
len(sirens)    # → 4
```

```python
# Exemple 2 : tranches avec un pas
nums = [0, 1, 2, 3, 4, 5]
nums[:3]       # → [0, 1, 2]  (3 premiers)
nums[-2:]      # → [4, 5]  (2 derniers)
nums[::2]      # → [0, 2, 4]  (un sur deux)
nums[::-1]     # → [5, 4, 3, 2, 1, 0]  (inversée)
```

- Quiz : Avec la liste de 4 SIREN, que valent `sirens[2:100]` et `sirens[100:]` ?
- [x] `["830024215", "912345678"]` et `[]`
- [ ] `IndexError` sur les deux
- [ ] `["830024215", "912345678"]`, puis `IndexError`
- [ ] `None` et `None`
- Réponse : `["830024215", "912345678"]` et `[]` : une tranche ne lève jamais `IndexError`, elle s'arrête au bout de la liste.

## 2. in, index, count : chercher
- Sous-thème : lire
- Niveau : 1
- Définition : `x in l` teste la présence, `l.index(x)` donne la position, `l.count(x)` compte les occurrences d'une valeur.
- Contexte : `index` lève `ValueError` si la valeur manque, là où `indexOf` renvoie `-1` en JS : tester avec `in` d'abord, ou capturer. `in` et `index` parcourent la liste du début (temps linéaire) : pour des milliers de tests, convertir en `set`. La comparaison se fait par égalité `==` sur l'élément entier.
- Usage : ✅ position d'un en-tête dans une ligne CSV, vérifier une valeur dans une petite liste · ❌ tests d'appartenance répétés sur une grande liste : `set`.

```python
# Exemple 1 : chercher une valeur
entetes = ["id", "siren", "ville"]
"siren" in entetes      # → True
entetes.index("ville")  # → 2
entetes.index("cp")     # ❌ ValueError
```

```python
# Exemple 2 : compter, chercher plus loin
codes = ["A1", "B2", "A1", "C3"]
codes.count("A1")       # → 2
codes.index("A1", 1)    # → 2  (dès l'index 1)
```

- Quiz : Que vaut `"4836" in ["483609327", "552100554"]` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- [ ] `0`
- Réponse : `False` : sur une liste, `in` compare chaque élément entier avec `==` ; la recherche de sous-chaîne ne vaut que sur une `str`.

## 3. sum, min, max : agréger
- Sous-thème : lire
- Niveau : 1
- Définition : `sum`, `min`, `max` et `len` donnent le total, le minimum, le maximum ou la taille d'une liste, sans boucle.
- Contexte : Ce sont des fonctions, pas des méthodes : `sum(l)`, pas `l.sum()`. `min` et `max` comparent avec `<`, donc des chaînes se comparent caractère par caractère. Sur une liste vide, `sum` renvoie `0` mais `min` et `max` lèvent `ValueError`, sauf avec `default=`. `sum` accepte directement une expression génératrice.
- Usage : ✅ total des capitaux, date ISO la plus récente, taille d'un lot · ❌ concaténer des chaînes : `"".join(l)`, pas `sum`.

```python
# Exemple 1 : total, min, max
capitaux = [500, 9000, 1200]
sum(capitaux)    # → 10700
min(capitaux)    # → 500
max(capitaux)    # → 9000
len(capitaux)    # → 3
```

```python
# Exemple 2 : liste vide
sum([])              # → 0
max([], default=0)   # → 0
max([])              # ❌ ValueError
```

- Quiz : Que vaut `max(["9", "10", "200"])` ?
- [ ] `"200"`
- [ ] `"10"`
- [x] `"9"`
- [ ] `200`
- Réponse : `"9"` : des chaînes se comparent caractère par caractère, et `"9"` > `"2"` > `"1"` ; pour comparer des nombres, `max(l, key=int)`.

## 4. == : comparer deux listes
- Sous-thème : lire
- Niveau : 1
- Définition : `==` compare deux listes élément par élément, dans l'ordre ; `<` les compare comme le dictionnaire compare des mots.
- Contexte : En JS, `[1] === [1]` vaut `false` ; en Python, `==` compare les contenus, récursivement. L'identité (même objet) se teste avec `is`. `<` et `>` décident sur le premier élément différent ; si l'une est le début de l'autre, la plus courte est la plus petite. C'est ce qui rend `assert resultat == [...]` si pratique en test.
- Usage : ✅ assert dans un test, comparer deux extractions ordonnées · ❌ comparer sans tenir compte de l'ordre : `sorted(a) == sorted(b)` ou des `set`.

```python
# Exemple 1 : contenu, pas identité
a = ["483609327", "552100554"]
b = ["483609327", "552100554"]
a == b         # → True
a is b         # → False  (deux objets)
a == b[::-1]   # → False  (l'ordre compte)
```

```python
# Exemple 2 : ordre de comparaison
[1, 2] < [1, 3]      # → True
[1, 2] < [1, 2, 0]   # → True  (préfixe)
[[1]] == [[1]]       # → True  (récursif)
```

- Quiz : Que vaut `[1, 2] == (1, 2)` ?
- [ ] `True`
- [ ] `TypeError`
- [x] `False`
- [ ] `None`
- Réponse : `False` : une liste n'est jamais égale à un tuple, même avec les mêmes éléments ; comparer `list(t) == l`.

## 5. list : modifier
- Sous-thème : modifier
- Niveau : 1
- Définition : Une `list` se modifie sur place avec `append`, `extend`, `insert`, `pop` et `remove`.
- Contexte : Ces méthodes changent la liste et renvoient `None`, sauf `pop` qui renvoie l'élément retiré. `append(x)` ajoute un élément ; `extend(itérable)` en ajoute plusieurs (≈ `push(...arr)`). `remove(v)` retire la première occurrence d'une valeur et lève `ValueError` si elle manque. L'opérateur `+` crée une nouvelle liste au lieu de modifier l'existante.
- Usage : ✅ construire une liste au fil d'une boucle, retirer un élément traité · ❌ construire en une expression : compréhension ; ajouter ou retirer souvent en tête : `collections.deque`.

```python
# Exemple 1 : ajouter
sirens = ["483609327"]
sirens.append("552100554")   # 1 élément
sirens.extend(["830024215",
               "912345678"]) # plusieurs
sirens.insert(0, "000000000")  # à l'index 0
len(sirens)    # → 5
sirens[0]      # → "000000000"
```

```python
# Exemple 2 : retirer
codes = ["A1", "B2", "C3", "B2"]
codes.pop()    # → "B2"  (le dernier, renvoyé)
codes.pop(0)   # → "A1"  (par index)
codes.remove("B2")   # par valeur, 1re occurrence
codes          # → ["C3"]
codes.remove("Z9")   # ❌ ValueError
```

- Quiz : Avec `x = [1, 2]`, que vaut `x` après `x += "ab"` ?
- [ ] `TypeError`
- [x] `[1, 2, "a", "b"]`
- [ ] `[1, 2, "ab"]`
- [ ] `"12ab"`
- Réponse : `[1, 2, "a", "b"]` : sur une liste, `+=` se comporte comme `extend`, et une chaîne est un itérable de caractères.

## 6. + et * : concaténer et répéter
- Sous-thème : construire
- Niveau : 1
- Définition : `a + b` crée une nouvelle liste qui met `b` après `a` ; `l * n` répète la liste `n` fois.
- Contexte : Les deux renvoient une nouvelle liste sans toucher aux originales, contrairement à `extend`. `+` exige deux listes, alors que `+=` accepte n'importe quel itérable. `* n` répète les références : avec des éléments modifiables, c'est le même objet répété (voir l'alias). En boucle, `l = l + [x]` recopie toute la liste à chaque tour.
- Usage : ✅ assembler deux petites listes, initialiser `[0] * 7` (un compteur par jour) · ❌ ajouter en boucle : `append` ; répéter des listes ou des dicts : compréhension.

```python
# Exemple 1 : de nouvelles listes
a = ["483609327"]
b = ["552100554"]
a + b    # → ["483609327", "552100554"]
a        # → ["483609327"]  (intact)
[0] * 3  # → [0, 0, 0]
```

```python
# Exemple 2 : un compteur par jour
par_jour = [0] * 7     # lundi..dimanche
par_jour[2] += 5       # mercredi
par_jour  # → [0, 0, 5, 0, 0, 0, 0]
```

- Quiz : Que fait `["A1"] + ("B2",)` ?
- [ ] `["A1", "B2"]`
- [ ] `("A1", "B2")`
- [ ] `["A1", ("B2",)]`
- [x] `TypeError`
- Réponse : `TypeError` : `+` n'additionne que deux listes ; `l += ("B2",)` ou `l.extend(("B2",))` acceptent un tuple.

## 7. range : une suite d'entiers
- Sous-thème : construire
- Niveau : 1
- Définition : `range(début, fin, pas)` produit les entiers de `début` inclus à `fin` exclue, sans créer de liste.
- Contexte : Comme pour une tranche, la borne de fin est exclue : `range(3)` donne 0, 1, 2. `range` est paresseux : `range(10**9)` ne coûte rien tant qu'on ne le convertit pas avec `list`. Un pas négatif compte à rebours. Il remplace la boucle `for (let i = 0; …)` de TS, mais pour parcourir une liste on écrit `for x in liste`.
- Usage : ✅ répéter N fois, découper en lots par index (`range(0, n, 500)`) · ❌ parcourir une liste : `for x in liste` ou `enumerate`, pas `range(len(liste))`.

```python
# Exemple 1 : bornes et pas
list(range(3))         # → [0, 1, 2]
list(range(1, 4))      # → [1, 2, 3]
list(range(0, 10, 4))  # → [0, 4, 8]
list(range(3, 0, -1))  # → [3, 2, 1]
```

```python
# Exemple 2 : découper en lots de 2
sirens = ["A", "B", "C", "D", "E"]
lots = [sirens[i:i + 2]
        for i in range(0, len(sirens), 2)]
lots  # → [["A", "B"], ["C", "D"], ["E"]]
```

- Quiz : Que vaut `list(range(5, 0))` ?
- [x] `[]`
- [ ] `[5, 4, 3, 2, 1]`
- [ ] `[4, 3, 2, 1, 0]`
- [ ] `ValueError`
- Réponse : `[]` : le pas par défaut est `+1`, on n'atteint jamais 0 en partant de 5 ; pour compter à rebours, `range(5, 0, -1)`.

## 8. enumerate : l'index avec l'élément
- Sous-thème : parcourir
- Niveau : 1
- Définition : `enumerate(seq)` donne des paires `(index, élément)` pendant une boucle, sans compteur à gérer (≈ `arr.forEach((x, i) => …)`).
- Contexte : En Python, `for x in liste` parcourt les éléments, pas les index. Pour avoir les deux, on n'écrit pas `range(len(liste))` : `enumerate` renvoie les paires, déballées directement dans le `for`. Le paramètre `start` fixe le premier numéro, utile pour un affichage qui commence à 1.
- Usage : ✅ numéroter des lignes, connaître la position d'un élément pendant le parcours · ❌ boucle qui n'utilise pas l'index : `for x in liste` suffit.

```python
# Exemple 1 : index et élément
sirens = ["483609327", "552100554"]
for i, s in enumerate(sirens):
    print(i, s)
# affiché : 0 483609327
# affiché : 1 552100554
```

```python
# Exemple 2 : numéroter à partir de 1
lignes = ["A1", "B2", "C3"]
numeros = [f"{n}. {c}" for n, c
           in enumerate(lignes, start=1)]
numeros        # → ["1. A1", "2. B2", "3. C3"]
list(enumerate("ab"))  # → [(0, "a"), (1, "b")]
```

- Quiz : Que fait `for i, s in ["483609327"]: pass` (sans `enumerate`) ?
- [ ] `i` vaut `0`, `s` vaut `"483609327"`
- [x] `ValueError`
- [ ] `i` vaut `"4"`, `s` vaut `"83609327"`
- [ ] Rien : la boucle ne tourne pas
- Réponse : `ValueError` (too many values to unpack) : Python essaie de découper la chaîne de 9 caractères en 2 variables.

## 9. Compréhensions : list, dict, set
- Sous-thème : construire
- Niveau : 2
- Définition : Une compréhension construit une liste, un dict ou un set en une expression : `[expr for x in seq if cond]` (≈ `filter` + `map`).
- Contexte : Elle remplace la boucle qui fait `append`, en plus lisible et plus rapide. Le `if` final filtre, l'expression de tête transforme. Avec des accolades et `k: v`, on obtient un dict ; avec des accolades seules, un set. Au-delà de deux `for` ou d'une logique longue, une boucle classique reste plus claire.
- Usage : ✅ transformer ou filtrer une collection en une ligne (normaliser des SIREN, indexer par clé) · ❌ effets de bord (écrire, envoyer) : boucle `for` ; gros volume parcouru une seule fois : générateur `(…)`.

```python
# Exemple 1 : liste filtrée et transformée
bruts = [" 483609327", "552100554 ", ""]
sirens = [s.strip() for s in bruts
          if s.strip()]
sirens  # → ["483609327", "552100554"]
```

```python
# Exemple 2 : dict et set par compréhension
annonces = [{"id": "A1", "ville": "Lyon"},
            {"id": "B2", "ville": "Paris"},
            {"id": "C3", "ville": "Lyon"}]
par_id = {a["id"]: a for a in annonces}
par_id["B2"]["ville"]   # → "Paris"
villes = {a["ville"] for a in annonces}
sorted(villes)          # → ["Lyon", "Paris"]
```

- Quiz : Que vaut `[v for v in ["A", "", None, "B", 0] if v]` ?
- [ ] `["A", "", "B", 0]`
- [x] `["A", "B"]`
- [ ] `["A", "", "B"]`
- [ ] `["A", "B", 0]`
- Réponse : `["A", "B"]` : `if v` écarte toutes les valeurs « fausses » (`""`, `None`, `0`), pas seulement `None`.

## 10. * : déballer dans une liste
- Sous-thème : construire
- Niveau : 2
- Définition : `[*a, *b]` déballe des itérables dans une nouvelle liste, et `f(*l)` passe ses éléments en arguments (≈ spread `...` en TS).
- Contexte : L'étoile accepte tout itérable : liste, tuple, set, générateur, dict (ses clés). Elle permet d'insérer des valeurs au milieu : `[premier, *reste, dernier]`. Dans un appel, `f(*l)` équivaut à `f(l[0], l[1], …)` : le nombre d'éléments doit correspondre aux paramètres. Le résultat est une nouvelle liste, copie superficielle.
- Usage : ✅ assembler des sources de types différents, passer une liste à une fonction à plusieurs paramètres · ❌ ajouter à une liste existante : `extend`.

```python
# Exemple 1 : assembler
hier = ["483609327"]
auj = ("552100554",)   # un tuple
[*hier, *auj, "830024215"]
# → ["483609327", "552100554", "830024215"]
```

```python
# Exemple 2 : déballer dans un appel
def plage(debut, fin):
    return f"{debut} → {fin}"

bornes = ["2026-10-21", "2026-10-23"]
plage(*bornes)
# → "2026-10-21 → 2026-10-23"
```

- Quiz : Que vaut `[*{"siren": "48", "nb": 2}]` ?
- [ ] `["48", 2]`
- [x] `["siren", "nb"]`
- [ ] `[("siren", "48"), ("nb", 2)]`
- [ ] `TypeError`
- Réponse : `["siren", "nb"]` : déballer un dict donne ses clés, comme le parcourir ; pour les paires, `[*d.items()]`.

## 11. Tranches : remplacer et supprimer
- Sous-thème : modifier
- Niveau : 2
- Définition : Affecter une tranche (`l[a:b] = …`) remplace une portion par un itérable ; `del l[a:b]` la supprime (≈ `splice` en JS).
- Contexte : La portion et son remplacement n'ont pas besoin d'avoir la même taille : la liste grandit ou rétrécit. `l[:] = …` remplace tout le contenu en gardant le même objet, ce qui compte quand d'autres variables y font référence. `del l[i]` retire un index, `del l[::2]` un élément sur deux, `l.clear()` vide tout.
- Usage : ✅ retirer une plage de lignes (en-tête, pied de page), vider sur place une liste partagée · ❌ code relu par d'autres : une compréhension qui crée une nouvelle liste est souvent plus claire.

```python
# Exemple 1 : remplacer, supprimer
l = [0, 1, 2, 3, 4]
l[1:3] = ["a"]      # 2 éléments → 1
l                   # → [0, "a", 3, 4]
del l[0]
l                   # → ["a", 3, 4]
```

```python
# Exemple 2 : vider sur place
sirens = ["483609327", "552100554"]
alias = sirens
sirens[:] = []      # même objet, vidé
alias               # → []
sirens is alias     # → True
```

- Quiz : Avec `l = [1, 2, 3]`, que vaut `l` après `l[1] = []` ?
- [ ] `[1, 3]`
- [x] `[1, [], 3]`
- [ ] `TypeError`
- [ ] `[1, 2, 3]`
- Réponse : `[1, [], 3]` : affecter un index remplace l'élément par l'objet donné ; seule une tranche (`l[1:2] = []`) retirerait l'élément.

## 12. Modifier pendant le parcours
- Sous-thème : parcourir
- Niveau : 2
- Définition : Retirer des éléments d'une liste pendant qu'on la parcourt en saute certains, sans erreur : on construit plutôt une nouvelle liste.
- Contexte : La boucle `for` avance un index interne : quand on retire l'élément courant, le suivant glisse à sa place et la boucle passe par-dessus. Aucune exception, contrairement au dict (`RuntimeError`) : le bug est silencieux. Solutions : filtrer par compréhension, parcourir une copie (`for x in l[:]`), ou parcourir à l'envers.
- Usage : ✅ `l = [x for x in l if garder(x)]` pour filtrer · ❌ `l.remove(x)` à l'intérieur de `for x in l`.

```python
# Exemple 1 : un élément sauté
sirens = ["", "", "483609327"]
for s in sirens:
    if not s:
        sirens.remove(s)
sirens   # → ["", "483609327"]  (raté)
```

```python
# Exemple 2 : filtrer sans muter
sirens = ["", "", "483609327"]
sirens = [s for s in sirens if s]
sirens   # → ["483609327"]
```

- Quiz : Avec `l = [1]`, que fait `for x in l: l.append(x)` ?
- [ ] Ajoute `1` une fois, puis s'arrête
- [ ] `RuntimeError`
- [x] Boucle à l'infini
- [ ] `IndexError`
- Réponse : boucle à l'infini : la liste grandit à chaque tour et la boucle n'en atteint jamais la fin ; un dict, lui, lèverait `RuntimeError`.

## 13. any et all : tester tous les éléments
- Sous-thème : parcourir
- Niveau : 2
- Définition : `any(it)` vaut `True` si au moins un élément est vrai, `all(it)` si tous le sont (≈ `some` / `every` en TS).
- Contexte : On leur passe souvent une expression génératrice : `all(len(s) == 9 for s in sirens)`. Elles s'arrêtent dès que le résultat est connu. Sans expression, elles testent la vérité de chaque élément : `0`, `""`, `None` et `[]` sont faux. Elles renvoient un booléen, jamais l'élément trouvé.
- Usage : ✅ valider un lot (tous les SIREN font 9 chiffres ?), détecter un champ manquant · ❌ besoin de l'élément fautif : `next((x for x in l if …), None)`.

```python
# Exemple 1 : valider un lot
sirens = ["483609327", "55210"]
all(len(s) == 9 for s in sirens)
# → False
any(len(s) != 9 for s in sirens)
# → True
```

```python
# Exemple 2 : vérité des éléments
any(["", None, 0])     # → False
all(["A1", "B2"])      # → True
any([[], [0]])         # → True  ([0] non vide)
```

- Quiz : Que vaut `all([])` ?
- [x] `True`
- [ ] `False`
- [ ] `None`
- [ ] `ValueError`
- Réponse : `True` : « tous les éléments sont vrais » est vrai quand il n'y en a aucun ; un lot vide passe la validation, à tester à part.

## 14. zip : avancer en parallèle
- Sous-thème : parcourir
- Niveau : 2
- Définition : `zip(a, b)` parcourt plusieurs séquences en parallèle et donne des tuples `(a[i], b[i])`.
- Contexte : `zip` évite d'indexer deux listes avec le même `i`. Combiné à `dict`, il associe des clés et des valeurs, comme les en-têtes d'un CSV et une ligne. `zip(*paires)` fait l'inverse : il sépare une liste de paires en colonnes. Il renvoie un itérateur, consommé une seule fois.
- Usage : ✅ associer des colonnes (en-têtes et valeurs), comparer deux listes élément par élément · ❌ besoin de l'index : `enumerate`.

```python
# Exemple 1 : en-têtes + valeurs → dict
entetes = ["siren", "ville", "capital"]
valeurs = ["483609327", "Lyon", "5000"]
ligne = dict(zip(entetes, valeurs))
ligne["ville"]          # → "Lyon"
```

```python
# Exemple 2 : en parallèle, puis séparer
codes = ["A1", "B2"]
capitaux = [500, 9000]
for code, cap in zip(codes, capitaux):
    print(code, cap)
# affiché : A1 500
# affiché : B2 9000
paires = [("A1", 500), ("B2", 9000)]
c, k = zip(*paires)
c                       # → ("A1", "B2")
```

- Quiz : Que vaut `list(zip([1, 2, 3], ["a", "b"]))` ?
- [x] `[(1, "a"), (2, "b")]`
- [ ] `[(1, "a"), (2, "b"), (3, None)]`
- [ ] `ValueError`
- [ ] `[(1, "a"), (2, "b"), (3,)]`
- Réponse : `[(1, "a"), (2, "b")]` : `zip` s'arrête à la plus courte, en silence ; `zip(..., strict=True)` lèverait `ValueError`.

## 15. Trier : sorted et key
- Sous-thème : trier
- Niveau : 2
- Définition : `sorted(seq, key=f)` renvoie une nouvelle liste triée selon `f(x)` ; `liste.sort()` trie la liste sur place.
- Contexte : `key` reçoit chaque élément et renvoie la valeur à comparer : pas de comparateur `(a, b) => …` comme en JS. `reverse=True` inverse l'ordre. Le tri est **stable** : à valeur égale, l'ordre d'origine est gardé. Pour plusieurs critères, la clé renvoie un tuple, comparé élément par élément. `min` et `max` acceptent aussi `key`.
- Usage : ✅ ordonner des enregistrements par champ (date, capital), trouver le plus grand avec `max(key=…)` · ❌ garder seulement les N premiers d'un gros volume : `heapq.nlargest`.

```python
# Exemple 1 : trier des dicts par champ
annonces = [{"id": "A1", "capital": 500},
            {"id": "B2", "capital": 9000},
            {"id": "C3", "capital": 1200}]
tries = sorted(annonces, reverse=True,
               key=lambda a: a["capital"])
[a["id"] for a in tries]
# → ["B2", "C3", "A1"]
max(annonces, key=lambda a: a["capital"])["id"]
# → "B2"
```

```python
# Exemple 2 : deux critères avec un tuple
lignes = [("Lyon", 3), ("Paris", 1),
          ("Lyon", 1)]
# ville croissante, puis nombre décroissant
sorted(lignes, key=lambda l: (l[0], -l[1]))
# → [("Lyon", 3), ("Lyon", 1), ("Paris", 1)]
```

- Quiz : Que vaut `[3, 1, 2].sort()` ?
- [ ] `[1, 2, 3]`
- [x] `None`
- [ ] `[3, 1, 2]`
- [ ] `AttributeError`
- Réponse : `None` : `.sort()` trie la liste sur place et ne renvoie rien ; `sorted()` renvoie une nouvelle liste.

## 16. sorted : types mélangés et casse
- Sous-thème : trier
- Niveau : 2
- Définition : `sorted` refuse de comparer des types différents (`TypeError`) et range les chaînes par code Unicode : majuscules avant minuscules.
- Contexte : `Array.sort` de JS convertit tout en chaîne ; Python compare les vraies valeurs et lève `TypeError` sur `int` contre `str`, ou sur `None`. Un champ vide (`None`) au milieu de dates venues d'un JSON fait donc planter le tri. Les chaînes se comparent code par code : `"Z" < "a"`. `key=str.casefold` ignore la casse.
- Usage : ✅ `key=lambda d: d or ""` pour placer les `None` en tête, `key=str.casefold` pour des noms · ❌ trier des nombres stockés en chaînes sans `key=int`.

```python
# Exemple 1 : types mélangés
sorted([3, 1, 2])          # → [1, 2, 3]
sorted(["2026", None])     # ❌ TypeError
dates = ["2026-10-22", None]
sorted(dates, key=lambda d: d or "")
# → [None, "2026-10-22"]
```

```python
# Exemple 2 : la casse
noms = ["martin", "Dupont", "abel"]
sorted(noms)
# → ["Dupont", "abel", "martin"]
sorted(noms, key=str.casefold)
# → ["abel", "Dupont", "martin"]
```

- Quiz : Que vaut `sorted(["Écully", "Lyon", "Arles"])` ?
- [ ] `["Arles", "Écully", "Lyon"]`
- [x] `["Arles", "Lyon", "Écully"]`
- [ ] `["Écully", "Arles", "Lyon"]`
- [ ] `TypeError`
- Réponse : `["Arles", "Lyon", "Écully"]` : `É` a un code Unicode plus grand que toutes les lettres ASCII ; pour un tri à la française, `locale.strxfrm` ou retirer les accents dans la clé.

## 17. reversed et reverse
- Sous-thème : trier
- Niveau : 2
- Définition : `l.reverse()` inverse la liste sur place et renvoie `None` ; `reversed(l)` renvoie un itérateur qui la parcourt à l'envers.
- Contexte : Même logique que `sort` et `sorted` : la méthode mute, la fonction laisse l'original intact. `reversed` ne crée pas de liste : il se consomme une seule fois, comme un générateur. Contrairement à `Array.reverse` en JS, qui mute et renvoie le tableau, `reverse()` renvoie `None` : `l = l.reverse()` perd la liste.
- Usage : ✅ `reversed` pour parcourir du plus récent au plus ancien sans copie, `l[::-1]` pour une copie inversée · ❌ `l = l.reverse()`.

```python
# Exemple 1 : sur place ou itérateur
jours = ["21", "22", "23"]
list(reversed(jours))  # → ["23", "22", "21"]
jours                  # → ["21", "22", "23"]
jours.reverse()        # sur place
jours                  # → ["23", "22", "21"]
```

```python
# Exemple 2 : une seule passe
r = reversed([1, 2, 3])
list(r)    # → [3, 2, 1]
list(r)    # → []  (déjà consommé)
```

- Quiz : Que vaut `reversed([1, 2]) == [2, 1]` ?
- [ ] `True`
- [ ] `TypeError`
- [ ] `None`
- [x] `False`
- Réponse : `False` : `reversed` renvoie un itérateur, qui n'est jamais égal à une liste ; comparer `list(reversed(l))`.

## 18. list[str] : annoter sans contrôler
- Sous-thème : lire
- Niveau : 2
- Définition : `list[str]` annote une liste de chaînes pour l'éditeur et mypy ; Python ne vérifie rien à l'exécution (≈ `string[]`, sans compilateur).
- Contexte : Depuis Python 3.9, on écrit `list[str]` directement, sans `from typing import List`. Les annotations sont ignorées à l'exécution : passer `[1, 2]` à une fonction annotée `list[str]` ne lève rien, l'erreur arrive plus loin. Pour un paramètre seulement lu, `Sequence[str]` accepte aussi un tuple. Valider des données externes demande pydantic.
- Usage : ✅ signatures (`def normaliser(sirens: list[str]) -> list[str]`), retours typés · ❌ compter sur l'annotation pour valider un JSON reçu : pydantic.

```python
# Exemple 1 : annotation, pas contrôle
def compter(sirens: list[str]) -> int:
    return len(sirens)

compter(["483609327"])   # → 1
compter([1, 2, 3])       # → 3  (accepté)
```

```python
# Exemple 2 : l'annotation reste lisible
from collections.abc import Sequence

def premier(s: Sequence[str]) -> str:
    return s[0]

premier(("483609327",))  # → "483609327"
premier.__annotations__["return"]  # → str
```

- Quiz : Que fait `x: list[str] = "483609327"` ?
- [ ] `TypeError`
- [ ] `x` vaut `["483609327"]`
- [x] Rien de spécial : `x` vaut la chaîne
- [ ] `SyntaxError`
- Réponse : rien de spécial, `x` vaut la chaîne : l'annotation n'est qu'une indication, seul un vérificateur (mypy, pyright) signalerait l'erreur.

## 19. Compréhension imbriquée : aplatir
- Sous-thème : construire
- Niveau : 3
- Définition : Plusieurs `for` dans une compréhension s'enchaînent dans l'ordre des boucles écrites : `[x for l in ll for x in l]` aplatit (≈ `flat()`).
- Contexte : On lit les `for` de gauche à droite, comme des boucles imbriquées : le premier est la boucle externe. Les inverser (`for x in l for l in ll`) lève `NameError`. Une compréhension dans une compréhension (`[[…] for …]`) construit une liste de listes, pas une liste aplatie. Au-delà de deux niveaux, `itertools.chain.from_iterable` ou une boucle restent plus lisibles.
- Usage : ✅ aplatir les SIREN de toutes les annonces, produit simple de deux listes · ❌ trois `for` ou plus avec des `if` : boucle explicite.

```python
# Exemple 1 : aplatir
annonces = [{"sirens": ["48", "55"]},
            {"sirens": ["83"]}]
[s for a in annonces
   for s in a["sirens"]]
# → ["48", "55", "83"]
```

```python
# Exemple 2 : aplatir ou matrice
from itertools import chain

ll = [[1, 2], [3]]
[x for l in ll for x in l]   # → [1, 2, 3]
[[x * 10 for x in l] for l in ll]
# → [[10, 20], [30]]
list(chain.from_iterable(ll))  # → [1, 2, 3]
```

- Quiz : Que vaut `[(i, j) for i in range(3) for j in range(i)]` ?
- [ ] `[(0, 0), (1, 1), (2, 2)]`
- [ ] `[(0, 1), (0, 2), (1, 2)]`
- [x] `[(1, 0), (2, 0), (2, 1)]`
- [ ] `NameError`
- Réponse : `[(1, 0), (2, 0), (2, 1)]` : `i` est la boucle externe ; pour `i = 0`, `range(0)` est vide, et le second `for` peut lire `i`.

## 20. Compréhension : sa propre portée
- Sous-thème : construire
- Niveau : 3
- Définition : La variable d'une compréhension n'existe que dedans, alors que celle d'une boucle `for` reste définie après la boucle.
- Contexte : Une boucle `for` ne crée pas de portée en Python : après `for s in sirens`, `s` vaut le dernier élément (≈ un `var`, pas un `let`). Une compréhension a sa propre portée : sa variable ne fuit pas et n'écrase pas une variable de même nom. Lire la variable d'une boucle après coup est fragile : si la liste était vide, elle n'a jamais été créée.
- Usage : ✅ compréhension pour ne pas polluer la portée · ❌ lire la variable de boucle pour obtenir « le dernier élément » : `l[-1]`.

```python
# Exemple 1 : for fuit, la compréhension non
for s in ["483609327", "552100554"]:
    pass
s        # → "552100554"  (toujours là)
[c for c in "ab"]
c        # ❌ NameError
```

```python
# Exemple 2 : pas d'écrasement
x = "garde"
carres = [x * x for x in range(3)]
x        # → "garde"
carres   # → [0, 1, 4]
```

- Quiz : Sans définition préalable de `s`, que fait `for s in []: pass` puis `print(s)` ?
- [ ] Affiche `None`
- [ ] Affiche une ligne vide
- [x] `NameError`
- [ ] `IndexError`
- Réponse : `NameError` : la boucle n'a jamais tourné, donc `s` n'a jamais été affectée ; Python ne déclare pas les variables à l'avance.

## 21. deque : ajouter et retirer en tête
- Sous-thème : modifier
- Niveau : 3
- Définition : `collections.deque` ajoute et retire aux deux bouts en temps constant, là où `insert(0, x)` et `pop(0)` d'une liste recopient tout.
- Contexte : Une `list` est un tableau contigu : retirer le premier élément décale tous les autres, en temps linéaire. Sur une file de 100 000 annonces, `pop(0)` en boucle devient quadratique. `deque` offre `appendleft` et `popleft` en O(1), et `maxlen` en fait un tampon qui garde les N derniers éléments. L'accès par index au milieu y est lent.
- Usage : ✅ file d'attente (pages à traiter), N dernières lignes d'un log · ❌ accès par index ou tranches : `list` ; file partagée entre threads : `queue.Queue`.

```python
# Exemple 1 : une file FIFO
from collections import deque
file = deque(["p1", "p2"])
file.append("p3")      # en queue
file.popleft()         # → "p1"  (O(1))
list(file)             # → ["p2", "p3"]
```

```python
# Exemple 2 : les N derniers
from collections import deque
derniers = deque(maxlen=2)
for l in ["l1", "l2", "l3"]:
    derniers.append(l)
list(derniers)         # → ["l2", "l3"]
```

- Quiz : Avec `d = deque([1, 2], maxlen=2)`, que vaut `list(d)` après `d.appendleft(0)` ?
- [ ] `[1, 2]`
- [x] `[0, 1]`
- [ ] `[0, 1, 2]`
- [ ] `IndexError`
- Réponse : `[0, 1]` : une deque pleine jette l'élément du côté opposé à l'ajout ; ici, le `2` à droite.
