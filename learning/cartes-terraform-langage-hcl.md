---
title: "Cartes · Langage HCL (Terraform)"
type: cartes
langage: Terraform
cours: Langage HCL
created: 2026-10-24
updated: 2026-10-25
---

# Cartes · Langage HCL (Terraform)
Terraform · Langage HCL : blocs, boucles, expressions, provider (format spec v3 de revision-pwa).

## 1. data : un dépôt créé hors Terraform
- Sous-thème : blocs
- Niveau : 1
- Définition : Un bloc `data` lit une ressource existante sans la gérer : ici le dépôt CodeCommit, créé à la main, dont on lit l'ARN et l'URL.
- Contexte : Terraform interroge AWS à chaque `plan` et expose les attributs, mais ne crée, ne modifie ni ne détruit jamais l'objet : `terraform destroy` laisse le dépôt et son code intacts. C'est voulu pour le code source, qui doit survivre à l'infra. Contrepartie : la ressource doit exister avant le premier `plan`, sinon erreur.
- Usage : ✅ ressource créée ailleurs (dépôt, zone DNS, VPC partagé), politiques gérées AWS · ❌ ressource propre au projet : `resource`, pour que Terraform la crée et la suive.

```hcl
# Exemple 1 : lire sans gérer
data "aws_codecommit_repository" "this" {
  repository_name = "revision-pwa"
}
# → .arn, .clone_url_http lisibles
# jamais créé ni détruit par Terraform
```

```bash
# Exemple 2 : la valeur lue
aws codecommit get-repository \
  --repository-name revision-pwa \
  --query \
  'repositoryMetadata.cloneUrlHttp'
# → https://git-codecommit.eu-west-3
#   .amazonaws.com/v1/repos/revision-pwa
```

- Quiz : Quelqu'un renomme le dépôt dans la console : que fait le `terraform plan` suivant ?
- [ ] Il recrée un dépôt `revision-pwa` vide
- [ ] Il renomme le dépôt en retour
- [ ] Rien : l'ARN reste en cache dans l'état
- [x] Il échoue : le `data` ne trouve plus le dépôt
- Réponse : il échoue : un `data` est relu à chaque `plan` et ne sait pas créer ; sans dépôt `revision-pwa`, la lecture lève une erreur.

## 2. local.prefix : un nom par environnement
- Sous-thème : blocs
- Niveau : 1
- Définition : Tous les noms passent par `local.prefix` (`revision-pwa-<env>`), pour faire cohabiter dev et prod dans le même compte sans collision.
- Contexte : Un `locals` est une constante calculée du module (≈ `const` en tête de fichier) : on change l'environnement à un seul endroit, la variable `environment` du `.tfvars`. Le compte AWS est partagé avec d'autres projets : le préfixe évite aussi les conflits de noms avec eux. Mais préfixer les noms ne sépare pas les déclencheurs : les deux environnements écoutent le même dépôt.
- Usage : ✅ tout nom de ressource (rôle, projet, groupe de logs, bucket) · ❌ valeur qui change par env sans être un nom (taille, rétention) : variable dédiée dans le `.tfvars`.

```hcl
# Exemple 1 : un préfixe pour tout
locals {
  prefix = "revision-pwa-${var.environment}"
}
# environment = "dev"
# → local.prefix = "revision-pwa-dev"
```

```hcl
# Exemple 2 : réutilisé partout
name = "${local.prefix}-deploy"
# → "revision-pwa-dev-deploy"
name = "/aws/codebuild/${local.prefix}-deploy"
# → "/aws/codebuild/revision-pwa-dev-deploy"
```

- Quiz : On applique aussi en prod (`environment = "prod"`), même code : un push sur `main` déploie quels environnements ?
- [ ] dev seulement : prod filtre la branche `prod`
- [ ] prod seulement : la dernière règle créée gagne
- [x] dev et prod : les deux règles filtrent `main`
- [ ] Aucun : deux règles sur un dépôt s'annulent
- Réponse : dev et prod : les deux règles filtrent le même dépôt et la même branche ; il faut un filtre différent (branche `prod`, tag) pour la prod.

## 3. resource : l'adresse type.nom
- Sous-thème : blocs
- Niveau : 1
- Définition : Un bloc `resource` décrit un objet réel à créer ; son adresse `type.nom` l'identifie dans le state et dans les références.
- Contexte : Le premier label est le type fourni par le provider (`aws_s3_bucket`), le second un nom local libre, jamais envoyé à AWS : le vrai nom du bucket est l'argument `bucket`. Lire `aws_s3_bucket.raw.id` ailleurs crée une dépendance implicite : Terraform crée le bucket d'abord. Le state associe l'adresse à l'ID réel de l'objet ; l'adresse est donc son identité.
- Usage : ✅ tout objet que Terraform crée et gère (bucket, rôle, Lambda) · ❌ objet créé ailleurs qu'on veut seulement lire : bloc `data`.

```hcl
# Exemple 1 : déclarer et référencer
resource "aws_s3_bucket" "raw" {
  bucket = "data-platform-dev-raw"
}
# adresse : aws_s3_bucket.raw
# lecture : aws_s3_bucket.raw.arn
```

