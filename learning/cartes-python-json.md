---
title: "Cartes · JSON Python"
type: cartes
langage: Python
cours: JSON
created: 2026-10-24
updated: 2026-10-25
---

# Cartes · JSON Python
Python · JSON : formes, jsonl, parser, sérialiser (format spec v3 de revision-pwa).

## 1. json : loads et dumps
- Sous-thème : parser
- Niveau : 1
- Définition : `json.loads` parse une chaîne JSON en dict/list Python, `json.dumps` fait l'inverse (≈ `JSON.parse` / `JSON.stringify`).
- Contexte : Les types se correspondent : objet → `dict`, tableau → `list`, `null` → `None`, `true` → `True`. `loads` et `dumps` travaillent sur des chaînes ; `load` et `dump` (sans s) sur un fichier ouvert. Un JSON invalide lève `json.JSONDecodeError`, sous-classe de `ValueError`. `indent=2` produit un JSON lisible, comme le 3e argument de `JSON.stringify`.
- Usage : ✅ lire une réponse d'API, écrire un rapport ou une config · ❌ gros fichier de milliers d'objets : JSON Lines, lu ligne par ligne.

```python
# Exemple 1 : parser puis resérialiser
import json

brut = '{"siren": "483609327", "nb": 2}'
a = json.loads(brut)   # dict Python
a["nb"]           # → 2
json.dumps(a)
# → '{"siren": "483609327", "nb": 2}'
```

```python
# Exemple 2 : types et erreur
import json

json.loads('{"ok": true, "x": null}')
# → {"ok": True, "x": None}
# JSON exige des guillemets doubles
json.loads("{'ok': 1}") # ❌ ValueError
```

- Quiz : Que vaut `json.dumps({1: "Lyon"})` ?
- [ ] `'{1: "Lyon"}'`
- [x] `'{"1": "Lyon"}'`
- [ ] `TypeError`
- [ ] `'[[1, "Lyon"]]'`
- Réponse : `'{"1": "Lyon"}'` : une clé JSON est toujours une chaîne, l'entier `1` devient `"1"` et ne revient pas en `int` au `loads`.

## 2. json : la racine n'est pas forcément un objet
- Sous-thème : parser
- Niveau : 1
- Définition : Un document JSON peut être un objet, un tableau, mais aussi un nombre, une chaîne, `true` ou `null` seul : `loads` renvoie alors un scalaire.
- Contexte : `json.loads("42")` renvoie `42`, `json.loads("null")` renvoie `None`. Le type du résultat dépend du contenu, pas de la fonction : une API qui répond `null` ou `[]` fait planter un code qui suppose un dict. Vérifier `isinstance(r, dict)` avant `r["clé"]` sur une réponse dont on n'est pas sûr.
- Usage : ✅ valider le type racine d'une réponse avant de lire ses champs · ❌ `r["results"]` directement sur une réponse non vérifiée.

```python
# Exemple 1 : des racines scalaires
import json

json.loads("42")        # → 42
json.loads('"Lyon"')    # → "Lyon"
json.loads("null")      # → None
json.loads("[]")        # → []
```

```python
# Exemple 2 : vérifier la racine
import json

r = json.loads("null")
r.get("results") if isinstance(r, dict) else []
# → []
```

- Quiz : Que vaut `json.dumps("483609327")` ?
- [ ] `'483609327'`
- [x] `'"483609327"'`
- [ ] `TypeError`
- [ ] `'["483609327"]'`
- Réponse : `'"483609327"'` : une chaîne seule est un document JSON valide, écrit avec ses guillemets doubles.

## 3. json : str(dict) n'est pas du JSON
- Sous-thème : sérialiser
- Niveau : 1
- Définition : `str(d)` et `print(d)` donnent la représentation Python (`'`, `True`, `None`), pas du JSON : seul `json.dumps` produit du JSON valide.
- Contexte : La représentation Python ressemble à du JSON mais diffère : guillemets simples, `True`, `False`, `None` au lieu de `true`, `false`, `null`, tuples entre parenthèses. Écrite dans un fichier ou une réponse d'API, elle casse `JSON.parse`, `jq` et Athena. Piège fréquent dans un log ou un `f"{d}"`. Pour relire une représentation Python, `ast.literal_eval`, pas `json`.
- Usage : ✅ `json.dumps(d)` pour tout ce qui sort du programme (fichier, HTTP, log structuré) · ❌ `str(d)` ou `f"{d}"` comme sérialisation.

```python
# Exemple 1 : deux écritures
import json

d = {"ok": True, "x": None}
str(d)         # → "{'ok': True, 'x': None}"
json.dumps(d)  # → '{"ok": true, "x": null}'
```

```python
# Exemple 2 : str ne se relit pas
import json

d = {"siren": "48"}
json.loads(str(d))   # ❌ JSONDecodeError
```

- Quiz : Que vaut `json.loads('{"ok": True}')` ?
- [ ] `{"ok": True}`
- [ ] `{"ok": "True"}`
- [x] `JSONDecodeError`
- [ ] `{"ok": 1}`
- Réponse : `JSONDecodeError` : en JSON, le booléen s'écrit `true` en minuscules ; `True` est un mot inconnu.

## 4. json.load et json.dump : un fichier
- Sous-thème : parser
- Niveau : 1
- Définition : `json.load(f)` lit un document JSON depuis un fichier ouvert, `json.dump(obj, f)` l'y écrit ; sans `s`, ils prennent un fichier, pas une chaîne.
- Contexte : Ils attendent un objet fichier (ce que renvoie `open`), pas un chemin. Ouvrir avec `encoding="utf-8"` pour ne pas dépendre de la machine. `load` lit tout le fichier en mémoire et attend un seul document. Avec `pathlib`, `json.loads(p.read_text("utf-8"))` fait la même chose en une ligne.
- Usage : ✅ lire une config, écrire un rapport ou un état local · ❌ fichier JSONL ou très gros : lecture ligne par ligne ; objet S3 : `json.loads(body.read())`.

```python
# Exemple 1 : écrire puis relire
import json, tempfile
from pathlib import Path

p = Path(tempfile.mkdtemp()) / "r.json"
with open(p, "w", encoding="utf-8") as f:
    json.dump({"nb": 2}, f)
with open(p, encoding="utf-8") as f:
    r = json.load(f)
r       # → {"nb": 2}
```

```python
# Exemple 2 : un chemin n'est pas un fichier
import json

json.load("rapport.json")  # ❌ AttributeError
```

- Quiz : Que renvoie `json.dump({"nb": 2}, f)` ?
- [x] `None`
- [ ] `'{"nb": 2}'`
- [ ] Le nombre d'octets écrits
- [ ] `True`
- Réponse : `None` : `dump` écrit dans le fichier et ne renvoie rien ; pour obtenir la chaîne, `dumps`.

