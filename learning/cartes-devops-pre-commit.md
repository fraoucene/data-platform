---
title: "Cartes · pre-commit"
type: cartes
langage: DevOps
cours: pre-commit
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · pre-commit
DevOps · pre-commit : ci, config, exécution, installation, versions (format spec v3 de revision-pwa).

## 1. hook qui corrige : Failed et commit annulé
- Sous-thème : exécution
- Niveau : 1
- Définition : Un hook qui modifie un fichier se déclare `Failed` et annule le commit : la correction est sur le disque, à relire puis re-stager.
- Contexte : C'est le contrat de pre-commit : rien ne part sans que tu aies vu la correction (`end-of-file-fixer`, `ruff-format`, `ruff-check --fix`). Le message dit `files were modified by this hook`. Le fichier apparaît `AM` : l'index a l'ancienne version, le disque la corrigée. `pre-commit run --files` ou `make fmt` avant le commit évite ce tour (≈ husky + lint-staged, sans `git add` automatique).
- Usage : ✅ `git add <fichier>` puis recommit après un `Failed` qui corrige ; `pre-commit run --files …` pour corriger avant · ❌ `git commit --no-verify` pour passer outre : le défaut part dans l'historique et en CI.

```bash
# Exemple 1 : le hook corrige, on réindexe
git commit -m "main: bodacc-client"
# fix end of files.........Failed
# - files were modified by this hook
git status --short
# AM tests/fixtures/records.json
git add tests/fixtures/records.json
git commit -m "main: bodacc-client"
# fix end of files.........Passed
```

- Quiz : Après ce `Failed`, on relance `git commit` sans `git add` : que se passe-t-il ?
- [ ] Commit de la version corrigée
- [ ] Commit de l'ancienne version
- [x] Nouveau `Failed`, aucun commit
- [ ] `Passed` : le fichier est déjà corrigé
- Réponse : nouveau `Failed` : les hooks lisent l'index, qui a toujours l'ancienne version ; pre-commit met de côté le disque non stagé le temps du contrôle.

## 2. pre-commit install : à refaire après un clone
- Sous-thème : installation
- Niveau : 1
- Définition : `pre-commit install` écrit le hook dans `.git/hooks/pre-commit` ; ce dossier n'est jamais versionné, donc chaque clone doit le refaire.
- Contexte : `.git/` reste local : un `git clone` récupère `.pre-commit-config.yaml`, pas le hook. Sans `install`, les commits passent sans aucun contrôle, en silence. D'où `uv run pre-commit install` dans les prérequis du README, juste après `uv sync` (≈ le script `prepare` de husky, qu'aucun gestionnaire de paquets ne lance ici).
- Usage : ✅ une fois par clone, documenté dans le README · ❌ le hook local comme seul garde-fou : refaire `ruff check` et `ruff format --check` en CI.

```bash
# Exemple 1 : un clone sans hook
git clone <repo> && cd data-platform
ls .git/hooks/pre-commit
# ❌ No such file or directory
uv run pre-commit install
# pre-commit installed at .git/hooks/pre-commit
```

- Quiz : On change un `rev` dans `.pre-commit-config.yaml` : faut-il relancer `pre-commit install` ?
- [ ] Oui, sinon l'ancien `rev` reste utilisé
- [x] Non : le YAML est relu à chaque lancement
- [ ] Oui, puis `pre-commit run --all-files`
- [ ] Non, mais `pre-commit clean` d'abord
- Réponse : non : le hook installé ne fait qu'appeler pre-commit, qui relit le YAML à chaque commit et prépare le nouvel environnement au besoin.

## 3. pre-commit run : l'index par défaut
- Sous-thème : exécution
- Niveau : 1
- Définition : `pre-commit run` sans option passe les hooks sur les fichiers stagés, exactement comme le ferait `git commit`, sans créer de commit.
- Contexte : C'est la répétition du commit : même liste de fichiers (l'index), même mise de côté des modifications non stagées (`Stashing unstaged files`), restaurées ensuite. Un fichier modifié mais non stagé n'est pas contrôlé. Pour tout le dépôt, `--all-files` ; pour une liste précise, `--files a.py b.py`.
- Usage : ✅ vérifier ce qui partira avant `git commit` · ❌ `pre-commit run` pour valider un fichier qu'on n'a pas encore stagé : `--files`.

