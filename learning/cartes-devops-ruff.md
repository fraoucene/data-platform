---
title: "Cartes · Ruff"
type: cartes
langage: DevOps
cours: Ruff
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Ruff
DevOps · Ruff : commandes, config, format, noqa, règles (format spec v3 de revision-pwa).

## 1. check ou format : lint ou mise en forme
- Sous-thème : commandes
- Niveau : 1
- Source : data-platform · S1-03
- Définition : `ruff check` est le linter (≈ eslint : `F401`, `E501`, `I001`), `ruff format` le formateur (≈ prettier : quotes, espaces, virgules) : deux contrôles distincts.
- Contexte : `x='a'` passe le lint et échoue au format. Le formateur ne touche qu'à la mise en forme : il ne trie jamais les imports, car les réordonner change l'ordre d'exécution des modules ; `I001` se corrige avec `ruff check --fix`. En CI, `ruff format --check` ne modifie rien et renvoie 1 si un fichier doit changer : d'où deux lignes dans `make lint`.
- Usage : ✅ `make lint` = `check` + `format --check`, `make fmt` = les deux avec correction · ❌ `ruff format` seul avant un commit : imports non triés ou inutiles restent.

```bash
# Exemple 1 : même fichier, deux verdicts
# a.py : import sys / import os / x='a'
ruff check a.py
# I001 Import block is un-sorted
# F401 `sys` imported but unused
ruff format --check a.py
# 1 file would be reformatted  (code 1)
```

```bash
# Exemple 2 : format ne trie pas
ruff format a.py
# 1 file reformatted
ruff check a.py
# I001, F401 toujours là
ruff check --fix a.py
# Found 3 errors (3 fixed, 0 remaining)
```

- Quiz : `ruff format`, puis `ruff check --fix` qui supprime des imports inutiles : `ruff format --check` passe-t-il ?
- [ ] Oui : le fichier vient d'être formaté
- [ ] Oui : `--fix` reformate aussi
- [ ] Non : les imports restent non triés
- [x] Non : une ligne vide reste en tête
- Réponse : non : `--fix` retire les imports mais laisse la ligne vide qui les suivait ; d'où l'ordre `check --fix` puis `format` (celui du hook pre-commit).

## 2. --fix : corriger sur place
- Sous-thème : commandes
- Niveau : 1
- Définition : `ruff check --fix` applique les corrections sûres (marquées `[*]`) et ne signale plus que le reste (≈ `eslint --fix`).
- Contexte : Seules les règles qui proposent une correction sûre sont touchées : imports inutiles (F401), tri (I001), syntaxe moderne (UP). Le code retour ne dépend que de ce qui reste : 0 si tout a été corrigé. `--diff` montre les corrections sans écrire, `--exit-non-zero-on-fix` fait échouer quand même s'il a fallu corriger. `--output-format concise` donne une ligne par erreur.
- Usage : ✅ `make fmt`, hook pre-commit `ruff-check --fix`, éditeur à l'enregistrement · ❌ `--fix` en CI : la CI doit signaler, pas réécrire un code qui ne sera pas commité.

```bash
# Exemple 1 : ce qui est corrigé
ruff check a.py --output-format concise
# F401 [*] `os` imported but unused
# B006 Do not use mutable data …
ruff check --fix a.py
# Found 4 errors (2 fixed, 2 remaining).
```

```bash
# Exemple 2 : voir avant d'écrire
ruff check --diff a.py
# -import os
# Would fix 2 errors (2 additional
#   fixes available with --unsafe-fixes)
```

- Quiz : `ruff check --fix` corrige les 3 erreurs d'un fichier, il n'en reste aucune : quel code retour ?
- [ ] 1 : il y avait des erreurs
- [x] 0
- [ ] 2 : fichier modifié
- [ ] 1, sauf avec `--quiet`
- Réponse : 0 (`Found 3 errors (3 fixed, 0 remaining)`) : seul ce qui reste compte ; `--exit-non-zero-on-fix` renvoie 1 dès qu'une correction a été faite.

