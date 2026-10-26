---
title: "Cartes · Modules Terraform"
type: cartes
langage: Terraform
chapitre: Réutiliser
cours: Modules
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Modules Terraform
Terraform · Modules : appel, boucles, providers, refactoring, source (format spec v4 de revision-pwa).

## 1. module : seuls les outputs sortent
- Id : modules-outputs-seuls-visibles
- Sous-thème : appel
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : output, variable Terraform, état, KMS
- Définition : Un `module` appelle un dossier de `.tf` avec des entrées ; l'appelant ne voit que ses `output` (≈ les exports d'un fichier TS).
- Contexte : Les arguments du bloc `module` (hors `source`, `version`, `count`, `for_each`) remplissent les `variable` du module. Ses ressources sont adressées `module.s3.aws_s3_bucket.raw` dans le state, mais restent privées dans le code. Dans data-platform, `infra/main.tf` appelle `modules/kms`, `modules/s3-buckets` et `modules/iam`, et passe `module.s3.bucket_arns` au module IAM.
- Usage : ✅ regrouper des ressources liées réutilisées par chaque env (buckets + chiffrement) · ❌ envelopper une seule ressource sans logique : la déclarer directement.

```hcl
# Exemple 1 : appeler, lire un output
module "s3" {
  source = "./modules/s3-buckets"
  prefix = local.prefix
}
# module.s3.bucket_arns → OK
```

```hcl
# Exemple 2 : côté module
# modules/s3-buckets/variables.tf
variable "prefix" { type = string }

# modules/s3-buckets/outputs.tf
output "bucket_arns" {
  value = [aws_s3_bucket.raw.arn]
}
```

- Quiz : Que donne `module.s3.aws_s3_bucket.raw.arn` dans le module racine ?
- [ ] L'ARN du bucket
- [ ] `null` tant qu'il n'y a pas eu d'apply
- [x] `Error: Unsupported attribute`
- [ ] `Error: Module not installed`
- Réponse : `Error: Unsupported attribute` : les ressources d'un module sont privées, seul un `output` du module les rend lisibles.

## 2. structure : modules/ et envs/
- Id : modules-structure-root-envs
- Sous-thème : appel
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : root module, module Terraform, tfvars, backend
- Définition : Le root module est le dossier où l'on lance `terraform` ; `modules/` range les modules enfants, `envs/<env>/` seulement les valeurs propres à chaque environnement.
- Contexte : Terraform ne lit que les `.tf` du dossier courant, jamais ses sous-dossiers : un module enfant n'existe que s'il est appelé par un bloc `module`. Dans data-platform, `infra/` est le root (providers, backend, appels), `infra/modules/{kms,s3-buckets,iam}` les briques, `infra/envs/dev/` les `dev.tfvars` et `backend.hcl`. Lancer `plan` dans `modules/s3-buckets` en ferait un root : `No value for required variable`.
- Usage : ✅ un seul root pour tous les environnements, différenciés par `-var-file` et `-backend-config` · ❌ un root copié par environnement (`envs/dev/main.tf`) : le code de dev et de prod diverge.

```bash
# Exemple 1 : l'arborescence de data-platform
# infra/            ← root : make plan
# ├── main.tf       appelle les modules
# ├── providers.tf  backend.tf
# ├── modules/
# │   ├── kms/      main, variables,
# │   ├── s3-buckets/  outputs, versions
# │   └── iam/
# └── envs/dev/     dev.tfvars
#                   backend.hcl
```

```bash
# Exemple 2 : un root, un env choisi
make plan ENV=dev
# terraform -chdir=infra plan \
#   -var-file=envs/dev/dev.tfvars
```

- Quiz : Un fichier `infra/envs/prod/main.tf` est ajouté : `make plan ENV=prod` (lancé dans `infra/`) le lit-il ?
- [ ] Oui : `-var-file` charge son dossier
- [x] Non : seuls les `.tf` de `infra/` sont lus
- [ ] Oui, après `terraform init`
- [ ] Non, sauf avec `-recursive`
- Réponse : non : Terraform ne lit que les `.tf` du dossier du root ; un sous-dossier n'est lu que s'il est appelé comme module (`source = "./envs/prod"`).

## 3. variable de module : argument requis
- Id : modules-variable-argument-requis
- Sous-thème : appel
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Prérequis : variables-declarer-valider
- Voir aussi : modules-null-pas-absent
- Mots-clés : module Terraform, variable Terraform, validation
- Définition : Chaque `variable` du module sans `default` devient un argument obligatoire du bloc `module` qui l'appelle (≈ une prop requise d'un composant).
- Contexte : Le bloc `module` est la signature de l'appel : ses arguments remplissent les `variable` du module, un par un, contrôlés par leur `type` et leurs `validation`. Un argument manquant est refusé dès `validate`, sans rien demander au clavier (contrairement à une variable du root). Chaque `variable` est documentée par `description` : c'est l'API du module pour ses appelants.
- Usage : ✅ sans `default` ce que l'appelant doit choisir (préfixe, ARN de clé), avec `default` les options (noms, rétention) · ❌ une `variable` lue par `var.` hors du module : elle n'existe que dedans.