## 5. indent et separators : lisible ou compact
- Sous-thème : sérialiser
- Niveau : 1
- Définition : `indent=2` rend le JSON lisible sur plusieurs lignes ; `separators=(",", ":")` le compacte en supprimant les espaces.
- Contexte : Par défaut, `dumps` écrit une seule ligne avec une espace après `,` et `:`. `indent` (≈ 3e argument de `JSON.stringify`) ajoute retours à la ligne et indentation : pour un humain, jamais en JSONL. `separators` retire les espaces : quelques pour cent de moins sur un gros volume. `sort_keys=True` trie les clés.
- Usage : ✅ `indent=2` pour une config ou un rapport relu, `separators` pour un payload réseau ou un stockage massif · ❌ `indent` dans un fichier JSONL : une ligne = un document.

```python
# Exemple 1 : défaut ou compact
import json

d = {"siren": "48", "nb": 2}
json.dumps(d)
# → '{"siren": "48", "nb": 2}'
json.dumps(d, separators=(",", ":"))
# → '{"siren":"48","nb":2}'
```

```python
# Exemple 2 : indent pour un humain
import json

s = json.dumps({"nb": 2}, indent=2)
s.splitlines()
# → ["{", '  "nb": 2', "}"]
```

- Quiz : Que vaut `json.dumps([1, 2], indent=0)` ?
- [ ] `'[1, 2]'`
- [ ] `'[1,2]'`
- [x] `'[\n1,\n2\n]'`
- [ ] `ValueError`
- Réponse : `'[\n1,\n2\n]'` : `indent=0` insère quand même les retours à la ligne, sans espaces ; seul `indent=None` (défaut) garde une ligne.

## 6. python -m json.tool : formater en terminal
- Sous-thème : parser
- Niveau : 1
- Définition : `python -m json.tool` valide et indente un JSON en ligne de commande, sans installer `jq`.
- Contexte : Il lit un fichier ou l'entrée standard, écrit le JSON indenté de 4 espaces, et sort en erreur (code 1) avec la ligne et la colonne si le JSON est invalide. `--compact`, `--sort-keys`, `--no-ensure-ascii` et `--json-lines` reprennent les options de `dumps`. Pour filtrer ou extraire un champ, `jq` reste plus puissant.
- Usage : ✅ vérifier vite une réponse `curl`, une fixture, un `catalog.json` · ❌ extraire, filtrer, transformer : `jq`.

```bash
# Exemple 1 : formater une réponse
echo '{"siren":"48","nb":2}' \
  | python -m json.tool
# {
#     "siren": "48",
#     "nb": 2
# }
```

```bash
# Exemple 2 : JSON invalide
echo "{'nb': 2}" | python -m json.tool
# Expecting property name enclosed in
#   double quotes: line 1 column 2 (char 1)
echo $?   # 1
```

- Quiz : Qu'affiche `echo '"é"' | python -m json.tool` ?
- [ ] `"é"`
- [x] `"\u00e9"`
- [ ] Une erreur : pas d'objet racine
- [ ] `"e"`
- Réponse : `"\u00e9"` : comme `dumps`, l'outil échappe le non-ASCII par défaut ; `--no-ensure-ascii` garde l'accent.

