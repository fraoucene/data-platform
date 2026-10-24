---
title: "Cartes · CI-CD"
type: cartes
langage: DevOps
cours: CI-CD
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · CI-CD
DevOps · CI-CD : chaîne, déclencheurs, dépendances, secrets, déploiement (format spec v3 de revision-pwa).

## 1. chaîne CI : du push au déploiement
- Sous-thème : chaîne
- Niveau : 1
- Définition : Un push sur `main` émet un événement CodeCommit ; EventBridge le filtre et lance CodeBuild, qui exécute `buildspec.yml` puis `make deploy`.
- Contexte : Aucun serveur de CI à maintenir (≈ GitLab CI sans runner) : chaque maillon est un service managé, branché par Terraform. EventBridge n'est qu'un déclencheur, le projet CodeBuild existe seul et se lance aussi à la main. Le build ne fait qu'appeler le Makefile : `make deploy` en local et en CI exécutent les mêmes commandes, ce qui rend la CI reproductible sur le poste.
- Usage : ✅ dépôt CodeCommit, déploiement simple d'un site statique ou d'une Lambda, coût quasi nul · ❌ pipeline multi-étapes avec validations manuelles : CodePipeline ou GitLab CI.

```bash
# Exemple 1 : la chaîne
git push origin main
# 1. CodeCommit : referenceUpdated
# 2. EventBridge : règle push-main
# 3. CodeBuild : buildspec.yml
# 4. make deploy → S3 + CloudFront
```

```bash
# Exemple 2 : qui a lancé le build ?
aws codebuild batch-get-builds \
  --ids "$BUILD_ID" --query \
  'builds[0].[initiator,buildStatus]'
# → rule/revision-pwa-dev-push-main
#   SUCCEEDED
```

- Quiz : Comment relancer un déploiement sans créer de nouveau commit ?
- [ ] `git push --force origin main`
- [ ] `aws events put-events` avec un faux push
- [x] `aws codebuild start-build --project-name …`
- [ ] Impossible : seul EventBridge lance le projet
- Réponse : `start-build` : un push sans nouveau commit ne change aucune référence, donc n'émet aucun événement ; le projet se lance directement.

## 2. stages : build, test, deploy
- Sous-thème : chaîne
- Niveau : 1
- Définition : Un pipeline enchaîne des étapes (`stages`) : tous les jobs d'une étape tournent en parallèle, l'étape suivante ne démarre que s'ils ont tous réussi.
- Contexte : L'ordre classique `build` → `test` → `deploy` fait du déploiement la récompense d'un build et de tests verts : un test rouge arrête le pipeline avant la prod. C'est le `buildspec.yml` de CodeBuild découpé en jobs isolés, chacun dans un conteneur neuf, relançable seul. Un job échoue dès qu'une commande de `script` sort avec un code non nul.
- Usage : ✅ étapes courtes et ordonnées : lint et tests avant tout déploiement · ❌ tout dans un seul job géant : impossible de relancer seulement l'étape cassée.

```yaml
# Exemple 1 : .gitlab-ci.yml
stages: [build, test, deploy]
build:
  stage: build
  script: [make build]
test:
  stage: test
  script: [make test]
deploy:
  stage: deploy
  script: [make deploy]
# test rouge → deploy ne part pas
```

- Quiz : L'étape `test` contient deux jobs, `lint` et `test` : `lint` échoue en 5 s. Que devient `test` ?
- [ ] Annulé aussitôt
- [x] Il continue jusqu'au bout
- [ ] Il n'a jamais démarré
- [ ] Relancé automatiquement
- Réponse : il continue : les jobs d'une même étape tournent en parallèle et indépendamment ; c'est l'étape `deploy` qui ne démarrera pas (doc GitLab).

