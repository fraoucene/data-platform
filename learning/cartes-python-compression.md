---
title: "Cartes · Compression Python"
type: cartes
langage: Python
chapitre: Fichiers et formats
cours: Compression
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Compression Python
Python · Compression : gzip, en-tête reproductible, niveaux, flux (format spec v4 de revision-pwa).

## 1. gzip.compress : des bytes, pas une str
- Id : compression-bytes-pas-str
- Sous-thème : mémoire
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Voir aussi : hachage-bytes-pas-str, json-dumps-encoder-bytes
- Mots-clés : bytes, UTF-8, S3
- Source : data-platform · S1-07
- Définition : `gzip.compress` et `gzip.decompress` travaillent sur des `bytes` en mémoire : une `str` s'encode d'abord en UTF-8 (≈ `zlib.gzipSync(Buffer)` en Node).
- Contexte : Python sépare strictement texte (`str`) et octets (`bytes`), là où Node convertit souvent en silence. `gzip.compress("A1")` lève `TypeError` ; il faut `"A1".encode("utf-8")`, et `decompress` rend des `bytes` qu'on décode à la main. Tout objet « bytes-like » est accepté : `bytes`, `bytearray`, `memoryview`.
- Usage : ✅ corps HTTP ou objet S3 déjà en mémoire, petits volumes · ❌ journée complète : écrire en flux avec `gzip.GzipFile` ou `gzip.open`, sans tout garder en RAM.

```python
# Exemple 1 : encoder, compresser, relire
import gzip
gz = gzip.compress("Créteil\n".encode())
gzip.decompress(gz)
# → b"Cr\xc3\xa9teil\n"
gzip.decompress(gz).decode()
# → "Créteil\n"
```

```python
# Exemple 2 : une str est refusée
import gzip

gzip.compress("A1")  # ❌ TypeError
```

- Quiz : Que fait `gzip.compress(bytearray(b"A1"))` ?
- [ ] `TypeError` : `bytes` attendu
- [x] Compresse normalement
- [ ] Compresse la représentation `"bytearray(...)"`
- Réponse : Compresse normalement : `bytearray` est « bytes-like », comme `bytes` et `memoryview` ; seule une `str` est refusée.

## 2. .gz : le nom ne compresse rien
- Id : compression-extension-gz-signature
- Sous-thème : format
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Voir aussi : compression-gzip-open-modes
- Mots-clés : gzip, Athena, clé S3
- Source : data-platform · S1-07
- Définition : L'extension `.gz` n'est qu'un nom : `open("p.jsonl.gz", "w")` écrit du texte en clair, seuls `gzip.open` ou `GzipFile` compressent.
- Contexte : Ni Python ni S3 ne regardent l'extension pour compresser. Un fichier nommé `.gz` mais écrit avec `open` est du texte brut : `gzip.decompress` lève `BadGzipFile`, et Athena ou `zcat` échouent à la lecture. Un vrai gzip commence toujours par les octets `\x1f\x8b` : c'est la vérification à faire, pas le nom.
- Usage : ✅ vérifier `data[:2] == b"\x1f\x8b"` avant d'envoyer un fichier `.gz` · ❌ déduire le format du nom de fichier ou de la clé S3.

```python
# Exemple 1 : un faux .gz
import gzip, tempfile
from pathlib import Path
p = Path(tempfile.mkdtemp()) / "p.jsonl.gz"
p.write_text('{"id": "A1"}\n')
p.read_bytes()[:2] == b"\x1f\x8b"  # → False
gzip.decompress(p.read_bytes())  # ❌ BadGzipFile
```

```python
# Exemple 2 : reconnaître un vrai gzip
import gzip

def est_gzip(data):
    return data[:2] == b"\x1f\x8b"

est_gzip(gzip.compress(b"A1"))   # → True
est_gzip(b'{"id": "A1"}')       # → False
```

- Quiz : Quelle classe d'exception `gzip.BadGzipFile` étend-elle ?
- [ ] `ValueError`
- [ ] `EOFError`
- [x] `OSError`
- [ ] `TypeError`
- Réponse : `OSError` : un fichier illisible est traité comme une erreur d'entrée-sortie ; `except ValueError` ne l'attrape pas.

