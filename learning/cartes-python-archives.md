---
title: "Cartes · Archives Python"
type: cartes
langage: Python
chapitre: Fichiers et formats
cours: Archives
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Archives Python
Python · Archives : zipfile pour écrire, lire et rendre reproductible un zip (format spec v4 de revision-pwa).

## 1. ZipFile : écrire une archive
- Id : archives-zipfile-ecrire
- Sous-thème : écrire
- Type : recette
- Niveau : 1
- Profils : débutant, ops, data
- Mots-clés : zip, répertoire central, context manager
- Source : data-platform · S1-07
- Définition : `zipfile.ZipFile(p, "w")` crée une archive zip ; `write` y ajoute un fichier du disque, `writestr` une chaîne ou des octets en mémoire.
- Contexte : Toujours dans un `with` : la table des entrées (le répertoire central) est écrite en fin de fichier, à la fermeture ; sans `close()`, l'archive est illisible. Le mode `"w"` écrase un fichier existant, `"a"` ajoute des entrées, `"x"` refuse d'écraser. Node n'a rien d'intégré : il faut `archiver` ou `adm-zip`.
- Usage : ✅ zip d'une Lambda, export à télécharger, plusieurs fichiers en un · ❌ un seul flux à compresser (un `.jsonl`) : `gzip`, plus simple et lisible en flux.

```python
# Exemple 1 : deux entrées en mémoire
import io, zipfile
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("handler.py", "x = 1")
    zf.writestr("data/a.json", b"{}")
zipfile.ZipFile(buf).namelist()
# → ['handler.py', 'data/a.json']
```

```python
# Exemple 2 : "x" refuse d'écraser
import tempfile, zipfile
from pathlib import Path
p = Path(tempfile.mkdtemp()) / "l.zip"
zipfile.ZipFile(p, "w").close()
zipfile.ZipFile(p, "x")  # ❌ FileExistsError
```

- Quiz : Que donne `zipfile.ZipFile(buf)` si l'écriture s'est faite sans `with` ni `close()` ?
- [ ] `[]` à `namelist()` : archive vide
- [x] `BadZipFile`
- [ ] Les entrées déjà écrites
- [ ] `ValueError: archive ouverte`
- Réponse : `BadZipFile` : sans fermeture, le répertoire central n'est pas écrit ; or un zip se lit par cette table, en fin de fichier.

## 2. ZipFile : lire une archive
- Id : archives-zipfile-lire
- Sous-thème : lire
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Mots-clés : répertoire central, bytes
- Source : data-platform · S1-07
- Définition : En mode `"r"` (défaut), `namelist()` liste les entrées, `read(nom)` rend leurs octets et `extractall(dossier)` les écrit sur le disque.
- Contexte : Le zip se lit par son répertoire central : on accède à une entrée sans décompresser les autres, contrairement à un `.tar.gz` qu'il faut parcourir depuis le début. `read` rend toujours des `bytes` : `.decode()` pour du texte. Un nom absent lève `KeyError`, comme une clé de dict.
- Usage : ✅ vérifier le contenu du zip de build dans un test, lire un fichier d'un export · ❌ tout extraire pour lire une seule entrée : `read(nom)` suffit.

```python
# Exemple 1 : lire une entrée
import io, zipfile
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("siren.txt", "552100554")
z = zipfile.ZipFile(buf)
z.read("siren.txt")   # → b'552100554'
z.read("autre.txt")   # ❌ KeyError
```

- Quiz : L'archive contient seulement `data/a.json` : que rend `z.read("data/")` ?
- [ ] La liste des fichiers du dossier
- [ ] `b""`
- [x] `KeyError`
- [ ] `IsADirectoryError`
- Réponse : `KeyError` : un zip n'a pas de vrais dossiers, seulement des noms d'entrées ; `data/` n'existe que si on l'a ajouté explicitement.

