---
title: "Cartes · CLI Terraform"
type: cartes
langage: Terraform
cours: CLI
created: 2026-10-24
updated: 2026-10-25
---

# Cartes · CLI Terraform
Terraform · CLI : apply, contrôle, global, init, plan, sorties (format spec v3 de revision-pwa).

## 1. init : préparer le dossier
- Sous-thème : init
- Niveau : 1
- Définition : `terraform init` configure le backend, installe modules et providers dans `.terraform/` et écrit `.terraform.lock.hcl` : la première commande de tout root.
- Contexte : Rien ne marche avant : `validate`, `plan` et `console` lisent ce que `init` a installé, pas le code directement. Il se relance sans risque (idempotent) et il le faut après tout changement de backend, de module ou de provider. `.terraform/` est local et gitignoré ; le lock, lui, se commite. `-input=false` évite toute question en CI.
- Usage : ✅ après un clone, un `git pull` qui touche `versions.tf` ou un `module`, un changement d'environnement (`make tf-init ENV=…`) · ❌ supprimer `.terraform/` pour « nettoyer » : `init` suffit.

```bash
# Exemple 1 : ce qu'init prépare
terraform -chdir=infra init -input=false \
  -backend-config=envs/dev/backend.hcl
# → Initializing the backend...
#   Initializing modules...
#   - s3 in modules/s3-buckets
#   - Installing hashicorp/aws v6.69.1...
#   Terraform has been successfully
#   initialized!
```

- Quiz : Un `git pull` ajoute le provider `hashicorp/random` dans `versions.tf` : que fait `plan` sans `init` ?
- [ ] Il télécharge `random` au passage
- [ ] Il planifie, `random` sera installé à l'apply
- [x] `Error: Inconsistent dependency lock file`
- [ ] Il ignore les ressources `random_*`
- Réponse : `Inconsistent dependency lock file` (mesuré) : `random` est exigé mais aucune version n'est choisie dans le lock ; seul `init` en choisit une.

## 2. fmt : le style canonique
- Sous-thème : contrôle
- Niveau : 1
- Définition : `terraform fmt` réécrit les fichiers au style canonique (indentation, `=` alignés) ; `-check` ne modifie rien et sort en erreur s'il y a à reformater.
- Contexte : Comme Prettier, il supprime les débats de style et les diffs parasites. Sans `-recursive`, il ne traite que le dossier courant : `modules/` reste intact. `-check` liste les fichiers fautifs et sort avec le code 3, ce qui fait échouer un job de CI ; `-diff` montre la correction.
- Usage : ✅ `fmt -recursive` avant chaque commit, `fmt -check -recursive` en CI ou en hook pre-commit · ❌ corriger l'indentation à la main : `fmt` le fait sans erreur.

```bash
# Exemple 1 : vérifier sans toucher
terraform fmt -check -recursive
# → main.tf
#   modules/s3/main.tf
echo $?          # → 3
terraform fmt -recursive   # corrige
terraform fmt -check -recursive
echo $?          # → 0
```

```bash
# Exemple 2 : voir la correction
terraform fmt -check -diff main.tf
# -input="x"
# +  input = "x"
```

- Quiz : `dev.tfvars` et `backend.hcl` sont mal indentés : lesquels `fmt -check -recursive` signale-t-il ?
- [ ] Les deux
- [x] `dev.tfvars` seulement
- [ ] `backend.hcl` seulement
- [ ] Aucun : seuls les `.tf` comptent
- Réponse : `dev.tfvars` seulement (mesuré) : `fmt` traite `.tf`, `.tfvars` et `.tftest.hcl` ; un `.hcl` de configuration de backend lui est invisible.

## 3. validate : cohérence, pas valeurs
- Sous-thème : contrôle
- Niveau : 1
- Définition : `terraform validate` vérifie la syntaxe, les types, les références et les arguments requis, sans état, sans AWS et sans valeurs de variables.
- Contexte : Il répond « ce code peut-il fonctionner ? », pas « fonctionnera-t-il avec dev.tfvars ? ». Une référence à une ressource inexistante ou un argument manquant échouent ; une valeur de variable hors de ses `validation` passe, car `validate` n'accepte ni `-var` ni `-var-file`. C'est le contrôle rapide de CI, avant `plan` qui, lui, évalue les valeurs.
- Usage : ✅ premier job de CI, après `fmt -check`, avec `init -backend=false` · ❌ s'en contenter : seul `plan` vérifie les valeurs, l'état et l'API AWS.

