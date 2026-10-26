---
title: "Cartes · Unicode Python"
type: cartes
langage: Python
chapitre: Bases du langage
cours: Unicode
created: 2026-10-26
updated: 2026-10-26
---

# Cartes · Unicode Python
Python · Unicode : caractères, normalisation, casse, accents (format spec v4 de revision-pwa).

## 1. ord et hex : voir les points de code
- Id : unicode-voir-points-de-code
- Sous-thème : caractères
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Voir aussi : texte-nombres-unicode-nfc
- Mots-clés : point de code, Unicode, caractère combinant
- Source : revision-pwa · pwa-parcours
- Définition : `[hex(ord(c)) for c in s]` liste les points de code d'une chaîne : la seule façon de voir deux textes identiques à l'écran mais différents.
- Contexte : Un `print` affiche des glyphes, pas ce qu'il y a dedans : « é » précomposé et « e » suivi d'un accent combinant s'affichent pareil. `ord` donne le numéro Unicode d'un caractère, `ascii(s)` échappe tout ce qui n'est pas ASCII, `unicodedata.name` nomme chaque caractère. En JS : `[...s].map(c => c.codePointAt(0).toString(16))`.
- Usage : ✅ comprendre pourquoi `==` échoue sur deux libellés « identiques », un doublon qui résiste à la déduplication · ❌ contrôle en production : normaliser plutôt que d'inspecter.

```python
# Exemple 1 : deux « é » à l'œil identiques
a = "é"
b = "é"   # e + accent combinant
[hex(ord(c)) for c in a]  # → ["0xe9"]
[hex(ord(c)) for c in b]
# → ["0x65", "0x301"]
```

```python
# Exemple 2 : nommer l'intrus
import unicodedata

s = "Créteil"
ascii(s)   # → "'Cre\\u0301teil'"
unicodedata.name(s[3])
# → "COMBINING ACUTE ACCENT"
```

- Quiz : Que vaut `hex(ord("É"))` ?
- [ ] `"0xe9"`
- [ ] `"0xc3"`
- [x] `"0xc9"`
- [ ] `"0x45"`
- Réponse : `"0xc9"` : le point de code de « É » (U+00C9) ; `0xc3` est le premier octet de son encodage UTF-8 (`c3 89`), `0xe9` la minuscule.

## 2. len : des points de code, pas des glyphes
- Id : unicode-len-points-de-code
- Sous-thème : caractères
- Type : comparaison
- Niveau : 1
- Profils : débutant, data, web
- Prérequis : unicode-voir-points-de-code
- Mots-clés : point de code, UTF-16, caractère combinant
- Source : revision-pwa · pwa-parcours
- Définition : `len(s)` compte les points de code ; `s.length` en JS compte les unités UTF-16 : un emoji vaut 1 en Python, 2 en JS.
- Contexte : Aucun des deux ne compte ce que l'œil voit : un accent combinant ou un modificateur de teinte d'emoji est un point de code de plus. Une limite « 25 caractères » vérifiée en Python et en TS peut donc donner deux verdicts différents. En JS, `[...s].length` compte les points de code comme Python.
- Usage : ✅ `len` pour une limite de stockage en points de code, après normalisation NFC · ❌ limite affichée à l'utilisateur (« 25 caractères ») : compter les graphèmes (`Intl.Segmenter` en JS, module `regex` et `\X` en Python).

```python
# Exemple 1 : ce que compte len
len("Créteil")        # → 7
len("Créteil")  # → 8
len("😀")             # → 1
len("😀".encode())    # → 4
```

```ts
// Exemple 2 : le même texte en TS
"😀".length         // → 2 (UTF-16)
Array.from("😀").length  // → 1 (points de code)
```

- Quiz : Que vaut `len("👍🏽")` (pouce avec teinte de peau) en Python ?
- [ ] `1`
- [x] `2`
- [ ] `4`
- [ ] `8`
- Réponse : `2` : le pouce et le modificateur de teinte sont deux points de code affichés comme un seul glyphe ; JS répondrait `4` (deux paires UTF-16).

## 3. Unicode : normaliser avant de comparer
- Id : texte-nombres-unicode-nfc
- Sous-thème : normalisation
- Type : piège
- Niveau : 2
- Profils : data, expert
- Prérequis : unicode-voir-points-de-code
- Mots-clés : point de code, Unicode, ingestion
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

## 4. casefold : ignorer la casse
- Id : texte-nombres-casefold
- Sous-thème : casse
- Type : concept
- Niveau : 2
- Profils : data
- Voir aussi : texte-nombres-unicode-nfc
- Mots-clés : ASCII, Unicode, normalisation Unicode
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