```hcl
# Exemple 1 : prefix oublié
# modules/s3-buckets/variables.tf
variable "prefix" { type = string }

module "s3" {
  source = "./modules/s3-buckets"
}
# validate → Error: Missing required
#   argument : "prefix" is required
```

```hcl
# Exemple 2 : l'appel de data-platform
module "s3" {
  source      = "./modules/s3-buckets"
  prefix      = local.prefix
  suffix      = data.aws_caller_identity.current.account_id
  kms_key_arn = module.kms.key_arn
}
```

- Quiz : L'appel passe aussi `region = "eu-west-3"`, que le module ne déclare pas : que dit `validate` ?
- [ ] Rien : l'argument est ignoré
- [ ] Un avertissement, puis valide
- [x] `Error: Unsupported argument`
- [ ] `region` devient `var.region`
- Réponse : `Unsupported argument` : un module n'accepte que ses `variable` déclarées (et `source`, `count`…), pas de props en trop comme en JS.

## 4. output de module : brancher deux modules
- Id : modules-output-dependance
- Sous-thème : appel
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Prérequis : modules-outputs-seuls-visibles
- Mots-clés : graphe de dépendances, depends_on, output, KMS
- Définition : Passer `module.kms.key_arn` en argument d'un autre module crée une dépendance : Terraform crée la clé avant les buckets, sans `depends_on`.
- Contexte : Le graphe de Terraform se construit à partir des références : un argument qui lit l'output d'un module fait attendre seulement les ressources dont cet output dépend. C'est ainsi que data-platform enchaîne `kms` → `s3` → `iam` (`bucket_arns`). Venant de TS, `module.kms` ressemble à un import : c'est une valeur, l'objet de tous ses outputs.
- Usage : ✅ chaîner les modules par leurs outputs (ARN, noms, maps) · ❌ `depends_on` pour ordonner : une référence suffit et garde un plan précis.

```hcl
# Exemple 1 : kms, puis s3
module "kms" {
  source = "./modules/kms"
  name   = local.prefix
}
module "s3" {
  source      = "./modules/s3-buckets"
  kms_key_arn = module.kms.key_arn
}
```

```hcl
# Exemple 2 : une map en sortie, en entrée
module "iam" {
  source      = "./modules/iam"
  bucket_arns = module.s3.bucket_arns
}
# bucket_arns : { raw = "arn:…", … }
```

- Quiz : Que renvoie `module.s3` tout seul, tapé dans `terraform console` ?
- [ ] `Error: Invalid reference`
- [x] L'objet de tous ses outputs
- [ ] La liste de ses ressources
- [ ] Le chemin `./modules/s3-buckets`
- Réponse : l'objet de ses outputs (`{ bucket_names = {…} }`, mesuré) : un module est une valeur dont les attributs sont ses `output`, rien d'autre.

## 5. init : installer un module ajouté
- Id : modules-init-installer
- Sous-thème : source
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Prérequis : cli-init-preparer-dossier
- Voir aussi : modules-source-changee-init
- Mots-clés : init, module Terraform
- Définition : `terraform init` installe chaque appel de module dans `.terraform/modules` ; un bloc `module` ajouté ou renommé exige un nouvel `init`.
- Contexte : Même un module local est « installé » : `init` enregistre chaque appel (sa clé, sa source, son dossier) dans `.terraform/modules/modules.json`. `plan` et `validate` lisent ce registre, pas le code : un appel absent du fichier est refusé (`Module not installed`). Un `git pull` qui ajoute un module demande donc un `make tf-init`.
- Usage : ✅ `init` après tout ajout ou changement d'un bloc `module` (nom, source, version) · ❌ supprimer `.terraform/` pour « réparer » : `init` suffit, et il faudrait rejouer le backend.

```bash
# Exemple 1 : module ajouté sans init
terraform plan
# → Error: Module not installed
#   module "s3_prod" { …
terraform init
# → - s3_prod in modules/s3
terraform plan   # → OK
```

- Quiz : Tu renommes seulement le label, `module "s3_prod"` → `module "prod"`, même source : `plan` sans `init` ?
- [ ] Passe : la source n'a pas changé
- [x] `Error: Module not installed`
- [ ] Propose de renommer les ressources
- [ ] `Error: Module source has changed`
- Réponse : `Module not installed` (mesuré) : `init` enregistre les modules par label ; `module.prod` est un appel nouveau pour lui.

