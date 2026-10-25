---
title: "Cartes · State et backend Terraform"
type: cartes
langage: Terraform
cours: State et backend
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · State et backend Terraform
Terraform · State et backend : backend, bucket, garde-fous, principe, state (format spec v3 de revision-pwa).

## 1. bootstrap : l'œuf et la poule
- Sous-thème : principe
- Niveau : 1
- Définition : Un root Terraform `bootstrap` séparé crée le bucket S3 d'état avant le root principal, qui y range ensuite le sien.
- Contexte : Le backend S3 doit exister dès le `terraform init` : un root ne peut pas créer le bucket qui contient son propre état. On isole donc 4 ressources quasi immuables (bucket, versioning, chiffrement, accès public) dans `infra/bootstrap/`, appliqué une fois par compte, à la main. Le root `infra/` ne fait ensuite que pointer vers ce bucket via `backend.hcl`. Chaque dépôt a son bucket : data-platform et revision-pwa ne partagent pas d'état.
- Usage : ✅ premier déploiement d'un dépôt sur un compte AWS, nouveau compte de dev · ❌ y ajouter d'autres ressources (clé KMS, IAM du projet) : elles vont dans `infra/`.

```bash
# Exemple 1 : l'ordre, une fois par compte
# 1. root bootstrap : crée le bucket
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap apply
# → data-platform-tfstate-<id>
# 2. root infra/ : état dans ce bucket
make tf-init ENV=dev
make plan ENV=dev
```

```bash
# Exemple 2 : deux roots, deux états
# infra/
# ├── bootstrap/      état LOCAL
# │   ├── main.tf     bucket + 3 réglages
# │   └── terraform.tfstate  (gitignoré)
# ├── backend.tf      backend "s3" partiel
# └── envs/dev/backend.hcl  → le bucket
```

- Quiz : Sur un compte neuf, `make tf-init ENV=dev` est lancé avant le bootstrap : que se passe-t-il ?
- [ ] Terraform crée le bucket manquant
- [ ] L'état reste en local en attendant
- [x] `init` échoue : le bucket n'existe pas
- [ ] `init` passe, `plan` échoue ensuite
- Réponse : `init` échoue : le backend S3 ne crée jamais son bucket, il le lit dès l'initialisation (erreur « S3 bucket does not exist »).

## 2. état : ce que contient terraform.tfstate
- Sous-thème : state
- Niveau : 1
- Définition : L'état est un fichier JSON qui relie chaque bloc `resource` à l'objet réel (id, attributs) ; `plan` compare code, état et réalité.
- Contexte : Sans état, Terraform ne saurait pas quel bucket AWS correspond à `aws_s3_bucket.tfstate` : il voudrait tout recréer. L'état garde tous les attributs lus, et on ne l'édite jamais à la main : `terraform state list`, `state show` et `import` le manipulent. Le perdre ne détruit rien sur AWS, mais Terraform ne gère plus ces ressources. Sans bloc `backend`, il est écrit en local, dans `terraform.tfstate` du root.
- Usage : ✅ `state list` pour savoir ce qu'un root gère, `state show` pour lire un attribut · ❌ éditer le JSON ou le commiter : gitignoré, ou dans un bucket privé et chiffré.

```bash
# Exemple 1 : ce que gère le root
terraform -chdir=infra/bootstrap \
  state list
# → data.aws_caller_identity.current
#   aws_s3_bucket.tfstate
#   aws_s3_bucket_public_access_block.tfstate
#   aws_s3_bucket_server_side_encryption_configuration.tfstate
#   aws_s3_bucket_versioning.tfstate
```

```bash
# Exemple 2 : lire un attribut
terraform -chdir=infra/bootstrap \
  state show aws_s3_bucket.tfstate \
  | grep -E '^ +(bucket|region) '
# → bucket = "data-platform-tfstate-<id>"
#   region = "eu-west-3"
```

- Quiz : Une variable `sensitive = true` passée à une ressource apparaît-elle dans `terraform.tfstate` ?
- [ ] Non : elle est retirée de l'état
- [ ] Oui, chiffrée par Terraform
- [x] Oui, en clair
- [ ] Oui, remplacée par `(sensitive value)`
- Réponse : oui, en clair : `sensitive` ne masque que l'affichage du plan et des sorties ; d'où un état gitignoré, ou dans un bucket privé et chiffré.

