---
title: "Cartes · CI-CD"
type: cartes
langage: DevOps
cours: CI-CD
created: 2026-10-24
updated: 2026-10-25
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

## 7. artefacts de job : ils expirent
- Sous-thème : déploiement
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Un artefact de job GitLab passe un fichier aux jobs suivants, puis expire : le livrable gardé pour un rollback va dans un bucket S3.
- Contexte : Pour redéployer la version de la semaine dernière, il faut le zip déployé ce jour-là. Sur S3, rangé sous son hash, il reste disponible tant qu'une règle de cycle de vie ne le supprime pas. Côté GitLab, `expire_in` règle la durée ; seuls les artefacts du dernier pipeline réussi d'une branche sont gardés au-delà, par défaut.
- Usage : ✅ artefact de job pour transmettre dans le pipeline, bucket `artifacts` pour conserver · ❌ un rollback qui compte sur l'artefact d'un vieux pipeline : expiré.

```yaml
# Exemple 1 : passer, puis publier
build:
  stage: build
  script: [make lambdas-build]
  artifacts:
    paths: [build/]
    expire_in: 1 day     # le temps du pipeline
publish:
  stage: deploy
  needs: [build]
  script: [make lambdas-publish]   # vers S3
```

- Quiz : Sur gitlab.com, un job sans `expire_in` : combien de temps son artefact reste-t-il ?
- [ ] Pour toujours
- [x] 30 jours
- [ ] Une semaine
- [ ] Jusqu'au pipeline suivant
- Réponse : 30 jours : c'est le réglage par défaut de l'instance gitlab.com (doc GitLab) ; une instance auto-hébergée peut en fixer un autre.

## 8. pointeur : désigner l'artefact courant
- Sous-thème : déploiement
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Un pointeur est un petit fichier mutable (`lambdas/<nom>/current.json`) qui désigne l'artefact immuable à déployer (≈ un dist-tag `latest` npm).
- Contexte : Les zips ne changent jamais sous leur clé ; seul le pointeur bouge. Il contient la clé, le `base64sha256` attendu par Terraform, la taille, le commit et la date. Déployer une autre version revient à réécrire le pointeur, puis `make up`. Même logique qu'une branche git vers un commit : le nom bouge, le contenu désigné reste figé.
- Usage : ✅ même commande de déploiement sur le poste et en CI, sans hash à recopier · ❌ réécrire le zip lui-même sous une clé fixe : on perd ce qui tournait avant.

```json
# Exemple 1 : lambdas/ingest-bodacc/current.json
{
  "key": "lambdas/ingest-bodacc/4881…f3f.zip",
  "base64sha256": "SIF3hiDV…",
  "size": 21180000,
  "git_commit": "c75b13b…",
  "git_dirty": true,
  "published_at": "2026-10-25T…"
}
```

- Quiz : Le pointeur est supprimé du bucket, les zips restent : que fait le `make up` suivant ?
- [ ] Il redéploie le dernier zip trouvé
- [ ] Rien : la fonction garde son code
- [x] Il échoue dès le plan
- [ ] Il supprime la fonction
- Réponse : il échoue dès le plan : le data source `aws_s3_object` ne trouve plus `current.json` ; il faut republier (`make lambdas-publish`) pour réécrire le pointeur.

## 9. make deploy : publier, puis appliquer
- Sous-thème : chaîne
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `deploy: lambdas-publish up` enchaîne la publication des zips et du pointeur, puis `terraform apply` : la même cible sert au poste et à la CI.
- Contexte : L'ordre est imposé par Terraform : le plan lit le pointeur, il doit donc exister et être à jour avant. `PROFILE=` vide en CI laisse la CLI prendre le rôle du job ; `LAMBDA=` vide publie toutes les Lambdas trouvées par convention (`lambdas/*/pyproject.toml`). La publication est idempotente : relancer `make deploy` sans changement n'envoie rien et ne modifie rien.
- Usage : ✅ `make deploy` après tout changement de code d'une Lambda · ❌ `make up` seul après un changement de code : rien ne republie le zip.

```makefile
# Exemple 1 : les cibles du Makefile
lambdas-publish:
	uv run infra/scripts/build_lambda.py \
	  --publish \
	  $(if $(PROFILE),--profile $(PROFILE)) \
	  $(LAMBDA)

deploy: lambdas-publish up
```