## 3. GzipFile : compresser en flux
- Id : compression-gzipfile-en-flux
- Sous-thème : flux
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Mots-clés : en flux, générateur, partition
- Source : data-platform · S1-07
- Définition : `gzip.GzipFile(fileobj=f, mode="wb")` enveloppe un fichier ouvert : chaque `write` y écrit des octets compressés, la mémoire reste plate.
- Contexte : C'est le cœur du writer BODACC : on ouvre le fichier final en `"wb"`, on pose un `GzipFile` par-dessus, et on écrit ligne par ligne depuis un générateur. Rien n'est accumulé : 32 373 annonces (55,6 Mo) passent avec un pic mémoire de 4,9 Mo. `write` renvoie le nombre d'octets **non compressés** reçus.
- Usage : ✅ écrire une partition depuis un générateur, compresser vers un `io.BytesIO` · ❌ simple fichier sur disque sans réglage : `gzip.open(chemin, "wb")` suffit.

```python
# Exemple 1 : un flux au-dessus d'un fichier
import gzip, io
buf = io.BytesIO()
with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
    for l in [b"A1\n", b"A2\n"]:
        gz.write(l)  # ligne par ligne
gzip.decompress(buf.getvalue())  # → b"A1\nA2\n"
```

```python
# Exemple 2 : depuis un générateur
import gzip, io

def annonces():
    for i in range(3):
        yield f'{{"n":{i}}}\n'.encode()

buf = io.BytesIO()
with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
    for ligne in annonces():
        gz.write(ligne)
len(gzip.decompress(buf.getvalue()).splitlines())
# → 3
```

- Quiz : Que renvoie `gz.write(b"A1\n")` ?
- [ ] `None`
- [ ] La taille compressée écrite
- [x] `3`
- [ ] `gz` lui-même, pour chaîner
- Réponse : `3` : `write` renvoie le nombre d'octets non compressés reçus ; la taille compressée ne se connaît qu'à la fermeture.

## 4. mtime=0 : l'heure dans l'en-tête
- Id : compression-mtime-zero
- Sous-thème : en-tête
- Type : piège
- Niveau : 1
- Profils : débutant, data, ops
- Voir aussi : compression-filename-vide, archives-writestr-heure-courante
- Mots-clés : sha256, idempotent, timestamp Unix
- Source : data-platform · S1-07
- Définition : L'en-tête gzip contient un horodatage (`mtime`) ; par défaut c'est l'heure courante, `mtime=0` le fixe pour obtenir des octets reproductibles.
- Contexte : Les octets 4 à 7 de l'en-tête stockent un horodatage Unix. Sans `mtime`, Python y écrit l'heure de la compression : deux compressions du même contenu à une seconde d'écart donnent des fichiers différents, donc des sha256 différents. Le piège passe les tests rapides (même seconde) et casse l'idempotence en production. `mtime=0` signifie « pas d'horodatage ».
- Usage : ✅ tout fichier comparé ou haché au rejeu, artefact de build reproductible · ❌ archive où l'on veut garder la date d'origine (`gzip -N`) : laisser l'horodatage.

```python
# Exemple 1 : deux runs, deux heures
import gzip
a = gzip.compress(b"A1\n", mtime=1000)
b = gzip.compress(b"A1\n", mtime=2000)
a == b          # → False
gzip.decompress(a) == gzip.decompress(b)
# → True  (même contenu)
```

```python
# Exemple 2 : mtime=0, mêmes octets
import gzip
a = gzip.compress(b"A1\n", mtime=0)
b = gzip.compress(b"A1\n", mtime=0)
a == b          # → True
```

- Quiz : Que vaut `gzip.compress(b"A1", mtime=0)[4:8]` ?
- [ ] `b""`
- [x] `b"\x00\x00\x00\x00"`
- [ ] `b"\x1f\x8b\x08\x00"`
- [ ] `b"0000"`
- Réponse : `b"\x00\x00\x00\x00"` : les octets 4 à 7 sont l'horodatage, mis à zéro ; `\x1f\x8b\x08\x00` est la signature, la méthode et les drapeaux (0 à 3).

