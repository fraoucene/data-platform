---
title: "Cartes · Texte et nombres Python"
type: cartes
langage: Python
chapitre: Bases du langage
cours: Texte et nombres
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Texte et nombres Python
Python · Texte et nombres : nombres, texte (format spec v3 de revision-pwa).

## 1. SIREN : chaîne, pas entier
- Id : texte-nombres-siren-chaine
- Sous-thème : texte
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Voir aussi : validation-annotated-type
- Définition : Un identifiant (SIREN, code postal) se garde en `str` : un `int` perd les zéros de tête et autorise des calculs absurdes.
- Contexte : Un SIREN qui commence par 0 perd ce chiffre en `int` ; `zfill(9)` le rétablit. CSV et JSON ne décident rien : le type se fixe à la lecture, et le garder en `str` évite aussi qu'un outil le transforme en float (`1.2345678e7`). Pour contrôler le format, `isdigit()` plus la longueur suffisent.
- Usage : ✅ SIREN, SIRET, code postal, numéro d'annonce · ❌ vraie quantité sur laquelle on calcule (montant, nombre d'annonces) : `int`, `Decimal`.

```python
# Exemple 1 : le zéro de tête
s = "012345678"
int(s)                # → 12345678
str(int(s))           # → "12345678"
str(int(s)).zfill(9)  # → "012345678"
```

```python
# Exemple 2 : valider un SIREN
def siren_ok(s):
    return s.isdigit() and len(s) == 9

siren_ok("483609327")   # → True
siren_ok("48360932")    # → False
siren_ok("48360932A")   # → False
```

- Quiz : Que fait `int("483 609 327")` ?
- [ ] Renvoie `483609327`
- [ ] Renvoie `483`
- [ ] `TypeError`
- [x] `ValueError`
- Réponse : `ValueError` : `int` tolère les blancs autour, pas les espaces internes ; nettoyer avec `s.replace(" ", "")` avant.

## 2. split : avec ou sans argument
- Id : texte-nombres-split-separateur
- Sous-thème : texte
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Voir aussi : json-split-ou-splitlines
- Définition : `split()` sans argument coupe sur tout blanc et ignore les blancs en trop ; `split(" ")` coupe sur chaque espace.
- Contexte : Sans argument, `split` retire aussi les blancs de début et de fin et traite tabulations et retours à la ligne comme des espaces. Avec un séparateur explicite, rien n'est fusionné. `maxsplit` limite le nombre de coupes. Pour recoller, `join` est une méthode du séparateur, pas de la liste : `" ".join(l)` (≈ `l.join(" ")` en JS).
- Usage : ✅ `split()` pour normaliser des libellés saisis à la main, `split(";", 1)` pour séparer un préfixe · ❌ découper un CSV : le module `csv` (guillemets).

```python
# Exemple 1 : normaliser les blancs
s = "  SARL   Dupont "
s.split()        # → ["SARL", "Dupont"]
" ".join(s.split())  # → "SARL Dupont"
"a\tb\nc".split()    # → ["a", "b", "c"]
```

```python
# Exemple 2 : couper une seule fois
v = "75001 Paris 1er"
v.split(" ", 1)
# → ["75001", "Paris 1er"]
cp, ville = v.split(" ", 1)
ville             # → "Paris 1er"
```

- Quiz : Que vaut `" a  b ".split(" ")` ?
- [ ] `["a", "b"]`
- [x] `["", "a", "", "b", ""]`
- [ ] `["a", "", "b"]`
- [ ] `["", "a", "b", ""]`
- Réponse : `["", "a", "", "b", ""]` : avec un séparateur explicite, chaque espace coupe et les cases vides restent (comme `split(" ")` en JS).

## 3. casefold : ignorer la casse
- Id : texte-nombres-casefold
- Sous-thème : texte
- Type : concept
- Niveau : 2
- Profils : data
- Voir aussi : texte-nombres-unicode-nfc
- Définition : `casefold` met en minuscules de façon agressive pour comparer sans tenir compte de la casse ; plus fiable que `lower` hors ASCII.
- Contexte : `lower` suffit en ASCII, mais certaines lettres ont une forme de comparaison différente de leur minuscule (`ß` → `ss`). `casefold` sert à comparer ou indexer, pas à afficher. Il ne retire pas les accents : « Créteil » et « CRETEIL » restent différents, il faut en plus une normalisation Unicode. Équivalent JS le plus proche : `localeCompare` avec `sensitivity`.
- Usage : ✅ dédoublonner des villes ou des raisons sociales, chercher sans casse · ❌ texte à afficher : `lower` ou `title` ; ignorer les accents : `unicodedata` en plus.

```python
# Exemple 1 : comparer sans casse
v = "LYON"
v.casefold() == "lyon"    # → True
"ß".casefold()            # → "ss"
```

```python
# Exemple 2 : dédoublonner
villes = ["Lyon", "LYON", "lyon",
          "Créteil", "CRETEIL"]
{v.casefold() for v in villes}
# → {"lyon", "créteil", "creteil"}
```

