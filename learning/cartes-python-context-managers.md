---
title: "Cartes · Context managers Python"
type: cartes
langage: Python
cours: Context managers
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Context managers Python
Python · Context managers : with, classes, contextlib, async (format spec v3 de revision-pwa).

## 1. with open : fermé à la sortie
- Sous-thème : with
- Niveau : 1
- Définition : `with open(p) as f:` ouvre le fichier et garantit sa fermeture à la fin du bloc, même si une exception survient.
- Contexte : `with` appelle une méthode d'entrée en début de bloc et une méthode de sortie à la fin, quelle que soit la façon d'en sortir : fin normale, `return`, `break` ou exception. Pour un fichier, la sortie fait `close()`, qui vide aussi le tampon d'écriture sur le disque. Sans `with`, un `open` oublié reste ouvert jusqu'au ramasse-miettes, et ce qui est écrit peut ne pas être encore sur le disque.
- Usage : ✅ tout fichier, client HTTP, verrou, connexion : toujours dans un `with` · ❌ `f = open(p)` sans `close` ; `Path.read_text()` suffit pour lire un petit fichier d'un coup.

```python
# Exemple 1 : fermé après le bloc
import os, tempfile
p = os.path.join(tempfile.mkdtemp(), "a.jsonl")
with open(p, "w") as f:
    f.write('{"id": "A1"}\n')
f.closed      # → True
```

```python
# Exemple 2 : fermé même sur erreur
import os, tempfile

p = os.path.join(tempfile.mkdtemp(), "a.txt")
try:
    with open(p, "w") as f:
        raise KeyError("siren")
except KeyError:
    pass
f.closed      # → True
```

- Quiz : Dans `with open(p, "w") as f:`, juste après `f.write("A1")`, que donne `open(p).read()` **dans** le bloc ?
- [ ] `"A1"`
- [x] `""`
- [ ] `ValueError`
- [ ] `PermissionError`
- Réponse : `""` : l'écriture est encore dans le tampon de `f` ; elle n'atteint le disque qu'au `close()` de la sortie du `with` (ou à un `f.flush()`).

## 2. with : l'équivalent de try/finally
- Sous-thème : with
- Niveau : 1
- Définition : `with X() as c:` équivaut à un `try/finally` qui nettoie dans le `finally` : impossible de l'oublier (≈ `using` en TS 5.2).
- Contexte : Sans `with`, chaque ressource demande un `try/finally` à la main ; c'est verbeux et on l'oublie sur le chemin d'erreur. Le `with` déplace ce code dans l'objet : `httpx.Client`, `open`, `threading.Lock`, `tempfile.TemporaryDirectory` savent se fermer. Un objet qui n'a qu'une méthode `close()` sans protocole `with` passe par `contextlib.closing`.
- Usage : ✅ toute ressource qui a un `with` : l'utiliser · ❌ `try/finally` écrit à la main pour un objet qui sait déjà se fermer seul.

```python
# Exemple 1 : à la main, avec finally
import httpx
c = httpx.Client()
try:
    pass             # appels à l'API…
finally:
    c.close()        # même sur erreur
c.is_closed    # → True
```

```python
# Exemple 2 : la même chose avec with
import httpx

with httpx.Client() as c:
    pass             # appels à l'API…
c.is_closed    # → True
```

- Quiz : `def f():` / `with httpx.Client() as c:` / `return c`. Que vaut `f().is_closed` ?
- [x] `True`
- [ ] `False`
- [ ] `None`
- [ ] `AttributeError`
- Réponse : `True` : un `return` sort du bloc, la sortie du `with` ferme le client avant que l'appelant ne le reçoive.

## 3. with : plusieurs ressources
- Sous-thème : with
- Niveau : 1
- Définition : Un seul `with` ouvre plusieurs ressources séparées par des virgules ; elles sont fermées dans l'ordre inverse de leur ouverture.
- Contexte : `with a() as x, b() as y:` équivaut à deux `with` imbriqués : si `b()` échoue, `x` est quand même fermé. Depuis Python 3.10, la liste peut être mise entre parenthèses pour tenir sur plusieurs lignes. L'ordre inverse est voulu : la dernière ressource ouverte, qui dépend souvent de la première, est fermée en premier. Pour un nombre variable de ressources : `ExitStack`.
- Usage : ✅ lire un fichier et en écrire un autre, client + fichier de sortie · ❌ liste de fichiers dont le nombre dépend des données : `contextlib.ExitStack`.