## 5. compresslevel : vitesse contre taille
- Id : compression-compresslevel-vitesse-taille
- Sous-thème : niveaux
- Type : choisir
- Niveau : 1
- Profils : débutant, data
- Mots-clés : empreinte, partition, Lambda
- Source : data-platform · S1-07
- Définition : `compresslevel` va de 1 (rapide, plus gros) à 9 (lent, plus petit) ; il change les octets compressés, jamais le contenu décompressé.
- Contexte : Mesuré sur une journée BODACC de 55,6 Mo : niveau 1 → 5,69 Mo en 0,3 s, niveau 6 → 4,44 Mo en 0,8 s, niveau 9 → 4,30 Mo en 1,3 s. Au-delà de 6, on paie 60 % de temps en plus pour 3 % de gain. Le niveau se fixe dans une constante : le changer modifie les octets du `.gz`, d'où une empreinte calculée sur le brut.
- Usage : ✅ niveau 6 pour des partitions rejouées chaque jour, 1 pour un fichier temporaire · ❌ niveau 9 par réflexe sur de gros volumes : le temps Lambda coûte plus que les octets S3 gagnés.

```python
# Exemple 1 : trois niveaux, un contenu
import gzip
raw = b'{"tribunal":"Paris","id":1}\n' * 2000
t = {n: len(gzip.compress(raw, n, mtime=0))
     for n in (1, 6, 9)}
t[1] > t[9]      # → True
```

```python
# Exemple 2 : le contenu ne bouge pas
import gzip

raw = b'{"id":"A1"}\n' * 50
g1 = gzip.compress(raw, 1, mtime=0)
g9 = gzip.compress(raw, 9, mtime=0)
g1 == g9                                   # → False
gzip.decompress(g1) == gzip.decompress(g9)  # → True
```

- Quiz : Que vaut `len(gzip.compress(raw, compresslevel=0)) > len(raw)` pour 120 octets de JSON ?
- [x] `True`
- [ ] `False`
- [ ] `ValueError` : niveau hors de 1 à 9
- Réponse : `True` : le niveau 0 stocke sans compresser ; l'en-tête et la fin gzip ajoutent des octets (143 pour 120 mesurés).

## 6. gzip : texte ou octets
- Id : compression-gzip-open-modes
- Sous-thème : flux
- Type : concept
- Niveau : 2
- Profils : data
- Mots-clés : en flux, encodage, Parquet
- Définition : `gzip.open` lit et écrit un fichier compressé comme un fichier normal ; les modes `"rt"` et `"wt"` travaillent en texte.
- Contexte : Un export `.jsonl.gz` se lit sans décompresser sur disque : `gzip.open` décompresse à la volée, ligne par ligne, en mémoire constante. Le mode par défaut est binaire (`"rb"`, `"wb"`) : des `bytes`. En `"rt"` ou `"wt"`, on manipule des `str` : préciser `encoding="utf-8"`, sinon l'encodage de la machine s'applique.
- Usage : ✅ archiver des journées d'annonces sur S3, lire un export compressé · ❌ lecture aléatoire au milieu du fichier : gzip se lit du début ; analytique : Parquet.

```python
# Exemple 1 : fichier en mode texte
import gzip
import tempfile
from pathlib import Path

d = Path(tempfile.mkdtemp())
p = d / "j.jsonl.gz"
with gzip.open(p, "wt",
               encoding="utf-8") as f:
    f.write('{"nb": 1}\n')
with gzip.open(p, "rt",
               encoding="utf-8") as f:
    l = f.readline()
l          # → '{"nb": 1}\n'
```

```python
# Exemple 2 : en "wb", des octets seulement
import gzip, tempfile
from pathlib import Path

p = Path(tempfile.mkdtemp()) / "j.gz"
f = gzip.open(p, "wb")
f.write('{"nb": 1}\n'.encode())  # → 10
f.write('{"nb": 2}\n')  # ❌ TypeError
f.close()
```

- Quiz : Ouvert avec `gzip.open(p)`, sans mode : que vaut `f.readline()` ?
- [ ] `'{"nb": 1}\n'`
- [x] `b'{"nb": 1}\n'`
- [ ] `UnicodeDecodeError`
- [ ] `'{"nb": 1}'`
- Réponse : `b'{"nb": 1}\n'` : le mode par défaut est `"rb"`, on reçoit des `bytes`, et `json.loads` ou `split(",")` dessus surprennent.