## 3. select : les familles de règles
- Sous-thème : règles
- Niveau : 1
- Définition : `select = ["E", "F", "I", "UP", "B"]` active des règles par préfixe : une famille entière (`E`), un groupe (`E5`) ou une règle (`E501`).
- Contexte : Chaque préfixe reprend un outil historique : `E`/`W` pycodestyle, `F` pyflakes, `I` isort, `UP` pyupgrade, `B` bugbear, `RUF` règles propres à ruff. `select` remplace le jeu par défaut au lieu de s'y ajouter ; `extend-select` ajoute. Depuis ruff 0.17, le jeu par défaut compte environ 400 règles (`B`, `UP`, `I`, `RUF`, `SIM`…), mais pas `E501`. `ruff linter` liste les préfixes.
- Usage : ✅ `select` explicite dans le `pyproject.toml` du monorepo, relu en revue · ❌ `select = ["ALL"]` : des règles contradictoires et des centaines d'alertes de style.

```toml
# Exemple 1 : la config de data-platform
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

```bash
# Exemple 2 : ajouter sans remplacer
ruff check --extend-select E501 \
  --output-format concise long.py
# long.py:1:89: E501 Line too long
#   (136 > 88)
# long.py:2:8: F401 [*] `os` imported …
```

- Quiz : On remplace `select = [...]` par `select = ["E501"]` pour tester les lignes longues : `import os` inutilisé est-il encore signalé ?
- [ ] Oui : F401 fait partie du défaut
- [ ] Oui : F est toujours actif
- [x] Non : seule E501 est active
- [ ] Non, mais `--fix` le retire
- Réponse : non : `select` remplace tout le jeu de règles ; pour ajouter E501 sans rien perdre, `extend-select`.

## 4. noqa : taire une ligne
- Sous-thème : noqa
- Niveau : 1
- Définition : `# noqa: F401` en fin de ligne fait ignorer cette règle sur cette ligne ; `# noqa` seul les ignore toutes (≈ `// eslint-disable-line`).
- Contexte : Toujours nommer la règle : un `# noqa` nu masque aussi les erreurs futures de la ligne. Plusieurs codes se séparent par des virgules (`# noqa: F401, E501`) ; la casse et l'espace après `:` sont tolérés (`# NOQA:F401`). Pour tout un fichier, `# ruff: noqa: F401` en tête ; pour un dossier, `per-file-ignores`.
- Usage : ✅ exception justifiée et rare : import pour effet de bord, ligne générée · ❌ faire passer la CI : corriger, ou désactiver la règle dans la config si elle ne convient pas au projet.

```python
# Exemple 1 : import gardé exprès
import os  # noqa: F401
import sys  # noqa

print("ok")
```

- Quiz : `import json  # noqa: E501` sur un import inutilisé : `ruff check` signale-t-il la ligne ?
- [ ] Non : la ligne porte un noqa
- [x] Oui : F401, non listée
- [ ] Oui : `noqa` invalide, E501 absente
- [ ] Non, mais avertit
- Réponse : oui, F401 : un `noqa` avec codes ne tait que ces codes ; E501 n'a rien à taire ici (RUF100 le signalerait).

## 5. ruff rule : expliquer un code
- Sous-thème : commandes
- Niveau : 1
- Définition : `ruff rule B006` affiche la documentation d'une règle : ce qu'elle détecte, pourquoi, exemple, correction disponible ou non.
- Contexte : Plus rapide que chercher sur le web, et à la version installée. Le nom lisible (`mutable-argument-default`) accompagne le code ; `ruff check --statistics` compte les erreurs par règle avant de décider d'en ignorer une. « Fix is sometimes available » veut dire que la correction ne s'applique pas à tous les cas, ou seulement en unsafe.
- Usage : ✅ avant d'ajouter un `noqa` ou un `ignore` : comprendre ce que la règle protège · ❌ ignorer une règle `B` sans l'avoir lue : ce sont de vrais bugs.

```bash
# Exemple 1 : la doc d'une règle
ruff rule F401 | head -4
# # unused-import (F401)
#
# Derived from the **Pyflakes** linter.
```

```bash
# Exemple 2 : compter avant de trier
ruff check --statistics --select F,B .
# 2  F401  [*] unused-import
# 1  B006  [ ] mutable-argument-default
# 1  F841  [ ] unused-variable
```