## 3. bucket : un nom unique au monde
- Sous-thème : bucket
- Niveau : 1
- Définition : Un nom de bucket S3 est unique dans toute la partition AWS, tous comptes confondus : on y ajoute l'account id lu par `aws_caller_identity`.
- Contexte : Les noms de bucket forment un espace global : si un autre compte a déjà pris `data-platform-tfstate`, `apply` échoue avec `BucketAlreadyExists`. Le suffixe account id rend le nom propre au compte, sans le taper : la data source `aws_caller_identity` le lit depuis les credentials. Règles S3 : 3 à 63 caractères, minuscules, chiffres, points et tirets.
- Usage : ✅ tout bucket créé par Terraform (état, contenu, logs), préfixé par le projet · ❌ un nom en dur copié d'un autre compte ou d'un tutoriel : collision probable.

```hcl
# Exemple 1 : suffixe account id
# local.bucket → "data-platform-tfstate-<id>"
data "aws_caller_identity" "current" {}
locals {
  id     = data.aws_caller_identity.current.account_id
  bucket = "data-platform-tfstate-${local.id}"
}
```

```hcl
# Exemple 2 : vérifier dans la console
# $ terraform console
# > local.bucket
# "data-platform-tfstate-<id>"
# > length(local.bucket)
# 34   (au-delà de 63 : validate échoue)
```

- Quiz : Avec `bucket = "Data-Platform-tfstate"` (majuscules), à quelle étape Terraform échoue-t-il ?
- [ ] `terraform validate`
- [ ] `terraform plan`
- [ ] Jamais : S3 passe le nom en minuscules
- [x] `terraform apply`, refusé par AWS
- Réponse : `apply` : le provider ne vérifie que la longueur, `validate` et `plan` passent ; c'est l'API S3 qui rejette le nom (`InvalidBucketName`).

## 4. versioning : garder chaque version de l'état
- Sous-thème : bucket
- Niveau : 1
- Définition : Le versioning S3 garde chaque version écrite d'un objet : chaque `apply` crée une nouvelle version de l'état, les anciennes restent récupérables.
- Contexte : Un état écrasé ou abîmé (mauvaise `key`, `state rm` de trop) se restaure en relisant une version précédente. Depuis le provider AWS v4, le versioning est une ressource à part, `aws_s3_bucket_versioning`, et non plus un bloc de `aws_s3_bucket`. Une fois activé, il ne se désactive plus : on peut seulement le suspendre, et les versions déjà écrites restent.
- Usage : ✅ tout bucket d'état Terraform, données brutes qu'on ne veut pas perdre · ❌ fichiers temporaires très réécrits : chaque version est facturée, prévoir une règle de cycle de vie.

```hcl
# Exemple 1 : activer le versioning
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

```bash
# Exemple 2 : retrouver les versions
aws s3api list-object-versions \
  --bucket "$B" --prefix dev/ \
  --query 'Versions[].LastModified'
# → une date par apply
```

- Quiz : `terraform destroy` d'un bucket versionné qui contient des états, sans `force_destroy` : résultat ?
- [ ] Le bucket et ses versions sont supprimés
- [x] Échec `BucketNotEmpty`
- [ ] Seule la dernière version est supprimée
- [ ] Le versioning passe en `Suspended`
- Réponse : `BucketNotEmpty` : S3 refuse de supprimer un bucket qui contient des objets ou des versions ; `force_destroy = true` les viderait (à éviter pour un état).

## 5. chiffrement : SSE-S3 sans KMS
- Sous-thème : bucket
- Niveau : 1
- Définition : `sse_algorithm = "AES256"` (SSE-S3) chiffre chaque objet au repos avec des clés gérées par S3, sans clé KMS à créer ni autoriser.
- Contexte : Depuis janvier 2023, S3 chiffre déjà tout nouvel objet en SSE-S3 par défaut ; le déclarer rend la règle explicite et visible au `plan`. Avec `aws:kms`, chaque lecteur de l'état devrait aussi avoir `kms:Decrypt`. Surtout, la clé KMS du projet est créée par le root `infra/`, donc par l'état que ce bucket stocke : dépendance circulaire.
- Usage : ✅ bucket d'état, tout bucket de bootstrap qui doit exister avant le reste · ❌ données soumises à un audit des accès aux clés : `aws:kms` avec une clé dédiée.

```hcl
# Exemple 1 : chiffrement par défaut
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

```bash
# Exemple 2 : l'état est bien chiffré
aws s3api head-object --bucket "$B" \
  --key dev/terraform.tfstate \
  --query ServerSideEncryption
# → "AES256"
```

- Quiz : Que fait `encrypt = true` dans le bloc `backend "s3"` ?
- [x] Demande à S3 de chiffrer l'état côté serveur
- [ ] Chiffre l'état sur le poste avant l'envoi
- [ ] Chiffre seulement les valeurs `sensitive`
- [ ] Impose HTTPS entre Terraform et S3
- Réponse : chiffrement côté serveur : Terraform demande à S3 de chiffrer l'objet d'état au repos ; le fichier reste du JSON lisible pour qui peut le télécharger.

