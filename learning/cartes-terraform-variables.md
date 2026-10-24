---
title: "Cartes · Variables Terraform"
type: cartes
langage: Terraform
cours: Variables
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Variables Terraform
Terraform · Variables : conditions, déclaration, options, types, validation (format spec v3 de revision-pwa).

## 1. variable : déclarer et valider
- Sous-thème : déclaration
- Niveau : 1
- Définition : `variable` déclare une entrée du module, typée, avec défaut et règle `validation` vérifiée avant le plan (≈ paramètre typé + garde).
- Contexte : On la lit avec `var.nom`. Sans `default`, elle est obligatoire : `plan` la demande au clavier, ou échoue avec `-input=false` (`No value for required variable`). La valeur vient de `-var`, d'un `.tfvars` (`envs/dev/dev.tfvars`) ou de `TF_VAR_nom`. `validation` rejette une valeur hors règle avec un message clair, avant tout appel AWS.
- Usage : ✅ ce qui change d'un env à l'autre (`environment`, région, rétention) · ❌ valeur calculée dans le module : `locals` ; secret en clair dans un `.tfvars` commité.

```hcl
# Exemple 1 : déclarer, valider
variable "environment" {
  type    = string
  default = "dev"
  validation {
    condition = contains(
      ["dev", "prod"], var.environment)
    error_message = "dev ou prod."
  }
}
```

```bash
# Exemple 2 : passer la valeur
terraform plan -var environment=prod
# → OK
terraform plan -var environment=qa
# → Error: Invalid value for variable
#   dev ou prod.
```

- Quiz : Avec cette validation, que fait `terraform plan -var environment=Prod` ?
- [ ] OK : `contains` ignore la casse
- [ ] OK : la valeur devient `"prod"`
- [x] `Error: Invalid value for variable`
- [ ] Un `Warning`, puis le plan
- Réponse : `Error: Invalid value for variable` : `contains` compare les chaînes exactement, `"Prod"` n'est pas dans la liste.

## 2. bool : conversion depuis la CLI
- Sous-thème : types
- Niveau : 1
- Définition : `type = bool` impose un booléen ; la chaîne reçue par `-var` ou un `.tfvars` est convertie si Terraform sait la lire.
- Contexte : En ligne de commande, tout arrive sous forme de chaîne : Terraform la convertit vers le type déclaré, ou refuse avec `a bool is required`. Seules quelques écritures passent, en minuscules : `TRUE` est refusé avec le conseil d'écrire `true`. Sans `type`, la variable garde la chaîne `"true"`, et un test `var.actif == true` devient faux.
- Usage : ✅ interrupteur d'option (activer les logs, le versioning) · ❌ plus de deux états (`off`, `lecture`, `complet`) : une `string` validée.

```hcl
# Exemple 1 : un interrupteur typé
variable "actif" {
  type = bool
}
# -var actif=true → true
# -var actif=oui
# → Error: Invalid value for input
#   variable: a bool is required.
```

```hcl
# Exemple 2 : activer une ressource
resource "aws_s3_bucket" "logs" {
  count  = var.actif ? 1 : 0
  bucket = "data-platform-dev-logs"
}
# actif = false → 0 instance
```

- Quiz : Que vaut `var.actif` avec `-var actif=1` ?
- [ ] `Error: a bool is required`
- [x] `true`
- [ ] `"1"`
- [ ] `false`
- Réponse : `true` : `"1"` et `"0"` font partie des chaînes que Terraform convertit en booléen.

## 3. number : le SIREN qui perd son zéro
- Sous-thème : types
- Niveau : 1
- Définition : `type = number` convertit la valeur reçue en nombre, sans garder sa forme d'origine (zéros de tête, format d'écriture).
- Contexte : Un `number` Terraform est une valeur, pas un texte : `012345678` devient `12345678`, sans erreur ni avertissement. Un identifiant qui ressemble à un nombre (SIREN, code postal, ID de compte AWS à 12 chiffres qui peut commencer par 0) se type donc `string`, validé par un `regex`. `number` est réservé aux quantités : rétention en jours, taille, nombre de réplicas.
- Usage : ✅ quantité qu'on compare ou calcule (`expiration_days`) · ❌ identifiant (SIREN, compte AWS, code postal) : `string` + `validation`.