- Quiz : Dans `--statistics`, B006 est marquée `[ ]` alors que `ruff check` la décrit avec une correction : pourquoi ?
- [ ] Ruff ne sait pas la corriger
- [x] Sa correction est unsafe
- [ ] Elle demande `--preview`
- [ ] La règle est désactivée
- Réponse : correction unsafe : `[*]` ne marque que les corrections sûres ; B006 se corrige avec `--fix --unsafe-fixes`, car elle change le comportement.

## 6. line-length : format et E501
- Sous-thème : format
- Niveau : 1
- Définition : `line-length` (88 par défaut) sert au formateur, qui coupe le code, et à la règle E501, qui signale les lignes trop longues restantes.
- Contexte : `ruff format` coupe appels, listes et expressions, jamais une chaîne : une longue phrase reste longue, et seule E501 la signale si `E` est sélectionnée. E501 tolère une ligne qui se termine par une URL commencée avant la limite, et un « mot » unique trop long. Dans data-platform, 120 vaut pour les deux, déclarée une fois sous `[tool.ruff]`.
- Usage : ✅ une seule `line-length` sous `[tool.ruff]` · ❌ `line-length` différente sous `[tool.ruff.format]` et `[tool.ruff.lint]` : le formateur produit des lignes que le linter refuse.

```bash
# Exemple 1 : format ne coupe pas les chaînes
# msg = "Annonce BODACC du tribunal … radiée"
ruff format f.py
ruff check --select E501 f.py \
  --output-format concise
# f.py:7:89: E501 Line too long (97 > 88)
```

- Quiz : `URL = "https://bodacc-datadila.opendatasoft.com/…/records"` fait 113 caractères, limite 88 : E501 la signale-t-elle ?
- [ ] Oui : 113 > 88
- [x] Non : la ligne finit par une URL
- [ ] Non : E501 ignore les chaînes
- [ ] Oui, et `format` la coupe
- Réponse : non : E501 laisse passer une ligne qui se termine par une URL commencée avant la limite ; une phrase de 97 caractères, elle, est signalée.

## 7. config : le pyproject le plus proche
- Sous-thème : config
- Niveau : 2
- Source : data-platform · S1-03
- Définition : Pour chaque fichier, ruff prend le `pyproject.toml` le plus proche qui contient `[tool.ruff]` : une config racine couvre tous les membres.
- Contexte : Un `pyproject.toml` de membre sans `[tool.ruff]` est sauté, la recherche remonte jusqu'à la racine : `line-length = 120` y vaut pour `packages/*`. Les configs ne fusionnent pas : la plus proche s'applique seule, sauf `extend`. `src` liste les dossiers first-party pour le tri d'imports (`I`). `ruff check --show-settings <fichier>` affiche le fichier retenu.
- Usage : ✅ une seule section `[tool.ruff]` à la racine du monorepo · ❌ une section `[tool.ruff]` dans un membre sans `extend` vers la racine.

```bash
# Exemple 1 : quelle config pour ce fichier ?
ruff check --show-settings \
  packages/dp-common/src/dp_common/__init__.py \
  | grep -E "^Settings path|line_length ="
# Settings path: "…/data-platform/pyproject.toml"
# linter.line_length = 120
```

```toml
# Exemple 2 : exception dans un membre
# packages/x/pyproject.toml
[tool.ruff]
extend = "../../pyproject.toml"
line-length = 100  # le reste : racine
```

- Quiz : Un membre ajoute seulement `[tool.ruff]` avec `target-version = "py312"` : quelle `line-length` pour ses fichiers ?
- [ ] 120, héritée de la racine
- [x] 88
- [ ] 100
- [ ] Aucune limite
- Réponse : 88, la valeur par défaut : la config la plus proche remplace la racine en entier ; sans `extend`, les 120 sont perdus.

## 8. target-version : ce que UP réécrit
- Sous-thème : règles
- Niveau : 2
- Source : data-platform · S1-03
- Définition : `target-version = "py312"` donne à ruff la version minimale de Python visée : les règles `UP` (pyupgrade) proposent la syntaxe moderne qu'elle autorise.
- Contexte : En `py312`, `Optional[str]` devient `str | None` (UP045) et `List[str]` devient `list[str]` (UP006). Sans `target-version`, ruff la déduit de `requires-python`. Les règles s'activent par préfixe dans `[tool.ruff.lint] select` : `E` pycodestyle, `F` pyflakes, `I` isort, `UP` pyupgrade, `B` bugbear (≈ plugins eslint).
- Usage : ✅ aligner `target-version` sur `requires-python` et le runtime Lambda (3.12) · ❌ viser plus haut que le runtime : ruff propose une syntaxe qui plante en production.