## 3. job GitLab : image, script, extends
- Sous-thème : chaîne
- Niveau : 1
- Définition : Dans `.gitlab-ci.yml`, toute clé de premier niveau qui n'est pas un mot réservé est un job : une `image` Docker, une `stage` et un `script`.
- Contexte : Le runner lance un conteneur de l'`image`, clone le dépôt, exécute `before_script` puis `script` ligne à ligne, arrêt à la première erreur. Les mots réservés (`stages`, `variables`, `default`, `workflow`, `include`) ne sont pas des jobs. `extends` réutilise un modèle : clés fusionnées, celles du job gagnent. Pas de runner à soi sur gitlab.com : runners partagés, facturés à la minute.
- Usage : ✅ un job par commande du Makefile, un modèle commun via `extends` · ❌ ancres YAML copiées partout : `extends` ou `default:`.

```yaml
# Exemple 1 : un job complet
test:
  image: python:3.13-slim
  stage: test
  before_script:
    - pip install uv
  script:
    - make test
```

```yaml
# Exemple 2 : un modèle réutilisé
.python:
  image: python:3.13-slim
  before_script: [pip install uv]
lint:
  extends: .python
  script: [make lint]
```

- Quiz : Dans l'exemple 2, combien de jobs le pipeline exécute-t-il ?
- [ ] 2 : `.python` et `lint`
- [x] 1 : `lint`
- [ ] 0 : `extends` exige `stage`
- [ ] 2 : `lint` est lancé deux fois
- Réponse : un seul : un nom qui commence par `.` est un job caché, jamais exécuté, qui ne sert que de modèle ; sans `stage`, `lint` prend `test` par défaut (doc GitLab).

## 4. GitHub Actions : workflow, jobs, steps
- Sous-thème : chaîne
- Niveau : 1
- Définition : Un workflow `.github/workflows/*.yml` déclare ses déclencheurs (`on`) et ses `jobs` ; chaque job tourne sur une VM (`runs-on`) et enchaîne des `steps`.
- Contexte : Un step est soit une commande (`run`), soit une action réutilisable (`uses: actions/checkout@v…`). Contrairement à GitLab, rien n'est cloné d'office : sans `actions/checkout`, le dossier de travail est vide. Pas de `stages` : l'ordre entre jobs se déclare avec `needs`. Les steps d'un job partagent la machine ; deux jobs, jamais.
- Usage : ✅ dépôt GitHub, actions officielles (`checkout`, `setup-node`, `configure-aws-credentials`) · ❌ action tierce non épinglée (`@main`) : épingler un tag, ou mieux un hash de commit.

```yaml
# Exemple 1 : ci.yml
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make test
```

- Quiz : Un workflow déclare `test` puis `deploy`, sans `needs` : si `test` échoue, `deploy` tourne-t-il ?
- [ ] Non : les jobs s'exécutent dans l'ordre du fichier
- [ ] Non : un job rouge annule le workflow
- [x] Oui : les deux démarrent en parallèle
- [ ] Oui, mais seulement après la fin de `test`
- Réponse : oui : sans `needs`, les jobs d'un workflow tournent en parallèle ; `needs: test` fait attendre `deploy` et le saute si `test` échoue (doc GitHub).

## 5. variables de CI : protégées et masquées
- Sous-thème : secrets
- Niveau : 1
- Définition : Un secret de CI vit dans les variables du projet, hors du dépôt : `protected` et `masked` sur GitLab, `secrets.NOM` sur GitHub.
- Contexte : Le YAML est commité : une valeur écrite dedans est publique pour qui lit le dépôt. La variable de projet est injectée au job comme variable d'environnement. `masked` remplace la valeur par `[MASKED]` dans les logs ; `protected` ne la donne qu'aux pipelines des branches et tags protégés (`main`, `v*`). Mieux encore pour AWS : pas de secret du tout, une identité OIDC.
- Usage : ✅ jeton d'API tiers protégé et masqué, réservé au job de déploiement · ❌ clé AWS en variable : rôle OIDC ; secret écrit dans `.gitlab-ci.yml`.

```yaml
# Exemple 1 : GitLab, variable de projet
# Settings > CI/CD > Variables :
#   INSEE_TOKEN  protected, masked
sync:
  script:
    - make sync  # lit $INSEE_TOKEN
# log : echo $INSEE_TOKEN → [MASKED]
```

```yaml
# Exemple 2 : GitHub, secret du dépôt
- run: make sync
  env:
    INSEE_TOKEN: ${{ secrets.INSEE_TOKEN }}
```