```bash
# Exemple 1 : une référence cassée
# input = terraform_data.c.id
terraform validate
# → Error: Reference to undeclared
#   resource
```

```bash
# Exemple 2 : pas de -var-file
terraform validate -var-file=dev.tfvars
# → Error: Failed to parse
#   command-line flags
#   flag provided but not defined:
#   -var-file
```

- Quiz : `staging.tfvars` contient `environment = "staging"`, refusé par la `validation` (dev ou prod). Quelle commande échoue ?
- [ ] `terraform validate`
- [x] `terraform plan -var-file=staging.tfvars`
- [ ] Les deux
- [ ] Aucune : `validation` ne s'exécute qu'à l'apply
- Réponse : `plan` (`Invalid value for variable`, mesuré) : `validate` ne lit aucune valeur et passe ; la `validation` s'évalue dès que les valeurs sont connues.

## 4. plan : lire les symboles
- Sous-thème : plan
- Niveau : 1
- Définition : Chaque ressource du plan porte un symbole : `+` créer, `~` modifier en place, `-` détruire, `-/+` remplacer, `<=` lire une data source.
- Contexte : `-/+` est le symbole à guetter : l'objet est détruit puis recréé (un bucket renommé perd ses données). `+/-` fait l'inverse, avec `create_before_destroy`. Dans le détail, `# forces replacement` désigne l'argument responsable, et `(known after apply)` une valeur que seul l'apply connaîtra. La ligne `Plan:` résume en ajouts, modifications et destructions.
- Usage : ✅ relire chaque `-/+` et chaque `-` avant l'apply, en MR · ❌ lire seulement la ligne `Plan:` : elle ne dit pas quoi est détruit.

```bash
# Exemple 1 : les trois actions (mesuré)
terraform plan -var v=b
# ~ resource "terraform_data" "upd"
#   ~ input = "a" -> "b"
# -/+ resource "terraform_data" "rep"
#   ~ triggers_replace = "a" -> "b"
# +/- resource "terraform_data" "cbd"
#   (create_before_destroy)
```

- Quiz : Le plan ne contient qu'un seul `-/+`. Que dit la ligne de résumé ?
- [ ] `0 to add, 1 to change, 0 to destroy`
- [x] `1 to add, 0 to change, 1 to destroy`
- [ ] `1 to replace`
- [ ] `0 to add, 0 to change, 1 to destroy`
- Réponse : `1 to add, 0 to change, 1 to destroy` (mesuré avec `-replace`) : un remplacement compte comme une création et une destruction.

## 5. apply : yes, et rien d'autre
- Sous-thème : apply
- Niveau : 1
- Définition : `terraform apply` recalcule le plan, l'affiche et n'exécute qu'après la saisie exacte de `yes` ; `-auto-approve` saute la question.
- Contexte : Entre l'affichage et la réponse, rien n'est encore écrit. En CI, sans clavier, `apply` échoue (`error asking for approval: EOF`) : on y applique un fichier de plan déjà relu (`apply tfplan`, sans question), ou `-auto-approve`. Chaque apply écrit l'état, même partiellement si une ressource échoue au milieu.
- Usage : ✅ `apply` interactif sur un poste, `apply tfplan` en CI · ❌ `-auto-approve` sur une prod sans plan relu juste avant.

```bash
# Exemple 1 : confirmer
terraform apply
# Do you want to perform these
#   actions?
#   Enter a value: yes
# → Apply complete! Resources:
#   0 added, 1 changed, 0 destroyed.
```

```bash
# Exemple 2 : sans clavier (CI)
terraform apply -input=false
# → Error: error asking for approval:
#   EOF
```

- Quiz : À la question, tu tapes `y` puis Entrée : que se passe-t-il ?
- [ ] L'apply démarre
- [ ] La question est reposée
- [x] `Apply cancelled.`
- [ ] Erreur, l'état est verrouillé
- Réponse : `Apply cancelled.` (mesuré, code de sortie 1) : seul `yes` exact est accepté (« Only 'yes' will be accepted to approve »).

## 6. -chdir : lancer depuis la racine
- Sous-thème : global
- Niveau : 1
- Définition : `terraform -chdir=infra plan` exécute la commande comme si on était dans `infra/` : option globale, placée avant la sous-commande.
- Contexte : Les Makefiles de data-platform et revision-pwa s'en servent (`TF = terraform -chdir=infra`) pour tout lancer depuis la racine du dépôt, sans `cd` qui ne survivrait pas à la ligne. Placée après la sous-commande, elle est refusée (`flag provided but not defined: -chdir`). Tous les chemins relatifs de la commande (`-var-file`, `-out`, `-backend-config`) partent alors de `infra/`.
- Usage : ✅ Makefile, CI, scripts lancés depuis la racine · ❌ `cd infra && terraform …` dans une recette Make multi-lignes : chaque ligne repart de la racine.