```bash
# Exemple 1 : la réécriture en py312
# t.py : def f(s: Optional[str]) -> List[str]
ruff check --select UP --fix t.py
# → def f(s: str | None) -> list[str]
```

```toml
# Exemple 2 : la config racine
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- Quiz : En `target-version = "py39"`, `ruff check --select UP` signale-t-il `s: Optional[str]` ?
- [ ] Oui : UP045, `str | None`
- [x] Non : rien sur cette annotation
- [ ] Oui : UP006, `list`
- [ ] Erreur : `Optional` est déprécié
- Réponse : non : `X | None` n'existe qu'à partir de Python 3.10, ruff ne le propose pas pour une cible 3.9.

## 9. --unsafe-fixes : changer le comportement
- Sous-thème : commandes
- Niveau : 2
- Définition : Une correction « unsafe » peut changer ce que fait le code ; `--fix` l'ignore, `--fix --unsafe-fixes` l'applique.
- Contexte : B006 (`def f(sirens=[])`) devient `sirens=None` + `if sirens is None` : même intention, mais un appelant qui passait `None` exprès change de comportement. F841 retire une affectation inutile, mais son expression aurait pu avoir un effet. `--unsafe-fixes` seul ne fait qu'afficher ces corrections comme disponibles (`[*]`). `extend-safe-fixes = ["F841"]` promeut une règle en sûre.
- Usage : ✅ `--fix --unsafe-fixes --diff`, relu, sur un fichier précis · ❌ `--unsafe-fixes` dans un hook ou `make fmt` : des changements de logique sans relecture.

```bash
# Exemple 1 : appliquer, puis relire
ruff check --fix --unsafe-fixes u.py
# def f(sirens=None):
#     if sirens is None:
#         sirens = []
#     return sirens   (x = 1 retiré)
```

```toml
# Exemple 2 : promouvoir une règle
[tool.ruff.lint]
extend-safe-fixes = ["F841"]
```

- Quiz : `ruff check --unsafe-fixes u.py`, sans `--fix` : que devient le fichier ?
- [ ] Les corrections unsafe sont appliquées
- [ ] Toutes les corrections sont appliquées
- [x] Rien : il affiche les corrections, `[*]`
- [ ] Erreur : `--fix` manquant
- Réponse : rien : `--unsafe-fixes` seul rend ces corrections visibles (marquées `[*]`), seul `--fix` écrit le fichier.

## 10. ignore : la règle la plus précise gagne
- Sous-thème : règles
- Niveau : 2
- Définition : `ignore = ["E501"]` désactive une règle pour tout le projet ; entre `select` et `ignore`, le préfixe le plus précis l'emporte.
- Contexte : `select = ["E"]` + `ignore = ["E501"]` : toutes les E sauf E501. À l'inverse, `select = ["E501"]` + `ignore = ["E"]` garde E501, plus précise que `E`. À précision égale, `ignore` gagne. Ignorer globalement vaut pour une règle qui ne convient pas au projet ; un cas isolé relève de `noqa`, un dossier de `per-file-ignores`.
- Usage : ✅ règle incompatible avec le style du projet (E501 laissée au formateur) · ❌ ignorer une famille entière (`B`) pour faire taire une seule alerte.

```bash
# Exemple 1 : la plus précise gagne
ruff check --isolated --select E \
  --ignore E501 --output-format concise long.py
