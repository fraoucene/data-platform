---
title: "Cours · Python : list, tuple, dict, set"
learning_id: cours-python-collections
type: cours
related: s1-06
created: 2026-10-23
updated: 2026-10-23
---

# Cours · Python : list, tuple, dict, set
Fiche de référence née pendant S1-06 (lecture de `packages/bodacc-client/src/bodacc_client/models.py`). Exemples tirés du contexte BODACC, avec l'équivalent TypeScript à chaque fois.

## Objectif
Savoir choisir la bonne collection Python, créer, lire, modifier et parcourir chacune, et reconnaître les pièges de syntaxe (`{}`, tuple à un élément). Pourquoi ça compte dans le projet : un client d'ingestion manipule en permanence des suites d'annonces (`list`), des constantes de config (`tuple`), des objets JSON (`dict`) et du dédoublonnage (`set`). Le mauvais choix donne soit des bugs (constante modifiée par erreur), soit des perfs dégradées (recherche linéaire dans une liste de 100 000 ids).

## Vue d'ensemble
| Python | Syntaxe | Mutable | Équivalent TS | Rôle |
|---|---|---|---|---|
| `list` | `["a", "b"]` | oui | `string[]` | suite ordonnée |
| `tuple` | `("a", "b")` | **non** | `readonly string[]` / `as const` | suite ordonnée figée |
| `dict` | `{"a": 1}` | oui | `Map` / `Record` | clé → valeur |
| `set` | `{"a", "b"}` | oui | `Set` | valeurs uniques, sans ordre |

À retenir :
- `list` et `tuple` sont deux listes ; la seule différence est que le tuple est en lecture seule.
- `dict` et `set` ne sont pas « la même chose en mutable / immutable » : ce sont deux structures différentes, toutes les deux mutables. Le `dict` est la vraie map (clé → valeur) ; le `set` n'a que des valeurs, uniques.
- Versions immutables : `tuple` pour `list`, `frozenset` pour `set`. Pas d'équivalent simple en standard pour `dict`.

## list — suite ordonnée, modifiable
### Lire
```python
sirens = ["123456789", "987654321", "555555555"]

sirens[0]                  # "123456789"   (arr[0])
sirens[-1]                 # "555555555"   (arr.at(-1))
sirens[0:2]                # ["123456789", "987654321"]   (arr.slice(0, 2))
len(sirens)                # 3             (arr.length)
"987654321" in sirens      # True          (arr.includes())
sirens.index("987654321")  # 1             (arr.indexOf(), mais ValueError si absent)
```

### Modifier
```python
sirens.append("111111111")     # ajoute à la fin          (push)
sirens.extend(["222", "333"])  # ajoute plusieurs          (push(...arr))
sirens.insert(0, "000000000")  # insère à l'index 0        (splice)
sirens.pop()                   # retire et renvoie le dernier (pop)
sirens.remove("222")           # retire la 1re occurrence de cette valeur
sirens.sort()                  # trie sur place
sirens.reverse()               # inverse sur place
sirens.clear()                 # vide
```

### Parcourir et transformer
```python
for s in sirens: ...
for i, s in enumerate(sirens): ...             # index + valeur (forEach((s, i) => …))
valides = [s for s in sirens if len(s) == 9]   # list comprehension = filter
longueurs = [len(s) for s in sirens]           # = map
```

### Cas d'usage : accumuler les annonces d'une pagination
```python
annonces = []
for page in pages:
    annonces.extend(page["results"])
```

## tuple — suite ordonnée, en lecture seule
### Lire
```python
NESTED_JSON_FIELDS = ("acte", "depot", "jugement")
point = (48.85, 2.35)

NESTED_JSON_FIELDS[0]            # "acte"
len(point)                       # 2
"depot" in NESTED_JSON_FIELDS    # True
NESTED_JSON_FIELDS.count("acte") # 1   (une des 2 seules méthodes)
NESTED_JSON_FIELDS.index("depot")# 1
```

### Unpacking (destructuring)
```python
lat, lon = point   # const [lat, lon] = point
```

### Modifier : impossible
```python
NESTED_JSON_FIELDS.append("x")   # AttributeError
NESTED_JSON_FIELDS[0] = "x"      # TypeError
```

