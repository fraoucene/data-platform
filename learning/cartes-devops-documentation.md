---
title: "Cartes · Documentation"
type: cartes
langage: DevOps
cours: Documentation
created: 2026-10-25
updated: 2026-10-25
---

# Cartes · Documentation
DevOps · Documentation : tester, readme, config, agents, sécurité (format spec v3 de revision-pwa).

## 1. clone neuf : le test d'une doc
- Sous-thème : tester
- Niveau : 1
- Source : data-platform · S1-09
- Définition : Tester une doc, c'est cloner le dépôt dans un dossier vide et suivre le README mot pour mot, sans rien deviner.
- Contexte : Sur ton poste, tout marche : `.venv` déjà rempli, fichiers gitignorés présents, profils AWS configurés. Un clone neuf n'a que ce qui est commité. Chaque endroit où il faut « savoir » quelque chose qui n'est pas écrit est un bug de la doc, au même titre qu'un test rouge. Mesuré ici : le README disait `uv sync`, et `make check` échouait dans le clone.
- Usage : ✅ avant de livrer un README, après un gros changement de structure, à l'arrivée d'un nouveau · ❌ relire la doc depuis son propre dossier de travail : les implicites y sont invisibles.

```bash
# Exemple 1 : un clone local suffit
git clone -q . /tmp/clone
cd /tmp/clone
uv sync -q          # ce que dit le README
make check
# → 4 errors : ModuleNotFoundError
#   No module named 'ingest_bodacc'
```

- Quiz : Le clone est fait depuis le dossier local (`git clone .`), pas depuis GitHub. Que manque-t-il au test ?
- [ ] Rien : c'est le même contenu
- [x] Les commits non poussés y sont, pas sur GitHub
- [ ] Les fichiers gitignorés y sont copiés
- [ ] Le `.venv` est copié avec
- Réponse : un clone local inclut les commits non poussés : un inconnu qui clone GitHub peut ne pas les avoir ; les fichiers ignorés et le `.venv`, eux, ne sont jamais copiés.

## 2. README racine : quatre questions, dans l'ordre
- Sous-thème : readme
- Niveau : 1
- Source : data-platform · S1-09
- Définition : Un README de dépôt répond dans l'ordre à : c'est quoi, il me faut quoi, comment je démarre de zéro, quelles commandes au quotidien.
- Contexte : Le lecteur arrive avec une seule question : « est-ce que je peux le faire tourner ? ». L'architecture en quelques lignes lui donne la carte, les prérequis lui évitent d'échouer à l'étape 3, le démarrage numéroté suit l'ordre réel des dépendances. Les décisions et le détail vont dans `docs/` et les README des dossiers.
- Usage : ✅ dépôt d'application ou d'infrastructure, partagé ou repris · ❌ README-journal qui raconte l'historique du projet : mettre l'historique dans les commits et les ADR.

```markdown
# Exemple 1 : le squelette
# data-platform
Plateforme data serverless (BODACC → S3).

## Architecture      (10 lignes, un schéma)
## Prérequis         (outils + versions)
## Démarrer de zéro  (1. 2. 3. …)
## Au quotidien      (make check, replay…)
```

- Quiz : Où mettre « pourquoi Scheduler plutôt qu'une règle EventBridge » ?
- [ ] En tête du README racine
- [x] Dans `docs/` ou le README du dossier concerné
- [ ] Dans le message de commit uniquement
- [ ] Dans `AGENTS.md`
- Réponse : dans `docs/` ou le README du dossier : c'est une décision, pas une étape de démarrage ; le README racine pointe vers elle.

## 3. .example : le modèle commité du fichier ignoré
- Sous-thème : config
- Niveau : 1
- Source : data-platform · S1-09
- Définition : Un fichier `x.example` commité montre la forme d'un fichier de config gitignoré, avec des valeurs factices : `cp x.example x`, puis on remplit.
- Contexte : `local.tfvars`, `backend.hcl` ou `.env` contiennent un numéro de compte, un email ou un secret : ils ne doivent pas être commités. Sans modèle, l'inconnu ne connaît ni les clés ni le format. Le `.example` utilise des valeurs de doc (`123456789012`, `prenom.nom@example.com`) et le `.gitignore` le réautorise (`!*.tfvars.example`). La doc dit quand et comment le copier.
- Usage : ✅ tout fichier de config gitignoré nécessaire au démarrage · ❌ un vrai identifiant dans le `.example`, ou un `.example` que le README ne mentionne pas.

```bash
# Exemple 1 : ignoré, mais pas le modèle
git check-ignore -v \
  infra/envs/dev/local.tfvars
# → .gitignore:275:infra/envs/*/local.tfvars
git check-ignore \
  infra/envs/dev/local.tfvars.example
echo $?   # → 1 : non ignoré, commité
```

```bash
# Exemple 2 : le démarrage
cp infra/envs/dev/local.tfvars.example \
   infra/envs/dev/local.tfvars
# puis : profile, account_id, alert_email
```

- Quiz : Le `.gitignore` ne contient que `*.tfvars`. `local.tfvars.example` est-il ignoré ?
- [ ] Oui : il contient `.tfvars`
- [x] Non : le motif doit finir le nom
- [ ] Oui, sauf à la racine
- [ ] Seulement s'il est vide
- Réponse : non (mesuré, `git check-ignore` → code 1) : `*.tfvars` exige que le nom se termine par `.tfvars` ; la négation `!*.tfvars.example` ne sert que face à un motif plus large comme `*.tfvars*`.