# long.py:2:1: E402 Module level import …
#   (E501 ignorée)
```

- Quiz : `select = ["E501"]` et `ignore = ["E"]` : la ligne de 136 caractères est-elle signalée ?
- [x] Oui : E501 est plus précise que E
- [ ] Non : `ignore` passe toujours en dernier
- [ ] Non : aucune règle active
- [ ] Erreur : configuration contradictoire
- Réponse : oui (`E501 Line too long (136 > 88)`) : ruff compare la précision des sélecteurs, pas leur ordre ; `E501` bat `E`.

## 11. per-file-ignores : par dossier
- Sous-thème : config
- Niveau : 2
- Définition : `[tool.ruff.lint.per-file-ignores]` désactive des règles pour les fichiers qui correspondent à un glob : `"tests/*" = ["S101"]`, `"__init__.py" = ["F401"]`.
- Contexte : Les tests ont leurs usages (`assert`, imports de fixtures), les `__init__.py` réexportent. Un motif sans `/` s'applique au nom du fichier, partout dans l'arbre ; `tests/*` couvre aussi les sous-dossiers. Les chemins sont relatifs au fichier de config qui déclare la section. Pour un réexport, `__all__` ou `from .core import parse as parse` évitent même l'exception.
- Usage : ✅ règles qui ne valent pas pour les tests, les scripts ou les fichiers générés · ❌ ignorer `F401` partout : les vrais imports morts passent.

```toml
# Exemple 1 : tests et réexports
[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"tests/*" = ["F401"]
```

```bash
# Exemple 2 : avant la section
ruff check --output-format concise
# src/pkg/__init__.py:1:19: F401 …
# tests/test_a.py:1:8: F401 [*] …
```

- Quiz : Dans `src/pkg/__init__.py`, `from .core import parse` inutilisé : que fait `ruff check --fix` sans exception ?
- [ ] Retire l'import, comme ailleurs
- [x] Rien : F401 n'est pas corrigé ici
- [ ] Ajoute `parse` à `__all__`
- [ ] Ajoute `as parse`
- Réponse : rien : dans un `__init__.py`, ruff signale le F401 (sans `[*]`) mais ne retire pas un import qui peut être un réexport ; à toi de choisir `__all__` ou l'exception.

## 12. isort : les trois sections
- Sous-thème : règles
- Niveau : 2
- Définition : La règle `I001` trie les imports en sections séparées par une ligne vide : bibliothèque standard, tiers, first-party (le code du projet), puis imports relatifs.
- Contexte : Ruff classe sans regarder ce qui est installé : un module est first-party s'il est trouvé sous un dossier de `src` (`[".", "src"]` par défaut). Dans un monorepo, `bodacc_client` vit sous `packages/bodacc-client/src` : sans `src = ["packages/*/src", …]`, il est rangé avec `httpx`. `known-first-party` force un nom. `--fix` trie ; `ruff format` ne trie jamais.
- Usage : ✅ `src` avec les globs du workspace dans la config racine · ❌ trier à la main ou ajouter isort à côté : deux outils qui se contredisent.

```python
# Exemple 1 : sans src
import json
import os

import httpx
from bodacc_client import BodaccClient
```

```python
# Exemple 2 : src = ["packages/*/src", …]
import json
import os

import httpx

from bodacc_client import BodaccClient
```

- Quiz : Où `I001 --fix` place-t-il `from . import core` dans ce fichier ?
- [ ] En tête, avant la stdlib
- [ ] Avec `bodacc_client`, sans ligne vide
- [x] En dernier, dans sa propre section
- [ ] Avec `httpx`, en tiers
- Réponse : en dernier : les imports relatifs forment une section à part (local-folder), après le first-party.

## 13. extend-exclude ou exclude
- Sous-thème : config
- Niveau : 2
- Définition : `extend-exclude` ajoute des chemins aux exclusions par défaut (`.venv`, `.git`, `build`…) ; `exclude` les remplace entièrement.
- Contexte : Ruff ignore déjà une liste de dossiers et ce que liste `.gitignore`. data-platform écrit `extend-exclude = ["docs/**/*_gen.py", "learning/**"]` : les scripts de schémas et les cours restent hors lint. Avec `exclude`, la liste par défaut disparaît : un dossier `.venv` non ignoré par git est alors analysé. Les exclusions s'appliquent à la découverte (`ruff check .`), pas à un fichier passé explicitement.
- Usage : ✅ `extend-exclude` pour du code généré ou des supports · ❌ `exclude` sans recopier les défauts : lint de `.venv`, de `build/`.

```bash
# Exemple 1 : exclude remplace les défauts
# pyproject : exclude = ["docs"]
ruff check --output-format concise
# .venv/lib/x.py:1:8: F401 …
# app.py:1:8: F401 …
# avec extend-exclude : app.py seul
```

