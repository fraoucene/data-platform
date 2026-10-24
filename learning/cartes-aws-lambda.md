---
title: "Cartes · Lambda (AWS)"
type: cartes
langage: AWS
cours: Lambda
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Lambda (AWS)
AWS · Lambda : choisir, déploiement, invocation, limites, logs, sécurité (format spec v3 de revision-pwa).

## 1. Lambda : 15 minutes maximum
- Sous-thème : limites
- Niveau : 1
- Définition : `timeout` fixe la durée maximale d'une invocation Lambda, de 1 à 900 secondes ; au-delà, l'exécution est tuée.
- Contexte : La valeur par défaut est 3 s, souvent trop courte pour un appel d'API paginée. Un timeout est une erreur comme une autre : en asynchrone, Lambda réessaie, et le travail déjà fait est refait. La mémoire (`memory_size`, jusqu'à 10 240 Mo) fixe aussi la part de CPU : plus de mémoire peut raccourcir la durée et coûter moins cher.
- Usage : ✅ traitement d'un jour BODACC (moins d'une minute), réaction à un événement · ❌ traitement de plus de 15 min : découper (Step Functions `Map`) ou passer sur Fargate / EMR.

```hcl
# Exemple 1 : 5 min max, 512 Mo
resource "aws_lambda_function" "i" {
  function_name = "bodacc-ingest"
  runtime       = "python3.12"
  timeout       = 300 # s, défaut 3
  memory_size   = 512 # Mo
}
# fetch_day : 32 000 annonces → 41 s
```

```python
# Exemple 2 : lire le temps restant
class Ctx:  # simule le context Lambda
    def get_remaining_time_in_millis(self):
        return 20_000

def handler(event, context):
    reste = context.get_remaining_time_in_millis()
    # arrêter proprement avant d'être tué
    return "stop" if reste < 30_000 else "go"

handler({}, Ctx())  # → "stop"
```

- Quiz : Un rejeu de 30 jours prend 25 minutes : que donne `timeout = 1500` ?
- [x] Refusé par l'API : maximum 900 s
- [ ] Accepté : la limite est sur la mémoire
- [ ] Accepté, mais tué à 15 min
- [ ] Accepté en asynchrone seulement
- Réponse : refusé : l'API rejette tout timeout au-delà de 900 s ; on découpe (un jour par invocation) ou on change de service.

## 2. Lambda : quand la choisir
- Sous-thème : choisir
- Niveau : 1
- Définition : Lambda est le choix par défaut pour un traitement court sur événement : 15 min au plus, 10 Go de mémoire, payé à la ms.
- Contexte : Pas de serveur ni de coût au repos, mise à l'échelle automatique (1 000 exécutions simultanées par compte et région par défaut). Le code part en archive zip (250 Mo décompressé, couches comprises) ou en image conteneur (jusqu'à 10 Go). Le plafond de 15 min est dur : un traitement plus long se découpe ou change de service.
- Usage : ✅ normaliser le fichier BODACC du jour, réagir à un dépôt S3, petite API · ❌ traitement de plus de 15 min, flux permanent : Fargate ; Spark sur des To : Glue ou EMR.

```
# Exemple 1 : la décision
Besoin  : normaliser le BODACC du
          jour (~50 Mo, ~1 min)
→ Choix : Lambda déclenchée par S3
Pourquoi: 0 $ au repos, rien à gérer,
          largement sous 15 min
Écarté  : Glue (démarrage plus lent,
          Spark inutile à ce volume)
```

```python
# Exemple 2 : coût d'un mois d'ingestion
go_s = 0.0000166667    # $ / Go-s (x86)
memoire_go = 0.5
duree_s = 41 * 30      # 41 s par jour
round(memoire_go * duree_s * go_s, 4)
# → 0.0103  ($/mois, hors free tier)
```

- Quiz : Le traitement doit embarquer une bibliothèque native d'OCR de 3 Go : Lambda reste-t-elle possible ?
- [ ] Non : 250 Mo maximum, il faut Fargate
- [ ] Oui, en couche (layer) de 3 Go
- [x] Oui, en image conteneur (10 Go max)
- [ ] Non : Lambda refuse le code natif
- Réponse : oui, en image conteneur : la limite de 250 Mo vaut pour le zip et ses couches ; une image conteneur peut faire jusqu'à 10 Go.

## 3. handler : event et context
- Sous-thème : invocation
- Niveau : 1
- Définition : Le handler est la fonction que Lambda appelle à chaque invocation, avec l'événement (JSON désérialisé) et un objet `context` ; `handler = "fichier.fonction"`.
- Contexte : `handler = "ingest.handler"` désigne la fonction `handler` du module `ingest.py` à la racine du zip ; en Node, `index.handler` est l'export `handler` de `index.mjs`. La forme de l'événement dépend de la source (S3, SQS, API Gateway). La valeur renvoyée est sérialisée en JSON et n'est vue que par un appelant synchrone. `context` donne l'ID de requête et le temps restant.
- Usage : ✅ handler mince qui extrait les champs de l'événement puis appelle une fonction testable seule · ❌ toute la logique dans le handler : impossible à tester sans fabriquer un événement complet.

