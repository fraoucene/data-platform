---
title: "Cartes · Make"
type: cartes
langage: DevOps
chapitre: Automatiser
cours: Make
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Make
DevOps · Make : règles, exécution, variables, fonctions, conditions (format spec v4 de revision-pwa).

## 1. règle : cible, prérequis, recette
- Id : make-regle-cible-recette
- Sous-thème : règles
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : make-recette-tabulation
- Mots-clés : package.json, CI
- Définition : Une règle `cible: prérequis` suivie de commandes indique à Make quoi lancer pour obtenir la cible (≈ un script de `package.json`).
- Contexte : `make test` cherche la règle `test`, construit d'abord ses prérequis, puis lance sa recette ligne par ligne. Sans argument, `make` prend la première cible du fichier, sauf si `.DEFAULT_GOAL` en désigne une autre. Make est né pour compiler du C à partir de fichiers ; dans nos dépôts, il sert surtout de lanceur de commandes documenté, le même en local et en CI.
- Usage : ✅ raccourcis partagés par l'équipe et la CI (`make check`, `make plan ENV=dev`) · ❌ logique complexe (boucles, JSON) : un script Python ou bash appelé par la recette.

```makefile
# Exemple 1 : une règle, une commande
# $ make test   → affiche puis lance :
# uv run pytest
test:
	uv run pytest
```

```makefile
# Exemple 2 : la cible par défaut
lint:
	@echo ruff
test:
	@echo pytest
# $ make        → ruff  (1re cible)
# $ make test   → pytest
```

- Quiz : Le fichier commence par `.PHONY: test lint`, puis définit `lint:` et `test:`. Que lance `make` seul ?
- [ ] `test`, cité en premier
- [x] `lint`
- [ ] `test` puis `lint`
- [ ] Rien : `.PHONY` n'a pas de recette
- Réponse : `lint` : les cibles spéciales comme `.PHONY` ne comptent pas, la cible par défaut est la première vraie règle du fichier.

## 2. recette : la tabulation
- Id : make-recette-tabulation
- Sous-thème : règles
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : make-regle-cible-recette
- Mots-clés : recette
- Définition : Chaque ligne de recette commence obligatoirement par une tabulation : c'est elle qui distingue une commande d'une nouvelle règle.
- Contexte : Make a gardé cette syntaxe de 1976 : des espaces, même nombreux, ne suffisent pas. Le piège vient des éditeurs qui convertissent les tabulations en espaces, d'où un `.editorconfig` avec `indent_style = tab` pour les Makefiles. Une ligne prolongée par `\` est une seule ligne logique : sa suite peut être indentée librement, espaces compris.
- Usage : ✅ vérifier avec `cat -et Makefile` (`^I` = tabulation) en cas d'erreur bizarre · ❌ copier une recette depuis une page web ou un chat : les tabulations y deviennent souvent des espaces.

```makefile
# Exemple 1 : une tabulation en tête
sync:
	uv sync --all-packages
# $ cat -et Makefile   (^I = tab)
# sync:$
# ^Iuv sync --all-packages$
```

```ini
# Exemple 2 : .editorconfig du dépôt
[Makefile]
indent_style = tab
```

- Quiz : Que fait `make sync` si la recette est indentée avec 4 espaces ?
- [ ] Lance la commande normalement
- [ ] Ignore la ligne, `sync` ne fait rien
- [x] `*** missing separator.  Stop.`
- [ ] Lance la commande dans un sous-shell
- Réponse : `missing separator` : sans tabulation, Make lit la ligne comme une nouvelle règle ou une variable, et n'y trouve ni `:` ni `=`.

## 3. prérequis : enchaîner les cibles
- Id : make-prerequis-enchainer
- Sous-thème : règles
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Prérequis : make-regle-cible-recette
- Mots-clés : cible Make, recette, backend, ruff
- Définition : Les prérequis d'une cible sont construits avant elle, de gauche à droite ; une cible sans recette sert d'alias.
- Contexte : `check: lint test` lance `lint`, puis `test`, puis la recette de `check` s'il y en a une. Un prérequis n'est construit qu'une fois par appel, même s'il apparaît dans plusieurs règles. Dans data-platform, `plan: tf-init` garantit un backend initialisé avant chaque `plan`. Avec `make -j`, les prérequis tournent en parallèle : l'ordre écrit n'est plus garanti.
- Usage : ✅ enchaîner des étapes (`plan: tf-init`, `check: lint test`) · ❌ compter sur l'ordre de gauche à droite avec `make -j` : déclarer la vraie dépendance.

```makefile
# Exemple 1 : un alias qui enchaîne
# $ make check  → ruff, puis pytest
check: lint test
lint:
	@echo ruff
test:
	@echo pytest
```

```makefile
# Exemple 2 : un prérequis partagé
plan: tf-init
	@echo plan
up: tf-init
	@echo apply
tf-init:
	@echo init
# $ make plan up
# init   (une seule fois)
# plan
# apply
```

- Quiz : Avec `check: lint test`, si `ruff` échoue dans `lint`, `pytest` est-il lancé ?
- [ ] Oui : les prérequis sont indépendants
- [ ] Oui, puis `check` échoue à la fin
- [x] Non : Make s'arrête à la première erreur
- Réponse : non : Make s'arrête dès qu'une commande renvoie un code non nul ; `make -k` continuerait les autres cibles (`pytest` tournerait).

