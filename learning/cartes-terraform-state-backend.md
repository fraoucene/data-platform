---
title: "Cartes · State et backend Terraform"
type: cartes
langage: Terraform
cours: State et backend
created: 2026-10-24
updated: 2026-10-25
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

## 8. couches : une ressource, sa durée de vie
- Sous-thème : principe
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Chaque ressource vit dans le root Terraform qui a sa durée de vie : bootstrap pour le compte, `infra/` pour l'environnement jetable.
- Contexte : La question n'est pas « à quoi ressemble la ressource » mais « quand doit-elle disparaître ». Un environnement de dev se détruit (`make down`) et se recrée (`make up`) : tout ce dont `make up` a besoin pour réussir doit lui survivre (état, zips publiés). Ces ressources vont dans `infra/bootstrap/`, appliqué une fois par compte. L'erreur de S1-04 : `artifacts` rangé avec les autres buckets parce qu'il leur ressemblait.
- Usage : ✅ avant chaque nouvelle ressource, se demander « survit-elle à `make down` ? » · ❌ ranger par type (tous les buckets ensemble) : on détruit ce qui sert à reconstruire.

```bash
# Exemple 1 : deux couches, deux rythmes
# infra/bootstrap/  une fois par compte
#   tfstate    état de infra/
#   artifacts  zips des Lambdas
# infra/            make up / make down
#   kms, raw, processed, out, logs
#   lambdas, rôles, log groups
make down    # détruit infra/ seul
make deploy  # repart des zips intacts
```

- Quiz : `artifacts` est resté dans `infra/` : après `make down`, que fait `make up` seul ?
- [ ] Il recrée les Lambdas depuis les zips
- [ ] Il recrée le bucket, puis les Lambdas sans code
- [x] Son `plan` échoue : pointeur introuvable
- [ ] Il recrée tout, zips compris
- Réponse : le `plan` échoue : le data source lit `current.json` dès le plan, dans un bucket détruit avec l'environnement ; aucun `apply` ne peut le recréer avant cette lecture.

## 9. bootstrap : ce qui y va
- Sous-thème : principe
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Le bootstrap porte ce que `make up` suppose déjà là : bucket d'état, bucket d'artefacts, plus tard dépôt ECR et rôle OIDC de la CI.
- Contexte : Critère : l'environnement en dépend, elle ne dépend pas de lui. Le bootstrap reste petit, appliqué à la main avec des droits élevés, rarement modifié : chaque ajout doit se justifier. Tout le reste (clé KMS du projet, buckets de données, Lambdas, rôles d'exécution) suit l'environnement et se recrée avec lui.
- Usage : ✅ état, artefacts, images ECR, rôle de déploiement de la CI et son fournisseur OIDC · ❌ données métier, clé KMS du projet, Lambdas : elles suivent l'environnement.

```hcl
# Exemple 1 : infra/bootstrap/
# main.tf       bucket d'état
# artifacts.tf  bucket des zips
# plus tard : ecr.tf, ci_oidc.tf
locals {
  artifacts_bucket = (
    "data-platform-artifacts-${local.account_id}"
  )
}
# → data-platform-artifacts-<account_id>
```

- Quiz : Le rôle OIDC de la CI est déclaré dans `infra/` : que peut encore faire la CI après un `make down` ?
- [ ] `make up`, le rôle se recrée au passage
- [ ] Tout : le rôle n'est pas détruit
- [x] Rien sur AWS : son rôle a disparu
- [ ] Seulement `make plan`, en lecture
- Réponse : rien sur AWS : `make down` a détruit le rôle qu'elle endosse ; seul un humain avec des droits admin peut refaire `make up`. D'où le rôle de la CI dans le bootstrap.