- Quiz : Avec `extend-exclude = ["docs"]`, que fait `ruff check docs/gen.py` (fichier nommé) ?
- [ ] Rien : le fichier est exclu
- [x] Il est analysé quand même
- [ ] Erreur : fichier exclu
- [ ] Avertit puis l'ignore
- Réponse : il est analysé : un chemin explicite passe outre les exclusions, sauf avec `--force-exclude`.

## 14. virgule magique : garder éclaté
- Sous-thème : format
- Niveau : 2
- Définition : Une virgule après le dernier élément (`["a", "b",]`) force `ruff format` à garder un élément par ligne (règle de black, sans équivalent prettier).
- Contexte : C'est le levier pour choisir la forme : avec virgule finale, la collection reste éclatée (diffs d'une ligne par ajout) ; sans, le formateur regroupe ce qui tient dans `line-length`. Le formateur ajoute lui-même la virgule finale quand il éclate. `skip-magic-trailing-comma = true` désactive ce comportement.
- Usage : ✅ listes de SIREN, de colonnes, de règles qui grandissent : virgule finale · ❌ retirer la virgule finale pour compacter à la main : le formateur décide.

```bash
# Exemple 1 : la virgule fait éclater
# sirens = ["483609327", "552100554",]
ruff format --diff f.py
# +sirens = [
# +    "483609327",
# +    "552100554",
# +]
```

- Quiz : Liste éclatée sur 4 lignes, mais **sans** virgule après le dernier élément : que fait `ruff format` ?
- [ ] La laisse éclatée
- [x] La regroupe sur une ligne
- [ ] Ajoute la virgule finale
- [ ] La signale sans la changer
- Réponse : la regroupe (`sirens = ["483609327", "552100554"]`) : sans virgule magique, seule la place compte, et elle tient dans la limite.

## 15. fmt: off : protéger un bloc
- Sous-thème : format
- Niveau : 2
- Définition : `# fmt: off` et `# fmt: on` encadrent un bloc que `ruff format` laisse intact ; `# fmt: skip` protège une instruction.
- Contexte : Pour une matrice alignée, un tableau de correspondances lisible en colonnes, du code généré. Les deux commentaires doivent être au même niveau d'indentation. Sans `# fmt: on`, la protection court jusqu'à la fin du bloc qui la contient. Le linter, lui, continue d'analyser le bloc : `fmt: off` n'est pas un `noqa`.
- Usage : ✅ alignement qui porte du sens (grille, table de codes tribunaux) · ❌ désactiver le formateur sur un fichier entier par confort : `extend-exclude` sous `[tool.ruff.format]`, ou mieux, rien.

```python
# Exemple 1 : grille alignée gardée
# fmt: off
grille = [1, 0,
          0, 1]
# fmt: on
z = [1, 2]
```

- Quiz : `# fmt: off` sans `# fmt: on`, dans le corps d'une fonction : le code après la fonction est-il formaté ?
- [ ] Non : jusqu'à la fin du fichier
- [x] Oui : off s'arrête avec la fonction
- [ ] Non, et ruff avertit
- [ ] Erreur : `fmt: on` manquant
- Réponse : oui : la protection vaut jusqu'à la fin du bloc qui la contient, ici le corps de la fonction ; au niveau du module, ce serait jusqu'à la fin du fichier.

## 16. ruff.toml : prioritaire sur pyproject
- Sous-thème : config
- Niveau : 2
- Définition : Dans un même dossier, ruff lit `.ruff.toml`, sinon `ruff.toml`, sinon `pyproject.toml` ; le premier trouvé s'applique seul, sans fusion.
- Contexte : Un `ruff.toml` ajouté pour une option fait perdre toute la section `[tool.ruff]` du `pyproject.toml` voisin : `line-length` revient à 88. Dans `ruff.toml`, les clés sont à la racine (`line-length = 120`, `[lint]`), sans préfixe `tool.ruff`. `ruff check --show-settings <fichier>` affiche le fichier retenu.
- Usage : ✅ `[tool.ruff]` dans `pyproject.toml` pour un projet Python · ❌ `ruff.toml` et `[tool.ruff]` côte à côte : la seconde est ignorée sans prévenir.

```bash
# Exemple 1 : le ruff.toml gagne
# pyproject.toml : line-length = 120
# ruff.toml      : target-version = "py312"
ruff check --show-settings a.py \
  | grep -E "^Settings path|line_length ="
# Settings path: "…/ruff.toml"
# linter.line_length = 88
```