```bash
# Exemple 1 : seul l'index compte
git add b.py
pre-commit run
# pas de print.............Failed
# b.py:1:print("y")
```

- Quiz : `b.py`, suivi par git, est modifié mais pas stagé ; rien d'autre n'est stagé. Que donne `pre-commit run` ?
- [ ] Failed : b.py est contrôlé
- [x] `(no files to check) Skipped`, code 0
- [ ] Erreur : rien à commiter
- [ ] Contrôle tous les fichiers suivis
- Réponse : `Skipped` : sans `--all-files` ni `--files`, seul l'index est lu, et il est vide ; la modification est mise de côté puis restaurée.

## 4. pre-commit run <id> : un seul hook
- Sous-thème : exécution
- Niveau : 1
- Définition : `pre-commit run ruff-check --all-files` ne lance que le hook dont l'`id` est donné, pour tester ou corriger une seule chose.
- Contexte : L'`id` est celui de la ligne `- id:` du YAML, pas le `name` affiché ni le nom de l'outil : `ruff-check`, pas `ruff`. Un `id` inconnu échoue avec `No hook with id … in stage pre-commit` ; un hook déclaré pour `pre-push` seulement n'est trouvé qu'avec `--hook-stage pre-push`. Sans `id`, tous les hooks tournent.
- Usage : ✅ relancer le hook qui vient d'échouer, mettre au point un nouveau hook · ❌ lancer l'outil directement (`ruff check .`) pour reproduire : autres arguments, autre version que celle du `rev`.

```bash
# Exemple 1 : par id, pas par outil
pre-commit run ruff --all-files
# No hook with id `ruff` in stage
#   `pre-commit`
pre-commit run ruff-check --all-files
# ruff check..................Passed
```

- Quiz : `pre-commit run ruff-check ruff-format --all-files` : que se passe-t-il ?
- [ ] Les deux hooks tournent, dans l'ordre
- [ ] Seul `ruff-check` tourne
- [ ] Les deux, en parallèle
- [x] Erreur : `unrecognized arguments`
- Réponse : erreur d'arguments : `run` n'accepte qu'un seul `id` ; pour deux hooks, deux commandes, ou `run` sans `id`.

## 5. SKIP : sauter un hook
- Sous-thème : exécution
- Niveau : 1
- Définition : `SKIP=ruff-check git commit …` saute les hooks dont l'`id` est listé, les autres tournent ; `--no-verify` saute tout.
- Contexte : La variable prend des `id` séparés par des virgules (espaces tolérés) et vaut aussi pour `pre-commit run`. Les hooks sautés s'affichent `Skipped`, le commit garde les autres contrôles : bien plus sûr que `--no-verify`, qui désactive aussi `end-of-file-fixer` ou `check-yaml`. La CI, elle, ne lit pas ton `SKIP` : le défaut y sera signalé.
- Usage : ✅ commit de travail urgent alors qu'un seul hook bloque (`SKIP=uv-lock`) · ❌ `--no-verify` par réflexe : tous les garde-fous tombent.

```bash
# Exemple 1 : un hook sauté, les autres non
SKIP=no-print git commit -m "main: wip"
# fix end of files.........Passed
# pas de print............Skipped
SKIP="check-json, no-print" pre-commit run
# check json..............Skipped
# pas de print............Skipped
```

- Quiz : Le hook affiche `pas de print` ; `SKIP="pas de print" git commit` le saute-t-il ?
- [ ] Oui : le nom suffit
- [ ] Oui, si on ajoute des guillemets simples
- [x] Non : SKIP attend l'`id`, `no-print`
- [ ] Non : SKIP ne vaut que pour `run`
- Réponse : non : `SKIP` compare aux `id` ; le `name` n'est qu'un libellé, le hook tourne et échoue.