## 10. bucket d'artefacts : un par compte
- Sous-thème : principe
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Le bucket d'artefacts est nommé par compte (`data-platform-artifacts-<account_id>`), sans environnement : tous les environnements du compte lisent les mêmes zips.
- Contexte : Le bootstrap n'a pas de variable `environment` : il existe une fois par compte. Les zips étant rangés sous leur hash, dev et int du même compte partagent les octets sans conflit. Le suffixe `<account_id>` rend le nom unique au monde (espace de noms global de S3) et évite la collision avec le même projet sur un autre compte. `infra/` recalcule ce nom par la même convention.
- Usage : ✅ un bucket par compte, préfixe `lambdas/<nom>/` · ❌ un bucket par environnement : la promotion dev → int copierait les zips au lieu de les réutiliser.

```hcl
# Exemple 1 : infra/ retrouve le nom
data "aws_caller_identity" "current" {}

locals {
  artifacts_bucket = format(
    "data-platform-artifacts-%s",
    data.aws_caller_identity.current.account_id,
  )
}
# dev et int du même compte
# → même bucket, mêmes zips
```

- Quiz : dev et prod sont sur deux comptes AWS : combien de buckets d'artefacts, et la prod lit-elle ceux de dev ?
- [ ] Un, lisible par les deux comptes
- [x] Deux, cloisonnés sans politique de bucket
- [ ] Deux, lisibles l'un par l'autre
- [ ] Un, recopié dans chaque compte
- Réponse : deux, cloisonnés : un bootstrap par compte ; la prod ne lit le zip de dev que si une politique de bucket l'ouvre à son compte, sinon on copie le zip.

## 11. backend.hcl absent : Failed to read file
- Sous-thème : backend
- Niveau : 1
- Source : data-platform · S1-09
- Définition : Dans un clone neuf, `init -backend-config=envs/dev/backend.hcl` échoue : le fichier est gitignoré, il faut d'abord le créer depuis son `.example`.
- Contexte : Le backend partiel lit bucket, key, région et profil dans `backend.hcl`, qui contient le numéro de compte : il n'est jamais commité. Toute cible qui dépend de `tf-init` échoue donc, `make tf-validate` compris, avant même de lire le code. C'est l'un des implicites d'un README écrit depuis son poste : la doc de démarrage doit dire `cp backend.hcl.example backend.hcl` et quoi y remplir.
- Usage : ✅ étape écrite « créer `backend.hcl` » avant le premier `make plan` · ❌ en CI, un fichier : y passer `-backend-config="bucket=…"` depuis les variables protégées.

```bash
# Exemple 1 : mesuré dans un clone neuf
terraform -chdir=infra init \
  -backend-config=envs/dev/backend.hcl
# → Error: Failed to read file
#   The file "envs/dev/backend.hcl"
#   could not be read.
```

```bash
# Exemple 2 : le correctif documenté
cp infra/envs/dev/backend.hcl.example \
   infra/envs/dev/backend.hcl
# bucket = sortie du bootstrap :
terraform -chdir=infra/bootstrap \
  output -raw state_bucket
```

- Quiz : Dans ce clone neuf, quelle commande passe sans `backend.hcl` ?
- [ ] `make tf-validate`
- [ ] `make plan`
- [x] `terraform -chdir=infra init -backend=false`
- [ ] `terraform -chdir=infra init` sans option
- Réponse : `init -backend=false` : il installe providers et modules sans backend ; `make tf-validate` passe par `tf-init`, qui lit `backend.hcl` (mesuré : `Failed to read file`).

## 12. accès public : tout bloquer
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

## 13. backend : ni variable ni local
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

## 14. init -reconfigure : changer d'environnement
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

## 15. init -backend=false : valider hors AWS
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

## 16. terraform_remote_state : lire les outputs d'un autre root
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

## 17. state pull : sauvegarder avant d'opérer
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

## 18. workspace : plusieurs états, un seul backend
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