## 6. backend : configuration partielle
- Sous-thème : backend
- Niveau : 1
- Définition : Un bloc `backend "s3"` presque vide se complète à l'`init` par `-backend-config=fichier.hcl` : un seul code, une config d'état par environnement.
- Contexte : On garde dans `backend.tf` ce qui ne change jamais (`encrypt = true`) ; bucket, key, région, profil et verrou viennent de `envs/<env>/backend.hcl`, gitignoré car il contient l'account id (un `.example` sert de modèle). `-backend-config` accepte aussi `clé=valeur` en ligne de commande. Les valeurs finales sont mémorisées dans `.terraform/` jusqu'au prochain `init`.
- Usage : ✅ même code pour dev et prod, rien de propre au compte dans git · ❌ bucket et key en dur dans `backend.tf` : un seul environnement possible, account id commité.

```hcl
# Exemple 1 : bloc partiel + fichier
terraform {
  backend "s3" {
    encrypt = true   # ce qui est fixe
  }
}
# envs/dev/backend.hcl : le reste
bucket       = "data-platform-tfstate-<id>"
region       = "eu-west-3"
key          = "dev/terraform.tfstate"
use_lockfile = true
```

```bash
# Exemple 2 : compléter à l'init
terraform -chdir=infra init \
  -backend-config=envs/dev/backend.hcl
# ou valeur par valeur :
terraform -chdir=infra init \
  -backend-config="key=dev/terraform.tfstate"
```

- Quiz : La ligne `key` manque dans `backend.hcl` : que fait `make tf-init`, qui passe `-input=false` ?
- [ ] Il prend `terraform.tfstate` par défaut
- [x] `Error: Missing Required Value`
- [ ] Il demande la valeur, puis continue
- [ ] Il écrit l'état à la racine du bucket
- Réponse : `Missing Required Value` (`"key" is required`) : le backend S3 exige `bucket` et `key` ; sans `-input=false`, `init` demanderait la valeur au clavier.

## 7. backend : une clé d'état par environnement
- Sous-thème : backend
- Niveau : 1
- Définition : `key` est le chemin de l'état dans le bucket : un bucket d'état par dépôt, une clé par environnement.
- Contexte : Dev et prod partagent le bucket mais pas l'état : chaque `backend.hcl` porte sa propre `key`. Le verrou se pose à côté (`dev/terraform.tfstate.tflock`), donc un `apply` en dev ne bloque pas la prod. Le préfixe est libre : S3 n'a pas de vrais dossiers, `dev/` n'est qu'un début de nom d'objet, créé à la première écriture.
- Usage : ✅ préfixe = nom de l'environnement, recopié depuis `backend.hcl.example` · ❌ un bucket d'état par environnement sur le même compte : plus de bootstrap pour rien.

```hcl
# Exemple 1 : même bucket, deux clés
# envs/dev/backend.hcl
key = "dev/terraform.tfstate"

# envs/prod/backend.hcl
key = "prod/terraform.tfstate"
```

```bash
# Exemple 2 : le contenu du bucket
aws s3 ls "s3://$B" --recursive
# → dev/terraform.tfstate
#   prod/terraform.tfstate
```

- Quiz : `envs/prod/backend.hcl` a gardé `key = "dev/terraform.tfstate"` : que propose `make plan ENV=prod` ?
- [ ] De créer toutes les ressources de prod
- [ ] Rien : `No changes.`
- [ ] Une erreur : clé déjà utilisée
- [x] De modifier ou remplacer celles de dev
- Réponse : de toucher à dev : même clé = même état ; Terraform compare le code de prod aux ressources de dev et veut les renommer, donc les remplacer.

## 8. accès public : tout bloquer
- Sous-thème : bucket
- Niveau : 2
- Définition : `aws_s3_bucket_public_access_block` interdit tout accès public au bucket, quelles que soient ses ACL ou sa politique.
- Contexte : Les 4 options couvrent deux portes. Les ACL : `block_public_acls` refuse d'en poser une publique, `ignore_public_acls` neutralise celles qui existent. La politique : `block_public_policy` refuse une politique publique, `restrict_public_buckets` coupe l'accès anonyme d'un bucket déjà public. Un état Terraform contient des secrets en clair : aucune fuite tolérée.
- Usage : ✅ tout bucket privé : état, données brutes, site servi par CloudFront avec OAC · ❌ ouvrir le bucket pour un site statique : CloudFront + OAC à la place.