```hcl
# Exemple 1 : le zéro de tête disparaît
variable "siren" {
  type = number
}
# -var siren=012345678
# → 12345678 (8 chiffres !)
```

```hcl
# Exemple 2 : le bon type
variable "siren" {
  type = string
}
output "siren" {
  value = var.siren
}
# -var siren=012345678
# → siren = "012345678"
```

- Quiz : Avec `type = number`, que vaut `var.capital` pour `-var capital=1e3` ?
- [ ] `"1e3"`
- [ ] `Error: a number is required`
- [ ] `1`
- [x] `1000`
- Réponse : `1000` : la notation scientifique est lue comme un nombre ; seule la valeur compte, pas l'écriture.

## 4. set : ni ordre ni doublon
- Sous-thème : types
- Niveau : 1
- Définition : `set(string)` est une collection sans doublon ni ordre (≈ `Set<string>` en TS), affichée triée.
- Contexte : Les doublons d'une valeur reçue disparaissent à la conversion, sans erreur. L'affichage trié ne garantit rien au code. Un set se parcourt avec `for`, se teste avec `contains`, se convertit avec `tolist`. C'est le type naturel d'une entrée destinée à `for_each`, qui refuse les listes.
- Usage : ✅ liste de noms uniques à passer à `for_each` (buckets, tribunaux) · ❌ ordre ou position significatifs : `list`.

```hcl
# Exemple 1 : doublon retiré, tri
variable "tribunaux" {
  type    = set(string)
  default = ["Paris", "Lyon", "Paris"]
}
# var.tribunaux
# → ["Lyon", "Paris"]
```

```hcl
# Exemple 2 : lire un set
locals {
  t      = var.tribunaux
  a_lyon = contains(local.t, "Lyon")
  liste  = tolist(local.t)
}
# local.a_lyon → true
```

- Quiz : Avec ce set, que donne `var.tribunaux[0]` ?
- [ ] `"Lyon"`
- [ ] `"Paris"`
- [ ] `null`
- [x] `Error: Invalid index`
- Réponse : `Error: Invalid index` : un set n'a pas d'index ; passer par `tolist()` ou une boucle `for`.

## 5. object : un schéma d'attributs
- Sous-thème : types
- Niveau : 1
- Définition : `object({...})` fixe les attributs attendus et leur type (≈ une `interface` TS) ; la valeur reçue est convertie vers ce schéma.
- Contexte : Contrairement à TS, un attribut en trop ne lève pas d'erreur : il est retiré en silence à la conversion, et une faute de frappe (`nmo` pour `nom`) passe inaperçue. Chaque attribut est lu par `var.x.attr`. Un objet regroupe des réglages liés d'un bucket ou d'un env en une seule entrée.
- Usage : ✅ réglages structurés (`{ nom, jours, versioning }`) passés à un module · ❌ nombre de clés variable : `map(object(…))`.

```hcl
# Exemple 1 : l'excédent disparaît
variable "entreprise" {
  type = object({ siren = string })
  default = { siren = "483609327",
              nom   = "ACME" }
}
# var.entreprise
# → { siren = "483609327" }
```

```hcl
# Exemple 2 : lire un attribut
variable "bucket" {
  type = object({
    nom   = string
    jours = number
  })
  default = { nom = "raw", jours = 30 }
}
# var.bucket.jours → 30
```

- Quiz : Que fait le `plan` avec `object({ siren = string, nom = string })` et `default = { siren = "483609327" }` ?
- [x] `Error: attribute "nom" is required`
- [ ] `nom` vaut `null`
- [ ] `nom` vaut `""`
- [ ] OK, `nom` est simplement absent
- Réponse : `Error: attribute "nom" is required` : l'excédent est jeté en silence, mais un attribut manquant bloque, sauf s'il est `optional`.

## 6. optional : défaut d'attribut
- Sous-thème : types
- Niveau : 1
- Définition : `optional(type, défaut)` rend un attribut d'objet facultatif et lui donne une valeur quand il manque (≈ `actif?: boolean = true`).
- Contexte : Sans `optional`, l'appelant doit fournir tous les attributs de l'objet. Le défaut s'écrit dans le type, attribut par attribut, et pas dans le `default` de la variable, qui ne sert que si la variable entière manque. Pratique pour un module qui reçoit une liste d'objets où seuls quelques champs changent.
- Usage : ✅ objets de configuration aux réglages facultatifs (`versioning`, `jours`) · ❌ attribut toujours requis : le laisser obligatoire.

