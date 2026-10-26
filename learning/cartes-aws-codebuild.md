---
title: "Cartes · CodeBuild"
type: cartes
langage: AWS
chapitre: Diffusion et livraison
cours: CodeBuild
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · CodeBuild
AWS · CodeBuild : projet, buildspec, logs, déclenchement, coûts (format spec v4 de revision-pwa).

## 1. source : CODECOMMIT, clone léger
- Id : codebuild-source-clone-leger
- Sous-thème : projet
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : codebuild-source-version-tete
- Définition : Le bloc `source` dit où CodeBuild prend le code : dépôt CodeCommit en HTTPS, cloné sur un seul commit, avec le chemin du buildspec.
- Contexte : `git_clone_depth = 1` fait un clone superficiel (≈ `git clone --depth 1`) : plus rapide, mais sans historique. `buildspec` est un chemin relatif à la racine du dépôt ; le fichier est donc versionné avec le code et change dans le même commit. Le rôle doit avoir `codecommit:GitPull` sur le dépôt, sinon le build échoue dès `DOWNLOAD_SOURCE`.
- Usage : ✅ build qui n'a besoin que de l'état courant du code · ❌ version calculée depuis l'historique (`git describe`, changelog) : `git_clone_depth = 0` (clone complet).

```hcl
# Exemple 1 : le code à construire
source {
  type = "CODECOMMIT"
  location = (data.aws_codecommit_repository
  .this.clone_url_http)
  git_clone_depth = 1
  buildspec       = "buildspec.yml"
}
```

- Quiz : Dans ce build, que renvoie `git log --oneline | wc -l` ?
- [ ] Le nombre total de commits de `main`
- [x] `1`
- [ ] `0` : le dossier n'est pas un dépôt git
- [ ] Une erreur `shallow repository`
- Réponse : `1` : `git_clone_depth = 1` ne récupère que le dernier commit ; `git log` fonctionne mais ne voit que lui.