## 4. commande documentée : la cible du projet
- Sous-thème : readme
- Niveau : 1
- Source : data-platform · S1-09
- Définition : La doc donne la commande du projet (`make sync`), pas l'outil brut (`uv sync`) : la cible porte les options choisies.
- Contexte : `make sync` lance `uv sync --all-packages` ; `uv sync` seul n'installe que le graphe de la racine, sans les membres non cités (la Lambda). Écrire l'outil brut dans le README contourne ce choix : le clone neuf échoue alors que le poste de l'auteur, synchronisé par `make`, passe. Une seule source de vérité : le Makefile ; le README la cite.
- Usage : ✅ toute commande qui a une cible (`make check`, `make plan`, `make replay`) · ❌ recopier dans le README la ligne de la recette : elle divergera au prochain changement.

```bash
# Exemple 1 : mesuré dans un clone neuf
uv sync -q && make check
# → 4 errors (ingest_bodacc absent)
make sync && make check
# → 103 passed, 1 skipped
```

- Quiz : Le Makefile passe de `uv sync --all-packages` à `uv sync --all-packages --locked`. Que faut-il changer au README qui dit `make sync` ?
- [x] Rien
- [ ] Ajouter `--locked` dans le README
- [ ] Remplacer par la commande uv complète
- Réponse : rien : le README cite la cible, pas sa recette ; c'est tout l'intérêt de passer par `make`.

## 5. résultat attendu : sous chaque commande
- Sous-thème : readme
- Niveau : 1
- Source : data-platform · S1-09
- Définition : Chaque commande d'une doc de démarrage est suivie de ce qu'on doit voir : `Success!`, `No changes`, `103 passed`, un ARN.
- Contexte : Sans résultat attendu, l'inconnu ne sait pas si une commande a marché : un `make up` qui finit sans erreur mais crée un abonnement `PendingConfirmation` a l'air réussi. Le résultat attendu transforme chaque étape en test : identique → on continue, différent → on s'arrête là, au bon endroit, au lieu de découvrir l'échec trois étapes plus loin.
- Usage : ✅ démarrage, procédure de rejeu ou d'incident, runbook · ❌ sortie complète collée (100 lignes de plan) : une ligne caractéristique suffit.

```bash
# Exemple 1 : commande + attendu
make tf-validate
# → Success! The configuration is valid.
make plan
# → Plan: N to add, 0 to change, 0 to destroy.
```

- Quiz : Pour l'étape « confirmer l'abonnement email », quel attendu écrire ?
- [ ] « Un mail est reçu »
- [x] `list-subscriptions-by-topic` → un ARN, pas `PendingConfirmation`
- [ ] `make up` sans erreur
- [ ] Le topic existe dans la console
- Réponse : l'ARN, pas `PendingConfirmation` : c'est le seul signe vérifiable que SNS livrera ; un mail reçu ne dit pas qu'on a cliqué.

## 6. placeholder : jamais <x> à copier tel quel
- Sous-thème : readme
- Niveau : 1
- Source : data-platform · S1-09
- Définition : Dans une commande à copier, `<raw>` est un piège : le shell lit `<` comme une redirection ; donner la commande qui calcule la valeur.
- Contexte : `--bucket <raw>` donne en zsh `no such file or directory: raw`, ou crée un fichier vide si `raw` existe (`>` suivant). Mieux : `--bucket "$(terraform -chdir=infra output -json bucket_names | jq -r .raw)"`, ou une variable posée une ligne plus haut. Si un placeholder est inévitable (valeur propre au lecteur), l'écrire `VOTRE_BUCKET` en majuscules et le dire.
- Usage : ✅ valeurs lues dans les outputs Terraform, variables d'environnement · ❌ `<account_id>` dans une commande : le réserver au texte descriptif.

```bash
# Exemple 1 : la valeur calculée
B=$(terraform -chdir=infra output \
  -json bucket_names | jq -r .raw)
aws s3 ls "s3://$B/bodacc/" \
  --profile data-platform
```

- Quiz : Un README écrit `aws s3 ls s3://<raw>/bodacc/`. Que voit le lecteur sous zsh, si aucun fichier `raw` n'existe ?
- [ ] La liste des partitions
- [ ] `NoSuchBucket`
- [x] `no such file or directory: raw`
- [ ] Une invite qui demande le bucket
- Réponse : `no such file or directory: raw` : zsh traite `<raw` comme une redirection avant même de lancer `aws`.

## 7. AGENTS.md : les règles pour les agents de code
- Sous-thème : agents
- Niveau : 1
- Source : data-platform · S1-09
- Définition : `AGENTS.md`, à la racine, donne aux agents de code (Claude Code, Codex, Cursor) structure, commandes de vérification, conventions et interdits du dépôt.
- Contexte : Un agent lit le dépôt, pas la conversation de l'équipe : ce qu'un développeur apprend en revue (« jamais le numéro de compte dans un fichier », « `make check` avant commit ») doit être écrit. Le format est un Markdown libre, court et impératif ; il complète le README, qui reste pour les humains. Standard ouvert, lu par plusieurs outils.
- Usage : ✅ tout dépôt où des agents écrivent du code ou lancent des commandes · ❌ y recopier le README : y mettre seulement ce qui change le comportement de l'agent.