```hcl
# Exemple 1 : les 4 verrous
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

```bash
# Exemple 2 : vérifier sur AWS
aws s3api get-public-access-block \
  --bucket "$B"
# → 4 options à true
```

- Quiz : Avec `block_public_policy = true`, la politique OAC de CloudFront (limitée par `AWS:SourceArn`) est-elle refusée ?
- [x] Non : elle n'est pas « publique »
- [ ] Oui : tout principal externe est bloqué
- [ ] Oui, sauf si `restrict_public_buckets = false`
- [ ] Non, seulement si le bucket a une ACL privée
- Réponse : non : un principal de service restreint à un ARN précis n'est pas public ; seul un `Principal: "*"` sans condition restrictive est bloqué.

## 9. backend : ni variable ni local
- Sous-thème : backend
- Niveau : 2
- Définition : Le bloc `backend` est lu avant les variables : il n'accepte que des valeurs littérales, jamais `var.` ni `local.`.
- Contexte : Terraform configure le backend dès `init`, avant d'évaluer le reste du code, pour savoir où lire l'état : aucune expression n'est encore disponible. Venant de TS, on voudrait un template `"${var.env}/…"` : refusé avec `Variables not allowed`. La valeur propre à l'environnement passe par `-backend-config` (fichier ou `clé=valeur`), et le Makefile choisit le fichier avec `ENV`.
- Usage : ✅ `-backend-config=envs/$(ENV)/backend.hcl` depuis le Makefile · ❌ générer `backend.tf` par script (`sed`) avant `init` : fragile, un `backend.hcl` par environnement suffit.

```hcl
# Exemple 1 : refusé dès init
terraform {
  backend "s3" {
    # → Error: Variables not allowed
    key = "${var.env}/terraform.tfstate"
  }
}
variable "env" {
  default = "dev"
}
```

```bash
# Exemple 2 : la valeur vient de l'init
ENV=prod
terraform -chdir=infra init \
  -backend-config="envs/$ENV/backend.hcl" \
  -reconfigure
```

- Quiz : Avec `locals { key = "dev/terraform.tfstate" }` puis `key = local.key` dans le backend, que fait `init` ?
- [ ] Accepté : une `local` constante est connue
- [x] `Error: Variables not allowed`
- [ ] Accepté, mais seulement avec `-reconfigure`
- [ ] `Error: Unsupported attribute`
- Réponse : `Variables not allowed` : même une `local` littérale est une expression, évaluée après le backend ; seul un littéral passe.

## 10. init -reconfigure : changer d'environnement
- Sous-thème : backend
- Niveau : 2
- Définition : `init -reconfigure` réinitialise le backend avec une nouvelle configuration sans copier l'état : indispensable pour passer d'un environnement à l'autre.
- Contexte : `init` mémorise la config du backend dans `.terraform/terraform.tfstate`, un fichier local qui n'est pas l'état. Si `-backend-config` change, Terraform refuse de deviner : soit on oublie l'ancienne config (`-reconfigure`), soit on copie l'état de l'ancien emplacement vers le nouveau (`-migrate-state`). Changer d'environnement, c'est le premier cas : chaque environnement a déjà son état.
- Usage : ✅ `make tf-init ENV=…` à chaque changement d'environnement · ❌ `-migrate-state` pour basculer de dev à prod : copierait l'état de dev dans la clé de prod.

```makefile
# Exemple 1 : la cible tf-init
ENV     ?= dev
TF       = terraform -chdir=infra
ENV_DIR  = envs/$(ENV)

tf-init:
	$(TF) init -input=false \
	  -backend-config=$(ENV_DIR)/backend.hcl \
	  -reconfigure