## 5. NFKC : la forme de compatibilité
- Id : unicode-nfkc-compatibilite
- Sous-thème : normalisation
- Type : concept
- Niveau : 2
- Profils : data, expert
- Prérequis : texte-nombres-unicode-nfc
- Mots-clés : normalisation Unicode, espace insécable
- Source : revision-pwa · pwa-parcours
- Définition : `normalize("NFKC", s)` ramène aussi les variantes de présentation à leur forme simple : `ﬁ` → `fi`, `²` → `2`.
- Contexte : NFC ne touche qu'aux accents ; le K (compatibilité) ramène aussi chiffres pleine chasse, exposants, ligatures de PDF et espace insécable à leur forme ordinaire. C'est une perte de sens assumée : « m² » devient « m2 ». On s'en sert pour une clé de recherche ou un identifiant saisi, jamais pour stocker le texte affiché.
- Usage : ✅ texte extrait d'un PDF (ligatures), saisie d'identifiants (chiffres pleine chasse), clé de recherche · ❌ libellé conservé pour l'affichage : NFC, qui ne change pas le sens.

```python
# Exemple 1 : NFC ne suffit pas
import unicodedata as u

u.normalize("NFC", "ﬁchier")   # → "ﬁchier"
u.normalize("NFKC", "ﬁchier")  # → "fichier"
u.normalize("NFKC", "m²")      # → "m2"
```

```python
# Exemple 2 : saisies venues d'ailleurs
import unicodedata as u

u.normalize("NFKC", "１２３")    # → "123"
u.normalize("NFKC", "a b")  # → "a b"
```

- Quiz : Que vaut `unicodedata.normalize("NFKC", "Ⅻ")` (chiffre romain en un seul caractère) ?
- [ ] `"Ⅻ"`
- [ ] `"12"`
- [x] `"XII"`
- [ ] `"X"`
- Réponse : `"XII"` : la compatibilité décompose le symbole en lettres latines, sans en calculer la valeur ; NFC le garderait tel quel.

## 6. œ, ø, ł, ß : pas d'accent à retirer
- Id : unicode-lettres-sans-decomposition
- Sous-thème : accents
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : texte-nombres-unicode-nfc
- Mots-clés : normalisation Unicode, caractère combinant, ASCII
- Source : revision-pwa · pwa-parcours
- Définition : NFD ne décompose que « lettre + accent » : `œ`, `æ`, `ø`, `ł`, `ß` sont des lettres à part, intactes après retrait des combinants.
- Contexte : Le retrait d'accents par NFD donne « Łodz » pour « Łódź » : le `ó` perd son accent, le `Ł` non. L'astuce répandue `encode("ascii", "ignore")` est pire : elle supprime ces lettres sans rien dire (« Cœur » → « Cur »). Pour une vraie translittération : une table explicite (`str.maketrans`) ou la bibliothèque `unidecode`.
- Usage : ✅ table `maketrans` pour les quelques lettres du corpus (œ, æ, ß), après NFD · ❌ `encode("ascii", "ignore")` sur des noms de personnes ou de communes : lettres perdues.

```python
# Exemple 1 : ce que NFD laisse
import unicodedata as u

def sans_accent(s):
    d = u.normalize("NFD", s)
    return "".join(c for c in d
                   if not u.combining(c))

sans_accent("Cœur à Łódź")
# → "Cœur a Łodz"
```

```python
# Exemple 2 : ascii ignore efface
import unicodedata as u

d = u.normalize("NFD", "Cœur")
d.encode("ascii", "ignore")  # → b"Cur"
t = str.maketrans({"œ": "oe", "ł": "l"})
"Cœur".translate(t)          # → "Coeur"
```

- Quiz : Avec la fonction `sans_accent` ci-dessus, que vaut `sans_accent("Straße")` ?
- [ ] `"Strasse"`
- [x] `"Straße"`
- [ ] `"Strae"`
- [ ] `"Strabe"`
- Réponse : `"Straße"` : `ß` n'a pas de décomposition, il n'y a aucun combinant à retirer ; c'est `casefold` qui le change en `ss`.

