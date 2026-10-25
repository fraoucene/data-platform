---
title: "Cartes · Packaging Python"
type: cartes
langage: Python
cours: Packaging
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Packaging Python
Python · Packaging : dépendances, distribution, layout, noms, pyproject (format spec v3 de revision-pwa).

## 1. [project] : la carte d'identité
- Sous-thème : pyproject
- Niveau : 1
- Définition : La table `[project]` de `pyproject.toml` décrit le paquet : `name`, `version`, `requires-python`, `dependencies` (≈ `package.json`, standard PEP 621).
- Contexte : Tous les outils lisent ce même format : uv, pip, le backend de build. Au build, ces champs deviennent les métadonnées du wheel (`METADATA`) : `Requires-Dist` pour chaque dépendance, `Requires-Python`. `name` et `version` sont obligatoires ; une version calculée (tag git) se déclare `dynamic = ["version"]`. Les réglages d'outils vivent à côté, sous `[tool.<outil>]`, jamais dans `[project]`.
- Usage : ✅ une source unique pour nom, version et dépendances de chaque membre · ❌ `setup.py` ou `requirements.txt` en parallèle : deux vérités qui divergent.

```toml
# Exemple 1 : packages/bodacc-client
[project]
name = "bodacc-client"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.28.1",
    "pydantic>=2.14.1",
]
```

```bash
# Exemple 2 : ce qui finit dans le wheel
uv build packages/bodacc-client
unzip -p dist/bodacc_client-*.whl \
  '*/METADATA' | grep Requires
# Requires-Dist: httpx>=0.28.1
# Requires-Dist: pydantic>=2.14.1
# Requires-Python: >=3.12
```

- Quiz : On supprime la ligne `version` de `[project]` (sans `dynamic`) : que fait `uv build` ?
- [ ] Construit en version `0.0.0`
- [ ] Prend la version du dernier tag git
- [x] Échoue : `missing field version`
- [ ] Construit, avec un avertissement
- Réponse : échec (`TOML parse error … missing field version`) : `version` est obligatoire, sauf déclarée `dynamic` et fournie par le backend.

## 2. nom : dp-common ou dp_common
- Sous-thème : noms
- Niveau : 1
- Source : data-platform · S1-03
- Définition : `dp-common` est le nom de distribution (uv, lock, PyPI), `dp_common` le nom de module importé : tiret pour `uv add`, underscore pour `import`.
- Contexte : Deux espaces de noms, reliés par le dossier `src/dp_common/` que le backend embarque. `import dp-common` se lit `dp - common` : erreur de syntaxe. Côté distribution, les noms sont normalisés : tiret, underscore, point et casse sont équivalents, `version("DP_Common")` trouve le paquet. Les deux noms peuvent même différer : `PyYAML` s'importe `yaml`, `python-dateutil` `dateutil`. Pas de `@scope/` : on préfixe (`dp-`).
- Usage : ✅ tiret dans `pyproject.toml`, `uv add`, `uv tree` ; underscore dans le code et sous `src/` · ❌ deviner le nom d'import d'une lib tierce (lire sa doc) ; un tiret dans un dossier de module.

```python
# Exemple 1 : module avec underscore
import dp_common
dp_common.project_tag()  # → "data-platform"
```

```python
# Exemple 2 : distribution, nom normalisé
from importlib.metadata import version
version("dp-common")  # → "0.1.0"
version("DP_Common")  # → "0.1.0"
version("dp.common")  # → "0.1.0"
```

- Quiz : À la racine, `uv add dp_common` (underscore) : qu'écrit uv dans `pyproject.toml` ?
- [ ] `dp_common`, tel quel
- [x] `dp-common`, normalisé
- [ ] Rien : paquet introuvable sur PyPI
- [ ] Les deux noms
- Réponse : `dp-common` : uv normalise le nom de distribution (et `[tool.uv.sources] dp-common = { workspace = true }`) ; seul l'`import` exige l'underscore.

## 3. dépendances : les spécificateurs de version
- Sous-thème : dépendances
- Niveau : 1
- Définition : Une dépendance s'écrit `nom` + spécificateurs PEP 440 : `>=2.14`, `<3`, `==0.28.1`, `~=2.14` (compatible), combinables par virgule.
- Contexte : `~=2.14` veut dire `>=2.14, <3` ; `~=2.14.1` veut dire `>=2.14.1, <2.15` : le dernier chiffre écrit est celui qui peut monter. Différence avec npm : pas de `^` ni de `~` à la sauce semver, et pas de borne haute implicite. `==2.14.*` fige une série. `uv add` écrit `>=` + la version résolue, la version exacte vivant dans `uv.lock`.
- Usage : ✅ `>=` minimal dans une lib, `~=` ou `<` quand une rupture est connue · ❌ `==` dans une lib publiée : conflits inévitables chez le consommateur.