```

- Quiz : Sans `-reconfigure`, que fait `make tf-init ENV=prod` juste après un `init` en dev ?
- [ ] Bascule sur l'état de prod
- [ ] Copie l'état de dev vers prod
- [ ] Reste sur l'état de dev, sans erreur
- [x] `Error: Backend configuration changed`
- Réponse : `Backend configuration changed` : Terraform exige de choisir entre `-reconfigure` (oublier l'ancienne config) et `-migrate-state` (copier l'état).

## 11. init -backend=false : valider hors AWS
- Sous-thème : backend
- Niveau : 2
- Source : revision-pwa · pwa-revision
- Définition : `terraform init -backend=false` installe providers et modules sans configurer le backend : `validate` tourne ensuite sans identifiants ni état.
- Contexte : Un `init` normal lit `backend.hcl`, contacte le bucket d'état et demande région et identifiants. Pour vérifier syntaxe, types et références (cycles compris), le backend est inutile : `validate` ne lit ni l'état ni AWS. C'est le premier contrôle, en local comme en CI, avant `plan` qui a besoin des deux.
- Usage : ✅ étape `validate` d'une CI, contrôle avant commit, dossier copié pour un test · ❌ avant `plan` ou `apply` : il faut un `init` complet, avec le backend.

```bash
# Exemple 1 : mesuré, sans identifiants
terraform init -backend=false
terraform validate
# → Success! The configuration
#   is valid.
terraform init   # backend "s3" {}
# → Error: The "region" attribute
#   or AWS_REGION must be set.
```

- Quiz : Après `init -backend=false`, que fait `terraform plan` ?
- [ ] Planifie avec un état local vide
- [ ] Planifie contre l'état S3, en lecture seule
- [x] Échoue : « Backend initialization required »
- [ ] Planifie sans rafraîchir les ressources
- Réponse : il échoue (mesuré) : le bloc `backend "s3"` exige un `init` complet ; Terraform refuse plutôt que de planifier contre un état vide, qui recréerait tout.

## 12. terraform_remote_state : lire les outputs d'un autre root
- Sous-thème : state
- Niveau : 2
- Définition : La data source `terraform_remote_state` lit les `output` de l'état d'un autre root (bootstrap, réseau), sans gérer ses ressources.
- Contexte : Seuls les outputs racine sont exposés, sous `.outputs` : les ressources de l'autre état restent invisibles. Mais il faut le droit de lire tout le fichier d'état (`s3:GetObject`), secrets compris. Le lien est aussi implicite : renommer un output casse le lecteur au `plan`. data-platform préfère reporter les sorties du bootstrap à la main dans `backend.hcl`.
- Usage : ✅ root qui consomme un socle partagé (VPC, zone DNS) dans le même compte · ❌ donner l'accès à un état contenant des secrets : un paramètre SSM, ou une data source sur la ressource elle-même.

```hcl
# Exemple 1 : lire l'état du bootstrap
data "terraform_remote_state" "boot" {
  backend = "local"
  config = {
    path = "bootstrap/terraform.tfstate"
  }
}
output "b" {
  value = data.terraform_remote_state.boot.outputs.bucket
}
# → b = "data-platform-tfstate-123"
```

```hcl
# Exemple 2 : un état sur S3
data "terraform_remote_state" "net" {
  backend = "s3"
  config = {
    bucket = "data-platform-tfstate-<id>"
    key    = "dev/terraform.tfstate"
    region = "eu-west-3"
  }
}
```

- Quiz : Que donne `data.terraform_remote_state.boot.bucket`, sans `.outputs` ?
- [ ] `"data-platform-tfstate-123"`
- [ ] `null` : l'attribut est facultatif
- [x] `Error: Unsupported attribute`
- [ ] L'ARN du bucket, lu dans l'état
- Réponse : `Unsupported attribute` (mesuré) : les outputs ne sont accessibles que sous l'attribut `outputs` de la data source.

## 13. state pull : sauvegarder avant d'opérer
- Sous-thème : state
- Niveau : 2
- Définition : `terraform state pull` affiche l'état courant en JSON, quel que soit le backend : la sauvegarde à faire avant toute commande `state`.
- Contexte : Avec un backend S3, aucun `terraform.tfstate` n'existe sur le poste : `pull` le télécharge. On garde la copie hors du dépôt avant un `state mv`, un `state rm` ou un `import`. `state push` la renverrait, mais refuse un état plus ancien (`serial` plus petit) ou d'une autre lignée (`lineage`) : `-force` passe outre, en écrasant tout ce qui a changé depuis.
- Usage : ✅ copie avant une opération sur l'état, lecture avec `jq` · ❌ `state push -force` d'une vieille copie : le versioning du bucket est la vraie restauration.

```bash
# Exemple 1 : copier, puis lire
terraform state pull > /tmp/dev.tfstate
jq -c '{serial, n: (.resources|length)}' \
  /tmp/dev.tfstate
