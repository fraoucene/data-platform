---
title: "Cartes · Fichiers temporaires Python"
type: cartes
langage: Python
chapitre: Fichiers et formats
cours: Fichiers temporaires
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Fichiers temporaires Python
Python · Fichiers temporaires (module tempfile) : dossiers, fichiers, emplacement (format spec v4 de revision-pwa).

## 1. TemporaryDirectory : un dossier jetable
- Id : fichiers-temporaires-temporarydirectory-jetable
- Sous-thème : dossiers
- Type : recette
- Niveau : 1
- Profils : débutant, data, ops
- Prérequis : context-managers-with-open-ferme
- Voir aussi : fichiers-temporaires-chemin-mort
- Mots-clés : context manager, Lambda, fixture pytest, Parquet
- Définition : `with tempfile.TemporaryDirectory() as d:` crée un dossier temporaire et le supprime avec tout son contenu à la sortie du bloc.
- Contexte : Pratique pour un traitement qui écrit des fichiers intermédiaires (télécharger, décompresser, convertir en Parquet, puis envoyer sur S3) sans rien laisser derrière, même sur erreur. Dans une Lambda, seul `/tmp` est accessible en écriture et il est conservé entre invocations du même conteneur : le nettoyer compte. Le `as` reçoit un `str`, pas un `Path`.
- Usage : ✅ fichiers de travail d'un script ou d'une Lambda · ❌ dans pytest : la fixture `tmp_path` (un `Path`, nettoyé par pytest) ; fichier à garder : un vrai chemin.

```python
# Exemple 1 : supprimé à la sortie
import os, tempfile
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "j.jsonl")
    open(p, "w").close()
    vu = os.path.exists(p)
(vu, os.path.exists(d))  # → (True, False)
```

```python
# Exemple 2 : une partition de travail
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as d:
    (Path(d) / "dt=2026-10-23").mkdir()
    noms = [x.name for x in Path(d).iterdir()]
noms     # → ["dt=2026-10-23"]
```

- Quiz : Dans `with TemporaryDirectory() as d:`, que fait `d / "j.jsonl"` ?
- [ ] Renvoie un `Path`
- [x] Lève `TypeError`
- [ ] Renvoie `"d/j.jsonl"`
- [ ] Lève `AttributeError`
- Réponse : `TypeError` (unsupported operand / for str) : `d` est un `str` ; écrire `Path(d) / "j.jsonl"` ou `os.path.join`.