## 6. registre : namespace/nom/fournisseur
- Id : modules-source-registre
- Sous-thème : source
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : registre Terraform, SemVer, module Terraform
- Définition : Une source de registre s'écrit `<namespace>/<nom>/<fournisseur>` (`terraform-aws-modules/s3-bucket/aws`) et se télécharge à l'`init`, à la version demandée.
- Contexte : Sans préfixe, `source` est lue comme une adresse de registre (registry.terraform.io par défaut, ou `hôte/namespace/nom/fournisseur`). Un chemin local doit commencer par `./` ou `../`, sinon Terraform cherche un module distant. Un module public est versionné en SemVer et documenté (entrées, sorties) sur le registre : on lit sa page avant de l'appeler.
- Usage : ✅ module public éprouvé (VPC, bucket complet), épinglé par `version` · ❌ un module public de 300 variables pour 3 ressources : un module local, lisible en entier.

```hcl
# Exemple 1 : module public
module "raw" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "4.1.0"
  bucket  = "data-platform-dev-raw"
}
# init → Downloading registry.terraform.io
#   /terraform-aws-modules/s3-bucket/aws
#   4.1.0 for raw...
```

- Quiz : Que fait `init` avec `source = "modules/s3"`, sans `./` ?
- [ ] Lit le dossier local `modules/s3`
- [ ] Cherche `modules/s3` sur le registre
- [x] `Error: Invalid module source address`
- [ ] Lit `.terraform/modules/s3`
- Réponse : `Invalid module source address` (mesuré) : sans `./`, ce n'est ni un chemin ni une adresse de registre valide (3 parties) ; Terraform suggère `"./modules/s3"`.

## 7. module : changer la source
- Id : modules-source-changee-init
- Sous-thème : source
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : modules-init-installer
- Mots-clés : init, registre Terraform, contrainte de version
- Définition : Changer la `source` d'un appel (dossier local, registre, git) exige un nouvel `init` : `plan` compare la source à celle enregistrée par le dernier `init`.
- Contexte : `init` note la source de chaque appel dans `.terraform/modules/modules.json` ; `plan` et `validate` lisent ce registre, pas le dossier. Une source de registre se fixe avec `version` (`~> 4.0` : 4.x, jamais 5.0) ; une source locale (`./modules/…`) est lue sur place et refuse `version` (`Invalid registry module source address`).
- Usage : ✅ `init` après tout changement de `source` ou de `version`, registre avec `version` épinglée · ❌ registre sans `version` : une mise à jour majeure arrive sans prévenir.

```hcl
# Exemple 1 : nouvelle source, sans init
module "s3" {
  # avant : ./modules/s3
  source = "./modules/s3-buckets"
}
# terraform plan (mesuré)
# → Error: Module source has changed
# terraform init → plan OK
```

```bash
# Exemple 2 : ce qu'init enregistre
terraform init
cat .terraform/modules/modules.json
# → {"Modules":[…,{"Key":"s3",
#   "Source":"./modules/s3-buckets",
#   "Dir":"modules/s3-buckets"}]}
```

- Quiz : Même source de registre, tu passes seulement `version` de `~> 0.24.0` à `~> 0.25.0`, sans `init` : que fait `plan` ?
- [ ] Il télécharge la 0.25 au passage
- [ ] Il garde la 0.24 installée, sans erreur
- [x] `Error: Module version requirements have changed`
- [ ] `Error: Module source has changed`
- Réponse : `Module version requirements have changed` (mesuré) : la version installée ne respecte plus la contrainte, seul `init` en choisit une autre.

## 8. git : épingler par ?ref
- Id : modules-source-git-ref
- Sous-thème : source
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : modules-source-registre
- Voir aussi : modules-versions-non-verrouillees
- Mots-clés : tag git, commit, registre Terraform, SemVer
- Définition : Une source `git::https://…git//sous-dossier?ref=v1.2.0` clone un dépôt à un tag ou un commit : la version passe dans l'URL, pas dans `version`.
- Contexte : C'est la façon de partager un module interne sans registre privé (dépôt GitLab ou CodeCommit). `//` sépare le dépôt du sous-dossier du module, `?ref=` choisit tag, branche ou SHA. `version` n'est accepté qu'avec une source de registre : à côté d'une URL git, `init` la lit comme une adresse de registre et échoue. Un `ref` de branche (`main`) n'épingle rien.
- Usage : ✅ module interne partagé entre dépôts, tag SemVer (`v1.2.0`) ou SHA · ❌ `?ref=main` ou pas de `ref` : chaque nouveau clone prend la dernière version de la branche.

```hcl
# Exemple 1 : un tag précis
module "s3" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git?ref=v4.1.0"
}
# init → Downloading git::https://…
#   ?ref=v4.1.0 for s3...
# .terraform/modules/s3 : git describe
# → v4.1.0
```

```hcl
# Exemple 2 : un sous-dossier du dépôt
module "kms" {
  # dépôt//dossier?ref=…
  source = "git::https://git.example.com/infra/modules.git//kms?ref=v1.2.0"
}
```