### Cas d'usage
- Constante de config, comme `NESTED_JSON_FIELDS` dans `models.py` : la liste des champs ne doit pas changer à l'exécution. Le nom en MAJUSCULES est la convention Python pour une constante ; le tuple renforce l'intention.
- Renvoyer plusieurs valeurs depuis une fonction :
```python
def fetch_page(offset: int) -> tuple[list[dict], int]:
    ...
    return results, total_count

results, total = fetch_page(0)
```

### Pièges
```python
("acte")    # str, pas un tuple : les parenthèses seules ne font qu'un groupement
("acte",)   # tuple à 1 élément : c'est la virgule qui crée le tuple
```
La virgule finale après le dernier élément d'un tuple multi-ligne est facultative : c'est une convention de formatage (ruff/black) qui garde des diffs git propres.

## dict — clé → valeur (la map)
### Lire
```python
annonce = {"id": "A2026-001", "typeavis": "annonce", "tribunal": "Paris"}

annonce["id"]                     # "A2026-001", mais KeyError si la clé est absente
annonce.get("commercant")         # None si absente, sans erreur (≈ obj?.commercant)
annonce.get("commercant", "N/A")  # valeur par défaut (?? "N/A")
"tribunal" in annonce             # True : teste la CLÉ (≈ "tribunal" in obj)
len(annonce)                      # 3
```

### Modifier
```python
annonce["siren"] = "123456789"     # ajoute ou écrase
annonce.update({"a": 1, "b": 2})   # fusionne ({...obj, a: 1, b: 2})
annonce.pop("tribunal")            # retire et renvoie la valeur
annonce.setdefault("registre", []) # crée la clé seulement si elle est absente
del annonce["a"]                   # supprime (delete obj.a)
```

### Parcourir et transformer
```python
annonce.keys()     # Object.keys()
annonce.values()   # Object.values()
annonce.items()    # Object.entries()
for cle, valeur in annonce.items(): ...

{k: v for k, v in annonce.items() if v is not None}   # dict comprehension : retire les None
```

### Cas d'usage : compter les annonces par famille d'avis
```python
par_famille: dict[str, int] = {}
for a in annonces:
    famille = a["familleavis"]
    par_famille[famille] = par_famille.get(famille, 0) + 1
# {"creation": 120, "radiation": 45, ...}
```

## set — valeurs uniques, sans ordre
### Lire
```python
vus = {"123456789", "987654321"}

"123456789" in vus   # True, très rapide même sur des millions d'éléments
len(vus)             # 2
for s in vus: ...    # ordre non garanti
vus[0]               # TypeError : pas d'index
```

### Modifier
```python
vus.add("555555555")    # ajoute (ignoré si déjà présent)
vus.update(["a", "b"])  # ajoute plusieurs
vus.remove("a")         # KeyError si absent
vus.discard("zzz")      # retire sans erreur si absent
vus.pop()               # retire un élément arbitraire
```

### Opérations ensemblistes
```python
a = {"1", "2", "3"}
b = {"2", "3", "4"}
a | b   # union          {"1", "2", "3", "4"}
a & b   # intersection   {"2", "3"}
a - b   # différence     {"1"}
a ^ b   # dans un seul des deux {"1", "4"}
```

### Cas d'usage : dédoublonner les annonces de plusieurs pages
```python
ids_vus: set[str] = set()
uniques = []
for a in annonces:
    if a["id"] in ids_vus:
        continue
    ids_vus.add(a["id"])
    uniques.append(a)
```
Dédoublonnage rapide d'une liste : `list(set(sirens))`, au prix de la perte de l'ordre.

Pourquoi un `set` plutôt qu'une `list` pour « déjà vu ? » : `x in liste` parcourt toute la liste (O(n)) ; `x in set` est une recherche par hash (O(1)). Sur 100 000 annonces, l'écart est énorme.

### Piège : `{}` sert aux deux
```python
{"a": 1}   # dict (il y a des ":")
{"a"}      # set
{}         # dict vide, pas un set vide → set()
```

## Quel type choisir
| Besoin | Type |
|---|---|
| collection ordonnée qui grossit | `list` |
| valeurs fixes, ou plusieurs valeurs en retour de fonction | `tuple` |
| accès par clé, objet JSON | `dict` |
| unicité, test « déjà vu ? » | `set` |

Conversions par le constructeur : `list(t)`, `tuple(l)`, `set(l)`, `dict(liste_de_paires)`.