```python
# Exemple 1 : ~= selon la précision
from packaging.specifiers import (
    SpecifierSet as S)
"2.15.0" in S("~=2.14")    # → True
"3.0" in S("~=2.14")       # → False
"2.14.9" in S("~=2.14.1")  # → True
```

```python
# Exemple 2 : bornes combinées
from packaging.specifiers import (
    SpecifierSet as S)

s = S(">=0.28.1,<0.29")
"0.28.5" in s  # → True
"0.29.0" in s  # → False
"1.0.1" in S("==1.0.*")  # → True
```

- Quiz : `pydantic~=2.14.1` accepte-t-il la version `2.15.0` ?
- [ ] Oui : même majeure, comme `^2.14.1`
- [x] Non : `~=2.14.1` borne à `<2.15`
- [ ] Oui : `~=` n'a pas de borne haute
- [ ] Non : `~=` exige `2.14.1` exactement
- Réponse : non : `~=` libère seulement l'avant-dernier niveau écrit ; `~=2.14.1` vaut `>=2.14.1, <2.15`.

## 4. version : l'ordre PEP 440
- Sous-thème : dépendances
- Niveau : 1
- Définition : Les versions Python se comparent selon PEP 440 (`packaging.version.Version`) : par segments numériques, avec pré-versions `a`, `b`, `rc` avant la finale.
- Contexte : Comparer des chaînes est faux : `"0.10.0" > "0.9.0"` est `False`, caractère par caractère. `Version` compare des nombres et connaît les suffixes : `1.0.0.dev1 < 1.0.0a1 < 1.0.0rc1 < 1.0.0 < 1.0.0.post1`. Les zéros de fin ne comptent pas. C'est ce que font uv et pip pour choisir une version ; on s'en sert dans un script de release ou un contrôle de compatibilité.
- Usage : ✅ comparer, trier, valider des versions dans un script (`Version(v)`) · ❌ comparer des chaînes ou découper sur `.` à la main.

```python
# Exemple 1 : nombres, pas chaînes
from packaging.version import Version as V
"0.10.0" > "0.9.0"        # → False
V("0.10.0") > V("0.9.0")  # → True
V("1.0.0rc1") < V("1.0.0")  # → True
```

```python
# Exemple 2 : trier des tags de release
from packaging.version import Version

tags = ["0.9.0", "0.10.0", "0.10.0rc1"]
sorted(tags, key=Version)
# → ["0.9.0", "0.10.0rc1", "0.10.0"]
```

- Quiz : Que vaut `Version("1.0") == Version("1.0.0")` ?
- [ ] `False` : segments différents
- [x] `True`
- [ ] `InvalidVersion`
- Réponse : `True` : PEP 440 complète par des zéros avant de comparer ; `1.0`, `1.0.0` et `1.0.0.0` sont la même version.

## 5. wheel ou sdist : deux formats
- Sous-thème : distribution
- Niveau : 1
- Définition : `uv build` produit un sdist (`.tar.gz`, les sources à construire) et un wheel (`.whl`, un zip prêt à installer, sans étape de build).
- Contexte : Le wheel se décompresse tel quel dans `site-packages` : installation rapide, sans exécuter de code. Il contient le module et un dossier `.dist-info` (métadonnées), mais ni `pyproject.toml` ni les tests. Le sdist garde le projet source (`pyproject.toml`, `src/`, `README`) : l'installer demande de reconstruire le wheel. Sur PyPI, on publie les deux ; pour une Lambda, on n'installe que des wheels.
- Usage : ✅ publier sdist + wheel, installer depuis des wheels (CI, image, zip Lambda) · ❌ dépendre d'un sdist en production : build à chaque installation, compilateur parfois requis.

```bash
# Exemple 1 : les deux artefacts
uv build packages/dp-common
# Successfully built dist/dp_common-0.1.0.tar.gz
# Successfully built dist/dp_common-0.1.0-py3-none-any.whl
```

```bash
# Exemple 2 : un wheel est un zip
unzip -l dist/dp_common-0.1.0-*.whl
# dp_common/__init__.py
# dp_common/py.typed
# dp_common-0.1.0.dist-info/WHEEL
# dp_common-0.1.0.dist-info/METADATA
# dp_common-0.1.0.dist-info/RECORD
```