- Quiz : On ajoute `version = "4.1.0"` à côté de la source git `?ref=v4.1.0` : que fait `init` ?
- [ ] Vérifie que le tag vaut bien 4.1.0
- [ ] Ignore `version`, garde `ref`
- [x] `Error: Invalid registry module source address`
- [ ] Prend `version`, ignore `ref`
- Réponse : `Invalid registry module source address` (mesuré) : `version` fait traiter `source` comme une adresse de registre, que l'URL git n'est pas.

## 9. providers : hérités du root
- Id : modules-providers-herites
- Sous-thème : providers
- Type : concept
- Niveau : 2
- Profils : ops
- Voir aussi : modules-configuration-aliases
- Mots-clés : provider, root module, default_tags
- Définition : Un module sans bloc `provider` utilise la configuration par défaut du root (région, profil, `default_tags`) : il ne configure jamais ses providers lui-même.
- Contexte : Le root configure, les modules consomment : la configuration `aws` par défaut est transmise implicitement à chaque module appelé. C'est pourquoi data-platform écrit `default_tags` une seule fois dans `infra/providers.tf` et retrouve les tags sur les buckets de `modules/s3-buckets`. Une configuration avec `alias` (`aws.use1`), elle, n'est jamais transmise sans `providers = { … }`.
- Usage : ✅ un seul `provider "aws"` dans le root, modules sans bloc `provider` · ❌ un `provider` dans un module réutilisable : région figée, et `for_each` interdit sur ce module.

```hcl
# Exemple 1 : le module hérite
# root : provider "aws" eu-west-3
module "cdn" {
  source = "./modules/cdn"
}
# plan → + region = "eu-west-3"
```

```hcl
# Exemple 2 : choisir une config alias
provider "aws" {
  alias  = "use1"
  region = "us-east-1"
}
module "cdn" {
  source    = "./modules/cdn"
  providers = { aws = aws.use1 }
}
# plan → + region = "us-east-1"
```

- Quiz : Le root pose `default_tags { tags = { project = "data-platform" } }` : un bucket créé dans un module les reçoit-il ?
- [x] Oui, dans son `tags_all`
- [ ] Non, le module doit les redéclarer
- [ ] Oui, seulement avec `providers = { aws = aws }`
- [ ] Non, `default_tags` vaut pour le root seul
- Réponse : oui (mesuré, `tags_all = { project = "data-platform" }`) : le module utilise la même configuration de provider, `default_tags` compris.

## 10. required_providers : sans required_version
- Id : modules-required-providers
- Sous-thème : providers
- Type : concept
- Niveau : 2
- Profils : ops
- Mots-clés : provider, contrainte de version, root module
- Définition : Le `versions.tf` d'un module déclare seulement `required_providers` (source et contrainte) ; `required_version` et le bloc `provider` restent au root.
- Contexte : `required_providers` dit d'où vient `aws` (`hashicorp/aws`) et quelles versions le module supporte. Terraform fait l'intersection des contraintes du root et de tous les modules, puis choisit une version qui les satisfait toutes. La CLI et la configuration (région, profil) sont l'affaire du root. Les modules publics posent un plancher large (`>= 5.83.0`) pour rester compatibles avec beaucoup de roots.
- Usage : ✅ contrainte de module large ou alignée sur le root (`~> 6.0` dans data-platform) · ❌ un module épinglé sur une version exacte : il bloque toute montée du provider dans le root.

```hcl
# Exemple 1 : modules/s3-buckets/versions.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
# pas de required_version, pas de provider
```

```bash
# Exemple 2 : l'arbre des contraintes
terraform providers
# ├── provider[…/hashicorp/aws] ~> 6.0
# └── module.s3
#     └── provider[…/hashicorp/aws] ~> 6.0
```

- Quiz : Le root exige `aws ~> 6.0`, un module `aws ~> 5.0` : que fait `terraform init` ?
- [ ] Installe la 6.x pour le root, la 5.x pour le module
- [ ] Prend la 6.x et avertit le module
- [x] Échoue : aucune version ne satisfait les deux
- [ ] Prend la 5.x, la plus ancienne
- Réponse : il échoue (`no available releases match the given constraints ~> 5.0, ~> 6.0`, mesuré) : un provider n'a qu'une version par root, partagée par tous les modules.

## 11. configuration_aliases : un module, deux régions
- Id : modules-configuration-aliases
- Sous-thème : providers
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : modules-providers-herites
- Mots-clés : provider, ACM, CloudFront, région AWS
- Définition : `configuration_aliases = [aws.use1]` déclare qu'un module attend une seconde configuration de provider, que l'appelant doit lui passer par `providers`.
- Contexte : Certaines ressources vivent dans une région imposée : un certificat ACM pour CloudFront doit être en `us-east-1`. Le module déclare l'alias dans `required_providers`, l'utilise avec `provider = aws.use1` sur ces ressources, et laisse le reste sur `aws`. L'appelant fait le lien dans `providers = { aws.use1 = aws.use1 }` ; oublier ce lien est refusé dès `validate`.
- Usage : ✅ module qui touche deux régions ou deux comptes (ACM + CloudFront, réplication S3) · ❌ alias juste pour changer de région tout le module : `providers = { aws = aws.use1 }` suffit.