## 6. args : remplacent ceux du hook
- Sous-thème : config
- Niveau : 1
- Définition : `args:` dans `.pre-commit-config.yaml` passe des options à l'outil du hook, avant la liste des fichiers : `args: [--fix]`, `args: [--maxkb=2000]`.
- Contexte : Le dépôt du hook déclare ses propres `args` par défaut dans son `.pre-commit-hooks.yaml` ; les tiens les **remplacent**, ils ne s'y ajoutent pas. La commande lancée est `entry` + `args` + fichiers. data-platform s'en sert pour `ruff-check` (`--fix`) et pour `check-added-large-files` (`--maxkb=2000`, aperçus PNG des schémas).
- Usage : ✅ options d'outil propres au dépôt (seuil, `--fix`) · ❌ y mettre la config de ruff (`--line-length`) : elle va dans `pyproject.toml`, lue aussi par `make lint` et l'éditeur.

```yaml
# Exemple 1 : options du hook
- id: ruff-check
  args: [--fix]
- id: check-added-large-files
  args: [--maxkb=2000]
```

```bash
# Exemple 2 : ce que reçoit l'outil
# hook : entry: echo, args: [--maxkb=500]
# config : args: [--maxkb=2000]
pre-commit run show-args --files m.py
# --maxkb=2000 m.py
```

- Quiz : Le hook déclare `args: [--maxkb=500]` dans son dépôt ; ta config met `args: [--enforce-all]`. Que reçoit l'outil ?
- [ ] `--maxkb=500 --enforce-all m.py`
- [ ] `--enforce-all --maxkb=500 m.py`
- [x] `--enforce-all m.py`
- [ ] Erreur : args en conflit
- Réponse : `--enforce-all m.py` : les `args` de la config remplacent ceux du dépôt ; pour garder `--maxkb=500`, le répéter.

## 7. --all-files : les fichiers suivis seulement
- Sous-thème : exécution
- Niveau : 2
- Définition : `pre-commit run --all-files` passe les hooks sur tous les fichiers suivis par git (`git ls-files`), pas sur ceux du disque.
- Contexte : Un fichier `??`, jamais ajouté, n'existe pas pour pre-commit : sur un scaffold neuf, les hooks affichent `(no files to check) Skipped` et le code retour vaut 0, un faux vert. Au `git commit`, seuls les fichiers stagés passent. Un `Skipped` attendu (aucun YAML dans le dépôt) est normal ; un `Skipped` sur `ruff-check` dans un dépôt Python est suspect.
- Usage : ✅ `git add` ciblé des nouveaux fichiers, puis `pre-commit run --all-files` · ❌ se fier au seul code retour : vérifier qu'aucun hook attendu n'est `Skipped`.

```bash
# Exemple 1 : scaffold pas encore ajouté
git status --short   # ?? a.toml
pre-commit run --all-files
# check toml...(no files to check)Skipped
echo $?   # → 0  (faux vert)
```

```bash
# Exemple 2 : après git add
git add a.toml .pre-commit-config.yaml
pre-commit run --all-files
# check toml.....................Passed
```

- Quiz : `new.toml` jamais ajouté (`??`) : `pre-commit run --files new.toml` le contrôle-t-il ?
- [ ] Non : `Skipped`, fichier non suivi
- [x] Oui : `--files` prend les chemins donnés
- [ ] Non : erreur, fichier inconnu de git
- [ ] Seulement avec `--all-files` en plus
- Réponse : oui : `--files` passe les chemins tels quels, suivis ou non ; seul `--all-files` part de `git ls-files`.

## 8. rev : un ruff à part
- Sous-thème : versions
- Niveau : 2
- Définition : Chaque dépôt de hooks est épinglé par `rev` (un tag git) et tourne dans son propre environnement, indépendant du `.venv` et de `uv.lock`.
- Contexte : Le ruff du hook est celui de `rev: v0.17.1`, installé dans `~/.cache/pre-commit` au premier lancement (lent une fois). Si `uv.lock` passe à un autre ruff sans toucher `rev`, deux ruff cohabitent : `make lint` et le hook peuvent rendre des verdicts différents. Même risque avec `uv-lock` : un uv de hook plus récent réécrit `uv.lock`. Tags : `git ls-remote --tags --refs <repo>`.
- Usage : ✅ `rev` = ruff de `uv.lock` (avec `v`), `uv --version` pour `uv-pre-commit` (sans `v`) · ❌ `rev: main` : jamais mis à jour après la première installation, pre-commit avertit.