- Quiz : Le code du handler change, puis on lance `make up` sans `lambdas-publish` : que montre le plan pour la fonction ?
- [ ] Une mise à jour du code
- [x] Aucun changement
- [ ] Une erreur : zip périmé
- [ ] Un remplacement de la fonction
- Réponse : aucun changement : Terraform lit le pointeur, qui désigne toujours l'ancien zip ; il ne voit ni le code source ni `build/`.

## 10. clé : le hash en hexadécimal
- Sous-thème : déploiement
- Niveau : 1
- Source : data-platform · S1-07
- Définition : La clé S3 de l'artefact porte le sha256 en hexadécimal (`<64 caractères>.zip`) ; le base64, attendu par Terraform, reste dans le pointeur.
- Contexte : Le base64 contient `/` et `+` : dans une clé S3, `/` crée un faux sous-dossier et `+` s'encode mal dans une URL. L'hexadécimal n'a que `0-9a-f`, se compare d'un coup d'œil à `sha256sum` et se tape sans échappement. Les deux écritures décrivent les mêmes 32 octets ; le script calcule l'une et l'autre depuis un seul `hashlib.sha256`.
- Usage : ✅ hexadécimal dans les noms (clés, tags d'image), base64 là où l'outil l'exige · ❌ le base64 dans un chemin ou une URL.

```python
# Exemple 1 : deux écritures, un hash
import base64
import hashlib

d = hashlib.sha256(b"PK v1")
cle = f"lambdas/ingest-bodacc/{d.hexdigest()}.zip"
b64 = base64.b64encode(d.digest()).decode()
"/" in b64        # → True
"/" in d.hexdigest()  # → False
len(d.hexdigest()), len(b64)  # → (64, 44)
```

- Quiz : Avec la clé `lambdas/ingest-bodacc/<base64>.zip` et ce `b64`, que liste `aws s3 ls s3://<bucket>/lambdas/ingest-bodacc/` ?
- [ ] Le zip, comme prévu
- [x] Un préfixe `7GpJDi6MgFQ6xHBo40d68Cfeu5JA/`
- [ ] Rien : la clé est refusée
- [ ] Le zip, avec `/` échappé en `%2F`
- Réponse : un préfixe : S3 n'a pas de dossiers, mais `ls` coupe la clé au `/` du base64 et affiche la première moitié comme un sous-dossier.

## 11. CI=true : le lockfile fait foi
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

## 12. cache : clé sur le lockfile
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

## 13. artefacts : construire une fois
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

## 14. needs : sortir de l'ordre des stages
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

## 15. rules : la première qui correspond
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

## 16. matrix : un job, plusieurs variantes
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

## 17. OIDC : un rôle AWS sans clé
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

## 18. environnement : approbation avant la prod
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

## 19. déploiement idempotent : rejouable sans risque
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

## 20. rollback : redéployer l'ancien commit
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

## 21. artefact par hash : la clé est l'empreinte
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : L'artefact est rangé sous son sha256 (`lambdas/ingest-bodacc/<sha256>.zip`) : même contenu, même clé ; une clé déjà présente n'est pas renvoyée.
- Contexte : Avec un build reproductible, deux pipelines sur le même code produisent le même hash : l'envoi est sauté (`head-object` répond 200) et Terraform ne voit aucun changement de `s3_key`. Un objet ne change jamais sous sa clé : on sait ce qui tourne, et revenir en arrière revient à remettre l'ancienne clé. Sans build reproductible, chaque pipeline crée une clé neuve et redéploie.
- Usage : ✅ zips de Lambda, couches, tout artefact promu entre environnements · ❌ clé fixe (`latest.zip`) écrasée à chaque build : on ne sait plus quelle version est déployée.

```python
# Exemple 1 : la clé dérivée du contenu
import hashlib
def cle(nom, zip_bytes):
    h = hashlib.sha256(zip_bytes).hexdigest()
    return f"lambdas/{nom}/{h}.zip"
a = cle("ingest-bodacc", b"PK v1")
a == cle("ingest-bodacc", b"PK v1")  # → True
a == cle("ingest-bodacc", b"PK v2")  # → False
```

```yaml
# Exemple 2 : envoyer seulement si absent
publish:
  stage: deploy
  script:
    - SHA=$(sha256sum build/ingest-bodacc.zip | cut -d' ' -f1)
    - KEY="lambdas/ingest-bodacc/$SHA.zip"
    - aws s3api head-object --bucket "$ARTIFACTS" --key "$KEY"
      || aws s3 cp build/ingest-bodacc.zip "s3://$ARTIFACTS/$KEY"
```

- Quiz : Deux pipelines du même commit, zip non reproductible (dates des fichiers) : combien d'objets sous `lambdas/ingest-bodacc/` ?
- [ ] 1 : même commit, même clé
- [x] 2 : deux hashs différents
- [ ] 1, écrasé par le second pipeline
- [ ] 0 : `head-object` bloque l'envoi
- Réponse : 2 : des octets différents donnent deux sha256, donc deux clés ; d'où le zip reproductible avant l'adressage par contenu.

## 22. promotion : le même artefact de dev à prod
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : On construit une fois, puis chaque environnement (dev, int, prod) déploie la même clé S3 : la prod reçoit les octets testés en dev.
- Contexte : Reconstruire par environnement réintroduit le doute : runner différent, résolution différente, build non reproductible. La promotion ne change que la configuration (tfvars, variables) ; la clé passe au Terraform de chaque environnement par une variable. Les comptes de dev et de prod lisent le même bucket `artifacts` (politique de bucket entre comptes si besoin).
- Usage : ✅ pipeline multi-environnements, approbation manuelle avant la prod · ❌ un job `build` par environnement : trois artefacts peut-être différents.

```yaml
# Exemple 1 : une clé, plusieurs environnements
.deploy:
  stage: deploy
  script:
    - make up ENV=$ENV TF_VAR_lambda_s3_key=$KEY
deploy-dev:
  extends: .deploy
  variables: { ENV: dev }
deploy-prod:
  extends: .deploy
  variables: { ENV: prod }
  when: manual             # approbation
```

```hcl
# Exemple 2 : la clé en variable
variable "lambda_s3_key" { type = string }
resource "aws_lambda_function" "ingest" {
  s3_bucket = "data-platform-artifacts"
  s3_key    = var.lambda_s3_key
  # autres arguments omis
}
```

- Quiz : `s3_key` contient le hash du zip : faut-il encore `source_code_hash` pour redéployer ?
- [ ] Oui : sinon le code n'est jamais mis à jour
- [x] Non : une nouvelle clé suffit à déclencher la mise à jour
- [ ] Oui : S3 l'exige pour Lambda
- [ ] Non : Lambda surveille le bucket
- Réponse : non : un nouveau contenu donne une nouvelle clé, et Terraform voit `s3_key` changer ; `source_code_hash` sert quand le chemin ou la clé restent fixes.

## 23. rules: changes : les vraies sources du zip
- Sous-thème : déclencheurs
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `rules: - changes: [...]` ne crée le job que si le push modifie l'un de ces fichiers : on ne reconstruit que la Lambda touchée.
- Contexte : Avec dix Lambdas, tout reconstruire à chaque push coûte des minutes. Le piège : le code d'une Lambda ne vit pas que dans son dossier. `ingest_bodacc` importe `packages/bodacc-client` et dépend de `uv.lock` : un filtre sur son seul dossier rate ces changements, et la Lambda n'est pas reconstruite. Lister toutes les sources : dossier, paquets internes, lock, script de build.
- Usage : ✅ monorepo à plusieurs Lambdas, filtres qui listent les dépendances internes · ❌ filtre sur le seul dossier de la fonction quand elle importe un paquet partagé.

```yaml
# Exemple 1 : GitLab
build-ingest:
  stage: build
  script: [make lambdas-build LAMBDA=ingest-bodacc]
  rules:
    - changes:
        - lambdas/ingest_bodacc/**/*
        - packages/bodacc-client/**/*
        - uv.lock
        - infra/scripts/build_lambda.py
```

- Quiz : Premier push d'une nouvelle branche : le job `build-ingest` est-il créé ?
- [ ] Non : aucun fichier filtré n'a changé
- [x] Oui : `changes` vaut vrai sur une branche neuve
- [ ] Seulement si la branche part de `main`
- [ ] Non : `changes` exige une merge request
- Réponse : oui : sans référence de comparaison, GitLab évalue `changes` à vrai pour une branche ou un tag neufs (doc GitLab) ; `compare_to: refs/heads/main` corrige.

## 24. matrix : un build par Lambda
- Sous-thème : chaîne
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `parallel: matrix` avec `LAMBDA: [ingest-bodacc, normalize-bodacc]` lance un job de build par fonction, en parallèle, à partir d'une seule définition.
- Contexte : Le script de build est générique (`build_lambda.py <membre>`) : la matrice ne fait varier que son argument. Chaque variante est un job à part, avec ses logs et ses artefacts ; une variante en échec n'empêche pas les autres de finir. Un job suivant peut viser une seule variante avec `needs: - job: build` et `parallel: matrix:`. La liste reste écrite à la main.
- Usage : ✅ quelques Lambdas construites par le même script · ❌ des dizaines de fonctions ajoutées souvent : un pipeline enfant généré évite de tenir la liste.

```yaml
# Exemple 1 : GitLab
build:
  stage: build
  parallel:
    matrix:
      - LAMBDA: [ingest-bodacc, normalize-bodacc]
  script: [make lambdas-build LAMBDA=$LAMBDA]
  artifacts:
    paths: [build/]
```

- Quiz : Quel nom GitLab affiche-t-il pour la variante `ingest-bodacc` de ce job ?
- [ ] `build 1/2`
- [ ] `build-ingest-bodacc`
- [x] `build: [ingest-bodacc]`
- [ ] `build`, deux fois
- Réponse : `build: [ingest-bodacc]` : une matrice nomme chaque job avec ses valeurs entre crochets (doc GitLab) ; `build 1/2` est le nom donné par `parallel: 2`.

## 25. Pants : reconstruire ce qui dépend du changement
- Sous-thème : chaîne
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Pants lit les imports du code pour connaître les dépendances : `--changed-since=origin/main --changed-dependents=transitive` ne reconstruit que les cibles touchées.
- Contexte : Là où un filtre de chemins se trompe dès qu'un paquet partagé change, Pants sait que `ingest_bodacc` importe `bodacc_client`. La cible `python_aws_lambda_function` produit le zip pour un runtime et une plateforme, avec un cache partagé entre runners. Coût : un outil de plus, des fichiers `BUILD`, un apprentissage ; rentable avec beaucoup de fonctions.
- Usage : ✅ gros monorepo Python (dizaines de Lambdas, paquets partagés) · ❌ deux ou trois Lambdas : un script et des filtres de chemins suffisent.

```bash
# Exemple 1 : seulement ce qui a changé
pants --changed-since=origin/main \
  --changed-dependents=transitive package
# → zips des Lambdas qui importent
#   le code modifié, et rien d'autre
```

```text
# Exemple 2 : lambdas/ingest_bodacc/BUILD
python_aws_lambda_function(
    name="lambda",
    handler="ingest_bodacc/handler.py:lambda_handler",
    runtime="python3.12",
)
```

- Quiz : On modifie seulement `packages/bodacc-client` : `ingest_bodacc` est-il reconstruit par la commande de l'exemple 1 ?
- [x] Oui : il dépend du paquet modifié
- [ ] Non : son dossier n'a pas changé
- [ ] Oui, mais toutes les Lambdas aussi
- [ ] Non : `--changed-since` ignore les paquets
- Réponse : oui : `--changed-dependents=transitive` ajoute tout ce qui importe, directement ou non, les fichiers modifiés.

## 26. SAM et CDK : le build intégré
- Sous-thème : chaîne
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `sam build --use-container` et `PythonFunction` (CDK) construisent eux-mêmes le zip d'une Lambda Python, dans un conteneur Linux à l'image du runtime.
- Contexte : Les dépendances s'installent dans l'image de build officielle du runtime : binaires Linux, bonne architecture, sans `--python-platform`, et même compilation d'un paquet sans roue. Les deux supposent leur outil de déploiement (CloudFormation) et Docker sur le runner. Avec Terraform, on garde un script de build et on passe le zip à `aws_lambda_function`.
- Usage : ✅ projet déjà sur SAM ou CDK, dépendance à compiler faute de roue · ❌ infrastructure en Terraform : SAM pour le seul build mélange deux outils de déploiement.

```bash
# Exemple 1 : SAM
sam build --use-container
# → .aws-sam/build/IngestFunction/
#   dépendances installées dans
#   l'image public.ecr.aws/sam/build-python3.12
```

- Quiz : Une dépendance n'a pas de roue `aarch64` : laquelle de ces méthodes peut quand même la construire ?
- [ ] `uv pip install --only-binary :all:`
- [ ] `--python-platform aarch64-manylinux2014`
- [x] `sam build --use-container` en arm64
- [ ] `uv export --no-editable`
- Réponse : `sam build --use-container` : il compile dans un vrai Linux de la bonne architecture ; uv sur le Mac ne peut que choisir des roues existantes.

## 27. publication idempotente : rien si déjà là
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : La publication n'envoie le zip que s'il manque, et ne réécrit le pointeur que s'il change : relancée, elle ne fait rien.
- Contexte : Deux contrôles, deux bénéfices. Sauter l'envoi d'un zip déjà présent économise 20 Mo par pipeline. Ne pas réécrire un pointeur identique évite une nouvelle version S3 (le bucket est versionné) et garde `published_at` et `git_commit` de la vraie publication. Le résultat se lit en trois états : `envoyé`, `déjà envoyé, pointeur →`, `à jour`.
- Usage : ✅ tout script de publication relancé par une CI ou un humain · ❌ envoyer et réécrire à chaque fois : versions inutiles, historique du pointeur illisible.

```python
# Exemple 1 : la logique, sur un dict
bucket = {}

def publier(nom, sha):
    cle = f"lambdas/{nom}/{sha}.zip"
    deja = cle in bucket
    if not deja:
        bucket[cle] = b"zip"
    ptr = f"lambdas/{nom}/current.json"
    if bucket.get(ptr) == cle:
        return "à jour"
    bucket[ptr] = cle
    return "déjà envoyé" if deja else "envoyé"

publier("ingest-bodacc", "4881")  # → 'envoyé'
publier("ingest-bodacc", "4881")  # → 'à jour'
```

- Quiz : Après ces deux appels, `publier("ingest-bodacc", "9c02")` puis `publier("ingest-bodacc", "4881")` : que renvoie le dernier ?
- [ ] `'à jour'`
- [ ] `'envoyé'`
- [x] `'déjà envoyé'`
- [ ] `KeyError`
- Réponse : `'déjà envoyé'` : le zip `4881` est toujours dans le bucket, mais le pointeur désigne `9c02` ; seul le pointeur est réécrit, c'est un retour arrière.

## 28. git_dirty : publié depuis un arbre modifié
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `git_dirty: true` dans le pointeur signale un zip construit avec des modifications non commitées : `git_commit` ne suffit pas à le reconstruire.
- Contexte : Le script lance `git status --porcelain` : toute ligne, même un fichier non suivi, rend l'arbre « sale ». En dev, publier avant de commiter est normal (étape 8 : `git_dirty: true`). En CI, l'arbre est un clone propre : un `true` y révèle un fichier généré par le build et non ignoré. La règle d'entreprise : seul un zip `git_dirty: false` part en prod.
- Usage : ✅ tracer d'où vient chaque zip, refuser la prod si `git_dirty` · ❌ ne garder que la date : impossible de relier un incident à un commit.

```python
# Exemple 1 : la sortie porcelain
def sale(porcelain):
    return bool(porcelain.strip())

sale("")                    # → False
sale(" M Makefile\n")       # → True
sale("M  infra/lambdas.tf\n")  # → True
```

- Quiz : Seul `out.json`, non suivi et non ignoré, traîne à la racine : que vaut `git_dirty` ?
- [ ] `False` : le fichier n'est pas suivi
- [x] `True` : porcelain liste `?? out.json`
- [ ] `False` : il n'est pas dans le zip
- [ ] `None` : état indéterminé
- Réponse : `True` : `git status --porcelain` affiche aussi les fichiers non suivis (`??`) ; l'ignorer ou le supprimer remet `git_dirty` à `false`.

## 29. rollback : une ancienne version du pointeur
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le bucket d'artefacts versionné garde chaque version du pointeur : revenir en arrière, c'est remettre l'ancienne valeur, puis `make up`.
- Contexte : Les zips n'étant jamais réécrits ni expirés, toute ancienne clé reste déployable. Le versioning ajoute l'historique : qui a pointé vers quoi, et quand (`published_at`, `git_commit`). La règle de cycle de vie supprime les versions non courantes après 90 jours : l'historique du pointeur est borné, pas les zips. Le rollback ne reconstruit rien : il redéploie des octets déjà testés.
- Usage : ✅ incident en dev ou en prod : remettre le pointeur précédent, `make up` · ❌ reconstruire l'ancien commit en urgence : autre machine, autres octets possibles.

```bash
# Exemple 1 : les versions du pointeur
aws s3api list-object-versions \
  --bucket "$ARTIFACTS" \
  --prefix lambdas/ingest-bodacc/current.json \
  --query 'Versions[].[VersionId,IsLatest]'
# → [["v2…", true], ["v1…", false]]
aws s3api get-object --bucket "$ARTIFACTS" \
  --key lambdas/ingest-bodacc/current.json \
  --version-id "v1…" old.json
```

- Quiz : On veut revenir au zip d'il y a 4 mois ; la version du pointeur a expiré (90 jours) : est-ce encore possible ?
- [ ] Non : le zip a expiré avec elle
- [x] Oui : le zip reste, on réécrit le pointeur
- [ ] Non : il faut reconstruire l'ancien commit
- [ ] Oui, en restaurant la version expirée
- Réponse : oui : seuls les objets non courants expirent ; le zip, objet courant sous sa clé, est toujours là ; on écrit un pointeur avec sa clé et son `base64sha256`.

## 30. pointeur ou hash en TF_VAR_ : le compromis
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le pointeur rend `make deploy` identique partout ; passer la clé en `TF_VAR_` par la CI rend chaque déploiement traçable au pipeline qui l'a lancé.
- Contexte : Avec le pointeur, ce qui est déployé dépend d'un fichier S3 au moment du plan, pas du dépôt : deux plans du même commit peuvent différer. Avec la clé en variable, le pipeline qui construit transmet le hash au job de déploiement (dotenv, artefact), et le plan ne dépend que de ses entrées. Le plan du projet : pointeur tant que tout part du poste, variable et pointeur supprimé quand la CI existera.
- Usage : ✅ pointeur en dev, avec un seul déployeur à la fois · ❌ pointeur partagé quand plusieurs pipelines déploient : la dernière écriture gagne.

```bash
# Exemple 1 : la clé passée par la CI
KEY=$(jq -r .key build/publish.json)
TF_VAR_lambda_keys="{\"ingest-bodacc\":\"$KEY\"}" \
  make up ENV=dev
# plan = f(commit, variables du pipeline)
# rien n'est relu dans un fichier S3
```

- Quiz : Deux branches publient à une minute d'écart, puis chacune lance `make up` : quel zip tourne à la fin ?
- [ ] Celui de la branche `main`
- [ ] Celui du premier `make up`
- [x] Celui du dernier pointeur écrit
- [ ] Les deux, en deux versions
- Réponse : celui du dernier pointeur écrit : chaque `make up` lit le pointeur courant ; sans verrou de déploiement, les deux plans peuvent même déployer le même zip.

## 31. concurrence : un déploiement à la fois
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

## 32. masquage : pas une protection
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

## 33. PR de fork : pas de secrets
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

## 34. clone superficiel : historique tronqué
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

## 35. pipeline enfant généré : un job par Lambda trouvée
- Sous-thème : chaîne
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Un job écrit un YAML (un job par dossier de `lambdas/`) en artefact, puis `trigger: include: - artifact:` lance ce pipeline enfant.
- Contexte : Résout ce que la matrice ne fait pas : la liste des fonctions vient du dépôt (convention `lambdas/*`), et le générateur peut n'émettre que les fonctions modifiées (`git diff --name-only`). Le parent prend le statut de l'enfant avec `strategy: depend`. Plus de code à maintenir : à réserver aux dépôts qui ont beaucoup de fonctions.
- Usage : ✅ monorepo à dizaines de Lambdas, ajoutées sans toucher au `.gitlab-ci.yml` · ❌ deux ou trois fonctions : une matrice écrite à la main se lit mieux.

```yaml
# Exemple 1 : générer puis déclencher
generate:
  stage: build
  script: [python ci/gen_jobs.py > child.yml]
  artifacts: { paths: [child.yml] }
lambdas:
  stage: build
  needs: [generate]
  trigger:
    include:
      - artifact: child.yml
        job: generate
    strategy: depend
```

```python
# Exemple 2 : le générateur, simplifié
import tempfile
from pathlib import Path
root = Path(tempfile.mkdtemp())
for n in ["ingest_bodacc", "normalize_bodacc"]:
    (root / "lambdas" / n).mkdir(parents=True)
dirs = sorted((root / "lambdas").iterdir())
jobs = [f"build-{d.name}:\n  script: [make "
        f"lambdas-build LAMBDA={d.name.replace('_', '-')}]"
        for d in dirs]
jobs[0].splitlines()[0]   # → 'build-ingest_bodacc:'
len(jobs)                 # → 2
```

- Quiz : Sans `strategy: depend`, l'enfant échoue : quel statut prend le job `lambdas` du parent ?
- [x] Succès : il a seulement déclenché
- [ ] Échec, comme l'enfant
- [ ] En attente, jusqu'à relance
- [ ] Annulé
- Réponse : succès : sans `depend`, le job de déclenchement réussit dès que l'enfant est créé (doc GitLab) ; le parent peut passer au vert avec un enfant rouge.

## 36. dotenv : passer une valeur au job suivant
- Sous-thème : dépendances
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `artifacts: reports: dotenv: build.env` publie les variables (`NOM=valeur`) écrites par un job ; les jobs qui en dépendent les reçoivent dans leur environnement.
- Contexte : La clé du zip n'est connue qu'après le build : le job de publication l'écrit dans `build.env`, les déploiements la lisent en `$LAMBDA_KEY` sans recalcul. Format : une variable par ligne. Les variables suivent `needs` et `dependencies`, comme les artefacts. GitHub Actions fait la même chose avec les `outputs` d'un job, lus par `needs.<job>.outputs`.
- Usage : ✅ transmettre une clé d'artefact, un numéro de version, une URL de préproduction · ❌ un secret : il est lisible dans les artefacts du pipeline ; variables protégées à la place.

```yaml
# Exemple 1 : de publish à deploy
publish:
  stage: build
  script:
    - make lambdas-build
    - echo "LAMBDA_KEY=lambdas/ingest-bodacc/$(sha256sum build/ingest-bodacc.zip | cut -d' ' -f1).zip" > build.env
  artifacts:
    reports:
      dotenv: build.env
deploy-dev:
  stage: deploy
  needs: [publish]
  script: [echo "$LAMBDA_KEY"]
```

- Quiz : `deploy-dev` déclare `needs: [{ job: publish, artifacts: false }]` : reçoit-il `$LAMBDA_KEY` ?
- [ ] Oui : dotenv passe toujours
- [ ] Oui, mais vide
- [x] Non : plus d'artefacts, dotenv compris
- [ ] Erreur de syntaxe du pipeline
- Réponse : non : les variables dotenv voyagent comme un artefact ; `artifacts: false` (ou `dependencies: []`) les coupe aussi (doc GitLab).

## 37. pointeur partagé : int déploie l'inédit
- Sous-thème : déploiement
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Un pointeur par Lambda et par compte sert à tous ses environnements : `make up ENV=int` déploie le dernier zip publié, testé ou non.
- Contexte : Le chemin `lambdas/<nom>/current.json` ne contient pas l'environnement. Tant qu'il n'y a que dev, c'est sans effet. Dès qu'un second environnement partage le compte, la promotion exige un pointeur par environnement (`current-<env>.json`) ou la clé passée en variable : promouvoir revient alors à copier la valeur de dev vers int, jamais à republier.
- Usage : ✅ un pointeur par environnement, ou la clé en variable, dès deux environnements par compte · ❌ un pointeur commun : int suit dev sans validation.

```bash
# Exemple 1 : promouvoir dev vers int
aws s3 cp \
  "s3://$ARTIFACTS/lambdas/ingest-bodacc/current-dev.json" \
  "s3://$ARTIFACTS/lambdas/ingest-bodacc/current-int.json"
make up ENV=int
# int reçoit les octets testés en dev
```

- Quiz : Juste après cette copie, dev republie un nouveau zip ; on relance `make up ENV=int` : quel zip tourne en int ?
- [ ] Le nouveau zip de dev
- [x] Celui copié, toujours désigné
- [ ] Aucun : pointeurs incohérents
- [ ] Le plus récent des deux
- Réponse : celui copié : la republication ne réécrit que `current-dev.json` ; int ne change qu'à la prochaine copie, donc à la prochaine promotion décidée.

## 38. rétention : n'expirer que l'ancien
- Sous-thème : déploiement
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Le bucket d'artefacts n'expire jamais un objet courant : seules les anciennes versions (du pointeur) et les envois multipart abandonnés sont nettoyés.
- Contexte : Un zip déployé n'est pas relu par la fonction, mais il l'est par tout `make up` qui recrée la fonction : après `make down`, dans un nouvel environnement, ou pour un retour arrière. Une règle « expirer après 90 jours » sur `lambdas/` casserait ces cas des mois plus tard, en silence. Le nettoyage des zips inutiles se fait à part, en listant les clés encore désignées par un pointeur ou un état.
- Usage : ✅ `noncurrent_version_expiration` et `abort_incomplete_multipart_upload` seuls · ❌ `expiration { days = 90 }` sur des artefacts : rupture différée.

```hcl
# Exemple 1 : ce qui expire, ce qui reste
rule {
  id     = "expire-noncurrent"
  status = "Enabled"
  filter {}
  noncurrent_version_expiration {
    noncurrent_days = 90
  }
}
# pas de bloc expiration : les zips
# courants restent indéfiniment
```

- Quiz : Avec une règle `expiration { days = 90 }` sur `lambdas/`, la fonction n'est pas redéployée pendant 4 mois : que se passe-t-il ?
- [ ] Elle s'arrête au 91e jour
- [x] Elle tourne ; le prochain `make up` qui la recrée échoue
- [ ] Rien : Lambda prolonge l'objet
- [ ] Elle passe sur l'ancienne version du zip
- Réponse : elle tourne, Lambda ayant sa copie ; mais une recréation (`make down` puis `make up`) relit une clé disparue et échoue à l'`apply`.

## 39. Prefix : une clé plus longue répond aussi
- Sous-thème : déploiement
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `list_objects_v2(Prefix=cle, MaxKeys=1)` teste l'existence d'une clé, mais compte aussi toute clé qui commence par elle (`<sha>.zip.part`).
- Contexte : Le script de publication utilise ce test plutôt que `head_object` : sans droit `s3:ListBucket`, `head_object` sur une clé absente répond `403` au lieu de `404`, et l'on ne sait plus distinguer absent de refusé. Le préfixe a son piège : un envoi interrompu laissé sous `<sha>.zip.tmp` ferait croire le zip présent. Avec une clé terminée par `.zip` et aucun autre outil qui écrit là, le risque reste théorique.
- Usage : ✅ `Prefix=cle` puis vérifier `Contents[0]["Key"] == cle` pour un test exact · ❌ se fier au seul `KeyCount` quand d'autres clés peuvent prolonger celle-ci.

```python
# Exemple 1 : le préfixe déborde
import boto3
from moto import mock_aws

with mock_aws():
    s3 = boto3.client("s3", region_name="eu-west-3")
    s3.create_bucket(
        Bucket="artefacts",
        CreateBucketConfiguration={
            "LocationConstraint": "eu-west-3"})
    s3.put_object(Bucket="artefacts",
                  Key="lambdas/x/ab.zip.part", Body=b"")
    r = s3.list_objects_v2(Bucket="artefacts",
        Prefix="lambdas/x/ab.zip", MaxKeys=1)
r["KeyCount"]  # → 1 : le zip n'existe pas
```

- Quiz : Même bucket, `Prefix="lambdas/x/ab.zip"` et `Delimiter="/"` : que vaut `KeyCount` ?
- [ ] 0 : le délimiteur exige une clé exacte
- [x] 1 : aucun `/` après le préfixe
- [ ] 0 : `.part` est ignoré
- [ ] 2 : clé et préfixe commun
- Réponse : 1 : le délimiteur ne regroupe que ce qui contient un `/` après le préfixe ; `.part` n'en a pas, la clé est comptée telle quelle.
