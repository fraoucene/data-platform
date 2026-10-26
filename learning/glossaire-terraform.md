---
type: glossaire
langage: Terraform
updated: 2026-10-26
---

# Glossaire Terraform

## .terraform.lock.hcl
- Définition : Fichier généré par `terraform init` qui fige la version exacte et les empreintes de chaque provider ; il se commite (≈ `package-lock.json`, mais sans les modules).
- Exemple : Le lock de data-platform fige `hashicorp/aws` en 6.69.1 : chaque poste et la CI installent exactement ce provider.
- Alias : lock des providers, lock Terraform
- Carte : cli-lock-provider-commite

## adresse
- Définition : Identifiant d'un objet dans le code et l'état : `type.nom`, préfixé par `module.x` et suivi d'une clé ou d'un index (`["raw"]`, `[0]`).
- Exemple : `module.s3.aws_s3_bucket.this["raw"]` désigne le bucket raw créé par le module s3 ; la renommer sans `moved` recrée le bucket.
- Alias : adresse Terraform, adresse de ressource, adresses
- Carte : langage-hcl-resource-adresse

## apply
- Définition : `terraform apply` : exécute le plan (création, modification, destruction des ressources réelles) après confirmation, puis enregistre le résultat dans l'état.
- Exemple : `make up` lance un `terraform apply` sur l'environnement dev de data-platform.
- Alias : terraform apply
- Carte : cli-apply-confirmation-yes

## backend
- Définition : Endroit où Terraform range l'état et pose son verrou : fichier local par défaut, ou un bucket S3 partagé par l'équipe et la CI.
- Exemple : data-platform range l'état de dev dans un bucket S3, sous la clé `dev/terraform.tfstate`, configurée par `backend.hcl`.
- Alias : backend Terraform, backend S3, backends
- Carte : state-backend-configuration-partielle

## bloc dynamic
- Définition : Bloc qui génère un bloc imbriqué répété par élément d'une collection (`for_each`), à l'intérieur d'une seule ressource.
- Exemple : `dynamic "origin"` crée un bloc `origin` par bucket dans la distribution CloudFront.
- Alias : dynamic, blocs dynamic
- Carte : langage-hcl-dynamic-bloc-facultatif

## bootstrap
- Définition : Petit root Terraform séparé, appliqué une fois par compte, qui crée ce dont l'environnement a besoin avant d'exister : bucket d'état, bucket d'artefacts.
- Exemple : `infra/bootstrap/` crée le bucket d'état de data-platform ; `make down` ne peut pas le détruire.
- Alias : root bootstrap
- Carte : state-backend-bootstrap-oeuf-poule

## contrainte de version
- Définition : Règle qui dit quelles versions sont acceptées (`>= 1.10`, `~> 6.0`) pour Terraform, un provider ou un module ; la version choisie est notée ailleurs (lock).
- Exemple : `~> 6.0` accepte tout provider AWS 6.x mais refuse 7.0.
- Alias : contraintes de version, contrainte
- Carte : cli-lock-provider-commite

## count
- Définition : Méta-argument qui crée N exemplaires d'une ressource ou d'un module, numérotés `[0]`, `[1]`… ; `count = cond ? 1 : 0` la rend facultative.
- Exemple : `count = var.alertes ? 1 : 0` ne crée le module d'alertes que si la variable est vraie.
- Carte : langage-hcl-count-index

## data source
- Définition : Bloc `data` qui lit un objet existant (créé ailleurs) à chaque plan, sans jamais le créer, le modifier ni le détruire.
- Exemple : `data "aws_s3_object"` lit le pointeur `current.json` publié par le script de build des Lambdas.
- Alias : data sources, bloc data, source de données
- Carte : langage-hcl-data-lire-sans-gerer

## default_tags
- Définition : Bloc du provider AWS qui pose les mêmes étiquettes sur toutes les ressources taggables, sans les répéter dans chaque ressource.
- Exemple : data-platform pose `project = "data-platform"` une seule fois dans `infra/providers.tf`.
- Carte : langage-hcl-default-tags

## dépendance implicite
- Définition : Ordre de création que Terraform déduit seul quand un bloc lit l'attribut d'un autre : le bloc lu est créé en premier.
- Exemple : Le module s3 reçoit `module.kms.key_arn` : Terraform crée la clé avant les buckets, sans `depends_on`.
- Alias : dépendances implicites
- Carte : modules-output-dependance