```markdown
# Exemple 1 : extrait
## Vérifier
- `make check` avant tout commit
- `make plan` après tout changement .tf

## Ne jamais
- écrire un numéro de compte AWS
  (dépôt public)
- lancer `make up` / `terraform apply`
  sans accord humain
```

- Quiz : Où mettre la règle « messages de commit en français » pour qu'un agent l'applique ?
- [ ] Dans le README racine
- [x] Dans `AGENTS.md`
- [ ] Dans un commentaire du Makefile
- [ ] Dans `docs/architecture.md`
- Réponse : `AGENTS.md` : c'est le fichier que les agents chargent pour leurs règles ; le README décrit le projet aux humains.

## 8. architecture : un schéma texte dans le README
- Sous-thème : readme
- Niveau : 1
- Source : data-platform · S1-09
- Définition : L'architecture du README racine tient en un schéma texte d'une dizaine de lignes, dans un bloc de code, à côté des commandes.
- Contexte : Un schéma en texte se relit dans la MR, se corrige dans le même commit que le code et s'affiche partout (GitHub, terminal, IDE). Une image exportée vieillit sans que personne le voie, et son diff est illisible. Le bloc de code est obligatoire : hors bloc, Markdown fusionne les lignes et écrase les espaces. Le détail (diagramme complet, ADR) vit dans `docs/`, relié par un lien.
- Usage : ✅ flux principal en 10 lignes (déclencheur → calcul → stockage → alerte) · ❌ coller un PNG d'Excalidraw comme seule description : le garder dans `docs/`, en plus du texte.

```text
# Exemple 1 : le flux de data-platform
Scheduler 06:00 Europe/Paris, event {}
   │ endosse le rôle …-scheduler
   ▼
Lambda ingest-bodacc ── API BODACC
   ▼
S3 raw : part-0001.jsonl.gz
         puis _MANIFEST.json
   │ échec → Errors → alarme → mail
   ▼
(S2) Step Functions → PySpark
```

- Quiz : Même schéma collé dans le README **sans** bloc de code : comment s'affiche-t-il sur GitHub ?
- [ ] Identique, au caractère près
- [x] Lignes fusionnées en un paragraphe, alignement perdu
- [ ] En image, générée par GitHub
- [ ] Erreur de rendu Markdown
- Réponse : lignes fusionnées : hors bloc de code, un retour à la ligne simple ne coupe pas le paragraphe et les espaces multiples sont réduits ; seul le bloc garde le texte tel quel.

## 9. lien relatif : le même partout
- Sous-thème : readme
- Niveau : 1
- Source : data-platform · S1-09
- Définition : Un lien Markdown relatif (`[infra/README.md](infra/README.md)`) pointe le fichier de la même branche, sur GitHub comme dans un clone ou un IDE.
- Contexte : Le chemin est résolu depuis le fichier qui contient le lien. Une URL absolue (`https://github.com/<compte>/<dépôt>/blob/main/…`) vise toujours `main` du dépôt d'origine : sur une branche, un fork ou après un renommage, elle affiche une autre version, ou rien. Le relatif suit le dépôt où qu'il soit cloné, et un script de CI peut vérifier que la cible existe.
- Usage : ✅ tout lien d'un README vers un autre fichier du dépôt · ❌ URL GitHub absolue vers son propre dépôt : chemin relatif.

```markdown
# Exemple 1 : depuis le README racine
détail : [lambdas/ingest_bodacc/README.md]
         (lambdas/ingest_bodacc/README.md)
source : [docs/source-bodacc.md]
         (docs/source-bodacc.md)
```

- Quiz : Sur la branche `feature/x`, le README modifié pointe `https://github.com/…/blob/main/infra/README.md`. Quelle version s'ouvre ?
- [ ] Celle de `feature/x`
- [x] Celle de `main`
- [ ] La dernière modifiée, toutes branches confondues
- Réponse : celle de `main` : l'URL absolue fige la branche ; un lien relatif ouvrirait le fichier de `feature/x`.

## 10. git ls-files --ignored : ce qui n'existe que chez toi
- Sous-thème : tester
- Niveau : 2
- Source : data-platform · S1-09
- Définition : `git ls-files --others --ignored --exclude-standard` liste les fichiers ignorés présents sur le disque : exactement ce qu'un clone neuf n'aura pas.
- Contexte : Ces fichiers sont les implicites de ta doc : `local.tfvars`, `backend.hcl`, l'état local du bootstrap. Chacun doit soit être recréé par une étape écrite (un `cp …example` puis remplir), soit être produit par une commande (`terraform apply` du bootstrap). Ce qui n'entre dans aucun des deux cas est un trou. `git status --ignored` donne la même liste, marquée `!!`.
- Usage : ✅ audit d'un README de démarrage, préparation d'un poste neuf · ❌ y chercher des secrets à commiter : la liste sert à documenter leur création, pas à les publier.

```bash
# Exemple 1 : mesuré sur le poste
git ls-files --others --ignored \
  --exclude-standard | grep -E \
  'tfvars|backend.hcl'
# → infra/bootstrap/local.auto.tfvars
#   infra/envs/dev/backend.hcl
#   infra/envs/dev/local.tfvars
# même commande dans le clone → 0 ligne
```

- Quiz : `infra/bootstrap/terraform.tfstate` apparaît dans la liste. Comment la doc doit-elle le traiter ?
- [ ] Fournir un `terraform.tfstate.example`
- [x] Le faire produire par l'étape `terraform apply` du bootstrap
- [ ] Le commiter : il est nécessaire
- [ ] L'ignorer : un inconnu n'en a pas besoin
- Réponse : produit par l'`apply` du bootstrap : un état ne se copie pas d'un modèle, il naît de la création des ressources (et un état local perdu se reconstruit par `import`).