## 7. filename="" : le nom dans l'en-tête
- Id : compression-filename-vide
- Sous-thème : en-tête
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : compression-gzipfile-en-flux
- Voir aussi : compression-mtime-zero
- Mots-clés : Lambda, tempfile, sha256
- Source : data-platform · S1-07
- Définition : `GzipFile(fileobj=f)` écrit le nom de `f` dans l'en-tête (champ FNAME) ; `filename=""` le laisse vide et rend les octets indépendants du nom.
- Contexte : Erreur vue sur le writer BODACC : `mtime=0` ne suffisait pas. Sans `filename`, `GzipFile` lit `f.name`, retire `.gz` et l'écrit dans l'en-tête. En Lambda, le fichier vient de `tempfile` et change de nom à chaque invocation : même contenu, autres octets, autre sha256. Mesuré : sans `filename=""` → `False`, avec → `True`. `gzip.compress` et un `io.BytesIO` (sans nom) n'ont pas ce problème.
- Usage : ✅ tout `GzipFile` posé sur un fichier nommé dont les octets doivent être reproductibles · ❌ compter sur `mtime=0` seul : le nom varie encore.

```python
# Exemple 1 : le nom entre dans l'en-tête
import gzip, tempfile
from pathlib import Path
p = Path(tempfile.mkdtemp()) / "tmpa1b2c3"
gzip.open(p, "wb").close()   # gzip vide
b"tmpa1b2c3" in p.read_bytes()  # → True
```

```python
# Exemple 2 : filename="" vide le champ
import gzip, tempfile
from pathlib import Path

d = Path(tempfile.mkdtemp())
for nom in ("tmpa1b2c3", "part.gz"):
    with (open(d / nom, "wb") as f,
          gzip.GzipFile(filename="", fileobj=f,
                        mode="wb", mtime=0) as gz):
        gz.write(b"A1\n")
a = (d / "tmpa1b2c3").read_bytes()
a == (d / "part.gz").read_bytes()  # → True
b"tmpa1b2c3" in a                  # → False
```

- Quiz : `GzipFile(fileobj=buf, mode="wb", mtime=0)` avec `buf = io.BytesIO()` : le nom varie-t-il d'un appel à l'autre ?
- [ ] Oui : un nom aléatoire est généré
- [x] Non : un `BytesIO` n'a pas de nom
- [ ] Oui : le nom vaut l'`id` de l'objet
- Réponse : Non : un `BytesIO` n'a pas de nom : `GzipFile` ne trouve pas d'attribut `name` et laisse FNAME vide.

## 8. niveau par défaut : 9 en Python, 6 en ligne de commande
- Id : compression-niveau-par-defaut
- Sous-thème : niveaux
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : compression-compresslevel-vitesse-taille
- Mots-clés : gzip, BODACC
- Source : data-platform · S1-07
- Définition : `gzip.compress`, `gzip.open` et `GzipFile` compressent au niveau 9 par défaut, alors que la commande `gzip` utilise 6.
- Contexte : Un même fichier compressé par le terminal puis par Python n'a donc ni la même taille ni les mêmes octets. Le niveau 9 est le plus lent pour un gain faible (4,30 Mo contre 4,44 Mo sur une journée BODACC, en 1,3 s au lieu de 0,8 s). D'où un `compresslevel` toujours explicite et nommé (`COMPRESS_LEVEL = 6`), pour que le choix se lise et ne change pas avec un défaut.
- Usage : ✅ `compresslevel=COMPRESS_LEVEL` explicite dans tout writer · ❌ s'en remettre au défaut puis comparer à un fichier produit par `gzip` en terminal.

```python
# Exemple 1 : le défaut, c'est 9
import gzip
raw = b'{"id":"A1","tribunal":"Paris"}\n' * 3000
d = gzip.compress(raw, mtime=0)
d == gzip.compress(raw, 9, mtime=0)  # → True
d == gzip.compress(raw, 6, mtime=0)  # → False
```

```bash
# Exemple 2 : la commande gzip, niveau 6
gzip -k part.jsonl          # niveau 6
gzip -k -9 -c part.jsonl > p9.gz
gzip -l part.jsonl.gz       # tailles et ratio
```