```python
# Exemple 1 : lire un événement S3
def handler(event, context):
    s3 = event["Records"][0]["s3"]
    return s3["object"]["key"]

ev = {"Records": [{"s3": {
  "bucket": {"name": "data-platform-dev-raw"},
  "object": {"key": "bodacc/2026-10-23.json"}}}]}
handler(ev, None)  # → "bodacc/2026-10-23.json"
```

```python
# Exemple 2 : handler mince, logique testable
def compter_procol(annonces):
    return sum(a["type"] == "procol"
               for a in annonces)

def handler(event, context):
    return {"procol": compter_procol(event["annonces"])}

handler({"annonces": [{"type": "procol"},
                      {"type": "vente"}]}, None)
# → {"procol": 1}
```

- Quiz : `handler = "ingest.main"`, mais `ingest.py` ne définit que `handler` : quand l'erreur apparaît-elle ?
- [ ] Au `terraform plan`
- [ ] À l'`apply`, refusé par l'API
- [x] À la première invocation : `Runtime.HandlerNotFound`
- [ ] Jamais : Lambda prend la première fonction du module
- Réponse : à la première invocation : l'API ne charge pas le code au déploiement ; c'est le runtime qui cherche `main` dans `ingest` et échoue en `Runtime.HandlerNotFound`.

## 4. invocation : trois modes
- Sous-thème : invocation
- Niveau : 1
- Définition : Lambda s'invoque en synchrone (l'appelant attend la réponse), en asynchrone (file interne, réponse `202`) ou par un mapping qui lit une file ou un flux.
- Contexte : API Gateway et `aws lambda invoke` sont synchrones : l'erreur revient à l'appelant, qui décide seul de réessayer. S3, SNS et EventBridge sont asynchrones : Lambda réessaie elle-même. SQS, Kinesis et DynamoDB Streams passent par un event source mapping : Lambda interroge la source, et les retries suivent les règles de la source. Le mode décide qui voit l'erreur et qui réessaie.
- Usage : ✅ identifier le mode d'appel avant de concevoir retries et alertes · ❌ supposer les 2 retries automatiques partout : en synchrone, il n'y en a aucun.

```bash
# Exemple 1 : synchrone, on attend
aws lambda invoke \
  --function-name bodacc-ingest \
  --payload '{"jour":"2026-10-23"}' \
  --cli-binary-format raw-in-base64-out \
  out.json
# → {"StatusCode": 200, ...}
#   réponse du handler dans out.json
```

```bash
# Exemple 2 : asynchrone, on n'attend pas
aws lambda invoke \
  --function-name bodacc-ingest \
  --invocation-type Event \
  --payload '{"jour":"2026-10-23"}' \
  --cli-binary-format raw-in-base64-out \
  out.json
# → {"StatusCode": 202}, out.json vide
```

- Quiz : En synchrone, le handler lève une exception : quel `StatusCode` renvoie `aws lambda invoke` ?
- [ ] `500`
- [ ] `202`
- [x] `200`, avec `"FunctionError": "Unhandled"`
- [ ] `400`
- Réponse : `200` avec `FunctionError` : le code HTTP dit que l'appel à Lambda a réussi ; l'erreur du code est dans `FunctionError` et le corps de la réponse.

## 5. variables d'environnement : toujours des chaînes
- Sous-thème : déploiement
- Niveau : 1
- Définition : `environment.variables` passe une configuration (bucket, réglage) au code, qui la lit dans `os.environ` ; toutes les valeurs sont des chaînes.
- Contexte : La même archive sert en dev et en prod : seul le bucket change, injecté par Terraform. Terraform convertit `50` en `"50"` et `false` en `"false"` (vu dans le plan) : le code doit convertir lui-même. `os.environ["X"]` lève `KeyError` si la variable manque, `os.environ.get("X")` renvoie `None`. Les valeurs sont lisibles en clair par qui a `lambda:GetFunctionConfiguration`.
- Usage : ✅ noms de bucket, préfixes, réglages non sensibles · ❌ secret (jeton, mot de passe) : Secrets Manager ou Parameter Store, lus au démarrage.

```hcl
# Exemple 1 : injectées par Terraform
environment {
  variables = {
    RAW_BUCKET = "data-platform-dev-raw"
    MAX_PAGES  = 50 # devient "50"
  }
}
```

```python
# Exemple 2 : lire et convertir
import os
os.environ["MAX_PAGES"] = "50"  # simule Lambda
pages = int(os.environ["MAX_PAGES"])
pages + 1                       # → 51
os.environ.get("RAW_BUCKET_X")  # → None
```

