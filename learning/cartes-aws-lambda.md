---
title: "Cartes · Lambda (AWS)"
type: cartes
langage: AWS
cours: Lambda
created: 2026-10-24
updated: 2026-10-25
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

## 7. os.environ[…] : échouer tout de suite
- Sous-thème : déploiement
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `os.environ["RAW_BUCKET"]` lève `KeyError` si la variable manque ; `.get("RAW_BUCKET")` renvoie `None` sans rien dire.
- Contexte : Une variable obligatoire absente (bucket, table) signale une configuration Terraform fausse : mieux vaut une invocation en échec avec `KeyError: 'RAW_BUCKET'` dans CloudWatch qu'un `None` qui voyage jusqu'à boto3 et casse loin de la cause, ou un défaut silencieux qui écrit dans le mauvais bucket. ≈ `process.env.X!` en TS, sauf qu'ici la vérification a vraiment lieu.
- Usage : ✅ `os.environ["X"]` pour une config obligatoire, `.get("X", défaut)` pour une option (niveau de log) · ❌ `.get("RAW_BUCKET", "dp-raw")` : un oubli de config écrit en silence ailleurs.

```python
# Exemple 1 : obligatoire ou facultatif
import os
os.environ.pop("RAW_BUCKET", None)
os.environ.pop("LOG_LEVEL", None)
os.environ.get("RAW_BUCKET")  # → None
os.environ.get("LOG_LEVEL", "INFO")
# → "INFO"
os.environ["RAW_BUCKET"]  # ❌ KeyError
```

```python
# Exemple 2 : le message nomme la variable
import os
os.environ.pop("RAW_BUCKET", None)
try:
    os.environ["RAW_BUCKET"]
except KeyError as e:
    msg = str(e)
msg  # → "'RAW_BUCKET'"
```

- Quiz : `bucket = os.environ.get("RAW_BUCKET")` sans la variable, puis `s3.put_object(Bucket=bucket, …)` : que se passe-t-il ?
- [ ] `KeyError: 'RAW_BUCKET'`
- [ ] Un objet écrit dans un bucket `None`
- [x] `TypeError` levé dans botocore
- [ ] `NoSuchBucket` renvoyé par S3
- Réponse : `TypeError` dans botocore (mesuré sous moto : expected string or bytes-like object) : le `None` passe le handler et casse dans le SDK, loin de la vraie cause.

## 8. context.aws_request_id : relier un log à son appel
- Sous-thème : logs
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `context.aws_request_id` est l'identifiant unique de l'invocation, le même que celui des lignes `START`, `END` et `REPORT` de CloudWatch.
- Contexte : Un flux de logs enchaîne les appels successifs d'un environnement chaud : mettre `request_id` dans la ligne JSON du handler relie ses champs (date, count) à la ligne `REPORT` (durée, mémoire) du même appel. En test, `context` vaut souvent `None` : `getattr(context, "aws_request_id", None)` évite l'`AttributeError`. Un faux `context` se fabrique avec `SimpleNamespace`.
- Usage : ✅ champ `request_id` de chaque log structuré, recherche d'un appel précis dans Logs Insights · ❌ s'en servir comme clé d'idempotence : un rejeu par Step Functions est une nouvelle invocation ; la clé vient de l'événement (la date).

```python
# Exemple 1 : un faux context en test
from types import SimpleNamespace
ctx = SimpleNamespace(
    aws_request_id="req-123")
def handler(event, context):
    return getattr(context,
                   "aws_request_id", None)
handler({}, ctx)   # → "req-123"
handler({}, None)  # → None
```

```python
# Exemple 2 : sans getattr, None casse
def handler(event, context):
    return context.aws_request_id
handler({}, None)  # ❌ AttributeError
```

- Quiz : Step Functions rejoue la même date après un échec du handler : le `aws_request_id` du rejeu est-il le même ?
- [ ] Oui : même événement, même identifiant
- [ ] Oui, si l'environnement est resté chaud
- [x] Non : c'est une nouvelle invocation
- Réponse : non (doc AWS) : chaque appel `Invoke` de Step Functions crée une invocation avec son propre identifiant ; seule la date de l'événement relie les deux essais.

## 9. valeur de retour : sérialisée en JSON
- Sous-thème : invocation
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Le runtime sérialise en JSON ce que renvoie le handler ; un objet non sérialisable (`date`, `set`) fait échouer l'invocation.
- Contexte : En Node, `JSON.stringify` change une `Date` en chaîne sans broncher ; en Python, `json.dumps(date(…))` lève `TypeError`, et Lambda répond `Runtime.MarshalError` (doc AWS) alors que le travail, l'écriture S3, est déjà fait. D'où `day.isoformat()` dans le résultat de `ingest_day`. Le dict renvoyé devient la sortie de l'état Step Functions.
- Usage : ✅ renvoyer `str`, nombres, listes, dicts (`isoformat()`, `sorted(un_set)`) · ❌ renvoyer une `date`, un `set` ou un objet métier : convertir avant le `return`.

```python
# Exemple 1 : ce que fait le runtime
import json
from datetime import date
d = date(2026, 10, 20)
json.dumps({"date": d.isoformat()})
# → '{"date": "2026-10-20"}'
json.dumps({"date": d})  # ❌ TypeError
```

```python
# Exemple 2 : un set non plus
import json
cles = {"bodacc/part-0001.jsonl.gz"}
json.dumps({"keys": cles})  # ❌ TypeError
json.dumps({"keys": sorted(cles)})
# → '{"keys": ["bodacc/part-0001.jsonl.gz"]}'
```

- Quiz : Le handler écrit le fichier S3 puis renvoie `{"date": date(2026, 10, 20)}` : état de S3 et de l'invocation ?
- [ ] Rien d'écrit : Lambda annule l'invocation
- [ ] Fichier écrit, invocation réussie avec `"2026-10-20"`
- [x] Fichier écrit, invocation en échec
- [ ] Fichier écrit, invocation réussie avec `null`
- Réponse : fichier écrit, invocation en échec : la sérialisation a lieu après le `return`, S3 n'a pas de retour arrière ; l'appelant voit une erreur et rejoue un travail déjà fait.

## 10. zip : le paquet du handler à la racine
- Sous-thème : déploiement
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `handler = "ingest_bodacc.handler.lambda_handler"` désigne `module.fonction` : le paquet `ingest_bodacc/` doit être à la racine du zip.
- Contexte : Lambda décompresse le zip dans `/var/task`, en tête de `sys.path`, puis importe le module du handler. Un zip qui garde `src/ingest_bodacc/` ou `build/package/…` dans ses noms donne `Runtime.ImportModuleError: No module named 'ingest_bodacc'`. Le src layout ne concerne que le dépôt : `uv pip install --target` met le paquet à plat. On vérifie avec `unzip -l`.
- Usage : ✅ installer membres et dépendances dans un dossier, zipper son contenu (pas le dossier lui-même) · ❌ `zip -r build.zip build/` : tout arrive sous `build/`.

```bash
# Exemple 1 : le zip vu par Lambda
unzip -l build/ingest-bodacc.zip \
  | grep -E ' (ingest_bodacc|bodacc_client)/__init__'
# bodacc_client/__init__.py
# ingest_bodacc/__init__.py
# → handler : ingest_bodacc.handler.lambda_handler
```

```python
# Exemple 2 : src/ resté dans le zip
import importlib, io, sys, tempfile, zipfile
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("src/demo_ingest/__init__.py", "")
task = tempfile.mkdtemp()        # ≈ /var/task
zipfile.ZipFile(buf).extractall(task)
sys.path.insert(0, task)
importlib.import_module("demo_ingest")  # ❌ ModuleNotFoundError
```

- Quiz : Handler `handler.lambda_handler`, fichier en `ingest_bodacc/handler.py` dans le zip : que se passe-t-il ?
- [ ] Ça marche : Lambda cherche dans tous les dossiers
- [ ] `Runtime.HandlerNotFound`
- [x] `Runtime.ImportModuleError`
- [ ] Le déploiement est refusé
- Réponse : `Runtime.ImportModuleError` : seul `/var/task` est dans `sys.path`, il n'y a pas de module `handler` à sa racine ; `HandlerNotFound` vise une fonction absente d'un module trouvé.

## 11. aws_lambda_function : une seule source de code
- Sous-thème : déploiement
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `aws_lambda_function` prend son code d'une seule source : `filename` (zip local), `s3_bucket` + `s3_key` (zip sur S3) ou `image_uri` (image ECR).
- Contexte : Avec S3, Terraform ne lit jamais le zip : il transmet bucket et clé à l'API `CreateFunction`, et Lambda copie l'objet. `filename` impose le zip sur le poste qui lance `apply`, donc un build juste avant, dans le même job. S3 découple le build du déploiement : un job construit et publie, un autre déploie, sur n'importe quel environnement.
- Usage : ✅ `s3_bucket`/`s3_key` dès qu'une CI construit et qu'un autre job déploie · ❌ `filename` vers `build/` en CI : le job de déploiement devrait reconstruire le zip.

```hcl
# Exemple 1 : le code vient de S3
resource "aws_lambda_function" "this" {
  function_name = var.name
  role          = aws_iam_role.this.arn
  runtime       = "python3.12"
  handler       = var.handler
  s3_bucket     = var.artifact.bucket
  s3_key        = var.artifact.key
}
```

```hcl
# Exemple 2 : s3_bucket sans s3_key
resource "aws_lambda_function" "f" {
  function_name = var.name
  role          = aws_iam_role.this.arn
  s3_bucket     = var.artifact.bucket
}
# terraform validate
# → "s3_bucket": all of
#   `s3_bucket,s3_key` must be specified
```