## 3. write : arcname, le nom dans l'archive
- Id : archives-write-arcname
- Sous-thème : écrire
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : archives-zipfile-ecrire
- Mots-clés : Lambda
- Source : data-platform · S1-07
- Définition : `zf.write(chemin, arcname=…)` choisit le nom de l'entrée ; sans `arcname`, l'entrée garde le chemin passé, dossiers parents compris.
- Contexte : Avec un chemin absolu, zipfile retire seulement le `/` de tête : `/tmp/build/ingest_bodacc/handler.py` devient `tmp/build/ingest_bodacc/handler.py`, et Lambda ne trouve plus `ingest_bodacc` à la racine. D'où `path.relative_to(source).as_posix()` dans le script de build : le nom part du dossier installé, avec des `/` même sous Windows.
- Usage : ✅ `arcname=p.relative_to(racine).as_posix()` pour chaque fichier · ❌ `zf.write(p)` avec un chemin absolu ou relatif au dépôt : l'arborescence du poste dans le zip.

```python
# Exemple 1 : avec ou sans arcname
import io, tempfile, zipfile
from pathlib import Path
src = Path(tempfile.mkdtemp())
f = src / "pkg" / "handler.py"
f.parent.mkdir()
f.write_text("x = 1")
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.write(f, f.relative_to(src).as_posix())
    zf.write(f)
noms = zipfile.ZipFile(buf).namelist()
noms[0]                  # → 'pkg/handler.py'
noms[1].startswith("/")  # → False
len(noms[1]) > 20        # → True : tout le chemin
```

- Quiz : Lancé depuis `build/`, quel nom porte l'entrée créée par `zf.write("../lib/a.py")` ?
- [ ] `'lib/a.py'`
- [x] `'../lib/a.py'`
- [ ] `'a.py'`
- [ ] `ValueError` : chemin hors du dossier
- Réponse : `'../lib/a.py'` (mesuré) : `write` ne retire que le `/` de tête ; le `../` reste dans le nom, et c'est `extractall` qui le neutralisera.

## 4. compression : ZIP_STORED par défaut
- Id : archives-zip-stored-par-defaut
- Sous-thème : écrire
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : archives-zipfile-ecrire
- Voir aussi : archives-zipinfo-compression-oubliee
- Mots-clés : deflate, Lambda
- Source : data-platform · S1-07
- Définition : `ZipFile(p, "w")` stocke les fichiers **sans** les compresser ; `compression=zipfile.ZIP_DEFLATED` active le deflate, celui de la commande `zip`.
- Contexte : Piège pour qui vient de `zip -r` : le défaut Python est `ZIP_STORED`, l'archive pèse la somme des fichiers. Pour une Lambda, c'est la taille du `.zip` qui compte pour la limite d'envoi direct (50 Mo). `compresslevel` (0 à 9) règle vitesse contre taille ; `ZIP_BZIP2` et `ZIP_LZMA` compressent mieux mais ne sont pas lus par tous les outils.
- Usage : ✅ `ZIP_DEFLATED` pour tout zip à transférer (Lambda, export) · ❌ contenu déjà compressé (`.gz`, images) : `ZIP_STORED` évite un travail inutile.

```python
# Exemple 1 : même contenu, deux tailles
import io, zipfile
data = "552100554\n" * 1000
def taille(**kw):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", **kw) as zf:
        zf.writestr("s.txt", data)
    return len(buf.getvalue())
taille()                 # → 10108
D = zipfile.ZIP_DEFLATED
taille(compression=D)    # → 154
```

- Quiz : `ZipFile(buf, "w", compresslevel=9)`, sans `compression` : l'archive est-elle compressée ?
- [ ] Oui, au niveau maximal
- [ ] Oui, en deflate niveau 9
- [x] Non : toujours `ZIP_STORED`
- [ ] `ValueError` : niveau sans méthode
- Réponse : non (mesuré : 10108 octets, comme sans option) : `compresslevel` règle la méthode choisie, et la méthode par défaut ne compresse pas.

