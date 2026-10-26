---
type: glossaire
langage: DevOps
updated: 2026-10-26
---

# Glossaire DevOps

## .gitignore
- Définition : Fichier qui liste, par motifs, les fichiers que Git ne doit pas proposer au commit ; il n'agit pas sur un fichier déjà suivi.
- Exemple : Le `.gitignore` de data-platform exclut `*.tfstate`, `.venv/` et `local.tfvars`, qui contiennent des secrets ou dépendent du poste.
- Alias : gitignore
- Carte : git-gitignore-derniere-regle

## ADR
- Définition : Architecture Decision Record : court document daté qui note une décision technique, son contexte et les options écartées.
- Exemple : « Pourquoi Scheduler plutôt qu'une règle EventBridge » relève d'un ADR dans `docs/`, pas du README.
- Alias : Architecture Decision Record, ADRs

## adressage par contenu
- Définition : Nommer un fichier ou un objet d'après l'empreinte de son contenu : même contenu, même nom ; un contenu changé donne un nouveau nom.
- Exemple : Le zip d'une Lambda est publié sous une clé qui contient son sha256 dans le bucket artifacts.
- Alias : adressé par contenu, content-addressed
- Carte : ci-cd-artefact-adresse-par-hash

## arbre de travail
- Définition : Les fichiers du dépôt tels qu'ils sont sur le disque, modifications non commitées comprises ; « propre » quand il ne diffère pas du dernier commit.
- Exemple : `git status --porcelain` vide signifie un arbre de travail propre : le zip publié correspond exactement au commit.
- Alias : working tree, copie de travail

## artefact
- Définition : Fichier produit par un build (zip, bundle, plan) et transmis tel quel aux étapes suivantes, pour déployer exactement ce qui a été testé.
- Exemple : Le zip de la Lambda `ingest-bodacc`, rangé sous son empreinte dans le bucket d'artefacts.
- Alias : artefacts, artifact
- Carte : ci-cd-artefact-construire-une-fois

## astreinte
- Définition : Organisation où une personne est joignable hors des heures ouvrées pour réagir aux alertes de production (≈ on-call).
- Exemple : Le topic d'alertes de prod est abonné au canal de l'astreinte ; celui de dev, non.
- Alias : on-call

## bash
- Définition : Shell Unix le plus répandu, celui des scripts `#!/usr/bin/env bash` et de la plupart des runners de CI ; macOS livre une vieille version 3.2.
- Exemple : Un script testé sous zsh peut casser sous bash, qui découpe une variable non protégée sur les espaces.
- Carte : shell-decoupage-zsh-bash

## branche
- Définition : Pointeur mobile vers un commit, qui avance à chaque nouveau commit ; une branche par sujet permet de travailler sans toucher `main`.
- Exemple : `git switch -c RLINK-123` crée la branche du ticket RLINK-123 sur le commit courant.
- Alias : branches, branche git
- Carte : git-branche-pointeur

## branche protégée
- Définition : Branche (souvent `main`) que la forge protège : pas de push forcé, fusion par MR, et seule à recevoir les variables de CI protégées.
- Exemple : Sur GitLab, un pipeline de la branche `RLINK-123` ne reçoit pas le jeton protégé réservé à `main`.
- Alias : branches protégées
- Carte : ci-cd-variables-protegees

## build reproductible
- Définition : Build qui produit les mêmes octets à partir du même code, sur n'importe quel poste : même contenu, même empreinte.
- Exemple : Le zip d'une Lambda de data-platform est reproductible (dates fixes, ordre trié) : deux pipelines du même commit donnent la même clé S3.
- Alias : reproductible, builds reproductibles
- Carte : ci-cd-artefact-adresse-par-hash

## cache de CI
- Définition : Dossier gardé d'un pipeline à l'autre pour accélérer les jobs (paquets téléchargés) ; sans garantie, il peut manquer à tout moment.
- Exemple : Le cache de `~/.cache/uv`, avec une clé calculée sur `uv.lock`, évite de retélécharger les paquets à chaque push.
- Alias : cache CI
- Carte : ci-cd-cache-cle-lockfile

## CI
- Définition : Intégration continue : chaque push déclenche automatiquement build, lint et tests sur un serveur ; avec le déploiement automatique, on parle de CI/CD.
- Exemple : revision-pwa déploie son app par CodeBuild à chaque push sur `main`.
- Alias : intégration continue, CI/CD, déploiement continu
- Carte : ci-cd-stages-ordre

## cible Make
- Définition : Nom d'une règle du Makefile (`plan`, `check`), lancée par `make <cible>` ; normalement le fichier qu'elle produit, souvent juste une commande.
- Exemple : `make check` lance ruff puis pytest dans data-platform.
- Alias : cible, cibles, cibles Make
- Carte : make-regle-cible-recette