- Quiz : Quel niveau utilise `gzip.GzipFile(fileobj=f, mode="wb")` sans `compresslevel` ?
- [ ] `6`, comme la commande `gzip`
- [x] `9`
- [ ] `1`
- [ ] `-1`, le défaut de zlib
- Réponse : `9` : `GzipFile` a `compresslevel=9` dans sa signature ; seule la commande `gzip` utilise 6 par défaut.

## 9. fin du gzip : CRC et taille à la fermeture
- Id : compression-fin-crc-fermeture
- Sous-thème : flux
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : compression-gzipfile-en-flux
- Voir aussi : context-managers-taille-apres-bloc
- Mots-clés : CRC32, tampon, context manager
- Source : data-platform · S1-07
- Définition : Un gzip finit par 8 octets (CRC32 et taille du contenu) écrits seulement à la fermeture : sans `close()`, le fichier est tronqué, illisible.
- Contexte : Pendant l'écriture, zlib garde des données en tampon et le CRC n'est pas encore connu. C'est `close()` (ou la sortie du `with`) qui vide le tampon et écrit la fin. Lire le fichier avant, ou oublier de fermer, donne `EOFError` à la décompression. D'où `path.stat()` après le bloc `with` dans le writer, jamais dedans.
- Usage : ✅ `with` autour de tout `GzipFile`, taille et hash lus après le bloc · ❌ `gz.write` sans `with` ni `close()`, ou envoi du fichier à S3 depuis l'intérieur du bloc.

```python
# Exemple 1 : lu avant la fermeture
import gzip, io
buf = io.BytesIO()
gz = gzip.GzipFile(fileobj=buf, mode="wb")
gz.write(b"A1\n" * 1000)
gzip.decompress(buf.getvalue())  # ❌ EOFError
gz.close()
len(gzip.decompress(buf.getvalue()))  # → 3000
```

```python
# Exemple 2 : la fin, octet par octet
import gzip, zlib

raw = b"A1\nA2\n"
gz = gzip.compress(raw)
gz[-8:-4] == zlib.crc32(raw).to_bytes(4, "little")
# → True  (CRC32 du brut)
int.from_bytes(gz[-4:], "little")  # → 6
```

- Quiz : On coupe les 8 derniers octets d'un gzip valide. Que fait `gzip.decompress` ?
- [ ] Rend le contenu sans vérifier le CRC
- [ ] `BadGzipFile`
- [x] `EOFError`
- [ ] Rend un contenu vide
- Réponse : `EOFError` : le flux s'arrête avant le marqueur de fin ; `BadGzipFile` est réservé à un en-tête invalide.

## 10. plusieurs membres : concaténer des gzip
- Id : compression-plusieurs-membres
- Sous-thème : flux
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : compression-bytes-pas-str
- Mots-clés : idempotent, rejeu
- Source : data-platform · S1-07
- Définition : Deux gzip collés bout à bout forment un gzip valide à plusieurs membres : la décompression rend les contenus à la suite.
- Contexte : Le format prévoit des « membres » successifs, chacun avec son en-tête et sa fin. `cat a.gz b.gz > ab.gz` est donc lisible, et `gzip.open(p, "ab")` ajoute un membre au lieu de recompresser. Pratique pour assembler des morceaux, piège pour l'idempotence : un rejeu en mode `"ab"` double la journée sans erreur.
- Usage : ✅ assembler des parts compressées séparément, sans tout recompresser · ❌ mode `"ab"` dans un job rejouable : `"wb"` écrase et reste idempotent.

```python
# Exemple 1 : coller deux gzip
import gzip
ab = gzip.compress(b"A1\n") + gzip.compress(b"A2\n")
gzip.decompress(ab)   # → b"A1\nA2\n"
```

```python
# Exemple 2 : "ab" au rejeu = doublon
import gzip, tempfile
from pathlib import Path

p = Path(tempfile.mkdtemp()) / "part.gz"
for _ in range(2):      # job rejoué
    with gzip.open(p, "ab") as f:
        f.write(b"A1\n")
gzip.decompress(p.read_bytes())
# → b"A1\nA1\n"
```

- Quiz : Que vaut `gzip.decompress(gzip.compress(b"") + gzip.compress(b"A1"))` ?
- [ ] `EOFError`
- [ ] `b""`
- [x] `b"A1"`
- [ ] `BadGzipFile`
- Réponse : `b"A1"` : un membre vide est valide (20 octets, contenu nul) ; les membres sont décompressés à la suite.