## 5. infolist : tailles des entrées
- Id : archives-infolist-tailles
- Sous-thème : lire
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Prérequis : archives-zipfile-lire
- Voir aussi : archives-zip-stored-par-defaut
- Mots-clés : Lambda, unzip, __pycache__
- Source : data-platform · S1-07
- Définition : `infolist()` rend un `ZipInfo` par entrée : `filename`, `file_size` (taille réelle), `compress_size` (taille dans l'archive), `date_time`, `external_attr`.
- Contexte : C'est ce que montrent `unzip -l` et `unzip -Z`. Pour un zip Lambda, la somme des `file_size` est la taille décompressée, celle que Lambda limite à 250 Mo ; la taille du fichier `.zip` compte pour l'envoi. `getinfo(nom)` rend un seul `ZipInfo`. Les entrées sont dans l'ordre d'écriture.
- Usage : ✅ test qui vérifie la taille décompressée ou l'absence de `__pycache__` dans le zip de build · ❌ juger la limite de 250 Mo sur la taille du `.zip` : elle est compressée.

```python
# Exemple 1 : taille décompressée
import io, zipfile
D = zipfile.ZIP_DEFLATED
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", D) as zf:
    zf.writestr("a.txt", "A" * 5000)
    zf.writestr("b.txt", "B" * 3000)
infos = zipfile.ZipFile(buf).infolist()
sum(i.file_size for i in infos)  # → 8000
sum(i.compress_size for i in infos) < 100
# → True
```

- Quiz : L'archive contient `a.txt` : que fait `zipfile.ZipFile(buf).getinfo("A.TXT")` ?
- [ ] Rend l'entrée `a.txt`
- [x] `KeyError`
- [ ] Rend `None`
- [ ] Dépend du système de fichiers
- Réponse : `KeyError` : les noms d'entrées sont des chaînes comparées exactement, même sur un Mac dont le disque ignore la casse.

## 6. BadZipFile : ce n'est pas un zip
- Id : archives-badzipfile-pas-un-zip
- Sous-thème : lire
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : gzip, deflate, artefact
- Source : data-platform · S1-07
- Définition : Ouvrir un fichier qui n'est pas un zip (tronqué, page HTML d'erreur, gzip) lève `zipfile.BadZipFile` ; `zipfile.is_zipfile(f)` le teste sans exception.
- Contexte : Un zip se lit par sa fin : un téléchargement coupé est illisible même si le début est bon. `BadZipFile` hérite directement d'`Exception`, pas d'`OSError` : un `except OSError` ne l'attrape pas. Un `.gz` n'est pas un zip, malgré le même algorithme deflate : autre enveloppe.
- Usage : ✅ valider un artefact téléchargé avant de le déployer, `is_zipfile` dans un test de build · ❌ se fier à l'extension `.zip` : seul le contenu compte.

```python
# Exemple 1 : un gzip n'est pas un zip
import gzip, io, zipfile
gz = io.BytesIO(gzip.compress(b"A1"))
zipfile.is_zipfile(gz)   # → False
zipfile.ZipFile(gz)      # ❌ BadZipFile
```

- Quiz : Que fait `zipfile.is_zipfile("absent.zip")` quand le fichier n'existe pas ?
- [ ] `FileNotFoundError`
- [ ] `BadZipFile`
- [x] Rend `False`
- [ ] Rend `None`
- Réponse : `False` (mesuré) : `is_zipfile` attrape l'`OSError` de l'ouverture et répond simplement « pas un zip ».

## 7. writestr(nom) : l'heure courante dans l'archive
- Id : archives-writestr-heure-courante
- Sous-thème : reproductible
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : archives-zipfile-ecrire
- Voir aussi : archives-zipinfo-date-fixe, compression-mtime-zero
- Mots-clés : sha256, source_code_hash, mtime, Terraform
- Source : data-platform · S1-07
- Définition : `zf.writestr("a.py", data)` avec un nom en chaîne date l'entrée à l'heure courante : deux builds identiques donnent deux zips différents.
- Contexte : Chaque entrée porte une date. Avec un nom en `str`, `writestr` prend `time.localtime()` ; `zf.write(p)` copie la date de modification du fichier. Le contenu est le même, les octets non : le sha256 du zip change, donc `source_code_hash`, et Terraform redéploie la Lambda à chaque `apply`. Même piège que `mtime` dans l'en-tête d'un gzip.
- Usage : ✅ un `ZipInfo` à date fixe pour tout zip dont on compare l'empreinte · ❌ `writestr(str)` dans un build qu'on veut reproductible.

```python
# Exemple 1 : la date vient de l'horloge
import io, time, zipfile
def build():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("handler.py", "x = 1")
    return buf.getvalue()
a = build()
time.sleep(2.1)          # pas de 2 s
a == build()             # → False
```