## 7. clé de recherche : casse, accents, espaces
- Id : unicode-cle-de-recherche
- Sous-thème : accents
- Type : recette
- Niveau : 2
- Profils : data, web
- Prérequis : texte-nombres-unicode-nfc, texte-nombres-casefold
- Voir aussi : unicode-garder-original, Data engineering/gouvernance-index-alias
- Mots-clés : normalisation Unicode, caractère combinant
- Source : revision-pwa · pwa-parcours
- Définition : Une clé de recherche ramène toutes les écritures d'un mot à une seule chaîne : `casefold`, NFD, retrait des combinants, espaces réduits.
- Contexte : C'est ce que fait `termKey` dans revision-pwa pour retrouver « Rôle IAM » quand une carte écrit « role iam ». L'ordre compte : NFD **avant** de filtrer les combinants, sinon un « é » précomposé n'a rien à filtrer. La clé sert à comparer et à indexer ; elle ne remplace jamais le texte d'origine.
- Usage : ✅ index d'un glossaire, dédoublonnage de communes ou de raisons sociales, recherche tolérante · ❌ identifiant exact (SIREN, Id de carte) : comparer tel quel.

```python
# Exemple 1 : la clé
import unicodedata as u

def cle(s):
    d = u.normalize("NFD", s.casefold())
    s = "".join(c for c in d
                if not u.combining(c))
    return " ".join(s.split())

cle("  Rôle   IAM ")  # → "role iam"
cle("ROLE iam")       # → "role iam"
```

```python
# Exemple 2 : dédoublonner des communes
import unicodedata as u

def cle(s):
    d = u.normalize("NFD", s.casefold())
    s = "".join(c for c in d
                if not u.combining(c))
    return " ".join(s.split())

villes = ["Créteil", "CRETEIL", "créteil "]
{cle(v) for v in villes}  # → {"creteil"}
```

- Quiz : On filtre les combinants **puis** on applique NFD : que devient « Créteil » (é précomposé) ?
- [ ] `"Creteil"`
- [ ] `"Crteil"`
- [x] Toujours accentué
- [ ] `ValueError`
- Réponse : toujours accentué (mesuré) : avant NFD, « é » est un seul point de code non combinant, rien n'est filtré ; NFD le décompose ensuite, trop tard.