## 11. README racine : lier, ne pas recopier
- Sous-thème : readme
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Le README racine relie les README des dossiers (`infra/README.md`, `lambdas/…/README.md`) au lieu de recopier leur contenu.
- Contexte : Deux copies d'une même procédure divergent au premier changement : l'une est corrigée, l'autre continue d'induire en erreur. Le README racine garde ce qui traverse le dépôt (architecture, démarrage, commandes du quotidien) ; chaque dossier documente son détail, au plus près du code qu'il décrit, et le README racine y renvoie par un lien relatif.
- Usage : ✅ procédures longues (bootstrap, reconstruction, rejeu) dans le README du dossier, lien depuis la racine · ❌ copier la table des rôles IAM dans deux fichiers.

```markdown
# Exemple 1 : un lien, une phrase
## Démarrer de zéro
3. Bootstrap du compte (une fois) :
   voir [infra/bootstrap/README.md]
   (infra/bootstrap/README.md).
```

- Quiz : `infra/README.md` et le README racine décrivent tous deux `make down`. On ajoute un bucket. Combien de fichiers faut-il corriger ?
- [ ] Un : Terraform s'en charge
- [x] Deux, et le risque d'en oublier un
- [ ] Aucun : la doc ne décrit pas les buckets
- Réponse : deux : chaque copie doit être mise à jour, et celle qu'on oublie devient fausse ; d'où un seul endroit et un lien.

## 12. ordre de démarrage : les dépendances réelles
- Sous-thème : readme
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Les étapes de démarrage suivent l'ordre réel des dépendances : ce qui est lu par une étape doit être créé par une étape précédente.
- Contexte : Ici : bootstrap (bucket d'état et bucket d'artefacts) → `backend.hcl` et `local.tfvars` → `make lambdas-publish` (zip + `current.json`) → `make up` (un data source lit `current.json` au `plan`) → confirmer les mails SNS. Inverser publish et up fait échouer tout le plan. L'auteur ne voit plus cet ordre : son pointeur existe depuis longtemps.
- Usage : ✅ dériver l'ordre des dépendances (qui lit quoi), puis le vérifier dans un compte ou un clone neuf · ❌ l'ordre dans lequel on a construit le projet : il contient des détours et des migrations.

```bash
# Exemple 1 : up avant publish (mesuré)
make up
# → Error: reading S3 Bucket
#   (data-platform-artifacts-<account_id>)
#   Object (lambdas/…/current.json):
#   couldn't find resource
```

- Quiz : `make deploy` vaut `lambdas-publish up`. Faut-il quand même documenter les deux étapes séparément ?
- [ ] Non : `make deploy` suffit toujours
- [x] Oui : le bootstrap doit exister avant, et publish seul sert à vérifier un zip
- [ ] Non : l'ordre ne compte pas pour Make
- Réponse : oui : `deploy` n'exprime pas le bootstrap préalable, et chaque étape seule a un résultat attendu à vérifier ; la doc nomme `deploy` comme raccourci.

## 13. prérequis : outils et versions minimales
- Sous-thème : readme
- Niveau : 2
- Source : data-platform · S1-09
- Définition : La section prérequis liste chaque outil appelé par les commandes documentées, avec la version minimale exigée par le code.
- Contexte : Les versions se lisent dans le dépôt : `required_version = ">= 1.10"` du bootstrap (verrou natif S3), `requires-python = ">=3.12"`, `.python-version`. Les outils se trouvent dans les recettes : le Makefile appelle `jq` (`replay`, `duckdb`) ; sans lui, l'erreur arrive au milieu d'une procédure. Ajouter le compte AWS, la région et le profil CLI attendus.
- Usage : ✅ relire les recettes du Makefile et les blocs `terraform {}` pour compléter la liste · ❌ « Terraform récent » : écrire la version, et d'où elle vient.

```bash
# Exemple 1 : versions lues dans le dépôt
grep -h required_version \
  infra/versions.tf \
  infra/bootstrap/versions.tf
# → required_version = ">= 1.9"
#   required_version = ">= 1.10"
grep -c jq Makefile   # outil caché
```

- Quiz : `infra/` exige Terraform `>= 1.9` et `infra/bootstrap/` `>= 1.10`. Quelle version écrire dans les prérequis ?
- [ ] `>= 1.9`
- [x] `>= 1.10`
- [ ] La dernière disponible
- Réponse : `>= 1.10` : le démarrage passe par le bootstrap ; la contrainte la plus forte de la procédure gagne.