- Quiz : Avec `zf.write(p, "a.py")` au lieu de `writestr`, deux builds à deux minutes d'écart sans toucher `p` : mêmes octets ?
- [x] Oui : la date du fichier n'a pas bougé
- [ ] Non : l'heure courante est écrite
- [ ] Non : `write` ajoute un champ aléatoire
- [ ] Oui, mais seulement en `ZIP_STORED`
- Réponse : oui (mesuré) : `write` copie le `mtime` du fichier, inchangé ; il suffit d'un `touch` ou d'une copie pour que les octets changent.

## 8. ZipInfo : une date fixe, 1980 au plus tôt
- Id : archives-zipinfo-date-fixe
- Sous-thème : zipinfo
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : archives-writestr-heure-courante
- Voir aussi : archives-date-time-deux-secondes
- Mots-clés : build reproductible, SOURCE_DATE_EPOCH, datetime naïf
- Source : data-platform · S1-07
- Définition : `zipfile.ZipInfo(nom, date_time=(1980, 1, 1, 0, 0, 0))` décrit une entrée à date fixe ; passé à `writestr`, il rend l'entrée indépendante de l'horloge.
- Contexte : Le format de date des zips (DOS) commence en 1980 : une date antérieure lève `ValueError`, d'où `(1980, 1, 1, 0, 0, 0)`, la plus petite possible. C'est l'équivalent zip de `SOURCE_DATE_EPOCH` des builds reproductibles. Le tuple est une heure locale naïve, sans fuseau ; le script de build la met dans une constante `FIXED_DATE`.
- Usage : ✅ build de Lambda, artefact rangé sous son hash · ❌ archive où la date des fichiers a un sens pour le lecteur (sauvegarde, export utilisateur).

```python
# Exemple 1 : même build, mêmes octets
import io, time, zipfile
FIXE = (1980, 1, 1, 0, 0, 0)
def build():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("handler.py", FIXE)
        zf.writestr(info, "x = 1")
    return buf.getvalue()
a = build()
time.sleep(2.1)
a == build()             # → True
```

```python
# Exemple 2 : avant 1980
import zipfile
d = (1970, 1, 1, 0, 0, 0)
zipfile.ZipInfo("a.py", d)  # ❌ ValueError
```

- Quiz : Que vaut `zipfile.ZipInfo("a.py").date_time`, sans `date_time` ?
- [ ] L'heure courante
- [x] `(1980, 1, 1, 0, 0, 0)`
- [ ] `(1970, 1, 1, 0, 0, 0)`
- [ ] `None`
- Réponse : `(1980, 1, 1, 0, 0, 0)` (mesuré) : c'est le défaut de `ZipInfo` ; seul `writestr` avec un nom en `str` met l'heure courante.

## 9. ZipInfo à la main : la compression oubliée
- Id : archives-zipinfo-compression-oubliee
- Sous-thème : zipinfo
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : archives-zipinfo-date-fixe, archives-zip-stored-par-defaut
- Mots-clés : ZipInfo, build reproductible
- Source : data-platform · S1-07
- Définition : Un `ZipInfo` construit à la main vaut `ZIP_STORED` : `writestr(info, …)` ignore alors la compression du `ZipFile`, sauf `info.compress_type` fixé.
- Contexte : Avec un nom en `str`, `writestr` crée lui-même le `ZipInfo` et y recopie `compression` et `compresslevel` du `ZipFile`. Avec un `ZipInfo` fourni, il le prend tel quel : le zip reproductible sort non compressé, sans erreur ni avertissement. D'où `info.compress_type = zipfile.ZIP_DEFLATED` dans le script de build.
- Usage : ✅ fixer `compress_type` sur chaque `ZipInfo` créé à la main · ❌ croire que `ZipFile(..., compression=ZIP_DEFLATED)` suffit dès qu'on passe des `ZipInfo`.

```python
# Exemple 1 : seule la 1re est compressée
import io, zipfile
D = zipfile.ZIP_DEFLATED
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", D) as zf:
    zf.writestr("a.txt", "A" * 1000)
    zf.writestr(zipfile.ZipInfo("b.txt"),
                "A" * 1000)
z = zipfile.ZipFile(buf)
z.getinfo("a.txt").compress_size  # → 11
z.getinfo("b.txt").compress_size  # → 1000
```