## 4. .PHONY : une cible sans fichier
- Id : make-phony-cible-sans-fichier
- Sous-thème : règles
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Prérequis : make-regle-cible-recette
- Voir aussi : make-cible-fichier-plus-recente
- Mots-clés : cible Make, recette
- Définition : `.PHONY` déclare des cibles qui ne produisent aucun fichier, pour que Make lance leur recette à chaque appel.
- Contexte : Par défaut, une cible est un nom de fichier : s'il existe et qu'aucun prérequis n'est plus récent, Make juge la cible à jour et ne fait rien. Les cibles de commande (`test`, `plan`, `deploy`) doivent donc être déclarées `.PHONY`. Dans data-platform et revision-pwa, la première ligne du Makefile les liste toutes.
- Usage : ✅ toute cible qui lance une commande sans produire de fichier · ❌ cible qui produit vraiment un fichier (`dist/index.mjs`) : hors de `.PHONY`, pour profiter du « à jour ».

```makefile
# Exemple 1 : toujours relancée
.PHONY: test
test:
	@echo pytest
# $ touch test   (un fichier « test »)
# $ make test
# pytest
```

```makefile
# Exemple 2 : une seule ligne en tête
.PHONY: sync lint test check \
        tf-init plan up down
```

- Quiz : Sans `.PHONY`, un **dossier** `test/` existe à côté du Makefile : que fait `make test` ?
- [x] Rien : ``make: `test' is up to date.``
- [ ] Lance `pytest` : un dossier n'est pas un fichier
- [ ] ``*** No rule to make target `test'``
- [ ] Lance `pytest` dans le dossier `test/`
- Réponse : rien, « up to date » : un dossier compte comme un fichier existant, et la règle n'a aucun prérequis plus récent.

## 5. @ : taire la commande
- Id : make-arobase-taire-commande
- Sous-thème : exécution
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : recette, CI
- Définition : Make affiche chaque commande avant de l'exécuter ; préfixée par `@`, elle s'exécute sans être affichée.
- Contexte : L'écho des commandes sert de journal : en CI, on voit exactement ce qui a tourné, variables développées. On réserve `@` aux lignes dont l'écho ferait doublon (`@echo …`). `make -s` (silencieux) supprime l'écho de toutes les lignes sans toucher au Makefile. `@` ne change rien à la sortie de la commande elle-même.
- Usage : ✅ `@echo` pour un message, cible d'aide (`make help`) · ❌ `@` devant `terraform apply` ou `aws s3 sync` : on perd la trace de la commande lancée.

```makefile
# Exemple 1 : seulement la sortie
hello:
	@echo plan dev
# $ make hello
# plan dev
```

```makefile
# Exemple 2 : tout taire avec -s
init:
	echo init
# $ make init      → echo init
#                    init
# $ make -s init   → init
```

- Quiz : Que montre `make -n hello` si la recette est `@echo plan dev` ?
- [ ] Rien : `@` masque la ligne
- [ ] `plan dev`
- [x] `echo plan dev`
- [ ] `@echo plan dev`
- Réponse : `echo plan dev` : `-n` affiche toutes les commandes sans les lancer, `@` compris ; `@` ne masque que l'écho d'une vraie exécution.

## 6. ?= : la valeur par défaut
- Id : make-valeur-par-defaut
- Sous-thème : variables
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : make-or-defaut-si-vide, make-evaluation-tardive-ou-immediate
- Mots-clés : variable d'environnement, cible Make
- Définition : `?=` n'affecte la variable que si elle n'est pas déjà définie (ligne de commande ou environnement) : c'est une valeur par défaut.
- Contexte : `ENV ?= dev` permet `make plan` (dev) comme `make plan ENV=prod`. Une variable passée en ligne de commande gagne toujours sur le Makefile. `?=` teste seulement si la variable existe : définie vide (`make plan ENV=`), elle reste vide. Les Makefiles réels l'utilisent pour tout ce qu'on surcharge : `ENV`, `PROFILE`, `REVISION_PWA`.
- Usage : ✅ paramètres surchargeables (`ENV`, `PROFILE`, chemins de dépôts voisins) · ❌ variable interne calculée (`TF`, `ENV_DIR`) : `=` ou `:=`, pour ne pas la reprendre par accident de l'environnement.

```makefile
# Exemple 1 : dev par défaut
ENV ?= dev
plan:
	@echo plan $(ENV)
# $ make plan           → plan dev
# $ make plan ENV=prod  → plan prod
```

```makefile
# Exemple 2 : l'environnement du shell
ENV ?= dev
plan:
	@echo plan $(ENV)
# $ ENV=prod make plan  → plan prod
```

- Quiz : Avec `ENV = dev` (sans `?`), qu'affiche `ENV=prod make plan` (variable du shell) ?
- [ ] `plan prod`
- [x] `plan dev`
- [ ] `plan` seul
- [ ] Une erreur de conflit
- Réponse : `plan dev` : `=` écrase l'environnement du shell ; seuls `make plan ENV=prod` (ligne de commande) ou `make -e` passent devant.

## 7. variable : absente = vide
- Id : make-variable-absente-vide
- Sous-thème : variables
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : make-error-garde, make-garde-dans-recette
- Mots-clés : variable d'environnement, recette
- Définition : `$(NOM)` d'une variable jamais définie vaut une chaîne vide, sans erreur ni avertissement (pas de `undefined` qui plante).
- Contexte : Make ne distingue pas « absente » et « vide ». Une faute de frappe (`$(EVN)`) donne en silence un chemin tronqué, et l'erreur n'apparaît que dans la commande lancée, loin de sa cause. `make --warn-undefined-variables` signale ces lectures. D'où le `ENV ?= dev`, ou un garde `$(error)` sur les variables obligatoires.
- Usage : ✅ option facultative avec `$(if $(PROFILE),--profile $(PROFILE))` · ❌ variable dont dépend un chemin ou un compte : valeur par défaut ou `$(error)`.