```hcl
# Exemple 1 : attribut absent → défaut
variable "entreprise" {
  type = object({
    siren = string
    actif = optional(bool, true)
  })
  default = { siren = "483609327" }
}
# var.entreprise.actif → true
```

- Quiz : Que vaut `var.entreprise.actif` si l'appelant écrit explicitement `actif = null` ?
- [ ] `null`
- [ ] `false`
- [x] `true`
- [ ] `Error: attribute "actif" is required`
- Réponse : `true` : pour un attribut `optional`, `null` est remplacé par le défaut, comme une absence.

## 7. validation : condition booléenne
- Sous-thème : validation
- Niveau : 1
- Définition : Un bloc `validation` vérifie la valeur d'une variable avant le plan ; si `condition` est faux, `error_message` s'affiche.
- Contexte : La règle est évaluée dès que la valeur est connue, avant tout appel AWS : une faute de saisie échoue en une seconde. `error_message` accepte l'interpolation, utile pour rappeler la valeur reçue. Le message s'affiche sous `Error: Invalid value for variable`, avec la valeur fautive. La condition doit renvoyer un vrai booléen.
- Usage : ✅ liste fermée (`dev`, `prod`), format (SIREN, compte AWS), bornes (rétention) · ❌ règle qui dépend d'une ressource créée à l'apply : `precondition` ou `postcondition`.

```hcl
# Exemple 1 : liste fermée
variable "env" {
  type = string
  validation {
    condition = contains(
      ["dev", "prod"], var.env)
    error_message = "env ${var.env} inconnu."
  }
}
# -var env=staging
# → Error: Invalid value for variable
#   env staging inconnu.
```

- Quiz : Que fait `condition = regex("^[0-9]{9}$", var.siren)` avec un SIREN valide ?
- [ ] OK : `regex` vaut `true`
- [x] `Error: Invalid variable validation result`
- [ ] OK : une chaîne non vide passe
- [ ] Le message `error_message` s'affiche
- Réponse : `Error: Invalid variable validation result` : `regex` renvoie la chaîne trouvée, pas un booléen ; l'envelopper dans `can()`.

## 8. Ternaire : conversion silencieuse
- Sous-thème : conditions
- Niveau : 1
- Définition : `cond ? a : b` choisit une valeur selon une condition ; Terraform convertit `a` et `b` vers un type commun avant de choisir.
- Contexte : Le type du résultat est fixé avant l'évaluation de la condition, à partir des deux branches. Si elles diffèrent, Terraform cherche une conversion qui les réunit ; la branche choisie arrive donc parfois dans un autre type que celui écrit. Le ternaire sert surtout à moduler une valeur par env ou à rendre une ressource facultative avec `count`.
- Usage : ✅ valeur qui dépend de l'env (réplicas, rétention), `count = cond ? 1 : 0` · ❌ plus de deux cas : `map` indexée par env.

```hcl
# Exemple 1 : valeur selon l'env
variable "env" {
  default = "prod"
}
output "replicas" {
  value = var.env == "prod" ? 3 : 1
}
# → replicas = 3
```

- Quiz : Que vaut l'output si tu écris `var.env == "prod" ? 3 : "1"` ?
- [ ] `3`
- [x] `"3"`
- [ ] `Error: Inconsistent conditional result types`
- [ ] `"1"`
- Réponse : `"3"` (chaîne) : le type commun de `number` et `string` est `string`, même la branche choisie est convertie.

## 9. sensitive : contagieux jusqu'aux outputs
- Sous-thème : options
- Niveau : 1
- Définition : `sensitive = true` masque la valeur d'une variable dans le plan et marque comme sensible toute expression qui en dérive.
- Contexte : Le marquage se propage : un local, un argument ou un output calculé à partir de la variable devient sensible à son tour. Un output racine qui contient une valeur sensible doit le confirmer avec `sensitive = true`, sinon le plan échoue. Le masque ne chiffre rien : la valeur reste en clair dans le state.
- Usage : ✅ mot de passe, jeton d'API passés en variable · ❌ protéger vraiment un secret : Secrets Manager, lu à l'exécution par la Lambda.