## CLI
- Définition : Command-Line Interface : programme qu'on pilote en tapant des commandes dans un terminal (`aws`, `terraform`, `git`).
- Exemple : `aws s3 ls` utilise la CLI AWS pour lister les buckets.
- Alias : ligne de commande, interface en ligne de commande

## clone
- Définition : Copie locale complète d'un dépôt Git (fichiers commités et historique), créée par `git clone` ; elle n'a aucun fichier ignoré.
- Exemple : Tester le README de data-platform dans un clone neuf révèle les fichiers qui n'existent que sur le poste de l'auteur.
- Alias : git clone, clone neuf
- Carte : documentation-tester-clone-neuf

## clone superficiel
- Définition : Clone git qui ne télécharge que les derniers commits (`--depth 1`), sans l'historique : plus rapide, mais `git log` et les anciens tags manquent.
- Exemple : CodeBuild clone le dépôt avec `git_clone_depth = 1` : seul le commit construit est récupéré.
- Alias : shallow clone, clone léger
- Carte : ci-cd-clone-superficiel

## code de sortie
- Définition : Nombre renvoyé par une commande quand elle se termine : 0 = succès, tout autre = échec ; le shell le donne dans `$?`.
- Exemple : `ruff check` sort avec 1 s'il reste une erreur : le job de CI échoue.
- Alias : code retour, exit code, $?, codes de sortie
- Carte : shell-code-de-sortie

## commit
- Définition : Instantané enregistré de tous les fichiers suivis, avec auteur, date, message et parent ; identifié par son hash.
- Exemple : `main: S1-09 terminée` est un commit de data-platform, préfixé par le nom de la branche.
- Alias : commits, git commit

## conflit git
- Définition : Arrêt d'un merge ou d'un rebase quand deux branches modifient les mêmes lignes ; Git écrit les deux versions entre marqueurs `<<<<<<<` et `>>>>>>>`.
- Exemple : Deux branches qui ajoutent chacune une dépendance entrent en conflit dans `uv.lock`.
- Alias : conflit, conflits, conflit de merge
- Carte : git-conflit-marqueurs

## conteneur
- Définition : Processus isolé lancé à partir d'une image (Docker) : il embarque son système de fichiers et ses outils, identique sur chaque machine.
- Exemple : Chaque job GitLab tourne dans un conteneur neuf de l'image `python:3.13-slim`.
- Alias : conteneurs, container

## Corepack
- Définition : Outil de Node.js qui installe et lance la version exacte du gestionnaire de paquets (pnpm, Yarn) fixée par `packageManager` du `package.json`.
- Exemple : `corepack enable` puis `pnpm install` utilise le pnpm demandé par le dépôt, quel que soit celui installé sur la machine.
- Carte : AWS/codebuild-corepack-pnpm

## cron
- Définition : Planificateur de tâches d'Unix ; par extension, l'expression à champs (minute, heure, jour, mois…) qui dit quand relancer une tâche.
- Exemple : `cron(0 6 * * ? *)` dans EventBridge Scheduler lance l'ingestion chaque jour à 06:00.
- Alias : expression cron, crontab
- Carte : AWS/sqs-eventbridge-scheduler-cron

## dépendance transitive
- Définition : Paquet qu'on n'a pas demandé soi-même, installé parce qu'une dépendance directe en a besoin.
- Exemple : `idna` arrive dans data-platform parce que `httpx` l'utilise.
- Alias : dépendances transitives, transitive
- Carte : uv-remove-transitives

## dépôt distant
- Définition : Copie du dépôt hébergée sur une forge (GitHub, GitLab), nommée `origin` par défaut ; `push` y envoie les commits, `fetch` les récupère.
- Exemple : `origin/main` est la copie locale de la branche `main` du dépôt distant au dernier `fetch`.
- Alias : origin, remote
- Carte : git-fetch-ou-pull

## dépôt git
- Définition : Dossier versionné par Git : les fichiers du projet plus le dossier `.git/`, qui contient tout l'historique.
- Exemple : data-platform est un dépôt GitHub public, revision-pwa un dépôt CodeCommit.
- Alias : dépôt, dépôts, repo, repository

## descripteur de fichier
- Définition : Petit entier par lequel le système désigne un fichier ou une connexion ouverts par un processus ; il faut le fermer après usage.
- Exemple : `fd, chemin = tempfile.mkstemp()` rend un descripteur brut : sans `os.close(fd)`, il reste ouvert.
- Alias : descripteurs de fichier, file descriptor, fd
- Carte : Python/fichiers-temporaires-mkstemp-descripteur

## Docker
- Définition : Outil qui construit des images (un système de fichiers figé avec un programme) et les lance en conteneurs isolés.
- Exemple : `sam build --use-container` construit le zip d'une Lambda dans un conteneur Docker à l'image du runtime.