## 11. gzip ou zlib : même deflate, autre enveloppe
- Id : compression-gzip-ou-zlib
- Sous-thème : format
- Type : comparaison
- Niveau : 2
- Profils : data, web
- Mots-clés : deflate, CRC32, Content-Encoding
- Source : data-platform · S1-07
- Définition : `zlib` et `gzip` utilisent le même algorithme (deflate) avec des en-têtes différents : `gzip.decompress` refuse un flux zlib.
- Contexte : gzip = en-tête de 10 octets (`\x1f\x8b`, heure, nom) + deflate + CRC32 ; zlib = 2 octets (`\x78\x9c`) + deflate + Adler-32. Les fichiers `.gz`, S3 et `Content-Encoding: gzip` attendent gzip ; certains protocoles parlent zlib. `zlib.decompress(data, wbits=31)` lit un gzip, `wbits=47` détecte seul l'un ou l'autre.
- Usage : ✅ fichiers `.gz`, objets S3, corps HTTP compressés : module `gzip` · ❌ `zlib.compress` pour produire un `.gz` : l'en-tête gzip manque.

```python
# Exemple 1 : deux signatures
import gzip, zlib
gzip.compress(b"A1")[:2]   # → b"\x1f\x8b"
zlib.compress(b"A1")[:2]   # → b"x\x9c"
gzip.decompress(zlib.compress(b"A1"))  # ❌ BadGzipFile
```

```python
# Exemple 2 : zlib sait lire un gzip
import gzip, zlib

gz = gzip.compress(b"A1\n")
zlib.decompress(gz, wbits=31)  # → b"A1\n"
zlib.decompress(gz, wbits=47)  # → b"A1\n"
```

- Quiz : Que fait `zlib.decompress(gzip.compress(b"A1"))`, sans `wbits` ?
- [ ] Rend `b"A1"`
- [x] `zlib.error`
- [ ] `BadGzipFile`
- [ ] Rend `b""`
- Réponse : `zlib.error` : sans `wbits`, zlib attend son propre en-tête (`\x78…`) et rejette `\x1f\x8b` ; `BadGzipFile` n'existe que côté `gzip`.

## 12. lire un gros .gz : en flux, ligne par ligne
- Id : compression-lire-gros-gz-en-flux
- Sous-thème : flux
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : compression-gzip-open-modes
- Voir aussi : json-jsonl-lire
- Mots-clés : en flux, partition, Lambda
- Source : data-platform · S1-07
- Définition : Itérer sur `gzip.open(p)` décompresse à la volée, une ligne à la fois ; `gzip.decompress(p.read_bytes())` charge tout le contenu en mémoire.
- Contexte : Pour relire une partition de 55 Mo dans une Lambda, la différence est la RAM : `read_bytes()` charge le `.gz`, puis `decompress` crée les 55 Mo d'un bloc. En itérant, seul un tampon et la ligne courante sont gardés. En mode `"rb"`, chaque ligne est un `bytes` terminé par `b"\n"` ; `json.loads` l'accepte tel quel.
- Usage : ✅ relire, compter ou contrôler une partition volumineuse · ❌ `decompress(read_bytes())` sur un fichier dont la taille n'est pas bornée.

```python
# Exemple 1 : compter sans tout charger
import gzip, tempfile
from pathlib import Path
p = Path(tempfile.mkdtemp()) / "j.gz"
p.write_bytes(gzip.compress(b'{"n":1}\n' * 5))
with gzip.open(p) as f:
    n = sum(1 for _ in f)  # une ligne à la fois
n                          # → 5
```

```python
# Exemple 2 : une ligne = des bytes
import gzip, json, tempfile
from pathlib import Path

p = Path(tempfile.mkdtemp()) / "j.gz"
p.write_bytes(gzip.compress(b'{"id":"A1"}\n'))
with gzip.open(p) as f:
    ligne = next(iter(f))
ligne                  # → b'{"id":"A1"}\n'
json.loads(ligne)      # → {"id": "A1"}
```