## 14. CLAUDE.md : importer AGENTS.md
- Sous-thème : agents
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Claude Code lit `CLAUDE.md` ; une ligne `@AGENTS.md` y importe le fichier commun, pour une seule source de règles partagée par plusieurs agents.
- Contexte : Chaque outil a son fichier (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules`). Écrire les mêmes règles trois fois, c'est trois copies qui divergent. `AGENTS.md` porte les règles ; `CLAUDE.md` l'importe, et peut ajouter ce qui n'est propre qu'à Claude Code. Les préférences personnelles restent dans `~/.claude/CLAUDE.md`, jamais dans le dépôt.
- Usage : ✅ `CLAUDE.md` d'une ligne `@AGENTS.md` dans le dépôt · ❌ y mettre ses préférences personnelles (langue, ton) : elles s'imposeraient à toute l'équipe.

```markdown
# Exemple 1 : CLAUDE.md complet
@AGENTS.md
```

- Quiz : La règle « préfixer chaque commit par la branche » est dans ton `~/.claude/CLAUDE.md`. Un collègue sous Codex l'applique-t-il dans ce dépôt ?
- [ ] Oui : Codex lit les fichiers Claude
- [x] Non : il faut l'écrire dans `AGENTS.md` du dépôt
- [ ] Oui, via le hook git
- Réponse : non : `~/.claude/CLAUDE.md` est personnel et propre à Claude Code ; une règle d'équipe va dans `AGENTS.md`, commité (ou dans un hook `commit-msg`, qui l'impose à tous).

## 15. numéro de compte : grep avant commit
- Sous-thème : sécurité
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Avant de commiter, chercher les suites de 12 chiffres dans le diff indexé : un numéro de compte AWS n'entre jamais dans un dépôt public.
- Contexte : Le numéro arrive par copier-coller : nom de bucket `…-raw-<12 chiffres>`, ARN dans une sortie de commande, champ `"account"` d'un événement. Une fois poussé, il reste dans l'historique : le retirer demande de réécrire l'historique et, sur GitHub, de recréer le dépôt (vécu en S1-07). Les comptes de la doc AWS (`123456789012`) sont des faux positifs à exclure.
- Usage : ✅ `git diff --cached | grep -E '[0-9]{12}'` avant chaque commit, ou un hook pre-commit · ❌ compter sur une relecture à l'œil d'un long diff.

```python
# Exemple 1 : le contrôle en Python
import re

diff = """+bucket = "dp-raw-999988887777"
+account_id = "123456789012"
+count = 32373"""
doc = {"123456789012", "111122223333"}
trouve = [m for m in
          re.findall(r"\b\d{12}\b", diff)
          if m not in doc]
trouve   # → ['999988887777']
```

- Quiz : Que trouve `re.findall(r"\b\d{12}\b", "arn:aws:iam::999988887777:role/x")` ?
- [x] `['999988887777']`
- [ ] `[]` : `\b` ne coupe pas sur `:`
- [ ] `['8264000000', '00']`
- [ ] `['999988887777', 'role']`
- Réponse : `['999988887777']` : `:` n'est pas un caractère de mot, `\b` sépare donc bien le numéro dans un ARN.

## 16. relecteur sans contexte : trouver les implicites
- Sous-thème : tester
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Une doc se fait relire par quelqu'un qui ne connaît que le dépôt (nouveau collègue, agent sans la conversation), avec une consigne et un garde-fou.
- Contexte : L'auteur ne voit plus ses implicites ; le relecteur, si. La consigne fixe le but (« aller jusqu'à `make up` sur un compte neuf ») et le garde-fou (« aucune commande AWS en écriture »). Il rend une liste de blocages, chacun avec l'endroit et la commande qui échoue. Un agent relecteur ne doit recevoir ni la conversation ni les conclusions de l'auteur, sinon il les confirme.
- Usage : ✅ avant de publier un README de démarrage, après une refonte · ❌ demander « est-ce que c'est clair ? » à quelqu'un qui a vu le projet se construire.

```text
# Exemple 1 : consigne de relecture
But : depuis /tmp/clone, aller jusqu'à
  `make up` sur un compte AWS neuf.
Interdit : toute commande AWS en écriture.
Rendu : chaque blocage = fichier, ligne,
  commande, ce qui manque.
```

- Quiz : On donne au relecteur-agent la liste des trous déjà trouvés « pour gagner du temps ». Risque ?
- [ ] Aucun : il va plus vite
- [x] Il confirme cette liste et cherche moins le reste
- [ ] Il refuse la consigne
- Réponse : il confirme la liste : un relecteur qui reçoit l'hypothèse de l'auteur la valide au lieu de chercher ce que l'auteur n'a pas vu.

## 17. interdit : une règle, sa raison
- Sous-thème : agents
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Dans `AGENTS.md`, chaque interdit s'écrit en une ligne impérative suivie de sa raison : « Jamais X : raison ».
- Contexte : Un agent applique mal un paragraphe et généralise mal une règle sans raison. La raison lui permet de traiter le cas voisin : « jamais le numéro de compte : dépôt public » couvre aussi un ARN dans un exemple de doc. Les règles vérifiables par un outil (format, tests, hook) vont dans l'outil ; `AGENTS.md` garde ce qu'aucun test ne voit.
- Usage : ✅ interdits courts, raison en une demi-ligne, commandes exactes · ❌ « faire attention à la sécurité » : rien de vérifiable, rien d'applicable.

```markdown
# Exemple 1 : vague, puis applicable
- Attention aux identifiants.
- Jamais de numéro de compte AWS dans
  un fichier : dépôt public, il reste
  dans l'historique (`<account_id>`).
```

- Quiz : Laquelle de ces règles a sa place dans un hook plutôt que dans `AGENTS.md` ?
- [ ] « Jamais `make up` sans accord humain »
- [x] « Lignes de 120 caractères au plus »
- [ ] « Ne pas éditer `learning/` miroir de Notion »
- [ ] « Expliquer le contexte avant le code »
- Réponse : les 120 caractères : `ruff` le vérifie à chaque commit ; une règle qu'un outil peut contrôler va dans l'outil, pas dans une consigne.

## 18. capture console : le numéro en haut à droite
- Sous-thème : sécurité
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Une preuve de livraison se produit par une commande (sortie CLI masquée, PNG de l'API), pas par une capture d'écran de la console AWS.
- Contexte : La console affiche le numéro de compte dans le menu, les ARN et les URL ; une capture l'emporte sans qu'on le voie. Une commande se relance, se masque (`sed -E 's/[0-9]{12}/<account_id>/g'`) et se vérifie par un grep. Pour un graphe, `aws cloudwatch get-metric-widget-image` rend un PNG à partir d'une définition JSON versionnable.
- Usage : ✅ livrable de fin de sprint, preuve dans une MR, doc d'exploitation · ❌ capture d'écran de console collée dans `docs/`.

```bash
# Exemple 1 : liste des partitions masquée
aws s3 ls "s3://$B/bodacc/" \
  --profile data-platform \
  | sed -E 's/[0-9]{12}/<account_id>/g' \
  > docs/livrables/s1/partitions.txt
grep -cE '[0-9]{12}' \
  docs/livrables/s1/partitions.txt
# → 0
```

- Quiz : Que donne `echo "arn:aws:iam::123456789012:role/x" | sed -E 's/[0-9]{12}/<account_id>/g'` ?
- [ ] `arn:aws:iam:::role/x`
- [x] `arn:aws:iam::<account_id>:role/x`
- [ ] La ligne inchangée : `{12}` exige `-r`
- [ ] `arn:aws:iam::<account_id>`
- Réponse : `arn:aws:iam::<account_id>:role/x` (mesuré) : `-E` active les quantificateurs `{12}`, seule la suite de 12 chiffres est remplacée.

## 19. chiffre dans la doc : daté, avec sa commande
- Sous-thème : readme
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Un chiffre de la doc (ressources, buckets, rôles) porte sa date et la commande qui le recalcule ; sinon il devient faux en silence.
- Contexte : Vu en S1-09 : « 43 ressources », « 5 buckets », « 3 rôles » dans `infra/README.md`, vrais en S1-04, faux en S1-08 (60 ressources, 4 buckets, 5 rôles). Un nombre nu ne dit ni quand il était vrai, ni comment le vérifier. Avec la date et la commande, le lecteur sait s'il doit le recalculer, et le recalcule en une ligne. Mieux encore : ne pas écrire de nombre quand la liste suffit.
- Usage : ✅ « 60 ressources gérées au 2026-10-25 (`state list | grep -vc '^data\.'`) » · ❌ « 43 ressources » nu, ou un compte qui inclut les data sources.

```bash
# Exemple 1 : le chiffre et sa commande
terraform -chdir=infra state list \
  | grep -vc '^data\.'
# → 60   (ressources gérées, 2026-10-25)
terraform -chdir=infra state list \
  | wc -l
# → inclut aussi les data sources
```

- Quiz : Le README dit « `make down` détruit 43 ressources » ; `make down` affiche `Resources: 60 destroyed.` Que corriger ?
- [ ] Rien : Terraform compte aussi les data sources
- [x] Le chiffre, et lui ajouter date et commande
- [ ] Le Makefile, qui détruit trop
- [ ] Rien : l'écart vient de `force_destroy`
- Réponse : le chiffre, daté et recalculable : le code a grandi (Lambda, planification, alarmes) ; `destroy` ne compte que les ressources gérées, sans les data sources.

## 20. version sans contrainte : écrire la version testée
- Sous-thème : readme
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Pour un outil dont aucun fichier du dépôt n'exige de version, le prérequis indique la version réellement testée, pas un minimum deviné.
- Contexte : Terraform et Python ont une contrainte dans le code (`required_version`, `requires-python`) : on la recopie. DuckDB, jq, l'AWS CLI n'en ont pas. Écrire « DuckDB ≥ 1.1 » invente une garantie que personne n'a vérifiée ; « testé en 2.0.0 » dit un fait. Le lecteur sait d'où partir, et un écart de comportement se rattache à une version connue.
- Usage : ✅ « testé en 2.0.0 » pour un outil facultatif ou sans contrainte · ❌ un minimum « au jugé » : il sera faux dans un sens ou dans l'autre.

```markdown
# Exemple 1 : contrainte ou fait mesuré
| Terraform | ≥ 1.10 (bootstrap)   |
| Python    | 3.12 (.python-version)|
| DuckDB    | testé en 2.0.0       |
```

- Quiz : DuckDB n'a aucune contrainte dans le dépôt et marche en 2.0.0 sur ton poste. Que gagne « testé en 2.0.0 » sur « ≥ 1.1 » ?
- [ ] Rien : les deux disent la même chose
- [x] C'est un fait vérifié, pas une limite inventée
- [ ] DuckDB refuse de démarrer sous 2.0.0
- [ ] `uv` installe alors la bonne version
- Réponse : un fait vérifié : personne n'a testé 1.1 ; la version testée donne un point de départ sûr sans promettre ce qui n'a pas été mesuré.

## 21. mise en garde : au pas qui piège, pas en annexe
- Sous-thème : readme
- Niveau : 2
- Source : data-platform · S1-09
- Définition : La raison d'un ordre ou d'une exception s'écrit en commentaire sur la ligne concernée, pas dans une section « Remarques » plus bas.
- Contexte : On suit une procédure en copiant les commandes une à une ; une note placée après est lue trop tard, ou jamais. Le commentaire sur la ligne dit le piège au moment où on va y tomber : `make sync` (pas `uv sync` seul), `make lambdas-publish` avant le premier `make up`, les mails SNS à confirmer. Une ligne, le pourquoi, rien de plus.
- Usage : ✅ commentaire `# AVANT … : parce que …` dans le bloc de commandes · ❌ « Attention » en fin de document, après la commande qui échoue.

```bash
# Exemple 1 : le piège sur sa ligne
# pas `uv sync` seul : il n'installe
# pas les Lambdas et les packages
make sync
# AVANT le premier `make up` :
# Terraform lit le pointeur current.json
make lambdas-publish
make up
```

- Quiz : La procédure liste `make up`, et une section « Remarques » en bas dit « publier les zips d'abord ». Que fait un lecteur qui copie les commandes ?
- [x] `make up` échoue sur `current.json`, avant d'avoir lu la remarque
- [ ] Il lit la remarque avant : elle est dans le même fichier
- [ ] `make up` publie les zips tout seul
- Réponse : `make up` échoue : la remarque est lue après la commande ; la mise en garde doit précéder la ligne qui piège.

## 22. AGENTS.md : affirmer après mesure
- Sous-thème : agents
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Une règle d'`AGENTS.md` impose qu'un comportement d'AWS ou de la source soit affirmé après une commande lancée et sa sortie lue, jamais de mémoire.
- Contexte : Un agent comble les trous avec ce qu'il croit savoir, sur le même ton qu'un fait mesuré. Dans ce projet, deux affirmations de mémoire étaient fausses le même jour : « pas de parution le dimanche » (7 dimanches sur 7 en avaient) et « l'alarme repasse en OK au bout de 15 min » (elle est restée en ALARM). Aucun test ne voit ce genre d'erreur : seule la règle écrite oblige à mesurer.
- Usage : ✅ calendrier d'une source, délai d'un service, limite d'API, comportement d'une alarme · ❌ conclure d'une doc lue en diagonale ou d'un souvenir : lancer la commande, citer la sortie.

```markdown
# Exemple 1 : la règle, sa raison
- Un comportement AWS ou de la source
  BODACC s'affirme après mesure
  (commande lancée, sortie lue), pas
  de mémoire : deux erreurs le
  2026-10-25 (calendrier, alarme).
```

- Quiz : L'agent écrit « le BODACC ne paraît pas le samedi » dans la doc. Que lui demander d'abord ?
- [ ] La page de la doc officielle qui le dit
- [x] La commande lancée et le nombre de samedis mesurés
- [ ] De le marquer « à vérifier »
- [ ] Rien : c'est vrai
- Réponse : la commande et la mesure : vrai ici (0 samedi sur 8 avec `count_day`), mais seule la mesure le prouve ; une doc tierce donnait un autre calendrier.

## 23. incident : une erreur, une ligne d'AGENTS.md
- Sous-thème : agents
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Chaque erreur vécue qu'aucun test ne détecte devient une ligne d'`AGENTS.md`, avec la commande qui la contrôle.
- Contexte : Une erreur corrigée sans règle revient au prochain agent ou au prochain arrivant. Ici : un numéro de compte poussé sur un dépôt public (historique réécrit, dépôt recréé) a donné « jamais 12 chiffres dans un fichier suivi » et le grep avant commit ; un `uv sync` qui cassait `make check` dans un clone neuf a donné « `make sync`, jamais `uv sync` seul ». La règle cite le contrôle, pas seulement l'interdit.
- Usage : ✅ post-mortem court : cause, règle, commande de contrôle · ❌ règle ajoutée « par précaution » sans incident ni raison : le fichier gonfle, plus personne ne le lit.

```bash
# Exemple 1 : la règle née de la fuite
git diff --cached \
  | grep -E '[0-9]{12}'
# → rien : on peut commiter
# → une ligne : remplacer par
#   <account_id> avant le commit
```

- Quiz : Après la fuite, où la règle « pas de numéro de compte » protège-t-elle aussi les agents d'un collègue ?
- [ ] Dans ton `~/.claude/CLAUDE.md`
- [x] Dans l'`AGENTS.md` du dépôt
- [ ] Dans la mémoire de ton agent
- [ ] Dans le message du commit correctif
- Réponse : dans l'`AGENTS.md` du dépôt : il voyage avec le clone ; ta config et ta mémoire ne servent qu'à toi.

## 24. chemin local : le dire dans un dépôt public
- Sous-thème : sécurité
- Niveau : 2
- Source : data-platform · S1-09
- Définition : Un chemin propre au poste de l'auteur (`~/.claude/skills/…`, un dépôt voisin) se signale comme local, avec la marche à suivre sans lui.
- Contexte : Un inconnu qui clone le dépôt suit les chemins cités et bute sur un dossier absent, sans savoir s'il a raté une étape. Écrire « local au poste de l'auteur ; sans lui, respecter le format à la main et ne pas publier » lève le doute. `~` ne révèle pas le nom d'utilisateur ; `/Users/<nom>/` le ferait, et se masque comme un numéro de compte.
- Usage : ✅ outils personnels cités dans `AGENTS.md`, dépendance à un dépôt voisin non publié · ❌ chemin absolu `/Users/<nom>/…` dans un fichier suivi : `~` ou une variable.

```markdown
# Exemple 1 : la mention qui lève le doute
Les skills `/tuteur` et `/cartes` sont
locaux au poste de l'auteur
(`~/.claude/skills/`) : sans eux,
respecter le format à la main, et ne
pas publier.
```

- Quiz : Lequel de ces chemins révèle une information personnelle dans un dépôt public ?
- [ ] `~/.claude/skills/tuteur/`
- [x] `/Users/jdupont/Desktop/workspace/`
- [ ] `$HOME/.aws/config`
- [ ] `infra/envs/dev/local.tfvars`
- Réponse : `/Users/jdupont/…` : le nom d'utilisateur y est en clair ; `~` et `$HOME` sont développés sur chaque poste.

## 25. doc qui dérive : la vérifier en CI
- Sous-thème : tester
- Niveau : 3
- Source : data-platform · S1-09
- Définition : Une doc se vérifie automatiquement sur ce qui est mécanique : chaque `make <cible>` citée existe, chaque lien relatif pointe un fichier.
- Contexte : Une cible renommée dans le Makefile laisse le README faux sans qu'aucun test ne rougisse. Un petit script en CI extrait les `make <cible>` des Markdown et les compare aux cibles du Makefile ; même chose pour les liens `](chemin)`. Le fond (ordre, prérequis, clarté) reste à la relecture humaine : on n'automatise que ce qui est vérifiable.
- Usage : ✅ dépôt dont le README cite beaucoup de commandes, documentation d'exploitation · ❌ tester le contenu exact d'une sortie de commande dans la doc : trop fragile.

```python
# Exemple 1 : cibles citées vs cibles réelles
import re

readme = "make sync puis make check, make replay FROM=…"
makefile = "sync:\n\tuv sync\ncheck: lint test\n"
citees = set(re.findall(r"make (\w[\w-]*)", readme))
reelles = set(re.findall(r"^([\w-]+):", makefile, re.M))
sorted(citees - reelles)   # → ['replay']
```

- Quiz : Avec ce script, `make plan ENV=prod` dans le README : quelle cible est extraite ?
- [x] `plan`
- [ ] `plan ENV=prod`
- [ ] `ENV`
- [ ] Aucune
- Réponse : `plan` : `\w[\w-]*` s'arrête à l'espace ; les variables qui suivent ne sont pas des cibles.

## 26. make help : la liste vient du Makefile
- Sous-thème : tester
- Niveau : 3
- Source : data-platform · S1-09
- Définition : Une cible `help` qui lit les commentaires `## …` des cibles affiche la liste à jour des commandes, générée depuis le Makefile lui-même.
- Contexte : Un tableau des cibles dans le README dérive à chaque ajout. Avec `cible: ## texte` et un `grep | awk` sur `$(MAKEFILE_LIST)`, la description vit sur la ligne de la cible : impossible de l'oublier en la renommant. Une cible sans `##` n'apparaît pas, ce qui cache les cibles internes (`tf-init`). Placée en premier, `help` devient la cible par défaut de `make` seul.
- Usage : ✅ dépôt à nombreuses cibles, README qui renvoie à `make help` · ❌ recopier la sortie de `make help` dans le README : la référence reste le Makefile.

```make
# Exemple 1 : documenter sur la ligne
help: ## liste des cibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) \
	| awk -F ':.*## ' \
	  '{printf "%-16s %s\n", $$1, $$2}'
sync: ## installe tout le workspace
	uv sync --all-packages
tf-init:
	@echo init
# make help → help, sync (pas tf-init)
```

- Quiz : Avec ce Makefile, que lance `make` sans argument ?
- [ ] Rien : il faut nommer une cible
- [x] `help`
- [ ] `sync`
- [ ] Toutes les cibles commentées
- Réponse : `help` (mesuré) : `make` seul lance la première cible du fichier ; d'où `help` placée en tête.

## 27. relecteur : séparer mesuré et déduit
- Sous-thème : tester
- Niveau : 3
- Source : data-platform · S1-09
- Définition : Le rapport d'un relecteur sépare le mesuré (commande lancée) du déduit (lu) ; seul le mesuré se corrige comme un fait.
- Contexte : Un relecteur privé d'AWS déduit beaucoup : ici, `make check` et `terraform validate` étaient mesurés, mais « `aws_budgets_budget` peut être refusé tant que l'accès IAM à la facturation n'est pas activé » était une déduction. Une déduction passe dans la doc au conditionnel (« si `make up` échoue sur le budget avec `AccessDenied`… »), jamais comme une étape obligatoire inventée.
- Usage : ✅ exiger les deux colonnes dans la consigne, écrire les déductions en « si… alors » · ❌ recopier tout le rapport en étapes impératives : la doc affirme ce que personne n'a vu.

```markdown
# Exemple 1 : la consigne au relecteur
Signale explicitement ce que tu as
mesuré (commande lancée) et ce que
tu as seulement déduit en lisant.
```

```markdown
# Exemple 2 : une déduction dans la doc
Si `make up` échoue sur
`aws_budgets_budget` avec
`AccessDenied` : activer l'accès IAM
à la facturation (compte root).
```

- Quiz : Le relecteur déduit qu'une commande « échouera probablement » sur un compte neuf. Que faire dans le README ?
- [ ] L'écrire comme une étape obligatoire
- [ ] L'ignorer tant que ce n'est pas mesuré
- [x] L'écrire au conditionnel, avec le symptôme
- [ ] Supprimer la commande
- Réponse : au conditionnel avec le symptôme : l'inconnu sait quoi faire si ça arrive, sans suivre une étape que personne n'a vérifiée.