- Quiz : `INSEE_TOKEN` est `protected` : que vaut-il dans le pipeline de la branche `RLINK-123`, non protégée ?
- [ ] La valeur, masquée dans les logs
- [x] Vide : la variable n'est pas injectée
- [ ] `[MASKED]` en toutes lettres
- [ ] Le job échoue avant de démarrer
- Réponse : vide : une variable protégée n'est donnée qu'aux branches et tags protégés ; le job tourne sans elle (doc GitLab).

## 6. déclencheurs : quelle branche lance quoi
- Sous-thème : déclencheurs
- Niveau : 1
- Définition : Le déclencheur dit quels événements lancent le pipeline : `on: push` filtré par `branches` sur GitHub, `rules` sur `$CI_COMMIT_BRANCH` sur GitLab.
- Contexte : Sans filtre, chaque push sur chaque branche lance tout, déploiement compris. On sépare donc : tests sur toutes les branches et MR, déploiement sur `main` seulement. `paths` évite un pipeline quand seuls des fichiers sans rapport changent (`learning/`). Le filtre est l'équivalent de la règle EventBridge `push-main` de la chaîne CodeCommit.
- Usage : ✅ tests sur toute branche, deploy sur `main`, `paths` pour un monorepo · ❌ déploiement lancé sur toute branche : la prod suit la dernière branche poussée.

```yaml
# Exemple 1 : GitHub, main seulement
on:
  push:
    branches: [main]
    paths: ["app/**"]
```

```yaml
# Exemple 2 : GitLab, deploy sur main
deploy:
  script: [make deploy]
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

- Quiz : Avec l'exemple 1, on pousse le tag `v1.2.0` sur un commit de `main` : le workflow part-il ?
- [ ] Oui : le commit est sur `main`
- [ ] Oui : un tag déclenche toujours `push`
- [x] Non : seul `branches` est filtré
- [ ] Non : un tag n'est jamais un `push`
- Réponse : non : quand `on.push` ne définit que `branches`, les push de tags sont ignorés ; ajouter `tags: ["v*"]` pour les inclure (doc GitHub).

## 7. CI=true : le lockfile fait foi
- Sous-thème : dépendances
- Niveau : 2
- Définition : `CI: "true"` fait passer `pnpm install` en `--frozen-lockfile` : le build installe exactement le lockfile commité, ou échoue.
- Contexte : En local, `pnpm install` met à jour `pnpm-lock.yaml` si `package.json` a changé. En CI, pnpm détecte `CI` et refuse de le réécrire : les versions déployées sont celles relues en revue. Poser `CI` explicitement dans `env.variables` rend ce comportement indépendant de la détection automatique de la plateforme par pnpm.
- Usage : ✅ toute CI qui installe des dépendances (pnpm, npm `ci`, `uv sync --locked`) · ❌ installation qui modifie le lockfile en CI : build non reproductible.

```yaml
# Exemple 1 : variable du buildspec
env:
  variables:
    CI: "true"
# local : pnpm install
#   → met à jour pnpm-lock.yaml
# CI : pnpm install
#   → --frozen-lockfile implicite
```

- Quiz : On ajoute une dépendance dans `package.json` sans commiter le lockfile : que fait le build ?
- [x] Échoue : `ERR_PNPM_OUTDATED_LOCKFILE`
- [ ] Installe et réécrit le lockfile
- [ ] Ignore la nouvelle dépendance
- [ ] Installe la dernière version publiée
- Réponse : il échoue (`ERR_PNPM_OUTDATED_LOCKFILE`) : mieux vaut un build rouge qu'un déploiement avec des versions jamais vérifiées.

## 8. cache : clé sur le lockfile
- Sous-thème : dépendances
- Niveau : 2
- Définition : Le cache garde un dossier (store pnpm, `~/.cache/uv`) d'un pipeline au suivant ; sa clé, calculée sur le lockfile, change dès qu'une dépendance change.
- Contexte : Sans cache, chaque job retélécharge tout : des minutes facturées à chaque push. Clé sur le hash du lockfile : même lockfile = même cache, lockfile modifié = cache neuf, jamais de dépendances périmées. Le cache est un accélérateur sans garantie : runner différent, cache expiré ou évincé, il manque ; l'installation doit donc toujours tourner après la restauration.
- Usage : ✅ store du gestionnaire de paquets, clé = lockfile · ❌ cache de `dist/` pour passer le build au job suivant : un artefact.

```yaml
# Exemple 1 : GitLab
test:
  cache:
    key:
      files: [pnpm-lock.yaml]
    paths: [.pnpm-store/]
  script:
    - pnpm config set store-dir .pnpm-store
    - pnpm install && make test