- Quiz : Que vaut `"straße".lower() == "STRASSE".lower()` ?
- [x] `False`
- [ ] `True`
- [ ] `TypeError`
- Réponse : `False` : `lower` garde `ß`, seul `casefold` le transforme en `ss` ; `casefold` des deux côtés renvoie `True`.

## 4. Decimal : les montants
- Id : texte-nombres-decimal-montants
- Sous-thème : nombres
- Type : choisir
- Niveau : 2
- Profils : data, web
- Voir aussi : json-parse-float-decimal, texte-nombres-round-au-pair
- Définition : `Decimal` représente un nombre décimal exact, indispensable pour les montants là où `float` cumule des erreurs binaires.
- Contexte : `Decimal` calcule en base 10 avec une précision réglable (28 chiffres par défaut). `quantize(Decimal("0.01"), ROUND_HALF_UP)` arrondit au centime de façon commerciale. Mélanger `Decimal` et `float` dans une opération lève `TypeError`, et `json` ne sérialise pas `Decimal` sans `default`. JS n'a rien de natif : on y passe par des centimes entiers ou une bibliothèque.
- Usage : ✅ capital social, montants de créances, tout calcul comptable · ❌ mesures physiques ou statistiques : `float`, plus rapide, l'erreur y est acceptable.

```python
# Exemple 1 : float contre Decimal
from decimal import Decimal

0.1 + 0.2 == 0.3          # → False
a = Decimal("0.1") + Decimal("0.2")
a == Decimal("0.3")       # → True
```

```python
# Exemple 2 : arrondir au centime
from decimal import Decimal, ROUND_HALF_UP

c = Decimal("0.01")
m = Decimal("2.675")
m.quantize(c, ROUND_HALF_UP)
# → Decimal("2.68")
m + 0.1     # ❌ TypeError
```

- Quiz : Que vaut `Decimal(0.1) == Decimal("0.1")` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : `Decimal(0.1)` reprend le float déjà imprécis (`0.1000000000000000055…`) ; toujours construire depuis une chaîne.

## 5. round : l'arrondi bancaire
- Id : texte-nombres-round-au-pair
- Sous-thème : nombres
- Type : piège
- Niveau : 2
- Profils : data
- Voir aussi : texte-nombres-decimal-montants
- Définition : `round` arrondit au pair le plus proche sur les cas `.5` (arrondi bancaire), pas toujours vers le haut comme `Math.round`.
- Contexte : L'arrondi au pair évite le biais vers le haut quand on arrondit de grandes séries ; c'est le mode par défaut de la norme IEEE 754. `round(x)` renvoie un `int`, `round(x, 2)` un `float`. Avec des décimales, les cas « .5 » sont en plus faussés par la représentation binaire : le float stocké n'est pas exactement la valeur écrite.
- Usage : ✅ arrondir une moyenne ou un indicateur affiché · ❌ montant facturé ou déclaré : `Decimal.quantize` avec `ROUND_HALF_UP`.

```python
# Exemple 1 : au pair le plus proche
round(1.5)    # → 2
round(2.5)    # → 2
round(3.5)    # → 4
```

```python
# Exemple 2 : type du résultat
type(round(2.5))       # → int
type(round(2.567, 2))  # → float
round(2.567, 2)        # → 2.57
round(1234, -2)        # → 1200
```

- Quiz : Que vaut `round(2.675, 2)` ?
- [ ] `2.68`
- [ ] `2.7`
- [x] `2.67`
- Réponse : `2.67` : le float `2.675` vaut en réalité `2.67499…`, arrondi vers le bas ; pour un arrondi commercial, `Decimal.quantize`.
## 6. Unicode : normaliser avant de comparer
- Id : texte-nombres-unicode-nfc
- Sous-thème : texte
- Type : piège
- Niveau : 3
- Profils : data, expert
- Définition : `unicodedata.normalize("NFC", s)` unifie les formes d'un même caractère accentué, pour comparer ou dédoublonner des libellés.
- Contexte : Un « é » peut être un seul point de code (U+00E9, forme NFC) ou « e » suivi d'un accent combinant (U+0301, forme NFD), selon la source : macOS, copier-coller depuis un PDF. Visuellement identiques, ils diffèrent pour `==`, `in`, les clés de dict et les jointures. Normaliser en NFC à l'ingestion ; NFD puis retrait des combinants supprime les accents.
- Usage : ✅ libellés de tribunaux, communes, raisons sociales venant de plusieurs sources · ❌ identifiants purement ASCII (SIREN, codes) : inutile.

```python
# Exemple 1 : deux « é » différents
import unicodedata

a = "Créteil"
b = "Créteil"   # e + accent
a == b                # → False
nfc = unicodedata.normalize("NFC", b)
nfc == a              # → True
```

```python
# Exemple 2 : retirer les accents
import unicodedata

def sans_accent(s):
    d = unicodedata.normalize("NFD", s)
    return "".join(
        c for c in d
        if not unicodedata.combining(c))

sans_accent("Créteil")  # → "Creteil"
```

- Quiz : Avec `b = "Créteil"`, que vaut `len(b)` ?
- [x] `8`
- [ ] `7`
- [ ] `9`
- Réponse : `8` : l'accent combinant compte comme un caractère à part, alors que `len("Créteil")` en NFC vaut `7`.