- Quiz : `zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)` : que vaut ensuite `info.compress_type` ?
- [ ] `0` : l'argument ne vaut que pour l'écriture
- [x] `8` : l'argument est écrit dans `info`
- [ ] `None`
- [ ] `TypeError` : argument refusé avec un `ZipInfo`
- Réponse : `8` (`ZIP_DEFLATED`, mesuré) : `writestr` modifie le `ZipInfo` reçu ; réutiliser le même objet pour une autre entrée garde ce réglage.

## 10. external_attr : les droits Unix d'une entrée
- Id : archives-external-attr-droits
- Sous-thème : zipinfo
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : archives-zipinfo-date-fixe
- Voir aussi : archives-external-attr-type-fichier
- Mots-clés : droits Unix, umask, Lambda
- Source : data-platform · S1-07
- Définition : `info.external_attr = 0o644 << 16` donne à l'entrée les droits `rw-r--r--` ; les 16 bits hauts portent le mode Unix, comme `st_mode`.
- Contexte : Sans valeur, `writestr` met `0o600` : fichier lisible par son seul propriétaire après extraction par `unzip`. Lambda exécute le code sous un autre utilisateur que le propriétaire des fichiers : AWS exige des fichiers lisibles par tous (644, dossiers 755), sinon l'import échoue à l'invocation. Le script de build fixe donc les droits sur chaque entrée, sans dépendre du `umask` du poste.
- Usage : ✅ `0o644 << 16` pour du code, `0o755 << 16` pour un exécutable (`bootstrap` d'un runtime custom) · ❌ le défaut `0o600` dans un zip de Lambda.

```python
# Exemple 1 : défaut et valeur fixée
import io, zipfile
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("a.py", "x = 1")
    i = zipfile.ZipInfo("b.py")
    i.external_attr = 0o644 << 16
    zf.writestr(i, "x = 1")
z = zipfile.ZipFile(buf)
oct(z.getinfo("a.py").external_attr >> 16)
# → '0o600'
oct(z.getinfo("b.py").external_attr >> 16)
# → '0o644'
```

- Quiz : `i.external_attr = 0o644`, sans `<< 16` : quels droits `unzip -Z` affiche-t-il ?
- [ ] `-rw-r--r--`
- [ ] `?rw-r--r--`
- [x] `?---------`
- [ ] `-rw-------`
- Réponse : `?---------` (mesuré) : `0o644` tombe dans les 16 bits bas (attributs MS-DOS) ; la partie Unix reste à zéro, aucun droit.

## 11. ordre des entrées : trier les fichiers
- Id : archives-ordre-des-entrees
- Sous-thème : reproductible
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : archives-zipfile-ecrire
- Voir aussi : archives-zip-reproductible-recette
- Mots-clés : rglob, sha256, runner CI
- Source : data-platform · S1-07
- Définition : L'ordre d'ajout fixe l'ordre des entrées, donc les octets : un zip reproductible ajoute ses fichiers triés (`sorted(src.rglob("*"))`).
- Contexte : `rglob`, `os.listdir` et `os.walk` rendent l'ordre du système de fichiers, sans garantie : APFS sur le Mac et ext4 sur un runner CI peuvent différer. Deux zips avec les mêmes entrées dans un autre ordre ont un sha256 différent, même avec des dates fixes. Trier des `Path` compare leurs parties une à une : ordre stable d'une machine à l'autre.
- Usage : ✅ `sorted(...)` avant toute boucle d'écriture d'archive ou de hash d'un dossier · ❌ se fier à l'ordre de `rglob` parce qu'il paraît alphabétique en local.

```python
# Exemple 1 : mêmes entrées, autre ordre
import io, zipfile
def build(noms):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n in noms:
            zf.writestr(zipfile.ZipInfo(n), n)
    return buf.getvalue()
a = build(["a.py", "b.py"])
b = build(["b.py", "a.py"])
len(a) == len(b)   # → True
a == b             # → False
```

- Quiz : Que vaut `sorted([Path("pkg-x/a.py"), Path("pkg/b.py")])[0]` ?
- [ ] `Path('pkg-x/a.py')` : `-` avant `/`
- [x] `Path('pkg/b.py')`
- [ ] `TypeError` : `Path` non comparable
- [ ] Dépend du système de fichiers
- Réponse : `Path('pkg/b.py')` (mesuré) : les `Path` se comparent partie par partie (`'pkg'` < `'pkg-x'`) ; trier les chaînes donnerait l'inverse, car `-` précède `/`.

## 12. zip reproductible : la recette
- Id : archives-zip-reproductible-recette
- Sous-thème : reproductible
- Type : recette
- Niveau : 2
- Profils : ops, data
- Prérequis : archives-zipinfo-date-fixe, archives-ordre-des-entrees, archives-external-attr-droits
- Voir aussi : compression-mtime-zero
- Mots-clés : source_code_hash, __pycache__, umask, artefact
- Source : data-platform · S1-07
- Définition : Mêmes fichiers, mêmes octets : entrées triées, noms relatifs, date et droits fixes, compression explicite, et rien de généré (`__pycache__`).
- Contexte : Chaque source de variation casse l'empreinte : date (horloge ou `mtime`), ordre (système de fichiers), droits (`umask`), fichiers générés (`.pyc`, métadonnées d'installation avec un chemin absolu). Le contrôle : construire deux fois et comparer (`cmp`, sha256). C'est la condition pour que `source_code_hash` ne bouge qu'avec le code, et pour ranger l'artefact sous son hash.
- Usage : ✅ build de Lambda, couche, artefact promu entre environnements · ❌ zip jetable lu par un humain : `shutil.make_archive` suffit.