```makefile
# Exemple 1 : la variable des Makefiles
TF = terraform -chdir=infra

plan:
	$(TF) plan -var-file=envs/$(ENV)/$(ENV).tfvars
```

```bash
# Exemple 2 : après la commande, refusé
terraform plan -chdir=infra
# → Error: Failed to parse
#   command-line flags
#   flag provided but not defined:
#   -chdir
```

- Quiz : Depuis la racine : `terraform -chdir=infra plan -var-file=infra/envs/dev/dev.tfvars`. Résultat ?
- [ ] Plan normal : le chemin part de la racine
- [x] `Given variables file … does not exist`
- [ ] `-var-file` est ignoré, plan sans valeurs
- [ ] Terraform corrige le chemin en double
- Réponse : fichier introuvable (mesuré) : avec `-chdir`, les chemins relatifs partent de `infra/` ; il faut `-var-file=envs/dev/dev.tfvars`.

## 7. console : tester une expression
- Sous-thème : sorties
- Niveau : 1
- Définition : `terraform console` évalue des expressions HCL avec les fonctions, variables, locals et l'état du root : le REPL de Terraform (≈ `node`).
- Contexte : On y met au point un `for`, un `merge` ou une regex avant de l'écrire dans le code, et on y lit `local.prefix` ou un attribut de l'état. Il faut un root initialisé. En pipe (`echo 'expr' | terraform console`), il répond une fois et sort, pratique dans un script. Il ne modifie jamais l'infra.
- Usage : ✅ mettre au point une expression, vérifier un `local` calculé, lire un attribut d'état · ❌ chercher la valeur d'un output appliqué : `terraform output`.

```bash
# Exemple 1 : une expression en pipe
echo 'upper("raw")' | terraform console
# → "RAW"
E='[for n in ["raw","logs"] : "dp-${n}"]'
echo "$E" | terraform console
# → ["dp-raw", "dp-logs"]
# une ligne par expression en pipe
```

- Quiz : `variable "env"` n'a ni défaut ni valeur passée : que répond la console à `var.env` ?
- [ ] Elle demande la valeur au clavier
- [ ] `null`
- [x] `(known after apply)`
- [ ] `Error: No value for required variable`
- Réponse : `(known after apply)` (mesuré) : la console traite une variable sans valeur comme inconnue au lieu d'échouer ; passer `-var` ou `-var-file` pour la voir.

## 8. output -json : listes et maps pour jq
- Sous-thème : sorties
- Niveau : 1
- Définition : `terraform output -json` écrit les sorties en JSON, chacune enveloppée dans `{value, type, sensitive}` : le format pour `jq` et les scripts.
- Contexte : `-raw` ne sait sortir qu'une chaîne, un nombre ou un booléen ; une map de buckets passe par `-json`. Avec un nom (`output -json bucket_names`), on obtient la valeur seule. Attention : `-json` et `output <nom>` affichent les valeurs `sensitive` en clair, alors que la liste simple les masque (`<sensitive>`).
- Usage : ✅ boucle shell sur les buckets d'un module, script Python qui lit les sorties · ❌ une seule chaîne pour une variable shell : `-raw`, sans `jq`.

```bash
# Exemple 1 : la valeur d'une map
terraform output -json bucket_names \
  | jq -r .raw
# → data-platform-dev-raw
terraform output -json | jq -c .token
# → {"sensitive":true,"type":"string",
#    "value":"s3cr3t"}   (en clair)
```

- Quiz : Sans nom : `terraform output -json | jq -r '.bucket_names.raw'` affiche ?
- [ ] `data-platform-dev-raw`
- [x] `null`
- [ ] Une erreur de `jq`
- [ ] `"data-platform-dev-raw"`
- Réponse : `null` (mesuré) : sans nom, chaque sortie est enveloppée ; le chemin est `.bucket_names.value.raw`.