```

```yaml
# Exemple 2 : GitHub
- uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: uv-${{ hashFiles('uv.lock') }}
- run: uv sync --locked
```

- Quiz : Pour gagner du temps, on retire `pnpm install` du script quand le cache existe : que risque-t-on ?
- [ ] Rien : la clé garantit un cache à jour
- [x] Un job rouge le jour où le cache manque
- [ ] Un cache réécrit à chaque job
- [ ] Des dépendances d'un autre lockfile
- Réponse : un job rouge : le cache n'est jamais garanti (autre runner, expiration) ; l'installation reste dans le script, le cache ne fait que l'accélérer (doc GitLab et GitHub).

## 9. artefacts : construire une fois
- Sous-thème : déploiement
- Niveau : 2
- Définition : Un artefact est un fichier produit par un job (`dist/`, `tfplan`) et transmis aux suivants : on déploie exactement ce qui a été testé.
- Contexte : Chaque job démarre dans un conteneur neuf : sans artefact, `deploy` rebâtirait `dist/`, peut-être différemment. Contrairement au cache, l'artefact est garanti et téléchargeable depuis l'interface. Il expire (`expire_in`) et peut contenir des données sensibles : un `tfplan` porte des valeurs en clair. GitHub passe par `upload-artifact` et `download-artifact`, car ses jobs ne partagent rien.
- Usage : ✅ `dist/` du build vers le deploy, `tfplan` du plan vers l'apply, rapport de tests · ❌ dépendances à réutiliser entre pipelines : le cache.

```yaml
# Exemple 1 : GitLab
build:
  stage: build
  script: [make build]
  artifacts:
    paths: [app/dist/]
    expire_in: 1 week
deploy:
  stage: deploy
  script: [make deploy]  # app/dist/ là
```

- Quiz : Sans `dependencies` ni `needs`, quels artefacts un job de l'étape `deploy` télécharge-t-il ?
- [ ] Aucun : il faut les déclarer
- [ ] Ceux du job juste avant lui
- [x] Ceux de tous les jobs des étapes précédentes
- [ ] Ceux du dernier pipeline réussi
- Réponse : tous ceux des étapes précédentes : c'est le défaut GitLab ; `dependencies: [build]` restreint, `dependencies: []` n'en prend aucun (doc GitLab).

## 10. needs : sortir de l'ordre des stages
- Sous-thème : chaîne
- Niveau : 2
- Définition : `needs` fait démarrer un job dès que les jobs listés ont réussi, sans attendre la fin de toute l'étape précédente (graphe de dépendances).
- Contexte : Avec les seules `stages`, `deploy-site` attend aussi le lent `test-api` sans rapport. `needs: [build-site]` le lance dès que son build est prêt, et il ne récupère que les artefacts des jobs listés. Sur GitHub, `needs` est le seul moyen d'ordonner des jobs. Un job dont un `needs` échoue est sauté.
- Usage : ✅ monorepo, chaînes indépendantes dans un même pipeline · ❌ `needs` partout dans un pipeline linéaire de trois jobs : les stages suffisent.

```yaml
# Exemple 1 : deux chaînes parallèles
build-site:
  stage: build
  script: [make -C app build]
test-api:
  stage: test
  script: [make test]   # 10 min
deploy-site:
  stage: deploy
  needs: [build-site]   # n'attend pas
  script: [make -C app deploy]