```hcl
# Exemple 1 : côté module
terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.use1]
    }
  }
}
resource "aws_s3_bucket" "edge" {
  provider = aws.use1
  bucket   = "revision-pwa-dev-edge"
}
```

```hcl
# Exemple 2 : côté appelant
module "cdn" {
  source = "./modules/cdn"
  providers = {
    aws      = aws
    aws.use1 = aws.use1
  }
}
```

- Quiz : L'appelant écrit seulement `module "cdn" { source = "./modules/cdn" }` : que dit `validate` ?
- [ ] Valide : `aws.use1` est hérité du root
- [x] `Error: Missing required provider configuration`
- [ ] Valide, `edge` part en eu-west-3
- [ ] `Error: Provider configuration not present` à l'apply
- Réponse : `Missing required provider configuration` (mesuré) : une configuration alias n'est jamais transmise implicitement, l'appelant doit la nommer dans `providers`.

## 12. for_each : un module par clé
- Id : modules-for-each-instances
- Sous-thème : boucles
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : langage-hcl-for-each-cle
- Voir aussi : modules-outputs-for-each
- Mots-clés : for_each, module Terraform, adresse, état
- Définition : `for_each` sur un bloc `module` crée une instance du module par clé : `module.s3["dev"]`, chacune avec ses ressources et ses outputs.
- Contexte : Comme sur une ressource, `for_each` prend une map ou un set de chaînes, et `each.key` / `each.value` alimentent les arguments. Les ressources sont adressées `module.s3["dev"].aws_s3_bucket.this["raw"]`. `module.s3` devient une map d'objets : on lit un output par la clé, jamais directement. La clé fait partie de l'adresse : la renommer détruit puis recrée l'instance.
- Usage : ✅ plusieurs jeux de ressources identiques dans un même root (un bucket set par producteur) · ❌ un environnement par clé : dev et prod partagent alors un état ; un état par env (`-var-file`, `-backend-config`).

```hcl
# Exemple 1 : une instance par clé
module "s3" {
  source   = "./modules/s3"
  for_each = toset(["dev"])
  prefix   = "data-platform-${each.key}"
}
# module.s3["dev"].bucket_names.raw
# → "data-platform-dev-raw"
```

- Quiz : Avec ce `for_each`, que donne `module.s3.bucket_names` ?
- [ ] La map des outputs de la seule instance
- [ ] `{ dev = { raw = … } }`
- [x] `Error: Unsupported attribute`
- [ ] `null` tant qu'il n'y a qu'une clé
- Réponse : `Unsupported attribute` (mesuré) : `module.s3` est une map d'instances, sans attribut `bucket_names` ; il faut `module.s3["dev"].bucket_names`.

## 13. count : activer un module ou non
- Id : modules-count-optionnel
- Sous-thème : boucles
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : langage-hcl-count-index
- Voir aussi : langage-hcl-dynamic-bloc-facultatif
- Mots-clés : count, output, module Terraform
- Définition : `count = var.x ? 1 : 0` sur un module l'active ou non ; ses outputs se lisent alors par index, ou par `one(module.x[*].out)`.
- Contexte : Avec `count`, `module.prod` devient une liste de 0 ou 1 instance. Indexer `[0]` quand `count = 0` échoue (`Invalid index`). `one()` renvoie l'unique élément ou `null` si la liste est vide : l'output reste lisible dans les deux cas. Pour plusieurs instances aux rôles distincts, `for_each` et des clés.
- Usage : ✅ option du root (module d'alertes, d'export) activée par une variable booléenne · ❌ plusieurs instances : `for_each`, leurs adresses ne se décalent pas quand on en retire une.

```hcl
# Exemple 1 : module optionnel
variable "with_prod" {
  type    = bool
  default = false
}
module "prod" {
  source = "./modules/s3"
  count  = var.with_prod ? 1 : 0
  prefix = "data-platform-prod"
}
output "raw" {
  # null si count = 0
  value = one(module.prod[*].bucket_names.raw)
}
```

- Quiz : Avec `count = 0`, un output `module.prod[0].bucket_names.raw` : où apparaît l'erreur ?
- [ ] `terraform validate`
- [x] `terraform plan`
- [ ] `terraform apply`
- [ ] Nulle part : l'output vaut `null`
- Réponse : au `plan` (`Invalid index`, mesuré) : `validate` ignore les valeurs de `count` et passe ; le plan découvre une liste vide.