- Quiz : On copie la section telle quelle dans `ruff.toml` : `[tool.ruff]` puis `line-length = 120`. Résultat ?
- [ ] Marche comme dans `pyproject.toml`
- [ ] Section ignorée, 88 par défaut
- [x] Erreur : `Failed to parse ruff.toml`
- [ ] Avertissement, puis 120
- Réponse : erreur de parsing : `ruff.toml` n'a pas de préfixe `tool.ruff`, ses clés sont à la racine ; ruff refuse alors de lancer l'analyse.

## 17. --force-exclude : pour pre-commit
- Sous-thème : commandes
- Niveau : 3
- Définition : `--force-exclude` applique `exclude` et `extend-exclude` même aux fichiers passés en argument, comme le fait pre-commit à chaque commit.
- Contexte : pre-commit appelle `ruff check a.py b.py` avec les fichiers stagés : sans `--force-exclude`, un fichier exclu dans la config est analysé dès qu'il est commité. Les hooks de `ruff-pre-commit` l'ont dans leur `entry` (`ruff check --force-exclude`) ; un hook `local` ou un script qui appelle ruff sur une liste de fichiers doit l'ajouter. `force-exclude = true` dans la config le rend permanent.
- Usage : ✅ hook local, script de CI qui passe `git diff --name-only` à ruff · ❌ compter sur `extend-exclude` seul dans un hook maison.

```bash
# Exemple 1 : le fichier exclu, nommé
# pyproject : exclude = ["docs"]
ruff check docs/gen.py \
  --output-format concise
# docs/gen.py:1:8: F401 …
ruff check --force-exclude docs/gen.py
# warning: No Python files found …
# All checks passed!
```

- Quiz : Hook `repo: local` avec `entry: ruff check` (sans `--force-exclude`), on commite `docs/gen.py`, exclu dans la config. Le hook ?
- [ ] Passe : le fichier est exclu
- [ ] Skipped : aucun fichier Python
- [x] Échoue sur les erreurs de `docs/gen.py`
- [ ] Échoue : option manquante
- Réponse : il échoue : pre-commit passe le chemin en argument, et un chemin explicite n'est exclu qu'avec `--force-exclude`.

## 18. RUF100 : le noqa inutile
- Sous-thème : noqa
- Niveau : 3
- Définition : La règle `RUF100` signale un `# noqa` qui ne tait plus rien ; `--fix` le retire ou retire les codes en trop.
- Contexte : Un `noqa` survit au code qu'il couvrait : l'import est utilisé depuis, la ligne a été raccourcie. Il masquera la prochaine vraie erreur de la ligne. RUF100 fait partie de `RUF`, absente de `select = ["E", "F", "I", "UP", "B"]` : à ajouter par `extend-select`. Elle ne vérifie que les règles actives : un code d'une règle désactivée n'est pas signalé comme inutile.
- Usage : ✅ `extend-select = ["RUF100"]` dans tout projet qui utilise des `noqa` · ❌ nettoyer les `noqa` à la main au fil des revues.

```bash
# Exemple 1 : codes en trop
# c.py : import os  # noqa: F401, E501
ruff check --extend-select RUF100 c.py \
  --output-format concise
# c.py:2:12: RUF100 [*] Unused `noqa`
#   directive (unused: `E501`)
ruff check --extend-select RUF100 --fix c.py
# → import os  # noqa: F401
```

- Quiz : `x = 1  # noqa` (sans code) sur une ligne sans aucune erreur : RUF100 le signale-t-elle ?
- [x] Oui : `Unused blanket noqa directive`
- [ ] Non : un noqa nu couvre tout
- [ ] Non : RUF100 ne vise que les codes
- [ ] Oui, mais sans correction
- Réponse : oui : un `noqa` nu inutile est aussi signalé (et corrigible avec `--fix`) ; c'est le plus dangereux, il tait tout.

## 19. --add-noqa : adopter une règle
- Sous-thème : noqa
- Niveau : 3
- Définition : `ruff check --add-noqa` ajoute un `# noqa: <code>` sur chaque ligne en erreur : la règle s'active tout de suite, la dette existante est marquée.
- Contexte : Activer `B` sur un code existant peut donner des centaines d'alertes : plutôt que reporter l'activation, on fige l'existant et on bloque le nouveau. Les `noqa` ajoutés sont précis (code nommé), cherchables (`grep -rn "noqa: B006"`) et à retirer au fil des corrections. RUF100 signalera ceux qui deviennent inutiles.
- Usage : ✅ activer une famille sur un dépôt existant, en un commit dédié · ❌ sur un projet neuf : corriger directement.