## 9. plan -out : appliquer le plan relu
- Sous-thème : plan
- Niveau : 2
- Source : data-platform · S1-04
- Définition : `plan -out=tfplan` enregistre le plan dans un fichier ; `apply tfplan` exécute exactement ces actions, sans recalculer ni redemander.
- Contexte : `apply` seul recalcule un plan et attend `yes` : entre la relecture et la confirmation, le code ou l'infra ont pu bouger. Le fichier fige les actions avec la configuration du moment : c'est ce qu'on relit en MR et ce que la CI rejoue (`plan` en artefact, `apply tfplan` ensuite). Si l'état a changé depuis (autre apply), Terraform refuse : `Saved plan is stale`.
- Usage : ✅ CI (plan en MR, apply du même fichier), audit du plan JSON avant l'apply (`show -json`) · ❌ garder un `tfplan` d'hier : périmé ; le commiter : il contient les valeurs en clair.

```bash
# Exemple 1 : planifier, appliquer, rejouer
terraform plan -out=tfplan
# → Saved the plan to: tfplan
terraform apply tfplan
# → Apply complete! (aucune question)
terraform apply tfplan
# → Error: Saved plan is stale
```

```bash
# Exemple 2 : auditer avant l'apply
make plan   # data-platform
# terraform plan -out=tfplan …
# terraform show -json tfplan \
#   | uv run infra/scripts/check_tags.py
# → 11 ressources taggables auditées,
#   32 ignorées, 0 violation(s)
```

- Quiz : Après `plan -out=tfplan` avec `input = "v1"`, le code passe à `"v2"` : que pose `apply tfplan` ?
- [x] `"v1"` : la valeur du plan enregistré
- [ ] `"v2"` : la valeur du code actuel
- [ ] Rien : `Error: Saved plan is stale`
- [ ] `"v2"`, après une nouvelle confirmation
- Réponse : `"v1"` : le fichier embarque la configuration du moment du plan ; le `plan` suivant propose `"v1" -> "v2"` (mesuré avec `terraform_data`).

## 10. dérive : la console contre le code
- Sous-thème : plan
- Niveau : 2
- Source : data-platform · S1-04
- Définition : Une modification faite hors Terraform (console, CLI) est une dérive : `plan` la détecte en relisant AWS, `apply` remet la valeur du code.
- Contexte : Avant de planifier, Terraform rafraîchit l'état : il relit chaque ressource qu'il connaît et compare au code. Un attribut écrit dans le code et changé à la main revient à sa valeur au prochain `apply`. Un tag `managed_by = terraform` n'empêche rien : c'est une étiquette ; le vrai verrou est un `Deny` IAM ou une SCP. `plan -refresh-only` montre la dérive seule.
- Usage : ✅ toute modification par le code (MR, puis `make up`), la console pour regarder · ❌ corriger en console « en urgence » : le prochain `make up` l'écrase.

```bash
# Exemple 1 : raw passé à 60 j en console
make plan
# → Note: Objects have changed outside
#   of Terraform
#   ~ days = 60 -> 90
make up
# → raw revient à 90 jours
```

```bash
# Exemple 2 : voir la dérive seule
terraform -chdir=infra plan -refresh-only \
  -var-file=envs/dev/dev.tfvars \
  -var-file=envs/dev/local.tfvars
# → les écarts, aucune action prévue
# apply -refresh-only : les inscrit
#   dans l'état, sans toucher AWS
```

- Quiz : Un bucket `data-platform-dev-tmp` créé à la main avec les tags du projet : que montre `make plan` ?
- [ ] Sa destruction : il est absent du code
- [ ] Une dérive à corriger
- [x] Rien : `No changes.`
- [ ] Une proposition d'`import`
- Réponse : rien : Terraform ne relit que les ressources de son état ; un objet créé à la main lui est invisible (le reprendre par `import`).

## 11. destroy : l'état survit, vide
- Sous-thème : apply
- Niveau : 2
- Source : data-platform · S1-04
- Définition : `terraform destroy` supprime toutes les ressources de l'état, dans l'ordre inverse des dépendances, puis réécrit l'état vide.
- Contexte : Le graphe est parcouru à l'envers : politiques avant rôles, logging avant buckets. L'état n'est pas une ressource : il reste, avec `resources: []`, la même `lineage` et un `serial` plus grand ; le bucket d'état, géré par le bootstrap, est hors périmètre. Les data sources ne sont ni créées ni détruites, mais `state list` les compte.
- Usage : ✅ environnement jetable (`make down` le vendredi), preuve que tout est décrit par le code · ❌ en prod : `prevent_destroy` sur les données, jamais `-auto-approve`.