```python
# Exemple 1 : lire et écrire en un with
import tempfile
from pathlib import Path
d = Path(tempfile.mkdtemp())
(d / "in.txt").write_text("A1\n")
with (open(d / "in.txt") as src,
      open(d / "out.txt", "w") as dst):
    dst.write(src.read().lower())
(d / "out.txt").read_text()  # → "a1\n"
```

```python
# Exemple 2 : fermeture en ordre inverse
from contextlib import contextmanager

log = []

@contextmanager
def ressource(nom):
    yield
    log.append(nom)

with (ressource("client"),
      ressource("fichier")):
    pass
log   # → ["fichier", "client"]
```

- Quiz : `with open(a) as x, open(b) as y:` où `b` n'existe pas : dans quel état est `x` après le `FileNotFoundError` ?
- [x] Fermé
- [ ] Ouvert, à fermer à la main
- [ ] Jamais ouvert
- [ ] Ouvert jusqu'au ramasse-miettes
- Réponse : Fermé : c'est l'équivalent de deux `with` imbriqués ; l'échec du second sort du premier, qui ferme `x`.

## 4. with : pas de portée de bloc
- Sous-thème : with
- Niveau : 1
- Définition : Un `with` ne crée pas de portée : la variable du `as` et celles du bloc restent accessibles après, mais la ressource est fermée.
- Contexte : En TS, `const` dans un bloc `{}` disparaît à la fin ; en Python, seuls les fonctions, classes et modules créent une portée. Après le `with`, `f` existe encore mais pointe sur un fichier fermé : le lire lève `ValueError`. Le bon réflexe : extraire les données dans le bloc (liste, dict) et ne garder que ça.
- Usage : ✅ lire ou calculer dans le bloc, utiliser le résultat après · ❌ utiliser l'objet du `as` après le bloc (fichier, flux HTTP) : il est fermé.

```python
# Exemple 1 : as reste défini après
import httpx
with httpx.Client() as c:
    total = 3      # aussi visible après
(c.is_closed, total)   # → (True, 3)
```

```python
# Exemple 2 : extraire dans le bloc
import tempfile
from pathlib import Path

p = Path(tempfile.mkdtemp()) / "j.jsonl"
p.write_text("A1\nA2\n")
with open(p) as f:
    lignes = f.read().splitlines()
lignes        # → ["A1", "A2"]
```

- Quiz : Avec l'exemple 2, que fait `list(f)` **après** le bloc `with` ?
- [ ] `["A1\n", "A2\n"]`
- [ ] `[]`
- [x] `ValueError`
- [ ] `NameError`
- Réponse : `ValueError` (I/O operation on closed file) : le nom `f` existe toujours, mais le fichier a été fermé à la sortie du `with`.

## 5. suppress : ignorer une exception précise
- Sous-thème : contextlib
- Niveau : 1
- Définition : `with contextlib.suppress(E):` avale l'exception `E` levée dans le bloc et continue après le `with`.
- Contexte : Équivaut à `try: … except E: pass`, en une ligne et sans ambiguïté sur l'intention. Le bloc s'arrête à la ligne qui lève : ce qui suit dans le bloc ne s'exécute pas. Seuls les types listés sont avalés, les autres remontent normalement. Plusieurs types : `suppress(KeyError, FileNotFoundError)`.
- Usage : ✅ cas attendu et sans conséquence : supprimer un fichier peut-être absent, lire une clé optionnelle · ❌ `suppress(Exception)` : masque les vrais bugs ; erreur qu'il faut journaliser : `try/except` avec un log.

```python
# Exemple 1 : un fichier peut-être absent
import os
from contextlib import suppress
with suppress(FileNotFoundError):
    os.remove("/tmp/absent-dp-xyz.lock")
"suite"     # → "suite"  (aucune erreur)
```

```python
# Exemple 2 : la fin du bloc est sautée
from contextlib import suppress

log = []
with suppress(KeyError):
    log.append("avant")
    {}["siren"]           # avalée ici
    log.append("après")   # jamais exécuté
log      # → ["avant"]
```

- Quiz : Que fait `with suppress(KeyError): int("483 609")` ?
- [ ] Rien : l'erreur est avalée
- [x] Lève `ValueError`
- [ ] Lève `KeyError`
- [ ] Renvoie `None`
- Réponse : Lève `ValueError` : `int` lève `ValueError`, qui n'est pas dans la liste de `suppress` ; seules les exceptions listées sont avalées.