```hcl
# Exemple 1 : variable et output masqués
variable "db_password" {
  type      = string
  sensitive = true
}
output "pwd" {
  value     = var.db_password
  sensitive = true
}
# plan → pwd = (sensitive value)
```

- Quiz : Que fait le `plan` avec `output "l" { value = length(var.db_password) }`, sans `sensitive` ?
- [ ] `l = 6`
- [ ] `l = (sensitive value)`
- [x] `Error: Output refers to sensitive values`
- [ ] `l = null`
- Réponse : `Error: Output refers to sensitive values` : `length` d'une valeur sensible est sensible aussi, et un output racine doit le déclarer.

## 10. variable : qui gagne ?
- Sous-thème : déclaration
- Niveau : 2
- Définition : Une variable peut venir du défaut, de `TF_VAR_x`, de `terraform.tfvars`, de `*.auto.tfvars`, de `-var-file` ou de `-var` ; la plus prioritaire gagne.
- Contexte : `terraform.tfvars` et `*.auto.tfvars` sont chargés sans rien demander ; `-var` et `-var-file` passent après eux, dans l'ordre de la ligne de commande : le dernier gagne. Le défaut ne sert qu'en l'absence de toute autre source. Dans data-platform, chaque env a son fichier (`envs/dev/dev.tfvars`) passé par le Makefile selon `ENV`, pour qu'aucun fichier racine ne s'applique à tous les envs.
- Usage : ✅ un `.tfvars` par env passé explicitement, `-var` pour une surcharge ponctuelle · ❌ un `terraform.tfvars` racine partagé par tous les envs.

```bash
# Exemple 1 : le dernier argument gagne
# prod.tfvars : environment = "prod"
terraform plan \
  -var environment=dev \
  -var-file=prod.tfvars
# → environment = "prod"
```

```bash
# Exemple 2 : ordre inversé
terraform plan \
  -var-file=prod.tfvars \
  -var environment=dev
# → environment = "dev"
```

- Quiz : `TF_VAR_environment=prod` est exporté, `terraform.tfvars` contient `"dev"`, aucune option : quelle valeur ?
- [ ] `"prod"`
- [x] `"dev"`
- [ ] La valeur du `default`
- Réponse : `"dev"` : `terraform.tfvars` passe avant les variables d'environnement `TF_VAR_*`, qui ne battent que le défaut.

## 11. optional sans défaut : null
- Sous-thème : types
- Niveau : 2
- Définition : `optional(type)` sans second argument laisse l'attribut à `null` quand il manque, pas à une valeur vide.
- Contexte : Un attribut `optional(string)` absent vaut `null`, jamais `""` : contrairement à TS, il n'y a pas d'`undefined` distinct. `null` passé à un argument de ressource revient à ne pas l'écrire (le provider prend son défaut), mais beaucoup de fonctions le refusent. Tester `!= null` avant usage, ou donner un défaut dans `optional`.
- Usage : ✅ attribut vraiment facultatif transmis tel quel à une ressource · ❌ attribut passé à une fonction (`upper`, `length`) : `optional(string, "")`.

```hcl
# Exemple 1 : absent → null
variable "entreprise" {
  type = object({
    siren = string
    ville = optional(string)
  })
  default = { siren = "483609327" }
}
# var.entreprise.ville → null
```

```hcl
# Exemple 2 : tester avant d'utiliser
locals {
  v     = var.entreprise.ville
  ville = local.v != null ? local.v : "?"
}
# local.ville → "?"
```

- Quiz : Que donne `upper(var.entreprise.ville)` quand `ville` est absent ?
- [ ] `""`
- [ ] `null`
- [x] `Error: Invalid function argument`
- [ ] `"NULL"`
- Réponse : `Error: Invalid function argument` : `upper` refuse `null` (argument must not be null) ; défaut `optional(string, "")` ou test `!= null`.

## 12. list(any) : un seul type d'élément
- Sous-thème : types
- Niveau : 2
- Définition : `any` laisse Terraform déduire le type de la valeur reçue ; dans `list(any)`, il choisit un type commun unique pour tous les éléments.
- Contexte : `any` n'est pas le `any` de TS : ce n'est pas « tout est permis », c'est « devine le type ». Seul, `type = any` garde la valeur telle quelle, même un mélange (un tuple). Dans un conteneur, `list(any)` impose un seul type d'élément : Terraform cherche une conversion commune, ou échoue si aucune n'existe.
- Usage : ✅ module générique qui transmet une valeur sans la lire · ❌ entrée qu'on lit champ par champ : type explicite (`list(object(…))`).