```bash
# Exemple 1 : l'état après destroy
terraform destroy -auto-approve
# → Destroy complete! Resources: 1 destroyed.
jq -c '{serial, lineage, resources}' \
  terraform.tfstate
# → {"serial":6,"lineage":"4218…",
#    "resources":[]}
```

```bash
# Exemple 2 : compter juste
make down
# → Resources: 43 destroyed.
make up
# → Resources: 43 added.
terraform -chdir=infra state list | wc -l
# → 53 : 43 ressources + 10 data sources
```

- Quiz : `force_destroy = true` ajouté au code d'un bucket non vide, puis `make down` sans `make up` avant : résultat ?
- [ ] Le bucket est vidé puis supprimé
- [x] `BucketNotEmpty` : l'état a encore `false`
- [ ] `destroy` applique d'abord l'argument
- [ ] Le bucket sort de l'état, laissé sur AWS
- Réponse : `BucketNotEmpty` : `destroy` supprime avec les valeurs de l'état, pas du code ; `force_destroy` doit d'abord passer par un `apply`.

## 12. init -upgrade : monter les versions
- Sous-thème : init
- Niveau : 2
- Définition : `terraform init -upgrade` choisit la plus récente version de chaque provider et module qui respecte les contraintes, puis réécrit le lock.
- Contexte : Sans `-upgrade`, `init` réutilise la version du lock (« Reusing previous version… from the dependency lock file »), même si une version plus récente est permise. Élargir une contrainte ne suffit donc pas : il faut `-upgrade`. La montée se fait en MR : lock modifié, plan relu, `No changes.` attendu.
- Usage : ✅ montée volontaire de provider ou de module, en MR avec le lock · ❌ `-upgrade` dans chaque job de CI : chaque pipeline peut prendre une version différente.

```bash
# Exemple 1 : la montée (null, mesuré)
# version = "~> 3.1" ; lock : 3.1.1
terraform init -upgrade
# → Finding hashicorp/null versions
#   matching "~> 3.1"...
#   Installing hashicorp/null v3.3.2...
grep version .terraform.lock.hcl
# → version = "3.3.2"
```

- Quiz : Lock en 3.1.1 sous `~> 3.1.0`. Tu élargis à `~> 3.1` et lances `init` sans `-upgrade` : version installée ?
- [x] 3.1.1, celle du lock
- [ ] 3.3.2, la plus récente permise
- [ ] Erreur : le lock ne correspond plus
- [ ] 3.1.0, le plancher de la contrainte
- Réponse : 3.1.1 (mesuré, « Reusing previous version ») : le lock respecte encore la nouvelle contrainte, donc `init` le garde.

## 13. .terraform.lock.hcl : se commite
- Sous-thème : init
- Niveau : 2
- Définition : `.terraform.lock.hcl` fige la version exacte et les hashes de chaque provider : commité, il garantit le même provider sur chaque poste et en CI.
- Contexte : La contrainte (`~> 6.0`) dit ce qui est permis, le lock ce qui est choisi (`6.69.1`) ; c'est le `package-lock.json` de Terraform. Il ne couvre que les providers, pas les modules. Si une contrainte resserrée exclut la version verrouillée, `init` refuse au lieu de descendre en silence. Le fichier est généré : on ne l'édite pas, `init` et `providers lock` l'écrivent.
- Usage : ✅ commiter le lock avec le code, le relire en MR quand il change · ❌ le mettre dans `.gitignore` comme `.terraform/` : chaque clone choisirait sa version.

```hcl
# Exemple 1 : le lock de data-platform
provider "registry.terraform.io/hashicorp/aws" {
  version     = "6.69.1"
  constraints = "~> 6.0"
  hashes = [
    "h1:P8yFqjGg6/8HbZOY0qtFSKm9…",
    "zh:0ad1319a9fea21dacf084152…",
  ]
}
```

- Quiz : Lock en 3.3.2 ; tu resserres la contrainte à `~> 3.1.0`. Que fait `terraform init` ?
- [ ] Descend en 3.1.x automatiquement
- [ ] Garde 3.3.2 avec un avertissement
- [x] Erreur : le lock ne respecte plus la contrainte
- [ ] Supprime le lock et repart de zéro
- Réponse : erreur (`locked provider … 3.3.2 does not match configured version constraint ~> 3.1.0`, mesuré) : il faut `init -upgrade` pour choisir à nouveau.