```hcl
# Exemple 2 : dépendance implicite
resource "aws_s3_bucket_versioning" "raw" {
  # lit .id → créé après le bucket
  bucket = aws_s3_bucket.raw.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

- Quiz : Après `apply`, tu renommes le label `"raw"` en `"brut"`, même `bucket` : que prévoit `plan` ?
- [ ] Aucun changement : c'est le même bucket
- [ ] Un update sur place de l'adresse
- [x] Destroy de `raw` et create de `brut`
- [ ] `Error: Duplicate resource`
- Réponse : Destroy de `raw` et create de `brut` : l'adresse est l'identité dans le state ; un bloc `moved { from = … to = … }` garde l'objet.

## 4. locals : nommer un calcul
- Sous-thème : blocs
- Niveau : 1
- Définition : `locals` nomme des valeurs calculées une fois et réutilisées dans le module (≈ des `const` du fichier), lues via `local.x`.
- Contexte : Un local évite de répéter un préfixe ou des tags dans chaque ressource. Ce n'est pas une entrée : l'appelant ne peut pas le changer, contrairement à une `variable`. Un local peut lire des variables, d'autres locals et des attributs de ressources. Plusieurs blocs `locals` peuvent coexister, mais chaque nom reste unique dans le module.
- Usage : ✅ préfixe de nommage, tags communs, expression répétée · ❌ valeur que l'appelant doit pouvoir changer : `variable`.

```hcl
# Exemple 1 : un préfixe commun
locals {
  prefix = "data-platform-${var.env}"
}
resource "aws_s3_bucket" "raw" {
  bucket = "${local.prefix}-raw"
}
# env = "dev" → "data-platform-dev-raw"
```

```hcl
# Exemple 2 : des tags réutilisés
locals {
  tags = {
    project = "data-platform"
    env     = var.env
  }
}
resource "aws_s3_bucket" "logs" {
  bucket = "${local.prefix}-logs"
  tags   = local.tags
}
```

- Quiz : Que donne `value = locals.prefix` dans un `output` ?
- [ ] `"data-platform-dev"`
- [ ] `Error: Unsupported attribute`
- [ ] `null`
- [x] `Error: Reference to undeclared resource`
- Réponse : `Error: Reference to undeclared resource` : on déclare dans `locals` mais on lit avec `local.` au singulier ; `locals.prefix` est pris pour une ressource de type `locals`.

## 5. output : exposer une valeur
- Sous-thème : blocs
- Niveau : 1
- Définition : `output` expose une valeur du module à l'appelant ou au terminal ; `sensitive = true` la masque à l'affichage.
- Contexte : Dans le module racine, les outputs s'affichent après `apply` et se relisent avec `terraform output`, pratique pour passer un nom de bucket à un script ou à la CI (`output -raw`). Dans un module enfant, ils sont la seule chose que l'appelant voit. `sensitive` n'est qu'un masque d'affichage : la valeur reste en clair dans le state, d'où un bucket d'état chiffré et à accès restreint.
- Usage : ✅ nom ou ARN de bucket à transmettre à la CI ou au module appelant · ❌ protéger un secret : le state le contient quand même, le garder dans Secrets Manager.

```hcl
# Exemple 1 : exposer le nom du bucket
output "raw_bucket" {
  value = aws_s3_bucket.raw.bucket
}
# apply →
# raw_bucket = "data-platform-dev-raw"
```

```hcl
# Exemple 2 : masquer à l'affichage
output "token" {
  value     = var.token
  sensitive = true
}
# plan             → (sensitive value)
# apply            → token = <sensitive>
# terraform output → token = <sensitive>
```

- Quiz : Après `apply`, qu'affiche `terraform output token`, le nom précisé ?
- [ ] `token = <sensitive>`
- [x] La valeur en clair, entre guillemets
- [ ] `Error: Output is sensitive`
- [ ] Une chaîne vide
- Réponse : La valeur en clair : demander un output précis le démasque (comme `-json` ou `-raw`), et le state le stocke en clair de toute façon.

## 6. list : lire par index
- Sous-thème : expressions
- Niveau : 1
- Définition : Une `list` est une suite ordonnée de valeurs d'un même type, lue par index à partir de 0 (≈ `string[]` en TS).
- Contexte : Un index hors bornes ne renvoie pas `undefined` : `plan` échoue avec `Invalid index`. Il n'y a pas d'index négatif : le dernier élément se lit `l[length(l) - 1]`. `slice(l, début, fin)` donne une tranche (fin exclue), `contains(l, v)` teste la présence, `length(l)` la taille.
- Usage : ✅ suite ordonnée (jours d'export, sous-réseaux) · ❌ éléments uniques à passer à `for_each` : `set` ; accès par nom : `map`.

```hcl
# Exemple 1 : lire par index
locals {
  sirens = ["483609327", "552100554"]
}
# local.sirens[0] → "483609327"
# length(local.sirens) → 2
# local.sirens[5]
# → Error: Invalid index
```

```hcl
# Exemple 2 : dernier élément, tranche
locals {
  jours   = ["lun", "mar", "mer"]
  dernier = local.jours[
    length(local.jours) - 1]
  debut   = slice(local.jours, 0, 2)
}
# local.dernier → "mer"
# local.debut   → ["lun", "mar"]
# local.jours[-1] → Error: Invalid index
```

- Quiz : Avec la liste de 2 SIREN, que vaut `element(local.sirens, 5)` ?
- [ ] `Error: Invalid index`
- [ ] `null`
- [x] `"552100554"`
- [ ] `"483609327"`
- Réponse : `"552100554"` : `element` boucle (index modulo la longueur, 5 % 2 = 1) au lieu d'échouer.

## 7. map : lire une clé
- Sous-thème : expressions
- Niveau : 1
- Définition : Une `map` associe des clés chaîne à des valeurs d'un même type, lues par `m["clé"]` (≈ `Record<string, T>`).
- Contexte : Une clé absente ne renvoie pas `undefined` : `plan` échoue avec `Invalid index`. Pour une clé facultative, `lookup(m, k, défaut)` ou `try(m[k], défaut)`. Les clés sont toujours des chaînes, même écrites `"75"` pour un département. Toutes les valeurs ont un même type ; des attributs de types différents relèvent d'un `object`.
- Usage : ✅ table de correspondance (département → tribunal, env → rétention) · ❌ attributs de types différents : `object` ; liste de noms sans valeur : `set`.

```hcl
# Exemple 1 : lire une clé
locals {
  trib = { "75" = "Paris",
           "69" = "Lyon" }
}
# local.trib["75"] → "Paris"
# local.trib["13"]
# → Error: Invalid index
```

```hcl
# Exemple 2 : clé facultative
locals {
  trib = { "75" = "Paris" }
  a = lookup(local.trib, "13", "?")
  b = try(local.trib["13"], "?")
}
# local.a → "?"
# local.b → "?"
```

- Quiz : Que vaut `local.trib[75]`, le nombre écrit sans guillemets ?
- [x] `"Paris"`
- [ ] `Error: Invalid index`
- [ ] `null`
- [ ] `Error: Invalid key type`
- Réponse : `"Paris"` : Terraform convertit le nombre `75` en chaîne `"75"`, le type des clés d'une map.

## 8. for : construire une liste
- Sous-thème : boucles
- Niveau : 1
- Définition : `[for x in coll : expr]` transforme une collection en liste (≈ `.map()` en TS), avec un `if` final optionnel pour filtrer.
- Contexte : L'expression ne modifie rien : elle produit une nouvelle valeur, souvent rangée dans un local. Le `if` final joue le rôle de `.filter()`. Sur une map ou un objet, deux variables `for k, v in m` donnent la clé et la valeur. Le résultat est une liste : pour l'utiliser dans `for_each`, le passer à `toset()`.
- Usage : ✅ dériver des noms, filtrer une entrée · ❌ créer plusieurs ressources : `for_each` sur la ressource ; logique longue : la découper en plusieurs locals.

```hcl
# Exemple 1 : transformer
locals {
  sirens = ["483609327", "552100554"]
  courts = [for s in local.sirens :
            substr(s, 0, 3)]
}
# local.courts → ["483", "552"]
```

```hcl
# Exemple 2 : filtrer avec if
locals {
  envs   = ["dev", "prod", "sandbox"]
  gardes = [for e in local.envs :
            e if e != "sandbox"]
}
# local.gardes → ["dev", "prod"]
```

- Quiz : Avec `m = { "75" = "Paris", "69" = "Lyon" }`, que vaut `[for k, v in m : "${k}-${v}"]` ?
- [ ] `["75-Paris", "69-Lyon"]`
- [x] `["69-Lyon", "75-Paris"]`
- [ ] `["Paris-75", "Lyon-69"]`
- [ ] `Error: Invalid for expression`
- Réponse : `["69-Lyon", "75-Paris"]` : une map est parcourue dans l'ordre trié des clés, pas dans l'ordre d'écriture.

## 9. toset : dédoublonner
- Sous-thème : boucles
- Niveau : 1
- Définition : `toset` convertit une liste en ensemble sans doublon ni ordre propre, la forme attendue par `for_each` pour une liste de chaînes.
- Contexte : Un set n'a pas d'index : il se parcourt avec `for` ou se reconvertit avec `tolist`. Terraform l'affiche trié, mais le code ne doit pas compter sur un ordre. Comme une liste, un set n'a qu'un seul type d'élément : à la conversion, Terraform choisit un type commun pour tous les éléments.
- Usage : ✅ passer une liste de noms à `for_each`, dédoublonner une entrée · ❌ ordre significatif ou accès par position : garder la `list`.

```hcl
# Exemple 1 : dédoublonner
locals {
  jours = toset(["lun", "mar", "lun"])
}
# length(local.jours) → 2
# local.jours → toset(["lun", "mar"])
```

```hcl
# Exemple 2 : la forme de for_each
variable "jours" {
  type    = list(string)
  default = ["lun", "mar"]
}
resource "aws_s3_object" "export" {
  for_each = toset(var.jours)
  bucket   = "data-platform-dev-raw"
  key      = "exports/${each.key}.csv"
}
```

- Quiz : Que vaut `length(toset([1, "1"]))` ?
- [ ] `2`
- [x] `1`
- [ ] `Error: Inconsistent types`
- [ ] `0`
- Réponse : `1` : le nombre `1` est converti en chaîne `"1"`, le type commun, puis le doublon disparaît.

## 10. aws_s3_object : data ou resource
- Sous-thème : blocs
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `resource "aws_s3_object"` écrit un objet et le gère ; `data "aws_s3_object"` lit un objet déposé par un autre outil, sans jamais le modifier.
- Contexte : Même type, deux rôles. Le pointeur `current.json` est écrit par `make lambdas-publish` (Python, boto3) : Terraform ne fait que le lire, à chaque plan. Le data source expose `body`, `etag`, `version_id`, `content_type`, `metadata`, `last_modified`. Un objet lu n'est pas dans les ressources de l'état : `make down` ne le supprime pas.
- Usage : ✅ `data` pour un fichier produit par un script, une CI ou une autre équipe · ❌ `resource` sur un fichier que quelqu'un d'autre réécrit : deux propriétaires.

```hcl
# Exemple 1 : lire le pointeur publié
data "aws_s3_object" "lambda_pointer" {
  for_each = local.lambdas

  bucket = local.artifacts_bucket
  key    = "lambdas/${each.key}/current.json"
}
# → .body = "{\"key\": \"lambdas/…zip\", …}"
```

- Quiz : Le pointeur est déclaré en `resource "aws_s3_object"` (`content = jsonencode(...)`), puis le script le réécrit : que propose le `plan` suivant ?
- [ ] Rien : Terraform relit l'objet
- [x] Remettre l'ancien contenu
- [ ] Supprimer l'objet
- [ ] Adopter le nouveau contenu
- Réponse : remettre l'ancien contenu : pour une `resource`, le code fait foi ; la réécriture par le script est une dérive que Terraform « corrige », d'où le `data`.

## 11. aws_s3_object : body selon le Content-Type
- Sous-thème : blocs
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Le data source `aws_s3_object` ne remplit `body` que pour un `Content-Type` lisible : `text/*`, `application/json`, YAML, XML ; sinon `body` reste vide.
- Contexte : Le provider refuse de charger du binaire dans l'état. Le test porte sur l'en-tête `Content-Type` de l'objet, jamais sur son extension : un `current.json` envoyé sans type reçoit `binary/octet-stream` de S3, et `body` est vide. D'où `ContentType="application/json"` dans le `put_object` du script de publication. Pour un zip, on lit `etag` ou des métadonnées, jamais `body`.
- Usage : ✅ fixer `ContentType` à l'envoi de tout fichier que Terraform doit lire · ❌ lire un binaire par `body` : vide ; utiliser `etag`, `metadata` ou un pointeur JSON.

```python
# Exemple 1 : le type que S3 met par défaut
import boto3
from moto import mock_aws

with mock_aws():
    s3 = boto3.client("s3", region_name="eu-west-3")
    s3.create_bucket(
        Bucket="artefacts",
        CreateBucketConfiguration={
            "LocationConstraint": "eu-west-3"})
    s3.put_object(Bucket="artefacts",
                  Key="current.json", Body=b"{}")
    h = s3.head_object(Bucket="artefacts",
                       Key="current.json")
h["ContentType"]  # → 'binary/octet-stream'
```

- Quiz : Le pointeur est envoyé avec `ContentType="text/plain"` : `body` est-il rempli ?
- [x] Oui : tout `text/*` est lisible
- [ ] Non : seul `application/json` l'est
- [ ] Non : il faut l'extension `.txt`
- [ ] Oui, mais encodé en base64
- Réponse : oui : le provider accepte `text/*`, `application/json`, YAML, XML et quelques autres (vérifié dans le provider AWS 6.69) ; `jsondecode` lit ensuite le texte.

## 12. jsondecode : du JSON vers HCL
- Sous-thème : expressions
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `jsondecode(chaîne)` transforme un texte JSON en valeur HCL (objet, tuple, nombre, booléen), dont on lit ensuite les champs avec `.` (≈ `JSON.parse`).
- Contexte : L'inverse de `jsonencode`. Les types JSON sont conservés : un nombre reste un nombre, `true` un booléen. Un champ absent lève `Unsupported attribute` au plan, comme une propriété manquante en TS strict ; `lookup(obj, "champ", défaut)` ou `try(obj.champ, défaut)` donnent une valeur de repli. Une chaîne vide n'est pas du JSON : `Call to function "jsondecode" failed: EOF`.
- Usage : ✅ lire un pointeur, un manifest ou un output JSON d'un autre outil · ❌ construire du JSON à la main par interpolation de chaînes : `jsonencode`.

```hcl
# Exemple 1 : terraform console
jsondecode("{\"size\": 21180000}").size
# → 21180000 (un nombre)
jsondecode("{\"key\":\"k\"}").base64sha256
# → Error: Unsupported attribute
jsondecode("")
# → Error: … jsondecode failed: EOF
```

- Quiz : Que vaut `jsondecode("{\"git_dirty\": true}").git_dirty == "true"` ?
- [ ] `true`
- [x] `false`
- [ ] Erreur de type
- [ ] `"true"`
- Réponse : `false` (vérifié dans `terraform console`) : `==` compare aussi les types, sans conversion ; un booléen n'est jamais égal à la chaîne `"true"`.

## 13. type de ressource : le nom de l'API AWS
- Sous-thème : blocs
- Niveau : 1
- Source : data-platform · S1-08
- Définition : Le type d'une ressource AWS reprend l'objet de l'API en snake_case, préfixé du service : `PutFunctionEventInvokeConfig` → `aws_lambda_function_event_invoke_config`.
- Contexte : On ne mémorise pas ces noms : on part du besoin (« retries d'une Lambda asynchrone »), la doc AWS donne la commande (`aws lambda put-function-event-invoke-config`), le registre ou le schéma local donne la ressource. Les attributs suivent la même règle (`MaximumRetryAttempts` → `maximum_retry_attempts`). Exceptions fréquentes : un objet de l'API éclaté en plusieurs ressources (bucket S3 : `aws_s3_bucket_versioning`, `…_lifecycle_configuration`).
- Usage : ✅ deviner puis vérifier un nom dans le registre ou `providers schema` · ❌ inventer un nom au hasard, ou chercher un réglage S3 en argument de `aws_s3_bucket` : il a souvent sa ressource.

```bash
# Exemple 1 : de la CLI AWS à Terraform
# aws lambda put-function-event-invoke-config
#   --maximum-retry-attempts 2
# → resource "aws_lambda_function_event_invoke_config"
#     maximum_retry_attempts = 2
# aws scheduler create-schedule
# → resource "aws_scheduler_schedule"
```

- Quiz : Quelle ressource règle le versioning d'un bucket avec le provider AWS v5 ?
- [ ] Argument `versioning` de `aws_s3_bucket`
- [x] `aws_s3_bucket_versioning`
- [ ] `aws_s3_versioning_config`
- [ ] `aws_s3_bucket_policy`
- Réponse : `aws_s3_bucket_versioning` : depuis la v4, les réglages du bucket sont des ressources séparées, nommées d'après l'API `PutBucketVersioning`.

## 14. Types : conversion automatique
- Sous-thème : expressions
- Niveau : 2
- Définition : Terraform convertit automatiquement entre chaîne, nombre et booléen selon le type attendu (`"5"` accepté pour un argument `number`).
- Contexte : Un nombre interpolé dans `"${…}"` devient une chaîne ; `"true"` passé à un `bool` devient booléen. `tonumber`, `tostring` et `tobool` forcent la conversion et échouent si elle est impossible, au plan. Ces conversions servent les arguments et les gabarits ; les opérateurs, eux, ne suivent pas forcément la même règle.
- Usage : ✅ composer un nom à partir de valeurs typées, lire un nombre venu d'une chaîne avec `tonumber` · ❌ comparer des valeurs de types différents sans conversion explicite.

```hcl
# Exemple 1 : conversion dans un gabarit
locals {
  siren = "483609327"
  annee = 2026
  cle   = "${local.siren}-${local.annee}"
}
# local.cle → "483609327-2026"
```

```hcl
# Exemple 2 : conversions explicites
# tonumber("12")  → 12
# tostring(5)     → "5"
# tonumber("12a")
# → Error: Invalid function argument
```

- Quiz : Que vaut `"5" == 5` ?
- [ ] `true`
- [x] `false`
- [ ] `Error: Invalid operand`
- [ ] `null`
- Réponse : `false` : `==` compare type et valeur sans conversion (≈ `===` en TS) ; écrire `tostring(x) == "5"`.

## 15. Condition : un type commun
- Sous-thème : expressions
- Niveau : 2
- Définition : `cond ? a : b` choisit une valeur (≈ ternaire TS) ; Terraform convertit les deux branches vers un type commun, ou échoue.
- Contexte : Terraform type l'expression avant de connaître la condition : si aucune conversion ne réunit les deux branches, le plan échoue, même pour la branche jamais choisie. Deux usages courants : une valeur qui dépend de l'env, et `count = var.x ? 1 : 0` pour une ressource facultative. Une expression longue se coupe à l'intérieur de parenthèses.
- Usage : ✅ valeur par env (rétention, taille), ressource facultative · ❌ plus de deux cas : une `map` indexée par env (`local.retention[var.env]`).

```hcl
# Exemple 1 : valeur selon l'env
locals {
  retention = (var.env == "prod"
    ? 365 : 30)
}
# env = "dev" → 30
```

```hcl
# Exemple 2 : ressource facultative
variable "logs" { default = false }
resource "aws_s3_bucket" "logs" {
  count  = var.logs ? 1 : 0
  bucket = "data-platform-dev-logs"
}
# logs = false → 0 instance
```

- Quiz : Que donne `true ? [] : {}` ?
- [ ] `[]`
- [ ] `{}`
- [ ] `null`
- [x] `Error: Inconsistent conditional result types`
- Réponse : `Error: Inconsistent conditional result types` : un tuple vide et un objet vide n'ont aucun type commun.

## 16. merge : fusionner des tags
- Sous-thème : expressions
- Niveau : 2
- Définition : `merge` fusionne plusieurs maps ou objets en un seul (≈ `{ ...a, ...b }`), pratique pour compléter des tags communs.
- Contexte : Les arguments sont lus de gauche à droite : en cas de clé commune, le plus à droite écrase. Un argument `null` est ignoré. Pour des tags identiques sur toutes les ressources, le provider AWS offre `default_tags` dans son bloc `provider`, ce qui évite de répéter `merge` partout.
- Usage : ✅ ajouter des tags propres à une ressource, surcharger des valeurs par défaut · ❌ mêmes tags partout : `default_tags` du provider.

```hcl
# Exemple 1 : tags communs + propres
locals {
  tags = { project = "data-platform",
           env     = "dev" }
  raw  = merge(local.tags,
    { layer = "raw", env = "test" })
}
# → { env = "test", layer = "raw",
#     project = "data-platform" }
```

- Quiz : Que vaut `merge({t = {a = 1}}, {t = {b = 2}})` ?
- [ ] `{ t = { a = 1, b = 2 } }`
- [x] `{ t = { b = 2 } }`
- [ ] `{ t = { a = 1 } }`
- [ ] `Error: Duplicate object key`
- Réponse : `{ t = { b = 2 } }` : `merge` est superficiel, la valeur entière de `t` est remplacée, sans fusion en profondeur.

## 17. can : une erreur en booléen
- Sous-thème : expressions
- Niveau : 2
- Définition : `can(expr)` renvoie `true` si l'expression s'évalue sans erreur, sinon `false` : la forme idéale d'une condition de `validation`.
- Contexte : Beaucoup de fonctions échouent au lieu de renvoyer `false` : `regex` sans correspondance, `tonumber("abc")`, un index absent. `can` capture l'erreur et renvoie un booléen ; `try(expr, repli)` renvoie la première expression qui réussit. Ils servent à tester des valeurs, pas à masquer un code mal écrit.
- Usage : ✅ condition de `validation` sur un format (`regex`), lecture tolérante d'une donnée facultative avec `try` · ❌ masquer une erreur de logique : corriger l'expression.

```hcl
# Exemple 1 : valider un format
variable "account_id" {
  type = string
  validation {
    condition = can(regex(
      "^[0-9]{12}$", var.account_id))
    error_message = "12 chiffres."
  }
}
```

```hcl
# Exemple 2 : can et try
# regex("^[0-9]+$", "12a")
# → Error: Error in function call
# can(regex("^[0-9]+$", "12a"))
# → false
# try(tonumber("12a"), 0) → 0
```

- Quiz : Que donne `can(var.inexistante)` quand aucune variable `inexistante` n'est déclarée ?
- [ ] `false`
- [ ] `true`
- [x] `Error: Reference to undeclared input variable`
- [ ] `null`
- Réponse : `Error: Reference to undeclared input variable` : `can` ne rattrape que les erreurs d'évaluation, pas une référence invalide, vérifiée avant.

## 18. for : construire une map
- Sous-thème : boucles
- Niveau : 2
- Définition : `{for x in coll : clé => valeur}` construit une map à partir d'une collection (≈ `Object.fromEntries`).
- Contexte : Les accolades et `=>` donnent une map au lieu d'une liste. C'est la forme typique pour préparer un `for_each` à partir d'une liste d'objets, indexée par un champ stable (le nom du bucket), plutôt que par une position. Un `if` final filtre comme dans la version liste.
- Usage : ✅ indexer une liste d'objets par un champ unique, préparer un `for_each` · ❌ simple transformation de valeurs : `[for …]`.

```hcl
# Exemple 1 : liste → map
locals {
  noms = ["raw", "curated"]
  arns = { for n in local.noms :
    n => "arn:aws:s3:::dp-${n}" }
}
# local.arns["raw"]
# → "arn:aws:s3:::dp-raw"
```

```hcl
# Exemple 2 : préparer un for_each
locals {
  buckets = [
    { nom = "raw", jours = 30 },
    { nom = "logs", jours = 90 },
  ]
  par_nom = { for b in local.buckets :
    b.nom => b }
}
# for_each = local.par_nom
# each.value.jours → 30, puis 90
```

- Quiz : Que vaut `{for s in ["4a", "4b"] : substr(s, 0, 1) => s}` ?
- [ ] `{ "4" = "4b" }`
- [ ] `{ "4" = "4a" }`
- [x] `Error: Duplicate object key`
- [ ] `{ "4" = ["4a", "4b"] }`
- Réponse : `Error: Duplicate object key` : deux éléments donnent la clé `"4"` ; `=> s...` (avec `...`) les regroupe en liste.

## 19. count : instances indexées
- Sous-thème : boucles
- Niveau : 2
- Définition : `count = n` crée n instances d'une ressource, adressées `res[0]`, `res[1]`… et distinguées par `count.index`.
- Contexte : Chaque instance est identifiée par sa **position** dans le state, pas par sa valeur. C'est parfait pour « 0 ou 1 instance » (`count = var.x ? 1 : 0`) ou N copies identiques. Le splat `res[*].attr` lit l'attribut de toutes les instances d'un coup.
- Usage : ✅ ressource facultative, N copies identiques · ❌ une instance par élément d'une liste qui évolue : `for_each`.

```hcl
# Exemple 1 : une instance par jour
variable "jours" {
  default = ["lun", "mar", "mer"]
}
resource "aws_s3_object" "export" {
  count  = length(var.jours)
  bucket = "data-platform-dev-raw"
  key    = var.jours[count.index]
}
# → export[0], export[1], export[2]
```

```hcl
# Exemple 2 : lire les instances
# une instance :
# aws_s3_object.export[0].key → "lun"
# toutes, avec le splat [*] :
# aws_s3_object.export[*].key
# → ["lun", "mar", "mer"]
```

- Quiz : Après `apply`, tu retires `"mar"` de la liste : que prévoit `plan` ?
- [ ] Détruire `export[1]` seulement
- [ ] Aucun changement
- [x] Changer `export[1]` en `mer`, détruire `export[2]`
- [ ] Tout détruire puis tout recréer
- Réponse : Changer `export[1]` en `mer` et détruire `export[2]` : les index se décalent ; `for_each` éviterait de toucher `mer`.

## 20. for_each : instances par clé
- Sous-thème : boucles
- Niveau : 2
- Définition : `for_each` crée une instance par clé d'une map ou d'un set, adressée `res["clé"]` : retirer un élément ne touche que lui.
- Contexte : `each.key` donne la clé, `each.value` la valeur (égale à la clé pour un set). Les clés doivent être connues au plan : pas d'ID généré à l'apply, sinon `Invalid for_each argument`. Passer de `count` à `for_each` change les adresses : prévoir des blocs `moved` pour ne rien recréer.
- Usage : ✅ une ressource par élément nommé (buckets, objets par jour, rôles) · ❌ clés calculées à l'apply ; simple « 0 ou 1 » : `count`.

```hcl
# Exemple 1 : un objet par jour
resource "aws_s3_object" "export" {
  for_each = toset(["lun", "mar"])
  bucket   = "data-platform-dev-raw"
  key      = "exports/${each.key}.csv"
}
# → export["lun"], export["mar"]
```

```hcl
# Exemple 2 : map → each.value
resource "aws_s3_bucket" "b" {
  for_each = {
    raw  = "data-platform-dev-raw"
    logs = "data-platform-dev-logs"
  }
  bucket = each.value
}
# aws_s3_bucket.b["raw"].arn
```

```hcl
# Exemple 3 : chaîner sur les buckets
resource "aws_s3_bucket_versioning" "this" {
  for_each = aws_s3_bucket.this
  bucket   = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}
# mêmes clés que les buckets :
# → this["raw"], this["logs"]
# each.value = le bucket entier
```

- Quiz : Que donne `for_each = ["lun", "mar"]`, une liste sans `toset` ?
- [x] `Error: Invalid for_each argument`
- [ ] Deux instances `["lun"]` et `["mar"]`
- [ ] Deux instances `[0]` et `[1]`
- [ ] Un `Warning`, puis la conversion en set
- Réponse : `Error: Invalid for_each argument` : `for_each` exige une map ou un set de chaînes ; une liste peut contenir des doublons, d'où `toset()`.

## 21. default_tags : taguer tout le root
- Sous-thème : provider
- Niveau : 2
- Définition : `default_tags` dans le provider pose des tags sur toutes les ressources taggables, sans les répéter dans chaque `resource`.
- Contexte : Le provider fusionne `default_tags` et les `tags` de la ressource dans l'attribut calculé `tags_all`, celui qui part réellement sur AWS. Les ressources de réglage (`aws_s3_bucket_versioning`…) n'ont pas de tags : seul le bucket les porte. Dans data-platform, `make plan` vérifie ensuite que chaque ressource taggable a bien ses tags (`check_tags.py`).
- Usage : ✅ tags communs d'un root (`project`, `component`, `managed_by`) · ❌ tag propre à une seule ressource (`Name`) : dans son bloc `tags`.

```hcl
# Exemple 1 : tags posés par le provider
# plan → tags_all = {
#   project = "data-platform" }
provider "aws" {
  default_tags {
    tags = { project = "data-platform" }
  }
}
resource "aws_s3_bucket" "tfstate" {
  bucket = local.bucket
}
```

```hcl
# Exemple 2 : hérité par les modules
# modules/b/main.tf : aucun provider
resource "aws_s3_bucket" "this" {
  bucket = "dp-dev-raw"
  tags   = { layer = "raw" }
}
# root : default_tags = merge(
#   { project = "data-platform" },
#   { environment = "dev" })
# plan → tags_all = {
#   environment = "dev", layer = "raw",
#   project = "data-platform" }
```

- Quiz : Provider : `component = "tfstate"` ; ressource : `tags = { component = "etat" }`. Que vaut `tags_all.component` ?
- [ ] `"tfstate"`
- [x] `"etat"`
- [ ] `["tfstate", "etat"]`
- [ ] `Error: duplicate tag`
- Réponse : `"etat"` : le tag de la ressource l'emporte sur `default_tags` ; `tags_all` est la fusion des deux.

## 22. allowed_account_ids : le bon compte
- Sous-thème : provider
- Niveau : 2
- Définition : `allowed_account_ids` dans le provider fait échouer Terraform si les credentials pointent sur un compte absent de la liste.
- Contexte : Avec plusieurs profils AWS (perso, dev, prod), un mauvais `AWS_PROFILE` suffit à créer des ressources sur le mauvais compte. Le provider lit le compte des credentials (appel STS) dès sa configuration et s'arrête avant toute ressource. L'account id vient d'une variable validée par une regex à 12 chiffres, rangée dans `local.auto.tfvars` gitignoré. `forbidden_account_ids` fait l'inverse.
- Usage : ✅ tout root qui écrit sur un compte précis (bootstrap, `infra/`) · ❌ dans un module réutilisable : le garde-fou va dans le root.

```hcl
# Exemple 1 : refuser les autres comptes
provider "aws" {
  region              = var.region
  profile             = var.profile
  allowed_account_ids = [var.account_id]
}
```

```hcl
# Exemple 2 : un account id bien formé
variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "12 chiffres attendus."
  }
}
# -var account_id=12345
# → Error: Invalid value for variable
```

- Quiz : Le profil choisi pointe sur un autre compte : que fait `terraform plan` ?
- [ ] Il planifie, et `apply` échouera
- [ ] Il bascule sur le compte autorisé
- [x] Il échoue avant toute ressource
- [ ] Il affiche un avertissement et continue
- Réponse : il échoue tout de suite (`AWS account ID not allowed`) : le provider vérifie le compte dès sa configuration, avant toute data source ou ressource.

## 23. output -raw : la valeur brute
- Sous-thème : blocs
- Niveau : 2
- Définition : `terraform output -raw nom` affiche la valeur d'une sortie sans guillemets, prête pour une variable shell ou un Makefile.
- Contexte : Les sorties sont le contrat du bootstrap : le root principal ne lit pas son état, on reporte `state_bucket` et `region` dans `backend.hcl`. `-raw` ne marche que pour une chaîne, un nombre ou un booléen : une liste ou un objet donne `Unsupported value for raw output`, il faut `-json` et `jq`. Les Makefiles s'en servent avec `$(shell …)` pour ne jamais taper un nom de bucket.
- Usage : ✅ alimenter un script, un `aws s3 sync`, une variable Makefile (`SITE_BUCKET`) · ❌ sortie liste ou map : `-json`.

```bash
# Exemple 1 : la valeur, sans guillemets
B=$(terraform -chdir=infra/bootstrap \
  output -raw state_bucket)
echo "$B"
# → data-platform-tfstate-<id>
aws s3 ls "s3://$B/"
# → PRE dev/
```

```makefile
# Exemple 2 : dans un Makefile
TF = terraform -chdir=infra
SITE_BUCKET ?= $(shell $(TF) output -raw site_bucket)
```

- Quiz : Que contient `B` après `B=$(terraform output state_bucket)`, sans `-raw` ?
- [ ] `data-platform-tfstate-<id>`
- [ ] `state_bucket = "data-platform-tfstate-<id>"`
- [x] `"data-platform-tfstate-<id>"`
- [ ] Le JSON `{"value": …}`
- Réponse : la valeur avec ses guillemets : sans option, `output` affiche du HCL ; `s3://$B` désignerait alors un bucket au nom invalide.

## 24. required_version : la version de la CLI
- Sous-thème : blocs
- Niveau : 2
- Source : data-platform · S1-01
- Définition : `required_version` dans le bloc `terraform {}` refuse toute CLI Terraform hors de la contrainte, dès `init`, avant de toucher l'état.
- Contexte : Le code s'appuie sur des fonctionnalités récentes (validations croisées de variables en 1.9, verrou S3 natif ensuite) : une CLI trop vieille échouerait plus loin, au pire moment. `>= 1.9` fixe un plancher, `~> 1.9` autorise tout 1.x depuis 1.9, `~> 1.9.0` bloque à 1.9.x. À ne pas confondre avec `required_providers`, qui contraint les providers.
- Usage : ✅ un plancher `>= 1.9` dans chaque root (`infra/`, `infra/bootstrap/`) · ❌ une contrainte serrée sur le patch : chaque montée de la CLI casse `init` pour toute l'équipe.

```hcl
# Exemple 1 : un plancher (infra/versions.tf)
terraform {
  required_version = ">= 1.9"
}
# terraform 1.14.4 : init OK
# terraform 1.8.x  : init refusé
```

```bash
# Exemple 2 : contrainte non tenue
# required_version = ">= 2.0"
terraform init
# Error: Unsupported Terraform Core
#   version
# This configuration does not support
#   Terraform version 1.14.4.
```

- Quiz : Avec `required_version = "~> 1.9.0"`, que fait `terraform init` en 1.14.4 ?
- [ ] Il passe : 1.14 ≥ 1.9
- [ ] Il passe avec un avertissement
- [x] `Unsupported Terraform Core version`
- [ ] Il télécharge une 1.9.x
- Réponse : erreur `Unsupported Terraform Core version` : `~> 1.9.0` n'autorise que le dernier chiffre (1.9.x), et Terraform ne télécharge jamais sa propre CLI.

## 25. filebase64sha256 : l'empreinte d'un binaire
- Sous-thème : expressions
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `filebase64sha256("x.zip")` rend le sha256 d'un fichier en base64, le format qu'attend `source_code_hash` ; `filesha256` le rend en hexadécimal.
- Contexte : `base64sha256(file("x.zip"))` paraît équivalent, mais `file()` exige de l'UTF-8 : sur un zip, erreur `contents of "f.zip" are not valid UTF-8` (mesuré). Les fonctions `file…` hachent les octets bruts. La valeur est calculée au `plan`, sur le fichier présent à ce moment : construire le zip avant (`make lambdas-build`, puis `make plan`).
- Usage : ✅ `source_code_hash` d'une Lambda ou d'une couche · ❌ `base64sha256(file(…))` sur un binaire ; `filesha256` là où la base64 est attendue.

```hcl
# Exemple 1 : terraform console (mesuré)
> filebase64sha256("a.txt")   # "A1\n"
"T8k6fjtH5CEuk451ZcVrh/6mlRRo9Zsf0ZzEwdg0PyI="
> filesha256("a.txt")
"4fc93a7e3b47e4212e938e7565c56b87fea6951468f59b1fd19cc4c1d8343f22"
> filebase64sha256("build/ingest-bodacc.zip")
"SIF3hiDVJCLXmMcvSwLBVm/BF/UEfFYHQLbbbqsinz8="
```

```python
# Exemple 2 : le même calcul en Python
import base64, hashlib
d = hashlib.sha256(b"A1\n").digest()
base64.b64encode(d).decode()
# → 'T8k6fjtH5CEuk451ZcVrh/6mlRRo9Zsf0ZzEwdg0PyI='
```

- Quiz : Que donne `base64encode(filesha256("a.txt"))` ?
- [ ] La même valeur que `filebase64sha256("a.txt")`
- [x] Une chaîne de 88 caractères, différente
- [ ] Une erreur de type
- [ ] L'hexadécimal, inchangé
- Réponse : 88 caractères, différente (mesuré) : c'est la base64 du **texte** hexadécimal (64 caractères), pas des 32 octets de l'empreinte.

## 26. data source : lu au plan
- Sous-thème : blocs
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Un data source dont tous les arguments sont connus est lu pendant le `plan` : un objet absent fait échouer le plan, avant toute création.
- Contexte : D'où l'ordre `bootstrap → lambdas-publish → plan → up`, réuni dans `make deploy`. Au tout premier déploiement d'une Lambda, son pointeur doit déjà exister. La lecture n'est reportée à l'`apply` que si un argument est inconnu au plan (référence à une ressource pas encore créée) ou si le data source dépend d'une ressource qui change.
- Usage : ✅ publier tout ce que les data sources lisent avant le `plan` · ❌ compter sur l'`apply` pour créer ce qu'un data source du même plan lit : il échoue avant.

```makefile
# Exemple 1 : l'ordre est dans la cible
deploy: lambdas-publish up
# 1. zip + current.json dans artifacts
# 2. plan : data source lit current.json
# 3. apply : la fonction copie le zip
```

```bash
# Exemple 2 : l'erreur, mesurée (S1-09)
terraform plan   # pointeur jamais publié
# → Error: reading S3 Bucket
#   (data-platform-artifacts-<account_id>)
#   Object (lambdas/nope/current.json):
#   couldn't find resource
```

- Quiz : Une nouvelle Lambda est ajoutée à `local.lambdas` sans être publiée ; `make plan` : résultat ?
- [ ] Un plan sans la nouvelle Lambda
- [x] Tout le plan échoue
- [ ] La Lambda est créée sans code
- [ ] Le plan passe, l'`apply` échoue
- Réponse : tout le plan échoue : une seule lecture de data source en erreur arrête le plan entier, même pour les ressources qui n'en dépendent pas.

## 27. data source : relu à chaque plan
- Sous-thème : blocs
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Terraform relit chaque data source à chaque `plan` : un pointeur republié change `s3_key` et `source_code_hash`, donc la fonction, sans toucher au code.
- Contexte : Le code Terraform ne contient aucune version : il dit « déploie ce que désigne le pointeur ». Le plan affiche alors `~ update in-place` sur `aws_lambda_function`, ancienne et nouvelle clé côte à côte. Conséquence : deux `plan` du même commit peuvent différer si quelqu'un a publié entre-temps ; le dépôt seul ne dit plus ce qui sera déployé.
- Usage : ✅ un pointeur relu pour suivre la dernière publication en dev · ❌ en prod sans contrôle : passer la clé en variable, versionnée avec le pipeline.

```bash
# Exemple 1 : republier, puis planifier
make lambdas-publish   # nouveau zip
make plan
# ~ module.lambda["ingest-bodacc"]
#   .aws_lambda_function.this
#   ~ s3_key = "lambdas/…/4881…zip"
#           -> "lambdas/…/9c02…zip"
# Plan: 0 to add, 1 to change
```

- Quiz : On lance `terraform plan -out=tfplan`, quelqu'un republie, puis `terraform apply tfplan` : quel zip est déployé ?
- [x] Celui lu au moment du plan
- [ ] Le nouveau, relu à l'`apply`
- [ ] Aucun : plan périmé, erreur
- [ ] Les deux, en deux versions
- Réponse : celui lu au plan : un plan sauvé fige les valeurs des data sources ; l'`apply` exécute ce plan sans relire le pointeur.

## 28. for + jsondecode : décoder une seule fois
- Sous-thème : boucles
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `{ for k, o in data.aws_s3_object.lambda_pointer : k => jsondecode(o.body) }` décode chaque pointeur une fois, dans un `local` réutilisable.
- Contexte : `lambdas.tf` appelle `jsondecode(...body)` deux fois par fonction (`key`, `base64sha256`) : correct, mais répétitif. Un `local` construit une map nom → pointeur décodé (`local.pointers[each.key].key`), lisible dans `terraform console`. Les clés de la map viennent du `for_each` du data source, donc de `local.lambdas` : les deux restent alignées.
- Usage : ✅ plusieurs champs lus dans le même JSON, pour plusieurs instances · ❌ un `jsondecode` par attribut recopié : une erreur de chemin à corriger partout.

```hcl
# Exemple 1 : terraform console
{ for k, o in {
    a = { body = "{\"key\":\"x\"}" }
  } : k => jsondecode(o.body) }["a"].key
# → "x"
```

```hcl
# Exemple 2 : dans lambdas.tf
locals {
  pointers = {
    for k, o in data.aws_s3_object.lambda_pointer :
    k => jsondecode(o.body)
  }
}
# key = local.pointers[each.key].key
```

- Quiz : La même expression écrite entre `[ ]` au lieu de `{ }`, avec `k =>` : résultat ?
- [ ] Une liste de pointeurs décodés
- [ ] Une liste de paires `[clé, valeur]`
- [x] Erreur : pas de clé dans un tuple
- [ ] Une map, comme avec `{ }`
- Réponse : erreur `Key expression is not valid when building a tuple` (vérifié dans `terraform console`) : `[for …]` construit un tuple, `k =>` n'est permis qu'entre `{ }`.

## 29. for_each : lire une instance, ou toutes
- Sous-thème : boucles
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Un data source en `for_each` se lit par clé (`data.aws_s3_object.lambda_pointer["ingest-bodacc"]`) ; sans clé, `Missing resource instance key`.
- Contexte : Le bloc devient une map d'instances : `data.aws_s3_object.lambda_pointer` seul est cette map, pas un objet. Dans un autre bloc en `for_each` sur la même map, `[each.key]` relie les instances deux à deux. Pour toutes les valeurs : `values(...)` donne une liste, sur laquelle le splat `[*]` marche. L'erreur sans clé tombe dès `terraform validate`.
- Usage : ✅ `[each.key]` entre deux blocs bouclés sur la même map, `values()` pour un output global · ❌ `[0]` sur un `for_each` : les instances n'ont pas d'index.

```hcl
# Exemple 1 : sans clé d'instance
output "o" {
  value = data.aws_s3_object.lambda_pointer.body
}
# terraform validate
# → Error: Missing resource instance key
# → … use: lambda_pointer[each.key]
```

- Quiz : Quelle expression donne la liste des `key` de toutes les instances d'une ressource en `for_each` ?
- [ ] `res[*].key`
- [x] `values(res)[*].key`
- [ ] `res["*"].key`
- [ ] `res.key`
- Réponse : `values(res)[*].key` : le splat n'itère que sur une liste ; sur la map d'instances, `[*]` l'enveloppe telle quelle et `.key` échoue (`Unsupported attribute`, vérifié en console).

## 30. for_each : une map de config qui choisit
- Sous-thème : boucles
- Niveau : 2
- Source : data-platform · S1-08
- Définition : Boucler sur une map dédiée (`local.schedules`) plutôt que sur la map complète (`local.lambdas`) ne crée des ressources que pour les clés choisies.
- Contexte : Les deux maps partagent leurs clés : dans la boucle, `module.lambda[each.key]` relie la planification à sa fonction. Ajouter une Lambda sans l'ajouter à `local.schedules` ne lui donne ni rôle ni planification. Une clé de `local.schedules` absente de `local.lambdas` échoue au plan avec `Invalid index` : la faute de frappe est vue avant tout déploiement.
- Usage : ✅ une option activée pour certaines entrées (planification, alarme, URL publique) · ❌ un attribut booléen `scheduled = true` filtré par `if` partout : une map dédiée se lit d'un coup d'œil.

```hcl
# Exemple 1 : sous-ensemble relié par clé
locals {
  lambdas = {
    ingest-bodacc = { timeout = 300 }
    publish       = { timeout = 60 }
  }
  schedules = { ingest-bodacc = {} }
}
output "noms" {
  value = [for k, v in local.schedules :
    "${k}:${local.lambdas[k].timeout}"]
}
# → ["ingest-bodacc:300"]
```

- Quiz : `local.schedules = { ingest-bodaac = {} }` (faute de frappe) : que dit `terraform plan` sur `module.lambda[each.key]` ?
- [ ] Rien : la planification est ignorée
- [ ] Il crée une Lambda `ingest-bodaac`
- [x] `Error: Invalid index`
- [ ] Un avertissement, puis il continue
- Réponse : `Invalid index` (mesuré sur une map de locals, même message) : la clé n'existe pas dans la map des instances, le plan s'arrête.

## 31. cycle : sortir la politique de la ressource
- Sous-thème : blocs
- Niveau : 3
- Définition : Terraform refuse deux ressources qui se référencent mutuellement (`Error: Cycle`) ; on casse la boucle en sortant l'attribut fautif dans une ressource à part.
- Contexte : La distribution lit le domaine du bucket ; la politique du bucket cite l'ARN de la distribution (`AWS:SourceArn`). Écrite dans `aws_s3_bucket` (`policy = …`), elle crée un cycle (mesuré, provider AWS 6.70). En `aws_s3_bucket_policy`, l'ordre devient bucket → distribution → politique. `depends_on` ne sert ensuite qu'aux liens invisibles : le blocage d'accès public avant la politique.
- Usage : ✅ attribut qui dépend d'une ressource qui dépend de vous : ressource dédiée · ❌ `depends_on` pour « forcer l'ordre » d'un cycle : il ajoute une arête, il n'en retire aucune.

```hcl
# Exemple 1 : l'ordre sans cycle
resource "aws_s3_bucket" "site" {
  bucket = "revision-pwa-dev-site"
}
# distribution : domain_name =
#   aws_s3_bucket.site
#   .bucket_regional_domain_name
resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  # cite l'ARN de la distribution
  policy = local.policy_json
  depends_on = [
    aws_s3_bucket_public_access_block.site,
  ]
}
```

```hcl
# Exemple 2 : le cycle, réduit
resource "terraform_data" "bucket" {
  input = terraform_data.cdn.id
}
resource "terraform_data" "cdn" {
  input = terraform_data.bucket.output
}
# → Error: Cycle: terraform_data.cdn,
#   terraform_data.bucket
```

- Quiz : Quelle commande signale ce cycle en premier ?
- [ ] `terraform plan`, en lisant l'état
- [x] `terraform validate`, sans appel à AWS
- [ ] `terraform apply`, à la création
- [ ] Aucune : il crée les deux en deux passes
- Réponse : `terraform validate` (mesuré, Terraform 1.14) : le graphe des références est construit hors ligne ; un cycle bloque avant tout appel à AWS.

## 32. dynamic : zéro ou un bloc
- Sous-thème : boucles
- Niveau : 3
- Source : data-platform · S1-04
- Définition : `dynamic` avec un `for_each` qui vaut `[]` ou `[valeur]` produit zéro ou un bloc imbriqué : le bloc conditionnel de HCL (≈ `{cond && <Rule/>}`).
- Contexte : Un bloc imbriqué (`rule`, `expiration`) n'accepte ni `count` ni condition : seul `dynamic` le rend facultatif. La liste vide ne génère rien, une liste d'un élément génère un bloc, et dans `content` l'itérateur prend le nom du bloc (`rule.value`). Dans data-platform, `raw` (90 j) et `logs` (30 j) reçoivent une règle d'expiration, les trois autres buckets non.
- Usage : ✅ bloc présent selon une map ou un booléen (expiration, logging, CORS) · ❌ ressource entière facultative : `count = cond ? 1 : 0` sur la ressource ; bloc toujours présent : l'écrire en clair.

```hcl
# Exemple 1 : 0 ou 1 bloc rule
# local.jours = { raw = 90 }
dynamic "rule" {
  # [] → aucun bloc ; [90] → un bloc
  for_each = try([local.jours[each.key]], [])
  content {
    id     = "expire-current"
    status = "Enabled"
    filter {}
    expiration { days = rule.value }
  }
}
# raw  → un bloc, days = 90
# logs → aucun bloc
```

```hcl
# Exemple 2 : la liste, dans la console
# $ terraform console
# > try([local.jours["raw"]], [])
# [90]
# > try([local.jours["logs"]], [])
# []
```

- Quiz : Avec `for_each = cond ? [] : [1]` et `days = rule.value`, au bout de combien de jours l'objet expire-t-il ?
- [ ] 90 : la valeur de la map
- [x] 1
- [ ] 0 : `rule.value` est l'index
- [ ] Aucun : `Error: Unsupported attribute`
- Réponse : 1 : `rule.value` est l'élément de la liste, ici `1` ; mesuré au `plan` (`days = 1`), `raw` expirerait en un jour.

## 33. try : ne rattrape pas un data source
- Sous-thème : expressions
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `try()` rattrape une erreur d'expression (champ absent, JSON invalide), jamais l'échec de lecture d'un data source : un pointeur absent fait toujours échouer le plan.
- Contexte : L'erreur de lecture vient du provider, pendant la lecture du data source, avant toute évaluation d'expression : ni `try`, ni `can`, ni `lookup` ne la voient. Pour qu'une Lambda soit facultative, il faut qu'aucune instance de son data source n'existe, en agissant sur la map du `for_each`. `try` sert pour ce qui suit la lecture : `body` vide, champ manquant.
- Usage : ✅ `try` sur un champ facultatif du JSON lu · ❌ `try` autour d'un data source pour tolérer un objet absent : la lecture échoue avant.

```hcl
# Exemple 1 : terraform console
try(jsondecode("").key, "absent")
# → "absent" : erreur d'expression
# try(jsondecode(data.aws_s3_object
#   .p["x"].body).key, "absent")
# objet absent → le plan échoue
#   quand même, à la lecture
```

- Quiz : `local.lambdas` est filtré par `{ for k, v in local.lambdas : k => v if v.enabled }` et `enabled = false` pour la Lambda non publiée : le plan passe-t-il ?
- [ ] Non : le pointeur est quand même lu
- [x] Oui : aucune instance, aucune lecture
- [ ] Oui, avec un avertissement
- [ ] Non : `for_each` refuse un filtre
- Réponse : oui : le filtre retire la clé avant le `for_each`, donc l'instance du data source n'existe pas et rien n'est lu.

## 34. data source : son résultat dans l'état
- Sous-thème : blocs
- Niveau : 3
- Source : data-platform · S1-07
- Définition : Les attributs lus par un data source sont écrits dans l'état : le `body` du pointeur figure en clair dans `terraform.tfstate`.
- Contexte : Terraform garde la dernière lecture pour calculer et afficher le plan. Sans danger pour un pointeur (clé, hash, commit), dangereux pour un secret : le lire par `aws_s3_object` ou `aws_secretsmanager_secret_version` le recopie dans l'état. Depuis Terraform 1.10, une ressource `ephemeral` lit une valeur sans l'écrire dans l'état, mais seulement pour des arguments eux aussi éphémères.
- Usage : ✅ lire par data source des métadonnées sans valeur secrète · ❌ lire un secret pour le passer à une ressource : le code le lit à l'exécution (Secrets Manager, SSM).

```bash
# Exemple 1 : la lecture est dans l'état
terraform -chdir=infra state show \
  'data.aws_s3_object.lambda_pointer["ingest-bodacc"]' \
  | grep content_type
# → content_type = "application/json"
# body = "{ \"key\": …, \"git_commit\": … }"
```

- Quiz : Le token INSEE est lu par `data "aws_secretsmanager_secret_version"` et posé en variable d'environnement de la Lambda : où apparaît-il en clair ?
- [ ] Nulle part : Secrets Manager le chiffre
- [ ] Seulement dans la console Lambda
- [x] Dans l'état et dans la config de la fonction
- [ ] Seulement dans les logs du plan
- Réponse : dans l'état (lecture du data source et attribut `environment` de la fonction) et dans la configuration Lambda, visible par tout lecteur de la fonction ; le code doit lire le secret lui-même.
