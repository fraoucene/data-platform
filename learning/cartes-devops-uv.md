---
title: "Cartes · uv"
type: cartes
langage: DevOps
cours: uv
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · uv
DevOps · uv : ci, dépendances, lock, outils, python, workspace (format spec v3 de revision-pwa).

## 1. workspace : members
- Sous-thème : workspace
- Niveau : 1
- Source : data-platform · S1-03
- Définition : `[tool.uv.workspace] members` déclare par globs les projets du monorepo : un seul `uv.lock`, un seul `.venv` racine (≈ `pnpm-workspace.yaml`).
- Contexte : Un seul lock = une seule résolution de versions : pas de `httpx` 0.27 dans un membre et 0.28 dans un autre. Chaque dossier qui correspond à un glob doit avoir son `pyproject.toml`, sinon `uv sync` échoue ; un glob qui ne correspond à rien (`lambdas/*` vide) est accepté. `uv init` lancé dans le workspace y ajoute le nouveau projet.
- Usage : ✅ monorepo de libs, Lambdas et jobs qui partagent leurs versions · ❌ projets aux dépendances incompatibles (deux versions de pyspark) : projets séparés, un lock chacun.

```toml
# Exemple 1 : pyproject.toml racine
[project]
name = "data-platform"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["packages/*", "lambdas/*",
           "jobs/*"]
```

```bash
# Exemple 2 : le glob inclut le nouveau
uv init --lib packages/dp-common
# Project `dp-common` is already a
#   member of workspace …
grep -A2 'name = "dp-common"' uv.lock
# version = "0.1.0"
# source = { editable = "packages/dp-common" }
```

- Quiz : On écrit `member = ["packages/*"]` (sans s) : que fait `uv sync` ?
- [ ] Ignore la clé : workspace sans membre
- [ ] Avertit puis continue
- [x] `unknown field 'member', expected 'members' or 'exclude'`
- [ ] Installe chaque dossier de `packages/`
- Réponse : erreur de parsing : uv valide le schéma de `[tool.uv]` strictement, là où `package.json` avale une clé inconnue ; le message donne ligne et colonne.

## 2. uv add --dev : dependency-groups
- Sous-thème : dépendances
- Niveau : 1
- Source : data-platform · S1-03
- Définition : `uv add --dev pytest` écrit dans `[dependency-groups] dev` (PEP 735, ≈ `devDependencies`) : installé en local, jamais publié avec le paquet.
- Contexte : uv écrit une borne basse (`pytest>=9.1.1`) dans `pyproject.toml` ; la version exacte vit dans `uv.lock`, qui se commite. `uv sync` installe le groupe `dev` par défaut, `--no-dev` l'écarte (image, zip de Lambda). À distinguer de `[project.optional-dependencies]` (`uv add --optional`) : des extras, installables par un consommateur (`pkg[s3]`).
- Usage : ✅ outils de dev : pytest, ruff, pre-commit, respx · ❌ dépendance optionnelle offerte aux utilisateurs du paquet (`boto3` pour S3) : `uv add --optional s3 boto3`.

```bash
# Exemple 1 : où ça atterrit
uv add --dev pytest ruff
# pyproject.toml :
# [dependency-groups]
# dev = [
#     "pytest>=9.1.1",
#     "ruff>=0.17.1",
# ]
```

```bash
# Exemple 2 : l'écarter pour livrer
uv sync --no-dev
# - pytest==9.1.1   (désinstallé)
uv run --no-sync python -c "import pytest"
# ❌ ModuleNotFoundError
```

- Quiz : Paquet avec `pytest` en `dev` et `boto3` en extra `s3` : que liste le `Requires-Dist` du wheel ?
- [ ] `pytest` et `boto3`
- [x] `boto3 ; extra == 's3'` seul
- [ ] `pytest` seul
- [ ] Rien : les deux restent locaux
- Réponse : `boto3` seul, conditionné à l'extra : les dependency groups ne vont jamais dans les métadonnées publiées, les extras si (`uv build` puis lecture de `METADATA`).

## 3. uv init : ce qu'il crée
- Sous-thème : workspace
- Niveau : 1
- Définition : `uv init <nom>` crée un projet : `pyproject.toml`, `main.py`, `README.md`, `.python-version` (≈ `npm init` qui épinglerait aussi la version de Node).
- Contexte : Le `.venv` et `uv.lock` n'apparaissent qu'au premier `uv run`, `uv add` ou `uv sync`. Hors dépôt git, `uv init` fait aussi `git init` et écrit un `.gitignore` ; dans un dépôt existant, non. `requires-python` reprend la version de Python par défaut d'uv : la plus récente installée par uv, pas forcément celle du runtime Lambda. `--lib` ajoute `src/` et un backend de build, `--bare` n'écrit que `pyproject.toml`.
- Usage : ✅ nouveau projet ou membre de workspace, avec `--python 3.12` pour coller au runtime · ❌ créer `pyproject.toml` à la main : champs oubliés, nom non normalisé.