## dotenv
- Définition : Format de fichier `NOM=valeur`, une variable par ligne ; GitLab l'utilise pour transmettre des variables d'un job aux suivants.
- Exemple : Le job de publication écrit `LAMBDA_KEY=…` dans `build.env`, lu par le job de déploiement.
- Alias : .env, fichier dotenv
- Carte : ci-cd-dotenv-variables-job

## droits Unix
- Définition : Permissions d'un fichier en lecture, écriture et exécution pour le propriétaire, le groupe et les autres, notées `rwxr-xr-x` ou en octal `755`.
- Exemple : Chaque fichier du zip d'une Lambda doit être en `644`, lisible par tous : le runtime ne tourne pas sous son propriétaire.
- Alias : permissions Unix, mode Unix
- Carte : Python/archives-external-attr-droits

## dry-run
- Définition : Exécution « à blanc » : l'outil affiche ce qu'il ferait sans rien modifier, pour relire avant de lancer.
- Exemple : `make -n up ENV=prod` affiche les commandes Terraform sans les exécuter.
- Alias : simulation, à blanc
- Carte : make-n-simuler

## entrée standard
- Définition : Flux par lequel une commande lit ses données (stdin) : le clavier par défaut, ou un fichier (`<`) ou la sortie d'une autre commande (`|`).
- Exemple : Dans `aws … | jq '.Buckets'`, jq lit la réponse JSON sur son entrée standard.
- Alias : stdin
- Carte : shell-redirection-entree

## environnement de déploiement
- Définition : Copie isolée de l'application et de son infrastructure (dev, int, prod), avec sa configuration et ses droits propres.
- Exemple : data-platform n'a qu'un environnement déployé, `dev`, préfixé `data-platform-dev-`.
- Alias : environnements de déploiement
- Carte : ci-cd-environnement-approbation

## fichier .example
- Définition : Modèle commité d'un fichier de configuration ignoré par Git, avec des valeurs factices, à copier puis remplir.
- Exemple : `cp backend.hcl.example backend.hcl`, puis on y met son propre bucket d'état.
- Alias : .example, fichiers .example
- Carte : documentation-fichier-example