```

- Quiz : Que fait `needs: []` sur un job de l'étape `deploy` ?
- [ ] Erreur : `needs` vide interdit
- [ ] Il attend toutes les étapes, comme sans `needs`
- [x] Il démarre dès la création du pipeline
- [ ] Il n'est jamais lancé
- Réponse : il démarre tout de suite : une liste vide veut dire « aucune dépendance », le job ignore l'ordre des étapes (doc GitLab).

## 11. rules : la première qui correspond
- Sous-thème : déclencheurs
- Niveau : 2
- Définition : `rules` décide si un job entre dans le pipeline : les règles sont lues dans l'ordre, la première qui correspond fixe son `when`.
- Contexte : Chaque règle combine `if` (variables prédéfinies : `$CI_COMMIT_BRANCH`, `$CI_PIPELINE_SOURCE`), `changes` (fichiers modifiés) et `when` (`on_success`, `manual`, `never`). Dès qu'une règle correspond, les suivantes sont ignorées : une règle large en tête masque les autres. `rules` remplace les anciens `only` et `except`, à ne pas mélanger dans un même job.
- Usage : ✅ `when: never` en tête pour exclure, puis les cas positifs · ❌ `only` et `except` dans un nouveau pipeline : `rules`.

```yaml
# Exemple 1 : exclure d'abord
deploy:
  script: [make deploy]
  rules:
    - if: $CI_COMMIT_MESSAGE =~ /WIP/
      when: never
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_PIPELINE_SOURCE ==
        "merge_request_event"
      when: manual
```

- Quiz : Push sur la branche `RLINK-123`, sans MR ouverte : que devient le job `deploy` ?
- [ ] Ajouté en `manual`
- [ ] Ajouté et exécuté
- [x] Absent du pipeline
- [ ] Le pipeline échoue
- Réponse : absent : aucune règle ne correspond, le job n'est pas ajouté ; une dernière règle `- when: on_success` sans `if` servirait de cas par défaut (doc GitLab).

## 12. matrix : un job, plusieurs variantes
- Sous-thème : chaîne
- Niveau : 2
- Définition : Une matrice génère un job par combinaison de valeurs (versions de Python, environnements) à partir d'une seule définition.
- Contexte : GitHub : `strategy.matrix`, lue via `${{ matrix.python }}` ; GitLab : `parallel: matrix`, chaque variable devient une variable d'environnement. Deux axes de 2 et 3 valeurs font 6 jobs, tous facturés. Sert à tester une bibliothèque sur plusieurs versions, ou à lancer le même plan Terraform par environnement.
- Usage : ✅ tests sur Python 3.12 et 3.13, `plan` sur `dev` et `prod` · ❌ variantes qui n'ont rien en commun : jobs séparés, plus lisibles.

```yaml
# Exemple 1 : GitHub
test:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python: ["3.12", "3.13"]
  steps:
    - uses: astral-sh/setup-uv@v6
      with:
        python-version: ${{ matrix.python }}
    - run: uv run pytest
```

```yaml
# Exemple 2 : GitLab
plan:
  parallel:
    matrix:
      - ENV: [dev, prod]
  script: [make plan ENV=$ENV]
```

- Quiz : Sur GitHub, le job `3.12` échoue alors que `3.13` tourne encore : que devient `3.13` ?
- [x] Annulé : `fail-fast` vaut `true` par défaut
- [ ] Il continue, le résultat est agrégé à la fin
- [ ] Il est relancé avec `3.12`
- [ ] Il continue, mais son résultat est ignoré
- Réponse : annulé : par défaut `fail-fast: true` arrête les jobs en cours de la matrice au premier échec ; `fail-fast: false` les laisse finir (doc GitHub).

## 13. OIDC : un rôle AWS sans clé
- Sous-thème : secrets
- Niveau : 2
- Définition : Avec OIDC, la CI reçoit un jeton signé décrivant le pipeline (dépôt, branche) et l'échange contre les identifiants temporaires d'un rôle IAM.
- Contexte : Aucune clé AWS à stocker, donc rien à faire tourner ni à fuiter : c'est l'équivalent du rôle de service CodeBuild pour une CI externe. Côté AWS, un fournisseur d'identité OIDC et un rôle dont la politique de confiance filtre `sub` (dépôt, branche). GitHub : `permissions: id-token: write` et l'action `configure-aws-credentials` ; GitLab : `id_tokens` puis `assume-role-with-web-identity`.
- Usage : ✅ tout pipeline GitHub ou GitLab qui appelle AWS · ❌ `AWS_ACCESS_KEY_ID` en secret de CI ; confiance sans condition sur `sub` : tout dépôt de la forge pourrait endosser le rôle.

```yaml
# Exemple 1 : GitHub Actions
permissions:
  id-token: write
  contents: read