## 14. outputs d'un module for_each : for et values
- Id : modules-outputs-for-each
- Sous-thème : boucles
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : modules-for-each-instances, langage-hcl-for-map
- Mots-clés : for_each, splat, output
- Définition : Un output de toutes les instances d'un module `for_each` se lit en parcourant la map : expression `for`, ou `values(module.s3)[*].out`.
- Contexte : `module.s3` est une map clé → objet d'outputs. Une expression `for` garde les clés, `values()` donne une liste triée par clé, sur laquelle le splat `[*]` fonctionne. Le splat ne sait parcourir qu'une liste : appliqué à une map, il l'emballe dans une liste à un élément au lieu de l'itérer. C'est le piège venant de `Object.values(x).map`.
- Usage : ✅ output du root qui agrège toutes les instances (noms de buckets par env ou par producteur) · ❌ `module.s3[*]` sur un module `for_each` : réservé à `count`.

```hcl
# Exemple 1 : garder les clés
output "raw_by_env" {
  value = {
    for k, m in module.s3 :
    k => m.bucket_names.raw
  }
}
# → { dev = "data-platform-dev-raw" }
```

```hcl
# Exemple 2 : une liste, par values()
output "raws" {
  value = values(module.s3)[*].bucket_names.raw
}
# → ["data-platform-dev-raw"]
```

- Quiz : Que donne `module.s3[*].bucket_names` sur ce module `for_each` ?
- [ ] La liste des `bucket_names`
- [ ] La map `{ dev = … }`
- [ ] `[]`
- [x] `Error: Unsupported attribute`
- Réponse : `Unsupported attribute` (mesuré) : le splat emballe la map en liste d'un élément, la map elle-même, qui n'a pas d'attribut `bucket_names`.

## 15. module : null n'est pas « absent »
- Id : modules-null-pas-absent
- Sous-thème : appel
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : modules-variable-argument-requis
- Voir aussi : variables-nullable-false
- Mots-clés : variable Terraform, module Terraform
- Définition : Le `default` d'une variable de module ne sert que si l'argument est omis : passer `null` donne `null`, pas le défaut.
- Contexte : Un appelant passe souvent une valeur calculée (`var.x`, une condition) qui peut valoir `null` sans qu'on le voie : le module reçoit alors `null` malgré son `default`. L'attribut `nullable` de la variable, vrai par défaut, décide si `null` est une valeur acceptée telle quelle.
- Usage : ✅ défaut pour une option rarement changée (suffixe, rétention) · ❌ compter sur le défaut quand l'appelant transmet une valeur peut-être `null` : ajouter `nullable = false`.

```hcl
# Exemple 1 : argument omis → défaut
# modules/bucket/variables.tf
variable "suffix" {
  type    = string
  default = "raw"
}
module "s3" {
  source = "./modules/bucket"
}
# var.suffix → "raw"
```

```hcl
# Exemple 2 : null passé explicitement
module "s3" {
  source = "./modules/bucket"
  suffix = null
}
# var.suffix → null (pas "raw")
```

- Quiz : Le module ajoute `nullable = false` à `suffix` (défaut `"raw"`) ; l'appelant passe toujours `suffix = null`. Que vaut `var.suffix` ?
- [x] `"raw"`
- [ ] `null`
- [ ] `Error: Required variable not set`
- [ ] `""`
- Réponse : `"raw"` (mesuré) : avec `nullable = false`, un `null` reçu est remplacé par le défaut ; sans défaut, ce serait `Required variable not set`.

## 16. moved : renommer un appel de module
- Id : modules-moved-renommer-appel
- Sous-thème : refactoring
- Type : recette
- Niveau : 3
- Profils : ops, expert
- Prérequis : state-backend-moved-renommer
- Voir aussi : modules-moved-count-for-each
- Mots-clés : adresse, état, module Terraform, KMS
- Définition : `moved { from = module.s3_prod  to = module.prod }` déplace dans l'état toutes les ressources du module renommé, sans les recréer.
- Contexte : Le label du bloc `module` fait partie de l'adresse de chaque ressource (`module.s3_prod.aws_s3_bucket.this["raw"]`). Le renommer sans `moved` fait détruire et recréer tout le module : buckets vidés, clé KMS planifiée en suppression. Un seul bloc `moved` au niveau du module suffit, Terraform déplace chaque ressource dessous. Le nouveau label demande aussi un `terraform init`.
- Usage : ✅ renommer un appel, regrouper des ressources du root dans un module (`from = aws_s3_bucket.raw`) · ❌ changer la `source` vers un module aux adresses internes différentes : des `moved` dans le module aussi.

```hcl
# Exemple 1 : renommer l'appel
module "prod" {
  source = "./modules/s3"
  prefix = "data-platform-prod"
}
moved {
  from = module.s3_prod
  to   = module.prod
}
# terraform init, puis plan
# → Plan: 0 to add, 0 to change,
#   0 to destroy.
```

```bash
# Exemple 2 : sans moved (mesuré)
terraform plan
# → module.prod…["raw"] will be created
#   module.s3_prod…["raw"] will be
#   destroyed
# Plan: 2 to add, 0 to change,
#   2 to destroy.
```