## 7. sort_keys : trier les clés
- Sous-thème : sérialiser
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `sort_keys=True` écrit les clés de chaque objet par ordre alphabétique, à tous les niveaux : deux dicts égaux donnent la même chaîne.
- Contexte : Sans option, `dumps` suit l'ordre d'insertion du dict, donc l'ordre dans lequel le serveur a envoyé les champs. L'ordre des clés n'a aucun sens en JSON, mais il change la chaîne et donc tout hash calculé dessus. `sort_keys` trie aussi les objets imbriqués ; il ne touche pas aux listes, dont l'ordre est une donnée.
- Usage : ✅ JSON haché, comparé ou versionné (manifest, ligne de partition, snapshot de test) · ❌ JSON lu par un humain qui attend un ordre logique (`id` d'abord) : garder l'ordre d'insertion.

```python
# Exemple 1 : même dict, même chaîne
import json
a = {"tribunal": "Créteil", "id": "A1"}
b = {"id": "A1", "tribunal": "Créteil"}
json.dumps(a) == json.dumps(b)           # → False
json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)  # → True
```

```python
# Exemple 2 : aussi dans les objets imbriqués
import json

d = {"b": 1, "a": {"d": 1, "c": 2}}
json.dumps(d, sort_keys=True)
# → '{"a": {"c": 2, "d": 1}, "b": 1}'
```

- Quiz : Que vaut `json.dumps({"l": [3, 1, 2]}, sort_keys=True)` ?
- [ ] `'{"l": [1, 2, 3]}'`
- [x] `'{"l": [3, 1, 2]}'`
- [ ] `TypeError`
- Réponse : `'{"l": [3, 1, 2]}'` : seules les clés d'objets sont triées ; l'ordre d'une liste est une donnée, il est conservé.

## 8. JSONL : écrire une ligne par document
- Sous-thème : jsonl
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Écrire un JSONL, c'est `json.dumps(doc) + "\n"` pour chaque document, sans `indent`, dernière ligne comprise.
- Contexte : Chaque ligne est un document complet, lisible seul : on écrit et on relit en flux, ligne par ligne, et `wc -l` compte les annonces. Le `\n` final de la dernière ligne est la convention POSIX : sans lui, `cat a b` colle deux documents sur une ligne. `dumps` sans `indent` ne produit jamais de retour à la ligne : ceux des valeurs sont échappés.
- Usage : ✅ partition d'annonces, export, logs structurés · ❌ `json.dumps(liste)` d'un bloc pour une journée : un seul document, illisible en flux.

```python
# Exemple 1 : une ligne par annonce
import json
rows = [{"id": "A1"}, {"id": "A2"}]
s = "".join(json.dumps(r) + "\n" for r in rows)
s   # → '{"id": "A1"}\n{"id": "A2"}\n'
len(s.splitlines())   # → 2
```

```python
# Exemple 2 : relire ligne par ligne
import json

s = '{"id": "A1"}\n{"id": "A2"}\n'
[json.loads(l)["id"] for l in s.splitlines()]
# → ["A1", "A2"]
```

- Quiz : Sans le `+ "\n"`, que fait `json.loads` sur la chaîne obtenue pour ces deux annonces ?
- [ ] Rend la première annonce
- [ ] Rend une liste des deux
- [x] `JSONDecodeError` (Extra data)
- [ ] Rend la dernière annonce
- Réponse : `JSONDecodeError` (Extra data) : `{"id": "A1"}{"id": "A2"}` est un document suivi de texte en trop ; `loads` refuse.

## 9. dumps rend une str : encoder pour du binaire
- Sous-thème : sérialiser
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `json.dumps` rend une `str` ; pour un fichier ouvert en `"wb"` ou un `GzipFile`, il faut `.encode("utf-8")` avant `write`.
- Contexte : Python distingue texte et octets : un flux binaire refuse une `str` (`TypeError: a bytes-like object is required`). Le writer BODACC encode chaque ligne une fois (`serialize(row) -> bytes`) : les mêmes octets partent dans le gzip et dans le hash. `json.dump(obj, f)` écrit des `str` par morceaux : il ne marche que sur un fichier texte.
- Usage : ✅ `(json.dumps(r) + "\n").encode("utf-8")` vers un flux binaire · ❌ `json.dump` sur un fichier `"wb"` ou un gzip binaire : ouvrir en `"wt"` ou encoder soi-même.

```python
# Exemple 1 : str puis bytes
import json
s = json.dumps({"id": "A1"})
type(s).__name__             # → "str"
(s + "\n").encode("utf-8")   # → b'{"id": "A1"}\n'
```

```python
# Exemple 2 : un flux binaire refuse la str
import io, json

buf = io.BytesIO()
buf.write(json.dumps({"id": "A1"}))  # ❌ TypeError
```

- Quiz : Que fait `json.dump({"id": "A1"}, gz)` avec `gz = gzip.GzipFile(fileobj=buf, mode="wb")` ?
- [ ] Écrit le JSON compressé
- [x] `TypeError`
- [ ] Écrit le JSON en ASCII
- [ ] `ValueError`
- Réponse : `TypeError` : `json.dump` écrit des `str` dans `gz`, qui n'accepte que des `bytes` ; encoder soi-même ou ouvrir en `"wt"`.

## 10. json et bytes : loads oui, dumps non
- Sous-thème : parser
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `json.loads` accepte des `bytes` UTF-8 (une ligne lue d'un `.gz`) ; `json.dumps` refuse un `bytes` dans les données à écrire.
- Contexte : Asymétrie qui surprend : on relit une partition gzip en `"rb"` et chaque ligne, un `bytes`, passe directement à `loads`. Dans l'autre sens, un champ resté en `bytes` (réponse HTTP non décodée) fait lever `TypeError: Object of type bytes is not JSON serializable`. Décoder à l'entrée, encoder à la sortie, `str` entre les deux.
- Usage : ✅ `json.loads(ligne)` sur les lignes binaires d'un `.gz` · ❌ garder un champ en `bytes` dans un dict destiné à `dumps` : `.decode()` d'abord.

```python
# Exemple 1 : loads lit des octets
import json
ligne = b'{"tribunal": "Cr\xc3\xa9teil"}\n'
json.loads(ligne)["tribunal"]  # → "Créteil"
```

```python
# Exemple 2 : dumps refuse des octets
import json

json.dumps({"brut": b"A1"})  # ❌ TypeError
json.dumps({"brut": b"A1".decode()})
# → '{"brut": "A1"}'
```

- Quiz : Que vaut `json.loads(b'"A1"')` ?
- [ ] `b"A1"`
- [x] `"A1"`
- [ ] `TypeError`
- Réponse : `"A1"` : les octets sont décodés en UTF-8 avant d'être parsés ; une chaîne JSON devient une `str`, jamais un `bytes`.

## 11. JSONDecodeError : lire l'erreur
- Sous-thème : parser
- Niveau : 2
- Définition : `json.JSONDecodeError`, sous-classe de `ValueError`, porte `msg`, `lineno`, `colno`, `pos` et `doc` : où et sur quel texte le décodage a échoué.
- Contexte : Capturer `json.JSONDecodeError` plutôt qu'un `Exception` large ; `except ValueError` l'attrape aussi. `e.doc[e.pos:]` montre l'extrait fautif. Causes fréquentes : page HTML d'erreur d'un proxy, virgule finale (acceptée par les littéraux JS, refusée en JSON), JSON tronqué par un timeout. Le texte de `msg` varie selon la version de Python : ne pas le tester.
- Usage : ✅ journaliser la position et un extrait, ou le numéro de ligne d'un JSONL · ❌ avaler l'erreur et continuer avec `{}` : la donnée perdue passe inaperçue.

```python
# Exemple 1 : où est l'erreur ?
import json

try:
    json.loads('{"nb": 2,}')
except json.JSONDecodeError as e:
    err = e
(err.lineno, err.colno)   # → (1, 10)
err.doc[err.pos]          # → "}"
```

```python
# Exemple 2 : un extrait lisible
import json

brut = '<html>502 Bad Gateway</html>'
try:
    json.loads(brut)
except ValueError as e:   # attrapée aussi
    extrait = e.doc[e.pos:e.pos + 6]
extrait   # → "<html>"
```

- Quiz : Que fait `json.loads("")` ?
- [ ] Renvoie `None`
- [x] `JSONDecodeError`
- [ ] Renvoie `{}`
- [ ] Renvoie `""`
- Réponse : `JSONDecodeError` (Expecting value) : un corps vide (204, timeout) n'est pas du JSON ; tester le corps ou le statut avant de décoder.

## 12. json : les nombres
- Sous-thème : parser
- Niveau : 2
- Définition : `loads` rend un entier JSON en `int` exact, quelle que soit sa taille, et un nombre à virgule ou à exposant en `float`.
- Contexte : Python n'a pas la limite de `Number.MAX_SAFE_INTEGER` : un identifiant de 20 chiffres reste exact en Python, mais perd ses derniers chiffres dans `JSON.parse` côté JS. `1.0` reste un float et `1e2` devient `100.0`. Un identifiant converti en nombre perd ses zéros de tête : il voyage en chaîne.
- Usage : ✅ identifiants (SIREN, ids d'annonce) en chaînes dans tout JSON produit · ❌ montants en `float` : `parse_float=Decimal`.

```python
# Exemple 1 : int exact, float sinon
import json

json.loads("12345678901234567890")
# → 12345678901234567890
json.loads("1.0")   # → 1.0  (float)
json.loads("1e2")   # → 100.0
```

```python
# Exemple 2 : un SIREN en chaîne
import json

d = {"siren": "012345678"}
json.loads(json.dumps(d))["siren"]
# → "012345678"
int("012345678")    # → 12345678  (0 perdu)
```

- Quiz : Que fait `json.loads('{"siren": 012345678}')` ?
- [ ] Renvoie `{"siren": 12345678}`
- [ ] Renvoie `{"siren": "012345678"}`
- [ ] Renvoie `{"siren": 12345678.0}`
- [x] `JSONDecodeError`
- Réponse : `JSONDecodeError` : JSON interdit les zéros en tête d'un nombre ; un SIREN commençant par 0 doit être une chaîne.

## 13. json : les accents
- Sous-thème : sérialiser
- Niveau : 2
- Définition : `ensure_ascii=False` fait écrire à `json.dumps` les caractères non ASCII tels quels au lieu de les échapper en `\uXXXX`.
- Contexte : Par défaut, `dumps` échappe tout caractère non ASCII : le JSON reste valide et `loads` retrouve bien « Créteil », mais un fichier lu à l'œil, par `grep` ou dans la console S3 devient illisible. Avec `ensure_ascii=False`, ouvrir le fichier en `encoding="utf-8"` explicitement, sinon l'encodage par défaut de la machine s'applique.
- Usage : ✅ fichiers JSON relus par des humains, libellés de tribunaux et de communes · ❌ canal qui n'accepte que l'ASCII (vieil en-tête HTTP, terminal limité) : garder le défaut.

```python
# Exemple 1 : garder l'accent
import json

t = {"tribunal": "Créteil"}
json.dumps(t, ensure_ascii=False)
# → '{"tribunal": "Créteil"}'
```

```python
# Exemple 2 : fichier en UTF-8
import json
import tempfile
from pathlib import Path

p = Path(tempfile.mkdtemp()) / "t.json"
t = {"tribunal": "Créteil"}
s = json.dumps(t, ensure_ascii=False)
p.write_text(s, encoding="utf-8")
json.loads(p.read_text("utf-8")) == t
# → True
```

- Quiz : Que vaut `len(json.dumps("é"))`, sans option ?
- [ ] `3`
- [ ] `1`
- [x] `8`
- [ ] `6`
- Réponse : `8` : par défaut `"é"` devient `\u00e9` entre guillemets, soit 6 caractères plus 2 guillemets ; avec `ensure_ascii=False`, ce serait `3`.

## 14. json : dates et default
- Sous-thème : sérialiser
- Niveau : 2
- Définition : `default=` donne à `dumps` une fonction appelée sur chaque objet non sérialisable, typiquement pour les dates.
- Contexte : `default` n'est appelé que pour ce que `json` ne sait pas écrire (`date`, `Decimal`, `set`, `UUID`). Sans lui, `dumps` lève `TypeError` : contrairement à `JSON.stringify`, aucun `toJSON` implicite. `default=str` est rapide mais grossier ; une fonction dédiée choisit le format et lève `TypeError` pour le reste. Au retour, `loads` ne recrée pas les dates : elles restent des chaînes.
- Usage : ✅ sérialiser un modèle avec dates ou montants (rapport, sortie Lambda) · ❌ modèles pydantic : `model_dump_json()` gère déjà dates et Decimal.

```python
# Exemple 1 : default=str
import json
from datetime import date

a = {"parution": date(2026, 10, 23)}
json.dumps(a, default=str)
# → '{"parution": "2026-10-23"}'
```

```python
# Exemple 2 : une fonction dédiée
import json
from datetime import date

def enc(o):
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(type(o).__name__)

a = {"d": date(2026, 10, 23)}
json.dumps(a, default=enc)
# → '{"d": "2026-10-23"}'
json.dumps({"x": object()},
           default=enc)  # ❌ TypeError
```

- Quiz : Que vaut `json.dumps({"s": {1, 2}}, default=str)` ?
- [ ] `'{"s": [1, 2]}'`
- [x] `'{"s": "{1, 2}"}'`
- [ ] `TypeError`
- [ ] `'{"s": "[1, 2]"}'`
- Réponse : `'{"s": "{1, 2}"}'` : `str` est appliqué au set entier, qui devient la chaîne `"{1, 2}"` ; pour un tableau, `default` doit renvoyer `list(o)`.

## 15. dataclass vers JSON : asdict
- Sous-thème : sérialiser
- Niveau : 2
- Définition : `json.dumps` ne sait pas écrire une `dataclass` : `dataclasses.asdict(obj)` la convertit d'abord en dict, récursivement.
- Contexte : `JSON.stringify` sérialise n'importe quel objet ; `dumps` ne connaît que dict, list, tuple, str, nombres, booléens et `None`. `asdict` convertit aussi les dataclasses imbriquées et les listes qu'elles contiennent. Les dates restent des `date` : combiner avec `default=`. Au retour, `Annonce(**d)` reconstruit l'objet, sans valider les types.
- Usage : ✅ écrire des objets métier simples en JSON ou JSONL · ❌ objets à valider à la relecture, avec dates et Decimal : pydantic (`model_dump_json`).

```python
# Exemple 1 : passer par asdict
import json
from dataclasses import asdict, dataclass

@dataclass
class Annonce:
    siren: str
    nb: int

json.dumps(asdict(Annonce("48", 2)))
# → '{"siren": "48", "nb": 2}'
```

```python
# Exemple 2 : aller-retour
import json
from dataclasses import asdict, dataclass

@dataclass
class Annonce:
    siren: str
    lies: list[str]

s = json.dumps(asdict(Annonce("48", ["55"])))
Annonce(**json.loads(s)).lies   # → ["55"]
```

- Quiz : Avec `Annonce` de l'exemple 1, que fait `json.dumps(Annonce("48", 2))`, sans `asdict` ?
- [ ] `'{"siren": "48", "nb": 2}'`
- [ ] `'"Annonce(siren=\'48\', nb=2)"'`
- [x] `TypeError`
- [ ] `ValueError`
- Réponse : `TypeError` (Object of type Annonce is not JSON serializable) : aucun `toJSON` implicite, il faut `asdict` ou `default=`.

## 16. pydantic : JSON validé en un passage
- Sous-thème : parser
- Niveau : 2
- Définition : `Modele.model_validate_json(texte)` parse et valide un JSON en une étape ; `obj.model_dump_json()` le resérialise, dates comprises.
- Contexte : Plus rapide que `json.loads` puis `model_validate` : le parsing se fait en Rust, dans pydantic-core, sans passer par le module `json`. En mode par défaut, `"2026-10-23"` devient une `date` et `"2"` l'entier `2`. Un champ au mauvais type lève `ValidationError`, qui liste tous les champs fautifs. `model_dump_json` écrit les dates en ISO, sans espaces.
- Usage : ✅ chaque ligne JSONL d'annonces lue depuis S3, corps d'événement Lambda · ❌ JSON au schéma inconnu ou variable : `json.loads`.

```python
# Exemple 1 : parser et valider
from datetime import date
from pydantic import BaseModel

class Annonce(BaseModel):
    siren: str
    parution: date

a = Annonce.model_validate_json(
    '{"siren": "48", "parution": "2026-10-23"}')
a.parution          # → date(2026, 10, 23)
a.model_dump_json()
# → '{"siren":"48","parution":"2026-10-23"}'
```

```python
# Exemple 2 : un champ au mauvais type
from pydantic import BaseModel, ValidationError

class Annonce(BaseModel):
    nb: int

Annonce.model_validate_json('{"nb": "2"}').nb
# → 2  (chaîne convertie)
Annonce.model_validate_json('{"nb": "x"}')  # ❌ ValidationError
```

- Quiz : Avec ce modèle, que lève `Annonce.model_validate_json("{nb: 1}")` (JSON invalide) ?
- [ ] `json.JSONDecodeError`
- [ ] `SyntaxError`
- [x] `ValidationError`
- [ ] `TypeError`
- Réponse : `ValidationError` (type `json_invalid`) : pydantic parse lui-même, une erreur de syntaxe devient une erreur de validation comme les autres.

## 17. JSON Lines : lire ligne par ligne
- Sous-thème : jsonl
- Niveau : 2
- Définition : un fichier `.jsonl` contient un document JSON par ligne ; on le lit ligne par ligne, un `json.loads` chacune.
- Contexte : Chaque ligne est autonome : on lit un fichier de plusieurs Go sans le charger en entier, on ajoute en fin sans réécrire, et une ligne corrompue n'empêche pas de lire les autres. C'est le format des exports BODACC du projet et celui qu'Athena et `jq -c` lisent nativement. Écrire avec `json.dumps(obj) + "\n"`, jamais avec `indent`.
- Usage : ✅ journées d'annonces, logs, tout flux d'enregistrements · ❌ un seul document structuré (config, rapport) : JSON classique.

```python
# Exemple 1 : lire ligne par ligne
import io
import json

f = io.StringIO('{"nb": 1}\n{"nb": 2}\n')
lignes = [json.loads(l) for l in f]
sum(l["nb"] for l in lignes)   # → 3
```

```python
# Exemple 2 : écrire
import io
import json

annonces = [{"siren": "483609327"},
            {"siren": "552100554"}]
buf = io.StringIO()
for a in annonces:
    buf.write(json.dumps(a) + "\n")
buf.getvalue().count("\n")   # → 2
```

- Quiz : Que fait `json.loads('{"nb": 1}\n{"nb": 2}')` ?
- [ ] Renvoie `[{"nb": 1}, {"nb": 2}]`
- [ ] Renvoie `{"nb": 2}`
- [x] `JSONDecodeError`
- [ ] Renvoie `{"nb": 1}`
- Réponse : `JSONDecodeError` (« Extra data ») : `loads` attend un seul document ; du JSONL se parse ligne par ligne.

## 18. JSONL : une ligne corrompue
- Sous-thème : jsonl
- Niveau : 2
- Définition : Lire un JSONL robuste, c'est décoder chaque ligne dans un `try`, numéroter avec `enumerate`, sauter les lignes vides et compter les rejets.
- Contexte : Une seule ligne tronquée (écriture interrompue, fichier coupé) ne doit pas faire perdre la journée : on isole l'erreur à sa ligne. `enumerate(f, start=1)` donne le numéro pour le journal. Une ligne vide se repère avec `not l.strip()`. Au-delà d'un seuil de rejets, lever : un fichier entièrement faux doit échouer, pas produire zéro annonce en silence.
- Usage : ✅ ingestion de journées BODACC, relecture de logs JSON · ❌ données critiques sans tolérance : laisser l'exception remonter dès la première ligne.

```python
# Exemple 1 : isoler la ligne fautive
import io, json

f = io.StringIO('{"nb": 1}\n{"nb": \n\n{"nb": 3}\n')
ok, rejets = [], []
for n, l in enumerate(f, start=1):
    if not l.strip():
        continue                # ligne vide
    try:
        ok.append(json.loads(l))
    except json.JSONDecodeError:
        rejets.append(n)
[d["nb"] for d in ok]   # → [1, 3]
rejets                  # → [2]
```

- Quiz : Que vaut `json.loads('{"nb": 1}\n')`, avec le `\n` final ?
- [x] `{"nb": 1}`
- [ ] `JSONDecodeError`
- [ ] `[{"nb": 1}]`
- [ ] `None`
- Réponse : `{"nb": 1}` : les espaces et retours à la ligne autour d'un document sont permis ; `strip()` ne sert qu'à repérer une ligne vide.

## 19. JSONL : un saut de ligne dans une valeur
- Sous-thème : jsonl
- Niveau : 2
- Définition : `json.dumps` échappe les retours à la ligne des chaînes en `\n` : sans `indent`, un document tient toujours sur une seule ligne.
- Contexte : Un texte d'annonce sur plusieurs lignes ne casse donc pas le JSONL : le retour devient les deux caractères `\` et `n`, et `loads` le restitue. Découper un JSONL avec `splitlines()` reste sûr, contrairement à un CSV aux champs multi-lignes. Le danger vient d'un JSON fabriqué à la main : un vrai retour à la ligne dans une chaîne JSON est invalide.
- Usage : ✅ écrire avec `json.dumps(obj) + "\n"`, relire ligne par ligne · ❌ concaténer des chaînes pour fabriquer du JSON : l'échappement est oublié.

```python
# Exemple 1 : le texte reste sur une ligne
import json

a = {"texte": "Liquidation\nJudiciaire"}
s = json.dumps(a)
"\n" in s                # → False
json.loads(s) == a       # → True
```

```python
# Exemple 2 : JSON fait à la main
import json

t = "Ligne 1\nLigne 2"
brut = '{"t": "' + t + '"}'
json.loads(brut)   # ❌ JSONDecodeError
json.loads(json.dumps({"t": t}))["t"] == t
# → True
```

- Quiz : Que vaut `len(json.dumps("a\nb"))` ?
- [ ] `5`
- [ ] `3`
- [x] `6`
- [ ] `4`
- Réponse : `6` : `"a\nb"` est écrit `"a\\nb"` : `a`, `\`, `n`, `b` et deux guillemets.

## 20. json : du JSON dans une chaîne
- Sous-thème : formes
- Niveau : 2
- Source : data-platform · S1-05
- Définition : Un champ dont la valeur est une chaîne contenant du JSON demande un second `json.loads` : le premier ne parse que l'enveloppe.
- Contexte : BODACC sérialise `listepersonnes`, `jugement`, `depot` en texte dans le JSON, et le schéma de l'API les déclare `text`. Après le premier `loads`, ces champs sont des `str` : `a["jugement"]["nature"]` lève `TypeError`. Selon la famille d'annonce, le champ vaut `None` ; s'il est déjà un dict, le redécoder lève `TypeError` : tester `isinstance(v, str)` d'abord. Contrôler en parsant, jamais sur le texte brut.
- Usage : ✅ exports OpenDataSoft, `body` d'un message SQS qui contient du JSON, colonne JSON dans un CSV · ❌ `loads` aveugle sur tous les champs : une vraie chaîne (`"Lyon"`) lève `JSONDecodeError`.

```python
# Exemple 1 : deux loads, deux niveaux
import json

ligne = json.dumps({"id": "A1",
    "jugement": json.dumps(
        {"nature": "Liquidation"})})
r = json.loads(ligne)
type(r["jugement"])  # → str
j = json.loads(r["jugement"])
j["nature"]          # → "Liquidation"
```

```python
# Exemple 2 : décoder seulement une chaîne
import json

def decoder(v):
    if isinstance(v, str):  # pas encore dict
        v = v.strip()
        return json.loads(v) if v else None
    return v

decoder('{"n": 1}')   # → {"n": 1}
decoder({"n": 1})     # → {"n": 1}
decoder(None)         # → None
decoder("  ")         # → None
```

- Quiz : Avec `ligne` de l'exemple 1, que vaut `'"nature": "Liquidation"' in ligne` ?
- [ ] `True`
- [x] `False`
- [ ] `TypeError`
- Réponse : `False` : dans le texte brut, les guillemets imbriqués sont échappés (`\"nature\"`) ; une recherche textuelle (`grep`, `in`) rate le champ, il faut parser.

## 21. JSON issu de XML : un dict ou une liste
- Sous-thème : formes
- Niveau : 2
- Source : data-platform · S1-05
- Définition : Du JSON converti depuis du XML donne un objet pour une valeur seule, une liste pour plusieurs : normaliser en liste avant de parcourir.
- Contexte : Le convertisseur ne connaît pas le schéma : un `<personne>` unique devient un dict, répété une liste. BODACC le fait sur `personne` et même sur `prenom`. Le code écrit sur le cas fréquent plante sur le rare, parfois une annonce sur mille : on ne le voit qu'en testant sur une journée complète. Une petite fonction `en_liste`, appliquée à la lecture, règle tous les champs concernés.
- Usage : ✅ données issues de XML (BODACC, SOAP, exports de greffes) · ❌ des `isinstance` dispersés dans tout le code : normaliser une fois, à la lecture.

```python
# Exemple 1 : toujours une liste
def en_liste(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

en_liste({"nom": "HERRERA"})
# → [{"nom": "HERRERA"}]
en_liste([{"nom": "A"}, {"nom": "B"}])
# → [{"nom": "A"}, {"nom": "B"}]
```

```python
# Exemple 2 : prenom simple ou multiple
def en_liste(x):
    return x if isinstance(x, list) else [x]

p1 = {"prenom": "David",
      "nom": "HERRERA"}
p2 = {"prenom": ["Noah", "Louis"],
      "nom": "MARTIN"}
[" ".join(en_liste(p["prenom"])
          + [p["nom"]]) for p in (p1, p2)]
# → ["David HERRERA", "Noah Louis MARTIN"]
```

- Quiz : Sans `en_liste`, que fait `" ".join([p2["prenom"], p2["nom"]])` ?
- [ ] `"Noah Louis MARTIN"`
- [ ] `"['Noah', 'Louis'] MARTIN"`
- [x] `TypeError`
- [ ] `"NoahLouis MARTIN"`
- Réponse : `TypeError` (sequence item 0: expected str instance, list found) : `join` n'accepte que des `str`, il ne convertit pas une liste comme le ferait `Array.join` en JS.

## 22. len : caractères ou octets
- Sous-thème : sérialiser
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `len(s)` compte des caractères, `len(s.encode())` des octets : avec `ensure_ascii=False`, un accent fait 1 caractère mais 2 octets UTF-8.
- Contexte : La taille qui compte pour S3, une limite Lambda ou un manifest (`raw_bytes`), c'est celle en octets. Le writer BODACC additionne `len(line)` sur la ligne déjà encodée, jamais sur la `str`. Avec `ensure_ascii=True` (défaut), le JSON est pur ASCII : caractères et octets coïncident, mais chaque accent devient 6 caractères `é`.
- Usage : ✅ mesurer `len(ligne_encodée)` pour une taille de fichier ou une limite de payload · ❌ `len(json.dumps(...))` comme taille en octets d'un JSON accentué.

```python
# Exemple 1 : 16 caractères, 17 octets
import json
s = json.dumps({"t": "Créteil"}, ensure_ascii=False)
len(s)              # → 16
len(s.encode())     # → 17
```

```python
# Exemple 2 : la taille d'un fichier JSONL
import json

rows = [{"t": "Créteil"}, {"t": "Nîmes"}]
lignes = [(json.dumps(r, ensure_ascii=False)
           + "\n").encode() for r in rows]
sum(len(l) for l in lignes)   # → 34
```

- Quiz : Que vaut `len(json.dumps("é", ensure_ascii=False).encode())` ?
- [ ] `1`
- [ ] `3`
- [x] `4`
- [ ] `8`
- Réponse : `4` : deux guillemets d'un octet chacun, plus `é` qui fait 2 octets en UTF-8.

## 23. JSONL : split ou splitlines
- Sous-thème : jsonl
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Un JSONL bien formé finit par `\n` : `split("\n")` rend alors une chaîne vide en dernier, `splitlines()` non.
- Contexte : Le `\n` final de la dernière ligne (convention POSIX, écrit par le writer) fait que `"A1\nA2\n".split("\n")` vaut `["A1", "A2", ""]` : le `json.loads("")` qui suit lève `JSONDecodeError`. `splitlines()` ne crée pas d'élément vide final et gère aussi `\r\n`. En flux, itérer sur le fichier rend chaque ligne avec son `\n`, que `loads` ignore.
- Usage : ✅ `splitlines()` sur un JSONL en mémoire, itération sur le fichier sinon · ❌ `split("\n")` suivi de `json.loads` sans filtrer les lignes vides.

```python
# Exemple 1 : la ligne vide de trop
s = '{"id": "A1"}\n{"id": "A2"}\n'
len(s.split("\n"))      # → 3
len(s.splitlines())     # → 2
s.split("\n")[-1]       # → ""
```

```python
# Exemple 2 : le loads qui casse
import json

s = '{"id": "A1"}\n'
[json.loads(l) for l in s.splitlines()]
# → [{"id": "A1"}]
[json.loads(l) for l in s.split("\n")]  # ❌ JSONDecodeError
```

- Quiz : Que vaut `len("A1\r\nA2\r\n".splitlines())` ?
- [ ] `4`
- [ ] `3`
- [x] `2`
- [ ] `5`
- Réponse : `2` : `splitlines` traite `\r\n` comme une seule fin de ligne et n'ajoute pas d'élément vide final.

## 24. flottants : la chaîne dépend de la valeur exacte
- Sous-thème : sérialiser
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `dumps` écrit un `float` sous sa forme la plus courte : `1` et `1.0`, ou `0.3` et `0.1+0.2`, donnent deux chaînes, donc deux hash.
- Contexte : Pour une empreinte, `{"capital": 1}` et `{"capital": 1.0}` sont deux contenus différents, alors que Python les dit égaux (`1 == 1.0`). Un calcul intermédiaire (`0.1 + 0.2`) laisse `0.30000000000000004`. Normaliser avant de hacher : montants en `Decimal` ou en entiers (centimes), et un seul type par champ.
- Usage : ✅ entiers ou chaînes pour les montants d'une ligne hachée · ❌ hacher des `float` issus de calculs, ou un champ tantôt `int` tantôt `float`.

```python
# Exemple 1 : égaux en Python, pas en JSON
import json
1 == 1.0                                   # → True
json.dumps({"c": 1}) == json.dumps({"c": 1.0})  # → False
json.dumps(0.1 + 0.2)   # → "0.30000000000000004"
```

```python
# Exemple 2 : des centimes entiers
import json

capital = round(1500.10 * 100)    # centimes
json.dumps({"capital_cts": capital})
# → '{"capital_cts": 150010}'
```

- Quiz : Que vaut `json.dumps(1e16)` ?
- [ ] `"10000000000000000"`
- [ ] `"1e16"`
- [x] `"1e+16"`
- [ ] `"1.0e16"`
- Réponse : `"1e+16"` : `dumps` reprend `repr(float)`, qui passe en notation scientifique à partir de 1e16 ; un `int` resterait en chiffres.

## 25. json : tuple et NaN
- Sous-thème : sérialiser
- Niveau : 3
- Définition : JSON n'a ni tuple ni NaN : un tuple devient une liste, et NaN produit un JSON invalide pour les autres langages.
- Contexte : `dumps` accepte les tuples (écrits en tableau) et `nan` / `inf` (écrits `NaN`, `Infinity`, hors norme JSON). Un aller-retour ne rend donc pas l'objet d'origine. `NaN` passe en Python, mais casse `JSON.parse`, Athena ou un validateur strict, loin de la cause. `allow_nan=False` fait échouer tôt, au moment de l'écriture.
- Usage : ✅ `allow_nan=False` sur toute sortie consommée par un autre système · ❌ compter sur un aller-retour JSON pour garder tuple, set ou date : typer à la relecture (pydantic).

```python
# Exemple 1 : tuple → liste
import json

t = ("483609327", "552100554")
json.loads(json.dumps(t))
# → ['483609327', '552100554']
```

```python
# Exemple 2 : refuser NaN à l'écriture
import json

ca = float("nan")
json.dumps({"ca": None})
# → '{"ca": null}'
json.dumps({"ca": ca},
  allow_nan=False)  # ❌ ValueError
```

- Quiz : Que vaut `json.dumps({"ca": float("nan")})`, sans option ?
- [ ] `'{"ca": null}'`
- [ ] `ValueError`
- [ ] `'{"ca": "nan"}'`
- [x] `'{"ca": NaN}'`
- Réponse : `'{"ca": NaN}'` : Python l'écrit sans erreur, mais ce n'est pas du JSON valide et `JSON.parse` côté JS plante.

## 26. json : montants en Decimal
- Sous-thème : parser
- Niveau : 3
- Définition : `parse_float=Decimal` fait lire les nombres décimaux d'un JSON en `Decimal` exact, au lieu de `float` arrondi.
- Contexte : Par défaut, `0.1` devient un `float` binaire, et les sommes de montants dérivent. `parse_float` reçoit le texte du nombre avant toute conversion : `Decimal("0.1")` est exact. À l'écriture, `dumps` refuse `Decimal` (`TypeError`) : `default=str` l'écrit en chaîne, pour qu'aucun consommateur ne le relise en float.
- Usage : ✅ capitaux, chiffres d'affaires, tout montant relu puis additionné · ❌ mesures ou scores : le `float` suffit.

```python
# Exemple 1 : float ou Decimal
import json
from decimal import Decimal

brut = "[0.1, 0.2]"
sum(json.loads(brut))   # → 0.30000000000000004
sum(json.loads(brut, parse_float=Decimal))
# → Decimal("0.3")
```

```python
# Exemple 2 : réécrire en chaîne
import json
from decimal import Decimal

d = {"capital": Decimal("1500.10")}
json.dumps(d, default=str)
# → '{"capital": "1500.10"}'
```

- Quiz : Que vaut `type(json.loads("1500", parse_float=Decimal)).__name__` ?
- [ ] `"Decimal"`
- [x] `"int"`
- [ ] `"float"`
- [ ] `"str"`
- Réponse : `"int"` : `parse_float` ne voit que les nombres à virgule ou exposant ; les entiers passent par `parse_int`.

## 27. object_hook : reconstruire des dates
- Sous-thème : parser
- Niveau : 3
- Définition : `object_hook` est appelé sur chaque objet décodé et renvoie sa version transformée, par exemple avec des champs date convertis.
- Contexte : `loads` ne recrée jamais de `date` : elles restent des chaînes. `object_hook` reçoit chaque dict, de l'intérieur vers l'extérieur, et ce qu'il renvoie remplace l'objet. C'est le pendant de `default=` à l'écriture. Pratique sans dépendance ; pydantic fait la même chose avec un schéma explicite et des erreurs claires.
- Usage : ✅ petit script ou Lambda sans pydantic, champs connus (`parution`) · ❌ schéma riche à valider : pydantic.

```python
# Exemple 1 : convertir un champ connu
import json
from datetime import date

def dates(d):
    if "parution" in d:
        d["parution"] = date.fromisoformat(
            d["parution"])
    return d

brut = '{"siren": "48", "parution": "2026-10-23"}'
json.loads(brut)["parution"]   # → "2026-10-23"
a = json.loads(brut, object_hook=dates)
a["parution"]   # → date(2026, 10, 23)
```

- Quiz : Si le hook oublie `return d`, que vaut `json.loads('{"a": 1}', object_hook=f)` ?
- [x] `None`
- [ ] `{"a": 1}`
- [ ] `TypeError`
- [ ] `{}`
- Réponse : `None` : ce que renvoie le hook remplace l'objet, et une fonction sans `return` renvoie `None`.

## 28. json : clés en double
- Sous-thème : formes
- Niveau : 3
- Définition : Un objet JSON qui contient deux fois la même clé est accepté sans erreur par `loads` : seule la dernière valeur est gardée.
- Contexte : La norme JSON ne l'interdit pas formellement ; Python, comme `JSON.parse`, garde la dernière. Un JSON produit par concaténation ou par un outil bogué perd ainsi une valeur en silence. `object_pairs_hook` reçoit la liste des paires avant la construction du dict : de quoi détecter les doublons et lever une erreur.
- Usage : ✅ `object_pairs_hook` pour valider des fichiers de partenaires ou des configs écrites à la main · ❌ sur chaque ligne d'un gros flux interne fiable : coût inutile.

```python
# Exemple 1 : en silence
import json

json.loads('{"nb": 1, "nb": 2}')
# → {"nb": 2}
```

```python
# Exemple 2 : détecter les doublons
import json

def strict(paires):
    cles = [k for k, _ in paires]
    if len(cles) != len(set(cles)):
        raise ValueError(f"doublon : {cles}")
    return dict(paires)

json.loads('{"a": 1}', object_pairs_hook=strict)
# → {"a": 1}
json.loads('{"a": 1, "a": 2}',
           object_pairs_hook=strict)  # ❌ ValueError
```

- Quiz : Combien de fois `strict` est-il appelé pour `'{"a": {"b": 1}}'` ?
- [ ] 1
- [x] 2
- [ ] 0
- [ ] 3
- Réponse : 2 : le hook est appelé pour chaque objet JSON, l'objet intérieur d'abord, puis l'objet racine.

## 29. sort_keys : l'ordre des points de code
- Sous-thème : sérialiser
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `sort_keys` trie les clés par point de code Unicode : majuscules avant minuscules, lettres accentuées après `z`.
- Contexte : C'est l'ordre de `sorted()` sur des `str`, pas l'ordre alphabétique français : `"B" < "a" < "e" < "é"`. Deux implémentations « canoniques » dans d'autres langages peuvent trier autrement (par octets UTF-8, par UTF-16 en JS) : un hash calculé en Python et un autre en TS sur le « même » JSON peuvent diverger. Garder des noms de champs en ASCII minuscule évite le problème.
- Usage : ✅ clés ASCII en minuscules (`dateparution`, `familleavis`) pour un JSON haché par plusieurs langages · ❌ clés accentuées ou à casse mixte dans un JSON canonique partagé.

```python
# Exemple 1 : majuscules d'abord, accents à la fin
import json
d = {"é": 3, "e": 4, "b": 1, "B": 2}
json.dumps(d, sort_keys=True, ensure_ascii=False)
# → '{"B": 2, "b": 1, "e": 4, "é": 3}'
```

```python
# Exemple 2 : le même ordre que sorted
import json

d = {"tribunal": 1, "Tribunal": 2, "id": 3}
list(json.loads(json.dumps(d, sort_keys=True)))
# → ["Tribunal", "id", "tribunal"]
```

- Quiz : Que vaut `sorted(["z", "É", "a"])` ?
- [ ] `["a", "É", "z"]`
- [ ] `["É", "a", "z"]`
- [x] `["a", "z", "É"]`
- [ ] `["z", "a", "É"]`
- Réponse : `["a", "z", "É"]` : `É` vaut U+00C9 (201), après `z` (122) ; l'ordre est celui des points de code, pas du dictionnaire.

## 30. sort_keys : clés de types mélangés
- Sous-thème : sérialiser
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `sort_keys=True` sur un dict dont les clés mélangent `int` et `str` lève `TypeError` : Python ne sait pas comparer `1` et `"b"`.
- Contexte : Sans `sort_keys`, `dumps({1: "a", "b": 2})` passe et convertit la clé `1` en `"1"`. Avec, le tri a lieu **avant** la conversion, sur les clés Python d'origine : `'<' not supported between instances of 'str' and 'int'`. Arrive avec un dict construit par compteur (`{annee: n}`) auquel on ajoute une clé texte (`"total"`). Convertir les clés en `str` d'abord.
- Usage : ✅ `{str(k): v for k, v in d.items()}` avant un `dumps(..., sort_keys=True)` · ❌ mélanger clés numériques et textuelles dans un dict sérialisé canoniquement.

```python
# Exemple 1 : sans tri, ça passe
import json
d = {2026: 12, "total": 12}
json.dumps(d)   # → '{"2026": 12, "total": 12}'
json.dumps(d, sort_keys=True)  # ❌ TypeError
```

```python
# Exemple 2 : clés en str d'abord
import json

d = {2026: 12, "total": 12}
s = {str(k): v for k, v in d.items()}
json.dumps(s, sort_keys=True)
# → '{"2026": 12, "total": 12}'
```

- Quiz : Que vaut `json.dumps({10: "a", 9: "b"}, sort_keys=True)` ?
- [ ] `'{"10": "a", "9": "b"}'`
- [x] `'{"9": "b", "10": "a"}'`
- [ ] `TypeError`
- Réponse : `'{"9": "b", "10": "a"}'` : le tri porte sur les entiers d'origine (9 < 10), avant leur conversion en chaînes.

## 31. ensure_ascii=False : le surrogate isolé
- Sous-thème : sérialiser
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Avec `ensure_ascii=False`, une chaîne contenant un surrogate isolé (`"\ud800"`) passe `dumps` mais fait lever `UnicodeEncodeError` à l'`encode("utf-8")`.
- Contexte : Un surrogate isolé n'est pas un caractère valide : il arrive d'un JSON source mal formé (`"\ud83d"` coupé d'un emoji) lu par `loads`, qui l'accepte. Avec `ensure_ascii=True`, `dumps` le réécrit en `\ud800` ASCII et tout passe ; sans, le caractère brut atteint `encode` et le writer plante au milieu de la journée. Choisir : nettoyer à l'entrée, ou `encode("utf-8", "surrogatepass")` en connaissance de cause.
- Usage : ✅ tester le writer avec une valeur contenant `"\ud800"` si la source est peu fiable · ❌ supposer que tout ce que `json.loads` a lu se réencode en UTF-8.

```python
# Exemple 1 : loads l'accepte, encode non
import json
v = json.loads('"\\ud800"')
s = json.dumps(v, ensure_ascii=False)
s.encode("utf-8")  # ❌ UnicodeEncodeError
```

```python
# Exemple 2 : en ASCII, il reste échappé
import json

v = json.loads('"\\ud800"')
json.dumps(v)                # → '"\\ud800"'
json.dumps(v).encode()       # → b'"\\ud800"'
```

- Quiz : Que vaut `len(json.loads('"\\ud83d\\ude00"'))` (un emoji écrit en paire de surrogates) ?
- [ ] `2`
- [x] `1`
- [ ] `UnicodeDecodeError`
- [ ] `4`
- Réponse : `1` : `loads` recombine une paire de surrogates valide en un seul caractère (l'emoji) ; seul un surrogate seul reste invalide.