- Quiz : Dans l'exemple 2, que vaut `ligne.split(",")` ?
- [ ] `["{\"id\":\"A1\"}\n"]`
- [ ] `[b'{"id":"A1"}\n']`
- [x] `TypeError`
- Réponse : `TypeError` : `ligne` est un `bytes`, son `split` attend un séparateur `bytes` (`b","`) ; décoder ou ouvrir en `"rt"`.

## 13. déjà compressé : gzip ne gagne rien
- Id : compression-deja-compresse
- Sous-thème : niveaux
- Type : concept
- Niveau : 2
- Profils : data, web
- Voir aussi : compression-compresslevel-vitesse-taille
- Mots-clés : deflate, Parquet, Content-Encoding
- Source : data-platform · S1-07
- Définition : Des données déjà compressées ou aléatoires (`.gz`, Parquet, images) ne rapetissent plus : gzip ajoute même quelques octets.
- Contexte : deflate gagne en remplaçant les répétitions ; un fichier compressé n'en contient presque plus. Recompresser coûte du CPU pour rien et complique la lecture (deux décompressions). Cas réel : envoyer un `.jsonl.gz` à S3 avec `Content-Encoding: gzip` et laisser un client le décompresser une fois, au lieu de le recompresser à la volée.
- Usage : ✅ gzip sur du texte répétitif (JSON, CSV, logs) · ❌ recompresser un `.gz`, un Parquet ou une archive avant envoi.

```python
# Exemple 1 : des octets aléatoires
import gzip, os
alea = os.urandom(1000)
len(gzip.compress(alea)) > 1000   # → True
```

```python
# Exemple 2 : JSON répétitif
import gzip

raw = b'{"familleavis":"collective"}\n' * 500
len(raw)                          # → 14500
len(gzip.compress(raw)) < 200     # → True
```

- Quiz : Un `.jsonl.gz` de 4,4 Mo est recompressé avec `gzip.compress`. Quelle taille obtient-on, à peu près ?
- [ ] 0,5 Mo
- [ ] 2,2 Mo
- [x] 4,4 Mo
- Réponse : 4,4 Mo : le flux deflate n'a plus de répétitions à exploiter ; le gain est nul, au mieux quelques octets.

## 14. gzip.compress ou GzipFile : l'octet système, avant 3.13
- Id : compression-octet-systeme
- Sous-thème : en-tête
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : compression-mtime-zero
- Mots-clés : runtime Lambda, dataset
- Source : data-platform · S1-07
- Définition : En Python 3.11 et 3.12, `gzip.compress(mtime=0)` et `GzipFile` écrivent un octet « système » différent : même contenu, autres octets.
- Contexte : En 3.11 et 3.12, `gzip.compress(..., mtime=0)` délègue à `zlib.compress`, qui écrit l'octet 9 selon la machine (3 sous Linux, 19 sous macOS) ; `GzipFile` écrit 255 (inconnu). Python 3.13 a rétabli 255 partout (mesuré en 3.13 et 3.14). Le runtime Lambda python3.12 est concerné : une seule voie d'écriture par dataset, et hacher le brut plutôt que le `.gz`.
- Usage : ✅ toujours la même fonction d'écriture pour un dataset dont on compare les octets · ❌ comparer un `.gz` écrit par `gzip.compress` en test et par `GzipFile` en production.

```python
# Exemple 1 : comparer le brut, pas le .gz
import gzip, io
raw = b"A1\n"
a = gzip.compress(raw, 9, mtime=0)
buf = io.BytesIO()
with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
    gz.write(raw)
gzip.decompress(a) == gzip.decompress(buf.getvalue())
# → True  (a == buf.getvalue() : False en 3.12)
```

```python
# Exemple 2 : l'octet « système »
import gzip, io

buf = io.BytesIO()
with gzip.GzipFile(fileobj=buf, mode="wb",
                   mtime=0) as gz:
    gz.write(b"A1\n")
buf.getvalue()[9]      # → 255  (inconnu)
gzip.decompress(buf.getvalue())  # → b"A1\n"
```

- Quiz : En Python 3.12, quel octet de l'en-tête diffère entre `gzip.compress(raw, mtime=0)` sur un Mac et sur Lambda (Linux) ?
- [ ] L'horodatage (octets 4 à 7)
- [ ] La signature `\x1f\x8b`
- [x] L'octet « système » (octet 9)
- [ ] Le CRC de fin
- Réponse : L'octet « système » (octet 9) : zlib y écrit le code de la plateforme (19 macOS, 3 Linux) ; contenu et CRC identiques. Depuis 3.13, 255 partout.