## 14. providers : qui exige quoi
- Sous-thème : init
- Niveau : 2
- Définition : `terraform providers` affiche l'arbre des providers exigés par le root et chaque module, avec leurs contraintes : le diagnostic d'un conflit de versions.
- Contexte : Quand `init` échoue sur `no available releases match the given constraints`, l'erreur cite les contraintes mais pas leur auteur : l'arbre montre quel module impose quoi. Un module sans contrainte apparaît sans version. La commande lit la configuration et les modules installés, donc demande un `init` préalable des modules.
- Usage : ✅ conflit de contraintes entre root et modules, audit avant une montée de provider · ❌ connaître la version installée : `terraform version` ou le lock.

```bash
# Exemple 1 : root + module (mesuré)
terraform providers
# Providers required by configuration:
# .
# ├── provider[registry.terraform.io/
# │     hashicorp/aws] ~> 6.0
# └── module.b
#     └── provider[registry.terraform.io/
#           hashicorp/aws]
```

- Quiz : Juste après un `git clone`, sans `init`, que fait `terraform providers` sur un root qui appelle un module local ?
- [ ] Affiche l'arbre, lu dans le code
- [ ] Affiche le root seul, sans le module
- [x] `Error: Module not installed`
- [ ] Lance `init` puis affiche l'arbre
- Réponse : `Module not installed` (mesuré) : même un module local doit être enregistré par `init` avant d'être lu.

## 15. -replace : forcer une recréation
- Sous-thème : plan
- Niveau : 2
- Définition : `plan -replace=adresse` (ou `apply -replace=…`) prévoit de détruire et recréer une ressource dont le code n'a pas changé ; remplace `terraform taint`.
- Contexte : Utile pour un objet abîmé que Terraform croit à jour (instance corrompue, clé à régénérer). Contrairement à `taint`, déprécié, qui modifiait l'état tout de suite, `-replace` passe par le plan : on le relit avant. Il respecte les garde-fous : sur une ressource `prevent_destroy`, le plan échoue (`Instance cannot be destroyed`). L'adresse suit la syntaxe de l'état (`'module.s3.aws_s3_bucket.this["raw"]'`).
- Usage : ✅ recréer un objet dégradé ou un secret à faire tourner, après relecture du plan · ❌ corriger une dérive d'attribut : un `apply` normal la rétablit sans recréer.

```bash
# Exemple 1 : rien n'a changé, on force
terraform plan \
  -replace=terraform_data.upd
# → # terraform_data.upd will be
#   replaced, as requested
# -/+ resource "terraform_data" "upd"
```

- Quiz : Faute de frappe : `-replace=terraform_data.updd`, adresse inexistante. Que dit `plan` ?
- [ ] `Error: Invalid replace address`
- [ ] Il recrée toutes les ressources du type
- [x] `No changes.`, sans erreur
- [ ] Il propose de créer `updd`
- Réponse : `No changes.` (mesuré) : une adresse `-replace` qui ne correspond à rien est ignorée en silence ; vérifier que le plan annonce bien `will be replaced`.

## 16. -detailed-exitcode : y a-t-il des changements ?
- Sous-thème : plan
- Niveau : 2
- Définition : `plan -detailed-exitcode` sort avec 0 (rien à faire), 1 (erreur) ou 2 (changements prévus) : la CI sait si l'infra a dérivé.
- Contexte : Sans l'option, `plan` sort avec 0 qu'il y ait des changements ou non : un job ne peut pas distinguer « à jour » de « à appliquer ». Avec, un job planifié détecte la dérive ou conditionne l'apply. Piège : le 2 est un code d'échec pour le shell, donc pour `set -e` et pour GitLab CI, qui marque le job en échec sans traitement du code.
- Usage : ✅ job planifié de détection de dérive, porte « rien à appliquer » avant un apply · ❌ un `plan -detailed-exitcode` brut dans un script : capturer le code, `|| rc=$?`.

```bash
# Exemple 1 : les trois codes (mesuré)
terraform plan -detailed-exitcode
echo $?   # → 2 : changements prévus
terraform apply -auto-approve
terraform plan -detailed-exitcode
echo $?   # → 0 : à jour
# erreur de code → 1
```

```yaml
# Exemple 2 : dans .gitlab-ci.yml
drift:
  script:
    - rc=0
    - terraform plan -detailed-exitcode || rc=$?
    - if [ "$rc" = 2 ]; then echo "dérive"; fi
    - test "$rc" != 1
```

- Quiz : Sans `-detailed-exitcode`, quel code de sortie donne un `plan` qui prévoit 3 modifications ?
- [x] 0
- [ ] 2
- [ ] 1
- [ ] 3
- Réponse : 0 (mesuré) : un plan réussi sort toujours avec 0 ; seule l'option distingue « changements » (2) de « rien à faire » (0).