- Quiz : Avec `DEBUG = false` dans Terraform, que vaut `bool(os.environ["DEBUG"])` dans la fonction ?
- [ ] `False`
- [x] `True`
- [ ] `"false"`
- [ ] `KeyError`
- Réponse : `True` : la variable vaut la chaîne `"false"`, non vide, donc vraie ; comparer explicitement (`== "true"`).

## 6. rôle d'exécution : les droits du code
- Sous-thème : sécurité
- Niveau : 1
- Définition : Le rôle d'exécution est le rôle IAM que la fonction endosse : il fixe ce que son code peut faire (lire S3, écrire ses logs).
- Contexte : Sa trust policy doit accepter `lambda.amazonaws.com`. Le SDK reçoit des identifiants temporaires de ce rôle, sans clé à gérer. Un droit manquant ne bloque pas le déploiement : `AccessDenied` arrive à l'exécution, à la première action refusée. `catalog-build` ne peut que lister et lire `sources/*`, écrire `content/catalog.json` et ses propres logs.
- Usage : ✅ un rôle par fonction, actions et ressources nommées (ARN, préfixe) · ❌ rôle partagé entre fonctions, `AmazonS3FullAccess` : une faille dans l'une ouvre tout.

```hcl
# Exemple 1 : qui peut endosser le rôle
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}
```

```hcl
# Exemple 2 : ce que le code peut faire
statement {
  sid       = "WriteCatalog"
  actions   = ["s3:PutObject"]
  resources = ["${local.content_arn}/content/catalog.json"]
}
# PutObject ailleurs → AccessDenied
```

- Quiz : Le rôle n'a aucun droit `logs:*` : que se passe-t-il à l'invocation ?
- [ ] `AccessDenied` avant même le handler
- [x] La fonction s'exécute, mais aucun log n'est écrit
- [ ] Lambda ajoute les droits de logs automatiquement
- [ ] Les logs partent dans un groupe par défaut du compte
- Réponse : la fonction s'exécute sans logs : l'écriture des logs échoue en silence ; on ne s'en aperçoit qu'en cherchant une trace absente.