```bash
# Exemple 1 : un projet neuf, hors git
uv init --python 3.12 demo
ls -a demo
# .git .gitignore .python-version
# main.py pyproject.toml README.md
cd demo && uv run main.py
# Creating virtual environment at: .venv
# Hello from demo!
```

```toml
# Exemple 2 : le pyproject.toml écrit
[project]
name = "demo"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []
```

- Quiz : `uv init --python 3.12 svc` lancé dans un dossier d'un dépôt git déjà initialisé : que crée-t-il en plus du projet ?
- [ ] Un `.git` et un `.gitignore` dans `svc/`
- [ ] Un `.gitignore` seul
- [x] Ni `.git` ni `.gitignore`
- [ ] Un sous-module git
- Réponse : ni l'un ni l'autre : uv détecte le dépôt parent et n'y imbrique pas un second dépôt ; le `.gitignore` du dépôt doit déjà couvrir `.venv`.

## 4. uv run : synchronise puis exécute
- Sous-thème : dépendances
- Niveau : 1
- Définition : `uv run <cmd>` met `uv.lock` et `.venv` à jour, puis lance la commande dans le venv, sans l'activer (≈ `pnpm exec`).
- Contexte : Pas de `source .venv/bin/activate` : chaque `uv run` vérifie que le lock correspond à `pyproject.toml` et que le venv correspond au lock, puis corrige ce qui manque. C'est pour ça que `make lint` écrit `uv run ruff` : le bon ruff, celui du lock, même sur un poste neuf. `--no-sync` saute la vérification, `--frozen` aussi mais sans toucher au lock.
- Usage : ✅ toute commande du projet : `uv run pytest`, `uv run python -m …`, cibles du Makefile · ❌ lancer `python` ou `pytest` du PATH : autre interpréteur, autres versions.

```bash
# Exemple 1 : sans activer le venv
uv run python -c "import sys; print(sys.prefix)"
# /…/data-platform/.venv
uv run ruff --version
# ruff 0.17.1   (celle du lock)
python -c "import httpx"
# ❌ ModuleNotFoundError (python du PATH)
```

- Quiz : On passe à la main `anyio==4.4.0` à `anyio==4.5.0` dans `pyproject.toml`, puis `uv run python …` : quelle version d'anyio ?
- [ ] 4.4.0 : il faut d'abord `uv lock`
- [x] 4.5.0, lock et venv mis à jour
- [ ] Erreur : lock désynchronisé
- [ ] 4.5.0 dans le venv, lock inchangé
- Réponse : 4.5.0 : `uv run` relance la résolution, réécrit `uv.lock`, puis synchronise le venv avant d'exécuter (`Uninstalled 1 package`, `Installed 1 package`).

## 5. uv remove : les transitives aussi
- Sous-thème : dépendances
- Niveau : 1
- Définition : `uv remove httpx` retire la dépendance de `pyproject.toml`, du lock et du venv, avec ses dépendances transitives devenues inutiles (≈ `pnpm remove`).
- Contexte : Contrairement à `pip uninstall`, qui ne retire que le paquet nommé et laisse ses dépendances orphelines, uv recalcule le graphe : une transitive reste si un autre paquet en a encore besoin. `--dev`, `--group` et `--package` ciblent le bon groupe ou le bon membre, comme pour `uv add`.
- Usage : ✅ retirer une lib directe qui ne sert plus · ❌ `uv pip uninstall` : le paquet revient au prochain `uv sync`, le lock n'a pas changé.

```bash
# Exemple 1 : anyio et httpx en directs
uv remove httpx
# - certifi==2026.10.23
# - h11==0.16.0
# - httpcore==1.0.9
# - httpx==0.28.1
uv pip list | grep idna
# idna 3.20  (anyio l'utilise encore)
```

- Quiz : `idna` n'est qu'une dépendance transitive (via httpx) : que fait `uv remove idna` ?
- [ ] Retire idna, httpx reste
- [ ] Retire idna et httpx
- [ ] Ajoute idna aux exclusions du lock
- [x] Erreur : absent de `project.dependencies`
- Réponse : erreur (`could not be found in project.dependencies`) : `uv remove` ne connaît que les dépendances directes déclarées ; une transitive part avec le paquet qui la tire.