```makefile
# Exemple 1 : rien ne signale l'oubli
ENV_DIR = envs/$(ENV)
init:
	@echo [$(ENV_DIR)]
# $ make init ENV=dev  → [envs/dev]
# $ make init          → [envs/]
```

```makefile
# Exemple 2 : faire signaler l'oubli
ENV_DIR = envs/$(ENV)
init:
	@echo [$(ENV_DIR)]
# $ make --warn-undefined-variables init
# Makefile:3: warning: undefined
#   variable `ENV'
# [envs/]
```

- Quiz : Le Makefile ne définit pas `ENV`, mais le shell a fait `export ENV=prod`. Qu'affiche `make init` ?
- [ ] `[envs/]`
- [x] `[envs/prod]`
- [ ] `[envs/$ENV]`
- [ ] Une erreur : `ENV` non définie
- Réponse : `[envs/prod]` : toute variable d'environnement du shell devient une variable Make ; un `ENV` oublié dans un vieux terminal change la cible en silence.

## 8. make -n : simuler
- Id : make-n-simuler
- Sous-thème : exécution
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Prérequis : make-regle-cible-recette
- Voir aussi : make-n-substitution-non-lancee
- Mots-clés : recette, cible Make
- Définition : `make -n` affiche les commandes qu'il lancerait, sans les exécuter (dry-run), pour relire une recette avant de la lancer.
- Contexte : Les variables sont développées : on voit la commande finale, chemins et options compris. Les recettes des prérequis sont listées aussi, dans l'ordre. Exception : une ligne qui contient `$(MAKE)` est exécutée, car c'est un sous-make qui hérite de `-n` et n'affiche à son tour que ses commandes.
- Usage : ✅ relire `make up ENV=prod` ou `make deploy` avant de les lancer, déboguer une variable · ❌ vérifier qu'une commande réussira : `-n` ne lance rien, il ne voit aucune erreur.

```makefile
# Exemple 1 : voir sans lancer
# $ make -n up ENV=prod   affiche :
# terraform apply -var-file=prod.tfvars
# (et ne lance rien)
ENV ?= dev
up:
	terraform apply -var-file=$(ENV).tfvars
```

```makefile
# Exemple 2 : prérequis compris
plan: tf-init
	terraform plan
tf-init:
	terraform init
# $ make -n plan
# terraform init
# terraform plan
```

- Quiz : `make -n` sur une recette qui utilise `B ?= $(shell terraform output -raw b)` : `terraform output` tourne-t-il ?
- [ ] Non : `-n` n'exécute rien
- [ ] Seulement si `B` est vide
- [ ] Non : `$(B)` reste affiché tel quel
- [x] Oui, pour développer la commande
- Réponse : oui : `$(shell …)` est une fonction de Make, évaluée pour afficher la commande finale, même en `-n` ; seules les lignes de recette ne sont pas lancées.

## 9. cible fichier : refaire si plus récent
- Id : make-cible-fichier-plus-recente
- Sous-thème : règles
- Type : concept
- Niveau : 2
- Profils : ops, data
- Prérequis : make-prerequis-enchainer, make-phony-cible-sans-fichier
- Mots-clés : cible Make, recette
- Définition : Quand cible et prérequis sont des fichiers, Make ne relance la recette que si la cible manque ou qu'un prérequis est plus récent.
- Contexte : Make compare les dates de modification : c'est sa raison d'être, éviter un build coûteux déjà fait (`dist/index.mjs` depuis `handler.ts`). La recette doit vraiment écrire la cible, sinon elle repart à chaque appel. Avec le make 3.81 de macOS, deux fichiers modifiés dans la même seconde sont vus comme aussi récents : pas de reconstruction.
- Usage : ✅ artefacts lents à produire (bundle, zip de Lambda, export de données) · ❌ cible de commande (`test`, `plan`) : `.PHONY`.

```makefile
# Exemple 1 : seulement si besoin
out.json: in.csv
	@echo conversion
	@touch out.json
# $ make   → conversion
# $ make   → make: `out.json' is up to date.
```

```makefile
# Exemple 2 : un prérequis modifié
out.json: in.csv
	@echo conversion
	@touch out.json
# $ touch in.csv   (plus récent)
# $ make   → conversion
```

- Quiz : Que fait `make` avec cette règle si `in.csv` n'existe pas ?
- [ ] Lance la recette quand même
- [ ] ``make: `out.json' is up to date.``
- [x] ``*** No rule to make target `in.csv'``
- [ ] Crée un `in.csv` vide, puis convertit
- Réponse : ``No rule to make target `in.csv'`` : un prérequis doit exister ou avoir sa propre règle, sinon Make s'arrête avant la recette.

## 10. = ou := : quand c'est évalué
- Id : make-evaluation-tardive-ou-immediate
- Sous-thème : variables
- Type : comparaison
- Niveau : 2
- Profils : ops
- Prérequis : make-valeur-par-defaut
- Voir aussi : make-shell-capter-sortie
- Mots-clés : recette
- Définition : `=` est développée à chaque usage (tardive, récursive), `:=` une seule fois, à la lecture de la ligne.
- Contexte : Avec `=`, Make garde le texte `$(B)` et le remplace au moment de l'usage : l'ordre des lignes compte peu, mais la valeur peut changer en cours de route. `:=` fige le résultat comme une affectation JS classique. Pour ajouter à une variable, `+=` garde le type d'origine (`=` ou `:=`). Les Makefiles réels utilisent surtout `=` pour les compositions (`ENV_DIR = envs/$(ENV)`).
- Usage : ✅ `=` pour composer des valeurs surchargeables, `:=` pour un calcul fait une fois (`$(shell …)`) · ❌ `:=` qui référence une variable définie plus bas : vide.