## 7. /tmp : disque éphémère réutilisé
- Sous-thème : limites
- Niveau : 2
- Définition : `/tmp` est le disque local de Lambda (512 Mo par défaut, jusqu'à 10 Go via `ephemeral_storage`), lié à l'environnement d'exécution.
- Contexte : Un environnement chaud est réutilisé pour les invocations suivantes : `/tmp` et les variables de niveau module survivent d'un appel à l'autre. C'est utile pour un cache (client boto3, fichier de référence), dangereux pour des fichiers de travail : un reste de la veille peut être relu. Rien n'est garanti : un démarrage à froid repart d'un `/tmp` vide.
- Usage : ✅ fichier temporaire volumineux (décompression d'un `.gz`), cache explicite · ❌ état entre invocations : S3 ou DynamoDB ; fichiers de travail sans nom unique ni nettoyage.

```hcl
# Exemple 1 : 2 Go de /tmp
resource "aws_lambda_function" "i" {
  function_name = "bodacc-ingest"
  ephemeral_storage {
    size = 2048 # Mo, de 512 à 10240
  }
}
```

```python
# Exemple 2 : l'état survit (conteneur chaud)
vus = []   # niveau module : gardé

def handler(event, context):
    vus.append(event["jour"])
    return len(vus)

handler({"jour": "2026-10-23"}, None)  # → 1
handler({"jour": "2026-10-24"}, None)  # → 2
# même environnement : liste conservée
```

- Quiz : Deux invocations simultanées de la même fonction écrivent `/tmp/part.gz` : se marchent-elles dessus ?
- [ ] Oui : `/tmp` est partagé par la fonction
- [x] Non : chaque invocation concurrente a son environnement
- [ ] Oui, sauf avec `ephemeral_storage`
- [ ] Non : Lambda verrouille le fichier
- Réponse : non : un environnement ne traite qu'une invocation à la fois ; deux appels simultanés tournent dans deux environnements, chacun avec son `/tmp`.

## 8. invocation asynchrone : 2 retries
- Sous-thème : invocation
- Niveau : 2
- Définition : S3, SNS et EventBridge invoquent Lambda en asynchrone : sur erreur, Lambda réessaie jusqu'à 2 fois, puis abandonne l'événement.
- Contexte : L'événement passe par une file interne : l'appelant reçoit un `202` immédiat et ne voit jamais l'erreur. Les retries ont lieu après environ 1 puis 2 minutes ; `maximum_event_age_in_seconds` (60 à 21 600) borne l'attente. Sans destination d'échec, l'événement abandonné n'existe plus que dans les logs : impossible à rejouer.
- Usage : ✅ toujours une destination `on_failure` (SQS, SNS, EventBridge) sur une Lambda asynchrone du pipeline · ❌ `maximum_retry_attempts = 0` sur un traitement non idempotent sans alerte.

```hcl
# Exemple 1 : retries + destination
resource "aws_lambda_function_event_invoke_config" "i" {
  function_name = "bodacc-ingest"
  maximum_retry_attempts       = 2
  maximum_event_age_in_seconds = 3600
  destination_config {
    on_failure {
      destination = aws_sqs_queue.dlq.arn
    }
  }
}
```

- Quiz : Sans `destination_config`, que devient l'événement S3 après le troisième échec ?
- [x] Perdu : il ne reste qu'une trace dans les logs
- [ ] Renvoyé par S3 une heure plus tard
- [ ] Gardé dans une DLQ par défaut
- [ ] Réessayé jusqu'à `maximum_event_age_in_seconds`
- Réponse : perdu : sans destination ni DLQ, Lambda abandonne l'événement après 2 retries ; d'où une destination `on_failure` pour pouvoir le rejouer.

## 9. ECS Fargate : conteneur long
- Sous-thème : choisir
- Niveau : 2
- Définition : Fargate exécute un conteneur sans gérer de serveur ni de limite de durée : la solution pour un batch long ou une dépendance lourde.
- Contexte : On paie le vCPU et la mémoire réservés, à la seconde (minimum une minute), du démarrage à l'arrêt de la tâche. Lancée par Step Functions (`ecs:runTask.sync`), une tâche se comporte comme une étape du pipeline. En service ECS, elle tourne en continu, donc facture en continu. Le démarrage prend de l'ordre de la minute, contre quelques centaines de ms pour Lambda.
- Usage : ✅ reprise d'historique de plusieurs heures, outil natif lourd, processus permanent · ❌ traitement court déclenché par événement : Lambda, moins cher et plus réactif.

```
# Exemple 1 : la décision
Besoin  : reprise de 5 ans d'archives
          BODACC, ~3 h, lib native
→ Choix : tâche ECS Fargate lancée
          par Step Functions
Pourquoi: pas de plafond de 15 min,
          image Docker libre
Écarté  : Lambda (15 min),
          EC2 (serveur à patcher)
```

- Quiz : La même tâche doit maintenant tourner 24 h/24 pour lire un flux continu : quel choix ?
- [ ] Lambda relancée toutes les 15 min
- [ ] Glue en mode streaming, à la DPU-heure
- [x] Un service ECS sur Fargate
- [ ] Step Functions Express en boucle
- Réponse : un service ECS sur Fargate : un processus permanent n'entre pas dans un modèle à durée bornée ; Fargate facture alors 24 h/24, à intégrer au coût.

## 10. esbuild : un fichier, sans le SDK
- Sous-thème : déploiement
- Niveau : 2
- Définition : `esbuild --bundle` réunit le handler TypeScript et ses imports en un seul `.mjs` ; `--external:@aws-sdk/*` laisse le SDK au runtime Lambda.
- Contexte : Lambda Node n'exécute pas de TypeScript et ne voit que le zip : sans `--bundle`, `index.mjs` garde ses `import './catalog.ts'`, absents de l'archive. Le runtime `nodejs22.x` fournit le SDK v3 : l'exclure fait passer le bundle de 1,4 Mo à 9 ko (mesuré). `archive_file` zippe le résultat, `source_code_hash` ne redéploie que si le code change.
- Usage : ✅ Lambda Node en TS qui utilise le SDK v3 du runtime · ❌ version précise du SDK exigée : l'embarquer ; `aws-sdk` v2 : absent des runtimes depuis Node 18.

```bash
# Exemple 1 : script "lambda" de l'app
esbuild lambda/handler.ts --bundle \
  --platform=node --target=node22 \
  --format=esm \
  '--external:@aws-sdk/*' \
  --outfile=dist-lambda/index.mjs
# → index.mjs 9 ko, un seul import :
#   "@aws-sdk/client-s3"
# sans --external : 1,4 Mo
```

- Quiz : Tapée dans zsh, sans guillemets, que donne `esbuild lambda/handler.ts --bundle --external:@aws-sdk/*` ?
- [ ] Un bundle de 9 ko, comme `pnpm lambda`
- [ ] Un bundle de 1,4 Mo : le motif est ignoré
- [x] `zsh: no matches found` : esbuild n'est pas lancé
- [ ] Une erreur d'esbuild : motif invalide
- Réponse : `no matches found` (mesuré) : zsh développe `*` lui-même et échoue faute de fichier ; quoter le motif. `pnpm lambda` passe par `sh`, qui laisse un motif sans correspondance tel quel.

## 11. cold start : initialiser hors du handler
- Sous-thème : invocation
- Niveau : 2
- Définition : Un démarrage à froid crée un environnement neuf et exécute le code de niveau module (imports, clients) avant le premier appel, puis le réutilise.
- Contexte : Mesuré sur `catalog-build` : `Init Duration` d'environ 300 ms, puis 1,4 à 1,9 s par appel. Créer le client S3 au niveau module le paie une fois par environnement, pas à chaque appel. L'init est facturée : `Billed Duration` 1 913 ms pour 1 617 ms d'appel et 296 ms d'init (mesuré). Un import lourd (pandas) allonge chaque démarrage à froid.
- Usage : ✅ clients SDK, configuration, connexions créés au niveau module · ❌ client créé dans le handler : refait à chaque appel ; état métier en module (voir `/tmp`).

```python
# Exemple 1 : init une fois par environnement
inits = 0
def creer_client():
    global inits
    inits += 1
    return object()  # ≈ boto3.client("s3")

CLIENT = creer_client()  # niveau module

def handler(event, context):
    return id(CLIENT)

handler({}, None) == handler({}, None)  # → True
inits  # → 1
```

```bash
# Exemple 2 : ligne REPORT (mesurée)
# Duration: 1616.56 ms
# Billed Duration: 1913 ms
# Init Duration: 296.01 ms
# → init facturée au 1er appel
# appel chaud : pas d'Init Duration
```

- Quiz : Dix jours BODACC arrivent en même temps sur une fonction sans environnement chaud : combien de lignes avec `Init Duration` ?
- [ ] `1`
- [ ] `0`
- [x] `10`
- [ ] `2`
- Réponse : `10` : un environnement ne traite qu'un appel à la fois ; dix appels simultanés créent dix environnements, chacun avec son démarrage à froid.

## 12. lambda_permission : qui peut invoquer
- Sous-thème : sécurité
- Niveau : 2
- Définition : `aws_lambda_permission` ajoute une ligne à la politique de ressource de la fonction : elle autorise un service (S3, EventBridge) à l'invoquer.
- Contexte : Deux politiques distinctes : le rôle d'exécution dit ce que la fonction peut faire, la politique de ressource dit qui peut l'appeler. `source_arn` et `source_account` bornent l'appel à ce bucket de ce compte : sans eux, n'importe quel bucket S3 configuré vers la fonction pourrait la déclencher. Lu sur le compte : conditions `AWS:SourceArn` et `AWS:SourceAccount`.
- Usage : ✅ une permission par source, bornée par `source_arn` · ❌ croire que le rôle d'exécution suffit : il ne donne à aucun service le droit d'appeler la fonction.

```hcl
# Exemple 1 : infra/lambda.tf
resource "aws_lambda_permission" "s3" {
  statement_id   = "AllowS3Invoke"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.catalog_build.function_name
  principal      = "s3.amazonaws.com"
  source_arn     = aws_s3_bucket.this["content"].arn
  source_account = var.account_id
}
```

```bash
# Exemple 2 : lu sur le compte
aws lambda get-policy --function-name \
  revision-pwa-dev-catalog-build
# → "Principal": {"Service": "s3.amazonaws.com"}
#   "ArnLike": {"AWS:SourceArn":
#     "arn:aws:s3:::revision-pwa-dev-content-…"}
```

- Quiz : Sans cette permission, que fait l'`apply` de `aws_s3_bucket_notification` ?
- [x] Il échoue : S3 ne peut pas valider la destination
- [ ] Il passe, les événements sont refusés ensuite
- [ ] Il passe et crée la permission tout seul
- [ ] Il passe, S3 utilise le rôle d'exécution
- Réponse : il échoue (`Unable to validate the following destination configurations`) : S3 vérifie le droit d'invoquer dès la création de la notification, d'où `depends_on` sur la permission.

## 13. logs : un flux par environnement
- Sous-thème : logs
- Niveau : 2
- Définition : Lambda envoie `print` et les lignes du runtime dans CloudWatch Logs, groupe `/aws/lambda/<nom>` par défaut, un flux par environnement d'exécution.
- Contexte : Chaque appel écrit `START`, les sorties du code, `END` et `REPORT` (durée, mémoire max). `logging_config` choisit le groupe et le format, `Text` ou `JSON` (champs filtrables). Créé par Terraform, le groupe a une rétention bornée (14 jours ici) ; créé par Lambda, il n'expire jamais. Les appels d'un même environnement se suivent dans un flux : retrouver un appel précis passe par son `RequestId`.
- Usage : ✅ groupe Terraform à rétention bornée, `aws logs tail` pour suivre · ❌ ouvrir les flux un par un : `filter-log-events` sur un motif (`REPORT`, `RequestId`).

```hcl
# Exemple 1 : groupe et format choisis
logging_config {
  log_format = "Text" # ou "JSON"
  log_group  = aws_cloudwatch_log_group.catalog_build.name
}
```

```bash
# Exemple 2 : les dernières durées
aws logs filter-log-events \
  --log-group-name \
  /aws/lambda/revision-pwa-dev-catalog-build \
  --filter-pattern '"REPORT"' \
  --query 'events[-1].message'
# → REPORT … Duration: 1919.38 ms
#   Max Memory Used: 150 MB
```

- Quiz : `aws logs tail /aws/lambda/bodacc-ingest`, sans `--since` : que montre-t-il ?
- [ ] Tout depuis la création du groupe
- [x] Les 10 dernières minutes
- [ ] Les 100 dernières lignes
- [ ] Seulement les nouvelles lignes, en continu
- Réponse : les 10 dernières minutes : c'est le défaut de `--since` ; `--follow` ajoute le suivi en continu, `--since 1d` remonte plus loin.

## 14. arm64 : Graviton, 20 % moins cher
- Sous-thème : déploiement
- Niveau : 2
- Définition : `architectures = ["arm64"]` exécute la fonction sur processeur Graviton, environ 20 % moins cher à la milliseconde que `x86_64`.
- Contexte : Le JavaScript et le Python pur tournent tel quel : `catalog-build` est en arm64 (lu sur le compte). Les dépendances natives (pydantic-core, numpy, lxml) sont des binaires compilés pour un système et un processeur : il faut empaqueter les roues Linux aarch64, pas celles de la machine de build. Le défaut, sans l'attribut, reste `x86_64`.
- Usage : ✅ arm64 par défaut pour toute nouvelle fonction · ❌ dépendance native sans roue aarch64 publiée : rester en `x86_64`.

```python
# Exemple 1 : prix au Go-s (us-east-1)
x86 = 0.0000166667
arm = 0.0000133334
round(1 - arm / x86, 2)  # → 0.2
```

```bash
# Exemple 2 : roues pour Lambda arm64
uv pip install pydantic \
  --python-platform aarch64-manylinux_2_28 \
  --python-version 3.12 \
  --target build/
# → binaires Linux aarch64 dans build/
```

- Quiz : Le zip embarque `pydantic_core` installé sur un Mac M1 : fonctionne-t-il sur Lambda arm64 ?
- [ ] Oui : même processeur ARM
- [ ] Oui, si le runtime est `python3.12`
- [x] Non : binaire macOS, pas Linux
- [ ] Non : Lambda refuse le code natif
- Réponse : non : le processeur est le même, mais le binaire est compilé pour macOS ; Lambda tourne sous Linux et l'import échoue.

## 15. event source mapping : Lambda lit la file
- Sous-thème : invocation
- Niveau : 2
- Définition : Un event source mapping est un lecteur géré par Lambda qui interroge SQS, Kinesis ou DynamoDB Streams et invoque la fonction par lots.
- Contexte : C'est Lambda qui lit la file, avec le rôle d'exécution : il lui faut `sqs:ReceiveMessage`, `DeleteMessage` et `GetQueueAttributes`, et aucune `aws_lambda_permission`. L'appel est synchrone : `maximum_retry_attempts` de l'asynchrone ne joue pas ; pour SQS, le visibility timeout et `maxReceiveCount` de la file décident des retries. `enabled = false` met la lecture en pause sans perdre de message.
- Usage : ✅ consommer une file de jours à rejouer, un flux Kinesis · ❌ régler les retries dans `aws_lambda_function_event_invoke_config` : réglage de la file à la place.

```hcl
# Exemple 1 : la file → la fonction
resource "aws_lambda_event_source_mapping" "m" {
  event_source_arn = aws_sqs_queue.jours.arn
  function_name    = aws_lambda_function.i.arn
  batch_size       = 10
  enabled          = true # false = pause
}
```

```hcl
# Exemple 2 : droits sur le rôle d'exécution
statement {
  actions = ["sqs:ReceiveMessage",
  "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
  resources = [aws_sqs_queue.jours.arn]
}
```

- Quiz : Le rôle d'exécution n'a pas `sqs:ReceiveMessage` : que se passe-t-il ?
- [x] La création du mapping échoue
- [ ] Le mapping lit avec les droits de la file
- [ ] Les messages partent en DLQ
- [ ] Le mapping est créé et reste vide, sans erreur
- Réponse : la création échoue : Lambda vérifie que le rôle d'exécution peut lire la file (`ReceiveMessage`) et refuse le mapping sinon.

## 16. couches : dépendances dans /opt
- Sous-thème : déploiement
- Niveau : 2
- Définition : Une couche (layer) est un zip monté dans `/opt` de l'environnement : dépendances partagées entre fonctions, versionnées à part du code.
- Contexte : Au plus 5 couches par fonction, 250 Mo décompressés au total avec le code. Pour Python, le contenu doit être sous `python/` dans le zip : il arrive dans `/opt/python`, déjà dans `sys.path`. Chaque publication crée une version immuable (`:3`) ; la fonction référence un ARN versionné. Une image conteneur n'accepte pas de couche : tout va dans l'image.
- Usage : ✅ dépendance lourde commune à plusieurs fonctions (pydantic, httpx) · ❌ une seule fonction : tout dans le zip, plus simple ; Node bundlé par esbuild : rien à partager.

```hcl
# Exemple 1 : publier et attacher
resource "aws_lambda_layer_version" "deps" {
  layer_name          = "bodacc-deps"
  filename            = "layer.zip"
  compatible_runtimes = ["python3.12"]
}
# dans aws_lambda_function :
#   layers = [aws_lambda_layer_version.deps.arn]
```

```text
# Exemple 2 : structure du zip
layer.zip
└── python/
    ├── pydantic/
    └── httpx/
# → /opt/python/pydantic dans Lambda
```

- Quiz : Le zip de la couche contient `pydantic/` à la racine, sans `python/` : que donne `import pydantic` ?
- [ ] Ça marche : `/opt` est dans `sys.path`
- [ ] Erreur dès la publication de la couche
- [x] `ModuleNotFoundError`
- [ ] Ça marche seulement en arm64
- Réponse : `ModuleNotFoundError` : le dossier arrive en `/opt/pydantic`, or seul `/opt/python` (et son `site-packages`) est dans `sys.path`.

## 17. récursion : ne pas écrire dans sa source
- Sous-thème : invocation
- Niveau : 2
- Définition : Une fonction qui écrit dans la ressource qui la déclenche (bucket, file) se relance elle-même : boucle infinie, facturée à chaque tour.
- Contexte : `catalog-build` est déclenchée par `sources/*.md` et n'écrit que `content/catalog.json` : entrée et sortie séparées par préfixe, filtre sur la notification. Lambda détecte les boucles qui passent par SQS, SNS, S3 et les bus EventBridge personnalisés, et coupe après environ 16 tours d'une même chaîne. Une boucle via DynamoDB n'est pas détectée (doc AWS).
- Usage : ✅ préfixes d'entrée et de sortie distincts, `filter_prefix` sur la notification · ❌ compter sur la détection : elle arrive après une quinzaine d'appels facturés.

```hcl
# Exemple 1 : entrée sources/, sortie content/
lambda_function {
  lambda_function_arn = aws_lambda_function.catalog_build.arn
  events        = ["s3:ObjectCreated:*"]
  filter_prefix = "sources/"
  filter_suffix = ".md"
}
# écrire content/catalog.json : pas d'appel
```

- Quiz : Même notification, mais la fonction écrit aussi `sources/index.md` : que se passe-t-il ?
- [ ] Rien : S3 ignore les écritures faites par Lambda
- [ ] Une seule relance, puis S3 déduplique
- [ ] `AccessDenied` : on n'écrit pas dans sa source
- [x] Une boucle, coupée par Lambda après ~16 tours
- Réponse : une boucle : chaque écriture sous `sources/` en `.md` redéclenche la fonction ; Lambda arrête la chaîne vers 16 appels et le signale.

## 18. concurrence réservée : une exécution à la fois
- Sous-thème : invocation
- Niveau : 3
- Définition : `reserved_concurrent_executions = 1` limite la fonction à une exécution simultanée : les invocations suivantes attendent au lieu de tourner en parallèle.
- Contexte : `catalog-build` relit toutes les sources et réécrit tout `catalog.json` : l'événement S3 n'est qu'un signal, son ordre et ses doublons (livraison « au moins une fois ») ne comptent pas. Deux exécutions parallèles, si : la plus lente, qui a listé avant le dernier dépôt, écraserait un catalogue complet. La réserve est prise sur les 1 000 du compte (999 non réservées, mesuré).
- Usage : ✅ traitement qui réécrit un résultat global (catalogue, index, agrégat) · ❌ traitement par objet indépendant : parallélisme bridé pour rien ; `0` coupe toute invocation.

```hcl
# Exemple 1 : infra/lambda.tf
resource "aws_lambda_function" "catalog" {
  function_name = "revision-pwa-dev-catalog-build"
  runtime       = "nodejs22.x"
  # une seule exécution à la fois
  reserved_concurrent_executions = 1
}
```

```bash
# Exemple 2 : lu sur le compte
aws lambda get-function-concurrency \
  --function-name \
  revision-pwa-dev-catalog-build
# → "ReservedConcurrentExecutions": 1
```

- Quiz : Trois dépôts S3 arrivent pendant qu'une exécution tourne : que deviennent leurs événements ?
- [ ] Perdus : S3 reçoit un refus `429`
- [ ] Fusionnés en un seul appel par S3
- [x] Gardés en file par Lambda, rejoués dès qu'une place se libère
- [ ] Envoyés aussitôt en destination d'échec
- Réponse : gardés et rejoués : l'appel S3 est asynchrone, Lambda retente les événements limités (throttling) jusqu'à `maximum_event_age` (6 h par défaut), hors des 2 retries d'erreur.

## 19. versions et alias : figer le code
- Sous-thème : déploiement
- Niveau : 3
- Définition : `publish = true` crée une version immuable à chaque changement ; un alias (`live`) pointe vers une version et donne aux appelants un ARN stable.
- Contexte : `$LATEST` est la seule version modifiable : c'est elle qu'appelle l'ARN nu, et la seule de `catalog-build` (lu sur le compte). Une version fige le code et la configuration (variables, mémoire, timeout). Revenir en arrière revient à repointer l'alias ; `routing_config` peut aussi répartir le trafic entre deux versions pour un déploiement progressif.
- Usage : ✅ prod derrière un alias : rollback immédiat, concurrence provisionnée · ❌ dev redéployé souvent : `$LATEST` suffit, les versions publiées s'accumulent.

```hcl
# Exemple 1 : alias sur la dernière version
resource "aws_lambda_function" "i" {
  function_name = "bodacc-ingest"
  publish       = true # nouvelle version
}
resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = aws_lambda_function.i.function_name
  function_version = aws_lambda_function.i.version
}
```

- Quiz : L'alias `live` est figé sur `"3"` ; on change `RAW_BUCKET` et on applique : quel bucket lit `live` ?
- [x] L'ancien : la version 3 garde sa configuration
- [ ] Le nouveau : les variables ne sont pas versionnées
- [ ] Le nouveau, après un démarrage à froid
- [ ] Aucun : l'`apply` est refusé
- Réponse : l'ancien : une version fige aussi les variables ; seule `$LATEST` et les versions publiées ensuite voient le nouveau bucket.

## 20. concurrence provisionnée : pas de démarrage à froid
- Sous-thème : invocation
- Niveau : 3
- Définition : La concurrence provisionnée garde N environnements initialisés en permanence sur une version ou un alias : aucun démarrage à froid jusqu'à N appels simultanés.
- Contexte : Contrairement à la concurrence réservée (un plafond, gratuit), elle se paie à l'heure, même sans trafic. L'init tourne à l'allocation, pas au premier appel. Au-delà de N, les appels passent sur des environnements à la demande, avec démarrage à froid. Elle exige une version publiée ou un alias.
- Usage : ✅ API synchrone sensible à la latence, pic prévisible (programmable) · ❌ pipeline asynchrone : 300 ms d'init n'y comptent pas, payer 24 h/24 si.

```hcl
# Exemple 1 : 2 environnements toujours prêts
resource "aws_lambda_provisioned_concurrency_config" "p" {
  function_name = aws_lambda_function.i.function_name
  qualifier     = aws_lambda_alias.live.name
  provisioned_concurrent_executions = 2
}
# 3e appel simultané → à la demande
```

- Quiz : `qualifier = "$LATEST"` dans cette ressource : que donne l'`apply` ?
- [ ] Accepté : `$LATEST` est une version comme une autre
- [x] Refusé : il faut une version publiée ou un alias
- [ ] Accepté, mais sans effet
- [ ] Accepté, appliqué à toutes les versions
- Réponse : refusé : la concurrence provisionnée prépare un code figé ; `$LATEST`, modifiable, n'est pas accepté.

## 21. destinations ou DLQ : garder l'erreur
- Sous-thème : invocation
- Niveau : 3
- Définition : En asynchrone, une destination `on_failure` reçoit l'événement et l'erreur ; la DLQ de la fonction (`dead_letter_config`) ne reçoit que l'événement d'origine.
- Contexte : L'enregistrement de destination porte `requestContext` (tentatives, condition), `requestPayload` et `responsePayload` (type et message d'erreur) : on sait pourquoi l'événement a échoué. La DLQ, plus ancienne, se limite à SQS ou SNS et à l'événement brut. `on_success` chaîne vers une autre cible sans code. Rien de cela ne joue en synchrone.
- Usage : ✅ `on_failure` vers SQS ou un bus EventBridge pour toute fonction asynchrone · ❌ DLQ de fonction quand l'erreur compte pour rejouer : elle ne la garde pas.

```hcl
# Exemple 1 : échecs et succès routés
resource "aws_lambda_function_event_invoke_config" "c" {
  function_name = aws_lambda_function.i.function_name
  destination_config {
    on_failure {
      destination = aws_sqs_queue.dlq.arn
    }
    on_success {
      destination = aws_cloudwatch_event_bus.dp.arn
    }
  }
}
```

```json
# Exemple 2 : ce que reçoit on_failure
{"requestContext": {
   "condition": "RetriesExhausted",
   "approximateInvokeCount": 3},
 "requestPayload": {"jour": "2026-10-23"},
 "responsePayload": {
   "errorType": "BodaccError",
   "errorMessage": "429 après 5 essais"}}
```

- Quiz : Une fonction consommée par un mapping SQS a une `dead_letter_config` : un message toxique y arrive-t-il ?
- [ ] Oui, après `maxReceiveCount` échecs
- [ ] Oui, dès le premier échec
- [x] Non : il faut une redrive policy sur la file source
- [ ] Non : un mapping SQS ne réessaie jamais
- Réponse : non : la DLQ de fonction ne sert qu'à l'asynchrone ; avec un mapping, c'est la redrive policy de la file source qui isole le message.