# → {"serial":1,"n":1}
```

- Quiz : Après un nouvel `apply`, tu lances `terraform state push /tmp/dev.tfstate` (la copie d'avant) : résultat ?
- [ ] L'état est restauré tel quel
- [x] Refusé : `serial` plus ancien
- [ ] Fusionné avec l'état courant
- [ ] Accepté, avec une confirmation `yes`
- Réponse : refusé (`cannot import state with serial 1 over newer state`, mesuré) : `push` protège les écritures récentes ; seul `-force` écraserait.

## 14. workspace : plusieurs états, un seul backend
- Sous-thème : backend
- Niveau : 2
- Définition : `terraform workspace new prod` crée un état séparé sous le même backend ; `terraform.workspace` donne son nom dans le code.
- Contexte : En local, l'état d'un workspace va dans `terraform.tfstate.d/<nom>/` ; en S3, sous `env:/<nom>/<key>` (doc). Le workspace choisi est mémorisé dans `.terraform/environment` : rien dans le code ni dans la commande ne le montre, d'où des `apply` sur le mauvais environnement. data-platform choisit une `key` par env, explicite dans `backend.hcl`, et `ENV=` dans le Makefile.
- Usage : ✅ copies jetables d'un même env (une branche, un test) · ❌ séparer dev et prod : même backend, mêmes droits, environnement invisible ; une `key` ou un compte par env.

```bash
# Exemple 1 : un état par workspace
terraform workspace new prod
# → Created and switched to
#   workspace "prod"!
terraform apply -auto-approve
# → n = "data-platform-prod-raw"
find . -name '*.tfstate'
# → ./terraform.tfstate.d/prod/
#   terraform.tfstate
```

- Quiz : Juste après, `terraform workspace select default` puis `plan` : que propose-t-il ?
- [ ] `No changes.` : même code, même infra
- [ ] De renommer `prod` en `default`
- [x] De tout créer : `1 to add`
- [ ] De détruire les ressources de `prod`
- Réponse : de tout créer (mesuré) : `default` a son propre état, vide ; les ressources de `prod` lui sont invisibles.

## 15. moved : renommer sans recréer
- Sous-thème : state
- Niveau : 3
- Définition : Un bloc `moved` déclare qu'une adresse a changé (`from` → `to`) : Terraform déplace l'objet dans le state au lieu de le recréer.
- Contexte : Renommer un label, passer à `for_each` ou ranger une ressource dans un module change son adresse ; sans `moved`, le plan détruit puis recrée, ce qui vide un bucket de données. Le bloc est revu dans le plan (`has moved to`) et appliqué avec le reste. Après l'apply partout, il peut être retiré, ou gardé pour les autres envs pas encore à jour.
- Usage : ✅ refactoring d'adresses (renommage, entrée dans un module, `count` → `for_each`) · ❌ objet à ne plus gérer : `removed` ; objet existant hors state : `import`.

```hcl
# Exemple 1 : renommer raw en brut
resource "aws_s3_bucket" "brut" {
  bucket = "data-platform-dev-raw"
}
moved {
  from = aws_s3_bucket.raw
  to   = aws_s3_bucket.brut
}
# plan → raw has moved to brut
# Plan: 0 to add, 0 to change,
#       0 to destroy
```

```hcl
# Exemple 2 : entrée dans un module
moved {
  from = aws_s3_bucket.raw
  to   = module.s3.aws_s3_bucket.raw
}
```

- Quiz : Tu ajoutes `count = 1` à `aws_s3_bucket.raw` déjà créé, sans bloc `moved` : que prévoit `plan` ?
- [ ] Destroy de `raw`, create de `raw[0]`
- [x] `raw has moved to raw[0]`, rien à recréer
- [ ] `Error: Missing resource instance key`
- [ ] Un second bucket `raw[0]`
- Réponse : `raw has moved to raw[0]` : Terraform déduit seul ce déplacement entre l'adresse sans index et l'index `[0]`.

## 16. state rm : oublier sans détruire
- Sous-thème : state
- Niveau : 3
- Définition : `terraform state rm` retire une ressource du state sans la toucher dans AWS : Terraform cesse simplement de la gérer.
- Contexte : Utile pour confier une ressource à un autre state (autre dossier, bootstrap) ou pour la sortir de Terraform. La commande agit tout de suite sur le state partagé, sans plan relu : depuis Terraform 1.7, le bloc `removed` fait la même chose de façon déclarative, revue dans le plan et dans la MR.
- Usage : ✅ déplacer une ressource vers un autre state, abandonner sa gestion · ❌ la supprimer pour de vrai : retirer le bloc et `apply` ; renommer : `moved`.

```bash
# Exemple 1 : oublier le bucket
terraform state rm aws_s3_bucket.raw
# → Removed aws_s3_bucket.raw
# le bucket existe toujours dans AWS
```

```hcl
# Exemple 2 : la version déclarative
removed {
  from = aws_s3_bucket.raw
  lifecycle {
    destroy = false
  }
}
# plan → will no longer be managed
#        by Terraform, but will not
#        be destroyed
```

- Quiz : Après `state rm`, la config contient toujours `aws_s3_bucket.raw` : que prévoit le `plan` suivant ?
- [x] `aws_s3_bucket.raw will be created`
- [ ] `No changes`
- [ ] `aws_s3_bucket.raw will be destroyed`
- [ ] `aws_s3_bucket.raw will be imported`
- Réponse : `will be created` : Terraform ne connaît plus le bucket ; l'apply échouera car le nom existe déjà dans AWS (`import` pour le reprendre).

## 17. verrou : use_lockfile natif S3
- Sous-thème : backend
- Niveau : 3
- Définition : `use_lockfile = true` pose un objet `<key>.tflock` à côté de l'état pendant `plan` et `apply`, pour qu'une seule exécution l'écrive à la fois.
- Contexte : Avant Terraform 1.10, le verrou S3 exigeait une table DynamoDB (`dynamodb_table`, désormais dépréciée). Le lockfile natif s'appuie sur l'écriture conditionnelle de S3 : créer le `.tflock` échoue s'il existe déjà. D'où `required_version = ">= 1.10"`. Si un `apply` est tué net, le verrou peut rester : `force-unlock` le retire, après avoir vérifié que personne ne tourne.
- Usage : ✅ tout backend S3 partagé (poste et CI) · ❌ `-lock=false` pour « débloquer » : deux écritures concurrentes corrompent l'état ; `force-unlock` à la place.

```bash
# Exemple 1 : le verrou pendant un apply
# terminal 1
make up ENV=dev
# terminal 2, pendant l'apply
aws s3 ls "s3://$B/dev/"
# → terraform.tfstate
#   terraform.tfstate.tflock
```

```bash
# Exemple 2 : verrou resté après un crash
terraform -chdir=infra \
  force-unlock <LOCK_ID>