```makefile
# Exemple 1 : = lit la valeur à l'usage
A = $(B)
B = prod
show:
	@echo $(A)
# $ make show
# prod
```

```makefile
# Exemple 2 : := fige la valeur
X := v1
Y := $(X)
X := v2
Z = $(X)
show:
	@echo $(Y) $(Z)
# → v1 v2
```

- Quiz : Que fait la ligne `FLAGS = $(FLAGS) -input=false` (après `FLAGS = -x`) ?
- [ ] Ajoute `-input=false` à `FLAGS`
- [ ] `FLAGS` vaut ` -input=false`
- [x] Erreur : variable récursive
- [ ] Une boucle infinie au `make`
- Réponse : erreur ``Recursive variable `FLAGS' references itself`` : avec `=`, `FLAGS` se développe en elle-même ; écrire `FLAGS += -input=false`.

## 11. $$ : la variable du shell
- Id : make-double-dollar-shell
- Sous-thème : variables
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : make-regle-cible-recette
- Voir aussi : jq-makefile-dollar-double
- Mots-clés : recette, shell, substitution de commande, variable d'environnement
- Définition : Dans une recette, `$(X)` est une variable Make ; pour une variable ou une substitution du shell, on double le dollar : `$$HOME`, `$$(cmd)`.
- Contexte : Make développe la recette avant de la passer à `/bin/sh` : chaque `$` est à lui. `$$` devient un `$` littéral pour le shell. revision-pwa s'en sert pour lire un nom de Lambda au moment de l'exécution : `$$($(TF) output -raw catalog_function)`. Les variables automatiques (`$@`) et Make (`$(TF)`) restent simples.
- Usage : ✅ variables d'environnement (`$$HOME`, `$$AWS_PROFILE`), substitution `$$(…)` et boucles shell (`$$f`) · ❌ `$(shell …)` quand la valeur ne sert que dans une ligne : `$$(…)` suffit.

```makefile
# Exemple 1 : la variable du shell
where:
	@echo $$HOME
# $ make where
# /Users/fraouceneguezout
```

```makefile
# Exemple 2 : substitution du shell
fn:
	@echo $$(echo catalog-build)
# $ make fn
# catalog-build
```

- Quiz : Qu'affiche `@echo $HOME` avec un seul `$` ?
- [ ] `/Users/fraouceneguezout`
- [ ] `$HOME`
- [x] `OME`
- [ ] Une ligne vide
- Réponse : `OME` : Make lit `$H` comme sa variable `H` (vide) et laisse `OME` ; un `$` seul vise toujours Make.

## 12. export : passer au shell
- Id : make-export-environnement
- Sous-thème : variables
- Type : concept
- Niveau : 2
- Profils : ops
- Voir aussi : shell-export-environnement
- Mots-clés : variable d'environnement, recette
- Définition : `export VAR = valeur` transmet une variable Make à l'environnement des commandes de la recette.
- Contexte : Une variable du Makefile n'existe que pour Make : `$(VAR)` est remplacé dans le texte de la recette, mais le programme lancé ne la voit pas dans son environnement. `export` la rend visible à `aws`, `terraform` ou un script Python. Une variable passée en ligne de commande (`make who AWS_PROFILE=x`) est exportée d'office. revision-pwa exporte ainsi `CARDS_DIR` pour ses scripts.
- Usage : ✅ configurer un outil par variable d'environnement (`AWS_PROFILE`, `TF_VAR_x`, `CARDS_DIR`) · ❌ tout exporter par défaut : passer l'option explicitement (`--profile`) reste plus lisible.

```makefile
# Exemple 1 : visible par le shell
export AWS_PROFILE = dp-dev
who:
	@echo "[$$AWS_PROFILE]"
# $ make who
# [dp-dev]
```

```makefile
# Exemple 2 : vu par un script
export CARDS_DIR := learning
check:
	@python3 -c 'import os; \
	  print(os.environ["CARDS_DIR"])'
# → learning
```

- Quiz : Sans `export` (et sans `AWS_PROFILE` dans le shell), qu'affiche `make who` ?
- [x] `[]`
- [ ] `[dp-dev]`
- [ ] `[$AWS_PROFILE]`
- [ ] Une erreur : variable non exportée
- Réponse : `[]` : `$$AWS_PROFILE` est lu par le shell, qui ne connaît pas la variable Make ; `aws` prendrait alors le profil par défaut.

## 13. $@, $< et $^ : variables automatiques
- Id : make-variables-automatiques
- Sous-thème : variables
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : make-cible-fichier-plus-recente
- Mots-clés : recette, cible Make
- Définition : Dans une recette, `$@` désigne la cible, `$<` le premier prérequis et `$^` tous les prérequis.
- Contexte : Elles évitent de répéter des noms de fichiers dans la recette et rendent les règles réutilisables, notamment les règles génériques (`%.json: %.csv`) où le nom n'est connu qu'à l'exécution. Elles n'existent que dans la recette : dans une ligne de prérequis ou une variable globale, elles valent vide.
- Usage : ✅ règle fichier qui produit sa cible (`$@`) à partir de ses sources (`$<`, `$^`) · ❌ cibles `.PHONY` de commande : écrire le nom en clair, plus lisible.

```makefile
# Exemple 1 : la cible et sa source
out.json: a.csv b.csv
	@echo $@ depuis $<
# $ make
# out.json depuis a.csv
```

```makefile
# Exemple 2 : une règle générique
%.json: %.csv
	@echo convert $< vers $@