## 19. états séparés : destroy ne traverse pas
- Sous-thème : state
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `terraform destroy` ne détruit que les ressources de son propre état : un root séparé est hors de portée de `make down`, même sans `prevent_destroy`.
- Contexte : Terraform ne connaît d'AWS que ce que son état référence. Le bucket d'artefacts, dans l'état local du bootstrap, n'apparaît jamais dans le plan de `infra/`. C'est la vraie protection ; `prevent_destroy` n'est qu'une seconde ceinture contre un `destroy` lancé par erreur dans le bootstrap lui-même. Contrepartie : chaque root se planifie et s'applique à part, dans le bon ordre.
- Usage : ✅ isoler dans un autre root ce qui ne doit pas mourir avec l'environnement · ❌ compter sur `-target` ou `prevent_destroy` pour protéger une ressource partagée dans le même état.

```bash
# Exemple 1 : chaque root, son état
terraform -chdir=infra state list \
  | grep -c 'aws_s3_bucket.artifacts'
# → 0 : pas dans l'état de infra/
terraform -chdir=infra/bootstrap \
  state list | grep 'bucket.artifacts'
# → aws_s3_bucket.artifacts
```

- Quiz : Dans `infra/`, on ajoute `data "aws_s3_bucket" "artifacts"` qui lit ce bucket, puis `make down` : le bucket est-il détruit ?
- [ ] Oui : il est maintenant dans l'état
- [x] Non : un data source n'est jamais détruit
- [ ] Oui, sauf `prevent_destroy` dans le bootstrap
- [ ] Non, mais il est vidé de ses objets
- Réponse : non : un data source est seulement lu ; `destroy` ne supprime que les blocs `resource` de son état, la lecture disparaît sans toucher au bucket.

## 20. dépendance : jamais vers une couche plus courte
- Sous-thème : principe
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Une ressource durable ne doit rien utiliser d'une couche plus éphémère : le bucket d'artefacts chiffré par la clé KMS de l'environnement mourrait avec elle.
- Contexte : Les références vont dans un seul sens : l'environnement lit le bootstrap, jamais l'inverse. D'où SSE-S3 sur `artifacts` : la clé KMS du projet vit dans `infra/` ; après `make down`, elle passe en `PendingDeletion` et tout objet qu'elle chiffre devient illisible, même si le bucket survit. Le test : le bootstrap doit pouvoir s'appliquer sur un compte où `infra/` n'existe pas encore.
- Usage : ✅ SSE-S3, ou une clé KMS créée dans le bootstrap, pour les ressources du bootstrap · ❌ passer au bootstrap l'ARN d'une ressource de `infra/` : dépendance à rebours.

```hcl
# Exemple 1 : un chiffrement autonome
rule {
  apply_server_side_encryption_by_default {
    sse_algorithm = "AES256" # SSE-S3
  }
}
# ❌ kms_master_key_id = clé de infra/
# make down → clé en PendingDeletion
# → GetObject refusé : zips illisibles
```

- Quiz : Une politique de bucket du bootstrap autorise le rôle `ingest` de `infra/` par son ARN ; `make down` puis `make up` : le rôle recréé a-t-il accès ?
- [ ] Oui : même nom, donc même ARN
- [x] Non : la politique visait l'ancien rôle
- [ ] Oui, après un `refresh` du bootstrap
- [ ] Non : un bucket refuse les ARN de rôle
- Réponse : non : IAM enregistre l'identifiant interne du rôle (`AROA…`) ; le rôle recréé en a un autre, et la politique affiche l'ancien identifiant à la place de l'ARN.

## 21. make down : le test de la couche
- Sous-thème : principe
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Une ressource peut rester dans `infra/` si `make down` puis `make up` la recréent sans perte qui compte ; sinon elle monte au bootstrap.
- Contexte : Le test se fait ressource par ressource. Rôles, log groups, Lambdas : recréés à l'identique. `raw` de dev : son contenu disparaît, mais BODACC se rejoue par backfill, donc perte acceptable (en prod, `force_destroy = false` bloque). L'état et les zips, eux, sont lus par `make up` lui-même : impossible de les reconstruire après coup. Une perte acceptable se décide et s'écrit dans le README, elle ne se découvre pas.
- Usage : ✅ revue d'une nouvelle ressource : « qui la recrée, et avec quoi ? » · ❌ garder des données non rejouables (saisies, appels d'API payants) dans un environnement jetable.