- Quiz : Le wheel de `dp-common` contient-il son `pyproject.toml` ?
- [ ] Oui, à la racine du zip
- [ ] Oui, dans `.dist-info/`
- [x] Non : seulement le module et `.dist-info`
- [ ] Non, il est remplacé par `setup.py`
- Réponse : non : le wheel ne garde que le résultat (module + métadonnées tirées du `pyproject.toml`) ; le `pyproject.toml` lui-même est dans le sdist.

## 6. __init__.py : la façade du paquet
- Sous-thème : layout
- Niveau : 1
- Définition : `__init__.py` fait d'un dossier un paquet et s'exécute au premier import : il réexporte l'API publique, listée dans `__all__` (≈ un `index.ts`).
- Contexte : `from bodacc_client import Annonce` marche parce que `__init__.py` importe `Annonce` depuis `models` : l'appelant ne dépend pas de l'organisation interne. `__all__` déclare l'API publique (lue par `import *`, les linters, la doc). Sans `__init__.py`, le dossier reste importable comme « paquet namespace » : pas d'erreur, mais pas de façade et des pièges de découverte.
- Usage : ✅ un `__init__.py` court qui réexporte les noms publics · ❌ du code lourd dans `__init__.py` (appel réseau, lecture de fichier) : il s'exécute à chaque import.

```python
# Exemple 1 : réexport depuis la façade
import bodacc_client
from bodacc_client import Annonce
from bodacc_client.models import (
    Annonce as A2)
Annonce is A2   # → True  (même classe)
bodacc_client.__all__[0]  # → "Annonce"
```

- Quiz : Un dossier `dp_ns/` sans `__init__.py`, sur le `sys.path` : que fait `import dp_ns` ?
- [ ] `ModuleNotFoundError`
- [x] Import réussi, paquet namespace
- [ ] `ImportError` : `__init__.py` manquant
- [ ] Import réussi seulement avec `python -m`
- Réponse : import réussi, comme paquet namespace (PEP 420, `__file__` vaut `None`) : toujours créer `__init__.py` pour un vrai paquet.

## 7. [build-system] : installable ou virtuel
- Sous-thème : pyproject
- Niveau : 2
- Source : data-platform · S1-03
- Définition : `[build-system]` déclare le backend qui construit le paquet ; sans lui, uv traite le projet comme virtuel : ses dépendances sont installées, lui non.
- Contexte : C'est voulu pour la racine d'un monorepo : un conteneur qui porte le lock, le venv et les outils de dev, rien à importer ni à publier (≈ `"private": true`). Un membre de `packages/` en a besoin pour être importé : `uv init --lib` l'écrit (backend `uv_build`), `uv init --bare` non. Exception : un projet cité en dépendance par un autre est construit quand même, avec setuptools par défaut.
- Usage : ✅ lib importée par d'autres membres, paquet publié · ❌ racine de monorepo, dossier de scripts : pas de `[build-system]`, le projet reste virtuel.

```toml
# Exemple 1 : packages/dp-common
[project]
name = "dp-common"
version = "0.1.0"

[build-system]
requires = ["uv_build>=0.9.28,<0.10.0"]
build-backend = "uv_build"
```

```bash
# Exemple 2 : la racine n'est pas installée
uv pip list
# dp-common 0.1.0  …/packages/dp-common
# pytest    9.1.1
# (pas de data-platform : projet virtuel)
```

- Quiz : `lambdas/x` sans `[build-system]`, que personne ne cite : après `uv sync --all-packages`, `import x` ?
- [x] `ModuleNotFoundError`
- [ ] Importé, en éditable
- [ ] Importé, copié dans le `.venv`
- [ ] `uv sync` échoue : backend manquant
- Réponse : `ModuleNotFoundError` : projet virtuel, `--all-packages` installe ses dépendances mais jamais le projet lui-même ; il lui faut un `[build-system]`.

## 8. src layout : pas d'import par accident
- Sous-thème : layout
- Niveau : 2
- Source : data-platform · S1-03
- Définition : En src layout, le code vit dans `src/<module>/` : il n'est importable qu'une fois installé, jamais par accident depuis le dossier courant.
- Contexte : Python met le dossier courant en tête de `sys.path`. En flat layout (`dp_common/` à la racine du projet), `import dp_common` marche sans installation : les tests passent sur un dossier, pas sur le paquet installé, et un fichier oublié par le build passe inaperçu. `src/` n'a pas de `__init__.py` : le module est `dp_common`, jamais `src.dp_common`.
- Usage : ✅ toute lib de `packages/`, installée en éditable par `uv sync` · ❌ scripts ou projet virtuel : un simple fichier suffit.