```yaml
# Exemple 1 : aligné sur le lock
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.17.1  # = ruff de uv.lock
  hooks:
    - id: ruff-check
      args: [--fix]
    - id: ruff-format  # après le fix
- repo: https://github.com/astral-sh/uv-pre-commit
  rev: 0.9.28   # = uv --version, sans v
  hooks:
    - id: uv-lock
```

```bash
# Exemple 2 : vérifier l'alignement
uv tree --depth 1 | grep ruff
# └── ruff v0.17.1 (group: dev)
grep -A1 ruff-pre-commit \
  .pre-commit-config.yaml
#   rev: v0.17.1
```

- Quiz : `uv.lock` passe à ruff 0.18 et `rev` reste `v0.17.1` : quel ruff lance le hook ?
- [x] 0.17.1
- [ ] 0.18, celui du `.venv`
- [ ] Celui du `PATH`
- [ ] Aucun : le hook échoue
- Réponse : 0.17.1 : le hook a son propre environnement, construit depuis le tag `rev` ; seul `pre-commit autoupdate` ou une édition du `rev` le change.

## 9. autoupdate : monter les rev
- Sous-thème : versions
- Niveau : 2
- Définition : `pre-commit autoupdate` remplace chaque `rev` par le dernier tag du dépôt de hooks ; `--repo <url>` en limite la portée, `--freeze` écrit un SHA.
- Contexte : C'est l'équivalent d'un `pnpm update` pour les hooks : il réécrit le YAML, à relire et commiter. Il suit les tags publiés, rien d'autre : ni `uv.lock`, ni une politique de version. `--freeze` met le SHA du commit avec le tag en commentaire (`# frozen: v6.0.0`), à l'abri d'un tag déplacé. Le nouvel environnement s'installe au lancement suivant.
- Usage : ✅ montée de version planifiée, en commit dédié · ❌ `autoupdate` sans `--repo` dans data-platform : le ruff du hook dépasse celui de `uv.lock`.

```bash
# Exemple 1 : un seul dépôt
pre-commit autoupdate --repo \
  https://github.com/pre-commit/pre-commit-hooks
# updating v5.0.0 -> v6.0.0
pre-commit autoupdate --freeze
# rev: 3e8a8703…  # frozen: v6.0.0
```

- Quiz : Dans data-platform (`uv.lock` : ruff 0.17.1, dernier tag publié v0.17.2), quel `rev` ruff après `pre-commit autoupdate` ?
- [ ] `v0.17.1`, aligné sur le lock
- [x] `v0.17.2`
- [ ] Inchangé : `rev` déjà récent
- [ ] `main`
- Réponse : `v0.17.2` : autoupdate prend le dernier tag sans regarder `uv.lock` ; aligner ensuite `uv add --dev ruff==0.17.2`, ou garder `v0.17.1`.

## 10. files et exclude : des regex
- Sous-thème : config
- Niveau : 2
- Définition : `files:` et `exclude:` filtrent les fichiers d'un hook par **expression régulière** Python cherchée dans le chemin, pas par glob.
- Contexte : `exclude: tests/` correspond partout où la chaîne apparaît : `integration_tests/t.py` aussi. Ancrer avec `^` (`^tests/`), échapper le point (`\.py$`). Un `exclude:` au niveau racine du fichier vaut pour tous les hooks. Le filtre s'ajoute à `types` : il faut passer les deux. `pre-commit run <id> --all-files --verbose` montre les fichiers retenus.
- Usage : ✅ regex ancrées : `^docs/`, `^infra/.*\.tf$` · ❌ réflexe `.gitignore` ou eslint : `*.py`, `**/tests`.

```yaml
# Exemple 1 : ancrer la regex
- id: no-print
  types: [python]
  exclude: ^tests/
  # exclude: tests/ exclurait aussi
  #   integration_tests/t.py
```

- Quiz : On écrit `files: "*.py"` sur un hook : que fait `pre-commit run` ?
- [ ] Le hook vise les fichiers `.py`
- [ ] Le hook ne vise aucun fichier
- [ ] Le hook vise tous les fichiers
- [x] Erreur : `'*.py' is not a valid python regex`
- Réponse : erreur de config : `*` en tête n'a rien à répéter, ce n'est pas une regex ; la bonne écriture est `files: \.py$` (ou `types: [python]`).