- Quiz : Le module contient 2 buckets : combien de blocs `moved` faut-il pour renommer l'appel ?
- [ ] Deux : un par ressource
- [x] Un seul, sur `module.s3_prod`
- [ ] Trois : le module et ses deux buckets
- [ ] Aucun : Terraform le déduit
- Réponse : un seul : un `moved` sur une adresse de module déplace tout ce qu'il contient (le plan affiche un « has moved » par ressource, mesuré).

## 17. moved : de count à for_each
- Id : modules-moved-count-for-each
- Sous-thème : refactoring
- Type : recette
- Niveau : 3
- Profils : ops, expert
- Prérequis : modules-moved-renommer-appel, modules-count-optionnel, modules-for-each-instances
- Mots-clés : count, for_each, moved, adresse
- Définition : Passer un module de `count` à `for_each` change ses adresses (`[0]` → `["dev"]`) : un `moved` par instance évite de tout recréer.
- Contexte : Les instances `count` sont indexées par position, celles de `for_each` par clé : pour Terraform, `module.s3[0]` et `module.s3["dev"]` sont deux objets différents. Le `moved` relie l'ancienne adresse à la nouvelle, instance par instance ; le plan doit afficher `has moved to` et `0 to destroy`. Garder le bloc tant que tous les environnements n'ont pas appliqué.
- Usage : ✅ migrer `count` vers `for_each`, ajouter `count` ou `for_each` à un module existant · ❌ compter sur une déduction automatique pour un module : toujours écrire le `moved` et relire le plan.

```hcl
# Exemple 1 : [0] devient ["dev"]
module "s3" {
  source   = "./modules/s3"
  for_each = toset(["dev"])
  prefix   = "data-platform-${each.key}"
}
moved {
  from = module.s3[0]
  to   = module.s3["dev"]
}
# plan → module.s3[0]… has moved to
#   module.s3["dev"]…
# Plan: 0 to add, 0 to change,
#   0 to destroy.
```

- Quiz : Tu ajoutes `count = 1` à un module déjà appliqué, sans `moved` : que prévoit le plan ?
- [ ] `module.s3 has moved to module.s3[0]`
- [x] Détruire `module.s3`, créer `module.s3[0]`
- [ ] `No changes.`
- [ ] `Error: Missing resource instance key`
- Réponse : destroy puis create (mesuré, 1.14) : la déduction `x` → `x[0]` vaut pour une ressource, pas pour un appel de module ; il faut `moved { from = module.s3  to = module.s3[0] }`.

## 18. provider dans un module : for_each interdit
- Id : modules-provider-interne-legacy
- Sous-thème : providers
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : modules-providers-herites, modules-for-each-instances
- Voir aussi : modules-configuration-aliases
- Mots-clés : provider, méta-argument, for_each, root module
- Définition : Un module qui contient son propre bloc `provider` est un module « legacy » : son appel refuse `count`, `for_each` et `depends_on`.
- Contexte : Une configuration de provider doit survivre à ses ressources pour pouvoir les détruire : si elle vit dans une instance de module qu'on retire du `for_each`, plus rien ne sait supprimer ses ressources. Terraform interdit donc ces méta-arguments dès `init`. La correction : sortir le bloc `provider` vers le root et le passer par `providers`.
- Usage : ✅ module sans `provider`, configuration reçue du root · ❌ copier un `providers.tf` dans un module pour « qu'il marche seul » : on perd `for_each` et la réutilisation.

```hcl
# Exemple 1 : refusé dès init
# modules/b/main.tf contient :
#   provider "aws" { region = … }
module "b" {
  source   = "./modules/b"
  for_each = toset(["dev"])
}
# → Error: Module is incompatible
#   with count, for_each, and
#   depends_on
```

- Quiz : Même module, mais l'appel utilise `count = 1` au lieu de `for_each` : résultat ?
- [ ] Accepté : `count = 1` ne crée qu'une instance
- [ ] Accepté avec un avertissement
- [x] La même erreur `Module is incompatible…`
- [ ] Le provider du module est ignoré
- Réponse : la même erreur (mesuré) : `count`, même à 1, rend l'instance supprimable ; seul un appel simple garde un module legacy.

## 19. lock : les modules ne sont pas verrouillés
- Id : modules-versions-non-verrouillees
- Sous-thème : source
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : cli-lock-provider-commite
- Voir aussi : modules-source-git-ref
- Mots-clés : .terraform.lock.hcl, contrainte de version, registre Terraform, init
- Définition : `.terraform.lock.hcl` fige les versions des providers, jamais celles des modules : seule la contrainte `version` les borne.
- Contexte : `init` choisit la plus récente version de module qui respecte `version` et la note dans `.terraform/modules/modules.json`, un fichier local non commité. Un `init` sur un poste neuf, en CI ou après `-upgrade` peut donc prendre une version plus récente que celle d'un collègue. D'où une version exacte (`= 4.1.0`) pour un module public en prod, montée par MR.
- Usage : ✅ version exacte d'un module de registre, `?ref=` sur un tag ou un SHA pour git · ❌ `~> 4.1` en croyant que le lock protège : il ne liste que des providers.