## 6. __enter__ et __exit__ : un with en classe
- Sous-thème : classes
- Niveau : 2
- Définition : Une classe avec `__enter__` et `__exit__` s'utilise dans `with` : `__exit__` est toujours appelé à la sortie (≈ `using` + `Symbol.dispose` en TS).
- Contexte : `with X() as c` appelle `__enter__()` et lie **sa valeur de retour** à `c`, d'où le `return self`. `__exit__(exc_type, exc, tb)` est appelé même si le bloc lève ; s'il renvoie une valeur vraie, l'exception est avalée. Règle « qui ouvre ferme » : `BodaccClient` ne ferme le `httpx.Client` que s'il l'a créé (`_owns_http`) ; un client injecté reste à l'appelant.
- Usage : ✅ objet qui possède une ressource (connexion HTTP, fichier, verrou) · ❌ simple donnée : `@dataclass` ; ressource ponctuelle dans une fonction : `@contextmanager`.

```python
# Exemple 1 : fermé même sur erreur
class Client:
    def __enter__(self):
        return self       # lié au as
    def __exit__(self, *exc):
        self.ferme = True
try:
    with Client() as c:
        raise KeyError("siren")
except KeyError:
    pass
c.ferme   # → True
```

```python
# Exemple 2 : ne fermer que ce qu'on a créé
class Http:
    ouvert = True
    def close(self):
        self.ouvert = False

class Client:
    def __init__(self, http=None):
        self._owns = http is None
        self._http = http or Http()
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        if self._owns:
            self._http.close()

partage = Http()
with Client(http=partage):
    pass
partage.ouvert   # → True  (à l'appelant)
```

- Quiz : Si `__enter__` oublie `return self`, que vaut `c` dans `with Client() as c:` ?
- [ ] L'instance de `Client`
- [x] `None`
- [ ] `AttributeError` à l'entrée
- [ ] La classe `Client`
- Réponse : `None` : `as` reçoit la valeur renvoyée par `__enter__`, pas l'objet placé après `with`.