## 6. uv.lock : commité et universel
- Sous-thème : lock
- Niveau : 1
- Définition : `uv.lock` fige version exacte et hashes de chaque paquet, pour toutes les plateformes ; commité, jamais édité à la main (≈ `pnpm-lock.yaml`).
- Contexte : `pyproject.toml` porte des bornes (`httpx>=0.28.1`), le lock la résolution exacte. Contrairement à un `requirements.txt` figé sur la machine qui l'a produit, le lock est universel : une seule résolution valable sur Mac, Linux de la CI et Windows, avec des marqueurs (`sys_platform == 'win32'`) pour ce qui dépend de la plateforme. Il est en TOML, lisible, mais seul `uv lock` l'écrit.
- Usage : ✅ commité avec chaque changement de `pyproject.toml`, relu en revue (versions qui bougent) · ❌ `.gitignore` sur `uv.lock` ou édition manuelle : builds non reproductibles.

```toml
# Exemple 1 : une entrée du lock
[[package]]
name = "httpx"
version = "0.28.1"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "anyio" },
    { name = "certifi" },
]
```

```bash
# Exemple 2 : le lock suit le pyproject
uv add httpx
git status --short
#  M pyproject.toml
#  M uv.lock
```

- Quiz : Sur un Mac, `pytest` tire `colorama` seulement sous Windows : `colorama` figure-t-il dans `uv.lock` ?
- [ ] Non : absent sur cette machine
- [x] Oui, avec `sys_platform == 'win32'`
- [ ] Oui, sans condition
- [ ] Seulement après `uv lock --universal`
- Réponse : oui, avec son marqueur : la résolution est universelle, le lock sert tel quel à un collègue sous Windows ; `uv sync` sur Mac ne l'installe pas.

## 7. uv tree : qui tire quoi
- Sous-thème : lock
- Niveau : 1
- Définition : `uv tree` affiche le graphe des dépendances lu dans le lock ; `--invert --package X` montre qui tire X (≈ `pnpm why`).
- Contexte : Utile avant un `uv remove` ou face à une version inattendue : `--depth 1` donne les dépendances directes, `--package <membre>` un seul membre du workspace, `(*)` signale un sous-arbre déjà affiché. Par défaut l'arbre est filtré pour la plateforme courante ; `--universal` montre tout le lock. `--outdated` ajoute la dernière version disponible.
- Usage : ✅ comprendre pourquoi un paquet est là, vérifier une version (`uv tree --depth 1`) · ❌ lire `uv.lock` à la main pour suivre une chaîne de dépendances.

```bash
# Exemple 1 : qui tire idna ?
uv tree --invert --package idna
# idna v3.20
# ├── anyio v4.15.1
# │   └── httpx v0.28.1
# │       └── ingest v0.1.0
# └── httpx v0.28.1 (*)
```

```bash
# Exemple 2 : les directs d'un membre
uv tree --package ingest --depth 1
# ingest v0.1.0
# ├── dp-common v0.1.0
# └── httpx v0.28.1
```

- Quiz : Sur un Mac, `uv tree` affiche-t-il `colorama`, que `pytest` tire seulement sous Windows ?
- [ ] Oui, marqué `(win32)`
- [x] Non, sauf avec `--universal`
- [ ] Oui, sans marqueur
- [ ] Non, il n'est pas dans le lock
- Réponse : non : l'arbre est filtré pour la plateforme courante ; `--universal` affiche tout le lock, où `colorama` est bien présent.

## 8. uvx : un outil sans l'installer
- Sous-thème : outils
- Niveau : 1
- Définition : `uvx <outil>` (alias de `uv tool run`) lance une CLI Python dans un environnement jetable, hors du projet (≈ `npx` / `pnpm dlx`).
- Contexte : uv résout l'outil, l'installe dans son cache et l'exécute : le second lancement est instantané. `uvx ruff@0.17.1` épingle une version. Le nom de l'exécutable doit être celui du paquet ; sinon `--from` : `uvx --from python-dotenv dotenv`. uvx ignore `pyproject.toml` et `uv.lock` : ce n'est pas le ruff du projet.
- Usage : ✅ outil ponctuel hors projet (`uvx pycowsay`, tester une version) · ❌ outil du projet (ruff, pytest) : `uv add --dev` puis `uv run`.

```bash
# Exemple 1 : version épinglée
uvx ruff@0.17.1 --version
# ruff 0.17.1
uvx python-dotenv --version
# An executable named `python-dotenv`
#   is not provided by package …
# - dotenv
uvx --from python-dotenv dotenv --version
```

- Quiz : Dans data-platform, dont `uv.lock` fixe ruff 0.17.1, que renvoie `uvx ruff --version` ?
- [ ] ruff 0.17.1, celui du lock
- [ ] Erreur : ruff déjà dans le projet
- [x] La dernière version publiée (0.17.2)
- [ ] La version du `rev` pre-commit
- Réponse : la dernière (0.17.2 ici) : uvx ignore le projet ; `uv run ruff` donne 0.17.1, d'où `uv run` dans le Makefile.