steps:
  - uses: actions/checkout@v4
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: ${{ vars.DEPLOY_ROLE }}
      aws-region: eu-west-3
  - run: make deploy PROFILE=
```

```yaml
# Exemple 2 : GitLab
deploy:
  id_tokens:
    AWS_TOKEN:
      aud: sts.amazonaws.com
  script:
    - echo "$AWS_TOKEN" > /tmp/t
    - export AWS_ROLE_ARN=$DEPLOY_ROLE
    - export AWS_WEB_IDENTITY_TOKEN_FILE=/tmp/t
    - make deploy PROFILE=
```

- Quiz : Dans l'exemple 1, on retire la ligne `contents: read` d'un dépôt privé : quel step échoue ?
- [ ] Aucun : `contents: read` est le défaut
- [x] `actions/checkout`
- [ ] `configure-aws-credentials`
- [ ] `make deploy`, faute de droits S3
- Réponse : `actions/checkout` : dès qu'un bloc `permissions` existe, toute permission non listée vaut `none`, le jeton ne peut plus lire le dépôt (doc GitHub).

## 14. environnement : approbation avant la prod
- Sous-thème : déploiement
- Niveau : 2
- Définition : Un environnement (`dev`, `prod`) nomme la cible d'un job de déploiement ; la CI y attache historique, URL, secrets dédiés et approbation manuelle.
- Contexte : GitLab : `environment: prod` liste chaque déploiement et permet le rollback ; `when: manual` pose un bouton. GitHub : `environment: production` avec « required reviewers » bloque le job jusqu'à validation, et réserve ses secrets à ce job. Un même pipeline déploie donc `dev` automatiquement, puis attend un humain pour `prod`, comme l'approbation d'une CodePipeline.
- Usage : ✅ `dev` automatique sur `main`, `prod` sur clic ou approbation · ❌ un pipeline séparé copié-collé pour la prod : même pipeline, deux environnements.

```yaml
# Exemple 1 : GitLab
deploy-dev:
  stage: deploy
  environment: dev
  script: [make deploy ENV=dev]
deploy-prod:
  stage: deploy
  environment: prod
  when: manual
  script: [make deploy ENV=prod]
```

```yaml
# Exemple 2 : GitHub
deploy-prod:
  needs: deploy-dev
  environment: production  # reviewers
  runs-on: ubuntu-latest
  steps:
    - run: make deploy ENV=prod
```

- Quiz : Dans l'exemple 1 (`when: manual` hors `rules`), une étape `notify` suit `deploy` : attend-elle le clic ?
- [ ] Oui : un job manuel bloque la suite
- [x] Non : le pipeline continue sans lui
- [ ] Non : le pipeline échoue aussitôt
- [ ] Oui, pendant une heure puis il continue
- Réponse : non : un job `when: manual` a `allow_failure: true` par défaut et ne bloque rien ; `allow_failure: false` (défaut d'un `manual` dans `rules`) fait attendre (doc GitLab).

## 15. déploiement idempotent : rejouable sans risque
- Sous-thème : déploiement
- Niveau : 2
- Définition : Un déploiement idempotent donne le même état final lancé une ou dix fois : relancer un job raté ne crée ni doublon ni dérive.
- Contexte : La CI relance des jobs (échec réseau, bouton retry, rollback) : chaque étape doit décrire un état, pas une action. `terraform apply` converge vers le code (`No changes` la 2e fois), `aws s3 sync` ne copie que ce qui diffère. Les pièges : un `create` qui échoue si la ressource existe, une version publiée à chaque passage, un fichier ajouté jamais retiré.
- Usage : ✅ `terraform apply`, `s3 sync --delete`, `put` plutôt que `create` · ❌ script de déploiement qui suppose un environnement vierge.

```bash
# Exemple 1 : rejouer = aucun effet
make deploy ENV=dev
make deploy ENV=dev   # même commit
# terraform : No changes.
# s3 sync   : rien à copier
```

- Quiz : On renomme un asset et le deploy fait `aws s3 sync dist/ s3://…` sans `--delete` : que devient l'ancien fichier ?
- [ ] Remplacé par le nouveau nom
- [x] Il reste dans le bucket
- [ ] Supprimé au déploiement suivant
- [ ] Le `sync` échoue : conflit de noms
- Réponse : il reste : `sync` ne fait qu'ajouter et mettre à jour ; seul `--delete` retire de la destination ce qui n'est plus dans `dist/` (doc AWS CLI).