## 7. @contextmanager : un with maison
- Sous-thème : contextlib
- Niveau : 2
- Définition : `contextlib.contextmanager` transforme un générateur en gestionnaire `with` : avant `yield` = entrée, après `yield` = sortie (≈ `try/finally` réutilisable).
- Contexte : À l'entrée du `with`, le générateur tourne jusqu'au `yield` ; la valeur produite est liée au `as`. À la sortie, il reprend après le `yield`. Si le corps du `with` lève, l'exception est **relancée au point du `yield`** dans le générateur : sans `try/finally` autour, le code de sortie ne s'exécute pas. Évite d'écrire une classe avec `__enter__` et `__exit__`.
- Usage : ✅ ouvrir / fermer une ressource (lot de traitement, connexion, chrono d'une étape) · ❌ ressource qui a déjà son `with` (`open`, client boto3) : l'utiliser directement.

```python
# Exemple 1 : entrée, corps, sortie
from contextlib import contextmanager
log = []
@contextmanager
def lot(jour):
    log.append(f"ouvre {jour}")
    try:
        yield jour  # valeur du as
    finally:
        log.append("ferme") # toujours
with lot("2026-10-23") as j:
    log.append(j)
log[-1]        # → "ferme"
```

```python
# Exemple 2 : malgré une erreur
from contextlib import contextmanager

log = []

@contextmanager
def lot(jour):
    try:
        yield jour
    finally:
        log.append("ferme")

try:
    with lot("2026-10-23"):
        raise KeyError("siren")
except KeyError:
    pass
log            # → ["ferme"]
```

- Quiz : Sans le `try/finally`, que contient `log` si le corps du `with` lève une exception, dans l'exemple 1 ?
- [ ] `["ouvre 2026-10-23", "ferme"]`
- [x] `["ouvre 2026-10-23"]`
- [ ] `[]`
- [ ] `["ferme"]`
- Réponse : `["ouvre 2026-10-23"]` : l'exception remonte au point du `yield`, la ligne de sortie n'est jamais atteinte.

## 8. __exit__ : avaler l'exception
- Sous-thème : classes
- Niveau : 2
- Définition : Si `__exit__` renvoie une valeur vraie, l'exception du bloc est avalée ; s'il renvoie `None` ou faux, elle continue de remonter.
- Contexte : C'est ainsi que `suppress` est écrit. Le piège : un `return` de `__exit__` écrit pour autre chose (un booléen de succès, un objet) avale toutes les erreurs du bloc sans bruit. La règle : ne rien renvoyer (`None`), sauf intention explicite de masquer une erreur précise, testée sur `exc_type`.
- Usage : ✅ gestionnaire qui ignore volontairement une erreur attendue, en testant son type · ❌ `return True` ou `return self` dans `__exit__` par habitude : toutes les erreurs disparaissent.

```python
# Exemple 1 : True = avalée
class Ignorer:
    def __enter__(self):
        return self
    def __exit__(self, typ, exc, tb):
        return typ is KeyError
with Ignorer():
    {}["siren"]       # avalée
"suite"   # → "suite"
```

```python
# Exemple 2 : un return vrai par erreur
class Log:
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        self.vu = exc[0]
        return self.vu  # ⚠️ une classe = vrai

l = Log()
with l:
    raise ValueError("SIREN")
l.vu is ValueError   # → True  (et avalée)
```

- Quiz : Le bloc lève `ValueError` et `__exit__` n'a pas de `return`. Que devient l'exception ?
- [x] Elle remonte après `__exit__`
- [ ] Elle est avalée
- [ ] Elle devient `TypeError`
- [ ] Elle remonte avant `__exit__`
- Réponse : Elle remonte après `__exit__` : sans `return`, `__exit__` renvoie `None`, faux, donc l'exception continue son chemin une fois le nettoyage fait.

## 9. __exit__ : commit ou rollback
- Sous-thème : classes
- Niveau : 2
- Définition : `__exit__(exc_type, exc, tb)` reçoit l'exception du bloc, ou trois `None` si le bloc s'est terminé sans erreur : de quoi valider ou annuler.
- Contexte : C'est le motif transactionnel : succès → commit, erreur → rollback, puis l'exception continue de remonter (aucun `return`). `exc` est l'objet exception, utile pour journaliser. Le même test sert à écrire un marqueur `_SUCCESS` seulement si la partition a été entièrement écrite, ou à supprimer un fichier temporaire à moitié rempli.
- Usage : ✅ transaction, écriture atomique (fichier temporaire puis renommage), marqueur de fin de lot · ❌ nettoyage identique dans les deux cas : ignorer les arguments (`*exc`).

```python
# Exemple 1 : exc_type dit s'il y a eu erreur
class Lot:
    def __enter__(self):
        return self
    def __exit__(self, typ, exc, tb):
        self.etat = "rollback" if typ else "commit"
with Lot() as ok:
    pass
ok.etat   # → "commit"
```

```python
# Exemple 2 : erreur → rollback, puis remonte
class Lot:
    def __enter__(self):
        return self
    def __exit__(self, typ, exc, tb):
        self.etat = "rollback" if typ else "commit"
        self.err = exc

try:
    with Lot() as l:
        raise ValueError("SIREN")
except ValueError:
    pass
(l.etat, str(l.err))  # → ("rollback", "SIREN")
```

- Quiz : Le bloc est interrompu par Ctrl+C (`KeyboardInterrupt`). `__exit__` est-il appelé ?
- [ ] Non : le processus s'arrête net
- [x] Oui, avec `typ` = `KeyboardInterrupt`
- [ ] Oui, avec `typ` = `None`
- [ ] Non : seulement pour les `Exception`
- Réponse : Oui, avec `KeyboardInterrupt` : `__exit__` reçoit toute `BaseException`, pas seulement les `Exception` ; le rollback a donc lieu.

## 10. closing : un with pour un objet à close()
- Sous-thème : contextlib
- Niveau : 2
- Définition : `contextlib.closing(obj)` donne un `with` à tout objet qui a une méthode `close()` mais pas le protocole `__enter__` / `__exit__`.
- Contexte : Beaucoup d'objets savent se fermer sans être des context managers : vieilles bibliothèques, connexions maison, et surtout les générateurs (`g.close()` exécute leurs `finally`). `closing` appelle `close()` à la sortie, quoi qu'il arrive, et lie l'objet lui-même au `as`. Mettre un tel objet directement dans un `with` lève `TypeError`.
- Usage : ✅ générateur qui tient une ressource et peut être abandonné avant la fin, objet tiers avec `close()` · ❌ objet qui a déjà un `with` (`open`, `httpx.Client`) : l'utiliser directement.

```python
# Exemple 1 : un objet avec close()
from contextlib import closing
class Conn:
    ouverte = True
    def close(self):
        self.ouverte = False
with closing(Conn()) as c:
    pass
c.ouverte     # → False
```

```python
# Exemple 2 : un générateur abandonné tôt
from contextlib import closing

log = []

def lire():
    try:
        yield "A1"
        yield "A2"
    finally:
        log.append("fermé")

with closing(lire()) as g:
    next(g)          # on s'arrête au 1er
log           # → ["fermé"]
```

- Quiz : Dans l'exemple 1, que fait `with Conn() as c:` sans `closing` ?
- [ ] Appelle `close()` à la sortie
- [ ] Ne fait rien de spécial
- [ ] Lève `AttributeError`
- [x] Lève `TypeError`
- Réponse : `TypeError` (does not support the context manager protocol) : `with` exige `__enter__` et `__exit__`, une méthode `close` ne suffit pas.

## 11. redirect_stdout : capturer les print
- Sous-thème : contextlib
- Niveau : 2
- Définition : `with redirect_stdout(buf):` envoie tout ce que `print` écrit vers `buf` (un `io.StringIO`) le temps du bloc.
- Contexte : Le gestionnaire remplace `sys.stdout` par l'objet donné, puis le remet à la sortie, même sur erreur. Utile pour récupérer la sortie d'une fonction qui imprime au lieu de renvoyer (vieux script, outil tiers). Il ne touche qu'à l'objet Python `sys.stdout` : un sous-processus ou une extension C qui écrit sur le descripteur 1 lui échappe. `redirect_stderr` fait de même pour les erreurs.
- Usage : ✅ capturer la sortie d'une fonction tierce, faire taire un outil bavard · ❌ dans pytest : la fixture `capsys`, faite pour ça ; journaliser : le module `logging`, pas `print`.

```python
# Exemple 1 : la sortie dans une chaîne
import io
from contextlib import redirect_stdout
buf = io.StringIO()
with redirect_stdout(buf):
    print("483609327")
buf.getvalue()   # → "483609327\n"
```

```python
# Exemple 2 : la même chose pour stderr
import io, sys
from contextlib import redirect_stderr

err = io.StringIO()
with redirect_stderr(err):
    print("HTTP 429", file=sys.stderr)
err.getvalue()   # → "HTTP 429\n"
```

- Quiz : Dans un `with redirect_stdout(buf):`, que capture `buf` de `subprocess.run(["echo", "x"])` ?
- [ ] `"x\n"`
- [x] Rien : `""`
- [ ] `b"x\n"`
- [ ] `TypeError`
- Réponse : Rien : le sous-processus écrit sur le descripteur 1 du système, pas dans l'objet Python `sys.stdout` remplacé ; passer `capture_output=True` à `run`.

## 12. ExitStack : un nombre variable de with
- Sous-thème : contextlib
- Niveau : 2
- Définition : `contextlib.ExitStack` empile des gestionnaires avec `enter_context()` et des nettoyages avec `callback()` ; tout est défait en ordre inverse à la sortie.
- Contexte : Un `with` écrit en dur ne gère qu'un nombre fixe de ressources. Quand ce nombre vient des données (un fichier par jour, un client par source), `ExitStack` remplace les `with` imbriqués : `enter_context(cm)` entre dans `cm` et renvoie sa valeur `as`. Si une entrée échoue au milieu, celles déjà ouvertes sont fermées. `callback(f, *args)` enregistre n'importe quelle fonction de nettoyage.
- Usage : ✅ N fichiers de sortie (une partition par jour), nettoyages conditionnels · ❌ deux ou trois ressources connues : un `with` à plusieurs éléments, plus lisible.

```python
# Exemple 1 : un fichier par jour
import tempfile
from contextlib import ExitStack
from pathlib import Path
d = Path(tempfile.mkdtemp())
jours = ["2026-10-22", "2026-10-23"]
with ExitStack() as pile:
    fs = [pile.enter_context(
          open(d / f"{j}.jsonl", "w"))
          for j in jours]
    fs[0].write("A1\n")
all(f.closed for f in fs)  # → True
```

```python
# Exemple 2 : des nettoyages arbitraires
from contextlib import ExitStack

log = []
with ExitStack() as pile:
    pile.callback(log.append, "purge tmp")
    pile.callback(log.append, "ferme client")
log  # → ["ferme client", "purge tmp"]
```

- Quiz : Que fait `pile.enter_context(obj)` si `obj` n'a qu'une méthode `close()` ?
- [ ] Appelle `close()` à la sortie
- [ ] L'ignore sans erreur
- [x] Lève `TypeError`
- [ ] Lève `AttributeError`
- Réponse : `TypeError` : `enter_context` exige le protocole `with` ; pour un simple `close()`, `pile.enter_context(closing(obj))` ou `pile.callback(obj.close)`.

## 13. nullcontext : un with optionnel
- Sous-thème : contextlib
- Niveau : 2
- Définition : `contextlib.nullcontext(x)` est un gestionnaire qui ne fait rien : il renvoie `x` au `as` et ne ferme rien à la sortie.
- Contexte : Il évite de dupliquer un bloc selon qu'une ressource doit être ouverte ou non. Cas typique : un client injecté par l'appelant ne doit pas être fermé (règle « qui ouvre ferme »), un client créé ici, si. On choisit le gestionnaire, puis un seul `with`. Sans argument, `nullcontext()` lie `None` au `as`.
- Usage : ✅ ressource tantôt fournie par l'appelant, tantôt créée localement ; verrou optionnel · ❌ toujours la même ressource : la mettre directement dans le `with`.

```python
# Exemple 1 : renvoie la valeur, rien d'autre
from contextlib import nullcontext
with nullcontext("client injecté") as c:
    pass
c      # → "client injecté"
```

```python
# Exemple 2 : ne fermer que ce qu'on crée
import httpx
from contextlib import nullcontext

def lire(http=None):
    cm = (nullcontext(http) if http
          else httpx.Client())
    with cm as c:
        return c

partage = httpx.Client()
lire(partage).is_closed   # → False
lire().is_closed          # → True
```

- Quiz : Que vaut `x` dans `with nullcontext() as x:` ?
- [x] `None`
- [ ] L'objet `nullcontext`
- [ ] `()`
- [ ] `TypeError` : argument manquant
- Réponse : `None` : l'argument `enter_result` vaut `None` par défaut, et c'est lui que `__enter__` renvoie au `as`.

## 14. TemporaryDirectory : un dossier jetable
- Sous-thème : with
- Niveau : 2
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

## 15. __enter__ qui lève : pas de __exit__
- Sous-thème : classes
- Niveau : 3
- Définition : Si `__enter__` lève, le bloc ne s'exécute pas et `__exit__` n'est **pas** appelé : `__enter__` doit nettoyer lui-même ce qu'il a ouvert.
- Contexte : `__exit__` ne protège que le corps du `with`. Un `__enter__` qui ouvre une socket puis échoue à s'authentifier laisse la socket ouverte, puisque personne n'appellera `__exit__`. Règle : `__enter__` fait tout ou rien, avec son propre `try/except` qui défait ce qu'il a déjà fait avant de relancer. Même logique pour `__init__` : s'il lève, rien du protocole n'est appelé.
- Usage : ✅ `__enter__` qui acquiert plusieurs choses (connexion + session) : nettoyer en cas d'échec partiel · ❌ compter sur `__exit__` pour défaire un `__enter__` raté.

```python
# Exemple 1 : __exit__ jamais appelé
log = []
class Client:
    def __enter__(self):
        log.append("connexion")
        raise ConnectionError("auth")
    def __exit__(self, *exc):
        log.append("fermeture")
try:
    with Client():
        pass
except ConnectionError:
    pass
log      # → ["connexion"]
```

```python
# Exemple 2 : __enter__ nettoie lui-même
log = []

class Client:
    def __enter__(self):
        log.append("socket")
        try:
            raise ConnectionError("auth")
        except Exception:
            log.append("ferme socket")
            raise
    def __exit__(self, *exc):
        log.append("fermeture")

try:
    with Client():
        pass
except ConnectionError:
    pass
log  # → ["socket", "ferme socket"]
```

- Quiz : Dans `with Client() as c:`, c'est `__init__` qui lève. Quelles méthodes du protocole sont appelées ?
- [ ] `__enter__` et `__exit__`
- [ ] Seulement `__exit__`
- [x] Aucune
- [ ] Seulement `__enter__`
- Réponse : Aucune : l'objet n'existe même pas ; `Client()` est évalué avant que le `with` ne commence.

## 16. @contextmanager : à usage unique
- Sous-thème : contextlib
- Niveau : 3
- Définition : L'objet renvoyé par une fonction `@contextmanager` ne sert qu'une fois : il enveloppe un générateur, épuisé après le premier `with`.
- Contexte : `lot()` crée un générateur neuf ; le `with` le consomme jusqu'au bout. Rentrer une seconde fois dans le **même** objet échoue (`AttributeError` en Python 3.12). La règle : appeler la fonction à chaque `with` (`with lot():`), ne pas stocker l'objet. Autre contrainte : le générateur doit faire **exactement un** `yield` ; un second lève `RuntimeError` à la sortie.
- Usage : ✅ `with lot(jour):` écrit à chaque utilisation · ❌ `cm = lot()` réutilisé dans une boucle ; gestionnaire réutilisable ou réentrant : une classe à `__enter__` / `__exit__`.

```python
# Exemple 1 : le même objet, deux fois
from contextlib import contextmanager
@contextmanager
def lot():
    yield "lot"
cm = lot()
with cm:
    pass
with cm:
    pass     # ❌ AttributeError
```

```python
# Exemple 2 : un appel par with
from contextlib import contextmanager

n = []

@contextmanager
def lot():
    n.append(1)
    yield

for _ in range(2):
    with lot():      # objet neuf
        pass
len(n)    # → 2
```

- Quiz : Le générateur fait `yield 1` puis `yield 2`. Que fait `with cm(): pass` ?
- [ ] Rien de spécial
- [ ] Lie `2` au `as`
- [x] `RuntimeError` à la sortie
- [ ] `StopIteration` à l'entrée
- Réponse : `RuntimeError` (generator didn't stop) : à la sortie, le générateur doit se terminer ; un second `yield` viole le contrat.

## 17. @contextmanager : aussi un décorateur
- Sous-thème : contextlib
- Niveau : 3
- Définition : Un gestionnaire créé par `@contextmanager` s'utilise aussi en décorateur : `@lot()` exécute toute la fonction décorée dans le `with`.
- Contexte : L'objet renvoyé hérite de `ContextDecorator` : posé avec `@lot()` sur une fonction, il recrée un gestionnaire neuf à chaque appel et y exécute la fonction. Les parenthèses sont obligatoires : `@lot()` crée le gestionnaire, `@lot` passerait la fonction à `lot` comme argument. Limite : la valeur du `yield` n'est pas accessible à la fonction décorée.
- Usage : ✅ entourer toute une fonction (handler de Lambda, étape de pipeline) d'un chrono ou d'un log · ❌ besoin de la valeur `as` dans la fonction : un `with` dans son corps.

```python
# Exemple 1 : le même lot en @
from contextlib import contextmanager
log = []
@contextmanager
def lot():
    log.append("ouvre")
    yield
    log.append("ferme")
@lot()            # avec parenthèses
def ingerer():
    log.append("ingère")
ingerer()
log   # → ["ouvre", "ingère", "ferme"]
```

```python
# Exemple 2 : un with neuf par appel
from contextlib import contextmanager

n = []

@contextmanager
def chrono():
    n.append("start")
    yield

@chrono()
def etape():
    return "ok"

etape(); etape()
len(n)    # → 2
```

- Quiz : Exemple 1 avec `@lot` **sans** parenthèses : que se passe-t-il ?
- [x] `TypeError` dès la définition
- [ ] `TypeError` au premier appel
- [ ] Même résultat qu'avec `@lot()`
- [ ] Seul `"ingère"` est ajouté
- Réponse : `TypeError` dès la définition (lot() takes 0 positional arguments) : `@lot` appelle `lot(ingerer)`, et `lot` n'attend aucun argument.

## 18. async with : __aenter__ et __aexit__
- Sous-thème : async
- Niveau : 3
- Définition : `async with` est le `with` des coroutines : il attend (`await`) `__aenter__` à l'entrée et `__aexit__` à la sortie (≈ `await using` en TS).
- Contexte : Ouvrir ou fermer une connexion réseau asynchrone prend du temps : ces méthodes sont des coroutines, que seul `async with` sait attendre. Un objet asynchrone (`httpx.AsyncClient`) refuse le `with` simple, et un objet synchrone refuse `async with` : `TypeError` dans les deux cas. `async with` n'est permis que dans une `async def`.
- Usage : ✅ `httpx.AsyncClient`, pools de connexions async, verrous `asyncio.Lock` · ❌ code synchrone (Lambda classique, boto3) : `with` simple.

```python
# Exemple 1 : entrée et sortie attendues
import asyncio
class Pool:
    async def __aenter__(self):
        await asyncio.sleep(0)
        return "connexion"
    async def __aexit__(self, *exc):
        self.ferme = True
async def main(p):
    async with p as c:
        return c
p = Pool()
asyncio.run(main(p))   # → "connexion"
p.ferme                # → True
```

```python
# Exemple 2 : un objet sync refuse async with
import asyncio

class Sync:
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        pass

async def main():
    async with Sync():
        pass

asyncio.run(main())   # ❌ TypeError
```

- Quiz : Que se passe-t-il avec `async with` écrit dans une fonction `def` ordinaire ?
- [x] `SyntaxError` à la compilation
- [ ] `TypeError` à l'exécution
- [ ] `RuntimeError` : pas de boucle
- [ ] Il se comporte comme `with`
- Réponse : `SyntaxError` ('async with' outside async function) : le fichier est refusé avant toute exécution.

## 19. @asynccontextmanager : la version async
- Sous-thème : async
- Niveau : 3
- Définition : `contextlib.asynccontextmanager` transforme une `async def` qui fait `yield` en gestionnaire pour `async with`.
- Contexte : Même règle que `@contextmanager` : avant `yield` = entrée, après = sortie, et `try/finally` autour du `yield` pour nettoyer même sur erreur. Le corps peut faire des `await` des deux côtés. Mélanger les versions ne marche pas : `@contextmanager` posé sur une `async def` donne un objet que ni `with` ni `async with` n'acceptent.
- Usage : ✅ fabrique d'un `httpx.AsyncClient` configuré, session asynchrone avec ouverture et fermeture · ❌ code synchrone : `@contextmanager`.

```python
# Exemple 1 : entrée, corps, sortie
import asyncio
from contextlib import asynccontextmanager
log = []
@asynccontextmanager
async def session(nom):
    log.append(f"ouvre {nom}")
    try:
        yield nom
    finally:
        log.append("ferme")
async def main():
    async with session("bodacc") as s:
        log.append(s)
asyncio.run(main())
log  # → ["ouvre bodacc", "bodacc", "ferme"]
```

```python
# Exemple 2 : un AsyncClient configuré
import asyncio, httpx
from contextlib import asynccontextmanager

@asynccontextmanager
async def client():
    t = httpx.MockTransport(
        lambda r: httpx.Response(200))
    async with httpx.AsyncClient(
            transport=t) as c:
        yield c

async def main():
    async with client() as c:
        r = await c.get("https://b.t")
    return r.status_code, c.is_closed

asyncio.run(main())   # → (200, True)
```

- Quiz : `@contextmanager` (la version sync) posé sur `async def session` avec `yield`, puis `async with session():` ?
- [ ] Fonctionne comme `@asynccontextmanager`
- [x] `TypeError`
- [ ] `SyntaxError`
- [ ] Un simple `RuntimeWarning`
- Réponse : `TypeError` (does not support the asynchronous context manager protocol) : `@contextmanager` produit un gestionnaire synchrone, sans `__aenter__`.

## 20. ExitStack.pop_all : garder si tout réussit
- Sous-thème : contextlib
- Niveau : 3
- Définition : `pile.pop_all()` transfère les nettoyages enregistrés vers une nouvelle pile : les ressources restent ouvertes à la sortie du `with`, sauf si une erreur survient avant.
- Contexte : Motif « tout ou rien » : ouvrir N ressources dans un `with ExitStack()` ; si la k-ième échoue, la sortie ferme les k-1 premières ; si tout réussit, `pop_all()` vide la pile courante et rend un `ExitStack` neuf qui porte les nettoyages, à fermer plus tard (`.close()`) par celui qui garde les ressources. C'est ainsi qu'on écrit un `__enter__` sûr qui acquiert plusieurs choses.
- Usage : ✅ fonction ou `__enter__` qui ouvre plusieurs ressources et les rend à l'appelant · ❌ ressources utilisées et fermées dans le même bloc : un `ExitStack` simple.

```python
# Exemple 1 : les ressources survivent
from contextlib import ExitStack, closing
class Conn:
    ouverte = True
    def close(self):
        self.ouverte = False
with ExitStack() as pile:
    cs = [pile.enter_context(closing(Conn()))
          for _ in range(2)]
    plus_tard = pile.pop_all()
[c.ouverte for c in cs]  # → [True, True]
plus_tard.close()
[c.ouverte for c in cs]  # → [False, False]
```

```python
# Exemple 2 : un échec referme les premières
from contextlib import ExitStack, closing

class Conn:
    ouverte = True
    def close(self):
        self.ouverte = False

cs = []
try:
    with ExitStack() as pile:
        for i in range(3):
            if i == 2:
                raise ConnectionError("3e")
            c = Conn()
            cs.append(pile.enter_context(closing(c)))
        pile.pop_all()
except ConnectionError:
    pass
[c.ouverte for c in cs]  # → [False, False]
```

- Quiz : Que renvoie `pile.pop_all()` ?
- [ ] `None`
- [ ] La liste des ressources
- [x] Un nouvel `ExitStack`
- [ ] La pile elle-même, vidée
- Réponse : Un nouvel `ExitStack` : il porte les nettoyages retirés de la pile courante ; l'appeler (`close()`) ou s'en servir comme `with` ferme tout plus tard.