## depends_on
- Définition : Méta-argument qui impose un ordre que Terraform ne peut pas déduire des références ; à réserver aux liens invisibles dans le code.
- Exemple : Une politique de bucket attend le blocage d'accès public par `depends_on`, faute de référence entre les deux.
- Carte : modules-depends-on-module

## dérive
- Définition : Écart entre le code Terraform et la réalité, causé par une modification faite hors Terraform (console, CLI) ; le plan suivant propose de la corriger.
- Exemple : Une rétention de logs changée à la main dans la console revient à sa valeur du code au prochain `make up`.
- Alias : drift
- Carte : cli-derive-hors-terraform

## destroy
- Définition : Commande `terraform destroy` : supprime toutes les ressources suivies par l'état du root, après un plan à confirmer.
- Exemple : `prevent_destroy = true` fait échouer un `terraform destroy` qui viserait la ressource protégée, avant toute suppression.
- Alias : terraform destroy
- Carte : cli-destroy-etat-vide

## état
- Définition : Fichier JSON où Terraform note, pour chaque ressource du code, l'objet réel qui lui correspond (identifiant, attributs) ; il contient aussi les secrets en clair.
- Exemple : L'état de dev de data-platform vit dans un bucket S3 chiffré ; `terraform state list` liste ce qu'il gère.
- Alias : état Terraform, state, tfstate, terraform.tfstate, états
- Carte : state-backend-contenu-etat

## for_each
- Définition : Méta-argument qui crée un exemplaire d'une ressource ou d'un module par clé d'une map ou d'un ensemble, adressé par sa clé (`["raw"]`).
- Exemple : Un `for_each` sur `local.lambdas` crée une fonction par entrée ; retirer une entrée ne touche qu'elle.
- Carte : langage-hcl-for-each-cle

## force_destroy
- Définition : Argument d'un bucket S3 qui autorise Terraform à le vider avant de le supprimer ; sans lui, la destruction d'un bucket non vide échoue.
- Exemple : En dev, `force_destroy = true` laisse `make down` supprimer le bucket raw et ses données.

## graphe de dépendances
- Définition : Ordre calculé par Terraform à partir des références entre blocs : il crée d'abord ce qui est lu, et détruit dans l'ordre inverse.
- Exemple : Deux ressources qui se citent mutuellement forment un cycle : `terraform validate` le refuse (`Error: Cycle`).
- Alias : graphe des dépendances
- Carte : langage-hcl-cycle-dependances

## HCL
- Définition : HashiCorp Configuration Language : le langage déclaratif des fichiers `.tf`, fait de blocs (`resource`, `variable`) et d'expressions.
- Exemple : `resource "aws_s3_bucket" "raw" { bucket = local.prefix }` est un bloc HCL.
- Alias : HashiCorp Configuration Language

## import
- Définition : Rattache à l'état une ressource qui existe déjà sur AWS, sans la recréer : commande `terraform import` ou bloc `import`.
- Exemple : Un état de bootstrap perdu se reconstruit en important le bucket existant ressource par ressource.
- Alias : terraform import, bloc import
- Carte : state-backend-import-existant

## init
- Définition : `terraform init` : prépare un dossier Terraform (backend, providers, modules) ; première commande à lancer, sans risque à relancer.
- Exemple : `make tf-init ENV=dev` lance `init` avec le `backend.hcl` de dev.
- Alias : terraform init
- Carte : cli-init-preparer-dossier

## interpolation
- Définition : Insertion d'une valeur dans une chaîne avec `${…}` (≈ template literal TS) ; `$${` écrit le texte `${` sans l'interpréter.
- Exemple : `"${local.prefix}-raw"` donne `data-platform-dev-raw`.
- Alias : ${…}
- Carte : langage-hcl-dollar-echapper-interpolation

## known after apply
- Définition : Mention du plan pour une valeur que seule la création révélera (identifiant, ARN) ; elle ne peut pas servir de clé de `for_each`.
- Exemple : L'ARN d'une clé KMS encore à créer apparaît `(known after apply)` dans le premier plan.
- Alias : (known after apply), valeur inconnue
- Carte : modules-for-each-cles-connues

## lifecycle
- Définition : Bloc d'une ressource qui règle son cycle de vie : `prevent_destroy`, `create_before_destroy`, `ignore_changes`, préconditions et postconditions.
- Exemple : `lifecycle { prevent_destroy = true }` protège le bucket d'état contre toute destruction par Terraform.
- Alias : bloc lifecycle
- Carte : state-backend-prevent-destroy-portee