# $ make annonces.json
# convert annonces.csv vers annonces.json
```

- Quiz : Avec `out.json: a.csv b.csv a.csv`, qu'affiche `@echo $^` ?
- [ ] `a.csv b.csv a.csv`
- [ ] `a.csv`
- [ ] `b.csv a.csv`
- [x] `a.csv b.csv`
- Réponse : `a.csv b.csv` : `$^` retire les doublons ; `$+` les garde, dans l'ordre écrit.

## 14. recette : une ligne, un shell
- Id : make-une-ligne-un-shell
- Sous-thème : exécution
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : make-recette-tabulation
- Voir aussi : make-abspath-chemin-absolu
- Mots-clés : recette, shell
- Définition : Chaque ligne de recette tourne dans un shell `/bin/sh` neuf : un `cd` ou une variable du shell ne survit pas à la ligne.
- Contexte : Make lance un shell par ligne, l'une après l'autre, et s'arrête à la première en erreur. Pour enchaîner, on reste sur une seule ligne logique (`&&`, `;`, ou `\` en fin de ligne). `.ONESHELL:` lance toute la recette dans un seul shell, mais seulement depuis GNU make 3.82 : le make 3.81 de macOS l'ignore en silence. Terraform évite le problème avec `-chdir=infra`.
- Usage : ✅ `cd dir && cmd` sur une ligne, ou une option de dossier (`-chdir`, `-C`, `--dir`) · ❌ `.ONESHELL` dans un dépôt utilisé sur macOS : ignoré par make 3.81.

```makefile
# Exemple 1 : cd et commande liés
init:
	@cd infra && pwd
# $ make init
# /…/data-platform/infra
```

```makefile
# Exemple 2 : une ligne logique (\ final)
init:
	@cd infra && \
	  echo "dans $$(basename $$PWD)"
# $ make init
# dans infra
```

- Quiz : Avec `cd infra` puis `pwd` sur deux lignes de recette, où `pwd` tourne-t-il ?
- [ ] Dans `infra/`
- [ ] Dans `$HOME`
- [x] À la racine du dépôt
- [ ] Nulle part : `cd` seul échoue
- Réponse : à la racine : le `cd` meurt avec le shell de la première ligne ; d'où `&&` ou `terraform -chdir=infra`.

## 15. - : ignorer une erreur
- Id : make-tiret-ignorer-erreur
- Sous-thème : exécution
- Type : concept
- Niveau : 2
- Profils : ops
- Mots-clés : code de sortie, recette, CI
- Définition : Une commande préfixée par `-` peut échouer sans arrêter la recette : Make signale l'erreur, puis continue.
- Contexte : Par défaut, un code de sortie non nul arrête tout. Le `-` sert aux commandes dont l'échec est attendu et sans gravité (supprimer un fichier peut-être absent, arrêter un conteneur qui ne tourne pas). Il se combine avec `@` (`-@cmd`). `make -i` ignore toutes les erreurs du Makefile : à éviter.
- Usage : ✅ nettoyage tolérant (`-docker stop dev`) · ❌ devant une commande qui doit réussir (`terraform apply`, tests) : l'échec passerait inaperçu en CI.

```makefile
# Exemple 1 : continuer malgré l'échec
clean:
	-rm tfplan
	@echo nettoye
# $ make clean   (sans tfplan)
# rm: tfplan: No such file or directory
# make: [clean] Error 1 (ignored)
# nettoye
```

- Quiz : `-rm tfplan` ou `rm -f tfplan` pour un `clean` silencieux ?
- [ ] `-rm tfplan` : l'erreur est masquée
- [x] `rm -f tfplan`
- [ ] Les deux, sortie identique
- Réponse : `rm -f tfplan` : `-f` ne produit aucune erreur ; `-` laisse passer l'échec mais affiche quand même le message et `(ignored)`.

## 16. make -C et $(MAKE) : un autre Makefile
- Id : make-sous-make-c
- Sous-thème : exécution
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : make-regle-cible-recette
- Voir aussi : Terraform/cli-chdir-option-globale
- Mots-clés : Makefile, recette, dry-run
- Définition : `make -C dossier cible` lit le Makefile de ce dossier et y lance la cible ; dans une recette, on l'écrit `$(MAKE) -C`.
- Contexte : `-C` équivaut à `cd dossier && make`, chemins relatifs compris. Dans une recette, `$(MAKE)` réutilise le même binaire et marque la ligne comme sous-make : elle tourne même sous `make -n`, qui se propage. data-platform appelle ainsi le validateur de cartes de revision-pwa, en lui passant son propre chemin avec `$(CURDIR)`.
- Usage : ✅ déléguer à un dépôt voisin ou un sous-projet (`$(MAKE) -C app build`) · ❌ `make` en dur dans une recette : `-n` ne s'appliquerait pas au sous-make.

```makefile
# Exemple 1 : déléguer à un autre dépôt
REV ?= ../revision-pwa
cards-validate:
	$(MAKE) -C $(REV) cards-validate \
	  PRODUCER=$(CURDIR)