## 11. types : filtrer par type de fichier
- Sous-thème : config
- Niveau : 2
- Définition : `types: [python]` limite un hook aux fichiers que la bibliothèque identify classe comme tels ; `types_or` accepte l'un ou l'autre.
- Contexte : identify reconnaît l'extension, et pour un fichier sans extension la ligne shebang (`#!/usr/bin/env python3`), à condition qu'il soit exécutable. Plusieurs valeurs dans `types` se combinent en ET : `types: [python, pyi]` ne vise rien, un fichier n'étant pas les deux. D'où `types_or: [python, pyi, jupyter]` dans les hooks ruff.
- Usage : ✅ `types` plutôt qu'une regex d'extension : couvre aussi les scripts sans extension · ❌ `types: [python, pyi]` pour « l'un ou l'autre » : `types_or`.

```bash
# Exemple 1 : shebang et ET
# deploy : #!/usr/bin/env python3, chmod +x
pre-commit run --all-files --verbose
# a (types: [python])...........Passed
#   deploy m.py
# b (types: [python, pyi])
#   (no files to check)Skipped
# c (types_or: [python, pyi])...Passed
#   deploy m.py stub.pyi
```

- Quiz : On retire le bit exécutable de `deploy` (`chmod -x`) : le hook `types: [python]` le contrôle-t-il encore ?
- [ ] Oui : le shebang suffit
- [x] Non : sans `+x`, plus de détection
- [ ] Oui : le contenu est analysé
- [ ] Non : le fichier est exclu par git
- Réponse : non : identify ne lit le shebang que des fichiers exécutables ; sans extension ni `+x`, `deploy` n'est plus du python.

## 12. repo: local : un hook maison
- Sous-thème : config
- Niveau : 2
- Définition : `repo: local` déclare un hook sans dépôt externe : `id`, `name`, `entry` (la commande), `language` (`system`, `unsupported`, `pygrep`, `python`…).
- Contexte : `language: unsupported` (ex-`system`, toujours accepté) lance la commande telle quelle, avec les outils du poste : `uv run pytest` passe par le `.venv` du projet. `pygrep` cherche une regex dans les fichiers : un hook `no-print` en trois lignes. `language: python` crée un environnement isolé, avec `additional_dependencies`. Les clés `id`, `name`, `entry` et `language` sont obligatoires.
- Usage : ✅ commande du projet (`uv run pytest`, `terraform fmt`) ou interdit simple (`pygrep`) · ❌ recopier en local un hook qui existe en dépôt : perte du `rev` et des mises à jour.

```yaml
# Exemple 1 : grep d'un motif interdit
- repo: local
  hooks:
    - id: no-print
      name: pas de print
      entry: "print\\("
      language: pygrep
      types: [python]
```

- Quiz : Un hook local avec `id`, `entry: "true"` et `language: system`, mais sans `name` : que fait `pre-commit` ?
- [ ] Affiche l'`id` comme nom
- [ ] Affiche la commande comme nom
- [x] Erreur : `Missing required key: name`
- [ ] Avertit puis lance le hook
- Réponse : erreur de config : en `repo: local`, rien ne vient d'un manifeste, `name` est obligatoire comme `id`, `entry` et `language`.

## 13. stages : au push plutôt qu'au commit
- Sous-thème : config
- Niveau : 2
- Définition : `stages: [pre-push]` réserve un hook au `git push` ; il faut aussi installer ce hook git : `pre-commit install --hook-type pre-push`.
- Contexte : Les tests lents (`uv run pytest`) au push, le formatage au commit. `pre-commit install` seul n'écrit que `.git/hooks/pre-commit` ; `default_install_hook_types: [pre-commit, pre-push]` en tête du YAML fait tout installer d'un coup. Un hook sans `stages` tourne à toutes les étapes installées : au commit **et** au push. `default_stages: [pre-commit]` change ce défaut.
- Usage : ✅ tests et contrôles longs en `pre-push` · ❌ `stages: [pre-push]` sans `install --hook-type pre-push` : le hook ne tourne jamais en local.