## 9. uv sync : le graphe de la racine
- Sous-thème : workspace
- Niveau : 2
- Source : data-platform · S1-03
- Définition : `uv sync` aligne le `.venv` sur le graphe de la racine : un membre non cité n'est pas installé, sauf avec `--all-packages`.
- Contexte : Contrairement à `pnpm install`, être membre ne suffit pas. La racine cite le membre deux fois : `dependencies = ["dp-common"]` et `[tool.uv.sources] dp-common = { workspace = true }` (≈ `"workspace:*"`), écrits ensemble par `uv add dp-common`. Sans l'entrée `sources`, `uv lock` refuse. `make sync` utilise `--all-packages` pour la CI.
- Usage : ✅ `uv add <membre>` à la racine pour chaque lib utilisée, `--all-packages` en CI · ❌ `pip install -e packages/x` à la main : hors du lock, non reproductible.

```bash
# Exemple 1 : membre non cité par la racine
uv sync
uv run python -c "import dp_common"
# ❌ ModuleNotFoundError
uv sync --all-packages
# + dp-common==0.1.0 (from file://…)
```

```toml
# Exemple 2 : ce qu'écrit uv add dp-common
[project]
dependencies = ["dp-common"]

[tool.uv.sources]
dp-common = { workspace = true }
# sans sources, uv lock : « is missing
#   an entry in tool.uv.sources »
```

- Quiz : Membre non cité, installé par `uv sync --all-packages` : que devient-il au `uv sync` suivant ?
- [ ] Il reste installé
- [x] Il est désinstallé
- [ ] Il est mis à jour
- [ ] `uv sync` échoue
- Réponse : désinstallé (`- dp-common==0.1.0`) : `uv sync` est exact, il retire du `.venv` tout ce qui n'est pas dans le graphe demandé.

## 10. uv add --package : le bon pyproject
- Sous-thème : dépendances
- Niveau : 2
- Source : data-platform · S1-06
- Définition : `uv add --package <membre> <dep>` écrit la dépendance dans le `pyproject.toml` du membre du workspace, pas dans celui de la racine (≈ `pnpm add --filter`).
- Contexte : Sans `--package`, la dépendance part à la racine : tout marche en local (un seul `.venv` pour le workspace), mais le zip Lambda construit depuis le membre n'a pas `httpx` → `ModuleNotFoundError` en production.
- Usage : ✅ dépendance runtime d'un package ou d'une Lambda du monorepo (`httpx`, `pydantic`) · ❌ outil de test ou de lint (`respx`, `pytest-cov`) : `uv add --dev` à la racine.

```bash
# Exemple 1 : où la dépendance est écrite
uv add --package bodacc-client httpx
# → packages/bodacc-client/pyproject.toml
#   dependencies = ["httpx>=0.28.1"]
uv add httpx
# → pyproject.toml racine seulement
```

- Quiz : `uv add bodacc-client` lancé **avant** `uv init --lib packages/bodacc-client` : que se passe-t-il ?
- [ ] uv crée le membre manquant
- [x] uv cherche sur PyPI et échoue
- [ ] uv écrit `{ workspace = true }` sans vérifier
- [ ] uv l'ajoute au groupe `dev`
- Réponse : uv cherche sur PyPI et échoue : un membre n'est connu que par le `name` de son `pyproject.toml` ; sans lui, le nom part sur PyPI (et s'installerait si quelqu'un l'y avait publié).

## 11. --locked ou --frozen : le lock en CI
- Sous-thème : ci
- Niveau : 2
- Définition : `uv sync --locked` échoue si `uv.lock` ne correspond plus à `pyproject.toml` ; `--frozen` installe le lock tel quel, sans vérifier (≈ `--frozen-lockfile` de pnpm).
- Contexte : En CI, on veut détecter un `pyproject.toml` modifié sans `uv lock` : c'est `--locked` (code retour 1, message explicite). `--frozen` ne relit pas les contraintes : il installe en silence l'ancienne version, utile seulement quand on sait le lock à jour (image Docker, étape après un `--locked`). Les deux refusent d'écrire `uv.lock`.
- Usage : ✅ `uv sync --locked` dans le job de test, `--frozen` dans une étape suivante du pipeline · ❌ `uv sync` nu en CI : il réécrit le lock en silence, le build ne teste pas ce qui est commité.

```bash
# Exemple 1 : pyproject édité, lock pas refait
# anyio==4.4.0 → anyio==4.5.0
uv sync --locked; echo $?
# The lockfile at `uv.lock` needs to be
#   updated, but `--locked` was provided.
# 1
uv sync --frozen; echo $?
# Audited 7 packages … 0  (anyio 4.4.0 !)
```