- Quiz : `filename` et `s3_bucket`/`s3_key` déclarés ensemble dans la fonction : que fait Terraform ?
- [ ] Il prend `filename`, prioritaire
- [ ] Il envoie le zip local dans le bucket
- [x] `validate` échoue : une seule source
- [ ] Il prend le zip S3, plus récent
- Réponse : `validate` échoue : « only one of `filename,image_uri,s3_bucket` can be specified » (vérifié avec le provider AWS 6.69), sans aucun appel à AWS.

## 12. log group : le créer avant la fonction
- Sous-thème : logs
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Terraform crée `/aws/lambda/<nom>` avant la fonction ; sinon Lambda le crée à la première invocation, hors de l'état Terraform.
- Contexte : Un groupe créé par Lambda n'a pas de rétention (logs gardés et facturés sans fin) et survit à `make down`, puisque Terraform ne le connaît pas. Déclaré dans le module, il a sa rétention (14 jours) et disparaît avec l'environnement. La référence `log_group = aws_cloudwatch_log_group.this.name` dans `logging_config` suffit à ordonner la création : groupe d'abord, fonction ensuite.
- Usage : ✅ un `aws_cloudwatch_log_group` par fonction, dans le même module · ❌ laisser Lambda créer le groupe : rétention infinie, ressource orpheline.

```hcl
# Exemple 1 : le groupe, puis la fonction
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = 14
}
resource "aws_lambda_function" "this" {
  function_name = var.name
  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.this.name
  }
}
```

- Quiz : La fonction a déjà tourné et Lambda a créé son groupe ; on ajoute ensuite `aws_cloudwatch_log_group` au code : que fait `apply` ?
- [ ] Il adopte le groupe existant
- [x] Erreur : le groupe existe déjà
- [ ] Il crée un second groupe suffixé
- [ ] Il remplace le groupe, logs perdus
- Réponse : erreur `ResourceAlreadyExistsException` : Terraform ne reprend jamais seul un objet existant ; un bloc `import` (ou `terraform import`) le rattache d'abord.

## 13. rôle : un par fonction
- Sous-thème : sécurité
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Chaque Lambda reçoit son propre rôle d'exécution, créé par le module avec elle : ses droits sont déclarés à côté de sa configuration.
- Contexte : Un rôle partagé additionne les besoins de toutes les fonctions : chacune hérite des droits des autres, et retirer un droit devient risqué faute de savoir qui l'utilise. Un rôle par fonction ne coûte rien (IAM est gratuit) et se détruit avec elle. Le rôle générique `lambda` de S1-04 (lire `raw`, écrire `processed`) aurait donné à l'ingestion l'inverse de ce dont elle a besoin.
- Usage : ✅ une Lambda, un rôle, une politique `app` sur mesure passée au module · ❌ un rôle « lambda » commun à tout le projet : le moindre privilège devient intenable.

```hcl
# Exemple 1 : les droits à côté de la config
locals {
  lambdas = {
    ingest-bodacc = {
      handler = "ingest_bodacc.handler.lambda_handler"
      timeout = 300
      policy_json = data.aws_iam_policy_document.ingest_bodacc.json
    }
  }
}
# module "lambda" crée un rôle par entrée
# → data-platform-dev-ingest-bodacc
```

- Quiz : Un rôle est partagé par 30 Lambdas ; une seule a besoin de `s3:DeleteObject` sur `raw`, ajouté au rôle : qui peut supprimer ?
- [ ] Seulement la Lambda qui en a besoin
- [x] Les 30 Lambdas
- [ ] Aucune sans politique de bucket
- [ ] Celles qui déclarent `DeleteObject` dans leur code
- Réponse : les 30 : les droits sont portés par le rôle, pas par la fonction ; une faille dans n'importe laquelle peut alors vider `raw`.

## 14. --cli-binary-format : le payload en JSON brut
- Sous-thème : invocation
- Niveau : 1
- Source : data-platform · S1-07
- Définition : En CLI v2, `--payload` est lu comme du base64 ; `--cli-binary-format raw-in-base64-out` le fait lire comme du JSON brut.
- Contexte : Sans l'option, la CLI décode `{"date":…}` comme du base64, envoie des octets illisibles, et Lambda répond `InvalidRequestContentException … Invalid UTF-8 start byte`. Le message accuse le JSON, pas l'option : piège classique en passant de la v1 à la v2. Se règle une fois pour toutes dans `~/.aws/config` : `cli_binary_format = raw-in-base64-out`.
- Usage : ✅ toute invocation manuelle avec un payload JSON écrit à la main · ❌ chercher l'erreur dans le JSON quand le message parle d'UTF-8 : ajouter l'option.

```bash
# Exemple 1 : sans l'option
aws lambda invoke \
  --function-name "$F" \
  --payload '{"date":"2026-10-20"}' \
  out.json
# → InvalidRequestContentException:
#   Could not parse payload into json:
#   Invalid UTF-8 start byte 0xab
```

```ini
# Exemple 2 : réglé pour le profil
[profile data-platform]
region = eu-west-3
cli_binary_format = raw-in-base64-out
```

- Quiz : D'où vient l'octet `0xab` du message d'erreur ?
- [ ] D'un accent dans le JSON
- [x] Du décodage base64 de `{"date"…}`
- [ ] Du BOM ajouté par zsh
- [ ] De la compression du payload par la CLI
- Réponse : du décodage base64 : la CLI v2 décode le texte comme du base64 ; les octets obtenus ne forment pas de l'UTF-8 valide.

## 15. /tmp : disque éphémère réutilisé
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

## 16. invocation asynchrone : 2 retries
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

## 17. ECS Fargate : conteneur long
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

## 18. esbuild : un fichier, sans le SDK
- Sous-thème : déploiement
- Niveau : 2
- Source : revision-pwa · pwa-revision
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

## 19. cold start : initialiser hors du handler
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

## 20. lambda_permission : qui peut invoquer
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

## 21. logs : un flux par environnement
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

## 22. arm64 : Graviton, 20 % moins cher
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

## 23. event source mapping : Lambda lit la file
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

## 24. couches : dépendances dans /opt
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

## 25. récursion : ne pas écrire dans sa source
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