## 15. ISIZE : la taille modulo 4 Go
- Id : compression-isize-modulo
- Sous-thème : format
- Type : piège
- Niveau : 3
- Profils : data, expert
- Prérequis : compression-fin-crc-fermeture
- Mots-clés : manifest, membre gzip
- Source : data-platform · S1-07
- Définition : Les 4 derniers octets d'un gzip donnent la taille du contenu modulo 2³² : faux au-delà de 4 Go, et limité au dernier membre.
- Contexte : `gzip -l` affiche cette valeur comme « uncompressed ». Elle est utile pour une estimation rapide sans décompresser, mais un fichier de 5 Go affiche 1 Go, et un gzip à plusieurs membres n'affiche que la taille du dernier. Pour une taille fiable, la compter pendant l'écriture (`raw_bytes += len(line)`), comme le writer BODACC, et la ranger dans le manifest.
- Usage : ✅ estimation rapide d'un petit fichier d'un seul membre · ❌ volumétrie d'un gros fichier ou contrôle de complétude : compter à l'écriture.

```python
# Exemple 1 : lire la taille sans décompresser
import gzip
gz = gzip.compress(b"A1\n" * 1000)
int.from_bytes(gz[-4:], "little")   # → 3000
```

```python
# Exemple 2 : plusieurs membres, dernier seul
import gzip

ab = gzip.compress(b"A1\n" * 1000) + gzip.compress(b"A2\n")
int.from_bytes(ab[-4:], "little")   # → 3
len(gzip.decompress(ab))            # → 3003
```

- Quiz : Que vaut l'ISIZE d'un gzip dont le contenu fait 2³² + 10 octets ?
- [ ] 2³² + 10
- [x] 10
- [ ] 0 : taille inconnue
- [ ] `OverflowError` à l'écriture
- Réponse : 10 : le champ fait 4 octets et stocke la taille modulo 2³² ; au-delà de 4 Go, il ne dit plus rien de fiable.

## 16. seek : pas d'accès direct dans un gzip
- Id : compression-seek-sequentiel
- Sous-thème : flux
- Type : concept
- Niveau : 3
- Profils : data, expert
- Prérequis : compression-gzip-open-modes
- Mots-clés : deflate, Parquet
- Source : data-platform · S1-07
- Définition : `gz.seek(n)` en lecture est permis mais décompresse tout depuis le début (ou la position courante) : un gzip ne se lit que séquentiellement.
- Contexte : deflate n'a pas d'index : atteindre l'octet n impose de décompresser les n premiers. `seek` en arrière repart même du début du fichier. En écriture, seul un `seek` en avant est accepté (il écrit des zéros). Conséquence data : un gros `.gz` ne se découpe pas entre plusieurs workers, d'où des parts de taille raisonnable ou un format à blocs (Parquet).
- Usage : ✅ lecture séquentielle d'une partition, du début à la fin · ❌ lecture aléatoire ou parallèle dans un gros `.gz` : plusieurs parts, ou Parquet.

```python
# Exemple 1 : seek fonctionne, mais lit tout
import gzip, io
gz = gzip.compress(b"A1\nA2\nA3\n")
f = gzip.GzipFile(fileobj=io.BytesIO(gz))
f.seek(6)        # → 6  (décompresse 6 octets)
f.read()         # → b"A3\n"
```

```python
# Exemple 2 : en écriture, pas de retour
import gzip, io

f = gzip.GzipFile(fileobj=io.BytesIO(),
                  mode="wb")
f.write(b"A1\n")
f.seek(0)        # ❌ OSError
```

- Quiz : Dans l'exemple 1, après `f.read()`, que coûte `f.seek(0)` puis `f.read(3)` ?
- [ ] Rien : retour direct au début
- [x] Repartir du début du flux compressé
- [ ] `OSError` : seek arrière interdit
- [ ] `ValueError` : flux épuisé
- Réponse : Repartir du début du flux compressé : un `seek` arrière rembobine et décompresse à nouveau jusqu'à la position voulue.