## locals
- Définition : Valeurs nommées calculées dans un module (≈ `const` en tête de fichier), lues par `local.nom` ; l'appelant ne peut pas les changer.
- Exemple : `local.prefix` vaut `data-platform-dev` et préfixe tous les noms de ressources.
- Alias : local Terraform, valeur locale
- Carte : langage-hcl-locals-nommer-calcul

## méta-argument
- Définition : Argument que Terraform comprend sur tout bloc `resource` ou `module`, quel que soit le provider : `count`, `for_each`, `depends_on`, `provider`, `lifecycle`.
- Exemple : Un module qui contient son propre bloc `provider` refuse les méta-arguments `count` et `for_each`.
- Alias : méta-arguments
- Carte : modules-provider-interne-legacy

## module Terraform
- Définition : Dossier de fichiers `.tf` appelé par un bloc `module` avec des entrées ; l'appelant ne voit que ses `output` (≈ un fichier TS et ses exports).
- Exemple : `infra/modules/s3-buckets` crée les buckets de data-platform pour chaque environnement.
- Alias : modules Terraform, module enfant, bloc module
- Carte : modules-outputs-seuls-visibles

## moved
- Définition : Bloc qui déclare qu'une adresse a changé (`from` → `to`) : Terraform déplace l'objet dans l'état au lieu de le détruire puis le recréer.
- Exemple : Renommer `module "s3_prod"` en `module "prod"` avec un `moved` garde les buckets et leurs données.
- Alias : bloc moved
- Carte : state-backend-moved-renommer

## output
- Définition : Valeur qu'un module expose à son appelant ou, dans le root, au terminal et aux scripts (`terraform output`).
- Exemple : `terraform -chdir=infra output -json bucket_names` donne les noms réels des buckets de data-platform.
- Alias : outputs, sortie Terraform, sorties Terraform, output Terraform
- Carte : langage-hcl-output-exposer

## plan
- Définition : `terraform plan` : compare le code, l'état et la réalité, puis liste ce que l'apply créerait, modifierait ou détruirait, sans rien toucher.
- Exemple : `make plan` affiche `Plan: 1 to add, 0 to change, 0 to destroy` avant tout déploiement.
- Alias : terraform plan
- Carte : cli-plan-symboles

## prevent_destroy
- Définition : Réglage de `lifecycle` qui fait échouer tout plan qui détruirait la ressource ; il ne protège pas d'une suppression faite hors Terraform.
- Exemple : Le bucket d'état porte `prevent_destroy = true` : un `terraform destroy` lancé par erreur s'arrête.
- Carte : state-backend-prevent-destroy-portee

## provider
- Définition : Plugin qui traduit le code Terraform en appels à l'API d'un service (AWS, GitHub) ; il fournit les types de ressources et de data sources.
- Exemple : `hashicorp/aws` fournit `aws_s3_bucket` et `aws_lambda_function` ; il est configuré une seule fois dans le root.
- Alias : providers, provider AWS
- Carte : modules-providers-herites

## registre Terraform
- Définition : Catalogue public (registry.terraform.io) où se publient et se documentent providers et modules, téléchargés par `init`.
- Exemple : `source = "terraform-aws-modules/s3-bucket/aws"` désigne un module du registre.
- Alias : Terraform Registry, registre
- Carte : modules-source-registre

## removed
- Définition : Bloc qui retire une ressource de l'état ; avec `destroy = false`, l'objet reste sur AWS, Terraform cesse seulement de le gérer.
- Exemple : Déplacer un bucket vers le bootstrap : `removed` dans `infra/`, puis `import` dans le bootstrap.
- Alias : bloc removed
- Carte : state-backend-state-rm-vs-removed

## required_providers
- Définition : Bloc de `terraform {}` qui déclare d'où vient chaque provider (`hashicorp/aws`) et quelles versions sont acceptées.
- Exemple : `aws = { source = "hashicorp/aws", version = "~> 6.0" }` dans le `versions.tf` de data-platform.
- Carte : modules-required-providers

## ressource Terraform
- Définition : Bloc `resource` qui décrit un objet réel que Terraform crée et gère (bucket, rôle, fonction), identifié par son adresse `type.nom`.
- Exemple : `resource "aws_s3_bucket" "raw"` crée le bucket raw de data-platform.
- Alias : ressources Terraform, bloc resource, resource
- Carte : langage-hcl-resource-adresse