```yaml
# Exemple 2 : job GitLab
test:
  script:
    - uv sync --locked --all-packages
    - uv run --frozen pytest
```

- Quiz : `uv.lock` oublié dans le commit : que fait `uv sync --frozen` en CI ?
- [ ] Résout et installe sans écrire de lock
- [ ] Installe selon `pyproject.toml` seul
- [ ] Crée `uv.lock` puis installe
- [x] Erreur : lockfile introuvable
- Réponse : erreur (`Unable to find lockfile at uv.lock, but --frozen was provided`) : `--frozen` et `--locked` exigent un lock, aucun ne le crée.

## 12. uv lock --upgrade-package : monter une version
- Sous-thème : lock
- Niveau : 2
- Définition : `uv lock --upgrade-package anyio` remonte ce seul paquet à la plus haute version permise par les contraintes ; `--upgrade` remonte tout (≈ `pnpm update anyio`).
- Contexte : Par défaut, `uv lock` garde les versions déjà verrouillées tant qu'elles respectent `pyproject.toml` : pas de mise à jour surprise au détour d'un `uv add`. Monter une version est donc un geste explicite, ciblé et relu (le diff de `uv.lock`). `-P` est l'alias court. Une source git suit la même règle : le commit verrouillé reste jusqu'à `--upgrade-package`.
- Usage : ✅ correctif de sécurité ou de bug sur une lib, un paquet à la fois · ❌ `uv lock --upgrade` la veille d'une démo : tout bouge, régressions difficiles à isoler.

```bash
# Exemple 1 : un seul paquet monte
uv lock --upgrade-package anyio
# Updated anyio v4.5.0 -> v4.15.1
# Removed sniffio v1.3.1
# Added typing-extensions v4.16.0
uv tree --depth 1
# ├── anyio v4.15.1
# └── httpx v0.28.1   (inchangé)
```

- Quiz : Lock à `anyio 4.4.0`, on relâche la contrainte `anyio==4.4.0` en `anyio>=4.4`, puis `uv lock` : quelle version ?
- [ ] 4.15.1, la plus récente
- [x] 4.4.0, celle du lock
- [ ] Erreur : contrainte modifiée
- [ ] 4.5.0, la suivante
- Réponse : 4.4.0 : la version verrouillée respecte encore `>=4.4`, uv la garde ; il faut `--upgrade-package anyio` pour monter.

## 13. groupes : --group et default-groups
- Sous-thème : dépendances
- Niveau : 2
- Définition : `uv add --group lint ruff` crée un groupe nommé ; `uv sync` n'installe que les groupes de `default-groups` (`dev` seul par défaut).
- Contexte : Un groupe hors des défauts est désinstallé au `uv sync` suivant, même juste après `uv add --group`. `--group lint` l'ajoute, `--only-group lint` n'installe que lui (sans le projet ni ses dépendances, pratique pour un job de lint), `--all-groups` tout. `[tool.uv] default-groups = ["dev", "lint"]` change les défauts ; `--no-default-groups` les retire tous.
- Usage : ✅ séparer lint, tests, docs pour des jobs CI légers · ❌ un groupe par outil : trop de drapeaux à retenir, `dev` suffit souvent.

```bash
# Exemple 1 : groupe hors défauts
uv add --group lint ruff   # + ruff
uv sync                    # - ruff
uv sync --group lint       # + ruff
uv sync --only-group lint
# - pytest … (seul ruff reste)
```

```toml
# Exemple 2 : changer les défauts
[dependency-groups]
dev = ["pytest>=9.1.1"]
lint = ["ruff>=0.17.2"]

[tool.uv]
default-groups = ["dev", "lint"]
```

- Quiz : Avec `default-groups = ["dev", "lint"]`, que laisse `uv sync --no-dev` pour le zip Lambda ?
- [ ] Aucun outil : ni pytest ni ruff
- [x] ruff reste, pytest part
- [ ] pytest et ruff restent
- [ ] Erreur : `--no-dev` interdit ici
- Réponse : ruff reste : `--no-dev` ne retire que le groupe `dev` ; pour livrer sans aucun groupe, `--no-default-groups`.

## 14. sources : path et git
- Sous-thème : dépendances
- Niveau : 2
- Définition : `[tool.uv.sources]` dit où prendre un paquet hors PyPI : dossier local (`path`), dépôt git (`git` + `branch`/`tag`/`rev`) ou membre (`workspace`).
- Contexte : `uv add ../siren-utils` ou `uv add git+https://… --branch main` écrivent la dépendance et sa source. Le lock fige le commit exact d'une source git : la branche peut avancer, rien ne change avant `uv lock --upgrade-package`. Ces sources sont propres à uv : elles ne partent pas dans les métadonnées d'un wheel publié, où ne reste que le nom.
- Usage : ✅ lib interne pas encore publiée, correctif d'une lib tierce sur un fork · ❌ dossier local hors du dépôt en CI : le chemin n'existe pas sur le runner.