## 17. show : relire l'état ou un plan
- Sous-thème : plan
- Niveau : 2
- Définition : `terraform show` affiche l'état courant ; `show tfplan` un plan enregistré, et `show -json tfplan` sa version JSON pour un script.
- Contexte : Le fichier `tfplan` n'est pas lisible tel quel : c'est une archive binaire, que seul `show` décode avec le même root initialisé. En JSON, `.resource_changes[]` donne pour chaque adresse ses `change.actions` (`create`, `update`, `delete`, `no-op`) : c'est ce que lit le contrôle de tags de data-platform. Le JSON contient les valeurs, `sensitive` comprises.
- Usage : ✅ audit automatique d'un plan en CI (tags, destructions interdites), relecture d'un plan avant `apply tfplan` · ❌ lire une seule valeur de l'état : `state show adresse` ou `output`.

```bash
# Exemple 1 : les actions d'un plan
terraform plan -out=tfplan
terraform show -json tfplan | jq -r \
  '.resource_changes[]
   | select(.change.actions != ["no-op"])
   | .address'
# → terraform_data.logs
```

- Quiz : Que contient le fichier `tfplan` produit par `plan -out=tfplan` ?
- [ ] Le texte du plan, tel qu'affiché
- [ ] Le JSON de `show -json`
- [x] Une archive zip : plan, état, code, lock
- [ ] La liste des adresses à modifier
- Réponse : une archive zip (mesuré, `unzip -l` : `tfplan`, `tfstate`, `tfconfig/`, `.terraform.lock.hcl`) : d'où un plan rejouable seul, et des secrets dedans.

## 18. providers schema : lister ressources et attributs
- Sous-thème : init
- Niveau : 2
- Source : data-platform · S1-08
- Définition : `terraform providers schema -json` sort le schéma des providers installés : toutes les ressources, data sources et attributs, sans aller sur le registre.
- Contexte : Pratique pour retrouver un nom (`grep '^aws_lambda_'`), vérifier qu'un attribut existe dans **la version installée** du provider, ou lire ses descriptions. Le schéma vient du dossier `.terraform/` : sans `terraform init`, la commande ne plante pas, elle renvoie un schéma vide. Sortie volumineuse (plusieurs Mo pour AWS) : toujours la filtrer avec `jq`.
- Usage : ✅ chercher une ressource ou un attribut, vérifier un argument avant de l'écrire · ❌ lire la sortie brute : `jq` sur `.provider_schemas[].resource_schemas`.

```bash
# Exemple 1 : les ressources Lambda
terraform -chdir=infra providers \
  schema -json | jq -r \
  '.provider_schemas[].resource_schemas
   | keys[]' | grep '^aws_lambda_'
# → aws_lambda_alias
#   aws_lambda_event_source_mapping
#   aws_lambda_function
#   aws_lambda_function_event_invoke_config
#   … (16 au total)
```

```bash
# Exemple 2 : les attributs d'une ressource
terraform -chdir=infra providers \
  schema -json | jq -r '.provider_schemas[]
  .resource_schemas
  .aws_lambda_function_event_invoke_config
  .block.attributes | keys[]'
# → function_name, id,
#   maximum_event_age_in_seconds,
#   maximum_retry_attempts, qualifier,
#   region
```

- Quiz : Dans un dossier jamais initialisé, que renvoie `terraform providers schema -json` ?
- [ ] Une erreur : `terraform init` requis
- [x] `{"format_version":"1.0"}` : un schéma vide
- [ ] Le schéma téléchargé depuis le registre
- [ ] Le schéma de la dernière version d'AWS
- Réponse : un schéma vide (mesuré) : sans provider installé dans `.terraform/`, il n'y a rien à décrire, et aucune erreur n'avertit.

## 19. -target : les dépendances suivent
- Sous-thème : plan
- Niveau : 3
- Définition : `plan -target=adresse` limite le plan à cette ressource et à tout ce dont elle dépend ; le reste est ignoré, avec un avertissement.
- Contexte : Terraform ajoute les dépendances (ce que la cible lit), sinon il ne pourrait pas la créer ; il n'ajoute pas les ressources qui dépendent d'elle. Le plan est donc partiel : l'état diverge du code jusqu'au prochain plan complet (`Resource targeting is in effect`). Pratique pour débloquer un apply, dangereux comme habitude.
- Usage : ✅ sortir d'une impasse (créer d'abord une ressource dont dépend un `for_each`), un cas ponctuel · ❌ déploiement de routine par morceaux : un plan complet, ou des roots séparés.