# LOCK_ID : affiché dans l'erreur
```

- Quiz : Un `make plan ENV=dev` lancé pendant un `apply` en cours sur dev : que fait-il ?
- [ ] Il attend la fin de l'apply
- [x] Il échoue tout de suite : verrou pris
- [ ] Il passe : `plan` ne verrouille pas
- [ ] Il lit l'ancien état et continue
- Réponse : il échoue (`Error acquiring the state lock`) : `plan` verrouille aussi, et l'attente par défaut est nulle ; `-lock-timeout=60s` attendrait.

## 18. prevent_destroy : ce qu'il protège
- Sous-thème : garde-fous
- Niveau : 3
- Définition : `lifecycle { prevent_destroy = true }` fait échouer tout plan qui détruirait la ressource, `destroy` compris.
- Contexte : Le contrôle porte sur le plan, pas sur la commande : tout ce qui finit en suppression est bloqué, y compris un remplacement (`-/+`) causé par un argument qui force la recréation, comme le nom d'un bucket. Il ne protège pas d'une suppression faite dans la console AWS ou en CLI : c'est une règle Terraform, pas une protection AWS. AWS refuse en plus de supprimer un bucket non vide sans `force_destroy`.
- Usage : ✅ bucket d'état, buckets de données de prod, clé KMS, toute ressource dont la perte est irréversible · ❌ ressources jetables de dev, recréées souvent : bloquerait `make down`.

```hcl
# Exemple 1 : destroy refusé
# terraform destroy
# → Error: Instance cannot be destroyed
resource "aws_s3_bucket" "tfstate" {
  bucket = local.bucket
  lifecycle {
    prevent_destroy = true
  }
}
```

```hcl
# Exemple 2 : un renommage aussi
resource "aws_s3_bucket" "tfstate" {
  # ancien : data-platform-tfstate-<id>
  bucket = "dp-state-${local.id}"
  lifecycle {
    prevent_destroy = true
  }
}
# plan → -/+ replace, donc
# → Error: Instance cannot be destroyed
```

- Quiz : Le bloc `resource "aws_s3_bucket" "tfstate"` est supprimé du code : que fait `terraform plan` ?
- [ ] `Error: Instance cannot be destroyed`
- [x] Il propose de détruire le bucket
- [ ] Il oublie le bucket sans le détruire
- [ ] `No changes.`
- Réponse : il propose la destruction, sans erreur : avec le bloc disparaît son `lifecycle` ; pour oublier sans détruire, un bloc `removed` avec `destroy = false`.

## 19. import : rattacher l'existant
- Sous-thème : state
- Niveau : 3
- Définition : `terraform import adresse id` rattache une ressource AWS existante à l'état sans la recréer : la parade à un état local perdu.
- Contexte : L'état du bootstrap est local : perdre le dossier (nouveau poste, `git clean`) laisse le bucket sur AWS, mais Terraform ne le connaît plus et `apply` tenterait de le recréer. `import` écrit l'état ressource par ressource : l'adresse vient du code, l'id dépend du type (le nom du bucket pour les 4 ressources). Depuis Terraform 1.5, un bloc `import { to, id }` fait la même chose au `plan`, relisible en revue.
- Usage : ✅ reprendre un bootstrap dont l'état est perdu, adopter une ressource créée à la main · ❌ ressource déjà gérée par un autre état : deux roots se la disputeraient.

```bash
# Exemple 1 : reconstruire l'état perdu
B=data-platform-tfstate-<id>
T="terraform -chdir=infra/bootstrap"
$T import aws_s3_bucket.tfstate "$B"
$T import \
  aws_s3_bucket_versioning.tfstate "$B"