```bash
# Exemple 1 : dossier local et git
uv add ../siren-utils
uv add git+https://github.com/pypa/sampleproject \
  --branch main
```

```toml
# Exemple 2 : ce qu'uv écrit
[tool.uv.sources]
siren-utils = { path = "../siren-utils" }
sampleproject = { git = "https://github.com/pypa/sampleproject", branch = "main" }
# uv.lock : …?branch=main#621e4974…
```

- Quiz : La branche `main` de la lib git reçoit un nouveau commit : que fait le `uv sync` suivant ?
- [ ] Installe le nouveau commit
- [x] Garde le commit du lock
- [ ] Échoue : lock périmé
- [ ] Avertit puis met à jour
- Réponse : garde le commit du lock (`Audited`) : seul `uv lock --upgrade-package <lib>` déplace le commit verrouillé.

## 15. uv python pin : .python-version
- Sous-thème : python
- Niveau : 2
- Définition : `uv python pin 3.12` écrit `.python-version`, l'interpréteur du venv ; `requires-python` reste la plage acceptée par le projet (≈ `.nvmrc` face à `engines`).
- Contexte : Changer le pin recrée le `.venv` au prochain `uv run` (`Removed virtual environment`). Un pin hors de `requires-python` est refusé par `uv python pin`, et `uv run` échoue si on édite le fichier à la main. Ce fichier est aussi lu par pyenv : un pin vers une version que pyenv ne connaît pas casse ses shims (`pyenv: version 3.13 is not installed`), y compris un `uv` installé par pyenv.
- Usage : ✅ pin = runtime Lambda (3.12), commité · ❌ pin plus récent que le runtime : le code passe en local, plante en production.

```bash
# Exemple 1 : changer d'interpréteur
uv python pin 3.13
# Updated `.python-version` from
#   `3.12` -> `3.13`
uv run python --version
# Python 3.13.11  (venv recréé)
```

- Quiz : `requires-python = ">=3.12"` : que fait `uv python pin 3.11` ?
- [ ] Écrit 3.11, le venv suit
- [ ] Écrit 3.11 avec un avertissement
- [x] Erreur : incompatible avec `requires-python`
- [ ] Remplace `requires-python` par `>=3.11`
- Réponse : erreur (`is incompatible with the project requires-python value of >=3.12`) : uv vérifie le pin contre la plage du projet avant d'écrire.

## 16. uv python install : téléchargé à la demande
- Sous-thème : python
- Niveau : 2
- Définition : uv télécharge l'interpréteur demandé s'il manque : explicitement (`uv python install 3.12`) ou au premier `uv run` (≈ `nvm install` intégré).
- Contexte : Les Python gérés par uv vivent dans `~/.local/share/uv/python` ; `uv python list --only-installed` montre aussi ceux du système (Homebrew, pyenv). Plus besoin de pyenv : le `.python-version` suffit, sur le poste comme en CI. `UV_PYTHON_DOWNLOADS=never` interdit le téléchargement : uv n'utilise que ce qui est déjà présent.
- Usage : ✅ runners CI et postes neufs : `uv sync` installe aussi Python · ❌ image Docker figée sans réseau : installer Python au build ou `UV_PYTHON_DOWNLOADS=never` avec un Python de l'image.

```bash
# Exemple 1 : téléchargé au premier besoin
cat .python-version   # 3.13
uv run python --version
# Downloading cpython-3.13.11-macos…
# Python 3.13.11
uv python find 3.13
# ~/.local/share/uv/python/cpython-3.13.11…
```

- Quiz : `.python-version` à `3.14`, absent de la machine, avec `UV_PYTHON_DOWNLOADS=never` : que fait `uv sync` ?
- [ ] Prend le Python le plus récent présent
- [ ] Télécharge quand même 3.14
- [ ] Ignore le fichier, garde le venv
- [x] Erreur : aucun interpréteur 3.14
- Réponse : erreur (`No interpreter found for Python 3.14 … downloads are set to 'never'`) : le pin est une exigence, pas une préférence.