```yaml
# Exemple 1 : tests au push
default_install_hook_types: [pre-commit, pre-push]
repos:
  - repo: local
    hooks:
      - id: tests
        name: tests
        entry: uv run pytest
        language: unsupported
        pass_filenames: false
        stages: [pre-push]
```

- Quiz : On écrit `stage: [pre-push]` (sans s) : que se passe-t-il ?
- [ ] Erreur de config, rien ne tourne
- [x] Avertissement, le hook tourne à chaque commit
- [ ] Le hook ne tourne plus jamais
- [ ] Le hook tourne au push seulement
- Réponse : avertissement (`Unexpected key(s) present … : stage`) : la clé inconnue est ignorée, le hook n'a donc pas de `stages` et tourne partout.

## 14. pass_filenames et always_run
- Sous-thème : config
- Niveau : 2
- Définition : `pass_filenames: false` lance la commande sans la liste des fichiers ; `always_run: true` la lance même quand aucun fichier ne correspond au filtre.
- Contexte : Pour un contrôle global du dépôt (`uv run pytest`, `uv lock`, `terraform validate`), la liste des fichiers n'a pas de sens. Mais pre-commit filtre d'abord : sans fichier correspondant (commit vide, push d'un commit qui ne touche que la doc), le hook est `Skipped`, même sans `pass_filenames`. `always_run: true` lève ce filtre. Le hook `uv-lock` combine `pass_filenames: false` et `files: ^(uv\.lock|pyproject\.toml|uv\.toml)$`.
- Usage : ✅ `pass_filenames: false` pour toute commande globale, `always_run` si elle doit tourner à chaque fois · ❌ `always_run` sur un hook lent au commit : chaque commit le paie.

```yaml
# Exemple 1 : tests à chaque push
- id: tests
  name: tests
  entry: uv run pytest
  language: unsupported
  pass_filenames: false
  always_run: true
  stages: [pre-push]
```

- Quiz : Sans `always_run`, on pousse un commit vide (`--allow-empty`) : le hook `tests` en `pre-push` tourne-t-il ?
- [ ] Oui : `pass_filenames: false` suffit
- [ ] Oui : pre-push contrôle tout le dépôt
- [x] Non : `(no files to check) Skipped`
- [ ] Non : pre-push ignore les commits vides
- Réponse : non : aucun fichier changé, donc aucun fichier retenu, donc `Skipped` ; seul `always_run: true` force l'exécution.

## 15. fail_fast : s'arrêter au premier échec
- Sous-thème : config
- Niveau : 2
- Définition : `fail_fast: true` en tête du YAML arrête pre-commit au premier hook en échec ; par défaut, tous les hooks tournent et tous les échecs s'affichent.
- Contexte : Par défaut, un commit raté montre d'un coup tout ce qui ne va pas : plus efficace à corriger. `fail_fast` vaut quand un hook coûteux n'a pas de sens si un précédent échoue (tests après un lint cassé). Il existe aussi par hook (`fail_fast: true` sur un hook) ; l'ordre d'exécution est celui du fichier.
- Usage : ✅ hooks longs placés après des contrôles rapides qui les conditionnent · ❌ `fail_fast` global avec des hooks qui corrigent : une correction à la fois, un commit raté par défaut.

```yaml
# Exemple 1 : arrêt au premier échec
fail_fast: true
repos:
  - repo: local
    hooks:
      - id: un
        name: un
        entry: "false"
        language: unsupported
        pass_filenames: false
      - id: deux
        name: deux
        entry: echo
        language: unsupported
# un.....Failed  (deux n'apparaît pas)
```

- Quiz : Sans `fail_fast`, `end-of-file-fixer` échoue (fichier corrigé), puis `check-yaml` : `check-yaml` tourne-t-il ?
- [x] Oui : tous les hooks tournent
- [ ] Non : un hook a déjà échoué
- [ ] Non : le fichier a changé
- [ ] Oui, après restauration du fichier
- Réponse : oui : sans `fail_fast`, chaque hook tourne et affiche son verdict ; le commit est annulé à la fin s'il y a eu un échec.

## 16. config non stagée : bloquée
- Sous-thème : exécution
- Niveau : 2
- Définition : pre-commit refuse de tourner au commit si `.pre-commit-config.yaml` a des modifications non stagées : `Your pre-commit configuration is unstaged`.
- Contexte : Les hooks doivent correspondre à la configuration qui part avec le commit ; une config modifiée sur le disque seulement donnerait un contrôle différent de celui des collègues et de la CI. Le refus vaut au commit comme au push : il suffit de `git add .pre-commit-config.yaml`, ou de remettre le fichier. Un `pre-commit run` lancé à la main n'est pas concerné.
- Usage : ✅ commiter la config dans un commit à part, `pre-commit run --all-files` avant · ❌ éditer la config en pleine série de commits sans la stager : chaque commit échoue.

```bash
# Exemple 1 : config modifiée, push bloqué
git push origin HEAD
# [ERROR] Your pre-commit configuration
#   is unstaged.
# `git add .pre-commit-config.yaml`
#   to fix this.
# error: failed to push some refs
```

- Quiz : Même situation, mais avec `SKIP=tests git push` : le push passe-t-il ?
- [ ] Oui : le seul hook du push est sauté
- [x] Non : la config est vérifiée avant les hooks
- [ ] Oui : `SKIP` désactive la vérification
- [ ] Non, sauf avec `SKIP=all`
- Réponse : non : le contrôle de la config non stagée a lieu avant de lancer le moindre hook, `SKIP` n'y change rien ; seul `--no-verify` le contourne.

## 17. en CI : --show-diff-on-failure
- Sous-thème : ci
- Niveau : 2
- Définition : En CI, `pre-commit run --all-files --show-diff-on-failure` rejoue tous les hooks et affiche le diff qu'ils auraient appliqué.
- Contexte : Le filet pour ceux qui n'ont pas fait `pre-commit install`. Un hook qui corrige fait échouer le job même s'il a « réparé » le fichier dans le runner : la correction n'est pas commitée. Le diff affiché dit quoi corriger sans relancer en local. Le cache des environnements se garde avec `PRE_COMMIT_HOME` dans le projet et une clé sur `.pre-commit-config.yaml` (syntaxe GitLab, d'après la doc).
- Usage : ✅ un job `lint` de plus dans le pipeline, avec cache · ❌ `|| true` ou un second `pre-commit run` qui passe : le premier a déjà corrigé dans le runner, le défaut reste dans le dépôt.