```bash
# Exemple 1 : le lock ignore le module
grep -c module .terraform.lock.hcl
# → 0
# version = "~> 4.1", installé : 4.1.0
terraform init -upgrade
# → Downloading …/s3-bucket/aws
#   4.11.0 for s3...
```

- Quiz : `version = "~> 4.1"`, ta machine a 4.1.0. Un clone neuf en CI lance `terraform init` : quelle version obtient-il ?
- [ ] 4.1.0, notée dans `.terraform.lock.hcl`
- [x] La dernière 4.x publiée
- [ ] 4.1.0 : `init` sans `-upgrade` ne monte jamais
- [ ] La dernière version, 5.x comprise
- Réponse : la dernière 4.x (4.11.0 mesurée) : sans `.terraform/` ni entrée de lock pour les modules, `init` prend la plus récente qui respecte `~> 4.1`.

## 20. for_each : clés connues avant l'apply
- Id : modules-for-each-cles-connues
- Sous-thème : boucles
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : langage-hcl-for-each-cle
- Voir aussi : cli-target-dependances
- Mots-clés : for_each, known after apply, count
- Définition : Les clés d'un `for_each` (ressource ou module) doivent être connues au `plan` : un set construit depuis un output encore inconnu est refusé.
- Contexte : Terraform doit nommer chaque instance avant de créer quoi que ce soit, or un id ou un ARN produit par l'apply n'existe pas encore (`known after apply`). `toset(module.kms.ids)` échoue donc au premier plan (`Invalid for_each argument`). Les valeurs, elles, peuvent rester inconnues : une map aux clés littérales passe. `count = length(…)` passe aussi si la longueur est connue.
- Usage : ✅ clés tirées de variables ou de littéraux (`raw`, `logs`), ARN en valeur · ❌ clés tirées d'ids générés : on ne peut pas planifier.

```hcl
# Exemple 1 : clés inconnues
module "s3" {
  source   = "./modules/s3"
  for_each = toset(module.kms.ids)
  prefix   = "x"
}
# plan → Error: Invalid for_each
#   argument
```

```hcl
# Exemple 2 : clés fixes, valeur inconnue
resource "terraform_data" "x" {
  for_each = { raw = module.kms.key_arn }
  input    = each.value
}
# plan → x["raw"] will be created
```

- Quiz : Même liste inconnue, mais `count = length(module.kms.ids)` avec `ids = [terraform_data.key.id]` : que fait le plan ?
- [ ] `Error: Invalid count argument`
- [x] Il passe : 1 instance prévue
- [ ] Il passe avec 0 instance
- [ ] Il reporte le calcul à l'apply
- Réponse : il passe (mesuré, `x[0] will be created`) : la liste a un élément connu en nombre, seul son contenu est inconnu ; `count` n'a besoin que de la longueur.

## 21. depends_on sur un module : data lues à l'apply
- Id : modules-depends-on-module
- Sous-thème : appel
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : modules-output-dependance, langage-hcl-data-source-lu-au-plan
- Mots-clés : depends_on, data source, known after apply, KMS
- Définition : `depends_on = [module.kms]` fait attendre tout le module ; ses data sources ne sont plus lues au plan dès que `kms` change.
- Contexte : Terraform ne sait pas quelle ressource du module dépend de quoi : il retarde tout. Une data source qui dépend de changements en attente est lue à l'apply (`will be read during apply`), donc ses attributs deviennent `known after apply`, et les ressources qui la lisent apparaissent modifiées à chaque plan où `kms` bouge. Une référence à un output ne lie que ce qui en dépend.
- Usage : ✅ dépendance réellement invisible (une politique IAM qui doit exister avant un appel) · ❌ ordonner deux modules liés par leurs valeurs : passer l'output, Terraform déduit l'ordre.

```hcl
# Exemple 1 : tout le module attend
module "s3" {
  source     = "./modules/s3"
  depends_on = [module.kms]
}
# kms change → plan (mesuré) :
# module.s3.data.terraform_remote_state
#   .boot will be read during apply
# ~ input = "data-platform-tfstate-123"
#   -> (known after apply)
```

- Quiz : Sans `depends_on`, même changement dans `kms` : combien de ressources `plan` modifie-t-il ?
- [x] 1 : la ressource de `kms`
- [ ] 2 : `kms` et celle de `s3`
- [ ] 0 : il faut un `apply` d'abord
- [ ] Toutes celles de `s3`, par prudence
- Réponse : 1 (mesuré : `Plan: 0 to add, 1 to change`) : la data source est lue au plan, sa valeur ne change pas, `s3` reste intact.