```bash
# Exemple 1 : figer l'existant
ruff check d.py --add-noqa
# Added 3 noqa directives.
cat d.py
# import os  # noqa: F401
# import sys  # noqa: F401
# def f(a=[]):  # noqa: B006
```

- Quiz : Juste après `--add-noqa`, que renvoie `ruff check d.py` ?
- [ ] Les 3 erreurs, marquées ignorées
- [x] `All checks passed!`, code 0
- [ ] 3 alertes RUF100
- [ ] Code 1 : fichier modifié
- Réponse : `All checks passed!` : chaque erreur est tue par son `noqa` ; les RUF100 n'apparaîtront qu'au fil des corrections, si la règle est active.

## 20. unfixable : signaler sans corriger
- Sous-thème : règles
- Niveau : 3
- Définition : `unfixable = ["F401"]` garde la règle active mais interdit à `--fix` de la corriger ; `fixable` restreint à l'inverse la liste des règles corrigeables.
- Contexte : Cas typique : l'éditeur lance `--fix` à chaque enregistrement et efface l'import qu'on vient d'écrire avant de l'utiliser. Avec `unfixable = ["F401"]`, l'import est signalé, plus supprimé ; le tri I001 continue d'être corrigé. Pour un réglage limité à l'éditeur, le mettre dans la config de l'extension, pas dans le projet, sinon `make fmt` ne nettoie plus les imports.
- Usage : ✅ règles dont la correction automatique gêne (F401 en cours de frappe, F841) · ❌ `unfixable = ["ALL"]` : autant ne pas lancer `--fix`.

```toml
# Exemple 1 : signaler, ne pas retirer
[tool.ruff.lint]
select = ["F", "I"]
unfixable = ["F401"]
```

```bash
# Exemple 2 : seul le tri est corrigé
# a.py : import sys / import os
ruff check --fix a.py
# Found 3 errors (1 fixed, 2 remaining).
```

- Quiz : Avec `unfixable = ["F401"]`, `ruff check --fix --unsafe-fixes` retire-t-il l'import inutile ?
- [ ] Oui : unsafe passe outre
- [x] Non : la règle n'est pas corrigeable
- [ ] Oui, avec un avertissement
- [ ] Non, mais il ajoute un noqa
- Réponse : non : `unfixable` retire la règle des corrections quel que soit le niveau, sûr ou unsafe ; elle reste signalée.

## 21. format : aussi les blocs du Markdown
- Sous-thème : format
- Niveau : 3
- Définition : En ruff 0.17, `ruff format` reformate aussi les blocs ```` ```python ```` des fichiers `.md` ; `ruff check`, lui, n'analyse pas le Markdown.
- Contexte : `ruff format .` et le hook `ruff-format` (`types_or: [python, pyi, jupyter, markdown]`) touchent donc la documentation : espaces normalisés, commentaires réalignés à deux espaces. C'est la raison de `"learning/**"` dans `extend-exclude` de data-platform : les cartes alignent leurs `# →` pour la lecture sur iPhone. Les blocs d'autres langages ne sont pas modifiés.
- Usage : ✅ exclure les supports dont la mise en forme est voulue (cours, cartes) · ❌ découvrir le changement dans un diff de 40 fichiers `.md` après `make fmt`.

```bash
# Exemple 1 : un bloc python d'un .md
ruff format --diff d.md
# -sirens[0]      # → "4836"
# -len(sirens)    # → 4
# +sirens[0]  # → "4836"
# +len(sirens)  # → 4
```

- Quiz : `ruff check cartes.md`, fichier qui contient un bloc python avec `import os` inutilisé : résultat ?
- [ ] F401 signalé dans le bloc
- [ ] Erreur : format non pris en charge
- [x] `No Python files found`, rien signalé
- [ ] Le bloc est corrigé
- Réponse : rien : le linter ignore les `.md` (`warning: No Python files found`) ; seul le formateur lit leurs blocs python.