```yaml
# Exemple 1 : job GitLab
pre-commit:
  variables:
    PRE_COMMIT_HOME: ${CI_PROJECT_DIR}/.cache/pre-commit
  cache:
    key:
      files: [.pre-commit-config.yaml]
    paths: [.cache/pre-commit]
  script:
    - uv run pre-commit run --all-files --show-diff-on-failure
```

```bash
# Exemple 2 : ce que montre le job
# pre-commit hook(s) made changes.
# All changes made by hooks:
# -a = 1␣␣␣
# +a = 1
```

- Quiz : En CI, `trailing-whitespace` corrige un fichier et tous les autres hooks passent : quel code retour pour le job ?
- [ ] 0 : le fichier est corrigé
- [x] 1 : un hook a modifié un fichier
- [ ] 0, avec un avertissement
- [ ] 1 seulement avec `--show-diff-on-failure`
- Réponse : 1 : un hook qui modifie un fichier est un échec, en CI comme en local ; un second `pre-commit run` dans le même runner passerait, à tort.

## 18. corrections annulées : stash en conflit
- Sous-thème : exécution
- Niveau : 3
- Définition : Un hook qui corrige un fichier ayant aussi des modifications non stagées voisines voit ses corrections annulées (`Rolling back fixes`).
- Contexte : pre-commit met de côté le non stagé, lance les hooks sur l'index, puis réapplique le patch mis de côté. Si ce patch ne s'applique plus sur le fichier corrigé, pre-commit privilégie ton travail : la correction est jetée, le commit échoue, le fichier reste `MM` avec son défaut. Cas typique : `git add -p` d'une partie d'un fichier, ou un éditeur qui modifie pendant le commit.
- Usage : ✅ stager tout le fichier, ou `git stash --keep-index` avant, puis recommit · ❌ relancer `git commit` en boucle : même conflit, même annulation.