```python
# Exemple 1 : write_zip, simplifié
import hashlib, io, tempfile, zipfile
from pathlib import Path
src = Path(tempfile.mkdtemp())
(src / "pkg/__pycache__").mkdir(parents=True)
(src / "pkg/h.py").write_text("x = 1")
(src / "pkg/__pycache__/h.pyc").write_text("")
def build():
    fs = sorted(p for p in src.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for p in fs:
            i = zipfile.ZipInfo(p.relative_to(src).as_posix())
            i.external_attr = 0o644 << 16
            zf.writestr(i, p.read_bytes(), zipfile.ZIP_DEFLATED)
    return hashlib.sha256(buf.getvalue()).hexdigest()
build() == build()   # → True
```

- Quiz : Même dossier copié ailleurs (`cp -r`, nouvelles dates) puis zippé avec `zf.write(p, nom)` trié : même sha256 que l'original ?
- [ ] Oui : même contenu, même ordre
- [x] Non : `write` copie les `mtime`, qui ont changé
- [ ] Oui, si la compression est la même
- [ ] Non : le chemin absolu est dans le zip
- Réponse : non (mesuré avec `os.utime`) : `write` reprend la date de chaque fichier ; seul un `ZipInfo` à date fixe passé à `writestr` en libère le zip.

## 13. doublon : deux entrées du même nom
- Id : archives-doublon-meme-nom
- Sous-thème : écrire
- Type : piège
- Niveau : 2
- Profils : ops
- Mots-clés : warning
- Source : data-platform · S1-07
- Définition : Écrire deux fois le même nom ajoute une seconde entrée, avec un `UserWarning` : l'archive garde les deux, et `read` rend la dernière.
- Contexte : zipfile n'écrase jamais une entrée : on écrit à la suite. Le zip grossit, `namelist()` montre le doublon, et selon l'outil d'extraction c'est la première ou la dernière qui gagne. Arrive quand deux paquets installent le même module, ou quand une boucle ajoute un dossier deux fois.
- Usage : ✅ dédoublonner les noms avant l'écriture, ou lever une erreur explicite · ❌ réécrire une entrée pour la « remplacer » : il faut reconstruire l'archive.

```python
# Exemple 1 : le doublon reste
import io, warnings, zipfile
buf = io.BytesIO()
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.py", "v1")
        zf.writestr("a.py", "v2")
str(w[0].message)   # → "Duplicate name: 'a.py'"
z = zipfile.ZipFile(buf)
z.namelist()        # → ['a.py', 'a.py']
z.read("a.py")      # → b'v2'
```

