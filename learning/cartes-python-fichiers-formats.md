---
title: "Cartes · Fichiers et formats Python"
type: cartes
langage: Python
chapitre: Fichiers et formats
cours: Fichiers et formats
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Fichiers et formats Python
Python · Fichiers et formats : csv, fichiers (format spec v4 de revision-pwa).

## 1. csv : DictReader
- Id : fichiers-formats-dictreader-chaines
- Sous-thème : csv
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Mots-clés : CSV, itérateur, DuckDB
- Définition : `csv.DictReader` lit un CSV en une suite de dicts dont les clés sont les en-têtes ; toutes les valeurs sont des chaînes.
- Contexte : La 1re ligne donne les clés, chaque ligne suivante devient un dict. Rien n'est typé : nombres et dates restent des `str`, à convertir soi-même. Le lecteur est un itérateur, il ne se parcourt qu'une fois. Les champs entre guillemets peuvent contenir le séparateur ; ouvrir un vrai fichier avec `newline=""` pour que les retours à la ligne dans ces champs soient bien lus.
- Usage : ✅ lire un export CSV (data.gouv, Excel) en accédant aux colonnes par nom · ❌ CSV sans en-tête : `csv.reader` ; calculs tabulaires lourds : DuckDB ou pandas.

```python
# Exemple 1 : tout est chaîne
import csv
import io

f = io.StringIO("siren,nb\n483609327,2\n")
r = next(csv.DictReader(f))
r["nb"]           # → "2"  (str)
int(r["nb"]) + 1  # → 3
```

```python
# Exemple 2 : virgule entre guillemets
import csv
import io

txt = ('nom,ville\n'
       '"Dupont, SA",Lyon\n')
f = io.StringIO(txt)
r = next(csv.DictReader(f))
r["nom"]      # → "Dupont, SA"
r["ville"]    # → "Lyon"
```

- Quiz : En-tête `siren,nb`, ligne `483609327` seule : que vaut `r["nb"]` ?
- [ ] `""`
- [ ] `KeyError`
- [x] `None`
- [ ] `ValueError`
- Réponse : `None` : une colonne manquante prend la valeur `restval` (par défaut `None`) ; à l'inverse, les valeurs en trop vont sous la clé `None`.

## 2. pathlib : construire un chemin
- Id : fichiers-formats-path-assembler-chemin
- Sous-thème : pathlib
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Mots-clés : pathlib, clé S3
- Définition : `Path` manipule les chemins comme des objets ; l'opérateur `/` les assemble sans gérer les séparateurs à la main.
- Contexte : `Path` remplace `os.path` : `.name`, `.stem`, `.suffix`, `.parent` découpent le chemin ; `.exists()`, `.read_text()`, `.mkdir(parents=True)`, `.glob()` agissent sur le disque. Un `Path` n'est pas une chaîne : `str(p)` pour une API qui en exige une. Le `/` accepte un `Path` ou une `str` à droite.
- Usage : ✅ construire `data/raw/<date>.jsonl`, lister les fichiers d'un dossier · ❌ clés S3 (`s3://…`) : ce ne sont pas des chemins locaux, concaténer des chaînes.

```python
# Exemple 1 : assembler et découper
from pathlib import Path

p = Path("data") / "raw" / "j.jsonl"
p.name        # → "j.jsonl"
p.suffix      # → ".jsonl"
p.parent      # → Path("data/raw")
```

```python
# Exemple 2 : écrire, lister, relire
import tempfile
from pathlib import Path

d = Path(tempfile.mkdtemp())
(d / "2026-10-23.jsonl").write_text("")
(d / "notes.txt").write_text("x")
[p.stem for p in d.glob("*.jsonl")]
# → ["2026-10-23"]
(d / "notes.txt").read_text()  # → "x"
```

- Quiz : Que vaut `Path("data") / "/raw"` ?
- [x] `Path("/raw")`
- [ ] `Path("data/raw")`
- [ ] `Path("data//raw")`
- [ ] `ValueError`
- Réponse : `Path("/raw")` : un segment absolu remplace tout ce qui précède, comme `path.resolve` en Node, pas comme `path.join`.