## 17. uv run --with : une dépendance de passage
- Sous-thème : dépendances
- Niveau : 2
- Définition : `uv run --with rich python …` ajoute une dépendance le temps d'une commande, sans toucher `pyproject.toml`, `uv.lock` ni le `.venv`.
- Contexte : uv crée un environnement temporaire superposé au venv du projet : le projet et ses dépendances restent importables, `rich` s'y ajoute. Pratique pour un essai (`ipython`, un profiler) ou un script de diagnostic. `--with` accepte une contrainte (`--with 'rich<14'`) et se répète.
- Usage : ✅ essai ponctuel, outil d'exploration (`uv run --with ipython ipython`) · ❌ dépendance dont le code a besoin : `uv add`, sinon le build et la CI ne l'ont pas.

```bash
# Exemple 1 : rien d'écrit
uv run --with rich python -c "import rich; print('ok')"
# ok
grep -c rich pyproject.toml uv.lock
# pyproject.toml:0
# uv.lock:0
```

- Quiz : Juste après, `uv run python -c "import rich"` : que se passe-t-il ?
- [ ] Ça marche : rich est en cache
- [x] `ModuleNotFoundError`
- [ ] Ça marche : `--with` a installé rich
- [ ] uv propose de l'ajouter
- Réponse : `ModuleNotFoundError` : `--with` n'installe pas dans le `.venv`, il superpose un environnement jetable le temps de la commande.

## 18. uv tool install : une CLI globale
- Sous-thème : outils
- Niveau : 2
- Définition : `uv tool install pre-commit` installe une CLI dans un venv dédié et met son exécutable dans `~/.local/bin` (≈ `pnpm add -g`, isolé).
- Contexte : Chaque outil a son environnement, sans conflit avec les autres ni avec les projets. `uv tool list` les liste, `uv tool upgrade --all` les met à jour, `--with pre-commit-uv` ajoute un plugin. Un outil installé avec une version exacte (`ruff==0.17.1`) reste épinglé : `upgrade` le refuse. Si `~/.local/bin` n'est pas dans le PATH, uv le signale (`uv tool update-shell`).
- Usage : ✅ CLI de poste utilisées partout (pre-commit, httpie, aws-sam-cli) · ❌ outil dont la version doit suivre le projet : `uv add --dev` et `uv run`.

```bash
# Exemple 1 : installer et lister
uv tool install pre-commit
# Installed 1 executable: pre-commit
uv tool list
# pre-commit v4.7.0
# - pre-commit
```

- Quiz : `uv tool install ruff==0.17.1`, puis `uv tool upgrade ruff` : quelle version ensuite ?
- [x] 0.17.1 : la version exacte est retenue
- [ ] La dernière publiée
- [ ] Erreur : outil inconnu
- [ ] 0.17.x la plus récente
- Réponse : 0.17.1 : uv retient la contrainte d'installation et l'indique (`pinned to 0.17.1`) ; `uv tool install ruff@latest` la remplace.

## 19. uv export : un requirements.txt pour la Lambda
- Sous-thème : ci
- Niveau : 2
- Définition : `uv export` convertit `uv.lock` en `requirements.txt` épinglé avec hashes, pour les outils qui ne lisent pas le lock (zip Lambda, `pip`).
- Contexte : `--package ingest` part du graphe d'un membre, `--no-dev` écarte le groupe dev, `--no-emit-workspace` retire les lignes `-e ./packages/…`, `--no-hashes` les hashes. On installe ensuite dans un dossier à zipper, pour la plateforme Lambda et non celle du poste : `uv pip install -r … --target build --python-platform x86_64-manylinux2014 --only-binary :all:`. Les marqueurs (`; sys_platform == 'win32'`) sont conservés.
- Usage : ✅ packager une Lambda ou une image à partir du lock · ❌ un `requirements.txt` maintenu à la main à côté du lock : deux vérités qui divergent.

```bash
# Exemple 1 : les dépendances d'un membre
uv export --package ingest --no-dev \
  --frozen --no-emit-workspace \
  -o req.txt
uv pip install -r req.txt --target build \
  --python-platform x86_64-manylinux2014 \
  --python-version 3.12 --only-binary :all:
ls build   # anyio certifi httpx …
```

- Quiz : À la racine virtuelle du workspace (aucune dépendance propre), que contient `uv export --no-dev` ?
- [ ] Les dépendances de tous les membres
- [ ] Une erreur : `--package` obligatoire
- [x] Rien d'autre que l'en-tête
- [ ] Les seules dépendances de dev
- Réponse : rien : sans `--package` ni `--all-packages`, l'export part du graphe de la racine, vide ici ; d'où `--package <membre>`.