- Quiz : Avec `warnings.simplefilter("error")`, que fait le second `writestr("a.py", …)` ?
- [ ] Écrase la première entrée sans rien dire
- [x] Lève `UserWarning` comme une exception
- [ ] Lève `FileExistsError`
- [ ] Ajoute l'entrée, l'avertissement est ignoré
- Réponse : lève `UserWarning` (mesuré) : le filtre `"error"` transforme tout avertissement en exception ; pratique en test pour attraper les doublons du build.

## 14. extractall : ../ neutralisé
- Id : archives-extractall-zip-slip
- Sous-thème : lire
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : archives-zipfile-lire
- Voir aussi : archives-write-arcname
- Mots-clés : tarfile, lien symbolique
- Source : data-platform · S1-07
- Définition : `extractall(dest)` nettoie les noms dangereux : `../` et `/` de tête sont retirés, une entrée ne s'écrit jamais hors de `dest`.
- Contexte : Une archive hostile peut contenir `../../.bashrc` (« zip slip »). zipfile s'en protège à l'extraction, pas à l'écriture : `namelist()` montre encore `../evil.py`. `tarfile.extractall` n'avait pas cette protection avant le paramètre `filter` (Python 3.12, `filter="data"`). Les liens symboliques ne sont pas recréés, et les droits Unix de l'archive ne sont pas appliqués.
- Usage : ✅ extraire un zip reçu de l'extérieur dans un dossier temporaire dédié · ❌ `tarfile.extractall` sans `filter="data"` sur une archive non maîtrisée.

```python
# Exemple 1 : ../ neutralisé
import io, tempfile, zipfile
from pathlib import Path
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("../evil.py", "x = 1")
dest = Path(tempfile.mkdtemp()) / "out"
zipfile.ZipFile(buf).extractall(dest)
(dest / "evil.py").exists()         # → True
(dest.parent / "evil.py").exists()  # → False
```

- Quiz : L'archive contient l'entrée `/tmp/x.py` (chemin absolu) : où `extractall(dest)` l'écrit-il ?
- [ ] `/tmp/x.py`
- [x] `dest/tmp/x.py`
- [ ] `dest/x.py`
- [ ] `ValueError` : chemin absolu
- Réponse : `dest/tmp/x.py` (mesuré) : le `/` de tête est retiré et le nom devient relatif à `dest`, alors que `namelist()` montre encore `/tmp/x.py`.

## 15. external_attr : le type de fichier
- Id : archives-external-attr-type-fichier
- Sous-thème : zipinfo
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Prérequis : archives-external-attr-droits
- Mots-clés : st_mode, droits Unix
- Source : data-platform · S1-07
- Définition : Le mode complet d'un fichier ordinaire est `0o100644` (`S_IFREG | 0o644`) ; `0o644 << 16` seul omet le type, et `unzip -Z` affiche `?rw-r--r--`.
- Contexte : Les 16 bits hauts d'`external_attr` reprennent `st_mode` en entier, type compris (fichier `0o100000`, dossier `0o040000`, lien `0o120000`). `ZipInfo.from_file` copie ce mode du disque. Le zip de l'étape montre `?rw-r--r--` : les outils traitent une entrée sans type comme un fichier, ce n'est pas bloquant, mais `(S_IFREG | 0o644) << 16` est la forme canonique.
- Usage : ✅ `(stat.S_IFREG | 0o644) << 16` pour un zip sans ambiguïté · ❌ lire le type d'une entrée dans `external_attr` sans vérifier qu'il a été écrit : `is_dir()` se fie au `/` final.

```python
# Exemple 1 : le type dans le mode
import stat, zipfile
i = zipfile.ZipInfo("handler.py")
i.external_attr = 0o644 << 16
stat.S_ISREG(i.external_attr >> 16)  # → False
i.external_attr = (stat.S_IFREG | 0o644) << 16
stat.S_ISREG(i.external_attr >> 16)  # → True
oct(i.external_attr >> 16)  # → '0o100644'
```