## 8. clé et original : comparer l'une, afficher l'autre
- Id : unicode-garder-original
- Sous-thème : normalisation
- Type : concept
- Niveau : 2
- Profils : data, web
- Prérequis : unicode-cle-de-recherche
- Mots-clés : clé de recherche
- Source : revision-pwa · pwa-parcours
- Définition : On indexe par la clé normalisée mais on garde le texte d'origine : la clé sert à retrouver, l'original à afficher.
- Contexte : Une clé sans casse ni accents est une projection à sens unique : de « creteil » on ne retrouve pas « Créteil ». Stocker la clé à la place du libellé détruit l'information. Le motif : un `dict` clé → entrée d'origine (c'est l'index du glossaire de l'app : clé de chaque alias → le terme complet). Côté stockage, l'original se garde en NFC.
- Usage : ✅ `index[cle(v)] = v`, colonne `nom` + colonne `nom_cle` dans une table · ❌ remplacer `nom` par `cle(nom)` « pour simplifier » : affichage et export abîmés.

```python
# Exemple 1 : la clé retrouve, l'original s'affiche
import unicodedata as u

def cle(s):
    d = u.normalize("NFD", s.casefold())
    return "".join(c for c in d
                   if not u.combining(c))

index = {}
for v in ["Créteil", "CRETEIL", "Évry"]:
    index.setdefault(cle(v), v)
index["evry"]   # → "Évry"
index[cle("créteil")]  # → "Créteil"
```

- Quiz : On n'a stocké que `cle(nom)`, soit `"saint-etienne"`. Comment réafficher « Saint-Étienne » ?
- [ ] `unicodedata.normalize("NFC", …)`
- [ ] `.title()` puis NFC
- [x] Impossible : l'information est perdue
- [ ] Recomposer avec NFD inverse
- Réponse : impossible : casse et accents ont été retirés, aucune normalisation ne les invente ; `.title()` donnerait « Saint-Etienne ».

## 9. espace insécable : invisible, pas égal
- Id : unicode-espace-insecable
- Sous-thème : caractères
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : unicode-voir-points-de-code
- Voir aussi : texte-nombres-split-separateur
- Mots-clés : espace insécable, point de code, CSV
- Source : revision-pwa · pwa-parcours
- Définition : Les espaces insécable (U+00A0) et fine (U+202F) ressemblent à une espace sans lui être égales ; `split()` sans argument les traite en blancs.
- Contexte : Le français en met partout (« 12 000 », « Créteil : »), et les copier-coller depuis un PDF ou une page web les ramènent. `==`, `in`, `replace(" ", …)` et `int()` butent dessus. `" ".join(s.split())` ramène tous les blancs Unicode à une espace ordinaire ; `\s` des regex Python et JS les reconnaît aussi.
- Usage : ✅ `" ".join(s.split())` dans toute clé de comparaison, nettoyage des montants avant `int` · ❌ `s.replace(" ", "")` pour nettoyer un nombre : l'insécable reste.

```python
# Exemple 1 : égal à l'œil, pas pour ==
s = "Créteil Val"
s == "Créteil Val"     # → False
s.split()              # → ["Créteil", "Val"]
" ".join(s.split())    # → "Créteil Val"
```

```python
# Exemple 2 : un montant à la française
m = "12 000"         # espace fine
m.replace(" ", "")        # → "12 000"
int("".join(m.split()))   # → 12000
```

- Quiz : Que vaut `"Créteil Val".split(" ")` ?
- [ ] `["Créteil", "Val"]`
- [x] `["Créteil\xa0Val"]`
- [ ] `["Créteil", "", "Val"]`
- [ ] `ValueError`
- Réponse : `["Créteil\xa0Val"]` (un seul élément) : avec un séparateur explicite, seule l'espace ordinaire U+0020 coupe ; sans argument, `split` aurait coupé.

## 10. \w : les lettres accentuées en Python, pas en JS
- Id : unicode-regex-w-lettres
- Sous-thème : caractères
- Type : comparaison
- Niveau : 2
- Profils : data, web
- Mots-clés : regex, Unicode, ASCII
- Source : revision-pwa · pwa-parcours
- Définition : En Python, `\w` reconnaît toute lettre Unicode (« é ») ; en JS, `\w` reste ASCII même avec le drapeau `u` : il faut `\p{L}`.
- Contexte : Python applique les classes Unicode par défaut sur une `str` ; `re.ASCII` rétablit le comportement ASCII. JS ne l'a jamais fait pour `\w`, `\d`, `\b` : `/\w+/u` coupe « Créteil » en « Cr ». Pour une regex partagée entre un script Python et une app TS, écrire les classes explicitement (`[^\W\d_]`, `\p{L}`) plutôt que de compter sur `\w`.
- Usage : ✅ `\w+` en Python pour découper des libellés français, `\p{L}+` avec `u` en JS · ❌ porter tel quel un `\w` d'un langage à l'autre.

```python
# Exemple 1 : Python, Unicode par défaut
import re

re.findall(r"\w+", "Créteil Évry")
# → ["Créteil", "Évry"]
re.findall(r"\w+", "Créteil Évry",
           re.ASCII)
# → ["Cr", "teil", "vry"]
```

```js
// Exemple 2 : JS, ASCII même avec u
"Créteil".match(/\w+/u)[0]  // → "Cr"
"Créteil Évry".match(/\p{L}+/gu)
// → ["Créteil", "Évry"]
```

- Quiz : Que vaut `re.findall(r"\w+", "Créteil")` (é en forme NFD) ?
- [ ] `["Créteil"]`
- [ ] `["Creteil"]`
- [x] `["Cre", "teil"]`
- [ ] `["Cr", "teil"]`
- Réponse : `["Cre", "teil"]` (mesuré) : l'accent combinant (catégorie `Mn`) n'est pas une lettre pour `\w` ; normaliser en NFC avant la regex.

## 11. \p{Diacritic} n'est pas combining
- Id : unicode-diacritic-vs-combining
- Sous-thème : accents
- Type : comparaison
- Niveau : 3
- Profils : web, expert
- Prérequis : unicode-cle-de-recherche
- Mots-clés : diacritique, caractère combinant, regex
- Source : revision-pwa · pwa-parcours
- Définition : En JS, `replace(/\p{Diacritic}/gu, "")` retire aussi des signes autonomes (`^`, `` ` ``, `·`) ; `unicodedata.combining` en Python ne vise que les accents combinants.
- Contexte : `Diacritic` est une propriété Unicode large : accents combinants, mais aussi accent circonflexe isolé, accent grave, point médian. La clé JS de revision-pwa (`termKey`) efface donc le `^` de « C^ » ; la version Python le garde. `\p{M}` (marques combinantes) est l'équivalent exact de `combining` côté JS.
- Usage : ✅ `\p{M}` en JS pour retirer les accents après NFD, comme Python · ❌ `\p{Diacritic}` sur un texte où `^`, `` ` `` ou `·` ont un sens (code, écriture inclusive).

```python
# Exemple 1 : Python ne vise que Mn
import unicodedata as u

u.combining("́")   # → 230
u.combining("^")        # → 0
u.category("^")         # → "Sk"
```

```js
// Exemple 2 : JS, deux classes
const k = (s, re) =>
  s.normalize("NFD").replace(re, "")
k("C^ é", /\p{Diacritic}/gu)  // → "C e"
k("C^ é", /\p{M}/gu)          // → "C^ e"
k("l·l", /\p{Diacritic}/gu)   // → "ll"
```

- Quiz : Clé JS avec `\p{Diacritic}`, clé Python avec `combining` : donnent-elles la même clé pour `"5^2"` ?
- [ ] Oui : `"52"` des deux côtés
- [ ] Oui : `"5^2"` des deux côtés
- [x] Non : `"52"` en JS, `"5^2"` en Python
- [ ] Non : `"5^2"` en JS, `"52"` en Python
- Réponse : non : `^` (U+005E) a la propriété `Diacritic` mais n'est pas combinant ; un index construit d'un côté et lu de l'autre ne retrouve pas le terme.

## 12. clé JS et clé Python : ß diverge
- Id : unicode-cle-js-python
- Sous-thème : casse
- Type : piège
- Niveau : 3
- Profils : web, data, expert
- Prérequis : texte-nombres-casefold, unicode-cle-de-recherche
- Mots-clés : clé de recherche
- Source : revision-pwa · pwa-parcours
- Définition : `toLowerCase()` en JS garde `ß` alors que `casefold()` en Python le change en `ss` : la même clé calculée des deux côtés diffère.
- Contexte : `casefold` applique le pliage de casse complet d'Unicode ; JS n'a pas d'équivalent direct (`toLowerCase` = `lower`). Un index de glossaire construit en Python et interrogé en TS rate donc « Straße ». Règle : une seule implémentation de la clé (celle de l'app : le parser TS l'utilise aussi au build), ou un test de parité sur une liste de cas pièges des deux côtés.
- Usage : ✅ même fonction de clé au build et à la lecture, tests de parité JS / Python · ❌ « réécrire la même chose » dans l'autre langage sans jeu de cas commun.

```python
# Exemple 1 : les deux pliages Python
"Straße".lower()      # → "straße"
"Straße".casefold()   # → "strasse"
```

```js
// Exemple 2 : côté JS
"Straße".toLowerCase()   // → "straße"
"Straße".localeCompare("STRASSE",
  "de", { sensitivity: "base" })
// → 0 (égales pour Intl)
```

- Quiz : Clé Python avec `lower()`, clé JS avec `toLowerCase()` : divergent-elles sur « Straße » ?
- [x] Non : `"straße"` des deux côtés
- [ ] Oui : `"strasse"` en Python
- [ ] Oui : `"strasse"` en JS
- Réponse : non : `lower` et `toLowerCase` suivent le même tableau de minuscules Unicode ; c'est `casefold` qui ajoute `ß` → `ss`.

## 13. İ turc : lower ajoute un caractère
- Id : unicode-i-turc
- Sous-thème : casse
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : texte-nombres-casefold
- Mots-clés : caractère combinant, point de code
- Source : revision-pwa · pwa-parcours
- Définition : `"İ".lower()` (I majuscule pointé, turc) donne `"i"` suivi d'un point combinant : la chaîne en minuscules est plus longue que l'originale.
- Contexte : Unicode ne sait pas, hors locale, que la minuscule turque de « İ » est un « i » simple : il garde le point en accent combinant (U+0307). `len` change, un découpage par index calculé sur l'original se décale, et `== "istanbul"` échoue. Le retrait des combinants (NFD + `combining`) le fait disparaître. Python ignore la locale du poste pour `lower` et `casefold`.
- Usage : ✅ clé de recherche complète (casefold, NFD, sans combinants) pour des noms étrangers · ❌ couper une chaîne en minuscules avec des positions calculées sur l'originale.

```python
# Exemple 1 : un caractère de plus
s = "İSTANBUL"
len(s)                # → 8
s.lower() == "i̇stanbul"  # → True
len(s.lower())        # → 9
```

```python
# Exemple 2 : la clé complète le rattrape
import unicodedata as u

d = u.normalize("NFD", "İSTANBUL".casefold())
"".join(c for c in d
        if not u.combining(c))  # → "istanbul"
```

- Quiz : Lancé avec `LANG=tr_TR.UTF-8`, que vaut `"I".lower()` en Python ?
- [ ] `"ı"` (i sans point)
- [x] `"i"`
- [ ] Dépend de la locale du système
- [ ] `"i̇"`
- Réponse : `"i"` (mesuré) : `str.lower` ne lit pas la locale ; une minuscule turque correcte demande une bibliothèque (PyICU).