```bash
# Exemple 1 : raw lit kms (mesuré)
terraform plan -target=terraform_data.raw
# → terraform_data.kms will be created
#   terraform_data.raw will be created
# Plan: 2 to add, 0 to change, 0 to destroy.
# Warning: Resource targeting is in effect
```

- Quiz : Même code (raw lit `kms.output`) : que planifie `-target=terraform_data.kms` ?
- [ ] `kms` et `raw`
- [x] `kms` seulement
- [ ] Les trois ressources du root
- [ ] Rien : une cible ne peut pas avoir de dépendants
- Réponse : `kms` seulement (mesuré, `1 to add`) : `-target` ajoute ce dont la cible dépend, jamais ce qui dépend d'elle.

## 20. providers lock : hashes multi-plateformes
- Sous-thème : init
- Niveau : 3
- Définition : `terraform providers lock -platform=linux_amd64 -platform=darwin_arm64` ajoute au lock les hashes `h1:` de chaque plateforme, sans rien installer.
- Contexte : `init` sur un Mac n'écrit que le `h1:` de sa plateforme, plus des `zh:` (zips publiés par le registre). Depuis le registre, une CI Linux vérifie avec ces `zh:` ; mais un miroir ou un cache de plugins (`TF_PLUGIN_CACHE_DIR`) ne vérifie que les `h1:` (doc), d'où des échecs sur un runner d'une autre plateforme. La commande complète le lock, elle n'efface pas les hashes déjà présents.
- Usage : ✅ équipe sur Mac Intel, Mac ARM et CI Linux, avec cache ou miroir de providers · ❌ la relancer à chaque `init` : seulement quand la version ou les plateformes changent.

```bash
# Exemple 1 : deux providers (mesuré)
grep -c 'h1:' .terraform.lock.hcl
# → 2 : un par provider (darwin)
terraform providers lock \
  -platform=linux_amd64 \
  -platform=darwin_arm64 \
  -platform=darwin_amd64
grep -c 'h1:' .terraform.lock.hcl
# → 6 : 2 providers × 3 plateformes
```

- Quiz : Sur un Mac Intel, `providers lock -platform=linux_amd64` seul : que deviennent les `h1:` darwin du lock ?
- [ ] Remplacés par ceux de Linux
- [x] Gardés, ceux de Linux s'ajoutent
- [ ] Supprimés, Linux seul reste
- [ ] Refusé : la plateforme courante manque
- Réponse : gardés (mesuré : 2 → 4 `h1:`) : `providers lock` fusionne avec le lock existant pour la même version.

## 21. TF_LOG : journal de débogage
- Sous-thème : global
- Niveau : 3
- Définition : `TF_LOG=DEBUG` (ou `TRACE`, `INFO`…) fait écrire à Terraform son journal interne sur stderr ; `TF_LOG_PATH` l'envoie dans un fichier.
- Contexte : Le journal montre les appels au provider et à l'API AWS : utile pour une erreur opaque (`AccessDenied` sans détail, verrou). Il va sur stderr : `$(terraform output -raw x)` reste propre. Un niveau inconnu (`TF_LOG=verbose`) retombe sur `TRACE`, le plus bavard. `TF_LOG_PROVIDER` et `TF_LOG_CORE` séparent provider et cœur. Le journal peut contenir des données sensibles.
- Usage : ✅ diagnostiquer un échec d'API ou de verrou, joindre un journal à un ticket · ❌ le laisser actif en CI : journaux énormes, données sensibles dans les artefacts.

```bash
# Exemple 1 : journal dans un fichier
TF_LOG=DEBUG TF_LOG_PATH=/tmp/tf.log \
  terraform plan
grep -c DEBUG /tmp/tf.log
# lignes « [DEBUG] … » horodatées
```

- Quiz : `TF_LOG_PATH=/tmp/tf.log terraform plan`, sans `TF_LOG` : que contient `/tmp/tf.log` ?
- [ ] Le journal au niveau `INFO`
- [ ] Le journal complet, niveau `TRACE`
- [x] Rien : fichier vide
- [ ] La sortie du plan
- Réponse : rien (mesuré : 0 octet) : `TF_LOG_PATH` choisit seulement la destination ; sans `TF_LOG`, aucun journal n'est produit.