## 26. boto3 : celui du runtime ou le sien
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le runtime Python de Lambda fournit `boto3`, dans une version choisie et mise à jour par AWS ; l'embarquer dans le zip la fige.
- Contexte : `sys.path` lit `/var/task` (le zip), puis `/opt/python` (couches), puis `/var/runtime` (le SDK d'AWS) : le premier `boto3` trouvé gagne. Sans SDK embarqué, le code tourne avec la version du runtime, souvent plus ancienne que celle des tests, et AWS peut la changer sans redéploiement. AWS recommande d'embarquer le SDK en production. Coût : ~28 Mo décompressés (`botocore` surtout).
- Usage : ✅ Lambda de production : `boto3` dans les dépendances du membre, version du lock · ❌ prototype ou script jetable : celle du runtime suffit.

```python
# Exemple 1 : la version qui tourne
import boto3
print(boto3.__version__)
# affiché : 1.43.118 en local (lock)
# sur Lambda sans zip : celle d'AWS
```

- Quiz : Zip avec `boto3` 1.43, couche avec `boto3` 1.40 : lequel la fonction importe-t-elle ?
- [ ] Celui de la couche : `/opt` passe en premier
- [x] Celui du zip : `/var/task` passe en premier
- [ ] Celui du runtime : AWS l'impose
- [ ] Aucun : `ImportError` sur le conflit
- Réponse : celui du zip : `/var/task` précède `/opt/python`, qui précède `/var/runtime` ; Python prend le premier module trouvé, sans vérifier de conflit.

## 27. exception : laisser l'invocation échouer
- Sous-thème : invocation
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Une exception non attrapée met l'invocation en échec (`errorType`, `errorMessage`) ; c'est ce statut que lit l'appelant pour décider de rejouer.
- Contexte : Step Functions, l'invocation asynchrone et les mappings SQS ne rejouent que ce qui a échoué. Attraper l'erreur pour renvoyer `{"ok": False}` change une panne en succès : personne ne rejoue, la journée manque dans la table. Journaliser est permis, à condition de relancer (`raise`). Ici rien n'est publié avant la fin de la lecture : laisser remonter est sans risque.
- Usage : ✅ laisser remonter, ou `logger.exception(…)` puis `raise` · ❌ `except Exception: return {"ok": False}` : succès pour Lambda, trou silencieux dans la partition.

```python
# Exemple 1 : l'erreur avalée devient un succès
def lire(day):
    raise ConnectionError("coupé")

def handler(event, context):
    try:
        lire(event["date"])
    except Exception:
        return {"ok": False}  # ⚠️ succès

handler({"date": "2026-10-20"}, None)
# → {"ok": False}
```

```bash
# Exemple 2 : une invocation en échec
aws lambda invoke \
  --function-name bodacc-ingest \
  --cli-binary-format raw-in-base64-out \
  --payload '{"date": "2026-10-20"}' out.json
# → "FunctionError": "Unhandled"
cat out.json
# → {"errorMessage": "coupé",
#    "errorType": "ConnectionError", …}
```

- Quiz : Invoquée en asynchrone, la fonction renvoie `{"ok": False}` sans lever : combien de fois Lambda la réessaie-t-elle ?
- [x] `0`
- [ ] `2`
- [ ] `3`
- [ ] Jusqu'à l'expiration de l'événement (6 h)
- Réponse : `0` (doc AWS) : les 2 nouvelles tentatives de l'asynchrone ne suivent qu'une erreur ; une valeur renvoyée, quelle qu'elle soit, est un succès.

## 28. client boto3 : créé au premier appel
- Sous-thème : invocation
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `@functools.cache` sur une fonction sans argument crée le client au premier appel, puis rend le même objet aux invocations suivantes du conteneur.
- Contexte : Même réutilisation qu'un client de niveau module (créé une fois par environnement), mais la création attend le premier appel : région, profil et identifiants sont lus à ce moment, pas à l'import. En test, les fixtures ont alors posé leur environnement ; `s3_client.cache_clear()` donne un client neuf par test. Un client de module est créé dès l'import du fichier de test, avant toute fixture.
- Usage : ✅ client SDK d'une Lambda testée avec moto et des variables posées par fixture · ❌ `boto3.client("s3")` dans le handler : recréé à chaque invocation.

```python
# Exemple 1 : un seul client par conteneur
import os
from functools import cache
import boto3
os.environ["AWS_DEFAULT_REGION"] = "eu-west-3"

@cache
def s3_client():
    return boto3.client("s3")

s3_client() is s3_client()  # → True
```

```python
# Exemple 2 : la région lue au 1er appel
import os
from functools import cache
import boto3
os.environ.pop("AWS_REGION", None)
@cache
def s3_client():
    return boto3.client("s3")
os.environ["AWS_DEFAULT_REGION"] = "eu-west-3"
s3_client().meta.region_name
# → "eu-west-3"
```

- Quiz : Exemple 2, puis `AWS_DEFAULT_REGION = "eu-west-1"` posé **après** ce premier appel : que vaut `s3_client().meta.region_name` ?
- [ ] `"eu-west-1"`
- [x] `"eu-west-3"`
- [ ] `"us-east-1"`
- [ ] `NoRegionError`
- Réponse : `"eu-west-3"` : le client est figé au premier appel et le cache le rend tel quel ; il faut `s3_client.cache_clear()` pour relire l'environnement.

## 29. client boto3 : région absente
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Sans région (variable, profil ou argument), `boto3.client("s3")` prend `us-east-1` sans prévenir, alors que `boto3.client("sqs")` lève `NoRegionError`.
- Contexte : Mesuré. S3 a un point d'accès global, d'où ce défaut silencieux : en local ou en CI, un client créé avant que la fixture pose `AWS_DEFAULT_REGION` vise `us-east-1`, et le bucket moto créé en `eu-west-3` ne correspond plus. Dans Lambda, le runtime fournit `AWS_REGION` : le problème n'apparaît qu'en dehors. `region_name=` explicite supprime l'ambiguïté.
- Usage : ✅ région explicite dans les tests et scripts, `AWS_REGION` du runtime dans la Lambda · ❌ compter sur le `~/.aws/config` du poste : la CI ne l'a pas.

```python
# Exemple 1 : S3 se rabat sur us-east-1
import os
for k in ("AWS_REGION", "AWS_PROFILE",
          "AWS_DEFAULT_REGION"):
    os.environ.pop(k, None)
os.environ["AWS_CONFIG_FILE"] = "/absent"
import boto3
s = boto3.session.Session()  # relit tout
s.client("s3").meta.region_name
# → "us-east-1"
s.client("sqs")  # ❌ NoRegionError
del os.environ["AWS_CONFIG_FILE"]
```

- Quiz : Dans la fonction Lambda déployée en `eu-west-3`, `boto3.client("s3")` sans `region_name` : quelle région ?
- [ ] `us-east-1`, comme en local
- [x] `eu-west-3`, celle de la fonction
- [ ] `NoRegionError`
- Réponse : `eu-west-3` (doc AWS) : le runtime pose `AWS_REGION` sur la région de la fonction, que boto3 lit ; le défaut `us-east-1` ne sert qu'en dehors de Lambda.

## 30. handler async def : jamais exécuté
- Sous-thème : invocation
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le runtime Python appelle le handler de façon synchrone : un `async def handler` renvoie une coroutine que personne n'exécute.
- Contexte : En Node, `export const handler = async (event) => …` est la norme ; en Python, le runtime fait `resultat = handler(event, context)` puis sérialise `resultat`. Une coroutine n'est pas du JSON : l'invocation échoue, et le corps n'a jamais tourné (doc AWS : handler synchrone). Pour du code async (`httpx.AsyncClient`), le handler reste un `def` qui appelle `asyncio.run(…)`.
- Usage : ✅ `def handler` + `asyncio.run(main(event))` si la logique est async · ❌ `async def handler` copié d'un handler Node.

```python
# Exemple 1 : ce que reçoit le runtime
import json
async def handler(event, context):
    return {"count": 2}
r = handler({}, None)
type(r).__name__  # → "coroutine"
json.dumps(r)  # ❌ TypeError
r.close()  # évite l'avertissement
```

```python
# Exemple 2 : un def, l'async dedans
import asyncio
async def compter(jour):
    await asyncio.sleep(0)
    return 2
def handler(event, context):
    n = asyncio.run(compter(event["date"]))
    return {"count": n}
handler({"date": "2026-10-20"}, None)
# → {"count": 2}
```

- Quiz : Dans un `async def handler`, le corps écrit un objet S3 avant son `return` : l'objet est-il écrit ?
- [ ] Oui, puis l'invocation échoue à la sérialisation
- [ ] Oui : le runtime attend la coroutine
- [x] Non : le corps ne s'exécute jamais
- Réponse : non : appeler une fonction `async` crée seulement la coroutine ; sans `await` ni boucle d'événements, aucune ligne du corps ne tourne.

## 31. variable d'env : lue dans le handler, pas à l'import
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Lire `os.environ["RAW_BUCKET"]` dans le handler, et non au niveau module, donne une erreur claire par invocation et laisse chaque test poser sa valeur.
- Contexte : Une lecture de module s'exécute à l'import : en test, avant `monkeypatch.setenv`, donc la valeur est figée (ou l'import casse) ; dans Lambda, pendant l'init, qui échoue alors pour chaque appel. Dans le handler, le coût est nul (un accès dict). Le client S3, coûteux, reste en cache ; la configuration bon marché se relit.
- Usage : ✅ config lue dans le handler, client coûteux derrière `@cache` · ❌ `BUCKET = os.environ["RAW_BUCKET"]` en tête de module : figé à l'import, impossible à changer par test.

```python
# Exemple 1 : figé à l'import
import os
os.environ["RAW_BUCKET"] = "dp-raw-dev"
BUCKET = os.environ["RAW_BUCKET"]  # import

def handler(event, context):
    return BUCKET

os.environ["RAW_BUCKET"] = "dp-raw-test"
handler({}, None)  # → "dp-raw-dev"
del os.environ["RAW_BUCKET"]
```

```python
# Exemple 2 : lu à chaque invocation
import os
def handler(event, context):
    return os.environ["RAW_BUCKET"]
os.environ["RAW_BUCKET"] = "dp-raw-test"
handler({}, None)  # → "dp-raw-test"
del os.environ["RAW_BUCKET"]
handler({}, None)  # ❌ KeyError
```

- Quiz : `handler.py` commence par `BUCKET = os.environ["RAW_BUCKET"]` ; la CI n'a pas la variable : quand pytest échoue-t-il ?
- [ ] Au premier `assert` du premier test
- [x] À la collecte, avant le moindre test
- [ ] Jamais : `BUCKET` vaut `None`
- [ ] Au teardown de la fixture `monkeypatch`
- Réponse : à la collecte (mesuré : `ERROR test_x.py - KeyError`) : l'import du module testé lève avant que pytest ait lancé une fixture ; tout le fichier est perdu.

## 32. /tmp : nettoyer à chaque invocation
- Sous-thème : limites
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Un fichier de travail laissé dans `/tmp` s'ajoute à ceux des invocations précédentes du conteneur, jusqu'à `OSError: [Errno 28] No space left on device`.
- Contexte : `/tmp` vit aussi longtemps que l'environnement chaud (des heures) et fait 512 Mo par défaut. Un nom par date ou un nom aléatoire sans suppression accumule ; l'erreur n'arrive qu'après N appels, jamais en test. `with tempfile.TemporaryDirectory()` supprime tout à la sortie, même sur exception ; `dir=` reste injectable pour vérifier le nettoyage en test.
- Usage : ✅ `TemporaryDirectory()` autour de l'écriture et de l'envoi S3 · ❌ `/tmp/part-{jour}.gz` sans `unlink` : chaque rejeu ajoute un fichier.

```python
# Exemple 1 : un fichier par invocation
import tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp())  # ≈ /tmp
def handler(event, context):
    p = tmp / f"part-{event['date']}.gz"
    p.write_bytes(b"x" * 1000)
for d in ("2026-10-20", "2026-10-21"):
    handler({"date": d}, None)
len(list(tmp.iterdir()))  # → 2 (gardés)
```

```python
# Exemple 2 : rien ne reste, même sur erreur
import tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp())
def handler(event, context):
    with tempfile.TemporaryDirectory(
            dir=tmp) as d:
        (Path(d) / "part.gz").write_bytes(b"x")
        raise ConnectionError("coupé")
handler({}, None)  # ❌ ConnectionError
list(tmp.iterdir())  # → []
```

- Quiz : Une fonction laisse 40 Mo dans `/tmp` (512 Mo) à chaque appel, environnement chaud : quand arrive la première erreur ?
- [ ] Jamais : `/tmp` est vidé après chaque invocation
- [ ] À la 2e : un seul fichier par environnement
- [x] Vers la 13e invocation du même environnement
- [ ] Jamais : Lambda agrandit `/tmp` à la demande
- Réponse : vers la 13e : 12 × 40 Mo tiennent, la 13e dépasse 512 Mo ; seul un démarrage à froid repart d'un `/tmp` vide, et `ephemeral_storage` ne fait que reculer l'échéance.

## 33. zip : 50 Mo en envoi direct, sinon S3
- Sous-thème : limites
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Un zip envoyé directement (`filename`) fait au plus 50 Mo ; au-delà, on le dépose sur S3 (`s3_bucket`, `s3_key`), toujours sous 250 Mo décompressé.
- Contexte : Deux limites distinctes : la taille du `.zip` transmis à l'API (`CreateFunction`, `UpdateFunctionCode`) et sa taille décompressée, couches comprises. Le zip BODACC : 20,2 Mo zippé, 32,4 Mo décompressé, `boto3` compris. Passer par S3 lève la première limite, jamais la seconde. Le script de build affiche la taille du zip à chaque build.
- Usage : ✅ suivre les deux tailles (`unzip -l` donne la décompressée en dernière ligne) · ❌ juger sur la seule taille du `.zip` : c'est souvent la décompressée qui bloque.

```bash
# Exemple 1 : les deux tailles du build
ls -l build/ingest-bodacc.zip
# 20157776 octets   ≤ 50 Mo : envoi direct
unzip -l build/ingest-bodacc.zip | tail -1
# 32421436   3144 files   ≤ 250 Mo
```

```hcl
# Exemple 2 : au-delà de 50 Mo, par S3
resource "aws_lambda_function" "ingest" {
  function_name = "data-platform-dev-ingest-bodacc"
  s3_bucket     = "data-platform-dev-artifacts"
  s3_key        = "lambdas/ingest-bodacc/<sha256>.zip"
  # filename interdit avec s3_bucket
}
```

- Quiz : Zip de 60 Mo, 180 Mo une fois décompressé : comment le déployer en zip ?
- [ ] `filename` : Terraform découpe l'envoi
- [x] Le déposer sur S3, puis `s3_bucket` et `s3_key`
- [ ] Impossible : couche obligatoire
- [ ] Impossible : image conteneur obligatoire
- Réponse : par S3 : la limite de 50 Mo ne vaut que pour l'envoi direct ; 180 Mo décompressés restent sous les 250 Mo.

## 34. zip, couche ou image : choisir
- Sous-thème : choisir
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Zip seul sous les limites ; couche pour partager des dépendances entre fonctions ; image au-delà de 250 Mo ou pour un système sur mesure.
- Contexte : Couche : socle versionné à part, mais compatibilité de runtime et d'architecture à suivre, et le total reste sous 250 Mo. Image (ECR, jusqu'à 10 Go) : Docker au build, image plus lourde à démarrer, et c'est à nous de la reconstruire pour les correctifs du runtime. Pour `ingest_bodacc` : une seule fonction, 20 Mo, donc zip.
- Usage : ✅ zip par défaut ; couche dès que plusieurs fonctions partagent un gros socle ; image pour PySpark, modèles, binaires système · ❌ image pour 20 Mo de dépendances : ECR, Docker et démarrage plus lent pour rien.

```text
# Exemple 1 : trois fonctions, trois choix
ingest-bodacc  20 Mo, seule      → zip
normalize-*    5 fonctions,
               pydantic commun   → couche
ocr-pdf        tesseract, 1 Go   → image
```

- Quiz : Une couche de 200 Mo décompressés, une fonction qui ajoute 60 Mo de code : déployable en zip ?
- [ ] Oui : la couche a sa propre limite
- [ ] Oui, si le zip fait moins de 50 Mo
- [x] Non : 260 Mo dépassent 250 Mo au total
- [ ] Non : une couche est limitée à 50 Mo
- Réponse : non : les 250 Mo décompressés comptent le code de la fonction et toutes ses couches ensemble.

## 35. droits des fichiers : lisibles par tous
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Lambda exécute le code sous un utilisateur sans privilèges : chaque fichier du zip doit être lisible par tous (644), chaque dossier traversable (755).
- Contexte : Un zip aux droits `600` (défaut de `zipfile.writestr`, ou `umask 077` sur la machine de build) se déploie sans erreur ; c'est l'import qui échoue (`Permission denied`). Le script de build fixe `external_attr = 0o644 << 16` sur chaque entrée ; un exécutable (`bootstrap` d'un runtime custom) demande 755.
- Usage : ✅ droits fixés par le script de build, vérifiés par `unzip -Z` · ❌ dépendre du `umask` du poste ou du runner CI.

```bash
# Exemple 1 : vérifier les droits du zip
unzip -Z build/ingest-bodacc.zip | sed -n 3,4p
# ?rw-r--r--  …  80-Jan-01 00:00 .lock
# ?rw-r--r--  …  80-Jan-01 00:00
#   annotated_types/__init__.py
```

- Quiz : Fichiers du zip en `600` : à quel moment l'erreur apparaît-elle ?
- [ ] Au `terraform apply`
- [ ] À l'appel `UpdateFunctionCode`
- [x] À l'invocation, à l'import du code
- [ ] Jamais : Lambda corrige les droits
- Réponse : à l'invocation : Lambda stocke le zip sans le lire ; c'est le runtime qui ne peut pas ouvrir les fichiers au moment de l'import.

## 36. source_code_hash : redéployer si le zip change
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `source_code_hash = filebase64sha256("x.zip")` donne à Terraform l'empreinte du zip : un changement d'octets déclenche la mise à jour du code.
- Contexte : Terraform ne lit pas le contenu de `filename`. Avec `source_code_hash`, chaque octet compte : un zip non reproductible (dates des fichiers, ordre des entrées) change l'empreinte à chaque build, et le `plan` affiche `~ source_code_hash` sans aucun changement de code. D'où le zip à date fixe : `No changes` tant que le code ne bouge pas.
- Usage : ✅ `filename` et `source_code_hash` pour un zip local ; `s3_key` contenant le hash pour un zip sur S3 · ❌ `zip -r` dans le Makefile avec `source_code_hash` : redéploiement à chaque `make up`.

```hcl
# Exemple 1 : le zip et son empreinte
locals {
  zip = "${path.root}/../build/ingest-bodacc.zip"
}
resource "aws_lambda_function" "ingest" {
  function_name    = "data-platform-dev-ingest-bodacc"
  filename         = local.zip
  source_code_hash = filebase64sha256(local.zip)
  handler          = "ingest_bodacc.handler.lambda_handler"
  runtime          = "python3.12"
  architectures    = ["arm64"]
  # role, timeout… omis
}
```

- Quiz : Sans `source_code_hash`, le zip est reconstruit avec du code neuf, au même chemin : que montre `terraform plan` ?
- [x] `No changes`
- [ ] `~ update in-place` sur la fonction
- [ ] `-/+` : la fonction est recréée
- [ ] Une erreur : empreinte manquante
- Réponse : `No changes` : sans empreinte, Terraform ne compare que le chemin `filename`, identique ; le nouveau code ne part jamais.

## 37. __pycache__ : pas de .pyc dans le zip
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le zip n'embarque pas les `.pyc` du poste : ils ne valent que pour une version de Python, et `/var/task` est en lecture seule.
- Contexte : Un `.pyc` porte la version dans son nom (`handler.cpython-312.pyc`) : compilé par un Python 3.13 local, il est ignoré par le runtime 3.12. Lambda ne peut pas non plus en écrire dans `/var/task` : chaque démarrage à froid recompile en mémoire, quelques millisecondes pour un petit paquet. Les `__pycache__` du dossier viennent d'un test ou d'un import lancé dedans.
- Usage : ✅ exclure `__pycache__` du zip ; pour un gros paquet, précompiler avec la version exacte du runtime · ❌ zipper un dossier où l'on a lancé `pytest` : des `.pyc` d'une autre version.

```python
# Exemple 1 : la version est dans le nom
import importlib.util, sys
importlib.util.cache_from_source("handler.py")
# → '__pycache__/handler.cpython-312.pyc'
sys.implementation.cache_tag  # → 'cpython-312'
```

- Quiz : Un `.pyc` compilé par CPython 3.12 sur un Mac arm64 : utilisable par Lambda `python3.12` en `x86_64` ?
- [x] Oui : le bytecode ne dépend pas du système
- [ ] Non : compilé pour macOS
- [ ] Non : compilé pour arm64
- [ ] Seulement si la fonction est en arm64
- Réponse : oui : le bytecode dépend de la version de Python, pas de l'OS ni du processeur ; c'est la différence avec un `.so` compilé.

## 38. bin/ : des scripts liés au Python du poste
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `uv pip install --target` crée un `bin/` (CLI `httpx`, `jp.py`) dont le shebang vise le Python du poste : inutile en Lambda, exclu du zip.
- Contexte : Les commandes déclarées par les dépendances deviennent des exécutables qui commencent par `#!/Users/…/.venv/bin/python3`. Lambda n'appelle que le handler, jamais ces commandes, et ce chemin n'existe pas dans le runtime. Les garder ajoute du poids et un chemin absolu du poste dans l'artefact, qui change d'un clone à l'autre.
- Usage : ✅ exclure `bin/` (et `__pycache__`) en construisant le zip · ❌ appeler la CLI d'une dépendance depuis le handler en sous-processus : importer la bibliothèque.

```bash
# Exemple 1 : ce que --target installe
ls package/bin     # dossier du build
# httpx  idna  jp.py
head -1 package/bin/httpx
# #!/Users/…/data-platform/.venv/bin/python3
```

- Quiz : Le zip garde `bin/httpx` : que se passe-t-il à l'invocation ?
- [x] Rien : le fichier est ignoré
- [ ] `Runtime.ImportModuleError`
- [ ] Le déploiement est refusé
- [ ] `httpx` n'est plus importable
- Réponse : rien : personne n'exécute ce script ; seul le poids du zip et sa reproductibilité en pâtissent.

## 39. depends_on : les droits avant la fonction
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `depends_on = [aws_iam_role_policy.logs, aws_iam_role_policy.app]` fait créer les politiques du rôle avant la fonction, que rien d'autre ne relie.
- Contexte : La fonction ne référence que `aws_iam_role.this.arn` : pour Terraform, les politiques inline et la fonction sont indépendantes et se créent en parallèle. Une invocation juste après l'`apply` pourrait tourner avec un rôle encore vide : premiers logs perdus, `AccessDenied` sur S3. `depends_on` ajoute l'arête que le graphe ne voit pas. À la destruction, l'ordre s'inverse : fonction d'abord, politiques ensuite.
- Usage : ✅ dépendance réelle sans référence (droits d'un rôle, notification S3) · ❌ doubler une référence qui existe déjà : l'ordre est connu.

```hcl
# Exemple 1 : la seule référence est le rôle
resource "aws_lambda_function" "this" {
  role = aws_iam_role.this.arn
  # politiques inline : aucun lien visible
  depends_on = [
    aws_iam_role_policy.logs,
    aws_iam_role_policy.app,
  ]
}
```

- Quiz : Sans `depends_on`, le log group est-il créé avant la fonction ?
- [x] Oui : `logging_config` le référence
- [ ] Non : seules les politiques sont ordonnées
- [ ] Au hasard : tout se crée en parallèle
- [ ] Non : Lambda le crée elle-même
- Réponse : oui : `log_group = aws_cloudwatch_log_group.this.name` est une référence, donc une arête du graphe ; `depends_on` ne sert qu'aux liens invisibles.

## 40. memory_size : la mémoire achète le CPU
- Sous-thème : limites
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `memory_size` (128 à 10 240 Mo) fixe aussi le CPU, environ 1 vCPU à 1 769 Mo ; on paie mémoire × durée.
- Contexte : Pas de réglage CPU séparé : une fonction lente sur du calcul (gzip, JSON, pydantic) va plus vite avec plus de mémoire, même si elle n'en consomme pas. Le prix est en Go-secondes : doubler la mémoire et diviser la durée par deux coûte pareil. Ici 1024 Mo : la compression d'une journée BODACC va deux fois plus vite qu'à 512 Mo. Mesurer avec la ligne `REPORT` (`Duration`, `Max Memory Used`).
- Usage : ✅ monter la mémoire d'une fonction limitée par le CPU, mesurer durée et coût · ❌ garder 128 Mo « pour économiser » sur du calcul : plus lent, parfois plus cher.

```python
# Exemple 1 : le coût en Go-secondes
def go_s(memoire_mo, duree_s):
    return memoire_mo / 1024 * duree_s

go_s(512, 8.0)   # → 4.0
go_s(1024, 4.0)  # → 4.0 : même coût
go_s(1024, 6.0)  # → 6.0 : gain partiel
```

- Quiz : Une fonction qui attend surtout l'API BODACC (réseau) passe de 512 à 1024 Mo : effet probable ?
- [ ] Deux fois plus rapide, même coût
- [ ] Même durée, même coût
- [x] Presque même durée, coût presque doublé
- [ ] Plus lente : démarrage à froid plus long
- Réponse : presque même durée, coût presque doublé : le CPU en plus ne raccourcit pas l'attente réseau, et l'on paie deux fois plus de Go par seconde.

## 41. module for_each : une entrée, une fonction
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `module "lambda"` en `for_each` sur `local.lambdas` crée rôle, log group et fonction par entrée : ajouter une Lambda, c'est ajouter une entrée.
- Contexte : La clé `ingest-bodacc` sert trois fois : adresse (`module.lambda["ingest-bodacc"]`), nom AWS (`data-platform-dev-ingest-bodacc`) et chemin du pointeur (`lambdas/ingest-bodacc/current.json`). C'est aussi le `name` du membre uv : une seule convention du build au déploiement. Changer une valeur de l'entrée (timeout, mémoire) modifie la fonction sur place.
- Usage : ✅ des dizaines de Lambdas sur le même modèle, chacune avec ses droits et réglages · ❌ copier le bloc `aws_lambda_function` par fonction : rôles et logs divergent.

```hcl
# Exemple 1 : une boucle, toutes les Lambdas
module "lambda" {
  source   = "./modules/lambda-python"
  for_each = local.lambdas

  name        = "${local.prefix}-${each.key}"
  handler     = each.value.handler
  timeout     = each.value.timeout
  policy_json = each.value.policy_json
}
# → module.lambda["ingest-bodacc"]
```

- Quiz : On renomme la clé en `bodacc-ingest` et on ajoute un bloc `moved` vers la nouvelle adresse : la fonction est-elle recréée ?
- [ ] Non : `moved` garde la même fonction
- [x] Oui : son nom AWS change, donc remplacement
- [ ] Non : seul le rôle est recréé
- [ ] Erreur : `moved` interdit avec `for_each`
- Réponse : oui : `moved` évite la recréation due à l'adresse, mais `function_name` (et les noms du rôle, du log group) changent, et ces arguments forcent le remplacement.

## 42. zip sur S3 : copié au déploiement
- Sous-thème : déploiement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Au déploiement, Lambda copie le zip depuis S3 dans son propre stockage : l'objet n'est plus relu ensuite, même au démarrage à froid.
- Contexte : Supprimer l'objet après coup ne casse pas la fonction en service, mais casse tout ce qui le relit : recréation après `make down`, retour arrière, déploiement d'un autre environnement. D'où un bucket d'artefacts versionné, sans expiration des objets courants. Le code se télécharge depuis la console ou par `get-function` (URL présignée de la copie de Lambda), pas depuis le bucket.
- Usage : ✅ un bucket d'artefacts durable, le zip gardé tant qu'un environnement peut le redéployer · ❌ supprimer les zips « déjà déployés » pour gagner de la place.

```bash
# Exemple 1 : le code vient de la copie
aws lambda get-function \
  --function-name \
  data-platform-dev-ingest-bodacc \
  --query 'Code.RepositoryType'
# → "S3" : stockage interne de Lambda
# Code.Location : URL présignée,
# pas l'objet du bucket artefacts
```

- Quiz : Le bucket d'artefacts est en `us-east-1`, la fonction en `eu-west-3` : que donne l'`apply` ?
- [ ] Ça marche, transfert inter-région facturé
- [x] Erreur : bucket d'une autre région
- [ ] Erreur dès le `plan`
- [ ] Ça marche, démarrage à froid plus lent
- Réponse : erreur à l'`apply` : `CreateFunction` exige un bucket dans la région de la fonction (doc AWS) ; le `plan` ne le voit pas, il ne lit pas le zip.

## 43. logs:CreateLogGroup : le retirer du rôle
- Sous-thème : sécurité
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Sans `logs:CreateLogGroup` dans le rôle, la fonction n'écrit que dans le groupe créé par Terraform : jamais de groupe fantôme à rétention infinie.
- Contexte : `AWSLambdaBasicExecutionRole` donne `CreateLogGroup`, `CreateLogStream` et `PutLogEvents` sur `*` : si le groupe manque (supprimé à la main, nom changé), Lambda le recrée en silence, hors état, sans rétention, et peut écrire dans les groupes des autres fonctions. Le module écrit sa propre politique `logs` : deux actions, sur son groupe seul.
- Usage : ✅ politique `logs` sur mesure dans le module de la fonction · ❌ `AWSLambdaBasicExecutionRole` quand Terraform crée les groupes : droits trop larges.

```hcl
# Exemple 1 : écrire, pas créer le groupe
data "aws_iam_policy_document" "logs" {
  statement {
    sid     = "WriteOwnLogs"
    actions = ["logs:CreateLogStream",
               "logs:PutLogEvents"]
    resources = [
      "${aws_cloudwatch_log_group.this.arn}:*",
    ]
  }
}
```

- Quiz : Le groupe est supprimé à la main, puis la fonction est invoquée : résultat de l'invocation ?
- [x] Réussie, mais aucun log écrit
- [ ] Échec : `AccessDenied` sur les logs
- [ ] Réussie, groupe recréé par Lambda
- [ ] Échec : `ResourceNotFoundException`
- Réponse : réussie, sans logs : un échec d'envoi des logs ne fait pas échouer le code ; le groupe revient au prochain `make up`, qui voit qu'il manque.

## 44. REPORT : durée, mémoire, init
- Sous-thème : logs
- Niveau : 2
- Source : data-platform · S1-07
- Définition : La ligne `REPORT` de chaque invocation donne `Duration`, `Billed Duration`, `Memory Size`, `Max Memory Used` et, au démarrage à froid, `Init Duration`.
- Contexte : C'est la mesure à lire avant de régler `memory_size` ou `timeout`. Ici : 4,6 s, 121 Mo utilisés sur 1 024. 121 Mo ne veut pas dire « descendre à 128 » : la mémoire achète aussi le CPU, et gzip va deux fois plus vite à 1 024. `Init Duration` présente = nouveau conteneur ; absente = conteneur réutilisé.
- Usage : ✅ dimensionner mémoire et timeout, repérer les démarrages à froid · ❌ régler la mémoire sur `Max Memory Used` seul : mesurer aussi la durée.

```bash
# Exemple 1 : filtrer les REPORT
aws logs tail \
  /aws/lambda/data-platform-dev-ingest-bodacc \
  --since 3h --filter-pattern REPORT
# → Duration: 4563.27 ms
#   Billed Duration: 5520 ms
#   Memory Size: 1024 MB
#   Max Memory Used: 121 MB
#   Init Duration: 956.27 ms
```

- Quiz : `Duration` 4 563 ms, `Init Duration` 956 ms, `Billed Duration` 5 520 ms : d'où viennent les 957 ms de plus ?
- [ ] De l'arrondi à la seconde supérieure
- [x] De l'init, facturée avec l'invocation
- [ ] Du temps d'envoi de la réponse
- [ ] De la journalisation CloudWatch
- Réponse : de l'init : 4 563 + 956 ≈ 5 520 (mesuré) ; la phase d'initialisation est comptée dans la durée facturée.

## 45. --log-type Tail : le log dans la réponse
- Sous-thème : logs
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `aws lambda invoke --log-type Tail` renvoie dans `LogResult` les 4 derniers Ko du log de l'invocation, encodés en base64.
- Contexte : Évite d'aller chercher le flux dans CloudWatch juste après un appel manuel. Ne marche qu'en synchrone (`RequestResponse`). Seule la fin du log revient : pour une invocation bavarde, le début (et souvent la vraie erreur) est coupé ; `aws logs tail` reste la référence. Le base64 se décode avec `base64 -d` (macOS : `base64 -D` sur les vieilles versions).
- Usage : ✅ coup d'œil sur un appel manuel, script de smoke test · ❌ diagnostic d'une erreur au milieu d'un long log : `aws logs tail --since`.

```bash
# Exemple 1 : la fin du log, décodée
aws lambda invoke --function-name "$F" \
  --payload '{"date":"2026-10-20"}' \
  --cli-binary-format raw-in-base64-out \
  --log-type Tail \
  --query LogResult --output text \
  out.json | base64 -d | tail -2
```

- Quiz : Avec `--invocation-type Event --log-type Tail`, que contient `LogResult` ?
- [ ] Les 4 derniers Ko du log
- [x] Rien : pas de log en asynchrone
- [ ] Le log complet, en base64
- [ ] Le lien vers le flux CloudWatch
- Réponse : rien : `Tail` ne s'applique qu'aux invocations synchrones (doc de l'API Invoke) ; en asynchrone, la réponse ne porte que le code `202`.

## 46. invoquer : par un rôle ou par la ressource
- Sous-thème : sécurité
- Niveau : 2
- Source : data-platform · S1-08
- Définition : Un service qui invoque en endossant un rôle (Scheduler, Step Functions) n'a besoin d'aucun `aws_lambda_permission` ; un service qui appelle en son nom, si.
- Contexte : Dans un même compte, un `Allow` côté identité **ou** côté ressource suffit. C'est l'appelant qui impose le côté : Scheduler, Step Functions, CodeBuild endossent un rôle (droit dans ce rôle) ; S3, SNS, API Gateway, règle EventBridge appellent en leur nom (`aws_lambda_permission`) ; SQS, Kinesis : c'est la Lambda qui lit, avec son propre rôle. Entre deux comptes, il faut les deux.
- Usage : ✅ Scheduler, Step Functions : droits dans leur rôle · ❌ ajouter un `aws_lambda_permission` pour Scheduler « par sécurité » : droit en double, plus large à auditer.

```bash
# Exemple 1 : aucune politique de ressource
aws lambda get-policy \
  --function-name data-platform-dev-ingest-bodacc
# → ResourceNotFoundException
#   les invoke manuels passaient
#   par ton identité
```

- Quiz : Une notification S3 doit déclencher la fonction : où mettre le droit d'invoquer ?
- [ ] Dans le rôle d'exécution de la Lambda
- [x] Dans la politique de ressource de la Lambda
- [ ] Dans la politique du bucket
- [ ] Dans un rôle endossé par S3
- Réponse : politique de ressource (`aws_lambda_permission`, principal `s3.amazonaws.com`) : S3 appelle en son nom, sans endosser de rôle de ton compte.

## 47. event_invoke_config : régler l'asynchrone
- Sous-thème : invocation
- Niveau : 2
- Source : data-platform · S1-08
- Définition : `aws_lambda_function_event_invoke_config` fixe, pour une fonction, les retries et l'âge maximal des invocations asynchrones (défaut : 2 tentatives, 6 h).
- Contexte : Ne touche que l'asynchrone : Scheduler, S3, SNS, `--invocation-type Event`. Un appel synchrone (`aws lambda invoke`, un script de rejeu) n'est jamais réessayé par Lambda, et un mapping SQS suit les règles de la file. Écrire la ressource même avec les valeurs par défaut rend le comportement visible dans le code au lieu de dépendre d'un réglage implicite.
- Usage : ✅ toute Lambda déclenchée par Scheduler, S3 ou SNS, réglée dans le module commun · ❌ croire qu'elle borne un `invoke` synchrone ou un mapping SQS : rien ne change pour eux.

```hcl
# Exemple 1 : borné à 2 essais, 1 h
resource "aws_lambda_function_event_invoke_config" "this" {
  function_name                = aws_lambda_function.this.function_name
  maximum_retry_attempts       = 2
  maximum_event_age_in_seconds = 3600
}
```

```bash
# Exemple 2 : relire le réglage appliqué
aws lambda get-function-event-invoke-config \
  --function-name "$F" \
  --query '[MaximumRetryAttempts,
    MaximumEventAgeInSeconds]' \
  --output text
# → 2  3600
```

- Quiz : Avec `maximum_retry_attempts = 0`, `make replay` invoque en synchrone et le handler lève : combien de nouvelles tentatives Lambda fait-elle ?
- [ ] `2`, le défaut de l'asynchrone
- [x] `0`, mais pas à cause du réglage
- [ ] `0`, grâce au réglage
- [ ] `1`
- Réponse : `0`, mais pas à cause du réglage : un appel synchrone n'est jamais réessayé par Lambda ; c'est l'appelant qui décide.

## 48. boto3 invoke : l'erreur du handler n'est pas une exception
- Sous-thème : invocation
- Niveau : 2
- Source : data-platform · S1-08
- Définition : En Python, `client.invoke(...)` ne lève rien quand le handler échoue : la réponse porte `FunctionError`, et le détail est dans `Payload`.
- Contexte : `StatusCode` 200 dit seulement que Lambda a exécuté l'appel. Un `try/except ClientError` n'attrape que les erreurs du service (droits, fonction absente, throttling), jamais une exception du handler. Le code appelant doit donc tester `"FunctionError" in response`, lire `errorType` et `errorMessage`, et en faire sa propre exception.
- Usage : ✅ tout appel synchrone dont on exploite le résultat (`replay.py`, tests d'intégration) · ❌ conclure au succès sur `StatusCode == 200`.

```python
# Exemple 1 : succès apparent, échec réel
import io, json

body = {"errorType": "ConnectError",
        "errorMessage": "coupé"}
resp = {"StatusCode": 200,
        "FunctionError": "Unhandled",
        "Payload": io.BytesIO(
            json.dumps(body).encode())}
resp["StatusCode"] == 200    # → True
"FunctionError" in resp      # → True
json.loads(resp["Payload"].read())["errorType"]
# → 'ConnectError'
```

- Quiz : Le handler lève `ValueError`. Que fait `try: client.invoke(...) except ClientError: ...` ?
- [ ] Attrape l'erreur dans `except`
- [x] Rien : la réponse revient avec `FunctionError`
- [ ] Lève `ValueError` côté appelant
- [ ] Lève `botocore.exceptions.FunctionError`
- Réponse : rien : l'appel au service a réussi ; l'échec du handler est une donnée de la réponse, à tester soi-même.

## 49. Payload : un flux lu une seule fois
- Sous-thème : invocation
- Niveau : 2
- Source : data-platform · S1-08
- Définition : Le `Payload` d'une réponse `invoke` est un `StreamingBody` : `.read()` rend les octets une fois, puis `b""` (≈ `response.body` d'un `fetch`).
- Contexte : Lire le flux pour journaliser, puis le relire pour décoder, donne une chaîne vide et un `json.loads` qui échoue (`JSONDecodeError`). Lire une fois dans une variable, puis travailler sur la variable. Même règle pour `get_object()["Body"]` de S3.
- Usage : ✅ `body = json.loads(resp["Payload"].read())` une fois, en tête · ❌ deux `.read()` sur la même réponse.

```python
# Exemple 1 : deuxième lecture vide
import io
from botocore.response import StreamingBody

raw = b'{"count": 3}'
p = StreamingBody(io.BytesIO(raw), len(raw))
p.read()         # → b'{"count": 3}'
p.read()         # → b''
```

- Quiz : Après un premier `.read()`, que fait `json.loads(resp["Payload"].read())` ?
- [ ] Rend le même dictionnaire
- [ ] Rend `None`
- [x] `JSONDecodeError` sur une chaîne vide
- [ ] `ValueError: stream closed`
- Réponse : `JSONDecodeError` : le flux est épuisé, `.read()` rend `b""`, qui n'est pas du JSON.

## 50. concurrence réservée : une exécution à la fois
- Sous-thème : invocation
- Niveau : 3
- Source : revision-pwa · pwa-revision
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

## 51. versions et alias : figer le code
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

## 52. concurrence provisionnée : pas de démarrage à froid
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

## 53. destinations ou DLQ : garder l'erreur
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

## 54. init : 10 secondes au plus
- Sous-thème : limites
- Niveau : 3
- Source : data-platform · S1-07
- Définition : L'init (imports, code de module) dure 10 s au plus ; trop longue ou en échec, elle est retentée à l'appel, dans le timeout.
- Contexte : Doc AWS, non reproductible en local. Un import qui plante (`Runtime.ImportModuleError`, roue macOS dans le zip) fait échouer chaque invocation, puisque l'init est retentée à chaque fois. Un gros chargement au niveau module (référentiel, modèle) peut dépasser les 10 s ; derrière `@cache`, il est payé au premier appel, dans le budget de l'invocation, puis réutilisé.
- Usage : ✅ imports et clients légers à l'init, gros chargements paresseux · ❌ télécharger un fichier S3 de 2 Go au niveau module.

```bash
# Exemple 1 : import en échec (CloudWatch)
# [ERROR] Runtime.ImportModuleError:
#   Unable to import module
#   'ingest_bodacc.handler': No module
#   named 'pydantic_core._pydantic_core'
# → chaque invocation échoue de même
```

```python
# Exemple 2 : coût déplacé dans l'appel
import time
from functools import cache
@cache
def referentiel():
    time.sleep(0.01)  # ≈ gros chargement
    return {"7501": "Paris"}
def handler(event, context):
    return referentiel()[event["code"]]
handler({"code": "7501"}, None)  # → "Paris"
```

- Quiz : Le code de module lève une exception pendant l'init : que deviennent les invocations suivantes ?
- [x] L'init est retentée à chaque fois, et chacune échoue
- [ ] Seule la première échoue, les suivantes réussissent
- [ ] Lambda désactive la fonction jusqu'au prochain déploiement
- Réponse : l'init est retentée à chaque fois (doc AWS) : un environnement sans init réussie n'est jamais réutilisé ; tant que le code plante à l'import, chaque appel échoue.

## 55. get_remaining_time_in_millis : s'arrêter avant le timeout
- Sous-thème : invocation
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `context.get_remaining_time_in_millis()` donne les millisecondes restantes avant le timeout ; on s'en sert pour s'arrêter proprement avant d'être coupé.
- Contexte : Au timeout, Lambda arrête l'exécution : pas d'exception Python, ni `except`, ni `finally`, ni sortie de `with` ; l'invocation finit en `Task timed out` (doc AWS). Un traitement par lots peut vérifier le temps restant entre deux lots et lever une erreur explicite tant qu'il reste une marge pour journaliser.
- Usage : ✅ boucle de lots longue, marge de quelques secondes avant le timeout · ❌ compter sur un `finally` pour nettoyer ou journaliser au timeout.

```python
# Exemple 1 : s'arrêter avec une marge
class Ctx:
    def __init__(self, ms):
        self.ms = ms
    def get_remaining_time_in_millis(self):
        return self.ms

def handler(event, context):
    ms = context.get_remaining_time_in_millis()
    if ms < 1000:
        raise TimeoutError("marge < 1 s")
    return "ok"

handler({}, Ctx(5000))  # → "ok"
handler({}, Ctx(900))  # ❌ TimeoutError
```

- Quiz : Au timeout, le bloc `finally` du handler s'exécute-t-il ?
- [ ] Oui, comme pour toute sortie de fonction
- [ ] Oui, si le timeout dépasse 3 s
- [x] Non : l'exécution est coupée sans exception Python
- [ ] Seulement s'il est dans un `with`
- Réponse : non (doc AWS) : Lambda interrompt le processus, sans lever d'exception dans le code ; ni `finally` ni `__exit__` ne tournent, d'où la marge à prendre soi-même.

## 56. .so : la version de Python dans le nom
- Sous-thème : limites
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `_pydantic_core.cpython-312-aarch64-linux-gnu.so` ne se charge que sous CPython 3.12 Linux aarch64 : changer de runtime impose de reconstruire le zip.
- Contexte : L'importeur ne cherche que les suffixes de son interpréteur (`importlib.machinery.EXTENSION_SUFFIXES`) : sous `python3.13`, ce fichier est invisible et l'import échoue en `No module named 'pydantic_core._pydantic_core'`. D'où `--python-version` aligné sur `runtime` : les deux montent ensemble, puis on reconstruit.
- Usage : ✅ changer `runtime` et `--python-version` dans le même commit · ❌ passer `python3.12` → `python3.13` dans Terraform en gardant le zip.

```python
# Exemple 1 : les suffixes de ce Python
import importlib.machinery as m
m.EXTENSION_SUFFIXES[1:]  # → ['.abi3.so', '.so']
print(m.EXTENSION_SUFFIXES[0])
# affiché : .cpython-312-darwin.so (Mac)
```

```python
# Exemple 2 : un .so d'un autre Python
import importlib, sys, tempfile
from pathlib import Path
d = Path(tempfile.mkdtemp())
nom = "demo_core.cpython-313-aarch64-linux-gnu.so"
(d / nom).write_bytes(b"")
sys.path.insert(0, str(d))
importlib.import_module("demo_core")  # ❌ ModuleNotFoundError
```

- Quiz : Une dépendance installée depuis une roue `cp311-abi3` : passe-t-elle de `python3.12` à `python3.13` sans rebuild ?
- [ ] Non : compilée pour 3.11 seulement
- [x] Oui : `abi3` vaut pour 3.11 et suivantes
- [ ] Non : il faut reconstruire à chaque version
- [ ] Oui, mais en `x86_64` seulement
- Réponse : oui : une roue `abi3` n'utilise que l'API stable de CPython ; son fichier `.abi3.so` est dans les suffixes de toutes les versions à partir de la minimale.

## 57. manylinux2014 : la version de glibc
- Sous-thème : limites
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `manylinux2014` (alias `manylinux_2_17`) garantit un binaire qui tourne sur tout Linux avec glibc 2.17 ou plus : un minimum, pas le système cible.
- Contexte : `manylinux_X_Y` signifie glibc ≥ X.Y. Le runtime `python3.12` tourne sur Amazon Linux 2023 (glibc 2.34) : une roue `manylinux_2_28` y convient aussi. Mais `--python-platform aarch64-manylinux2014` n'accepte que les roues jusqu'à 2.17 : un paquet publié seulement en `manylinux_2_28` n'est pas trouvé, et `aarch64-manylinux_2_28` le débloque. `musllinux` (Alpine) ne tourne pas sur Lambda.
- Usage : ✅ `manylinux2014` par défaut (le plus large), `manylinux_2_28` si une dépendance l'exige · ❌ une roue `musllinux` ou `macosx` dans un zip Lambda.

```python
# Exemple 1 : deux noms, un même binaire
from packaging.utils import parse_wheel_filename
n = ("pydantic_core-2.50.1-cp312-cp312-"
     "manylinux_2_17_aarch64."
     "manylinux2014_aarch64.whl")
tags = parse_wheel_filename(n)[3]
sorted(t.platform for t in tags)
# → ['manylinux2014_aarch64', 'manylinux_2_17_aarch64']
```

- Quiz : Plateforme `aarch64-manylinux2014`, une dépendance ne publie que `manylinux_2_28_aarch64` : que fait uv avec `--only-binary :all:` ?
- [ ] Il prend la roue 2_28 : Lambda a glibc 2.34
- [ ] Il compile la source
- [ ] Il prend la roue `x86_64`
- [x] Il échoue : aucune roue compatible
- Réponse : il échoue : la cible déclarée est glibc 2.17, une roue qui exige 2.28 est incompatible ; et `--only-binary` interdit de compiler.

## 58. architecture : roues et fonction alignées
- Sous-thème : limites
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Roues du zip et `architectures` de la fonction doivent correspondre : un zip `aarch64` sur une fonction `x86_64` échoue à l'import du code natif.
- Contexte : Le déploiement passe : Lambda ne lit pas le zip. L'erreur arrive à l'invocation, `No module named 'pydantic_core._pydantic_core'`, car le runtime x86_64 cherche `.cpython-312-x86_64-linux-gnu.so`. Une seule source de vérité : `PLATFORM` du script de build et `architectures` du Terraform changent ensemble. Vérifier le tag des binaires fait partie du build.
- Usage : ✅ un contrôle du zip après build (`grep aarch64`, aucun `macosx`) · ❌ passer la fonction en `x86_64` pour un essai sans reconstruire le zip.

```bash
# Exemple 1 : le contrôle de l'étape
Z=build/ingest-bodacc.zip
unzip -l $Z | grep -c '_pydantic_core.*aarch64'
# → 1
unzip -l $Z | grep -c macosx
# → 0
```

- Quiz : Zip `aarch64`, fonction `x86_64`, handler qui n'importe que `json` et `httpx` : que se passe-t-il ?
- [ ] `Runtime.ImportModuleError` dès l'import
- [x] Ça marche : tout est pur Python
- [ ] Le déploiement est refusé
- [ ] Ça marche, mais 20 % plus cher
- Réponse : ça marche : `httpx` et ses dépendances sont `py3-none-any` ; l'erreur ne sort qu'au premier import d'un module natif, ce qui la cache longtemps.

## 59. CodeSha256 : vérifier le code déployé
- Sous-thème : déploiement
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `CodeSha256` de la fonction est le sha256 du zip encodé en base64 : le comparer au `base64sha256` du pointeur prouve quel build tourne.
- Contexte : C'est la valeur que Terraform compare à `source_code_hash`. Le script de publication calcule la même empreinte ; l'étape 8 a retrouvé `SIF3hiDV…` à trois endroits : build, pointeur, fonction. Attention au format : `sha256sum` et la clé S3 donnent l'hexadécimal (64 caractères), Lambda et Terraform le base64 des 32 octets bruts (44 caractères).
- Usage : ✅ vérifier après un déploiement ou pendant un incident que le code attendu tourne · ❌ comparer un hash hexadécimal à `CodeSha256` : jamais égaux.

```python
# Exemple 1 : deux écritures d'un hash
import base64
import hashlib

d = hashlib.sha256(b"PK v1")
d.hexdigest()[:12]  # → 'ec6a490e2e8c'
base64.b64encode(d.digest()).decode()[:8]
# → '7GpJDi6M'
```

```bash
# Exemple 2 : le hash côté AWS
aws lambda get-function-configuration \
  --function-name \
  data-platform-dev-ingest-bodacc \
  --query CodeSha256 --output text
# → SIF3hiDV… = base64sha256 du pointeur
```

- Quiz : Que vaut `len(base64.b64encode(hashlib.sha256(b"x").hexdigest().encode()))` ?
- [ ] 44
- [ ] 64
- [x] 88
- [ ] 32
- Réponse : 88 : on encode en base64 les 64 caractères hexadécimaux, pas les 32 octets bruts ; c'est l'erreur qui rend `CodeSha256` « différent ».

## 60. s3_object_version : clé fixe, version qui change
- Sous-thème : déploiement
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Avec un bucket versionné, `s3_object_version` désigne une version précise d'une clé fixe : une nouvelle version redéploie, sans hash dans la clé.
- Contexte : Alternative à l'adressage par contenu : `lambdas/ingest-bodacc.zip` réécrit à chaque build, et son `version_id` passé à Terraform. Plus simple à publier, mais l'identifiant est opaque (il ne dit rien du contenu) et dépend du bucket : impossible de retrouver la même version dans un autre compte. La clé par hash reste lisible, idempotente et vérifiable contre `CodeSha256`.
- Usage : ✅ outil tiers qui impose un nom de zip fixe, bucket versionné · ❌ en remplacement d'une clé par hash qui marche : on perd l'idempotence.

```hcl
# Exemple 1 : clé fixe, version explicite
resource "aws_lambda_function" "this" {
  function_name     = var.name
  role              = aws_iam_role.this.arn
  s3_bucket         = var.artifacts_bucket
  s3_key            = "lambdas/ingest-bodacc.zip"
  s3_object_version = var.zip_version
}
# zip_version = "3HL4kqtJlcpXroDTDmJ"
```

- Quiz : Le même zip (octets identiques) est réécrit sur la clé fixe, sa nouvelle version passée à Terraform : que montre `plan` ?
- [ ] `No changes` : même contenu
- [x] Mise à jour de la fonction
- [ ] Remplacement de la fonction
- [ ] Erreur : version déjà déployée
- Réponse : mise à jour sur place : chaque `PUT` crée un nouveau `version_id`, même pour des octets identiques ; Terraform voit l'argument changer et redéploie.

## 61. allowed_triggers : les permissions générées
- Sous-thème : sécurité
- Niveau : 3
- Source : data-platform · S1-08
- Définition : En entreprise, le module Lambda reçoit une map `allowed_triggers` et génère un `aws_lambda_permission` par entrée, `source_arn` obligatoire.
- Contexte : Avec des dizaines de fonctions, une permission écrite à la main finit par oublier `source_arn` : n'importe quelle ressource du service (un autre bucket, une autre règle) peut alors invoquer. Une `validation` de variable refuse l'entrée dès le plan. Le contrôle global reste à IAM Access Analyzer et aux SCP ; le module garantit la forme de chaque permission.
- Usage : ✅ module Lambda partagé entre équipes, nombreuses sources d'événements · ❌ `aws_lambda_permission` libres dans chaque projet : impossibles à auditer d'un coup.

```hcl
# Exemple 1 : source_arn exigé au plan
variable "allowed_triggers" {
  type = map(object({
    principal  = string
    source_arn = optional(string)
  }))
  validation {
    condition = alltrue([
      for t in values(var.allowed_triggers) :
      t.source_arn != null])
    error_message = "source_arn requis."
  }
}
# s3 sans source_arn
# → Error: Invalid value for variable
```

- Quiz : La permission `principal = "s3.amazonaws.com"` sans `source_arn` ni `source_account` : qui peut déclencher la fonction ?
- [ ] Seuls les buckets du même compte
- [x] Tout bucket configuré vers elle, quel que soit le compte
- [ ] Personne : S3 exige `source_arn`
- [ ] Seul le bucket créé dans le même module
- Réponse : tout bucket configuré vers la fonction : le principal désigne le service S3 entier ; `source_arn` et `source_account` sont la seule borne.

## 62. retries empilés : compter les exécutions
- Sous-thème : invocation
- Niveau : 3
- Source : data-platform · S1-08
- Définition : Scheduler réessaie la livraison, Lambda réessaie le handler : les deux couches ne se multiplient pas, car un appel livré ne revient jamais à Scheduler.
- Contexte : Scheduler appelle en asynchrone : dès le `202`, l'appel est livré et Scheduler a fini, même si le handler échoue ensuite. Ses tentatives ne servent qu'aux échecs de dépôt (droits, limitation). Un handler qui échoue toujours tourne donc 1 + `maximum_retry_attempts` fois, quel que soit `retry_policy`. Compter ainsi avant de choisir les chiffres, et parce que chaque exécution réappelle l'API source.
- Usage : ✅ dimensionner retries et charge sur l'API source, expliquer un nombre d'exécutions dans les logs · ❌ multiplier les deux couches : elles couvrent des pannes différentes.

```bash
# Exemple 1 : une journée qui échoue toujours
# Scheduler : retry_policy 3 essais
#   → livraison OK au 1er essai (202)
# Lambda : maximum_retry_attempts = 2
#   → exécutions du handler :
#     1 (06:00) + 2 retries = 3
aws logs tail /aws/lambda/"$F" \
  --since 1h --filter-pattern START
# → 3 lignes START
```

- Quiz : Livraison OK, handler qui lève toujours, `retry_policy` 3 essais, `maximum_retry_attempts = 2` : combien d'exécutions du handler ?
- [ ] `12` : 4 livraisons × 3 exécutions
- [ ] `4` : celles de Scheduler
- [x] `3`
- [ ] `6`
- Réponse : `3` : Scheduler s'arrête au `202` ; seules comptent l'exécution initiale et les 2 retries de Lambda.

## 63. event_invoke_config : la première limite gagne
- Sous-thème : invocation
- Niveau : 3
- Source : data-platform · S1-08
- Définition : Lambda abandonne un événement asynchrone dès que l'une des deux limites est atteinte : nombre de tentatives ou âge maximal de l'événement.
- Contexte : Les retries partent environ 1 minute puis 2 minutes après l'échec, mais l'événement peut aussi attendre dans la file interne (fonction limitée en concurrence, throttling) : son âge court pendant ce temps. Un âge maximal trop court fait sauter des retries sans le dire. Bornes de Lambda : 0 à 2 tentatives, 60 à 21 600 secondes.
- Usage : ✅ âge maximal d'au moins quelques minutes pour laisser passer les 2 retries, borné à l'horizon voulu (1 h ici) · ❌ `maximum_event_age_in_seconds = 60` avec 2 retries : le second ne partira pas.

```hcl
# Exemple 1 : 2 retries, horizon 1 h
maximum_retry_attempts       = 2
maximum_event_age_in_seconds = 3600
# retry 1 vers +1 min, retry 2 vers +3 min
# → les deux passent avant 1 h
```

- Quiz : Que répond l'API à `maximum_retry_attempts = 3` ?
- [ ] OK : 3 nouvelles tentatives
- [x] Refus : 2 au maximum
- [ ] OK, ramené à 2 sans erreur
- [ ] OK si `maximum_event_age_in_seconds` ≥ 3600
- Réponse : refus : l'API n'accepte que 0 à 2 nouvelles tentatives ; d'où le bloc `validation` qui l'arrête dès le `plan`.

## 64. Config : read_timeout et retries pour un invoke long
- Sous-thème : invocation
- Niveau : 3
- Source : data-platform · S1-08
- Définition : `botocore.config.Config(read_timeout=…, retries=…)` règle combien de temps le client attend la réponse et combien de fois il renvoie l'appel.
- Contexte : Par défaut, le client attend 60 s (mesuré) ; une Lambda de 300 s fait expirer la lecture alors que l'invocation continue côté AWS. En mode `legacy`, botocore fait jusqu'à 5 tentatives (`_retry.json`) : il relance l'invocation, qui s'exécute alors deux fois. Pour un invoke synchrone long : `read_timeout` au-delà du timeout de la fonction, `total_max_attempts: 1`.
- Usage : ✅ script de rejeu, appel synchrone d'une Lambda lente · ❌ client par défaut pour un handler qui peut dépasser 60 s.

```python
# Exemple 1 : défaut puis réglé
import boto3
from botocore.config import Config

s = boto3.Session(region_name="eu-west-3")
s.client("lambda").meta.config.read_timeout
# → 60
c = s.client("lambda", config=Config(
    read_timeout=330,
    retries={"total_max_attempts": 1}))
c.meta.config.read_timeout   # → 330
```

- Quiz : Client par défaut, handler de 90 s : que se passe-t-il côté AWS ?
- [ ] Une exécution, le client attend
- [x] Plusieurs exécutions : le client relance après 60 s
- [ ] Le handler est interrompu à 60 s
- [ ] Rien : l'appel est refusé
- Réponse : plusieurs exécutions : la lecture expire à 60 s, botocore réessaie, et chaque tentative lance une nouvelle invocation.
