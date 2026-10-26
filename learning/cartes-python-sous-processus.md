---
title: "Cartes · Sous-processus Python"
type: cartes
langage: Python
chapitre: Système et réseau
cours: Sous-processus
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Sous-processus Python
Python · Sous-processus : subprocess pour lancer une commande, lire sa sortie et traiter ses erreurs (format spec v3 de revision-pwa).

## 1. run : lancer une commande
- Id : sous-processus-run-lancer
- Sous-thème : lancer
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Source : data-platform · S1-07
- Définition : `subprocess.run([...])` lance un programme, attend sa fin et rend un `CompletedProcess` : `args`, `returncode`, `stdout`, `stderr` (≈ `spawnSync` de Node).
- Contexte : La commande est une liste : le programme, puis chaque argument, sans shell entre les deux. La sortie du processus va au terminal, pas dans `stdout`, qui vaut `None` sans capture. `run` bloque jusqu'à la fin, il n'y a pas de promesse à attendre. Un code de sortie non nul ne lève rien par défaut : il faut lire `returncode`.
- Usage : ✅ appeler `uv`, `terraform`, `git` depuis un script de build · ❌ ce que la bibliothèque standard fait déjà (`shutil.copy`, `zipfile`, `Path.glob`) : pas de `cp` ni de `zip` en sous-processus.

```python
# Exemple 1 : le code de sortie
import subprocess, sys
py = sys.executable        # le Python courant
r = subprocess.run([py, "-c", "pass"])
r.returncode   # → 0
r.stdout       # → None : non capturé
r = subprocess.run([py, "-c", "exit(3)"])
r.returncode   # → 3 : pas d'exception
```

- Quiz : Que fait le script pendant `subprocess.run(["sleep", "5"])` ?
- [ ] Il continue : `run` rend une promesse
- [x] Il attend les 5 secondes
- [ ] Il continue : `run` rend un résultat vide
- [ ] Il lève `TimeoutExpired`
- Réponse : il attend : `run` est synchrone, comme `spawnSync` ; pour lancer sans attendre, `subprocess.Popen`.

## 2. check=True : lever si la commande échoue
- Id : sous-processus-check-true
- Sous-thème : erreurs
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : sous-processus-run-lancer
- Voir aussi : sous-processus-calledprocesserror-stderr
- Source : data-platform · S1-07
- Définition : Par défaut `run` ne lève pas quand la commande échoue ; `check=True` lève `CalledProcessError` dès que le code de sortie n'est pas 0.
- Contexte : Piège en venant de Node : `execSync` lève, `run` non. Sans `check=True`, un `uv export` en échec laisse le script continuer avec un fichier vide, et le zip part incomplet. C'est le `set -e` de Python : le script de build le met dans son unique fonction `uv(*args)`, donc sur chaque appel.
- Usage : ✅ toute étape dont la suite dépend (export, install, build) · ❌ commande dont le code non nul est une réponse attendue (`grep` sans résultat) : lire `returncode`.

```python
# Exemple 1 : l'échec devient une exception
import subprocess, sys
cmd = [sys.executable, "-c", "exit(2)"]
subprocess.run(cmd).returncode   # → 2
subprocess.run(cmd, check=True)  # ❌ CalledProcessError
```

```python
# Exemple 2 : lire le code
import subprocess, sys
cmd = [sys.executable, "-c", "exit(2)"]
try:
    subprocess.run(cmd, check=True)
except subprocess.CalledProcessError as e:
    code = e.returncode
code   # → 2
```

- Quiz : `git diff --quiet` rend 1 s'il y a des changements : que fait `run(["git", "diff", "--quiet"], check=True)` sur un dépôt modifié ?
- [x] `CalledProcessError`
- [ ] Rend `returncode` 1 sans lever
- [ ] Rend `True`
- [ ] `FileNotFoundError`
- Réponse : `CalledProcessError` (mesuré) : `check=True` ne sait pas que 1 veut dire « il y a des changements » ; pour ce genre de commande, lire `returncode` sans `check`.