## 20. script : dépendances en tête du fichier
- Sous-thème : outils
- Niveau : 3
- Définition : `uv add --script fetch.py httpx` écrit un bloc `# /// script` (PEP 723) en tête du fichier ; `uv run fetch.py` les installe à part.
- Contexte : Le script devient autonome : ses dépendances et `requires-python` vivent dans ses commentaires, sans `pyproject.toml`. uv crée un environnement dédié, mis en cache. Dès qu'un script a ce bloc, `uv run` ignore le projet qui l'entoure : ni son venv ni ses dépendances. `uv lock --script fetch.py` écrit un `fetch.py.lock` pour figer les versions.
- Usage : ✅ script d'exploration ou d'admin partagé seul (rejouer une journée BODACC, purger un préfixe S3) · ❌ code qui importe les libs du monorepo : le mettre dans un membre du workspace.

```python
# Exemple 1 : le bloc écrit par uv
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx<0.28",
# ]
# ///
import httpx

print(httpx.__version__)
# affiché : 0.27.2  (uv run fetch.py)
```

- Quiz : Ce script, avec son bloc `# /// script`, est posé dans un projet qui dépend de `click` ; il fait `import click`. `uv run` ?
- [ ] Ça marche : click vient du projet
- [ ] uv ajoute click au bloc
- [x] `ModuleNotFoundError: click`
- [ ] Ça marche : `--with` implicite
- Réponse : `ModuleNotFoundError` : avec des métadonnées inline, le script tourne dans son propre environnement, sans le venv du projet ; sans le bloc, il aurait vu click.

## 21. cache : partagé, à élaguer en CI
- Sous-thème : ci
- Niveau : 3
- Définition : uv garde paquets et wheels dans un cache global (`uv cache dir`) et lie les fichiers dans chaque `.venv` au lieu de les copier.
- Contexte : D'où des `uv sync` en millisecondes. En CI, on met le cache dans le projet (`UV_CACHE_DIR`) pour que GitLab le conserve, avec une clé sur `uv.lock`. `uv cache prune --ci` avant la sauvegarde retire les wheels téléchargées (plus rapides à re-télécharger qu'à restaurer) et garde celles compilées depuis les sources. `uv cache clean` vide tout. Cache sur un autre disque que le venv : copie, avertissement, `UV_LINK_MODE=copy`.
- Usage : ✅ cache GitLab clé `uv.lock` + `prune --ci` · ❌ mettre le `.venv` en cache : chemins absolus, interpréteur du runner, restauration fragile.

```yaml
# Exemple 1 : cache uv dans GitLab
variables:
  UV_CACHE_DIR: .uv-cache
test:
  cache:
    key:
      files: [uv.lock]
    paths: [.uv-cache]
  script:
    - uv sync --locked
    - uv run pytest
    - uv cache prune --ci
```

```bash
# Exemple 2 : ce que prune retire
uv cache prune --ci
# Removed 1100 files (34.4MiB)
```

- Quiz : Juste après `uv cache prune --ci`, on supprime `.venv` et lance `uv sync --offline` : que se passe-t-il ?
- [ ] Ça marche : le cache est complet
- [x] Échec : wheels absentes du cache
- [ ] Ça marche, en compilant tout
- [ ] uv ignore `--offline` et télécharge
- Réponse : échec : `prune --ci` a retiré les wheels téléchargées et `--offline` interdit le réseau ; le cache ainsi élagué suppose un réseau rapide.

## 22. uv.lock en conflit : régénérer
- Sous-thème : lock
- Niveau : 3
- Définition : Un conflit git dans `uv.lock` ne se résout pas à la main : régler `pyproject.toml`, reprendre une version du lock, puis `uv lock`.
- Contexte : Deux branches qui ajoutent chacune une dépendance touchent les mêmes lignes du lock. Avec les marqueurs `<<<<<<<`, le fichier n'est plus du TOML valide : `uv lock` et `uv sync` refusent de le lire. Reprendre la version de `main` (`git checkout --theirs` pendant un rebase) puis `uv lock` réintègre les dépendances du `pyproject.toml` fusionné, en gardant les versions verrouillées de `main`.
- Usage : ✅ résoudre d'abord `pyproject.toml`, puis lock repris et régénéré, puis `uv sync --locked` · ❌ fusionner les blocs du lock à la main : hashes et graphe incohérents.

```bash
# Exemple 1 : marqueurs de conflit
uv lock
# 66 | <<<<<<< HEAD
#    |         ^
# key with no value, expected `=`
git checkout --theirs uv.lock
uv lock          # Resolved 10 packages
git add uv.lock
```

- Quiz : Pour aller vite, on supprime `uv.lock` puis on lance `uv lock` : quel effet de bord ?
- [ ] Aucun : même résolution
- [x] Toutes les versions remontent
- [ ] `uv lock` refuse sans ancien lock
- [ ] Seules les dépendances de dev remontent
- Réponse : tout remonte : sans lock existant, uv ne connaît plus les versions verrouillées et prend la plus récente de chaque paquet (anyio 4.4.0 → 4.15.1).