```hcl
# Exemple 1 : any garde le mélange
variable "x" {
  type    = any
  default = [1, "a"]
}
output "x" {
  value = var.x
}
# → x = [1, "a"]  (tuple gardé)
```

- Quiz : Que vaut `var.x` avec `type = list(any)` et le même défaut `[1, "a"]` ?
- [ ] `[1, "a"]`
- [x] `["1", "a"]`
- [ ] `Error: Invalid default value`
- [ ] `[1]`
- Réponse : `["1", "a"]` : une liste a un seul type d'élément, `1` est converti en `string`, le type commun.

## 13. nullable = false : null interdit
- Sous-thème : options
- Niveau : 2
- Définition : `nullable = false` empêche `null` d'arriver dans la variable : un `null` reçu est remplacé par le défaut.
- Contexte : Par défaut, une variable accepte `null` comme valeur à part entière, même si elle a un `default` : passer `null` n'est pas « ne rien passer ». Avec `nullable = false`, le code du module n'a plus à tester `null`. Utile quand l'appelant transmet une valeur calculée, peut-être `null`, venue d'une autre variable.
- Usage : ✅ variable de module avec défaut, que le code lit sans test `null` · ❌ variable où `null` veut dire « laisser le provider choisir » : garder `nullable = true`.

```hcl
# Exemple 1 : null → défaut
# module m
variable "env" {
  default  = "dev"
  nullable = false
}
# appelant
module "m" {
  source = "./m"
  env    = null
}
# var.env → "dev"
```

- Quiz : Que fait le `plan` si `env` a `nullable = false` mais aucun `default`, et que l'appelant passe `null` ?
- [ ] `var.env` vaut `null`
- [ ] `var.env` vaut `""`
- [x] `Error: Required variable not set`
- [ ] `plan` demande la valeur au clavier
- Réponse : `Error: Required variable not set` (`required variable may not be set to null`) : sans défaut, il n'y a rien pour remplacer `null`.

## 14. can(regex) : ancrer le motif
- Sous-thème : validation
- Niveau : 2
- Définition : `can(regex(motif, v))` vaut `true` si le motif trouve une correspondance, `false` sinon : la forme standard d'une validation de format.
- Contexte : `regex` échoue quand rien ne correspond ; `can` transforme cet échec en `false`, ce que `condition` attend. Le motif suit la syntaxe RE2 (pas de lookahead). Les accolades d'une répétition (`{9}`) n'entrent pas en conflit avec l'interpolation `${…}`, qui exige un `$` devant.
- Usage : ✅ format d'identifiant (SIREN, compte AWS, nom de bucket) · ❌ liste fermée de valeurs : `contains`, plus lisible.

```hcl
# Exemple 1 : 9 chiffres exactement
variable "siren" {
  type = string
  validation {
    condition = can(regex(
      "^[0-9]{9}$", var.siren))
    error_message = "SIREN = 9 chiffres."
  }
}
# -var siren=48360932
# → Error: … SIREN = 9 chiffres.
```

- Quiz : Que vaut `can(regex("[0-9]{9}", "A483609327Z"))` ?
- [x] `true`
- [ ] `false`
- [ ] `Error: Error in function call`
- [ ] `"483609327"`
- Réponse : `true` : sans `^` et `$`, `regex` cherche une sous-chaîne ; seul le motif ancré valide la valeur entière.

## 15. Plusieurs validation : toutes évaluées
- Sous-thème : validation
- Niveau : 2
- Définition : Une variable peut porter plusieurs blocs `validation`, un par règle, chacun avec son message dédié.
- Contexte : Découper une règle complexe en plusieurs blocs donne un message précis pour chaque cas, au lieu d'un « valeur invalide » générique. L'ordre des blocs n'a pas d'importance. Chaque message est suivi de l'emplacement de la règle (`checked by the validation rule at main.tf:3,3`), utile pour retrouver laquelle a échoué.
- Usage : ✅ plusieurs contraintes indépendantes (longueur, caractères, préfixe) · ❌ une seule règle simple : un bloc suffit.