```bash
# Exemple 1 : l'arborescence (uv init --lib)
packages/dp-common/
├── pyproject.toml
├── src/dp_common/
│   ├── __init__.py
│   └── py.typed
└── tests/test_smoke.py
```

```bash
# Exemple 2 : sans installation
cd flat/    # dp_common/ à la racine
python3 -c "import dp_common"  # OK
cd ../src_l/  # src/dp_common/
python3 -c "import dp_common"
# ❌ ModuleNotFoundError
```

- Quiz : `dp-common` installé en éditable, on crée `src/dp_common/io.py` : faut-il relancer `uv sync` pour l'importer ?
- [ ] Oui, sinon `ModuleNotFoundError`
- [x] Non, importable tout de suite
- [ ] Oui, et `uv build` avant
- [ ] Non, mais seulement après `uv lock`
- Réponse : non : l'installation éditable pointe vers `src/` (un `.pth`), tout fichier ajouté y est visible ; seul un changement de `pyproject.toml` demande un `uv sync`.

## 9. import relatif : from .models
- Sous-thème : layout
- Niveau : 2
- Définition : `from .util import propre` importe depuis le même paquet ; le point désigne le paquet du module courant, `..` le paquet parent.
- Contexte : Un import relatif dépend de `__package__`, connu seulement quand le fichier est importé comme partie du paquet (`import dp_demo.models`, `python -m`). L'import absolu (`from dp_demo.util import propre`) marche partout et se lit mieux ; la plupart des projets le préfèrent, ruff peut l'imposer (`TID252`). Pas d'équivalent des chemins `./` de TS : on importe des modules, jamais des fichiers.
- Usage : ✅ imports absolus par défaut, relatifs à la rigueur dans un sous-paquet profond · ❌ lancer un module du paquet par son chemin de fichier : `python -m paquet.module`.

```bash
# Exemple 1 : src/dp_demo/models.py
from .util import propre        # relatif
from dp_demo.util import propre # absolu
# importé via le paquet : OK
uv run python -c "import dp_demo.models"
```

```bash
# Exemple 2 : lancer via le paquet
uv run python -m dp_demo
# ingest 483609327
```

- Quiz : Que donne `uv run python src/dp_demo/models.py` (lancé par son chemin) ?
- [ ] Le module s'exécute normalement
- [ ] `ModuleNotFoundError: dp_demo`
- [x] `ImportError` : import relatif sans paquet parent
- [ ] `SyntaxError` sur le point
- Réponse : `ImportError: attempted relative import with no known parent package` : lancé par chemin, le fichier est `__main__`, sans paquet.