- Quiz : Que rend `stat.filemode(0o100755)` ?
- [ ] `'drwxr-xr-x'`
- [ ] `'?rwxr-xr-x'`
- [ ] `'-rw-r--r--'`
- [x] `'-rwxr-xr-x'`
- Réponse : `'-rwxr-xr-x'` (mesuré) : `0o100000` = fichier ordinaire (`-`), `755` = `rwx` pour le propriétaire, `r-x` pour les autres.

## 16. date_time : une précision de 2 secondes
- Id : archives-date-time-deux-secondes
- Sous-thème : zipinfo
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : archives-zipinfo-date-fixe
- Mots-clés : mtime, timestamp Unix
- Source : data-platform · S1-07
- Définition : Le format DOS du zip stocke les secondes par pas de 2 : une entrée datée 10:00:07 est relue 10:00:06.
- Contexte : L'heure DOS tient sur 16 bits (heures, minutes, secondes divisées par 2), la date sur 16 autres (année depuis 1980, mois, jour). Ni fuseau ni sous-seconde. Comparer `date_time` au `mtime` du fichier source échoue donc d'une seconde une fois sur deux. Python n'ajoute pas de champ supplémentaire (`extra` vide), contrairement à la commande `zip` qui écrit aussi un horodatage Unix.
- Usage : ✅ date fixe paire, comparaisons de dates zip à 2 s près · ❌ détecter un changement de fichier par la date d'une entrée : comparer les octets ou un hash.

```python
# Exemple 1 : 7 s relues 6 s
import io, zipfile
buf = io.BytesIO()
t = (2026, 10, 25, 10, 0, 7)
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr(zipfile.ZipInfo("a", t), "x")
zipfile.ZipFile(buf).getinfo("a").date_time
# → (2026, 10, 25, 10, 0, 6)
```

- Quiz : Que vaut `zipfile.ZipInfo("a", (2026, 10, 25, 10, 0, 7)).date_time`, avant toute écriture ?
- [ ] `(2026, 10, 25, 10, 0, 6)`
- [x] `(2026, 10, 25, 10, 0, 7)`
- [ ] `ValueError` : seconde impaire
- [ ] `(2026, 10, 25, 10, 0, 8)`
- Réponse : `(…, 7)` (mesuré) : `ZipInfo` garde le tuple tel quel ; l'arrondi n'a lieu qu'à l'encodage DOS, lors de l'écriture.

## 17. ZipFile.open("w") : écrire en flux
- Id : archives-open-ecrire-en-flux
- Sous-thème : écrire
- Type : recette
- Niveau : 3
- Profils : data, expert
- Prérequis : archives-zipfile-ecrire
- Voir aussi : compression-gzipfile-en-flux
- Mots-clés : en flux, ZIP64
- Source : data-platform · S1-07
- Définition : `zf.open(info, "w")` rend un fichier où écrire une entrée par morceaux, sans charger tout son contenu en mémoire comme `writestr`.
- Contexte : `writestr(info, p.read_bytes())` lit chaque fichier en entier : ça va pour le code d'une Lambda (quelques Mo par fichier), pas pour une entrée de plusieurs Go. `open("w")` s'emploie avec `shutil.copyfileobj` ; la taille n'étant pas connue d'avance, une entrée qui peut dépasser 2 Gio exige `force_zip64=True`.
- Usage : ✅ gros fichiers (export, jeu de données) à archiver sans pic mémoire · ❌ petits fichiers de code : `writestr`, plus court.

```python
# Exemple 1 : copier en flux
import io, shutil, zipfile
src = io.BytesIO(b"552100554\n" * 10_000)
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    info = zipfile.ZipInfo("sirens.txt")
    with zf.open(info, "w") as dst:
        shutil.copyfileobj(src, dst)
zipfile.ZipFile(buf).getinfo("sirens.txt").file_size
# → 100000
```

- Quiz : Pendant le `with zf.open(info, "w")`, que fait `zf.writestr("b.txt", "x")` ?
- [ ] Écrit `b.txt` après `sirens.txt`
- [ ] Écrit `b.txt` au milieu de `sirens.txt`
- [x] `ValueError`
- [ ] Attend la fermeture de `dst`
- Réponse : `ValueError` (mesuré : « an open writing handle exists ») : une seule entrée peut être en cours d'écriture à la fois.