## 16. rollback : redéployer l'ancien commit
- Sous-thème : déploiement
- Niveau : 2
- Définition : Un rollback remet en service la dernière version saine : on redéploie un commit connu, jamais on ne corrige à la main en prod.
- Contexte : Deux voies. Rapide : relancer le job de déploiement d'un pipeline précédent (bouton « Rollback » d'un environnement GitLab, « Re-run » sur GitHub) : il redéploie l'ancien commit. Durable : `git revert` du commit fautif, poussé sur `main`, qui repasse par tests et déploiement. Prérequis : un déploiement idempotent, et un schéma de données compatible avec l'ancienne version.
- Usage : ✅ rollback de l'environnement puis `git revert` pour réaligner `main` · ❌ patch à la main dans la console AWS : Terraform l'écrasera au prochain apply.

```bash
# Exemple 1 : la voie durable
git revert --no-edit a1b2c3d
git push origin main
# → pipeline : test, puis deploy
#   de main sans le commit fautif
```

- Quiz : Après un rollback GitLab vers le déploiement d'hier, le pipeline suivant sur `main` déploie quoi ?
- [ ] La version d'hier, le rollback est retenu
- [x] Le dernier commit de `main`, fautif compris
- [ ] Rien : l'environnement est verrouillé
- [ ] La version d'hier plus le dernier commit
- Réponse : le dernier commit de `main` : le rollback ne touche pas Git ; sans `git revert`, le prochain push redéploie le bug (doc GitLab, environnements).

## 17. concurrence : un déploiement à la fois
- Sous-thème : déploiement
- Niveau : 3
- Définition : `concurrency` (GitHub) et `resource_group` (GitLab) empêchent deux déploiements simultanés sur un même environnement : le second attend.
- Contexte : Deux pushes rapides lancent deux pipelines : sans verrou, deux `terraform apply` se disputent l'état (le lock S3 en fait échouer un) et deux `s3 sync` se mélangent. Sur GitHub, `cancel-in-progress: true` coupe le déploiement en cours, risqué en plein `apply` : à réserver aux tests. GitLab met les jobs du même `resource_group` en file.
- Usage : ✅ un groupe par environnement (`deploy-dev`), `cancel-in-progress` pour les tests seulement · ❌ annuler un `terraform apply` en cours : état partiel, lock à lever.

```yaml
# Exemple 1 : GitHub
concurrency:
  group: deploy-dev
  cancel-in-progress: false
```

```yaml
# Exemple 2 : GitLab
deploy-dev:
  resource_group: dev
  script: [make deploy ENV=dev]
```

- Quiz : Exemple 1, trois pushes en quelques secondes : combien de déploiements s'exécutent ?
- [ ] 3, l'un après l'autre
- [x] 2 : le 1er, puis le 3e
- [ ] 1 : le 1er seulement
- [ ] 1 : le 3e seulement
- Réponse : 2 : le 1er tourne, le 2e attend puis est annulé quand le 3e arrive ; un seul run en attente par groupe, le plus récent (doc GitHub).