# $ make cards-validate
# → lance la cible dans ../revision-pwa
```

- Quiz : `make deploy ENV=prod` lance `$(MAKE) -C app build`, et `app/Makefile` contient `ENV ?= dev`. Que vaut `ENV` dans `app` ?
- [x] `prod`
- [ ] `dev`
- [ ] vide
- Réponse : `prod` : les variables de la ligne de commande passent aux sous-makes (via `MAKEFLAGS`) et y gagnent sur `?=` comme sur `=`.

## 17. $(abspath) : un chemin qui survit au cd
- Id : make-abspath-chemin-absolu
- Sous-thème : fonctions
- Type : recette
- Niveau : 2
- Profils : ops
- Mots-clés : variable d'environnement, pnpm
- Source : revision-pwa · pwa-revision
- Définition : `$(abspath chemin)` rend un chemin absolu, calculé depuis le dossier où `make` est lancé, sans vérifier qu'il existe.
- Contexte : Un chemin relatif se lit depuis le dossier courant de la commande qui le reçoit. `pnpm --dir app` tourne dans `app/` : un `CARDS_DIR=../data-platform/learning` y viserait `revision-pwa/data-platform/learning`. D'où `export CARDS_DIR := $(abspath $(PRODUCER))/learning` : la valeur reste juste dans `app/`, dans `tsx`, dans Vite.
- Usage : ✅ chemin passé à un sous-processus qui change de dossier (`--dir`, `cd`, `-C`) · ❌ chemin relatif dans une variable exportée : juste par hasard, tant que tout tourne au même endroit.

```makefile
# Exemple 1 : relatif ou absolu
PRODUCER ?= .
REL := $(PRODUCER)/learning
ABS := $(abspath $(PRODUCER))/learning
show:
	@cd app && ls $(REL) 2>/dev/null \
	  && echo OK || echo KO
	@cd app && ls $(ABS) 2>/dev/null \
	  && echo OK || echo KO
# make show → KO puis OK
# REL = ./learning, lu depuis app/
```

- Quiz : Que rend `$(realpath ../absent)` quand ce dossier n'existe pas ?
- [ ] Le chemin absolu, comme `abspath`
- [ ] `../absent`, inchangé
- [x] Une chaîne vide
- [ ] Une erreur de make
- Réponse : une chaîne vide (mesuré) : `realpath` résout les liens et exige un chemin existant, `abspath` calcule sans vérifier ; une faute dans `PRODUCER` passe donc inaperçue avec `abspath`.

## 18. $(shell) : capter une commande
- Id : make-shell-capter-sortie
- Sous-thème : fonctions
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : make-evaluation-tardive-ou-immediate
- Voir aussi : shell-substitution-commande
- Mots-clés : substitution de commande, output, cible Make
- Définition : `$(shell cmd)` exécute une commande quand Make le développe et renvoie sa sortie, retours à la ligne remplacés par des espaces.
- Contexte : Avec `:=`, la commande tourne une fois, à la lecture du fichier. Avec `=` ou `?=`, elle tourne à chaque usage de la variable, et seulement si la variable sert : c'est voulu pour `CARDS_BUCKET ?= $(shell terraform … output -raw …)`, qui n'interroge Terraform que pour `cards-publish`. `$$(cmd)` fait le même travail côté shell, dans une seule ligne.
- Usage : ✅ lire une sortie Terraform ou la branche git pour plusieurs recettes · ❌ commande lente avec `=` utilisée partout : `:=`, ou `$$(…)` dans la seule recette concernée.

```makefile
# Exemple 1 : la branche courante
BR := $(shell git branch --show-current)
tag:
	@echo $(BR)
# $ make tag
# main
```

```makefile
# Exemple 2 : = relance la commande
N = $(shell echo x >> n.log; echo main)
t:
	@echo $(N) $(N) $(N)
# $ make t; wc -l < n.log
# main main main
# 3      (1 avec :=)
```

- Quiz : Que vaut `X` avec `X := $(shell false)` (commande en échec) ?
- [ ] Make s'arrête : `Error 1`
- [ ] `false`
- [x] Vide, et Make continue
- [ ] `1`, le code de sortie
- Réponse : vide, sans erreur : `$(shell)` ignore le code de sortie ; vérifier la valeur avec une garde `$(if $(X),,$(error …))`.

## 19. $(or) : un défaut à l'usage
- Id : make-or-defaut-si-vide
- Sous-thème : fonctions
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : make-variable-absente-vide
- Voir aussi : make-valeur-par-defaut
- Mots-clés : cible Make, Lambda
- Source : data-platform · S1-08
- Définition : `$(or $(A),défaut)` renvoie le premier argument non vide : une valeur par défaut qui s'applique aussi quand `A` est passée vide.
- Contexte : `A ?= défaut` ne joue que si `A` n'existe pas : `make replay LAMBDA=` la laisse vide. `$(or …)` teste la valeur, pas l'existence : vide ou absente, le défaut gagne. On l'écrit dans une seconde variable (`REPLAY_LAMBDA = $(or $(LAMBDA),ingest-bodacc)`) quand `LAMBDA` sert déjà ailleurs avec un autre sens (vide = toutes les Lambdas pour `lambdas-publish`).
- Usage : ✅ défaut d'une option partagée entre cibles, robuste à `VAR=` · ❌ défaut simple d'une variable propre à la cible : `?=`.

```makefile
# Exemple 1 : absente, autre, vide
L = $(or $(LAMBDA),ingest-bodacc)
show:
	@echo "[$(L)]"
# make show             → [ingest-bodacc]
# make show LAMBDA=autre → [autre]
# make show LAMBDA=     → [ingest-bodacc]
```

- Quiz : Avec `L ?= ingest-bodacc` et la recette `@echo "[$(L)]"`, qu'affiche `make show L=` ?
- [ ] `[ingest-bodacc]`
- [x] `[]`
- [ ] Une erreur : `L` vide
- Réponse : `[]` (mesuré) : `L` est définie, vide, en ligne de commande ; `?=` ne joue donc pas. C'est le cas que `$(or)` couvre.

## 20. $(if) : une option seulement si la variable existe
- Id : make-if-option-facultative
- Sous-thème : fonctions
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : make-variable-absente-vide
- Mots-clés : profil AWS, OIDC, CI
- Source : data-platform · S1-08
- Définition : `$(if $(P),--profile $(P))` produit l'option quand `P` n'est pas vide, et rien sinon : une même cible sert en local et en CI.
- Contexte : En local, `PROFILE = data-platform` donne `--profile data-platform` ; en CI, `PROFILE=` (identifiants OIDC de l'environnement) ne donne rien, au lieu d'un `--profile` sans valeur qui ferait échouer la commande. La fonction est évaluée par Make avant le shell : `make -n` montre la commande finale, avec ou sans l'option.
- Usage : ✅ options facultatives (`--profile`, `-var-file`, `--dry-run`) · ❌ logique sur plusieurs branches : `ifeq` à la lecture, ou un script.

```makefile
# Exemple 1 : local puis CI
P ?= data-platform
opt:
	@echo cmd $(if $(P),--profile $(P))