## 2. environment : la machine de build
- Id : codebuild-environment-machine
- Sous-thème : projet
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : codebuild-runtime-versions-cout
- Définition : Le bloc `environment` choisit le conteneur du build : type, taille (`compute_type`) et image fournie par AWS avec ses runtimes.
- Contexte : `aws/codebuild/standard:7.0` est une image Ubuntu maintenue par AWS, avec Node, Python, Docker et la CLI AWS préinstallés : rien à construire soi-même (≈ `image:` d'un job GitLab). `BUILD_GENERAL1_SMALL` donne 3 Go de RAM et 2 vCPU, assez pour un build Vite. Le conteneur est neuf à chaque build : rien ne persiste d'un build à l'autre sans cache explicite.
- Usage : ✅ image `standard` pour un build Node ou Python classique · ❌ outils exotiques installés à chaque build : image Docker personnalisée dans ECR.

```hcl
# Exemple 1 : petit conteneur Linux
environment {
  type         = "LINUX_CONTAINER"
  compute_type = "BUILD_GENERAL1_SMALL"
  image  = "aws/codebuild/standard:7.0"
}
# small : 3 Go RAM, 2 vCPU
```

- Quiz : On passe en `BUILD_GENERAL1_MEDIUM` pour accélérer : les 100 minutes gratuites par mois s'appliquent-elles encore ?
- [ ] Oui, divisées par deux
- [ ] Oui, comme en small
- [x] Non : medium est facturé dès la 1re minute
- [ ] Non : medium exige une image ARM
- Réponse : non : l'offre gratuite ne couvre que `general1.small` et `arm1.small` ; une autre taille est payée dès la première minute.

## 3. buildspec : les phases
- Id : codebuild-buildspec-phases
- Sous-thème : buildspec
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : codebuild-post-build-deploiement, codebuild-finally
- Définition : `buildspec.yml` décrit le build en phases ordonnées (`install`, `pre_build`, `build`, `post_build`), chacune une liste de commandes shell.
- Contexte : Une commande en échec arrête sa phase et passe le build en `FAILED` : `make deploy` placé après `make test lint` ne part jamais si les tests cassent. `runtime-versions` choisit la version de Node fournie par l'image. Les phases ne sont pas toutes équivalentes en cas d'échec : la suite dépend de la phase qui a échoué.
- Usage : ✅ `install` pour l'outillage, `build` pour tester puis déployer · ❌ logique longue dans le YAML : la mettre dans le Makefile, exécutable aussi en local.

```yaml
# Exemple 1 : install puis build
version: 0.2
phases:
  install:
    runtime-versions:
      nodejs: 22
    commands:
      - make install
  build:
    commands:
      - make test lint
      - make deploy PROFILE=
```

- Quiz : `make install` échoue dans la phase `install` : la phase `post_build` s'exécute-t-elle ?
- [ ] Oui, `post_build` s'exécute toujours
- [ ] Oui, mais sans les variables d'environnement
- [ ] Non, mais `build` s'exécute quand même
- [x] Non : le build passe directement en `FINALIZING`
- Réponse : non : observé sur le 1er build du projet, `INSTALL` en échec enchaîne sur `FINALIZING` ; seul un échec de `build` laisse `post_build` tourner.

## 4. artifacts : NO_ARTIFACTS
- Id : codebuild-no-artifacts
- Sous-thème : projet
- Type : concept
- Niveau : 1
- Profils : ops
- Définition : `NO_ARTIFACTS` dit à CodeBuild de ne rien téléverser en fin de build : le buildspec publie lui-même dans S3 via `make deploy`.
- Contexte : Par défaut, CodeBuild sait copier des fichiers produits vers S3 (phase `UPLOAD_ARTIFACTS`), pour un artefact destiné à une étape suivante. Ici le déploiement est déjà fait par le Makefile pendant `build`, avec ses propres options d'envoi : un artefact ferait doublon. Le bloc `artifacts` reste obligatoire dans la ressource, même vide de sens.
- Usage : ✅ build qui déploie lui-même (`s3 sync`, `terraform apply`) · ❌ artefact consommé par une autre étape (CodePipeline, Lambda) : `type = "S3"`.

```hcl
# Exemple 1 : rien à téléverser
artifacts {
  type = "NO_ARTIFACTS"
}
# le build publie déjà :
# make deploy → aws s3 sync app/dist/
#   s3://$SITE_BUCKET/ --delete
```

- Quiz : Artefact `type = "S3"` vers le bucket site, ou `make deploy` : lequel pose un `Cache-Control` différent par fichier ?
- [ ] L'artefact S3, via `packaging = "ZIP"`
- [x] `make deploy`
- [ ] Les deux, via `encryption_disabled`
- [ ] Aucun : c'est CloudFront qui le pose
- Réponse : `make deploy` : l'artefact CodeBuild copie tout tel quel, le Makefile met `immutable` sur `assets/` et `no-cache` sur `index.html`.

## 5. logs : suivre un build en direct
- Id : codebuild-suivre-logs
- Sous-thème : logs
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Définition : `aws logs tail --follow` affiche en continu dans le terminal les logs du build, lus dans le groupe `/aws/codebuild/<projet>`.
- Contexte : Chaque build écrit dans un flux nommé par la partie de son ID après `:` (mesuré). `batch-get-builds` donne ensuite le statut final : `SUCCEEDED`, `FAILED` (une commande a échoué), `FAULT` (erreur de CodeBuild), `TIMED_OUT` ou `STOPPED`. Son champ `initiator` dit qui a lancé le build : `rule/revision-pwa-dev-push-main` pour la règle EventBridge (mesuré).
- Usage : ✅ suivre un déploiement juste après un push, lire l'erreur exacte · ❌ rafraîchir la console : `batch-get-builds` pour statut et durées par phase.

```bash
# Exemple 1 : suivre le build en cours
aws logs tail --follow --since 5m \
  /aws/codebuild/revision-pwa-dev-deploy
# → [Container] … Entering phase INSTALL
#   [Container] … Running command make install
```

```bash
# Exemple 2 : statut et déclencheur (mesuré)
aws codebuild batch-get-builds \
  --ids "$BUILD_ID" --query \
  'builds[0].[buildStatus,initiator]'
# → SUCCEEDED
#   rule/revision-pwa-dev-push-main
```

- Quiz : Le build `revision-pwa-dev-deploy:7f3c…` : dans quel flux du groupe écrit-il ses logs ?
- [ ] `revision-pwa-dev-deploy:7f3c…`
- [x] `7f3c…`, la partie de l'ID après `:`
- [ ] `build-3`, d'après son numéro
- [ ] Un flux unique partagé par tous les builds
- Réponse : `7f3c…` (mesuré) : le flux porte la partie de l'ID après `:`, le nom du projet étant déjà dans celui du groupe ; d'où `--log-stream-names` pour isoler un build.

## 6. logs : groupe créé par Terraform
- Id : codebuild-log-group-terraform
- Sous-thème : logs
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : codebuild-suivre-logs
- Voir aussi : lambda-log-group-avant-fonction
- Définition : Terraform crée le groupe de logs du build avec une rétention ; le rôle n'a que `CreateLogStream` et `PutLogEvents` dessus.
- Contexte : Chaque build écrit dans un flux (stream) nommé par son ID, dans le groupe `/aws/codebuild/<projet>`. Créer le groupe soi-même permet de fixer `retention_in_days` (14 ici, mesuré sur le compte) et de retirer `logs:CreateLogGroup` du rôle. L'ARN d'un groupe suivi de `:*` couvre ses flux, ce que demande `CreateLogStream`.
- Usage : ✅ groupe de logs déclaré en Terraform pour tout CodeBuild ou Lambda · ❌ laisser le service créer le groupe : rétention illimitée et droit de création en plus.

```hcl
# Exemple 1 : groupe à rétention fixe
resource "aws_cloudwatch_log_group" "deploy" {
  name = "/aws/codebuild/${local.prefix}-deploy"
  retention_in_days = 14
}
```

```hcl
# Exemple 2 : écrire, pas créer
statement {
  actions = ["logs:CreateLogStream",
  "logs:PutLogEvents"]
  resources = [
    "${aws_cloudwatch_log_group.deploy.arn}:*"
  ]
}
```

- Quiz : Sans la ressource `aws_cloudwatch_log_group`, le groupe créé automatiquement garde les logs combien de temps ?
- [ ] 14 jours, comme le build
- [ ] 30 jours, le défaut CloudWatch
- [x] Indéfiniment
- [ ] Jusqu'à la fin du build
- Réponse : indéfiniment : un groupe créé sans rétention n'expire jamais ; les logs s'accumulent et se paient à vie.

## 7. environment_variable : PLAINTEXT par défaut
- Id : codebuild-variables-plaintext
- Sous-thème : projet
- Type : piège
- Niveau : 2
- Profils : ops
- Définition : `environment_variable` injecte des valeurs Terraform (bucket, ID de distribution) dans le build, lues par le Makefile comme des variables shell.
- Contexte : Le Makefile déclare `SITE_BUCKET ?= $(shell terraform output …)` : en local, il lit l'output ; en CI, la variable du projet est déjà définie et `?=` la garde, sans `terraform` dans le conteneur. Le type par défaut est `PLAINTEXT` (mesuré sur le projet) : la valeur est stockée en clair dans la définition du projet.
- Usage : ✅ noms et ID non sensibles (bucket, distribution) · ❌ secret (jeton d'API) en clair : `type = "PARAMETER_STORE"` ou `"SECRETS_MANAGER"`, droit de lecture au rôle.

```hcl
# Exemple 1 : nom du bucket pour make
environment_variable {
  name  = "SITE_BUCKET"
  value = aws_s3_bucket.this["site"].bucket
}
# dans le build :
# echo $SITE_BUCKET
# → revision-pwa-dev-site-<account_id>
```

```hcl
# Exemple 2 : un secret, par référence
environment_variable {
  name  = "API_TOKEN"
  type  = "PARAMETER_STORE"
  value = "/revision-pwa/dev/api-token"
}
# value = nom du paramètre, pas le secret
```

- Quiz : Un jeton d'API passé en `environment_variable` sans `type` : qui peut le lire ?
- [ ] Personne : CodeBuild masque toute variable
- [x] Quiconque a `codebuild:BatchGetProjects`
- [ ] Seulement le rôle de service du build
- [ ] Seulement l'utilisateur racine du compte
- Réponse : quiconque a `BatchGetProjects` (ou la console) : en `PLAINTEXT`, la valeur est rendue telle quelle dans la définition du projet.

## 8. build_timeout : couper un build bloqué
- Id : codebuild-build-timeout
- Sous-thème : projet
- Type : concept
- Niveau : 2
- Profils : ops
- Définition : `build_timeout` (en minutes) arrête un build qui dépasse la durée fixée : ici 15 min, pour un build mesuré à moins de 2 min.
- Contexte : Sans l'attribut, CodeBuild attend 60 minutes avant d'arrêter un build. Un test qui attend un réseau absent ou une commande interactive bloquée consommerait alors une heure de calcul. Le build arrêté passe en `TIMED_OUT`. Un second délai, `queued_timeout` (480 min par défaut, mesuré), borne l'attente en file avant démarrage.
- Usage : ✅ plafond à quelques fois la durée normale, sur toute CI payée à la minute · ❌ plafond trop serré : un build lent mais sain échoue au hasard.

```hcl
# Exemple 1 : plafond à 15 minutes
resource "aws_codebuild_project" "deploy" {
  build_timeout = 15 # minutes
}
# test bloqué sur un réseau absent
# → arrêt à 15 min : TIMED_OUT
```

- Quiz : Sur l'offre gratuite (100 min/mois), pourquoi ne pas garder le délai par défaut ?
- [x] Un build bloqué brûlerait 60 des 100 minutes
- [ ] Le défaut est illimité : le build ne s'arrête jamais
- [ ] Le défaut de 5 min couperait les builds normaux
- [ ] L'offre gratuite impose `build_timeout` au plus à 15
- Réponse : un build bloqué brûlerait 60 minutes : le défaut est de 60 ; 15 min plafonne la perte à 15 % du mois.

## 9. post_build : le piège du déploiement
- Id : codebuild-post-build-deploiement
- Sous-thème : buildspec
- Type : piège
- Niveau : 2
- Profils : ops
- Définition : La phase `post_build` s'exécute même quand `build` a échoué : on y met nettoyage ou notification, jamais un déploiement.
- Contexte : CodeBuild enchaîne `build` → `post_build` quel que soit le résultat de `build`, pour permettre un rapport ou un nettoyage. La variable `CODEBUILD_BUILD_SUCCEEDING` (`1` ou `0`) dit si tout a réussi jusque-là. Le buildspec du projet garde `make deploy` dans `build`, juste après les tests, pour hériter de l'arrêt à la première erreur.
- Usage : ✅ `post_build` pour notifier ou publier un rapport de tests · ❌ déployer en `post_build` : on publierait un code qui casse les tests.

```yaml
# Exemple 1 : à ne pas faire
phases:
  build:
    commands:
      - make test lint
  post_build:
    commands:
      # s'exécute même si les
      # tests ont échoué
      - make deploy PROFILE=
```

- Quiz : Quelle clé fait sauter `post_build` quand `build` échoue ?
- [ ] `on-failure: CONTINUE` dans `post_build`
- [ ] `finally:` sous `build`
- [ ] `exit-on-error: true` sous `env`
- [x] `on-failure: ABORT` sous `build`
- Réponse : `on-failure: ABORT` sous la phase `build` : le build s'arrête là au lieu d'enchaîner sur `post_build` (`CONTINUE` fait l'inverse).

## 10. commandes : un seul shell, sh
- Id : codebuild-shell-sh-partage
- Sous-thème : buildspec
- Type : piège
- Niveau : 2
- Profils : ops
- Définition : En `version: 0.2`, toutes les commandes du buildspec tournent dans la même instance du shell : un `cd` ou un `export` vaut pour les suivantes.
- Contexte : En `0.1`, chaque commande avait son propre shell, d'où les `cd x && …` des vieux buildspecs. Le shell par défaut est `sh` (doc AWS) : sur l'image Ubuntu, c'est `dash`, sans les extensions de bash. `env.shell: bash` change le shell de tout le buildspec. Le build démarre à la racine du dépôt, `CODEBUILD_SRC_DIR`.
- Usage : ✅ `version: 0.2`, `shell: bash` dès qu'une commande utilise une syntaxe bash · ❌ logique shell longue dans le YAML : la mettre dans le Makefile ou un script versionné.

```yaml
# Exemple 1 : l'état passe d'une commande à l'autre
version: 0.2
phases:
  build:
    commands:
      - cd app
      - export MODE=production
      - pnpm build  # dans app/, MODE défini
```

```yaml
# Exemple 2 : passer en bash
version: 0.2
env:
  shell: bash
phases:
  build:
    commands:
      - source ci/env.sh  # bash : OK
```

- Quiz : Sans `env.shell`, que donne la commande `[[ "$CODEBUILD_BUILD_SUCCEEDING" == 1 ]] && make notify` ?
- [ ] `make notify` si le build réussit
- [x] Une erreur `[[: not found`
- [ ] Rien : la condition est toujours fausse
- [ ] Une erreur de syntaxe YAML
- Réponse : `[[: not found` : `[[` est une extension de bash, absente de `sh` ; écrire `[ "$X" = 1 ]` ou passer `shell: bash` (doc AWS).

## 11. CODEBUILD_* : le contexte du build
- Id : codebuild-variables-codebuild
- Sous-thème : buildspec
- Type : concept
- Niveau : 2
- Profils : ops
- Voir aussi : codebuild-source-version-tete
- Définition : CodeBuild injecte des variables `CODEBUILD_*` dans chaque build : commit construit, numéro et ID du build, dossier source, déclencheur.
- Contexte : `CODEBUILD_RESOLVED_SOURCE_VERSION` donne le commit réellement cloné, disponible après `DOWNLOAD_SOURCE`. `CODEBUILD_BUILD_NUMBER` s'incrémente à chaque build du projet (3 builds ici). `CODEBUILD_SRC_DIR` vaut `/codebuild/output/src…/src/git-codecommit…/revision-pwa` (mesuré). `CODEBUILD_INITIATOR` donne le lanceur. Le préfixe `CODEBUILD_` est réservé : n'en définir aucune soi-même.
- Usage : ✅ écrire la version déployée dans le site (`version.json`), nommer un artefact · ❌ `git describe` sur un clone superficiel : pas d'historique, la variable suffit.

```yaml
# Exemple 1 : tracer le commit déployé
build:
  commands:
    - make build
    - >-
      printf '{"commit":"%s","build":%s}'
      "$CODEBUILD_RESOLVED_SOURCE_VERSION"
      "$CODEBUILD_BUILD_NUMBER"
      > app/dist/version.json
# → {"commit":"91e9e1a…","build":3}
```

- Quiz : Dans un build lancé par la règle EventBridge, que contient `CODEBUILD_SOURCE_VERSION` (sans `RESOLVED`) ?
- [ ] Le SHA du commit poussé
- [x] `refs/heads/main`
- [ ] Une chaîne vide
- [ ] `main`
- Réponse : `refs/heads/main` : c'est la référence demandée (`source_version` du projet) ; seul `CODEBUILD_RESOLVED_SOURCE_VERSION` donne le SHA cloné.

## 12. cache : S3 ou LOCAL
- Id : codebuild-cache-s3-local
- Sous-thème : buildspec
- Type : concept
- Niveau : 2
- Profils : ops
- Définition : Le cache CodeBuild garde des dossiers (store pnpm, `~/.cache/uv`) d'un build à l'autre, dans S3 ou sur l'hôte (`LOCAL`), listés sous `cache.paths`.
- Contexte : Le projet est en `NO_CACHE` (lu sur le compte) et le log dit `Skip cache due to: no paths specified to be cached` : chaque build retélécharge ses 494 paquets. `type = "S3"` archive les chemins en fin de build et les restaure au début : fiable, mais l'aller-retour prend du temps. `LOCAL` réutilise le disque d'un hôte encore chaud : gratuit, sans garantie.
- Usage : ✅ dépendances lourdes et stables (store pnpm, roues Python) · ❌ cache S3 pour gagner 4 s sur un build de 100 s : la minute facturée ne bouge pas.

```hcl
# Exemple 1 : où stocker (projet)
cache {
  type     = "S3"
  location = "data-platform-dev-ci-cache/codebuild"
}
```

```yaml
# Exemple 2 : quoi garder (buildspec)
cache:
  paths:
    - "/root/.local/share/pnpm/store/**/*"
# restauré avant install, sauvé à la fin
```

- Quiz : En `type = "LOCAL"`, quel mode garde un dossier choisi comme le store pnpm ?
- [ ] `LOCAL_SOURCE_CACHE`
- [ ] `LOCAL_DOCKER_LAYER_CACHE`
- [x] `LOCAL_CUSTOM_CACHE`
- [ ] `LOCAL_NODE_CACHE`
- Réponse : `LOCAL_CUSTOM_CACHE` : il garde les `cache.paths` du buildspec ; `SOURCE` garde le dépôt git, `DOCKER_LAYER` les couches d'images (doc AWS).

## 13. start-build : rejouer un commit
- Id : codebuild-start-build-rejouer
- Sous-thème : déclenchement
- Type : recette
- Niveau : 2
- Profils : ops
- Voir aussi : codebuild-source-version-tete
- Définition : `aws codebuild start-build` lance le projet à la main et peut surcharger, pour ce build seulement, le commit (`--source-version`) et des variables.
- Contexte : Rejouer un commit antérieur redéploie l'ancien site sans toucher à git : c'est le rollback le plus rapide de revision-pwa. La surcharge ne vaut que pour ce build, le projet ne change pas. Celui qui lance doit avoir `codebuild:StartBuild` ; le build tourne, lui, avec le rôle de service du projet.
- Usage : ✅ rollback vers un commit connu, essai d'une branche sans pousser sur main · ❌ changer `source_version` dans Terraform pour un essai : tous les builds suivants changent.

```bash
# Exemple 1 : redéployer un ancien commit
aws codebuild start-build \
  --project-name revision-pwa-dev-deploy \
  --source-version e6862e4c4976be36cbc32e03ed46055b81ea66eb
# → build.sourceVersion = e6862e4…
```

```bash
# Exemple 2 : surcharger une variable
aws codebuild start-build \
  --project-name revision-pwa-dev-deploy \
  --environment-variables-override \
  name=SITE_BUCKET,value=revision-pwa-test-site
```

- Quiz : `SITE_BUCKET` est défini dans le `env.variables` du buildspec et dans le projet Terraform : quelle valeur voit le build ?
- [ ] Celle du buildspec : le plus proche du code
- [x] Celle du projet
- [ ] La dernière modifiée des deux
- [ ] Aucune : le build échoue sur le doublon
- Réponse : celle du projet : priorité `start-build` > projet > buildspec (doc AWS) ; le buildspec ne donne qu'une valeur par défaut.

## 14. webhook : GitHub ou GitLab
- Id : codebuild-webhook-filtres
- Sous-thème : déclenchement
- Type : concept
- Niveau : 2
- Profils : ops
- Voir aussi : sqs-eventbridge-event-target
- Définition : `aws_codebuild_webhook` lance le build sur un événement d'un dépôt GitHub, GitLab ou Bitbucket, filtré par groupes (`EVENT`, `HEAD_REF`, `FILE_PATH`).
- Contexte : Dans un groupe, tous les filtres doivent matcher (ET) ; un seul groupe vrai suffit (OU). Les motifs sont des regex RE2, à ancrer : `^refs/heads/main$`. `FILE_PATH` filtre sur les fichiers modifiés, ce que l'événement CodeCommit d'EventBridge ne permet pas. CodeCommit n'a pas de webhook CodeBuild : revision-pwa passe par une règle EventBridge.
- Usage : ✅ dépôt GitHub ou GitLab, build seulement quand `infra/` change · ❌ dépôt CodeCommit : règle EventBridge ; GitLab CI déjà en place : garder `.gitlab-ci.yml`.

```hcl
# Exemple 1 : push sur main touchant infra/
resource "aws_codebuild_webhook" "w" {
  project_name = aws_codebuild_project.d.name
  filter_group {
    filter {
      type    = "EVENT"
      pattern = "PUSH"
    }
    filter {
      type    = "HEAD_REF"
      pattern = "^refs/heads/main$"
    }
    filter {
      type    = "FILE_PATH"
      pattern = "^infra/"
    }
  }
}
```

- Quiz : Un push sur main modifie `app/a.ts`, `app/b.ts` et `infra/cdn.tf` : le build part-il ?
- [x] Oui : un fichier qui matche suffit
- [ ] Non : tous les fichiers doivent matcher
- [ ] Non : `FILE_PATH` exige un seul fichier modifié
- [ ] Oui, trois fois, une par fichier
- Réponse : oui, une fois : `FILE_PATH` est vrai dès qu'un fichier modifié matche (parmi les 100 premiers, doc AWS).

## 15. privileged_mode : docker build
- Id : codebuild-privileged-mode-docker
- Sous-thème : projet
- Type : concept
- Niveau : 2
- Profils : ops
- Définition : `privileged_mode = true` donne au conteneur de build l'accès au démon Docker : requis pour `docker build` d'une image Lambda ou ECS.
- Contexte : Sans ce mode, `docker build` échoue avec `Cannot connect to the Docker daemon`. Le mode élargit les droits du conteneur sur l'hôte : à réserver aux projets qui construisent des images. revision-pwa est à `false` (lu sur le compte) : il ne fait que du Node et de la CLI AWS. L'image se pousse ensuite dans ECR, avec des droits limités au dépôt.
- Usage : ✅ build d'images (Lambda en conteneur, Fargate) · ❌ projet sans Docker : laisser `false`, moins de surface d'attaque.

```hcl
# Exemple 1 : accès au démon Docker
environment {
  type            = "LINUX_CONTAINER"
  compute_type    = "BUILD_GENERAL1_SMALL"
  image           = "aws/codebuild/standard:7.0"
  privileged_mode = true
}
```

```yaml
# Exemple 2 : construire et pousser
build:
  commands:
    - aws ecr get-login-password |
      docker login --username AWS
      --password-stdin "$REGISTRY"
    - docker build -t "$REGISTRY/ocr:$TAG" .
    - docker push "$REGISTRY/ocr:$TAG"
```

- Quiz : `docker login` vers ECR échoue en `AccessDenied` alors que le rôle a `ecr:*` sur le dépôt : quel droit manque ?
- [ ] `ecr:BatchGetImage` sur le dépôt
- [x] `ecr:GetAuthorizationToken` sur `*`
- [ ] `sts:AssumeRole` sur ECR
- [ ] `iam:PassRole` sur le rôle de service
- Réponse : `ecr:GetAuthorizationToken` sur `*` : le jeton vaut pour tout le registre, l'action ne se borne pas à un dépôt ; un `ecr:*` limité à l'ARN du dépôt ne la couvre pas.

## 16. depends_on : la politique avant le projet
- Id : codebuild-depends-on-politique
- Sous-thème : projet
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : iam-role-de-service-ci
- Voir aussi : lambda-depends-on-droits
- Définition : `depends_on` force un ordre que les références ne montrent pas : le projet référence le rôle, mais pas la politique qui lui donne ses droits.
- Contexte : Terraform ordonne par références : le projet cite `aws_iam_role.deploy.arn`, donc le rôle est créé avant, mais rien ne relie le projet à `aws_iam_role_policy.deploy`. Les deux seraient créés en parallèle, et un build lancé aussitôt tournerait sans droits. `depends_on` ajoute l'arête manquante, valable aussi à la destruction, dans l'ordre inverse.
- Usage : ✅ dépendance réelle sans référence (politique, attachement, blocage d'accès public) · ❌ dépendance déjà exprimée par une référence : bruit qui masque le vrai graphe.

```hcl
# Exemple 1 : arête ajoutée au graphe
resource "aws_codebuild_project" "deploy" {
  service_role = aws_iam_role.deploy.arn
  depends_on = [
    aws_iam_role_policy.deploy
  ]
}
# rôle → politique → projet
```

- Quiz : Au `destroy`, dans quel ordre partent le projet et la politique `deploy` ?
- [ ] La politique d'abord, puis le projet
- [ ] En parallèle : `depends_on` ne joue qu'à la création
- [x] Le projet d'abord, puis la politique
- [ ] Dans l'ordre alphabétique des adresses
- Réponse : le projet d'abord : Terraform détruit dans l'ordre inverse du graphe, donc un build ne perd jamais ses droits pendant que le projet existe.

## 17. source_version : quel commit est construit
- Id : codebuild-source-version-tete
- Sous-thème : projet
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Définition : `source_version` fixe la référence construite quand le build démarre sans révision précise, ce que fait la cible EventBridge.
- Contexte : La cible EventBridge appelle `StartBuild` sans commit : le build clone `refs/heads/main` tel qu'il est au démarrage, pas le commit qui a déclenché l'événement. Le commit réellement construit est noté dans `resolvedSourceVersion`. Deux pushs rapprochés peuvent donc produire deux builds du même dernier commit.
- Usage : ✅ déploiement continu « la tête de main gagne », sans ordre à garantir · ❌ build qui doit construire chaque commit : passer `sourceVersion` à `StartBuild` (transformateur d'entrée) ou CodePipeline.

```bash
# Exemple 1 : demandé vs construit
aws codebuild batch-get-builds \
  --ids "$BUILD_ID" --query \
  'builds[0].[sourceVersion,
   resolvedSourceVersion]'
# → refs/heads/main
#   e6862e4c4976be36cbc32e03ed46055b81ea66eb
```

- Quiz : Push A à 10:00:00, push B à 10:00:20, les deux builds clonent après 10:00:20 : A a-t-il été déployé seul ?
- [ ] Oui, par le 1er build
- [x] Non : les deux builds construisent B
- [ ] Oui, puis B l'écrase 20 s plus tard
- [ ] Non : le 2e build annule le 1er
- Réponse : non : chaque build clone la tête de `main` à son démarrage ; A n'est jamais construit isolément, B l'est deux fois.

## 18. Corepack : la version de pnpm
- Id : codebuild-corepack-pnpm
- Sous-thème : buildspec
- Type : piège
- Niveau : 3
- Profils : web, ops, expert
- Définition : Corepack fournit le gestionnaire de paquets demandé par `packageManager` du `package.json`, au lieu d'un pnpm global de version imprévisible.
- Contexte : Corepack lit le `package.json` du dossier courant. Le buildspec tourne à la racine, sans `package.json` : Corepack a pris la dernière version (pnpm 12.15.0), puis `pnpm --dir app install` l'a refusée car `app/` exige `pnpm@10.33.0`. C'est l'échec mesuré du 1er build, en `ERR_PNPM_BAD_PM_VERSION`. Correctif : installer en global la version lue dans `app/package.json`.
- Usage : ✅ épingler pnpm via `packageManager` et `corepack install -g` en CI · ❌ `npm i -g pnpm` sans version : la CI change d'outil le jour d'une sortie majeure.

```yaml
# Exemple 1 : la version de app/
install:
  commands:
    - corepack enable
    - corepack install -g "$(node -p
        "require('./app/package.json')
        .packageManager")"
    - pnpm --version
      # → 10.33.0
```

- Quiz : Avec seulement `corepack enable`, pourquoi `pnpm --dir app install` tourne-t-il en pnpm 12 ?
- [ ] `--dir` est ignoré par Corepack
- [x] Corepack lit le dossier courant, la racine sans `package.json`
- [ ] L'image `standard:7.0` embarque pnpm 12
- [ ] `nodejs: 22` impose pnpm 12
- Réponse : Corepack lit le dossier courant : à la racine, aucun `packageManager`, il prend la dernière version ; `--dir` n'agit qu'une fois pnpm lancé.

## 19. runtime-versions : la minute cachée
- Id : codebuild-runtime-versions-cout
- Sous-thème : buildspec
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Voir aussi : codebuild-minutes-arrondies
- Définition : `runtime-versions` choisit la version d'un langage dans l'image ; si ce n'est pas celle active par défaut, CodeBuild l'installe à chaque build.
- Contexte : Mesuré sur le projet : `nodejs: 22` lance `n $NODE_22_VERSION`, qui prend environ 56 s, sur un build d'environ 100 s. Ce temps n'apparaît pas dans la phase `INSTALL` (5 s) : la console le range dans `DOWNLOAD_SOURCE` (65 s). Optimiser `make install` ne gagne donc presque rien ; le levier est l'image ou la version de Node.
- Usage : ✅ lire les horodatages des logs avant d'optimiser un build · ❌ se fier à la seule durée des phases : `INSTALL` ne compte pas l'installation du runtime.

```bash
# Exemple 1 : logs du build (extrait)
# 15:43:16 Running command
#   n $NODE_22_VERSION
# 15:44:12 Moving to directory …
# 15:44:12 Running command
#   corepack enable
# → 56 s pour installer Node 22
```

```bash
# Exemple 2 : durée par phase
aws codebuild batch-get-builds \
  --ids "$BUILD_ID" --query \
  'builds[0].phases[].[phaseType,
   durationInSeconds]'
# → DOWNLOAD_SOURCE 65
#   INSTALL 5 · BUILD 23
```

- Quiz : On met `make install` en cache et il passe de 5 s à 1 s : combien de minutes facturées gagne chaque build de 100 s ?
- [ ] 1 minute
- [ ] Une fraction de minute
- [x] 0
- [ ] 4 minutes
- Réponse : 0 : 96 s s'arrondissent encore à 2 minutes ; il faudrait passer sous 60 s, donc s'attaquer aux 56 s du runtime.

## 20. offre gratuite : minutes arrondies
- Id : codebuild-minutes-arrondies
- Sous-thème : coûts
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Voir aussi : couts-cout-au-repos
- Définition : Un build CodeBuild se paie à la minute entamée ; l'offre gratuite (100 min/mois en small) borne donc le nombre de déploiements gratuits.
- Contexte : Chaque build est arrondi à la minute supérieure, séparément : 61 s coûtent 2 minutes. Le build mesuré dure environ 100 s, soit 2 minutes facturées et 50 déploiements gratuits par mois. Quelques secondes au-dessus d'un multiple de 60 coûtent une minute entière à chaque build, d'où l'intérêt de connaître la durée réelle.
- Usage : ✅ estimer le budget de CI depuis la durée réelle des builds · ❌ raisonner sur la durée moyenne cumulée : l'arrondi s'applique build par build.

```bash
# Exemple 1 : builds gratuits par mois
s=100                    # durée (s)
m=$(( (s + 59) / 60 ))   # arrondi sup.
echo $m $(( 100 / m ))
# → 2 50
```

```bash
# Exemple 2 : l'effet de seuil
for s in 60 61 125; do
  m=$(( (s + 59) / 60 ))
  echo "$s s → $(( 100 / m ))"
done
# → 60 s → 100
#   61 s → 50
#   125 s → 33
```

- Quiz : Un `make install` sans cache fait passer le build à 3 min 05 s : combien de builds gratuits par mois ?
- [ ] `33`
- [ ] `32`
- [x] `25`
- [ ] `30`
- Réponse : `25` : 185 s s'arrondissent à 4 minutes, et 100 // 4 = 25 ; 5 secondes de trop coûtent une minute par build.

## 21. vpc_config : Internet par un NAT
- Id : codebuild-vpc-config-nat
- Sous-thème : projet
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Voir aussi : couts-nat-gateway-endpoint
- Définition : `vpc_config` place le conteneur de build dans des sous-réseaux d'un VPC pour joindre une ressource privée (base, API interne).
- Contexte : Dans un VPC, le build sort par le routage du sous-réseau : sans NAT Gateway ni endpoints VPC (S3, ECR, logs), `pnpm install`, l'envoi des logs et les appels AWS échouent par timeout. Le NAT se paie à l'heure, environ 36 $/mois à Paris avant trafic : un coût fixe qui dépasse vite un CodeBuild gratuit.
- Usage : ✅ tests d'intégration contre une base RDS privée, migrations · ❌ build qui n'appelle que S3 et CloudFront : hors VPC, sans NAT à payer.

```hcl
# Exemple 1 : build dans le VPC
vpc_config {
  vpc_id             = "vpc-0abc"
  subnets            = ["subnet-0priv"] # route 0.0.0.0/0 → NAT
  security_group_ids = ["sg-0ci"]
}
# + rôle : ec2:CreateNetworkInterface, …
```

- Quiz : Le build est placé dans un sous-réseau public (route vers l'Internet Gateway), sans NAT : `pnpm install` passe-t-il ?
- [ ] Oui : le sous-réseau est public
- [ ] Oui, si le groupe de sécurité ouvre le 443 en sortie
- [x] Non : CodeBuild ne donne pas d'IP publique à son interface
- [ ] Non : CodeBuild refuse les sous-réseaux publics
- Réponse : non : l'interface réseau du build n'a qu'une IP privée, l'Internet Gateway ne la route pas ; il faut un sous-réseau privé avec NAT (doc AWS).

## 22. finally : nettoyer même en échec
- Id : codebuild-finally
- Sous-thème : buildspec
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Prérequis : codebuild-post-build-deploiement
- Définition : Le bloc `finally` d'une phase s'exécute après ses `commands`, même si l'une a échoué : nettoyage ou rapport, sans sauver la phase.
- Contexte : Une commande en échec saute les suivantes de `commands`, puis `finally` tourne. La phase ne réussit que si `commands` et `finally` réussissent tous les deux (doc AWS). Contrairement à `post_build`, `finally` reste dans sa phase : il marche aussi pour `install`, après lequel un échec saute `build` et `post_build`.
- Usage : ✅ effacer un fichier de secrets, publier un rapport de tests partiel · ❌ déployer dans `finally` : il tourne justement quand les tests cassent.

```yaml
# Exemple 1 : rapport même si les tests cassent
build:
  commands:
    - make test       # échoue
    - make deploy     # sautée
  finally:
    - make coverage-report  # exécutée
```

- Quiz : `make test` échoue, puis la commande de `finally` réussit : quel est l'état de la phase `build` ?
- [ ] `SUCCEEDED` : `finally` a réussi
- [x] `FAILED`
- [ ] `SUCCEEDED`, avec un avertissement
- [ ] `STOPPED`
- Réponse : `FAILED` : `finally` ne rattrape pas l'échec ; la phase n'est réussie que si toutes ses commandes, `finally` compris, réussissent.