```hcl
# Exemple 1 : une règle par bloc
variable "siren" {
  type = string
  validation {
    condition = length(var.siren) == 9
    error_message = "9 caractères."
  }
  validation {
    condition = can(tonumber(var.siren))
    error_message = "chiffres seulement."
  }
}
```

- Quiz : Combien d'erreurs affiche le `plan` avec `-var siren=ABC` ?
- [ ] Une : il s'arrête au premier échec
- [x] Deux, une par bloc
- [ ] Une seule, qui fusionne les messages
- [ ] Aucune : `tonumber` fait planter
- Réponse : Deux : chaque bloc est évalué, Terraform ne s'arrête pas au premier échec et liste les deux messages.

## 16. alltrue : la liste vide passe
- Sous-thème : validation
- Niveau : 2
- Définition : `alltrue([for … : cond])` vérifie une règle sur chaque élément d'une liste (≈ `arr.every(...)` en TS).
- Contexte : Une `validation` ne s'écrit pas en boucle : on fabrique une liste de booléens avec `for`, puis `alltrue` les réunit. `anytrue` est l'équivalent de `.some()`. Le message ne dit pas quel élément échoue : pour le montrer, construire la liste des fautifs dans `error_message`. Les deux fonctions acceptent aussi des chaînes `"true"`/`"false"`.
- Usage : ✅ valider chaque SIREN d'une liste, chaque nom de bucket · ❌ règle sur la liste entière (taille, doublons) : `length`, `distinct`.

```hcl
# Exemple 1 : chaque élément
variable "sirens" {
  type = list(string)
  validation {
    condition = alltrue([
      for s in var.sirens :
      length(s) == 9
    ])
    error_message = "9 chiffres."
  }
}
# ["48360932"] → Error: … 9 chiffres.
```

- Quiz : Que fait le `plan` avec `-var 'sirens=[]'` ?
- [ ] `Error: … 9 chiffres.`
- [ ] `Error: Invalid function argument`
- [x] Il passe sans erreur
- [ ] `Error: list must not be empty`
- Réponse : Il passe : `alltrue([])` vaut `true` (comme `[].every()`) ; ajouter `length(var.sirens) > 0` pour exiger un élément.

## 17. coalesce : vide ≠ null
- Sous-thème : conditions
- Niveau : 2
- Définition : `coalesce(a, b, …)` renvoie le premier argument ni `null` ni chaîne vide (≈ `a || b` pour des chaînes, pas `a ?? b`).
- Contexte : `coalesce` sert de valeur de repli pour une entrée facultative. Il saute `null` **et** `""`, ce qui le rapproche de `||` en JS. Pour un repli sur `null` seulement, écrire un ternaire `v != null ? v : repli`. Tous les arguments sont convertis vers un type commun ; s'ils sont tous vides, `coalesce` échoue.
- Usage : ✅ repli pour une chaîne facultative (nom, ville, suffixe) · ❌ `""` est une valeur voulue : ternaire sur `null`.

```hcl
# Exemple 1 : repli sur null
variable "ville" {
  type    = string
  default = null
}
output "v" {
  value = coalesce(var.ville, "AUCUNE")
}
# → v = "AUCUNE"
```

- Quiz : Avec `-var ville=`, que valent `coalesce(var.ville, "AUCUNE")` puis `var.ville != null ? var.ville : "AUCUNE"` ?
- [ ] `""` puis `""`
- [ ] `"AUCUNE"` puis `"AUCUNE"`
- [ ] `""` puis `"AUCUNE"`
- [x] `"AUCUNE"` puis `""`
- Réponse : `"AUCUNE"` puis `""` : `coalesce` saute aussi la chaîne vide, le ternaire ne teste que `null`.

## 18. precondition : avant l'action
- Sous-thème : conditions
- Niveau : 2
- Définition : `precondition` dans `lifecycle` vérifie une hypothèse avant de créer ou modifier une ressource, et bloque le plan si elle est fausse.
- Contexte : Contrairement à `validation`, liée à une seule entrée, une `precondition` vit à côté de la ressource qu'elle protège et peut combiner variables, locals et attributs d'autres ressources. Si une valeur n'est connue qu'à l'apply, le contrôle est repoussé à l'apply. L'échec affiche `Resource precondition failed` suivi du message.
- Usage : ✅ hypothèse propre à une ressource (rétention minimale du bucket de prod, région attendue) · ❌ contrôle d'une seule entrée : `validation` sur la variable.