## 18. masquage : pas une protection
- Sous-thème : secrets
- Niveau : 3
- Définition : Le masquage remplace dans les logs la valeur exacte d'un secret par `[MASKED]` (GitLab) ou `***` (GitHub) ; toute variante transformée apparaît en clair.
- Contexte : La CI cherche la chaîne exacte dans la sortie. Encodée, échappée, découpée ou écrite dans un artefact, elle n'est plus reconnue. Tout script exécuté par le job lit d'ailleurs le secret : une dépendance compromise ou une MR malveillante peut l'exfiltrer. GitLab exige aussi une valeur d'au moins 8 caractères, sur une ligne, pour la masquer. Le vrai garde-fou : identités OIDC et secrets réservés aux branches protégées.
- Usage : ✅ masquer tous les secrets, en plus de `protected` · ❌ compter sur le masquage pour exposer un secret à un job qui exécute du code non relu.

```bash
# Exemple 1 : le log d'un job GitLab
echo "$INSEE_TOKEN"
# → [MASKED]
env | grep INSEE
# → INSEE_TOKEN=[MASKED]
```

- Quiz : Que montre le log pour `echo "$INSEE_TOKEN" | base64` ?
- [ ] `[MASKED]`
- [x] La valeur encodée, en clair
- [ ] Une ligne vide
- [ ] Le job échoue : secret détecté
- Réponse : la valeur encodée : elle ne ressemble plus au secret, rien ne la masque ; `base64 -d` la rend (doc GitLab : une sortie modifiée n'est pas masquée).

## 19. PR de fork : pas de secrets
- Sous-thème : secrets
- Niveau : 3
- Définition : Un workflow `pull_request` venu d'un fork tourne sans les secrets du dépôt, avec un `GITHUB_TOKEN` en lecture seule.
- Contexte : Le code de la PR est celui d'un inconnu : s'il recevait les secrets, il les exfiltrerait. `pull_request_target`, lui, tourne dans le contexte du dépôt cible, avec ses secrets : y faire un `checkout` du code de la PR puis l'exécuter est la faille classique. GitLab est analogue : un pipeline de MR de fork tourne dans le projet du fork, sans les variables du parent.
- Usage : ✅ tests sans secret sur les PR externes, déploiement sur `main` seulement · ❌ `pull_request_target` qui construit ou exécute le code de la PR.

```yaml
# Exemple 1 : tests seulement
on: pull_request
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make test   # sans secret
```

- Quiz : Une PR de fork déclenche un job qui lit `${{ secrets.INSEE_TOKEN }}` : que reçoit-il ?
- [ ] Le secret, masqué en `***`
- [ ] Une erreur de syntaxe du workflow
- [x] Une chaîne vide
- [ ] Le secret, en lecture seule
- Réponse : une chaîne vide : hors `GITHUB_TOKEN`, aucun secret n'est transmis à un workflow déclenché depuis un fork (doc GitHub).

## 20. clone superficiel : historique tronqué
- Sous-thème : chaîne
- Niveau : 3
- Définition : La CI clone peu de commits pour aller vite : `actions/checkout` un seul et sans tags, GitLab 20 par défaut (`GIT_DEPTH`).
- Contexte : Tout ce qui lit l'historique casse alors en silence ou en erreur : `git describe` pour numéroter une version, `git diff` avec un commit ancien, un changelog depuis le dernier tag. Correctif ciblé : `fetch-depth: 0` (tout l'historique et les tags) sur GitHub, `GIT_DEPTH: 0` sur GitLab, seulement dans le job qui en a besoin, car un clone complet coûte du temps.
- Usage : ✅ `fetch-depth: 0` dans le job de release qui lit les tags · ❌ clone complet sur tous les jobs : du temps perdu à chaque pipeline.

```bash
# Exemple 1 : reproduire le checkout
git clone --depth 1 --no-tags URL s
cd s && git describe --tags
# → fatal: No names found,
#   cannot describe anything.
git rev-list --count HEAD   # → 1
```

```yaml
# Exemple 2 : le correctif
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- run: git describe --tags
```

- Quiz : Projet GitLab récent, réglages par défaut, dépôt de 500 commits : que renvoie `git rev-list --count HEAD` dans un job ?
- [ ] `500`
- [ ] `1`
- [x] `20`
- [ ] `50`
- Réponse : `20` : la profondeur de clone par défaut d'un projet GitLab récent vaut 20, modifiable par `GIT_DEPTH` (doc GitLab).