## fichier suivi
- Définition : Fichier que Git connaît (présent dans l'index ou le dernier commit) ; un fichier non suivi (`??`) n'est versionné qu'après `git add`.
- Exemple : `out.json` non suivi et non ignoré suffit à rendre l'arbre « sale » pour `git status`.
- Alias : fichiers suivis, suivi, non suivi
- Carte : git-gitignore-fichier-deja-suivi

## forge
- Définition : Plateforme qui héberge des dépôts Git avec revue, CI et gestion des accès : GitHub, GitLab, CodeCommit.
- Exemple : data-platform vit sur la forge GitHub, revision-pwa sur CodeCommit.
- Alias : forges

## fork
- Définition : Copie d'un dépôt sous un autre compte de la forge, depuis laquelle on propose des changements au dépôt d'origine par PR.
- Exemple : Une PR venue d'un fork tourne sans les secrets du dépôt cible.
- Alias : forks
- Carte : ci-cd-pr-fork-sans-secrets

## formateur
- Définition : Outil qui réécrit le code dans un style unique (espaces, guillemets, retours à la ligne), sans changer ce qu'il fait (≈ prettier).
- Exemple : `ruff format` est le formateur Python de data-platform, lancé par `make fmt`.
- Alias : formatter, formatage
- Carte : ruff-check-ou-format

## Git
- Définition : Système de gestion de versions : il enregistre l'historique des fichiers d'un projet en commits et permet de travailler en branches.
- Exemple : Chaque changement de data-platform part en commit Git préfixé par la branche, puis est poussé sur GitHub.

## GitHub
- Définition : Forge de Microsoft qui héberge des dépôts Git, avec pull requests, revue et CI (GitHub Actions).
- Exemple : Le dépôt public data-platform est hébergé sur GitHub.

## GitHub Actions
- Définition : CI de GitHub : des workflows YAML dans `.github/workflows/` déclarent leurs déclencheurs et leurs jobs, faits d'étapes.
- Exemple : Un workflow `on: push` sur `main` peut lancer `make check` puis le déploiement.
- Alias : workflow GitHub, workflows GitHub
- Carte : ci-cd-github-actions-workflow

## GitLab
- Définition : Forge qui héberge des dépôts Git, avec merge requests, revue et CI intégrée (GitLab CI).
- Exemple : Les projets d'entreprise utilisent souvent GitLab, avec un `.gitlab-ci.yml` à la racine.

## GitLab CI
- Définition : CI de GitLab : un fichier `.gitlab-ci.yml` décrit stages et jobs, exécutés par des runners à chaque push.
- Exemple : Un job `test` avec `script: [make check]` dans l'étape `test`.
- Alias : .gitlab-ci.yml, GitLab CI/CD
- Carte : ci-cd-job-gitlab-script

## glibc
- Définition : Bibliothèque C standard de GNU, présente sur la plupart des Linux ; un binaire compilé contre une version récente ne tourne pas sur une plus ancienne.
- Exemple : Une roue `manylinux2014` exige glibc 2.17 ou plus ; Amazon Linux 2023, le système des runtimes Lambda récents, en fournit une plus récente.
- Carte : AWS/lambda-manylinux-glibc

## glob
- Définition : Motif de noms de fichiers avec jokers (`*` n'importe quels caractères, `?` un seul, `[ab]` un parmi) que le shell remplace par les fichiers trouvés.
- Exemple : `lambdas/*` désigne tous les dossiers de Lambda ; zsh refuse un glob qui ne trouve rien.
- Alias : globs, motif de fichiers
- Carte : shell-glob-zsh-sans-correspondance

## hash de commit
- Définition : Identifiant d'un commit (SHA de 40 caractères, souvent abrégé à 7) calculé sur son contenu et son parent ; il change si le commit est refait.
- Exemple : `6533882` désigne le commit « miroir Notion des cours » de data-platform.
- Alias : SHA de commit, hash git
- Carte : git-branche-pointeur

## HEAD
- Définition : Pointeur de Git vers le commit sur lequel on travaille, en général le dernier commit de la branche courante.
- Exemple : `git diff HEAD` compare le disque au dernier commit ; `HEAD~1` désigne son parent.
- Carte : git-diff-disque-index-head

## heredoc
- Définition : Bloc de texte sur plusieurs lignes, délimité par un marqueur (`<<EOF` … `EOF`), dans le shell ou en HCL ; ses `${…}` sont remplacés sauf échappement.
- Exemple : `git commit -F - <<'EOF'` envoie un message de commit multi-ligne sans rien interpréter.
- Alias : heredocs, here-document
- Carte : shell-heredoc-fige

## Homebrew
- Définition : Gestionnaire de paquets de macOS (et de Linux) : `brew install <outil>` télécharge et installe un logiciel en ligne de commande.
- Exemple : `brew install duckdb jq` installe les deux outils qui servent à explorer les partitions BODACC.
- Alias : brew

## hook
- Définition : Script lancé automatiquement à un moment précis (avant un commit, un push, un build) pour contrôler ou compléter l'action.
- Exemple : Le hook pre-commit de data-platform lance ruff à chaque `git commit` et l'annule s'il échoue.
- Alias : hooks, hook git, hooks git
- Carte : git-hook-commit-msg

## hotfix
- Définition : Correctif urgent livré directement en production, en dehors du rythme normal des versions.
- Exemple : Un correctif fait sur une branche de ticket est recopié sur `main` par `git cherry-pick` pour partir tout de suite.
- Alias : hotfixes, correctif urgent
- Carte : git-cherry-pick

## image Docker
- Définition : Modèle figé (système de fichiers, outils, programme) à partir duquel on lance des conteneurs ; nommée et versionnée par un tag.
- Exemple : `python:3.13-slim` est l'image Docker d'un job GitLab qui lance les tests Python.
- Alias : images Docker

## index git
- Définition : Zone de préparation de Git (staging) : ce que `git add` y place part au prochain commit, indépendamment du disque.
- Exemple : `git diff --staged` montre exactement le contenu de l'index, donc du prochain commit.
- Alias : staging, zone de staging
- Carte : git-diff-disque-index-head

## job
- Définition : Unité de travail d'un pipeline de CI : une suite de commandes exécutée seule, dans une machine ou un conteneur neuf.
- Exemple : Le job `lint` lance `make lint` ; s'il échoue, le pipeline s'arrête avant le déploiement.
- Alias : jobs, job de CI
- Carte : ci-cd-job-gitlab-script

## jq
- Définition : Outil en ligne de commande qui lit du JSON, en extrait ou transforme des valeurs avec un filtre, et réécrit du JSON ou du texte.
- Exemple : `terraform output -json bucket_names | jq -r .raw` donne le nom du bucket raw.
- Carte : jq-lire-champ

## latence
- Définition : Délai entre une demande et sa réponse, ou entre l'arrivée d'une donnée et son traitement ; on la suit en millisecondes, souvent par percentile.
- Exemple : Une fenêtre de batching SQS de 10 s ajoute jusqu'à 10 s de latence avant que la Lambda voie le message.
- Alias : latency

## lien symbolique
- Définition : Fichier spécial qui pointe vers un autre chemin : l'ouvrir ouvre la cible (≈ raccourci).
- Exemple : `ln -s ../shared lib` crée `lib`, qui renvoie vers `../shared` ; une archive piégée peut s'en servir pour écrire hors du dossier visé.
- Alias : liens symboliques, symlink, symlinks

## linter
- Définition : Outil qui analyse le code sans l'exécuter et signale erreurs probables et mauvaises pratiques (≈ eslint).
- Exemple : `ruff check` est le linter de data-platform : il signale un import inutilisé (F401).
- Alias : lint, linters
- Carte : ruff-check-ou-format

## locale
- Définition : Réglage régional d'un processus (`LANG`, `LC_ALL`) : langue des messages, encodage du texte, format des nombres et des dates.
- Exemple : Avec `LANG=fr_FR.UTF-8`, `subprocess.run(text=True)` décode la sortie d'une commande en UTF-8.
- Alias : LANG, LC_ALL

## lockfile
- Définition : Fichier généré qui fige la version exacte et l'empreinte de chaque dépendance installée ; commité, il garantit les mêmes versions partout.
- Exemple : `uv.lock` dans data-platform, `pnpm-lock.yaml` dans revision-pwa.
- Alias : fichier de verrou, uv.lock, pnpm-lock.yaml, package-lock.json
- Carte : uv-lock-universel

## Makefile
- Définition : Fichier lu par l'outil `make`, qui décrit des cibles et les commandes (recettes) à lancer pour les obtenir.
- Exemple : Le Makefile de data-platform offre `make check`, `make plan` et `make up`.
- Alias : Make, Makefiles
- Carte : make-regle-cible-recette

## Markdown
- Définition : Format de texte léger (`#` titres, `-` listes, blocs de code entre trois accents graves) affiché mis en forme par GitHub et les éditeurs.
- Exemple : Les README, les cours et les cartes de révision de data-platform sont écrits en Markdown.
- Alias : .md
- Carte : documentation-schema-texte

## matrice
- Définition : Définition de CI qui génère un job par combinaison de valeurs (versions, environnements) à partir d'un seul modèle.
- Exemple : `parallel: matrix` avec `LAMBDA: [ingest-bodacc, normalize-bodacc]` lance un build par Lambda.
- Alias : matrix, matrices
- Carte : ci-cd-matrix-variantes

## merge
- Définition : Intégration d'une branche dans une autre ; Git avance simplement la branche, ou crée un commit de merge à deux parents.
- Exemple : Fusionner la MR `RLINK-123` crée un merge dans `main`.
- Alias : git merge, fusion
- Carte : git-merge-fast-forward

## monorepo
- Définition : Dépôt unique qui contient plusieurs projets liés (bibliothèques, services, infrastructure), versionnés et testés ensemble.
- Exemple : data-platform réunit packages Python, Lambdas et Terraform dans un seul dépôt.
- Alias : monorepos, mono-dépôt
- Carte : uv-workspace-members

## MR
- Définition : Merge request (PR, pull request sur GitHub) : demande de fusion d'une branche, relue et testée par la CI avant d'entrer dans `main`.
- Exemple : Une montée de version du provider AWS passe par une MR où l'on relit le lock et le plan.
- Alias : merge request, PR, pull request, MRs

## npm
- Définition : Gestionnaire de paquets livré avec Node.js, et registre public des paquets JavaScript ; pnpm en est une alternative plus économe en disque.
- Exemple : `npm install` lit le `package.json` ; revision-pwa utilise pnpm, qui installe depuis le même registre npm.
- Alias : registre npm

## OOM killer
- Définition : Mécanisme du noyau Linux qui tue un processus par `SIGKILL` quand la mémoire manque (OOM : Out Of Memory).
- Exemple : Un sous-processus tué par l'OOM killer rend `returncode = -9` en Python.
- Alias : OOM, Out Of Memory
- Carte : Python/sous-processus-returncode-signal

## package.json
- Définition : Fichier manifeste d'un projet Node.js : nom, version, dépendances et scripts (`pnpm run build`).
- Exemple : Le champ `packageManager` du `package.json` de revision-pwa fixe la version de pnpm que Corepack installe.
- Carte : pnpm-prebuild-hook-avant

## PATH
- Définition : Variable d'environnement qui liste les dossiers où le shell cherche les commandes tapées ; un outil hors de ces dossiers est « introuvable ».
- Exemple : `uv tool install` place ses outils dans `~/.local/bin`, qui doit être dans le PATH.

## pipe
- Définition : `a | b` branche la sortie standard de `a` sur l'entrée standard de `b`, pour chaîner des commandes.
- Exemple : `aws s3 cp s3://…/part-0001.jsonl.gz - | zcat | wc -l` compte les annonces d'une partition.
- Alias : pipes, tube, |
- Carte : shell-pipe-code-du-dernier

## pipeline
- Définition : Suite automatisée de jobs de CI/CD (build, tests, déploiement) déclenchée par un push, une MR ou un horaire.
- Exemple : Un pipeline GitLab enchaîne les étapes `build`, `test` et `deploy`.
- Alias : pipelines, pipeline CI
- Carte : ci-cd-stages-ordre

## placeholder
- Définition : Texte à remplacer dans un exemple (`<account_id>`, `VOTRE_BUCKET`), qui marque une valeur propre au lecteur.
- Exemple : Dans une commande, `<raw>` est un mauvais placeholder : le shell le lit comme une redirection.
- Alias : placeholders, valeur à remplacer
- Carte : documentation-placeholder-redirection

## pnpm
- Définition : Gestionnaire de paquets JavaScript (comme npm), rapide et économe en disque, avec un lockfile `pnpm-lock.yaml`.
- Exemple : `pnpm build` construit l'app de révision revision-pwa.
- Carte : pnpm-prebuild-hook-avant

## pointeur
- Définition : Petit fichier modifiable qui désigne l'artefact immuable à déployer (≈ dist-tag `latest` de npm) : changer de version, c'est réécrire le pointeur.
- Exemple : `lambdas/ingest-bodacc/current.json` désigne le zip à déployer et donne son empreinte.
- Alias : pointeurs, pointeur d'artefact, current.json
- Carte : ci-cd-pointeur-artefact

## POSIX
- Définition : Norme qui fixe l'interface commune des systèmes Unix (commandes, shell, appels système) ; macOS et Linux la suivent largement.
- Exemple : Pour POSIX, une ligne de texte finit par `\n` : un fichier JSONL bien formé se termine donc par un saut de ligne.
- Carte : Python/json-split-ou-splitlines

## pre-commit
- Définition : Outil qui installe et lance des hooks Git décrits dans `.pre-commit-config.yaml` (lint, format, contrôles) à chaque commit.
- Exemple : Dans data-platform, pre-commit lance `ruff check --fix` et `ruff format` avant chaque commit.
- Carte : pre-commit-install-par-clone

## promotion
- Définition : Déploiement dans l'environnement suivant (dev → int → prod) du même artefact déjà testé, sans le reconstruire.
- Exemple : Promouvoir une Lambda, c'est copier la clé du zip de dev vers le pointeur d'int.
- Carte : ci-cd-promotion-meme-artefact

## push forcé
- Définition : `git push --force` : remplace la branche distante par la locale même si des commits distants disparaissent ; `--force-with-lease` vérifie d'abord.
- Exemple : Après un rebase de sa branche de MR, on la pousse avec `--force-with-lease`.
- Alias : force push, push --force, --force-with-lease
- Carte : git-push-force-with-lease

## README
- Définition : Fichier `README.md` à la racine d'un dépôt ou d'un dossier : ce que c'est, les prérequis, le démarrage et les commandes courantes.
- Exemple : Le README de data-platform décrit l'architecture et l'ordre `bootstrap → make up`.
- Alias : README.md
- Carte : documentation-readme-quatre-questions

## rebase
- Définition : `git rebase` rejoue les commits d'une branche au-dessus d'une autre : historique linéaire, mais nouveaux hash.
- Exemple : `git rebase main` remet sa branche de ticket à jour avant la MR.
- Alias : git rebase, rebaser
- Carte : git-rebase-rejouer-commits

## recette
- Définition : Commandes d'une règle Make, chacune sur une ligne commençant par une tabulation, lancées pour obtenir la cible.
- Exemple : La recette de `make plan` lance `terraform -chdir=infra plan` avec le `.tfvars` de l'environnement.
- Alias : recettes, recette Make
- Carte : make-regle-cible-recette

## redirection
- Définition : Branchement d'un flux d'une commande vers un fichier : `>` écrase, `>>` ajoute, `<` lit, `2>` vise les erreurs.
- Exemple : `aws lambda invoke … out.json > /dev/null` jette l'affichage et garde la réponse dans `out.json`.
- Alias : redirections
- Carte : shell-ecraser-ou-ajouter

## reflog
- Définition : Journal local de Git qui garde chaque position passée de HEAD : on y retrouve un commit « perdu » après un reset ou un rebase.
- Exemple : `git reset --hard HEAD@{1}` revient avant un rebase raté.
- Alias : git reflog
- Carte : git-reflog-commit-perdu

## release
- Définition : Version publiée et identifiée d'un logiciel (`v1.2.0`), en général marquée par un tag Git et livrée par un pipeline dédié.
- Exemple : Pousser le tag `v1.2.0` peut déclencher le pipeline de release.
- Alias : releases, version publiée
- Carte : git-tag-leger-ou-annote

## répertoire courant
- Définition : Dossier à partir duquel un processus résout les chemins relatifs ; chaque processus a le sien, hérité de son parent.
- Exemple : `subprocess.run(cmd, cwd="infra")` lance la commande dans `infra/` sans changer le répertoire courant du script.
- Alias : dossier courant, cwd, working directory
- Carte : Python/sous-processus-cwd

## revert
- Définition : `git revert` crée un nouveau commit qui annule les changements d'un commit précédent, sans réécrire l'historique.
- Exemple : Un commit fautif déjà déployé depuis `main` s'annule par `git revert`, puis repasse par la CI.
- Alias : git revert
- Carte : git-revert-commit-publie

## rollback
- Définition : Retour à la dernière version saine en production, en redéployant un artefact ou un commit connu.
- Exemple : Remettre l'ancienne valeur du pointeur `current.json` puis `make up` redéploie le zip précédent.
- Alias : retour arrière, rollbacks
- Carte : ci-cd-rollback-ancien-commit

## RPO
- Définition : Recovery Point Objective : quantité maximale de données qu'on accepte de perdre lors d'une panne, exprimée en durée.
- Exemple : Une global table DynamoDB en MRSC a un RPO nul : une écriture confirmée existe déjà dans plusieurs régions.
- Alias : Recovery Point Objective
- Carte : AWS/dynamodb-global-tables-mrsc

## ruff
- Définition : Outil Python très rapide qui réunit linter (`ruff check`) et formateur (`ruff format`), configuré dans `pyproject.toml`.
- Exemple : `make lint` lance `uv run ruff check` puis `ruff format --check` dans data-platform.
- Carte : ruff-check-ou-format

## runbook
- Définition : Procédure écrite, pas à pas, pour exploiter ou réparer un système : quoi vérifier, quelles commandes lancer, quel résultat attendre.
- Exemple : La description d'une alarme CloudWatch peut contenir le runbook à suivre quand elle sonne.
- Alias : runbooks, procédure d'exploitation
- Carte : AWS/cloudwatch-alarm-description-runbook

## runner
- Définition : Machine (ou conteneur) qui exécute les jobs de CI ; sur gitlab.com, des runners partagés facturés à la minute.
- Exemple : Un runner neuf n'a aucun cache : une erreur masquée sur le poste y apparaît.
- Alias : runners, runner CI
- Carte : ci-cd-job-gitlab-script

## SemVer
- Définition : Versionnement sémantique `MAJEUR.MINEUR.CORRECTIF` : le majeur change en cas de rupture, le mineur pour un ajout compatible, le correctif pour un bug.
- Exemple : Passer d'un module en 4.1.0 à 5.0.0 annonce un changement incompatible.
- Alias : versionnement sémantique, semantic versioning

## set -e
- Définition : Option du shell qui arrête un script dès qu'une commande échoue (code de sortie non nul), au lieu de continuer.
- Exemple : `set -euo pipefail` en tête d'un script de déploiement : une étape ratée arrête tout avant la suivante.
- Alias : errexit
- Carte : shell-set-euo-pipefail

## shebang
- Définition : Première ligne d'un script (`#!/usr/bin/env bash`) qui indique quel programme doit l'exécuter, quel que soit le terminal d'où on le lance.
- Exemple : `#!/usr/bin/env python3` en tête d'un script sans extension le fait exécuter par Python.

## shell
- Définition : Programme qui lit les commandes tapées dans le terminal (ou un script) et les exécute : zsh, bash, sh.
- Exemple : Chaque ligne de recette Make tourne dans un shell `/bin/sh` neuf.
- Alias : shells, interpréteur de commandes

## signal Unix
- Définition : Notification que le système envoie à un processus : `SIGTERM` (arrête-toi), `SIGKILL` (tué sans délai), `SIGINT` (Ctrl+C).
- Exemple : En Python, `returncode = -15` signifie que le processus enfant a reçu `SIGTERM`.
- Alias : signaux Unix, SIGKILL, SIGTERM
- Carte : Python/sous-processus-returncode-signal

## SLA
- Définition : Service Level Agreement : engagement chiffré d'un fournisseur sur la disponibilité d'un service, avec compensation s'il n'est pas tenu.
- Exemple : Le SLA de DynamoDB promet 99,999 % de disponibilité pour une global table, 99,99 % pour une table d'une seule région.
- Alias : Service Level Agreement

## sortie d'erreur
- Définition : Flux où une commande écrit ses messages d'erreur (stderr, numéro 2), séparé de la sortie normale.
- Exemple : `B=$(terraform output -raw x)` ne capture pas l'erreur, qui part sur la sortie d'erreur.
- Alias : stderr, sortie erreur
- Carte : shell-dev-null

## sortie standard
- Définition : Flux où une commande écrit son résultat (stdout, numéro 1) : l'écran par défaut, ou un fichier ou une autre commande.
- Exemple : `jq -r .raw` écrit le nom du bucket sur la sortie standard, capté par `$(…)`.
- Alias : stdout
- Carte : shell-ecraser-ou-ajouter

## SOURCE_DATE_EPOCH
- Définition : Variable d'environnement standard des builds reproductibles : un timestamp Unix que les outils utilisent à la place de l'heure courante.
- Exemple : `SOURCE_DATE_EPOCH=315532800` fixe toutes les dates d'une archive au 1er janvier 1980.
- Carte : Python/archives-zipinfo-date-fixe

## sous-shell
- Définition : Copie du shell lancée dans un processus à part (pipe, `$(…)`, parenthèses) : les variables qu'elle modifie sont perdues ensuite.
- Exemple : En bash, un compteur incrémenté dans `cmd | while read` vaut toujours 0 après la boucle.
- Alias : subshell, sous-shells
- Carte : shell-pipe-while-sous-shell

## stage
- Définition : Étape d'un pipeline GitLab (`build`, `test`, `deploy`) : ses jobs tournent en parallèle, la suivante attend qu'ils aient tous réussi.
- Exemple : Un test rouge dans le stage `test` empêche le stage `deploy` de démarrer.
- Alias : stages, étape de pipeline
- Carte : ci-cd-stages-ordre

## stash
- Définition : Pile locale où `git stash` met de côté les modifications non commitées, pour retrouver un dossier propre puis les réappliquer.
- Exemple : `git stash` avant de passer sur `main` pour un hotfix, `git stash pop` au retour.
- Alias : git stash
- Carte : git-stash-mettre-de-cote

## substitution de commande
- Définition : `$(cmd)` dans une ligne de shell est remplacé par ce que `cmd` écrit sur la sortie standard.
- Exemple : `B=$(terraform -chdir=infra output -raw state_bucket)` range le nom du bucket dans `B`.
- Alias : $( ), $(…), substitutions de commande
- Carte : shell-substitution-commande

## système de fichiers
- Définition : Organisation des fichiers et dossiers d'un disque, gérée par le système ; un renommage n'y est atomique qu'à l'intérieur d'un même système de fichiers.
- Exemple : `os.replace(tmp, final)` est atomique quand `tmp` est dans le même dossier ; S3, lui, n'est pas un système de fichiers.
- Alias : systèmes de fichiers, filesystem
- Carte : Python/context-managers-ecriture-atomique

## tag git
- Définition : Nom fixe posé sur un commit (`v1.2.0`), qui ne bouge plus ensuite ; sert à marquer une version et à épingler une dépendance.
- Exemple : Un module Terraform partagé s'épingle par `?ref=v1.2.0`, un tag git.
- Alias : tags git, git tag
- Carte : git-tag-leger-ou-annote

## timeout
- Définition : Durée maximale accordée à une opération : passé ce délai, elle est interrompue et signalée en erreur.
- Exemple : Une Lambda a un timeout de 3 s par défaut, 15 min au plus ; httpx lève `ReadTimeout` quand la réponse tarde.
- Alias : timeouts, délai d'expiration
- Carte : AWS/lambda-timeout-15-minutes

## TOML
- Définition : Format de fichier de configuration lisible (`clé = valeur`, sections `[table]`), utilisé par `pyproject.toml` et `uv.lock`.
- Exemple : `[tool.ruff]` puis `line-length = 120` dans le `pyproject.toml` de data-platform.
- Alias : .toml

## umask
- Définition : Masque de droits d'un processus Unix : les permissions retirées des fichiers qu'il crée (avec `022`, un fichier `666` devient `644`).
- Exemple : Avec un umask `077`, les fichiers créés sont en `600` : zippés tels quels, le runtime Lambda ne pourrait pas les lire.
- Carte : AWS/lambda-droits-fichiers-zip

## unzip
- Définition : Commande Unix qui liste ou extrait le contenu d'une archive zip.
- Exemple : `unzip -Z lambda.zip` affiche droits, tailles et dates de chaque entrée du zip.

## uv
- Définition : Gestionnaire de projets et de paquets Python très rapide (≈ pnpm) : environnement virtuel, dépendances, lockfile et versions de Python.
- Exemple : `make sync` lance `uv sync --all-packages` pour installer tout le monorepo data-platform.
- Carte : uv-run-sync-auto

## variable d'environnement
- Définition : Valeur nommée transmise par le shell aux programmes qu'il lance (≈ `process.env`), lue par exemple par `aws` ou Python.
- Exemple : `export AWS_PROFILE=data-platform` fait utiliser ce profil à toutes les commandes `aws` de la session.
- Alias : variables d'environnement, env var
- Carte : shell-export-environnement

## workspace uv
- Définition : Ensemble de projets Python d'un monorepo déclarés comme membres, partageant un seul `uv.lock` et un seul environnement virtuel.
- Exemple : Les packages et les Lambdas de data-platform sont les membres du workspace uv racine.
- Alias : workspace Python, membre du workspace, membres du workspace
- Carte : uv-workspace-members

## YAML
- Définition : Format de configuration fondé sur l'indentation (`clé: valeur`, listes en `-`), utilisé par les CI et pre-commit.
- Exemple : `.gitlab-ci.yml` et `.pre-commit-config.yaml` sont des fichiers YAML.
- Alias : .yml, .yaml

## zsh
- Définition : Shell par défaut de macOS, proche de bash mais plus strict : un motif de fichiers sans correspondance y arrête la commande.
- Exemple : Sous zsh, `uv add --dev moto[s3]` sans guillemets échoue avec `no matches found`.
- Carte : shell-glob-zsh-sans-correspondance