```bash
# Exemple 1 : chaque ressource au test
# ressource     après down + up
# lambda, rôle  recréés à l'identique
# log groups    recréés, logs perdus
# raw (dev)     vide : backfill BODACC
# tfstate       lu par up : bootstrap
# artifacts     lu par up : bootstrap
```

- Quiz : Un bucket `refs` contient des codes de tribunaux corrigés à la main, sans autre copie : où le ranger ?
- [ ] Dans `infra/`, `make up` le recrée
- [ ] Dans `infra/` avec `force_destroy`
- [x] Hors de l'environnement jetable
- [ ] Dans `raw`, sous un préfixe `refs/`
- Réponse : hors de l'environnement jetable (bootstrap ou root de données durable) : `make up` recréerait un bucket vide, et ces corrections ne se rejouent pas comme BODACC.

## 22. for_each : grouper par forme, le piège
- Sous-thème : principe
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Un `for_each` sur une liste de noms crée des ressources jumelles : des buckets de durées de vie différentes y subissent le même sort.
- Contexte : L'erreur de S1-04 : `names = ["raw", "processed", "out", "artifacts", "logs"]` dans `modules/s3-buckets`, même clé KMS, même `force_destroy` en dev. La forme commune cachait une différence de cycle de vie. Une boucle est saine quand chaque élément se crée, se modifie et se détruit avec les autres ; dès qu'un élément demande un réglage à part, il sort de la boucle.
- Usage : ✅ buckets jumeaux d'une même couche (`raw`, `processed`, `out`) · ❌ glisser dans la boucle une ressource à protéger ou à garder plus longtemps.

```hcl
# Exemple 1 : la boucle d'origine
variable "names" {
  type    = list(string)
  default = ["raw", "processed", "out",
             "artifacts", "logs"]
}
resource "aws_s3_bucket" "this" {
  for_each      = toset(var.names)
  bucket        = "${var.prefix}-${each.key}"
  force_destroy = var.force_destroy
}
# make down → les 5 détruits ensemble
```

- Quiz : Pour protéger `artifacts` seul dans la boucle, on écrit `prevent_destroy = each.key == "artifacts"` : résultat ?
- [ ] Seul `artifacts` est protégé
- [ ] Les cinq buckets sont protégés
- [x] Erreur : `Variables not allowed`
- [ ] Ignoré sans erreur ni effet
- Réponse : `Variables not allowed` (vérifié avec `terraform validate`) : les arguments de `lifecycle` doivent être des littéraux ; la ressource à protéger sort de la boucle.