## 10. python -m : exécuter un paquet
- Sous-thème : layout
- Niveau : 2
- Définition : `python -m dp_demo` exécute le module `dp_demo/__main__.py` du paquet installé (≈ le champ `bin` d'un package npm, sans installation).
- Contexte : `-m` cherche le module sur `sys.path` comme un `import`, puis l'exécute en `__main__` : les imports du paquet marchent, quel que soit le dossier courant. Pour un paquet, il faut un `__main__.py` ; pour un module simple, `python -m dp_demo.cli` suffit. C'est aussi la façon fiable de lancer un outil du venv : `python -m pytest`, `python -m pip`.
- Usage : ✅ point d'entrée d'un paquet en dev, job lancé en CI ou en conteneur · ❌ `python chemin/vers/fichier.py` dans un paquet : les imports relatifs cassent.

```bash
# Exemple 1 : src/dp_demo/__main__.py
from dp_demo.models import main
main()
# puis :
uv run python -m dp_demo
# ingest 483609327
```

- Quiz : On retire `__main__.py`, puis `uv run python -m dp_demo` : résultat ?
- [ ] Exécute `__init__.py` à la place
- [ ] Ne fait rien, code retour 0
- [x] Erreur : `cannot be directly executed`
- [ ] `ModuleNotFoundError: dp_demo`
- Réponse : erreur `No module named dp_demo.__main__; 'dp_demo' is a package and cannot be directly executed` : un paquet n'est exécutable qu'avec un `__main__.py`.

## 11. [project.scripts] : une commande installée
- Sous-thème : pyproject
- Niveau : 2
- Définition : `[project.scripts]` déclare une commande (`dp-ingest = "dp_demo.models:main"`) que l'installation crée dans `.venv/bin`, appelant cette fonction.
- Contexte : Le wheel porte un `entry_points.txt` ; l'installeur écrit un petit script qui importe la fonction et fait `sys.exit(main())`. La commande s'appelle par son nom, sans `python -m` (≈ `bin` dans `package.json`). La valeur de retour de `main` devient le code de sortie : `None` ou `0` = succès, un entier non nul = échec, une chaîne = affichée puis code 1.
- Usage : ✅ CLI d'un paquet (`dp-ingest --day 2026-10-20`), lancée par `uv run dp-ingest` · ❌ scripts internes jamais installés : un `Makefile` ou `python -m` suffit.

```toml
# Exemple 1 : pyproject.toml
[project.scripts]
dp-ingest = "dp_demo.models:main"
```

```bash
# Exemple 2 : après uv sync
uv run dp-ingest
# ingest 483609327
tail -3 .venv/bin/dp-ingest
#     sys.exit(main())
```

- Quiz : `main()` finit par `return len(annonces)` (25 annonces) : quel code de sortie voit la CI ?
- [ ] `0` : la commande a réussi
- [x] `25`, donc un échec
- [ ] `1`
- [ ] `0`, la valeur est ignorée
- Réponse : `25` : le script fait `sys.exit(main())`, la valeur rendue devient le code de sortie ; `main` doit rendre `None` ou `0`.

## 12. extras : des dépendances à la carte
- Sous-thème : dépendances
- Niveau : 2
- Définition : `[project.optional-dependencies]` déclare des extras : `s3 = ["boto3>=1.35"]` n'est installé que si on demande `dp-demo[s3]`.
- Contexte : Dans le wheel, chaque dépendance d'extra porte un marqueur `extra == 's3'` : ignorée sans l'extra. Un consommateur choisit : `uv add 'dp-demo[s3]'`, plusieurs extras séparés par des virgules (`[s3,cli]`). Sous zsh, les crochets sont un motif de fichiers : sans guillemets, la commande échoue avant d'atteindre uv. À distinguer des dependency groups (`dev`), jamais publiés.
- Usage : ✅ dépendance lourde utile à une partie des usages (boto3, pyarrow) · ❌ outils de test ou de lint : `uv add --dev`.

```toml
# Exemple 1 : déclarer l'extra
[project.optional-dependencies]
s3 = ["boto3>=1.35"]
# METADATA du wheel :
# Requires-Dist: boto3>=1.35 ; extra == 's3'
# Provides-Extra: s3
```

```python
# Exemple 2 : la ligne, lue par packaging
from packaging.requirements import (
    Requirement)
r = Requirement('boto3>=1.35; extra == "s3"')
r.marker.evaluate({"extra": "s3"})  # → True
r.marker.evaluate({"extra": ""})    # → False
sorted(Requirement(
    "dp-demo[s3,cli]").extras)
# → ["cli", "s3"]
```

- Quiz : Dans zsh, que fait `uv add dp-demo[s3]` (sans guillemets) ?
- [ ] Ajoute `dp-demo` avec l'extra `s3`
- [ ] Ajoute `dp-demo` sans l'extra
- [x] `zsh: no matches found: dp-demo[s3]`
- [ ] uv refuse : extra inconnu
- Réponse : `no matches found` : zsh lit `[s3]` comme un motif de fichiers et s'arrête ; écrire `'dp-demo[s3]'`.

## 13. marqueurs : une dépendance conditionnelle
- Sous-thème : dépendances
- Niveau : 2
- Définition : Un marqueur d'environnement (`; python_version < "3.11"`, `; sys_platform == "linux"`) n'installe la dépendance que si la condition est vraie.
- Contexte : Le marqueur suit la dépendance après un `;` et s'évalue à l'installation, sur la machine cible. `python_version` se compare comme une **version**, pas comme une chaîne : `"3.10" > "3.9"` est vrai. uv résout pour toutes les plateformes à la fois (lock universel) et garde le marqueur dans `uv.lock`. Cas classique : `tomli` seulement avant 3.11, où `tomllib` est arrivé dans la bibliothèque standard.
- Usage : ✅ rétroportage pour une vieille version de Python, dépendance propre à un OS · ❌ dépendance requise partout : sans marqueur ; choix d'option par l'utilisateur : un extra.

```toml
# Exemple 1 : pyproject.toml
dependencies = [
    "tomli>=2; python_version < '3.11'",
    "uvloop; sys_platform == 'linux'",
]
```

```python
# Exemple 2 : évaluer un marqueur
from packaging.markers import Marker
m = Marker("python_version < '3.11'")
m.evaluate()   # → False  (Python 3.12)
m.evaluate({"python_version": "3.10"})
# → True
```

- Quiz : Que vaut `Marker("python_version > '3.9'").evaluate({"python_version": "3.10"})` ?
- [x] `True`
- [ ] `False` : `"3.10" < "3.9"` en chaîne
- [ ] `InvalidMarker`
- Réponse : `True` : `python_version` est comparé comme une version PEP 440 (10 > 9), pas caractère par caractère.

## 14. requires-python : la borne qui résout
- Sous-thème : dépendances
- Niveau : 2
- Définition : `requires-python = ">=3.12"` déclare les versions de Python supportées ; uv résout les dépendances pour **toute** cette plage, pas seulement pour le Python local.
- Contexte : Le lock d'uv est universel : il doit fonctionner pour chaque version permise. Une dépendance qui exige `>=3.13` rend la résolution impossible tant que le projet promet 3.12, même si le `.venv` tourne déjà en 3.13. Le message le dit et propose de relever la borne. Côté consommateur, `Requires-Python` empêche l'installation sur un Python trop ancien.
- Usage : ✅ aligner `requires-python` sur le runtime réel (Lambda `python3.12`), relever quand une dépendance l'exige · ❌ borne haute (`<3.14`) par précaution : elle bloque les consommateurs sans raison.

```bash
# Exemple 1 : dp-new exige >=3.13
uv add ../new    # projet : >=3.12
# × No solution found when resolving
#   dependencies: the requested Python
#   version (>=3.12) does not satisfy
#   Python>=3.13
```

```bash
# Exemple 2 : relever la borne
# requires-python = ">=3.13"
uv add ../new
# + dp-new==0.1.0
```

- Quiz : Projet en `>=3.12`, `.venv` déjà en Python 3.13 : `uv add ../new` (qui exige `>=3.13`) passe-t-il ?
- [ ] Oui : le `.venv` est en 3.13
- [x] Non : la résolution couvre aussi 3.12
- [ ] Oui, avec un avertissement
- [ ] Non : uv recrée le `.venv` en 3.12
- Réponse : non : uv résout pour toute la plage `requires-python`, pas pour le seul interpréteur local ; relever la borne à `>=3.13`.

## 15. bornes : plage dans la lib, versions dans le lock
- Sous-thème : dépendances
- Niveau : 2
- Définition : Une lib publie des plages (`pydantic>=2.14.1`) ; les versions exactes de `uv.lock` ne servent qu'au projet lui-même, jamais à ses consommateurs.
- Contexte : `uv.lock` n'entre ni dans le wheel ni dans le sdist : un projet qui installe `bodacc-client` résout ses propres versions dans la plage `Requires-Dist`. D'où la règle : une application (Lambda, job) garantit ses versions par le lock ; une lib reste large pour cohabiter avec d'autres. Comme en npm, où le `package-lock.json` d'une dépendance est ignoré.
- Usage : ✅ lib : `>=` minimal testé ; application : `uv.lock` commité, `uv sync --frozen` en CI · ❌ figer `==` dans une lib pour « stabiliser » : conflits chez chaque consommateur.

```bash
# Exemple 1 : le lock n'est pas publié
uv build packages/bodacc-client
tar tzf dist/bodacc_client-0.1.0.tar.gz \
  | grep -c lock
# 0
unzip -p dist/bodacc_client-*.whl \
  '*/METADATA' | grep Requires-Dist
# Requires-Dist: pydantic>=2.14.1
```

- Quiz : Un autre projet installe `bodacc-client` publié (lock : `pydantic==2.14.1`) : quel pydantic reçoit-il ?
- [ ] `2.14.1`, la version du lock
- [x] La plus récente qui respecte `>=2.14.1` et ses autres contraintes
- [ ] Aucune : à installer à la main
- [ ] `2.14.1`, si `--frozen` est passé
- Réponse : la plus récente compatible : seul `Requires-Dist` (`>=2.14.1`) voyage avec le paquet ; le lock reste chez son auteur.

## 16. éditable : un .pth vers src/
- Sous-thème : distribution
- Niveau : 2
- Définition : Une installation éditable (`uv sync` pour un membre du workspace) pointe vers les sources sans les copier : un `.pth` ajoute `src/` au `sys.path`.
- Contexte : Dans `site-packages`, `dp_common.pth` contient une seule ligne, le chemin de `packages/dp-common/src` ; Python l'ajoute au `sys.path` au démarrage. Une modification du code est donc visible sans réinstaller (≈ `pnpm link` / `workspace:*`). Un wheel installé, lui, copie les fichiers dans `site-packages` : les sources peuvent changer, l'installé non. `direct_url.json` porte `"editable": true`.
- Usage : ✅ membres du monorepo en dev, installés éditables par `uv sync` · ❌ image Docker ou zip de Lambda : installer le wheel (copie figée, reproductible).

```bash
# Exemple 1 : le .pth
cat .venv/lib/python3.12/site-packages/\
dp_common.pth
# /…/data-platform/packages/dp-common/src
```

```python
# Exemple 2 : importé depuis les sources
import dp_common
f = dp_common.__file__
"packages/dp-common/src" in f  # → True
"site-packages" in f           # → False
```

- Quiz : `dp-demo` installé depuis son wheel dans un autre venv ; on ajoute `NOUVEAU = 1` dans `src/dp_demo/util.py` : ce venv le voit-il ?
- [ ] Oui, au prochain import
- [x] Non : le wheel a copié les fichiers
- [ ] Oui, après `uv lock`
- [ ] Non, et l'import lève une erreur
- Réponse : non : un wheel installé est une copie dans `site-packages` ; seule une installation éditable suit les sources.

## 17. fichiers de données : importlib.resources
- Sous-thème : layout
- Niveau : 2
- Définition : Un fichier non Python placé dans le module (`src/dp_demo/tribunaux.json`) est embarqué dans le wheel ; on le lit avec `importlib.resources.files(...)`.
- Contexte : `files("dp_demo")` désigne le dossier du paquet installé, où qu'il soit (site-packages, zip de Lambda) : le chemin ne dépend pas du dossier courant. Le backend `uv_build` embarque tout ce qui est sous `src/<module>/`, `py.typed` compris : ce fichier vide (PEP 561) annonce aux vérificateurs de types que le paquet est annoté. Un fichier hors du module (racine du projet) n'est pas dans le wheel.
- Usage : ✅ référentiels livrés avec le code (liste de tribunaux, schéma JSON, SQL) · ❌ `open("tribunaux.json")` ou un chemin bâti sur le dossier courant : faux dès qu'on lance ailleurs.

```python
# Exemple 1 : un fichier du paquet
from importlib.resources import files
p = files("bodacc_client") / "py.typed"
p.is_file()   # → True
p.read_text() # → ""  (marqueur vide)
```

```bash
# Exemple 2 : embarqué dans le wheel
unzip -l dist/dp_demo-0.1.0-*.whl
# dp_demo/__init__.py
# dp_demo/py.typed
# dp_demo/tribunaux.json
```

- Quiz : Dans la Lambda (dossier courant `/var/task`), le code de `dp_demo` fait `open("tribunaux.json")` : résultat ?
- [ ] Ouvre le fichier à côté du module
- [x] `FileNotFoundError`
- [ ] Ouvre le fichier via le wheel
- [ ] `ModuleNotFoundError`
- Réponse : `FileNotFoundError` : un chemin relatif part du dossier courant, pas du module ; utiliser `files("dp_demo") / "tribunaux.json"`.

## 18. tags de wheel : pur Python ou compilé
- Sous-thème : distribution
- Niveau : 3
- Définition : Le nom d'un wheel porte ses tags `python-abi-plateforme` : `py3-none-any` tourne partout, `cp312-cp312-macosx_11_0_arm64` seulement sur ce Python et cet OS.
- Contexte : httpx est pur Python (`py3-none-any`) ; pydantic-core est compilé en Rust, avec un wheel par plateforme. Installer sur un Mac puis zipper pour Lambda (Linux) embarque le `.so` macOS : la Lambda plante à l'import. On installe pour la cible : `uv pip install --python-platform x86_64-manylinux2014 --python-version 3.12 --target build/`, ou on construit dans une image Linux.
- Usage : ✅ zip de Lambda construit pour la plateforme et l'architecture de la fonction (x86_64 ou arm64) · ❌ zipper le `.venv` du Mac : binaires incompatibles.

```python
# Exemple 1 : lire les tags
from packaging.utils import (
    parse_wheel_filename as p)
_, _, _, t = p("httpx-0.28.1-py3-none-any.whl")
str(next(iter(t)))  # → "py3-none-any"
_, _, _, t = p("pydantic_core-2.50.1-"
    "cp312-cp312-macosx_11_0_arm64.whl")
next(iter(t)).platform
# → "macosx_11_0_arm64"
```

```bash
# Exemple 2 : installer pour Lambda
uv pip install --python-version 3.12 \
  --python-platform x86_64-manylinux2014 \
  --target build/ pydantic-core==2.50.1
ls build/pydantic_core | grep so
# _pydantic_core.cpython-312-x86_64-linux-gnu.so
```

- Quiz : Le zip de Lambda contient le pydantic-core installé sur le Mac (`darwin.so`) : que se passe-t-il ?
- [ ] Ça marche : Python est portable
- [ ] Lambda recompile le module au démarrage
- [x] `ImportError` à l'import de pydantic
- [ ] `SyntaxError` au chargement
- Réponse : `ImportError` (sur `pydantic_core._pydantic_core`) : le binaire compilé pour macOS ne se charge pas sous Linux ; installer pour la plateforme cible.

## 19. version installée : importlib.metadata
- Sous-thème : distribution
- Niveau : 3
- Définition : `importlib.metadata.version("bodacc-client")` lit la version dans les métadonnées installées (`.dist-info`), pas dans `pyproject.toml`.
- Contexte : Une seule source : la `version` de `pyproject.toml`, recopiée dans `METADATA` à l'installation ; inutile de dupliquer un `__version__` en dur, qui finit par diverger. Piège en éditable : le code suit les sources, mais les métadonnées datent du dernier `uv sync`. Après un changement de version dans `pyproject.toml`, `.venv/bin/python` lit encore l'ancienne ; `uv run`, qui resynchronise d'abord, lit la nouvelle.
- Usage : ✅ afficher la version dans un log, un `User-Agent` (`data-platform-bodacc-client/0.1`), une sortie `--version` · ❌ `__version__` écrit à la main en plus de `pyproject.toml`.

```python
# Exemple 1 : lire la version installée
from importlib.metadata import version
version("bodacc-client")  # → "0.1.0"
version("pydantic")       # → "2.14.1"
```

```bash
# Exemple 2 : métadonnées en retard
# pyproject.toml : 0.1.0 → 0.2.0
.venv/bin/python -c "from importlib.\
metadata import version as v; \
print(v('dp-demo'))"
# 0.1.0   (pas encore resynchronisé)
```

- Quiz : Juste après, sans autre commande : que rend `uv run python -c "…print(v('dp-demo'))"` ?
- [ ] `0.1.0` : l'éditable ne change rien
- [x] `0.2.0`
- [ ] `PackageNotFoundError`
- [ ] `0.1.0`, il faut `uv build`
- Réponse : `0.2.0` : `uv run` resynchronise le `.venv` (réinstalle `dp-demo`) avant de lancer ; `--no-sync` afficherait `0.1.0`.

## 20. dist-info : une distribution installée
- Sous-thème : distribution
- Niveau : 3
- Définition : Chaque paquet installé a un dossier `<nom>-<version>.dist-info` : `METADATA`, `RECORD` (fichiers installés), `entry_points.txt`, `direct_url.json`.
- Contexte : C'est ce que lisent `importlib.metadata`, `uv pip list` et la désinstallation : `RECORD` liste chaque fichier posé, avec son empreinte, pour pouvoir tout retirer. `distribution(nom).files` en donne la liste. Une installation éditable n'y inscrit que le `.pth` et les métadonnées : le code reste dans `src/`. `entry_points(group="console_scripts")` retrouve les commandes déclarées.
- Usage : ✅ diagnostiquer « quelle version, installée d'où, avec quels fichiers » · ❌ modifier un `.dist-info` à la main : réinstaller.

```python
# Exemple 1 : la carte d'un paquet installé
from importlib.metadata import (
    distribution, metadata)
m = metadata("bodacc-client")
m["Requires-Python"]  # → ">=3.12"
m.get_all("Requires-Dist")
# → ["httpx>=0.28.1", "pydantic>=2.14.1"]
```

- Quiz : `dp-common` installé en éditable : `distribution("dp-common").files` contient-il `dp_common/__init__.py` ?
- [ ] Oui, comme tout paquet installé
- [x] Non : seulement `.dist-info` et `dp_common.pth`
- [ ] Oui, en lien symbolique
- [ ] `files` vaut `None`
- Réponse : non : en éditable, rien n'est copié ; `RECORD` ne liste que les métadonnées et le `.pth` qui pointe vers `src/`.