## 2. mkdtemp : un dossier que personne ne supprime
- Id : fichiers-temporaires-mkdtemp-sans-nettoyage
- Sous-thème : dossiers
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : fichiers-temporaires-temporarydirectory-jetable
- Mots-clés : atomique, droits Unix, Lambda
- Source : data-platform · S1-07
- Définition : `tempfile.mkdtemp()` crée un dossier au nom unique et renvoie son chemin (`str`) ; c'est à l'appelant de le supprimer.
- Contexte : Le nom est tiré au hasard et la création est atomique : deux processus n'obtiennent jamais le même dossier. Les droits sont `700` (lisible par son seul propriétaire). Rien ne le nettoie : ni la sortie d'une fonction, ni la fin du processus. Pour un dossier de travail jetable, `TemporaryDirectory()` fait la même création et la suppression.
- Usage : ✅ dossier qui doit survivre à la fonction (renvoyé à l'appelant, inspecté après coup) · ❌ fichiers de travail dans une Lambda : `/tmp` se remplit d'une invocation à l'autre ; `TemporaryDirectory()`.

```python
# Exemple 1 : créé, puis laissé
import os, tempfile
d = tempfile.mkdtemp(prefix="bodacc-")
os.path.isdir(d)  # → True
os.path.basename(d).startswith("bodacc-")
# → True
oct(os.stat(d).st_mode)[-3:]  # → "700"
os.rmdir(d)  # à faire soi-même
```

- Quiz : Une fonction appelle `tempfile.mkdtemp()` et se termine par une exception : que devient le dossier ?
- [ ] Supprimé à la sortie de la fonction
- [ ] Supprimé à la fin du processus
- [x] Il reste sur le disque
- [ ] Supprimé au prochain `mkdtemp`
- Réponse : il reste : `mkdtemp` n'a aucun nettoyage ; seuls `TemporaryDirectory` (en `with` ou `cleanup()`) ou un `shutil.rmtree` le suppriment.

## 3. gettempdir : où vont les fichiers temporaires
- Id : fichiers-temporaires-gettempdir-emplacement
- Sous-thème : emplacement
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : variable d'environnement, Lambda, conteneur
- Source : data-platform · S1-07
- Définition : `tempfile.gettempdir()` renvoie le dossier temporaire par défaut : `TMPDIR` s'il est posé et accessible en écriture, sinon `/tmp` (ou équivalent).
- Contexte : Ordre de recherche : `TMPDIR`, `TEMP`, `TMP`, puis `/tmp`, `/var/tmp`, `/usr/tmp`, enfin le dossier courant ; le premier où l'on peut écrire gagne. Sur macOS, `TMPDIR` vise un dossier par utilisateur sous `/var/folders/…` ; dans une Lambda, c'est `/tmp`, seul disque inscriptible. Tous les `mkdtemp`, `TemporaryDirectory` et `NamedTemporaryFile` sans `dir=` y écrivent.
- Usage : ✅ lire l'emplacement pour un log ou un message d'erreur · ❌ écrire `/tmp` en dur : faux sur macOS et dans certains conteneurs ; `gettempdir()` ou `dir=`.

```python
# Exemple 1 : le dossier par défaut
import os, tempfile
base = tempfile.gettempdir()
os.path.isdir(base)  # → True
d = tempfile.mkdtemp()
os.path.dirname(d) == base  # → True
os.rmdir(d)
```

- Quiz : `TMPDIR=/var` (dossier qui existe mais où l'on ne peut pas écrire) : que renvoie `gettempdir()` sur un poste où `TEMP` et `TMP` sont absents ?
- [ ] `"/var"`
- [x] `"/tmp"`
- [ ] `PermissionError`
- [ ] Le dossier courant
- Réponse : `"/tmp"` (mesuré) : un candidat où l'écriture échoue est sauté ; `/tmp` vient ensuite dans la liste.

## 4. prefix et suffix : des noms lisibles
- Id : fichiers-temporaires-prefix-suffix
- Sous-thème : fichiers
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Mots-clés : clé S3, Content-Type
- Source : data-platform · S1-07
- Définition : `prefix=` et `suffix=` encadrent la partie aléatoire du nom : `prefix="bodacc-"`, `suffix=".jsonl.gz"` donne `bodacc-k3j9x2a1.jsonl.gz`.
- Contexte : Toutes les fonctions de `tempfile` les acceptent. Le préfixe aide à repérer qui laisse traîner des fichiers dans `/tmp` ; le suffixe donne une extension aux outils qui la regardent (`gzip`, un `ContentType` deviné). Aucun séparateur n'est ajouté : il faut mettre soi-même le tiret ou le point. La partie aléatoire reste au milieu, le nom n'est donc jamais stable.
- Usage : ✅ `prefix` par programme, `suffix` pour l'extension · ❌ le nom temporaire dans une clé S3 ou un en-tête : il change à chaque fois.

```python
# Exemple 1 : préfixe et suffixe
import os, tempfile
with tempfile.TemporaryDirectory(
        prefix="bodacc-", suffix="-2026") as d:
    nom = os.path.basename(d)
nom.startswith("bodacc-")  # → True
nom.endswith("-2026")  # → True
```

- Quiz : `NamedTemporaryFile(suffix="gz")` (sans point) : comment se termine le nom du fichier ?
- [ ] Par `.gz` : le point est ajouté
- [x] Par `gz`, collé à la partie aléatoire
- [ ] `ValueError` : extension invalide
- Réponse : par `gz` collé (`tmpk3j9x2gz`) : le suffixe est ajouté tel quel ; écrire `suffix=".gz"`.

## 5. mode "w+b" : binaire par défaut
- Id : fichiers-temporaires-mode-binaire
- Sous-thème : fichiers
- Type : piège
- Niveau : 1
- Profils : débutant, data
- Voir aussi : fichiers-temporaires-namedtemporaryfile-nom-aleatoire
- Mots-clés : bytes, seek, encodage
- Source : data-platform · S1-07
- Définition : `NamedTemporaryFile()` et `TemporaryFile()` s'ouvrent par défaut en `"w+b"` : écriture et lecture d'octets ; écrire une `str` lève `TypeError`.
- Contexte : À l'inverse d'`open(p, "w")`, texte par défaut. `mode="w+"` (avec `encoding="utf-8"`) donne un fichier texte. Le `+` permet de relire ce qu'on vient d'écrire, après un `seek(0)` : la position est en fin de fichier après l'écriture. `t.mode` affiche `"rb+"`, autre écriture du même mode.
- Usage : ✅ binaire pour un `.gz` ou un upload S3 · ❌ `t.write(json.dumps(…))` sans `mode="w+"` ni `.encode()`.

```python
# Exemple 1 : str refusée, octets acceptés
import tempfile
with tempfile.NamedTemporaryFile() as t:
    t.mode  # → "rb+"
    t.write(b"A1\n")  # → 3
    t.seek(0)
    t.read()  # → b"A1\n"
    t.write("A2\n")  # ❌ TypeError
```

- Quiz : Même fichier, `t.write(b"A1\n")` puis `t.read()` **sans** `seek(0)` : que renvoie `read` ?
- [ ] `b"A1\n"`
- [x] `b""`
- [ ] `"A1\n"`
- [ ] `io.UnsupportedOperation`
- Réponse : `b""` : après l'écriture, la position est en fin de fichier ; `read` part de là. `seek(0)` revient au début.

## 6. NamedTemporaryFile : un nom aléatoire
- Id : fichiers-temporaires-namedtemporaryfile-nom-aleatoire
- Sous-thème : fichiers
- Type : concept
- Niveau : 2
- Profils : data, ops
- Mots-clés : context manager, partition, en-tête gzip, Lambda
- Source : data-platform · S1-07
- Définition : `tempfile.NamedTemporaryFile()` crée un fichier au nom aléatoire (`tmpk3j9x…`) et le supprime à la sortie du `with`, sauf `delete=False`.
- Contexte : Utile en Lambda pour écrire une partition dans `/tmp` avant l'envoi S3. Deux pièges : le nom change à chaque invocation (il finit dans l'en-tête gzip si l'on oublie `filename=""`), et le fichier disparaît à la sortie du bloc, donc l'envoi doit se faire dedans ou avec `delete=False`. `suffix=".jsonl.gz"` donne une extension lisible.
- Usage : ✅ fichier de travail dans `/tmp`, avec `delete=False` si un autre bloc le lit · ❌ compter sur le nom du fichier temporaire pour quoi que ce soit de stable (clé S3, en-tête).

```python
# Exemple 1 : supprimé à la sortie
import tempfile
from pathlib import Path
with tempfile.NamedTemporaryFile() as t:
    nom = Path(t.name)
    dedans = nom.exists()
dedans, nom.exists()   # → (True, False)
```

```python
# Exemple 2 : garder le fichier
import tempfile
from pathlib import Path

with tempfile.NamedTemporaryFile(
        delete=False, suffix=".jsonl.gz") as t:
    t.write(b"A1\n")
p = Path(t.name)
p.exists(), p.name.endswith(".jsonl.gz")
# → (True, True)
p.unlink()
```

- Quiz : Deux `NamedTemporaryFile()` successifs, sans option : leurs `name` sont-ils égaux ?
- [ ] Oui : même dossier, même préfixe
- [x] Non : chaque nom est tiré au hasard
- [ ] Oui, si le premier est déjà supprimé
- Réponse : Non : chaque nom est tiré au hasard : c'est tout l'intérêt, et la raison pour laquelle il ne doit jamais entrer dans les octets d'un fichier.

## 7. dir= : choisir le dossier parent
- Id : fichiers-temporaires-dir-parent
- Sous-thème : emplacement
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : fichiers-temporaires-gettempdir-emplacement
- Voir aussi : context-managers-ecriture-atomique
- Mots-clés : injection de dépendance, fixture pytest, atomique
- Source : data-platform · S1-07
- Définition : `dir=` place le fichier ou le dossier temporaire dans le dossier donné au lieu de `gettempdir()` ; `None` garde le défaut.
- Contexte : Dans `ingest_day(…, tmp_dir=None)`, le paramètre est passé tel quel à `TemporaryDirectory(dir=tmp_dir)` : la Lambda écrit dans `/tmp`, le test passe `tmp_path` et vérifie que le dossier est vide après une erreur. Utile aussi pour écrire sur le même disque que la destination, condition d'un `os.replace` atomique. Le dossier parent doit exister.
- Usage : ✅ paramètre `dir` injectable pour tester le nettoyage, même disque qu'un renommage · ❌ `dir=` vers un dossier partagé entre invocations sans nettoyage.

```python
# Exemple 1 : le nettoyage se vérifie
import tempfile
from pathlib import Path
parent = Path(tempfile.mkdtemp())  # tmp_path
def ingest(tmp_dir=None):
    with tempfile.TemporaryDirectory(
            dir=tmp_dir) as d:
        (Path(d) / "part.gz").write_bytes(b"x")
        raise ConnectionError("coupé")
ingest(tmp_dir=str(parent))  # ❌ ConnectionError
list(parent.iterdir())  # → []
```

- Quiz : `TemporaryDirectory(dir="/tmp/absent")` quand ce dossier n'existe pas : que se passe-t-il ?
- [ ] Le dossier parent est créé au passage
- [ ] Repli silencieux sur `gettempdir()`
- [x] `FileNotFoundError`
- [ ] `ValueError` : `dir` invalide
- Réponse : `FileNotFoundError` : `tempfile` ne crée pas le parent ; il faut un dossier existant.

## 8. TemporaryFile : un fichier sans nom
- Id : fichiers-temporaires-temporaryfile-sans-nom
- Sous-thème : fichiers
- Type : concept
- Niveau : 2
- Profils : data
- Mots-clés : descripteur de fichier, objet fichier, boto3
- Source : data-platform · S1-07
- Définition : `tempfile.TemporaryFile()` donne un fichier sans nom visible : sous Linux et macOS, il est retiré du dossier dès sa création et disparaît à la fermeture.
- Contexte : Comme le fichier n'a pas de chemin, `t.name` est un simple numéro de descripteur (`int`) : aucun autre programme ne peut l'ouvrir. Parfait pour un tampon qu'on écrit et relit soi-même (`seek(0)`) ; inutilisable si une API demande un chemin, comme `s3.upload_file(chemin, …)`. Dans ce cas : `NamedTemporaryFile`, ou passer l'objet fichier à `upload_fileobj`.
- Usage : ✅ tampon disque privé, passé en objet fichier (`upload_fileobj`, `GzipFile(fileobj=…)`) · ❌ API qui attend un chemin : `NamedTemporaryFile`.

```python
# Exemple 1 : un nom qui n'est qu'un numéro
import tempfile
with tempfile.TemporaryFile() as t:
    type(t.name).__name__  # → "int"
    t.write(b"A1\n")
    t.seek(0)
    t.read()  # → b"A1\n"
```

- Quiz : `s3.upload_file(t.name, "dp-raw", "k")` avec `t = TemporaryFile()` : que reçoit `upload_file` comme chemin ?
- [ ] Le chemin complet du fichier dans `/tmp`
- [x] Un entier, pas un chemin
- [ ] `None`
- Réponse : un entier (le descripteur) : le fichier n'a plus de nom dans le dossier ; utiliser `upload_fileobj(t, …)` après `seek(0)`.

## 9. mkstemp : un descripteur à fermer
- Id : fichiers-temporaires-mkstemp-descripteur
- Sous-thème : fichiers
- Type : piège
- Niveau : 2
- Profils : ops
- Voir aussi : fichiers-temporaires-mktemp-obsolete
- Mots-clés : descripteur de fichier, atomique, conteneur chaud
- Source : data-platform · S1-07
- Définition : `tempfile.mkstemp()` crée un fichier au nom unique et renvoie `(fd, chemin)` : un descripteur bas niveau ouvert, que l'appelant doit fermer et supprimer.
- Contexte : C'est la brique sûre sous `NamedTemporaryFile` : création atomique, droits `600`. Mais `fd` est un entier, pas un objet fichier : l'oublier laisse un descripteur ouvert (une Lambda chaude en a un nombre limité) ; le fichier, lui, reste sur le disque. `os.fdopen(fd, "wb")` l'enveloppe dans un objet fichier qui le fermera.
- Usage : ✅ fichier qui doit survivre, créé sans risque de collision · ❌ fichier de travail : `NamedTemporaryFile` ou `TemporaryDirectory`, qui ferment et suppriment.

```python
# Exemple 1 : fermer, puis supprimer
import os, tempfile
fd, p = tempfile.mkstemp(suffix=".gz")
type(fd).__name__  # → "int"
with os.fdopen(fd, "wb") as f:  # ferme fd
    f.write(b"x")
os.path.getsize(p)  # → 1
os.unlink(p)  # suppression manuelle
```

- Quiz : Que vaut `oct(os.stat(p).st_mode)[-3:]` pour un fichier créé par `mkstemp()` ?
- [ ] `"644"`
- [x] `"600"`
- [ ] `"700"`
- [ ] `"666"`
- Réponse : `"600"` : lecture et écriture pour le seul propriétaire, quel que soit l'`umask` ; c'est une des garanties de `mkstemp`.

## 10. mktemp : un nom, pas un fichier
- Id : fichiers-temporaires-mktemp-obsolete
- Sous-thème : fichiers
- Type : piège
- Niveau : 2
- Profils : ops
- Voir aussi : fichiers-temporaires-mkstemp-descripteur
- Mots-clés : TOCTOU
- Source : data-platform · S1-07
- Définition : `tempfile.mktemp()` renvoie seulement un nom libre au moment de l'appel, sans rien créer : obsolète, car un autre processus peut créer ce fichier avant vous.
- Contexte : Entre l'obtention du nom et l'`open`, la place est libre : course classique (TOCTOU), exploitable sur un `/tmp` partagé. La doc le marque obsolète depuis longtemps, mais l'appel ne lève aucun avertissement (mesuré en 3.12) : il passe en revue de code. Les fonctions sûres créent le fichier en même temps qu'elles choisissent le nom : `mkstemp`, `NamedTemporaryFile`, `mkdtemp`.
- Usage : ✅ jamais dans du code neuf · ❌ `mktemp()` pour un fichier de travail, même dans un test : `tmp_path`, `NamedTemporaryFile` ou un chemin dans `TemporaryDirectory`.

```python
# Exemple 1 : rien n'est créé
import os, tempfile
p = tempfile.mktemp(suffix=".gz")
os.path.exists(p)  # → False
```

```python
# Exemple 2 : la version sûre
import os, tempfile
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "part.gz")
    open(p, "wb").close()
    os.path.exists(p)  # → True
```

- Quiz : Ruff signale-t-il `tempfile.mktemp()` ?
- [x] Oui : règle `S306` (flake8-bandit)
- [ ] Non : la fonction n'émet aucun avertissement
- [ ] Oui, mais seulement en Python 3.13
- Réponse : oui, `S306` (suspicious-mktemp-usage) dans les règles `S` : le linter compense l'absence d'avertissement à l'exécution.

## 11. TemporaryDirectory : ne pas renvoyer un chemin du dedans
- Id : fichiers-temporaires-chemin-mort
- Sous-thème : dossiers
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : fichiers-temporaires-temporarydirectory-jetable
- Mots-clés : context manager, sha256
- Source : data-platform · S1-07
- Définition : Un chemin pris dans un `TemporaryDirectory` ne vaut que dans le `with` : renvoyé par la fonction, il pointe vers un fichier déjà supprimé.
- Contexte : Le `return` dans le `with` déclenche d'abord la sortie du bloc, donc la suppression du dossier, puis rend la valeur. L'appelant reçoit un chemin mort et l'erreur sort plus loin (`FileNotFoundError` à l'upload). D'où, dans `ingest_day`, l'écriture **et** la publication S3 dans le même bloc, et un résultat fait de valeurs (`count`, `sha256`), pas de chemins.
- Usage : ✅ tout ce qui lit le fichier (upload, hash) à l'intérieur du `with` · ❌ `return chemin` depuis le bloc : renvoyer le contenu, un résumé ou passer un `dir=` qui survit.

```python
# Exemple 1 : un chemin mort
import os, tempfile
def ecrire():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "part.gz")
        open(p, "wb").close()
        return p  # le with sort d'abord
p = ecrire()
os.path.exists(p)  # → False
open(p, "rb")  # ❌ FileNotFoundError
```

- Quiz : Même fonction, mais `return open(p, "rb")` (le fichier ouvert) : que donne `ecrire().read()` sous Linux ou macOS ?
- [x] `b""` : le contenu du fichier, vide ici
- [ ] `FileNotFoundError` à l'appel de `read`
- [ ] `ValueError: I/O operation on closed file`
- Réponse : `b""` : un fichier ouvert reste lisible après sa suppression du dossier (le nom part, pas les données) ; c'est fragile et propre à POSIX, mieux vaut lire dans le `with`.

## 12. NamedTemporaryFile : delete_on_close=False
- Id : fichiers-temporaires-delete-on-close
- Sous-thème : fichiers
- Type : recette
- Niveau : 3
- Profils : ops, expert
- Prérequis : fichiers-temporaires-namedtemporaryfile-nom-aleatoire
- Mots-clés : context manager, tampon, boto3
- Source : data-platform · S1-07
- Définition : Depuis 3.12, `NamedTemporaryFile(delete_on_close=False)` garde le fichier après `close()` et ne le supprime qu'à la sortie du `with`.
- Contexte : Par défaut, fermer le fichier le supprime : impossible d'écrire, fermer pour vider les tampons, puis passer le chemin à une API qui le rouvre (`upload_file`, un outil externe, Windows qui refuse une double ouverture). `delete=False` réglait ça en laissant le fichier pour toujours ; `delete_on_close=False` ferme sans supprimer et garde le nettoyage du `with`.
- Usage : ✅ écrire, fermer, puis `s3.upload_file(t.name, …)` dans le même `with` · ❌ `delete=False` sans `unlink` : le fichier reste dans `/tmp`.

```python
# Exemple 1 : fermé mais encore là
import os, tempfile
with tempfile.NamedTemporaryFile(
        delete_on_close=False) as t:
    t.write(b"A1\n")
    t.close()  # tampons vidés
    open(t.name, "rb").read()  # → b"A1\n"
os.path.exists(t.name)  # → False
```

- Quiz : Sans l'option (défaut), `t.close()` dans le `with`, puis `os.path.exists(t.name)` juste après : que vaut-il ?
- [ ] `True` : supprimé seulement à la sortie du `with`
- [x] `False` : supprimé à la fermeture
- [ ] `ValueError` : fichier fermé
- Réponse : `False` (mesuré) : avec `delete=True` et `delete_on_close=True` (défauts), la fermeture supprime le fichier.

## 13. TemporaryDirectory sans with : cleanup()
- Id : fichiers-temporaires-cleanup-sans-with
- Sous-thème : dossiers
- Type : concept
- Niveau : 3
- Profils : expert
- Prérequis : fichiers-temporaires-temporarydirectory-jetable
- Mots-clés : fixture pytest, ramasse-miettes, CPython
- Source : data-platform · S1-07
- Définition : `td = TemporaryDirectory()` crée le dossier tout de suite ; `td.name` donne son chemin et `td.cleanup()` le supprime, appel répétable sans erreur.
- Contexte : Utile quand la durée de vie ne suit pas un bloc : une fixture qui crée en `setup` et nettoie en `teardown`, un objet qui garde son dossier. Oublié, le dossier est supprimé quand l'objet est détruit par le ramasse-miettes, avec un `ResourceWarning` « Implicitly cleaning up » : sur CPython, souvent tôt, mais rien n'est garanti. `with` reste la forme sûre.
- Usage : ✅ `cleanup()` dans un `finally` ou un teardown quand le `with` ne convient pas · ❌ compter sur le ramasse-miettes pour vider `/tmp`.

```python
# Exemple 1 : créer, utiliser, nettoyer
import os, tempfile
td = tempfile.TemporaryDirectory()
os.path.isdir(td.name)  # → True
type(td.name).__name__  # → "str"
td.cleanup()
os.path.exists(td.name)  # → False
td.cleanup()  # 2e appel : sans erreur
```

- Quiz : `d = TemporaryDirectory().name` sur une seule ligne, puis `os.path.isdir(d)` sous CPython : que vaut-il ?
- [ ] `True` : le dossier vit jusqu'à la fin du processus
- [x] `False` : l'objet est détruit aussitôt, le dossier avec
- [ ] `AttributeError` : `name` n'existe qu'en `with`
- Réponse : `False` (mesuré sous CPython) : plus aucune référence à l'objet, son finaliseur supprime le dossier dès la fin de la ligne.

## 14. SpooledTemporaryFile : en mémoire, puis sur disque
- Id : fichiers-temporaires-spooled-bascule-disque
- Sous-thème : fichiers
- Type : concept
- Niveau : 3
- Profils : data, expert
- Prérequis : fichiers-temporaires-temporaryfile-sans-nom
- Mots-clés : BytesIO, descripteur de fichier, Lambda
- Source : data-platform · S1-07
- Définition : `SpooledTemporaryFile(max_size=n)` garde les données en mémoire (`BytesIO`) jusqu'à `n` octets, puis bascule seul vers un vrai fichier temporaire.
- Contexte : Compromis pour une taille inconnue : un petit lot reste en RAM, une grosse journée passe sur disque sans saturer la mémoire de la Lambda. `t._rolled` dit si la bascule a eu lieu ; `t.rollover()` la force. Avant la bascule, il n'y a ni nom ni descripteur. L'interface fichier (`write`, `seek`, `read`) reste la même des deux côtés.
- Usage : ✅ tampon dont la taille varie beaucoup (de quelques Ko à des centaines de Mo) · ❌ besoin d'un chemin (`upload_file`) : `NamedTemporaryFile`.

```python
# Exemple 1 : bascule au-delà de 10 octets
import tempfile
with tempfile.SpooledTemporaryFile(
        max_size=10) as t:
    t.write(b"12345")
    t._rolled  # → False  (en mémoire)
    t.write(b"6789012")
    t._rolled  # → True  (sur disque)
```

- Quiz : `SpooledTemporaryFile(max_size=0)` (la valeur par défaut) : quand bascule-t-il sur disque ?
- [ ] Dès la création
- [ ] À la première écriture
- [x] Jamais : `0` veut dire sans limite
- Réponse : jamais : `max_size=0`, le défaut, garde tout en mémoire quelle que soit la taille ; il faut une valeur positive pour basculer.

## 15. tempdir : lu une fois, puis mis en cache
- Id : fichiers-temporaires-tempdir-mis-en-cache
- Sous-thème : emplacement
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : fichiers-temporaires-gettempdir-emplacement
- Voir aussi : tests-monkeypatch
- Mots-clés : variable d'environnement, monkeypatch
- Source : data-platform · S1-07
- Définition : Le premier `gettempdir()` calcule le dossier et le range dans `tempfile.tempdir` ; un `TMPDIR` changé ensuite est ignoré par tout le module.
- Contexte : Comme un client figé au premier appel : un test qui pose `TMPDIR` avec `monkeypatch.setenv` après qu'une autre partie du code a utilisé `tempfile` ne change rien. Remettre `tempfile.tempdir = None` force un nouveau calcul ; affecter `tempfile.tempdir` directement fixe le dossier pour tout le processus. Plus simple et local : passer `dir=`.
- Usage : ✅ `dir=` explicite (paramètre injectable) pour choisir le dossier dans un test · ❌ `monkeypatch.setenv("TMPDIR", …)` en comptant qu'il soit relu.

```python
# Exemple 1 : TMPDIR changé trop tard
import os, tempfile
avant = tempfile.gettempdir()
autre = tempfile.mkdtemp()
os.environ["TMPDIR"] = autre
tempfile.gettempdir() == avant  # → True
tempfile.tempdir = None  # force le calcul
tempfile.gettempdir() == autre  # → True
del os.environ["TMPDIR"]
tempfile.tempdir = None  # remet l'état
```

- Quiz : Après la ligne `tempfile.tempdir = None` et le recalcul, `TemporaryDirectory()` (sans `dir=`) crée son dossier où ?
- [ ] Dans l'ancien dossier par défaut
- [x] Dans `autre`
- [ ] Dans le dossier courant
- Réponse : dans `autre` : toutes les fonctions sans `dir=` utilisent `gettempdir()`, qui vaut maintenant la nouvelle valeur mise en cache.