## 23. couches : se retrouver par convention
- Sous-thème : principe
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `infra/` retrouve le bucket du bootstrap en recalculant son nom (`data-platform-artifacts-<account_id>`), sans lire l'état du bootstrap.
- Contexte : Trois façons de relier deux roots : une convention de nom (rien à lire, mais deux endroits à garder alignés), `terraform_remote_state` (lit les outputs, mais exige l'accès à l'état de l'autre root), un data source (`aws_s3_bucket`) qui vérifie l'existence au plan. L'output `artifacts_bucket` du bootstrap sert aux humains et aux scripts (`build_lambda.py --publish`).
- Usage : ✅ convention de nom pour une ressource unique par compte, au nom stable · ❌ copier le nom en dur dans trois fichiers : un `local` unique par root.

```bash
# Exemple 1 : le même nom, deux sources
terraform -chdir=infra/bootstrap \
  output -raw artifacts_bucket
# → data-platform-artifacts-<account_id>
grep artifacts_bucket infra/lambdas.tf
# → "data-platform-artifacts-${
#    data.aws_caller_identity.current
#    .account_id}"
```

- Quiz : Pourquoi `infra/` ne lit-il pas ce nom par `terraform_remote_state` vers le bootstrap ?
- [x] L'état du bootstrap est local, absent en CI
- [ ] `terraform_remote_state` est interdit entre roots
- [ ] Il ne lit que des ressources, pas des outputs
- [ ] Il recréerait le bucket du bootstrap
- Réponse : l'état du bootstrap est local, sur le poste qui l'a appliqué : la CI ne peut pas le lire ; la convention de nom ne dépend d'aucun fichier.

## 24. nom global : un préfixe d'environnement
- Sous-thème : principe
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Une ressource dont le nom ne contient pas l'environnement entre en collision dès qu'un second environnement est déployé dans le même compte.
- Contexte : `data-platform-monthly-cost` (budget) et `data-platform-budget-alerts` (topic SNS) n'ont pas d'env. Un `prod` dans le même compte : le budget échoue (doublon), mais le topic est pire, car `CreateTopic` sur un nom existant renvoie le topic déjà là, sans erreur : deux états gèrent le même objet, et le `destroy` de l'un le supprime pour l'autre. Renommer après coup recrée la ressource : préfixer avant le second env, ou un compte par env.
- Usage : ✅ `name = "${local.prefix}-…"` pour toute ressource nommée ; un compte AWS par environnement · ❌ nom fixe « parce qu'il n'y a qu'un env » : le piège sort au second.

```hcl
# Exemple 1 : nom fixe, puis préfixé
resource "aws_sns_topic" "alerts" {
  # ❌ name = "data-platform-alerts"
  name = "${local.prefix}-alerts"
  # → data-platform-dev-alerts
}
```

- Quiz : `dev` et `prod` dans le même compte, même nom de topic SNS. Que fait le `apply` de `prod` ?
- [ ] Il échoue : le nom existe déjà
- [x] Il réussit et reprend le topic de `dev`
- [ ] Il crée un second topic au même nom
- [ ] Il renomme le topic de `dev`
- Réponse : il réussit et reprend le topic de `dev` : `CreateTopic` est idempotent sur le nom ; deux états pointent alors vers le même topic.

## 25. moved : renommer sans recréer
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

## 26. state rm : oublier sans détruire
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

## 27. verrou : use_lockfile natif S3
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

## 28. prevent_destroy : ce qu'il protège
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

## 29. import : rattacher l'existant
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

## 30. init -migrate-state : déplacer un état
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

## 31. state mv : déplacer tout de suite
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

## 32. changer de couche : moved ne traverse pas
- Sous-thème : state
- Niveau : 3
- Source : data-platform · S1-07
- Définition : `moved` ne déplace une ressource qu'à l'intérieur d'un même état ; vers un autre root, il faut la sortir d'un état puis l'importer dans l'autre.
- Contexte : Un bloc `moved` réécrit une adresse dans l'état courant : il ne voit aucun autre root. Pour garder un bucket en changeant de couche : bloc `removed` avec `destroy = false` dans `infra/`, puis `import` dans le bootstrap, en deux `apply`. Ici, rien à garder (un zip se republie) : détruire et recréer était plus simple, et changeait au passage nom et chiffrement.
- Usage : ✅ `removed` + `import` pour déplacer une ressource à garder (données, nom imposé) · ❌ ce détour pour une ressource jetable : la recréer dans la bonne couche.

```hcl
# Exemple 1 : infra/, sortir sans détruire
removed {
  from = module.s3.aws_s3_bucket.this["artifacts"]
  lifecycle {
    destroy = false
  }
}
# Exemple 1 (suite) : bootstrap, reprendre
import {
  to = aws_s3_bucket.artifacts
  id = "data-platform-dev-artifacts-<account_id>"
}
```

- Quiz : On fait l'`import` dans le bootstrap, mais on oublie le bloc `removed` dans `infra/` : que fait le `make down` suivant ?
- [ ] Rien : le bootstrap protège le bucket
- [x] Il détruit le bucket, géré par deux états
- [ ] Il échoue : bucket verrouillé par l'autre état
- [ ] Il le retire de l'état sans le détruire
- Réponse : il le détruit : les deux états le référencent, chacun se croit propriétaire ; `prevent_destroy` du bootstrap ne joue que dans le bootstrap. Une ressource, un seul état.

## 33. couches : au-delà de deux
- Sous-thème : principe
- Niveau : 3
- Source : data-platform · S1-07
- Définition : En entreprise, les roots s'empilent par durée de vie et rythme de changement : socle du compte, réseau, données, applications.
- Contexte : Chaque couche a son état, ses droits de déploiement et son rythme : le socle (état, artefacts, OIDC) bouge une fois par an, le réseau rarement, les Lambdas à chaque commit. Séparer réduit le rayon d'explosion : un `apply` raté sur une Lambda ne peut pas toucher un VPC. Le coût : des valeurs à passer d'une couche à l'autre (convention de nom, paramètre SSM, `terraform_remote_state`) et un ordre de déploiement à tenir.
- Usage : ✅ séparer ce qui change à des rythmes très différents ou ce qu'une autre équipe possède · ❌ un root par ressource : des dizaines d'états et d'ordres à orchestrer pour rien.

```bash
# Exemple 1 : quatre couches, de bas en haut
# 0-socle    état, artefacts, OIDC
#            1 apply par an, admin
# 1-reseau   VPC, endpoints
# 2-donnees  buckets prod, catalogue
#            prevent_destroy partout
# 3-app      lambdas, step functions
#            1 apply par commit, CI
```

- Quiz : Les buckets `raw` et `processed` de prod doivent survivre à une refonte complète des Lambdas : où les placer ?
- [ ] Dans le root des Lambdas, avec `prevent_destroy`
- [x] Dans une couche données, sous les applications
- [ ] Dans le socle, avec l'état
- [ ] Un root par bucket
- Réponse : une couche données, sous les applications : elle a la durée de vie des données, ses propres droits, et la refonte des Lambdas ne touche plus son état.

## 34. état perdu : importer chaque sous-ressource
- Sous-thème : state
- Niveau : 3
- Source : data-platform · S1-09
- Définition : Reconstruire un état perdu demande un `terraform import` par bloc `resource` du code, sous-ressources comprises, jusqu'à un `plan` à « No changes ».
- Contexte : Un bucket du provider AWS v4+ se décrit en plusieurs ressources : `aws_s3_bucket`, `_versioning`, `_server_side_encryption_configuration`, `_public_access_block`, `_lifecycle_configuration`. Chacune a son adresse et s'importe à part, souvent avec le nom du bucket comme id. Oublier les 5 ressources du bucket d'artefacts laissait le `plan` final avec 5 créations : la procédure n'était pas finie, et « No changes » est la seule preuve qu'elle l'est.
- Usage : ✅ lister les blocs `resource` du root (`grep '^resource'`), un import par ligne, `plan` final · ❌ s'arrêter au bucket principal : le plan propose de recréer le reste.

```bash
# Exemple 1 : ce qu'il faut importer
grep -h '^resource' infra/bootstrap/*.tf \
  | wc -l
# → 9  (4 tfstate, 5 artifacts)
terraform -chdir=infra/bootstrap plan
# → No changes : état reconstruit
```

- Quiz : Après import du seul `aws_s3_bucket.artifacts`, que propose `plan` pour son versioning ?
- [ ] Rien : il fait partie du bucket
- [x] Une création de `aws_s3_bucket_versioning`
- [ ] Une erreur : bucket déjà versionné
- [ ] Une suppression du versioning
- Réponse : une création : la ressource est dans le code mais pas dans l'état, donc Terraform prévoit de la créer, même si le réglage existe déjà sur AWS.