## root module
- Définition : Dossier où l'on lance `terraform` : il configure providers et backend, appelle les modules et possède son propre état.
- Exemple : `infra/` est le root de data-platform ; `infra/bootstrap/` en est un second, avec un autre état.
- Alias : root, module racine, roots
- Carte : modules-structure-root-envs

## sensitive
- Définition : Marque une variable ou un output comme secret : la valeur est masquée à l'affichage, mais reste en clair dans l'état.
- Exemple : Un jeton passé en variable `sensitive = true` s'affiche `(sensitive value)` dans le plan.
- Carte : variables-sensitive-contagieux

## source_code_hash
- Définition : Argument d'une fonction Lambda : l'empreinte du zip ; quand elle change, Terraform redéploie le code.
- Exemple : data-platform lit cette empreinte dans le pointeur `current.json` publié avec chaque zip.
- Carte : AWS/lambda-source-code-hash

## splat
- Définition : Expression `[*]` qui lit un attribut sur tous les éléments d'une liste (≈ `.map(x => x.attr)`) ; elle ne parcourt pas une map.
- Exemple : `aws_s3_bucket.export[*].arn` donne la liste des ARN des buckets créés avec `count`.
- Alias : [*]
- Carte : modules-outputs-for-each

## Terraform
- Définition : Outil d'infrastructure as code de HashiCorp : on décrit les ressources cloud dans des fichiers `.tf`, puis `plan` et `apply` les créent ou les alignent.
- Exemple : Toute l'infrastructure AWS de data-platform (buckets, Lambdas, alarmes) est décrite en Terraform sous `infra/`.
- Alias : infrastructure as code, IaC

## terraform_remote_state
- Définition : Data source qui lit les outputs de l'état d'un autre root ; elle exige le droit de lire tout cet état.
- Exemple : Un root applicatif pourrait lire le nom du bucket d'artefacts dans l'état du bootstrap.
- Carte : state-backend-remote-state-outputs

## TF_VAR_
- Définition : Préfixe de variable d'environnement qui donne une valeur à une variable Terraform : `TF_VAR_environment=dev` remplit `var.environment`.
- Exemple : Une CI peut passer la clé du zip à déployer par `TF_VAR_lambda_key`.
- Alias : TF_VAR_x, TF_VAR
- Carte : variables-priorite-sources

## tfplan
- Définition : Fichier écrit par `terraform plan -out=tfplan` : le plan figé, rejoué tel quel par `apply tfplan` ; il contient des valeurs en clair.
- Exemple : Une CI relit le `tfplan` en MR, puis l'applique sans recalculer.
- Alias : fichier de plan, plan sauvé
- Carte : cli-plan-out-fichier

## tfvars
- Définition : Fichier de valeurs de variables Terraform (`nom = valeur`), passé par `-var-file` ou chargé seul s'il s'appelle `terraform.tfvars` ou `*.auto.tfvars`.
- Exemple : `infra/envs/dev/dev.tfvars` porte les valeurs de l'environnement dev.
- Alias : .tfvars, fichier tfvars, *.auto.tfvars
- Carte : variables-auto-tfvars

## validation
- Définition : Bloc d'une variable Terraform qui vérifie sa valeur avant le plan (`condition`, `error_message`) et arrête tout si elle est fausse.
- Exemple : `environment` n'accepte que `dev` ou `prod` : `-var environment=Prod` échoue en une seconde.
- Alias : bloc validation
- Carte : variables-validation-condition

## variable Terraform
- Définition : Entrée typée d'un module (`variable "nom"`), lue par `var.nom`, avec défaut et règles de validation facultatifs (≈ paramètre de fonction).
- Exemple : `var.environment` choisit l'environnement (dev, prod) de data-platform.
- Alias : variables Terraform, variable d'entrée, var.
- Carte : variables-declarer-valider

## verrou d'état
- Définition : Marque posée pendant `plan` et `apply` pour qu'une seule exécution écrive l'état à la fois ; sur S3, un objet `.tflock` (`use_lockfile`).
- Exemple : Un `make plan` lancé pendant un `apply` en cours échoue avec `Error acquiring the state lock`.
- Alias : verrou, state lock, use_lockfile
- Carte : state-backend-use-lockfile

## workspace Terraform
- Définition : Second état rangé sous le même backend, choisi par `terraform workspace select` ; rien dans la commande ne montre lequel est actif.
- Exemple : data-platform préfère une clé d'état par environnement, explicite dans `backend.hcl`, aux workspaces.
- Alias : workspaces Terraform
- Carte : state-backend-workspace-vs-cle