# make opt    → cmd --profile data-platform
# make opt P= → cmd
```

- Quiz : Qu'affiche `make opt P=" "` (une espace) ?
- [ ] `cmd --profile`
- [x] `cmd`
- [ ] `cmd --profile  `
- Réponse : `cmd` (mesuré, GNU make 3.81) : une condition qui ne contient que des espaces compte comme vide pour `$(if)`.

## 21. ifeq : une condition à la lecture
- Id : make-ifeq-a-la-lecture
- Sous-thème : conditions
- Type : concept
- Niveau : 2
- Profils : ops
- Mots-clés : recette, shell
- Définition : `ifeq (a,b)` … `endif` garde ou retire des lignes du Makefile selon une valeur, évaluée à la lecture du fichier, pas à l'exécution.
- Contexte : C'est un préprocesseur, comme un `#if` de C : Make lit le fichier, tranche chaque `ifeq`, puis exécute les recettes. La condition ne voit que les variables Make connues à ce moment (ligne de commande, environnement, lignes au-dessus). `ifdef`, `ifndef` et `ifneq` suivent la même règle ; `else` est permis.
- Usage : ✅ options propres à un environnement (`-lock-timeout` en prod) · ❌ tester le résultat d'une commande lancée par la recette : faire le test dans le shell (`if [ … ]`).

```makefile
# Exemple 1 : une option seulement en prod
# make plan ENV=prod → plan -lock-timeout=5m
# make plan          → plan
ENV ?= dev
ifeq ($(ENV),prod)
FLAGS = -lock-timeout=5m
endif
plan:
	@echo plan $(FLAGS)
```

- Quiz : Une recette fait `ENV=prod` (shell) puis, plus bas, contient un `ifeq ($(ENV),prod)`. Le bloc est-il gardé ?
- [ ] Oui : la ligne précédente a défini `ENV`
- [x] Non : `ifeq` est tranché à la lecture
- [ ] Oui, si `ENV` est exportée
- [ ] Erreur : `ifeq` interdit dans une recette
- Réponse : non : `ifeq` est tranché avant toute exécution, et une variable du shell n'existe jamais pour Make ; tester dans le shell avec `if [ … ]`.

## 22. $(error) : bloquer tôt
- Id : make-error-garde
- Sous-thème : conditions
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : make-variable-absente-vide
- Voir aussi : make-garde-dans-recette
- Mots-clés : recette, compte AWS
- Définition : `$(error message)` arrête Make avec ce message dès qu'il est développé : sert de garde sur une variable obligatoire.
- Contexte : Placé au niveau du fichier (dans un `ifndef`), il s'exécute à la lecture, avant toute recette. Placé dans une recette, il s'exécute quand Make développe la recette, et Make développe la recette entière avant d'en lancer la première ligne : rien ne tourne. `$(warning …)` affiche sans arrêter.
- Usage : ✅ variable sans valeur par défaut raisonnable (compte AWS, nom de bucket de prod) · ❌ variable qui a un défaut sûr : `?=` suffit.

```makefile
# Exemple 1 : garde au niveau du fichier
# make plan     → *** ENV obligatoire.  Stop.
# make plan ENV=dev → plan dev
ifndef ENV
$(error ENV obligatoire)
endif
plan:
	@echo plan $(ENV)
```

```makefile
# Exemple 2 : garde dans la recette
plan:
	@echo avant
	$(if $(ENV),,$(error ENV obligatoire))
# $ make plan
# *** ENV obligatoire.  Stop.
# ("avant" n'est jamais affiché)
```

- Quiz : Avec la garde `ifndef ENV`, que fait `make plan ENV=` (valeur vide) ?
- [x] `*** ENV obligatoire.  Stop.`
- [ ] `plan` seul : `ENV` est définie
- [ ] `plan dev` : défaut implicite
- [ ] Un avertissement, puis `plan`
- Réponse : `ENV obligatoire` : pour `ifdef` / `ifndef`, une variable vide compte comme non définie ; la garde protège aussi de `ENV=`.

## 23. garde dans la recette : test -n || { …; exit 2; }
- Id : make-garde-dans-recette
- Sous-thème : conditions
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : make-variable-absente-vide, shell-enchainer-et-ou
- Mots-clés : recette, cible Make, code de sortie
- Source : data-platform · S1-08
- Définition : `@test -n "$(FROM)" || { echo "usage : …"; exit 2; }` en première ligne arrête la seule cible concernée quand un paramètre manque.
- Contexte : Contrairement à `$(error)` au niveau du fichier, la garde ne touche que la cible qui l'utilise : `make check` n'exige pas `FROM`. Les accolades sont indispensables : sans elles, `test … || echo usage; exit 2` lance `exit 2` dans tous les cas, et la cible échoue toujours. `exit 2` suit la convention « erreur d'utilisation ».
- Usage : ✅ paramètre obligatoire d'une seule cible (`make replay FROM= TO=`) · ❌ variable dont dépend tout le Makefile (`ENV`) : garde à la lecture avec `$(error)`.