```hcl
# Exemple 1 : rétention minimale
resource "terraform_data" "raw" {
  input = var.retention
  lifecycle {
    precondition {
      condition = var.retention >= 30
      error_message = "30 j min."
    }
  }
}
# -var retention=7
# → Error: Resource precondition failed
```

- Quiz : Hors d'une ressource, où peut-on aussi poser un bloc `precondition` ?
- [ ] Dans un bloc `variable`
- [x] Dans un bloc `output`
- [ ] Dans un bloc `locals`
- [ ] Dans un bloc `provider`
- Réponse : Dans un `output` (et une data source) : un échec donne `Module output value precondition failed`.

## 19. tfvars : *.auto.tfvars chargé seul
- Sous-thème : déclaration
- Niveau : 2
- Définition : Terraform charge seul `terraform.tfvars` et tout `*.auto.tfvars` du root ; un autre fichier de valeurs exige `-var-file`.
- Contexte : Le bootstrap lit l'account id dans `local.auto.tfvars`, gitignoré : `apply` le trouve sans option, et rien de propre au compte n'est commité (un `.example` sert de modèle). Le root `infra/` fait l'inverse : `dev.tfvars` et `local.tfvars` sont passés par `-var-file` dans le Makefile, car les valeurs d'un environnement ne doivent pas être chargées partout. En cas de conflit, `-var` et `-var-file` l'emportent sur les fichiers `auto`.
- Usage : ✅ `*.auto.tfvars` pour un root à un seul jeu de valeurs (bootstrap) · ❌ `auto` dans un root multi-environnement : les valeurs de dev seraient chargées en prod.

```bash
# Exemple 1 : chargé sans option
cat infra/bootstrap/local.auto.tfvars
# account_id = "<12 chiffres>"
terraform -chdir=infra/bootstrap plan
# → account_id lu tout seul
```

```bash
# Exemple 2 : nom libre = -var-file
terraform -chdir=infra plan \
  -var-file=envs/dev/dev.tfvars \
  -var-file=envs/dev/local.tfvars
```

- Quiz : `local.auto.tfvars` est renommé `local.tfvars` : que fait `terraform plan -input=false` dans le bootstrap ?
- [ ] Même résultat : le fichier est lu
- [ ] Il prend `account_id = null`
- [ ] Il lit `local.tfvars` après les `auto`
- [x] `Error: No value for required variable`
- Réponse : `No value for required variable` : seuls `terraform.tfvars` et `*.auto.tfvars` sont chargés d'office ; sinon `-var-file=local.tfvars`.

## 20. null dans une condition
- Sous-thème : validation
- Niveau : 3
- Définition : Une variable `default = null` doit être testée avant tout appel de fonction ; `||` court-circuite et protège le reste.
- Contexte : Une condition de validation est une expression comme une autre : si elle échoue (fonction appelée sur `null`), Terraform affiche une erreur technique au lieu de `error_message`. En 1.14, `||` et `&&` court-circuitent : avec `var.x == null || …`, le côté droit n'est pas évalué si la variable est nulle. Les anciennes versions évaluaient les deux côtés, d'où des `try` ou des ternaires dans du code plus ancien.
- Usage : ✅ variable facultative (`default = null`) validée seulement quand elle est fournie · ❌ variable obligatoire : pas de `default`, pas de test `null`.

```hcl
# Exemple 1 : tester null d'abord
variable "sirens" {
  type    = list(string)
  default = null
  validation {
    condition = (var.sirens == null
      || length(var.sirens) > 0)
    error_message = "au moins un."
  }
}
# sans -var → OK
```

- Quiz : Que fait le `plan`, sans `-var`, si la condition est seulement `length(var.sirens) > 0` ?
- [ ] OK : `length(null)` vaut `0`
- [ ] `Error: … au moins un.`
- [x] `Error: Invalid function argument`
- [ ] OK : la validation est sautée pour `null`
- Réponse : `Error: Invalid function argument` : `length(null)` échoue avant même que `error_message` puisse s'afficher.