## 3. csv : le séparateur français
- Id : fichiers-formats-csv-point-virgule
- Sous-thème : csv
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : fichiers-formats-dictreader-chaines
- Mots-clés : CSV, JSONL, INSEE
- Définition : `delimiter=";"` lit les CSV exportés en français (Excel, data.gouv), où la virgule sert de séparateur décimal.
- Contexte : Le module `csv` ne devine pas le séparateur : par défaut c'est la virgule, quelle que soit la source. Un mauvais séparateur ne lève aucune erreur, il produit une seule colonne. Les nombres à virgule décimale (`1234,50`) restent des chaînes : `float` les refuse, il faut remplacer la virgule. `csv.Sniffer` peut deviner le format sur un échantillon.
- Usage : ✅ fichiers data.gouv, exports Excel en français, référentiels INSEE · ❌ fichiers produits par le projet : garder la virgule (norme RFC 4180) ou passer en JSONL.

```python
# Exemple 1 : point-virgule
import csv, io

txt = "siren;ville\n483609327;Lyon\n"
f = io.StringIO(txt)
r = next(csv.DictReader(f, delimiter=";"))
r["ville"]        # → "Lyon"
```

```python
# Exemple 2 : virgule décimale
import csv
import io

f = io.StringIO("siren;ca\n48;1234,50\n")
r = next(csv.DictReader(f, delimiter=";"))
r["ca"]           # → "1234,50"
float(r["ca"].replace(",", "."))
# → 1234.5
float(r["ca"])    # ❌ ValueError
```

- Quiz : Même fichier lu sans `delimiter=";"` : que vaut `r` ?
- [ ] `csv.Error`
- [x] `{"siren;ville": "483609327;Lyon"}`
- [ ] `{"siren": "483609327", "ville": "Lyon"}`
- [ ] `ValueError`
- Réponse : `{"siren;ville": "483609327;Lyon"}` : aucune erreur, une seule colonne ; le bug passe silencieusement.

## 4. csv : DictWriter
- Id : fichiers-formats-dictwriter-fieldnames
- Sous-thème : csv
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : fichiers-formats-dictreader-chaines
- Mots-clés : CSV, JSONL
- Définition : `csv.DictWriter` écrit des dicts en lignes CSV selon `fieldnames`, qui fixe l'ordre et la liste des colonnes.
- Contexte : L'ordre des colonnes vient de `fieldnames`, jamais de l'ordre des clés du dict. Une clé manquante est écrite vide (valeur `restval`). Les lignes se terminent par `\r\n`, comme le veut la norme ; ouvrir un vrai fichier avec `newline=""` évite des lignes vides en trop sous Windows. Les valeurs non chaînes sont converties par `str`.
- Usage : ✅ export tabulaire pour un humain ou un tableur · ❌ données imbriquées (listes de SIREN, sous-objets) : JSONL, le CSV n'a qu'un niveau.

```python
# Exemple 1 : l'ordre vient de fieldnames
import csv
import io

buf = io.StringIO()
w = csv.DictWriter(buf, ["siren", "nb"])
w.writerow({"nb": 2, "siren": "48"})
buf.getvalue()    # → "48,2\r\n"
```

```python
# Exemple 2 : en-tête et clé manquante
import csv
import io

buf = io.StringIO()
w = csv.DictWriter(buf, ["siren", "nb"])
w.writeheader()
w.writerow({"siren": "48"})   # pas de nb
buf.getvalue()
# → "siren,nb\r\n48,\r\n"
```

- Quiz : Même `w`, que fait `w.writerow({"siren": "48", "ville": "Lyon"})` ?
- [ ] `ville` est ignorée
- [ ] Ajoute une colonne `ville`
- [ ] `KeyError`
- [x] `ValueError`
- Réponse : `ValueError` : une clé absente de `fieldnames` est refusée ; `extrasaction="ignore"` la laisse tomber.