```bash
# Exemple 1 : ligne 1 stagée, ligne 2 non
git add m.py   # a = 1␣␣␣
# puis sur le disque : b = 3
git commit -m "main: fix"
# trim trailing whitespace....Failed
# [WARNING] Stashed changes conflicted
#   with hook auto-fixes... Rolling back
git status --short   # MM m.py
```

- Quiz : Après ce `Rolling back fixes`, les espaces en fin de ligne 1 sont-ils retirés sur le disque ?
- [ ] Oui : la correction est gardée
- [ ] Oui, mais seulement dans l'index
- [x] Non : la correction a été annulée
- [ ] Non : le fichier a été remis à `HEAD`
- Réponse : non : pre-commit a jeté la correction pour réappliquer ton travail non stagé ; `a = 1` garde ses espaces, à corriger après avoir tout stagé.

## 19. try-repo : tester un dépôt de hooks
- Sous-thème : versions
- Niveau : 3
- Définition : `pre-commit try-repo <chemin|url> <id>` lance un hook d'un dépôt sans l'ajouter à `.pre-commit-config.yaml`, pour l'essayer ou le mettre au point.
- Contexte : Utile avant d'adopter un dépôt de hooks, ou pour développer le sien (son `.pre-commit-hooks.yaml`). Il affiche la config à copier, puis le résultat. Sur un dépôt local, il prend `HEAD` ; si le dépôt a des modifications non commitées, il les inclut via un dépôt temporaire (`shadow-repo`). Les options de `run` s'appliquent (`--files`, `--all-files`).
- Usage : ✅ développer un hook maison partagé entre dépôts, évaluer un dépôt tiers · ❌ s'en servir en CI à la place d'un `rev` épinglé.

```bash
# Exemple 1 : un hook en cours d'écriture
pre-commit try-repo ../hookrepo show-args \
  --files m.py
# Using config:
# repos:
# -   repo: ../hookrepo
#     rev: 0ab155a8…
#     hooks:
#     -   id: show-args
# show args...................Passed
```

- Quiz : On modifie `.pre-commit-hooks.yaml` de `../hookrepo` sans commiter, puis `try-repo` : quelle version du hook tourne ?
- [ ] Celle de `HEAD`, sans les modifications
- [x] La version modifiée, non commitée
- [ ] Erreur : dépôt sale
- [ ] Celle du dernier tag
- Réponse : la version modifiée : try-repo crée un dépôt temporaire avec les changements non commités (`Creating temporary repo with uncommitted changes`).

## 20. cache : PRE_COMMIT_HOME, gc et clean
- Sous-thème : installation
- Niveau : 3
- Définition : pre-commit clone et installe chaque dépôt de hooks dans `~/.cache/pre-commit` (ou `PRE_COMMIT_HOME`) ; `gc` retire les inutilisés, `clean` vide tout.
- Contexte : Un environnement par couple dépôt + `rev` + dépendances, réutilisé par tous tes projets : d'où un premier lancement lent (`Installing environment … This may take a few minutes`) puis instantané. Changer un `rev` en ajoute un sans retirer l'ancien : `pre-commit gc` nettoie ceux qu'aucune config connue n'utilise. `clean` force une réinstallation complète au prochain lancement (réseau requis).
- Usage : ✅ `gc` de temps en temps, `PRE_COMMIT_HOME` dans le projet en CI pour le cache · ❌ `clean` pour « réparer » un hook qui échoue sur ton code : le hook n'est pas en cause.

```bash
# Exemple 1 : premier lancement, puis nettoyage
pre-commit run --all-files
# [INFO] Installing environment for
#   https://github.com/pre-commit/pre-commit-hooks.
pre-commit gc
# 1 repo(s) removed.
```

- Quiz : Après `pre-commit clean`, sans réseau, on lance `git commit` : que se passe-t-il ?
- [ ] Les hooks tournent : ils sont dans `.git/hooks`
- [ ] Les hooks sont sautés en silence
- [x] Échec : le dépôt de hooks doit être recloné
- [ ] Le commit passe, avec un avertissement
- Réponse : échec : `.git/hooks/pre-commit` n'est qu'un lanceur ; les environnements vidés par `clean` doivent être reclonés depuis l'URL du `repo`.