## 21. validation croisée
- Sous-thème : validation
- Niveau : 3
- Définition : La `condition` d'une validation peut lire d'autres variables pour imposer une règle entre plusieurs entrées.
- Contexte : Avant Terraform 1.9, une validation ne pouvait lire que sa propre variable, et les règles entre entrées passaient par une `precondition`. Désormais, elle peut citer d'autres variables, des locals, et même des objets du module. Une règle « si prod alors… » s'écrit avec `||` : non-prod passe, prod doit respecter la contrainte.
- Usage : ✅ règle qui lie deux entrées (rétention minimale en prod, taille selon l'env) · ❌ règle sur le résultat d'une ressource : `postcondition`.

```hcl
# Exemple 1 : contrainte en prod seulement
variable "env" { type = string }

variable "retention" {
  type = number
  validation {
    condition = (var.env != "prod"
      || var.retention >= 30)
    error_message = "prod : 30 j min."
  }
}
# env=prod retention=7 → Error
```

- Quiz : En 1.14, la condition peut-elle lire `terraform_data.raw.input`, un attribut de ressource ?
- [x] Oui, comme tout objet du module
- [ ] Non : seulement `var.<elle-même>`
- [ ] Non : seulement des variables
- [ ] Oui, mais seulement à l'apply
- Réponse : Oui : depuis 1.9, une validation peut citer d'autres objets du module ; une valeur connue au plan est vérifiée dès le plan.

## 22. postcondition : après coup
- Sous-thème : conditions
- Niveau : 3
- Définition : `postcondition` vérifie le résultat d'une ressource via `self` ; si la valeur n'est connue qu'après création, le contrôle a lieu à l'apply.
- Contexte : `self` désigne l'objet tel que le provider le renvoie, avec ses attributs calculés (ARN, ID, `output`). Une postcondition garantit à ce qui en dépend une propriété du résultat : si elle échoue, l'apply s'arrête là et les ressources dépendantes ne sont pas traitées. Elle sert aussi sur une data source, pour vérifier ce qu'on a lu.
- Usage : ✅ vérifier un attribut calculé (chiffrement actif, région du bucket lu) · ❌ contrôle d'une entrée : `validation` ; simple alerte : `check`.

```hcl
# Exemple 1 : vérifier le résultat
resource "terraform_data" "raw" {
  input = "data-platform-dev-raw"
  lifecycle {
    postcondition {
      condition = (
        length(self.output) <= 10)
      error_message = "nom trop long."
    }
  }
}
# plan → OK (output inconnu au plan)
# apply → Error: Resource
#   postcondition failed
```

- Quiz : Après cet échec à l'`apply`, la ressource existe-t-elle ?
- [ ] Non : l'apply est annulé
- [ ] Non : Terraform la détruit aussitôt
- [x] Oui, et elle est dans le state
- [ ] Oui, mais hors du state
- Réponse : Oui : elle est créée et enregistrée dans le state ; la postcondition échoue après coup, elle n'annule rien.

## 23. check : avertir sans bloquer
- Sous-thème : conditions
- Niveau : 3
- Définition : Un bloc `check` porte des `assert` évalués à chaque plan et apply, hors de tout cycle de vie de ressource.
- Contexte : `check` sert à la surveillance continue : une hypothèse sur l'infra qui peut dériver (nom, certificat, endpoint qui répond via une data source locale au bloc). Il est évalué en dernier, après les ressources, et ne bloque jamais rien. Contrairement à `precondition`, il n'empêche ni la création ni la suite du plan.
- Usage : ✅ vérification de santé ou de convention (suffixe, tag présent) qu'on veut voir sans bloquer · ❌ règle à faire respecter : `validation` ou `precondition`.

```hcl
# Exemple 1 : une convention de nom
resource "terraform_data" "raw" {
  input = "data-platform-dev-raw"
}
check "nom_bucket" {
  assert {
    condition = endswith(
      terraform_data.raw.input, "-raw")
    error_message = "suffixe -raw."
  }
}
# plan → OK, rien affiché
```

- Quiz : Que fait `apply` si l'assertion d'un `check` est fausse ?
- [ ] `Error: Check block assertion failed`
- [x] Il applique, avec `Warning: Check block assertion failed`
- [ ] Il s'arrête avant les ressources
- [ ] Il détruit la ressource contrôlée
- Réponse : Il applique quand même : `Warning: Check block assertion failed`, jamais une erreur, contrairement à `precondition`.