# (+ chiffrement, accès public)
$T plan
# → No changes.
```

```hcl
# Exemple 2 : la version déclarative
import {
  to = aws_s3_bucket.tfstate
  id = "data-platform-tfstate-<id>"
}
# terraform plan
# → 1 to import, 0 to add
```

- Quiz : `terraform import aws_s3_bucket.tfstate <nom>`, sans ce bloc `resource` dans le code : résultat ?
- [ ] Terraform génère le bloc dans `main.tf`
- [ ] Import réussi, bloc à écrire ensuite
- [x] Erreur : adresse absente de la configuration
- [ ] L'état est écrit, puis `plan` veut détruire
- Réponse : erreur `resource address … does not exist in the configuration` : `import` remplit un bloc existant ; écrire le code d'abord, ou `plan -generate-config-out` avec un bloc `import`.

## 20. init -migrate-state : déplacer un état
- Sous-thème : backend
- Niveau : 3
- Définition : `init -migrate-state` copie l'état de l'ancien backend vers le nouveau, pour déplacer un état sans réimporter les ressources.
- Contexte : Cas typiques : un root démarré en état local qu'on passe sur S3, ou une `key` renommée. Terraform lit l'ancienne config dans `.terraform/`, la nouvelle dans le code et `-backend-config`, puis demande confirmation (`-force-copy` répond oui). Avant, `plan` doit dire `No changes.` ; après, sur le nouveau backend, aussi.
- Usage : ✅ changer de bucket ou de `key` pour un même environnement, passer du local au S3 · ❌ basculer d'un environnement à l'autre : `-reconfigure`.

```bash
# Exemple 1 : de l'état local vers S3
terraform -chdir=infra init \
  -backend-config=envs/dev/backend.hcl \
  -migrate-state -force-copy
# → Successfully configured
#   the backend "s3"!
terraform -chdir=infra plan
# → No changes.
```

- Quiz : `infra/` passe d'un état local à S3 par `-migrate-state` : que devient `terraform.tfstate` local ?
- [ ] Inchangé : la migration copie sans toucher la source
- [x] Vidé (0 octet), l'état complet part en `.backup`
- [ ] Supprimé, sans aucune copie locale
- [ ] Remplacé par un renvoi vers le bucket
- Réponse : vidé : Terraform efface l'état local migré mais laisse `terraform.tfstate.backup`, l'état complet en clair, à mettre à la corbeille ; entre deux backends (changement de `key`), la source reste intacte (mesuré, Terraform 1.14).

## 21. state mv : déplacer tout de suite
- Sous-thème : state
- Niveau : 3
- Définition : `terraform state mv A B` change l'adresse d'un objet dans l'état immédiatement, sans plan : la version impérative du bloc `moved`.
- Contexte : Elle écrit l'état partagé tout de suite, sans revue ni trace dans le dépôt, et ne touche pas le code : le renommage doit y être fait à la main, sinon le plan suivant détruit et recrée. `-dry-run` montre ce qui serait déplacé. En zsh, une adresse avec `["raw"]` se met entre apostrophes, sinon le shell la prend pour un motif (`no matches found`).
- Usage : ✅ correction ponctuelle sur un poste, état local du bootstrap · ❌ refactoring d'un root partagé : un bloc `moved`, relu en MR et appliqué partout.

```bash
# Exemple 1 : déplacer, puis vérifier
terraform state mv \
  terraform_data.raw terraform_data.brut
# → Successfully moved 1 object(s).
terraform state mv -dry-run \
  terraform_data.brut \
  'module.s3.terraform_data.this["raw"]'
# → Would move "terraform_data.brut"
#   to "module.s3.terraform_data
#   .this[\"raw\"]"
```

- Quiz : Après `state mv terraform_data.raw terraform_data.brut`, sans toucher au code : que prévoit `plan` ?
- [ ] `No changes.`
- [ ] `raw has moved to brut`
- [x] Détruire `brut`, créer `raw`
- [ ] Modifier `brut` en place
- Réponse : détruire `brut`, créer `raw` (mesuré) : le code déclare toujours `raw` ; l'état a bougé, pas la configuration.