## 3. capture_output et text : lire la sortie
- Id : sous-processus-capture-output-text
- Sous-thème : sortie
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Prérequis : sous-processus-run-lancer
- Source : data-platform · S1-07
- Définition : `capture_output=True` range la sortie dans `r.stdout` et `r.stderr` ; `text=True` les décode en `str` au lieu de `bytes`.
- Contexte : Sans `text=True`, on reçoit des octets (`b'42\n'`) : `.decode()` ou `text=True`, qui décode selon la locale (`encoding="utf-8"` pour l'imposer). Le saut de ligne final reste : `.strip()` avant de comparer. Capturer garde tout en mémoire jusqu'à la fin, et rien ne s'affiche pendant l'exécution.
- Usage : ✅ récupérer une valeur (`git rev-parse HEAD`, `terraform output -raw`) · ❌ commande longue dont on veut voir la progression (`uv pip install`) : laisser la sortie au terminal.

```python
# Exemple 1 : str ou bytes
import subprocess, sys
cmd = [sys.executable, "-c", "print(552100554)"]
r = subprocess.run(cmd, capture_output=True)
r.stdout          # → b'552100554\n'
r = subprocess.run(cmd, capture_output=True,
                   text=True)
r.stdout.strip()  # → '552100554'
```

- Quiz : Que vaut `r.stderr` après `r = run(cmd, stdout=subprocess.PIPE, text=True)` ?
- [x] `None`
- [ ] `''`
- [ ] `b''`
- [ ] La sortie d'erreur de la commande
- Réponse : `None` (mesuré) : seul stdout est capturé ; stderr part au terminal, et le champ reste vide de valeur.

## 4. liste ou chaîne : sans shell, un seul programme
- Id : sous-processus-liste-sans-shell
- Sous-thème : lancer
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : sous-processus-run-lancer
- Voir aussi : sous-processus-shell-true-injection
- Source : data-platform · S1-07
- Définition : Sans `shell=True`, une chaîne est prise comme **nom du programme** entier : `run("ls -l")` cherche un exécutable nommé `ls -l`.
- Contexte : La liste est passée telle quelle au système : chaque élément est un argument, espaces compris, sans découpage ni développement (`$HOME`, `*`, `|`), puisqu'il n'y a pas de shell. C'est ce qui rend la liste sûre face aux valeurs variables. Pour découper une ligne de commande écrite à la main, `shlex.split`.
- Usage : ✅ toujours une liste : `["uv", "export", "--package", nom]` · ❌ une f-string `f"uv export --package {nom}"` passée à `run` : `FileNotFoundError` sans shell, injection avec.

```python
# Exemple 1 : chaîne sans shell
import shlex, subprocess
subprocess.run("ls -l")  # ❌ FileNotFoundError
shlex.split("uv export --package ingest-bodacc")
# → ['uv', 'export', '--package', 'ingest-bodacc']
```

- Quiz : Que vaut `run(["echo", "$HOME"], capture_output=True, text=True).stdout` ?
- [ ] `'/Users/…\n'`
- [x] `'$HOME\n'`
- [ ] `'\n'`
- [ ] `KeyError: 'HOME'`
- Réponse : `'$HOME\n'` (mesuré) : sans shell, personne ne développe la variable ; `echo` reçoit le texte tel quel.

## 5. cwd= : le dossier de l'enfant
- Id : sous-processus-cwd
- Sous-thème : environnement
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Source : data-platform · S1-07
- Définition : `run(cmd, cwd=dossier)` lance la commande dans ce dossier, sans changer le dossier courant du script (≈ option `cwd` de `spawn`).
- Contexte : Les chemins relatifs de la commande partent de `cwd`. Le script de build passe `cwd=ROOT` pour que `uv export` trouve le `pyproject.toml` racine quel que soit le dossier d'où l'on lance `make`, avec `ROOT = Path(__file__).resolve().parents[2]`. Préférable à `os.chdir`, qui change l'état global de tout le processus.
- Usage : ✅ `cwd=ROOT` pour un outil qui lit sa config dans le dossier courant (`uv`, `terraform`, `git`) · ❌ `os.chdir` avant l'appel : effet de bord sur tout le script.

```python
# Exemple 1 : le parent ne bouge pas
import os, subprocess, tempfile
d = os.path.realpath(tempfile.mkdtemp())
avant = os.getcwd()
r = subprocess.run(["pwd"], cwd=d,
                   capture_output=True, text=True)
r.stdout.strip() == d    # → True
os.getcwd() == avant     # → True
```

- Quiz : Que fait `run(["ls"], cwd="dossier-absent")` ?
- [ ] `ls` liste le dossier courant
- [ ] Rend `returncode` 1
- [ ] `CalledProcessError`
- [x] `FileNotFoundError`
- Réponse : `FileNotFoundError` (mesuré) : le changement de dossier échoue avant le lancement ; `ls` n'est jamais exécuté, donc pas de code de sortie.

## 6. sys.executable : le bon Python
- Id : sous-processus-sys-executable
- Sous-thème : environnement
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Source : data-platform · S1-07
- Définition : `sys.executable` est le chemin de l'interpréteur qui exécute le script : celui du venv sous `uv run`, à préférer à `"python"` en dur.
- Contexte : `"python"` est cherché dans le `PATH` : sur un Mac, il peut manquer (seul `python3` existe) ou désigner un autre Python, sans les dépendances du projet. `[sys.executable, "-m", "pytest"]` garantit le même interpréteur, donc le même venv. C'est aussi le moyen portable d'écrire un exemple de sous-processus qui marche partout.
- Usage : ✅ lancer un module Python en sous-processus (`-m pytest`, `-m json.tool`) · ❌ `["python", ...]` en dur dans un script partagé.

```python
# Exemple 1 : même venv que le parent
import subprocess, sys
code = "import sys; print(sys.prefix)"
r = subprocess.run([sys.executable, "-c", code],
                   capture_output=True, text=True)
r.stdout.strip() == sys.prefix   # → True
```

- Quiz : Un script lancé hors de `uv run` appelle `run(["python3", "-c", "import pydantic"])` : ce Python a-t-il pydantic ?
- [ ] Oui : l'enfant hérite des imports du parent
- [ ] Oui : `python3` désigne toujours le venv
- [x] Pas forcément : `python3` vient du `PATH`
- [ ] Non : un enfant n'importe jamais rien
- Réponse : pas forcément : l'enfant est un processus neuf, sans les modules du parent ; c'est le `python3` trouvé dans le `PATH` qui tourne.

## 7. check_output : la sortie ou une exception
- Id : sous-processus-check-output
- Sous-thème : sortie
- Type : comparaison
- Niveau : 1
- Profils : ops
- Prérequis : sous-processus-check-true, sous-processus-capture-output-text
- Source : data-platform · S1-07
- Définition : `subprocess.check_output(cmd, text=True)` rend directement la sortie standard et lève `CalledProcessError` si le code n'est pas 0.
- Contexte : Équivaut à `run(cmd, check=True, stdout=PIPE).stdout`. API plus ancienne que `run` (Python 3.5), toujours courante dans du code existant. Elle ne capture pas stderr, qui s'affiche au terminal. `check_call` est la variante sans capture. Pour du code neuf, `run` avec des arguments nommés dit tout explicitement.
- Usage : ✅ lire du code existant, une valeur en une ligne (`git rev-parse --short HEAD`) · ❌ besoin de stderr ou du code de sortie sans exception : `run`.

```python
# Exemple 1 : la valeur en une ligne
import subprocess, sys
out = subprocess.check_output(
    [sys.executable, "-c", "print(3144)"],
    text=True)
out        # → '3144\n'
int(out)   # → 3144 : int tolère le \n
```

- Quiz : Que rend `subprocess.check_output(["true"])` ?
- [x] `b''`
- [ ] `None`
- [ ] `0`
- [ ] `''`
- Réponse : `b''` (mesuré) : la commande réussit sans rien écrire ; sans `text=True`, la sortie est en `bytes`, vide.

## 8. shell=True : la donnée devient du code
- Id : sous-processus-shell-true-injection
- Sous-thème : lancer
- Type : piège
- Niveau : 2
- Profils : ops, web
- Prérequis : sous-processus-liste-sans-shell
- Source : data-platform · S1-07
- Définition : `shell=True` fait exécuter une chaîne par `/bin/sh` : pipes, `$VAR` et jokers marchent, mais toute valeur insérée peut devenir une commande.
- Contexte : Une valeur venue d'ailleurs (`nom = "x; echo PIRATE"`) dans `f"echo {nom}"` exécute une seconde commande : injection, comme une requête SQL concaténée. Si le shell est indispensable, `shlex.quote` sur chaque valeur. Le plus souvent, Python fait le travail du pipe (`text=True` puis `.splitlines()`, `len`). Ruff le signale (règle `S602`).
- Usage : ✅ commande fixe écrite par soi, avec pipe, sans valeur externe · ❌ toute chaîne qui contient une valeur variable : liste sans shell.

```python
# Exemple 1 : la donnée devient du code
import subprocess
nom = "x; echo PIRATE"
r = subprocess.run(f"echo {nom}", shell=True,
                   capture_output=True, text=True)
r.stdout.splitlines()   # → ['x', 'PIRATE']
```

```python
# Exemple 2 : shlex.quote
import shlex, subprocess
nom = "x; echo PIRATE"
r = subprocess.run(f"echo {shlex.quote(nom)}",
                   shell=True, capture_output=True,
                   text=True)
r.stdout    # → 'x; echo PIRATE\n'
```

- Quiz : Qu'affiche `run(["echo", "a", "|", "wc"])` ?
- [ ] `1 1 2` : le résultat de `wc`
- [x] `a | wc`
- [ ] `a`
- [ ] `FileNotFoundError`
- Réponse : `a | wc` (mesuré) : sans shell, `|` est un argument comme un autre, passé à `echo` qui l'affiche.

## 9. FileNotFoundError : programme introuvable
- Id : sous-processus-programme-introuvable
- Sous-thème : erreurs
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : sous-processus-check-true
- Source : data-platform · S1-07
- Définition : Un programme absent du `PATH` lève `FileNotFoundError` au lancement, même avec `check=True` : ce n'est pas un `CalledProcessError`.
- Contexte : Rien n'a tourné, donc pas de code de sortie. Un `except CalledProcessError` ne l'attrape pas : un script de build qui suppose `uv` installé plante avec une trace peu claire. `shutil.which("uv")` teste la présence d'avance ; c'est l'équivalent de l'erreur `ENOENT` de `spawn` en Node.
- Usage : ✅ `shutil.which` en tête de script pour un message clair (« installer uv ») · ❌ un seul `except CalledProcessError` en croyant couvrir toutes les erreurs de commande.

```python
# Exemple 1 : rien n'a été lancé
import shutil, subprocess
shutil.which("outil-absent")    # → None
cmd = ["outil-absent", "--version"]
subprocess.run(cmd, check=True)  # ❌ FileNotFoundError
```

- Quiz : Que lève `run(["sh", "-c", "outil-absent"], check=True)` ?
- [ ] `FileNotFoundError`
- [ ] Rien : `returncode` vaut 127
- [x] `CalledProcessError`
- [ ] `OSError`
- Réponse : `CalledProcessError` (mesuré, code 127) : `sh` existe et a bien tourné ; c'est lui qui ne trouve pas la commande et sort en erreur.

## 10. CalledProcessError : où est la cause
- Id : sous-processus-calledprocesserror-stderr
- Sous-thème : erreurs
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : sous-processus-check-true, sous-processus-capture-output-text
- Source : data-platform · S1-07
- Définition : `CalledProcessError` porte `returncode`, `cmd`, `stdout` et `stderr` ; les deux derniers valent `None` si la sortie n'a pas été capturée.
- Contexte : Son message (`Command '[...]' returned non-zero exit status 1.`) ne contient pas la sortie d'erreur : un log CI qui affiche seulement `str(e)` dit « échec » sans dire pourquoi. Deux choix : ne rien capturer, l'erreur s'affiche au terminal (le script de build), ou capturer et journaliser `e.stderr` (un service).
- Usage : ✅ `capture_output=True, text=True` puis `log.error(e.stderr)` dans un service · ❌ capturer sans jamais afficher : la cause de l'échec disparaît.

```python
# Exemple 1 : la cause est dans stderr
import subprocess, sys
code = "import sys; sys.exit('lock ' + 'absent')"
try:
    subprocess.run([sys.executable, "-c", code],
                   check=True, capture_output=True,
                   text=True)
except subprocess.CalledProcessError as e:
    err = e
err.returncode               # → 1
err.stderr.strip()           # → 'lock absent'
"lock absent" in str(err)    # → False
```

- Quiz : `e.output` est un alias de quel attribut ?
- [x] `e.stdout`
- [ ] `e.stderr`
- [ ] `stdout + stderr` concaténés
- [ ] Aucun : toujours `None`
- Réponse : `e.stdout` (mesuré) : `output` vient de `check_output`, qui ne capture que la sortie standard.

## 11. timeout= : borner la durée
- Id : sous-processus-timeout
- Sous-thème : erreurs
- Type : concept
- Niveau : 2
- Profils : ops, data
- Prérequis : sous-processus-run-lancer
- Source : data-platform · S1-07
- Définition : `run(cmd, timeout=30)` tue le processus après 30 s et lève `subprocess.TimeoutExpired` ; sans `timeout`, `run` peut attendre indéfiniment.
- Contexte : Un outil bloqué (attente réseau, question posée sur l'entrée standard) fige le script ou le job CI jusqu'à la limite du runner. Le processus est tué avant que l'exception remonte. En Lambda, garder ce timeout sous le temps restant de l'invocation (`context.get_remaining_time_in_millis()`), sinon c'est la fonction entière qui expire.
- Usage : ✅ tout appel réseau ou outil externe dans un script automatisé · ❌ build long et légitime (`uv pip install` à froid) borné trop court : échecs aléatoires en CI.

```python
# Exemple 1 : tué au bout de 0,5 s
import subprocess, sys
cmd = [sys.executable, "-c",
       "import time; time.sleep(5)"]
subprocess.run(cmd, timeout=0.5)  # ❌ TimeoutExpired
```

- Quiz : Quelle classe parente commune ont `TimeoutExpired` et `CalledProcessError` ?
- [ ] `TimeoutError`
- [x] `subprocess.SubprocessError`
- [ ] `OSError`
- [ ] `RuntimeError`
- Réponse : `SubprocessError` (mesuré) : `except subprocess.SubprocessError` attrape les deux ; `TimeoutExpired` n'hérite pas de `TimeoutError`.

## 12. env= : remplace tout l'environnement
- Id : sous-processus-env-remplace-tout
- Sous-thème : environnement
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : sous-processus-run-lancer
- Voir aussi : tests-monkeypatch
- Source : data-platform · S1-07
- Définition : `env={...}` donne au processus **uniquement** ces variables : `PATH`, `HOME` et le reste disparaissent ; pour en ajouter une, `{**os.environ, "X": "1"}`.
- Contexte : Piège classique : `env={"AWS_PROFILE": "data-platform"}` fait perdre `PATH`, et `run(["uv", ...])` lève `FileNotFoundError`, le programme étant cherché dans un `PATH` par défaut (`/bin:/usr/bin`). Sans `env`, l'enfant hérite de l'environnement du parent, modifications de `os.environ` comprises. Ça ressemble à `env` de `spawn` en Node, qui remplace aussi tout.
- Usage : ✅ `{**os.environ, "AWS_PROFILE": p}` pour ajouter, un dict minimal pour isoler un test · ❌ `env={"X": "1"}` en croyant ajouter une variable.

```python
# Exemple 1 : ajouter sans tout perdre
import os, subprocess
cmd = ["sh", "-c", 'echo "$X:$HOME"']
env = {**os.environ, "X": "1"}
r = subprocess.run(cmd, env=env,
                   capture_output=True, text=True)
r.stdout.startswith("1:/")   # → True
r = subprocess.run(cmd, env={"X": "1"},
                   capture_output=True, text=True)
r.stdout   # → '1:\n' : HOME perdu
```

- Quiz : Que fait `run(["sh", "-c", "true"], env={"PORT": 8080})` ?
- [ ] `PORT` vaut `'8080'` dans l'enfant
- [ ] `PORT` est ignoré
- [x] `TypeError`
- [ ] `ValueError`
- Réponse : `TypeError` (mesuré) : les valeurs d'environnement doivent être des `str` (ou `bytes`) ; aucune conversion automatique.

## 13. input= : écrire sur l'entrée standard
- Id : sous-processus-input-stdin
- Sous-thème : sortie
- Type : recette
- Niveau : 2
- Profils : ops, data
- Source : data-platform · S1-07
- Définition : `run(cmd, input=données)` envoie ces données sur l'entrée standard du processus puis la ferme (≈ `echo données | cmd`).
- Contexte : Avec `text=True`, `input` est une `str`, sinon des `bytes`. Évite un fichier temporaire pour passer un JSON ou une liste à un outil qui lit l'entrée standard (`jq`). Sans `input`, l'enfant hérite de l'entrée du script : en CI, un outil qui pose une question attend une réponse qui ne viendra pas.
- Usage : ✅ données produites en mémoire vers un outil qui lit l'entrée standard · ❌ gros volume produit au fil de l'eau : `Popen` et écriture par morceaux.

```python
# Exemple 1 : entrée vers sortie
import subprocess, sys
code = "import sys; print(sys.stdin.read().upper())"
r = subprocess.run([sys.executable, "-c", code],
                   input="a1", capture_output=True,
                   text=True)
r.stdout   # → 'A1\n'
```

- Quiz : Que donne `input="a1"` avec `capture_output=True` mais sans `text=True` ?
- [ ] `r.stdout` vaut `b'A1\n'`
- [ ] `"a1"` est encodé en UTF-8 automatiquement
- [x] `TypeError`
- [ ] `UnicodeError`
- Réponse : `TypeError` (mesuré) : sans `text=True`, le flux est binaire et attend des `bytes` (`input=b"a1"`).

## 14. *args : un wrapper de commande
- Id : sous-processus-wrapper-args
- Sous-thème : lancer
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : sous-processus-run-lancer, listes-deballer-etoile
- Source : data-platform · S1-07
- Définition : Un wrapper `def uv(*args): run(["uv", *args], cwd=ROOT, check=True)` fixe une fois programme, dossier et `check`, en gardant la liste d'arguments.
- Contexte : `*args` rassemble les arguments en tuple, `["uv", *args]` les déplie dans la liste : chaque argument reste séparé, sans shell. Le script de build appelle `uv("export", "--package", p, ...)` et `uv("pip", "install", *common, ...)`. Piège : `uv("export --frozen")` passe un seul argument contenant une espace, que uv rejette.
- Usage : ✅ script qui appelle souvent le même outil avec les mêmes options · ❌ wrapper qui assemble une chaîne pour `shell=True` : on perd la sûreté de la liste.

```python
# Exemple 1 : le même motif, avec Python
import subprocess, sys
def py(*args):
    r = subprocess.run([sys.executable, *args],
        capture_output=True, text=True, check=True)
    return r.stdout.strip()
code = "import sys; print(sys.argv[1:])"
py("-c", code, "a b", "c")   # → "['a b', 'c']"
```

- Quiz : `common = ["--quiet", "--target", "build"]` : combien d'arguments reçoit uv avec `uv("pip", "install", *common)` ?
- [ ] 3
- [ ] 2
- [x] 5
- [ ] 4
- Réponse : 5 : `"pip"`, `"install"`, puis les trois éléments dépliés de `common` ; sans l'étoile, la liste serait un seul argument (et `TypeError`).

## 15. stderr=STDOUT : un seul flux
- Id : sous-processus-stderr-vers-stdout
- Sous-thème : sortie
- Type : recette
- Niveau : 3
- Profils : ops, expert
- Prérequis : sous-processus-capture-output-text
- Source : data-platform · S1-07
- Définition : `stdout=subprocess.PIPE, stderr=subprocess.STDOUT` capture les deux flux dans `r.stdout`, dans l'ordre d'écriture ; `r.stderr` vaut alors `None`.
- Contexte : Utile pour journaliser tout ce qu'un outil a dit, erreurs comprises, en un bloc lisible. L'ordre exact dépend des tampons de l'enfant : un Python enfant tamponne sa sortie standard quand ce n'est pas un terminal, ses `print` peuvent donc arriver après ses erreurs ; `-u` ou `PYTHONUNBUFFERED=1` l'évite.
- Usage : ✅ log complet d'un outil externe en cas d'échec · ❌ besoin de séparer erreurs et résultats (parser stdout) : garder deux flux.

```python
# Exemple 1 : un seul flux
import subprocess
cmd = ["sh", "-c", "echo ok; echo err >&2"]
r = subprocess.run(cmd, stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT,
                   text=True)
r.stdout.split()   # → ['ok', 'err']
r.stderr           # → None
```

- Quiz : Que fait `run(cmd, capture_output=True, stderr=subprocess.STDOUT)` ?
- [ ] Tout arrive dans `r.stdout`
- [ ] `stderr` est ignoré, tout est capturé
- [x] `ValueError`
- [ ] `TypeError`
- Réponse : `ValueError` (mesuré) : `capture_output` fixe déjà `stdout` et `stderr` ; les deux options s'excluent.

## 16. returncode négatif : tué par un signal
- Id : sous-processus-returncode-signal
- Sous-thème : erreurs
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Prérequis : sous-processus-check-true
- Voir aussi : sous-processus-timeout
- Source : data-platform · S1-07
- Définition : Sous Unix, `returncode = -N` signifie que le processus a été tué par le signal N (`-9` : `SIGKILL`, souvent le manque de mémoire).
- Contexte : Un code positif vient du programme (`exit(2)`), un code négatif du système. En CI ou dans un conteneur, `-9` sans message est souvent le tueur OOM du noyau. Passé par `sh -c`, le shell rend `128 + N` quand c'est son propre enfant qui meurt. `signal.Signals(9).name` donne le nom du signal.
- Usage : ✅ distinguer un échec du programme d'un arrêt forcé dans les logs de build · ❌ traiter tout code non nul comme une erreur du programme sans regarder le signe.

```python
# Exemple 1 : tué par SIGKILL
import signal, subprocess
r = subprocess.run(["sh", "-c", "kill -9 $$"])
r.returncode                        # → -9
signal.Signals(-r.returncode).name  # → 'SIGKILL'
```

- Quiz : Que vaut `run(["sh", "-c", "sleep 9 & kill -9 $!; wait $!"]).returncode` ?
- [ ] `-9`
- [x] `137`
- [ ] `9`
- [ ] `0`
- Réponse : `137` (mesuré) : le shell survit et rend le statut de son enfant tué, codé `128 + 9` ; seul le processus lancé directement donne `-9`.

## 17. Popen : lancer sans attendre
- Id : sous-processus-popen-parallele
- Sous-thème : lancer
- Type : choisir
- Niveau : 3
- Profils : ops, expert
- Source : data-platform · S1-07
- Définition : `subprocess.Popen(cmd)` démarre le processus et rend la main tout de suite ; `wait()` attend la fin, `communicate()` attend en lisant les sorties.
- Contexte : `run` est un `Popen` suivi de `communicate` et des vérifications. `Popen` sert à lancer plusieurs processus en parallèle (un build par Lambda) ou à lire une sortie ligne par ligne. Piège : `stdout=PIPE` puis `wait()` sans lire bloque pour toujours quand le tampon du pipe est plein (quelques dizaines de Kio) ; `communicate()` lit pendant qu'il attend.
- Usage : ✅ builds parallèles, suivi de progression ligne par ligne · ❌ appel simple et séquentiel : `run`.

```python
# Exemple 1 : trois processus en parallèle
import subprocess, sys, time
code = "import time; time.sleep(0.5)"
t = time.monotonic()
ps = [subprocess.Popen([sys.executable, "-c", code])
      for _ in range(3)]
[p.wait() for p in ps]          # → [0, 0, 0]
time.monotonic() - t < 1.4      # → True
```

- Quiz : Juste après `p = Popen(cmd)`, pendant que la commande tourne, que vaut `p.returncode` ?
- [ ] `0`
- [ ] `-1`
- [ ] Lève une exception
- [x] `None`
- Réponse : `None` (mesuré) : le code n'existe qu'une fois le processus terminé et attendu (`wait`, `poll`, `communicate`).