```makefile
# Exemple 1 : la garde de make replay
replay:
	@test -n "$(FROM)" -a -n "$(TO)" \
	  || { echo "usage : make replay \
	FROM=… TO=…"; exit 2; }
	@echo "rejoue $(FROM) → $(TO)"
# make replay → usage…, Error 2
```

- Quiz : Que fait `make bad FROM=2026-10-01` avec la recette `@test -n "$(FROM)" || echo usage; exit 2` ?
- [ ] Rien : `FROM` est fourni
- [x] Échoue avec `Error 2`
- [ ] Affiche `usage` puis réussit
- Réponse : `Error 2` (mesuré) : sans accolades, `; exit 2` n'appartient pas au `||` et s'exécute toujours.

## 24. variable : l'espace avant le commentaire
- Id : make-espace-avant-commentaire
- Sous-thème : variables
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Mots-clés : backend
- Définition : La valeur d'une variable s'étend jusqu'au `#`, espaces compris : un commentaire en fin de ligne laisse un espace final.
- Contexte : Make retire les espaces au début de la valeur, pas à la fin. `ENV ?= dev # défaut` vaut donc `dev ` : invisible à l'écho, mais un chemin construit avec devient `envs/dev /backend.hcl`, et l'erreur vient de Terraform, pas de Make. On met les commentaires sur leur propre ligne, ou on nettoie avec `$(strip …)`.
- Usage : ✅ commentaire sur la ligne au-dessus de la variable · ❌ commentaire en bout de ligne de variable : espace final garanti.

```makefile
# Exemple 1 : le commentaire au-dessus
# $ make init → [envs/dev/backend.hcl]
# défaut : dev
ENV ?= dev
F = envs/$(ENV)/backend.hcl
init:
	@echo "[$(F)]"
```

```makefile
# Exemple 2 : nettoyer avec strip
V = dev   # ici la valeur est "dev   "
init:
	@echo "[$(strip $(V))]"
# → [dev]
```

- Quiz : Avec `ENV ?= dev # défaut` sur une seule ligne, qu'affiche `make init` ?
- [ ] `[envs/dev/backend.hcl]`
- [ ] `[envs/dev # défaut/backend.hcl]`
- [ ] `*** missing separator.  Stop.`
- [x] `[envs/dev /backend.hcl]`
- Réponse : `[envs/dev /backend.hcl]` : l'espace avant `#` fait partie de la valeur ; le chemin casse sans aucune erreur Make.

## 25. make -n : $$( ) n'est pas lancé
- Id : make-n-substitution-non-lancee
- Sous-thème : exécution
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : make-n-simuler, make-double-dollar-shell
- Mots-clés : dry-run, substitution de commande, output
- Source : data-platform · S1-08
- Définition : En simulation (`make -n`), une substitution du shell `$$(cmd)` est affichée telle quelle, sans être exécutée, contrairement à `$(shell cmd)`.
- Contexte : `$(shell …)` est une fonction de Make : elle tourne pour afficher la commande. `$$(…)` n'est qu'un texte pour Make, que le shell exécuterait : `-n` ne lance pas le shell, donc rien ne tourne. Conséquence : `make -n replay` ne contacte ni Terraform ni AWS, et montre `--function $(terraform … | jq …)` au lieu du nom résolu.
- Usage : ✅ relire une cible qui interroge Terraform ou AWS sans rien appeler · ❌ attendre de `make -n` la valeur résolue d'un `$$(…)` : lancer la sous-commande à part.

```makefile
# Exemple 1 : la substitution reste du texte
n:
	echo $$(date +%s)
# make -n n → echo $(date +%s)
#   (date n'est pas lancé)
```

- Quiz : `make -n replay FROM=2026-10-01 TO=2026-10-19` : combien d'appels à AWS ?
- [x] Aucun
- [ ] Un : `terraform output` lit l'état S3
- [ ] Dix-neuf
- Réponse : aucun : `terraform output` est dans un `$$(…)`, donc non exécuté en simulation (mesuré : la commande affichée garde `$(terraform …)`).

## 26. $$( ) en échec : la recette continue
- Id : make-substitution-en-echec
- Sous-thème : exécution
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : make-double-dollar-shell, shell-substitution-commande
- Voir aussi : shell-set-euo-pipefail
- Mots-clés : substitution de commande, code de sortie, jq
- Source : data-platform · S1-08
- Définition : Si la commande d'un `$$(…)` échoue au milieu d'une ligne, la ligne réussit quand même : c'est le code de la commande principale qui compte.
- Contexte : `--function $$(… | jq -er '."x"')` : la clé absente fait échouer `jq`, mais `-e` affiche quand même `null`, capturé, et la commande principale tourne avec `--function null`. Make ne voit que le code final. Pour échouer tôt : une ligne séparée qui teste la valeur, ou `$(shell …)` plus `$(error)` si elle est vide.
- Usage : ✅ valeur lue dans un output, puis contrôlée avant usage · ❌ compter sur `jq -e` ou `set -e` à l'intérieur d'un `$$(…)` inséré dans une autre commande.

```makefile
# Exemple 1 : null capturé, ligne réussie
subjq:
	@echo fn=[$$(echo '{}' \
	  | jq -er '.x')]
# make subjq → fn=[null]
#   code 0
```

- Quiz : `make replay LAMBDA=inconnue` avec `--function $$(… | jq -er …)` : que reçoit `replay.py` ?
- [ ] Rien : make s'arrête sur l'échec de jq
- [x] `--function null`
- [ ] `--function` sans valeur
- Réponse : `--function null` : `jq -e` écrit `null` avant de sortir en 1, et ce code est perdu dans la substitution (mesuré : `fn=[null]`).
