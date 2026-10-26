---
title: "Cartes · Git"
type: cartes
langage: DevOps
chapitre: Versionner et documenter
cours: Git
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Git
DevOps · Git : config, gitignore, commit, branches, historique, remote (format spec v4 de revision-pwa).

## 1. git config : global ou local
- Id : git-config-global-ou-local
- Sous-thème : config
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : dépôt git, commit
- Source : data-platform · S1-01
- Définition : `git config --global` écrit dans `~/.gitconfig` pour tous les dépôts ; sans `--global`, dans `.git/config` du dépôt courant, qui l'emporte.
- Contexte : Trois niveaux, du plus large au plus précis : `--system`, `--global`, local. Git lit les trois et garde la valeur la plus précise. D'où une identité perso en global (alias noreply GitHub) et une surcharge locale dans chaque dépôt client. `--show-origin` dit quel fichier a fourni chaque valeur : premier réflexe quand un commit part avec le mauvais email.
- Usage : ✅ identité perso et `init.defaultBranch` en global, email client en local dans le dépôt client · ❌ `--global` lancé dans un dépôt client : tous les projets perso partent avec l'email client.

```bash
# Exemple 1 : le local gagne
git config --global user.email \
  "123+moi@users.noreply.github.com"
cd ~/client && git config user.email \
  "f.g@client.example"
git config user.email
# → f.g@client.example
```

```bash
# Exemple 2 : d'où vient chaque valeur ?
git config --show-origin --get-all \
  user.email
# file:~/.gitconfig  123+…@users.noreply…
# file:.git/config   f.g@client.example
```

- Quiz : Dans le dépôt client, que renvoie `git config --global --get user.email` ?
- [ ] `f.g@client.example`
- [x] L'alias noreply GitHub
- [ ] Les deux emails
- [ ] Rien : la valeur locale masque la globale
- Réponse : l'alias noreply : `--global` ne lit que `~/.gitconfig`, la surcharge du dépôt n'entre pas en compte.

## 2. .gitignore : trop tard pour un fichier suivi
- Id : git-gitignore-fichier-deja-suivi
- Sous-thème : gitignore
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : git-status-ignores-ou-non-suivis, git-gitignore-derniere-regle
- Mots-clés : index git, fichier suivi, commit
- Source : data-platform · S1-01
- Définition : `.gitignore` n'agit que sur les fichiers non suivis : un fichier déjà commité reste suivi, et dans l'historique, même ajouté ensuite.
- Contexte : Un fichier présent dans l'index est suivi, quel que soit le `.gitignore`. Pour arrêter de le suivre : `git rm --cached` (il reste sur le disque), puis commit. L'historique garde l'ancienne version : un secret poussé sur un dépôt public se révoque, il ne suffit pas de le retirer. D'où le `.gitignore` dès le premier commit, avant `.venv/`, `.terraform/` ou un `*.tfstate`.
- Usage : ✅ `.gitignore` au premier commit, `git rm --cached` pour un fichier suivi par erreur · ❌ compter sur le `.gitignore` pour cacher un `.env` déjà commité : révoquer le secret.

```bash
# Exemple 1 : ignoré trop tard
git add .env && git commit -m "init"
echo ".env" >> .gitignore
echo changed > .env
git status --short
# → " M .env"  (toujours suivi)
```

```bash
# Exemple 2 : arrêter de le suivre
git rm --cached .env
git status --short
# → "D  .env"  (retiré de l'index)
ls .env   # → .env (resté sur le disque)
git log --oneline -- .env
# → l'ancien commit le contient encore
```

- Quiz : `.env` est suivi et listé dans `.gitignore` : que renvoie `git check-ignore -v .env` ?
- [ ] `.gitignore:1:.env  .env`, code 0
- [x] Rien, code retour 1
- [ ] Une erreur : fichier suivi
- [ ] `!! .env`
- Réponse : rien, code 1 : `check-ignore` ne consulte pas les règles pour un fichier présent dans l'index ; `--no-index` les teste quand même.

## 3. git status --ignored : !! ou ??
- Id : git-status-ignores-ou-non-suivis
- Sous-thème : gitignore
- Type : comparaison
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : fichier suivi, .gitignore, état
- Source : data-platform · S1-01
- Définition : `git status --short --ignored` marque `??` les fichiers non suivis, donc commitables, et `!!` ceux que le `.gitignore` exclut.
- Contexte : `??` ne protège de rien : un `git add .` l'embarque. Seul `!!` garantit qu'un `terraform.tfstate` ou un `local.auto.tfvars` ne partira pas. Un dossier entièrement non suivi s'affiche replié (`?? infra/`), `-uall` liste chaque fichier. Git suit des fichiers, pas des dossiers : d'où un `README.md` (ou un `.gitkeep`) pour qu'un dossier encore vide existe dans le dépôt.
- Usage : ✅ avant le premier commit d'un dossier sensible (`infra/`), compter les `!!` attendus · ❌ `git status` sans `--ignored` : un fichier ignoré y est invisible, comme un fichier qui n'existe pas.

```bash
# Exemple 1 : ignoré ou seulement non suivi ?
git status --short --ignored infra/
# ?? infra/main.tf          commitable
# !! infra/.terraform/      ignoré
# !! infra/terraform.tfstate
# !! infra/local.auto.tfvars
```

- Quiz : `git status --short --ignored` affiche `?? infra/tfplan` : que fait ensuite `git add infra/` ?
- [x] Stage `infra/tfplan` (`A  infra/tfplan`)
- [ ] L'ignore : `??` vaut exclusion
- [ ] Refuse : fichier non suivi
- [ ] Le stage avec un avertissement `ignored`
- Réponse : il le stage : `??` = non suivi mais commitable, seul `!!` protège ; ajouter `tfplan` au `.gitignore` (mesuré).

## 4. git add : ciblé, jamais -A
- Id : git-add-chemins-explicites
- Sous-thème : commit
- Type : recette
- Niveau : 1
- Profils : débutant
- Voir aussi : git-diff-disque-index-head
- Mots-clés : index git, .gitignore, tfplan, HEAD
- Source : data-platform · S1-03
- Définition : `git add <fichier>` stage ce que tu as décidé d'inclure ; `git add -A` stage tout le non-ignoré, oublis compris.
- Contexte : Le `.gitignore` liste ce à quoi tu as pensé : un `tfplan` pas encore listé (ARN, ID de compte) part avec `-A`. Un commit = un sujet : `-A` mélange `infra/`, `learning/` et le scaffold. Réflexe avant de commiter : `git status --short`, rien que des `A` et `M` voulus. Un fichier stagé par erreur se retire de l'index sans toucher au disque.
- Usage : ✅ chemins explicites, `git add -p` pour choisir des morceaux · ❌ `git add -A` ou `git add .` dans un dépôt public qui a des fichiers sensibles non suivis.

```bash
# Exemple 1 : stager le sujet du commit
git add README.md docs/architecture.md \
  .gitignore packages/README.md
git status --short | grep -v '^??'
# A  README.md
# A  docs/architecture.md
# M  .gitignore
```

```bash
# Exemple 2 : retirer de l'index
git add -A        # oups : infra/tfplan
git restore --staged infra/tfplan
git status --short infra/tfplan
# ?? infra/tfplan  (resté sur le disque)
```

- Quiz : Dépôt neuf, aucun commit encore : que fait `git restore --staged f` ?
- [x] `fatal: could not resolve HEAD`
- [ ] Retire `f` de l'index
- [ ] Supprime `f` du disque
- [ ] Rien, sans message
- Réponse : erreur : `restore --staged` recopie la version de `HEAD` dans l'index, et `HEAD` n'existe pas encore ; `git rm --cached f` marche.

## 5. git diff : disque, index ou HEAD
- Id : git-diff-disque-index-head
- Sous-thème : commit
- Type : comparaison
- Niveau : 1
- Profils : débutant
- Voir aussi : git-add-chemins-explicites
- Mots-clés : index git, HEAD, commit
- Définition : `git diff` compare le disque à l'index, `git diff --staged` l'index au dernier commit, `git diff HEAD` le disque au dernier commit.
- Contexte : Git a trois états d'un fichier : le dernier commit (`HEAD`), l'index (ce qui partira au prochain commit) et le disque. Après `git add`, `git diff` devient vide alors que rien n'est commité : c'est le piège quand on cherche « ce que je vais commiter ». Le réflexe avant un commit : `git diff --staged`, qui montre exactement le contenu du prochain commit.
- Usage : ✅ `git diff --staged` avant chaque commit, `--stat` pour un résumé · ❌ `git diff` seul pour relire un commit à venir : il ignore ce qui est déjà stagé.

```bash
# Exemple 1 : vide après git add
echo "siren" >> schema.md
git diff --stat
# → schema.md | 1 +
git add schema.md
git diff --stat           # → (rien)
git diff --staged --stat
# → schema.md | 1 +  (le prochain commit)
```

```bash
# Exemple 2 : stagé puis encore modifié
git add schema.md; echo "date" >> schema.md
git diff --stat           # disque / index
# → 1 insertion
git diff HEAD --stat      # disque / HEAD
# → 2 insertions
```

- Quiz : On fait `git add f`, on modifie encore `f`, puis `git commit -m …` : que contient le commit ?
- [ ] La version du disque, avec la dernière modification
- [x] La version stagée, sans la dernière modification
- [ ] Rien : `f` modifié depuis l'ajout bloque le commit
- [ ] Les deux versions, en deux commits
- Réponse : la version stagée : `commit` enregistre l'index tel qu'au `git add` ; la suite reste en ` M f`, à re-stager (mesuré).

## 6. commit --amend : refaire le dernier commit
- Id : git-commit-amend
- Sous-thème : commit
- Type : recette
- Niveau : 1
- Profils : débutant
- Voir aussi : git-push-force-with-lease, git-reset-trois-modes
- Mots-clés : hash de commit, reflog, push forcé, dépôt distant
- Définition : `git commit --amend` remplace le dernier commit par un nouveau (index actuel, message corrigé) : son hash change.
- Contexte : Rien n'est modifié en place : Git crée un commit neuf et déplace la branche dessus, l'ancien n'est plus référencé (le reflog le garde). `--no-edit` garde le message, idéal pour un fichier oublié. Comme le hash change, amender un commit déjà poussé diverge de la branche distante : réservé aux commits encore locaux, sinon il faut forcer le push.
- Usage : ✅ message mal préfixé, fichier oublié, avant le push · ❌ commit déjà poussé sur une branche partagée : nouveau commit correctif.

```bash
# Exemple 1 : corriger le message
git commit -m "fix parsing"
git commit --amend \
  -m "main: fix parsing BODACC"
git log --oneline -1
# → 3f2a1c9 main: fix parsing BODACC
```

```bash
# Exemple 2 : ajouter un fichier oublié
git add tests/test_parse.py
git commit --amend --no-edit
git log --oneline | wc -l
# → inchangé : le dernier est remplacé
git show --stat HEAD
# → contient aussi tests/test_parse.py
```

- Quiz : Le commit était déjà sur `origin/main` ; après `--amend`, que fait `git push` ?
- [ ] Remplace le commit distant par le nouveau
- [ ] Pousse le nouveau à la suite de l'ancien
- [x] Refusé : `! [rejected] (non-fast-forward)`
- [ ] Rien : le hash est le même
- Réponse : refusé (non-fast-forward) : le nouveau commit n'a pas l'ancien pour parent, le distant perdrait un commit ; il faudrait `--force-with-lease` (mesuré).

## 7. git switch -c : une branche est un pointeur
- Id : git-branche-pointeur
- Sous-thème : branches
- Type : concept
- Niveau : 1
- Profils : débutant
- Voir aussi : git-merge-fast-forward
- Mots-clés : commit, hash de commit
- Définition : Une branche est un pointeur mobile vers un commit ; `git switch -c feat` la crée sur le commit courant et s'y place.
- Contexte : Créer une branche ne copie rien : un fichier `.git/refs/heads/feat` contient un hash, déplacé à chaque commit. Les modifications non commitées n'appartiennent à aucune branche : elles suivent le changement de branche. `switch` (Git 2.23) remplace la moitié « branche » de `checkout` ; `git restore` prend l'autre moitié (fichiers).
- Usage : ✅ une branche par ticket (`RLINK-123`), `git switch -` pour revenir à la précédente · ❌ `git checkout <nom>` quand un fichier porte le même nom qu'une branche : ambigu, préférer `switch`.

```bash
# Exemple 1 : créer et changer
git switch -c RLINK-123
# → Switched to a new branch 'RLINK-123'
cat .git/refs/heads/RLINK-123
# → 0413858…  (juste un hash)
git switch -   # retour à main
```

```bash
# Exemple 2 : le travail en cours suit
echo "x" >> f            # non commité
git switch -c feat
git status --short       # →  M f
git switch main
git status --short       # →  M f
```

- Quiz : `f` est modifié localement et diffère sur la branche `other` : que fait `git switch other` ?
- [ ] Bascule et écrase la modification locale
- [ ] Bascule et crée des marqueurs de conflit
- [x] Refuse : `would be overwritten by checkout`
- [ ] Bascule et met la modification dans le stash
- Réponse : il refuse : la version de `other` écraserait le travail non commité ; commiter, `git stash` ou `switch -m` d'abord (mesuré).

## 8. git stash : mettre de côté
- Id : git-stash-mettre-de-cote
- Sous-thème : branches
- Type : recette
- Niveau : 1
- Profils : débutant
- Voir aussi : pre-commit-stash-conflit
- Mots-clés : fichier suivi, branche, hotfix
- Définition : `git stash` range les modifications des fichiers suivis dans une pile et remet le dossier propre ; `git stash pop` les réapplique.
- Contexte : Utile pour changer de branche en urgence (hotfix) sans commit bancal. La pile est locale et se lit avec `git stash list` (`stash@{0}` le plus récent). `pop` applique puis supprime l'entrée ; en cas de conflit, l'entrée est gardée pour ne rien perdre. `apply` applique sans supprimer. Un stash oublié des semaines devient un piège : préférer une branche WIP.
- Usage : ✅ interruption courte : hotfix sur `main`, `git pull` bloqué par une modif locale · ❌ travail de plusieurs jours : branche et commit WIP, poussés.

```bash
# Exemple 1 : de côté, puis retour
git stash
# → Saved working directory and index
#   state WIP on main: 0413858 c2
git status --short       # → (propre)
git switch hotfix && git switch -
git stash pop            # modifs revenues
```

```bash
# Exemple 2 : pop en conflit
git stash pop
# → CONFLICT (content): Merge conflict in f
# → The stash entry is kept in case
#   you need it again.
git stash list
# → stash@{0}: WIP on main: fe63099 c2
```

- Quiz : On a modifié `f` et créé `u.txt` (jamais ajouté) : après `git stash`, que montre `git status --short` ?
- [ ] Rien : tout est dans le stash
- [x] `?? u.txt`
- [ ] ` M f`
- [ ] ` M f` et `?? u.txt`
- Réponse : `?? u.txt` : `stash` ne prend que les fichiers suivis ; `git stash -u` embarque aussi les non suivis (mesuré).

## 9. fetch ou pull : récupérer le distant
- Id : git-fetch-ou-pull
- Sous-thème : remote
- Type : comparaison
- Niveau : 1
- Profils : débutant
- Voir aussi : git-merge-fast-forward, git-rebase-rejouer-commits
- Mots-clés : dépôt distant, rebase, merge
- Définition : `git fetch` télécharge les commits distants et met à jour `origin/main` seulement ; `git pull` = `fetch` puis intégration dans la branche courante.
- Contexte : `origin/main` est la copie locale, en lecture seule, de la branche distante au dernier fetch. `fetch` ne touche jamais au travail : on regarde (`git log main..origin/main`), puis on choisit merge ou rebase. `git status -sb` dit `ahead`/`behind` par rapport à ce dernier fetch, pas en direct. `pull --rebase` rejoue ses commits locaux au-dessus du distant, sans commit de merge.
- Usage : ✅ `fetch` puis relecture avant d'intégrer, `pull --rebase` sur sa branche perso · ❌ `pull` aveugle sur une branche partagée en plein travail local.

```bash
# Exemple 1 : fetch ne touche pas main
git fetch
git status -sb
# → ## main...origin/main
#   [ahead 1, behind 1]
git log --oneline main..origin/main
# → e281bf4 fromB  (à intégrer)
```

```bash
# Exemple 2 : intégrer en rebase
git pull --rebase
git log --oneline -3
# → 77c1d2e fromA  (rejoué)
#   e281bf4 fromB
#   1a8c478 c1
```

- Quiz : Branches divergentes, aucun `pull.rebase` configuré (Git récent) : que fait `git pull` ?
- [ ] Un merge automatique, comme avant
- [ ] Un rebase automatique
- [x] Refuse : `Need to specify how to reconcile divergent branches`
- [ ] Écrase les commits locaux par le distant
- Réponse : il refuse : Git récent exige de choisir `--rebase`, `--no-rebase` ou `--ff-only` (ou `git config pull.rebase true`) ; mesuré avec Git 2.39.

## 10. .gitignore : la dernière règle gagne
- Id : git-gitignore-derniere-regle
- Sous-thème : gitignore
- Type : piège
- Niveau : 2
- Profils : ops
- Mots-clés : glob, tfvars
- Source : data-platform · S1-04
- Définition : Dans `.gitignore`, un chemin suit la dernière ligne qui le désigne ; `!motif` ré-inclut ce qu'une ligne précédente excluait.
- Contexte : Git lit le fichier de haut en bas, sans priorité au motif le plus précis : l'ordre fait la règle, d'où « exclure large, ré-inclure le commitable, re-exclure le secret ». Un fichier sous un dossier exclu ne peut pas être ré-inclus : Git ne descend plus dedans. `git check-ignore` teste un chemin même inexistant ; piège : `-v` affiche aussi la ligne `!` qui ré-autorise, code 0 ; seul `-q` et son code retour tranchent.
- Usage : ✅ commiter `dev.tfvars` sans jamais `local.tfvars`, tester les règles avec `git check-ignore` avant le premier `git add` · ❌ exclure un dossier entier pour en ré-inclure un fichier : exclure par motif de fichier (`*.tfvars`).

```bash
# Exemple 1 : l'ordre de data-platform
# .gitignore
#   *.tfvars
#   !infra/envs/*/*.tfvars
#   infra/envs/*/local.tfvars
git status --short --untracked-files=all
# → ?? infra/envs/dev/dev.tfvars
#   (local.tfvars reste ignoré)
git check-ignore -v \
  infra/envs/dev/local.tfvars
# → .gitignore:3:infra/envs/*/local.tfvars
```

```bash
# Exemple 2 : lignes 2 et 3 inversées
#   *.tfvars
#   infra/envs/*/local.tfvars
#   !infra/envs/*/*.tfvars
git status --short --untracked-files=all
# → ?? infra/envs/dev/dev.tfvars
#   ?? infra/envs/dev/local.tfvars
#   (le secret devient commitable)
```

```bash
# Exemple 3 : -v montre aussi l'exception
# .gitignore : *.tfvars
#              !*.auto.tfvars.example
git check-ignore -v \
  a.auto.tfvars.example; echo $?
# → .gitignore:2:!*.auto.tfvars.example
# → 0  (ligne en ! : NON ignoré)
git check-ignore -q \
  a.auto.tfvars.example; echo $?
# → 1  (non ignoré)
```

- Quiz : `.gitignore` contient `envs/` puis `!envs/dev/dev.tfvars` : `dev.tfvars` apparaît-il dans `git status` ?
- [ ] Oui : la ré-inclusion vient après
- [x] Non : son dossier parent est exclu
- [ ] Oui : le motif le plus précis gagne
- [ ] Non : `!` ne marche qu'en début de fichier
- Réponse : non : `envs/` exclut le dossier, Git n'y descend plus et `!` ne peut rien ré-inclure dedans (mesuré : `check-ignore` → `.gitignore:1:envs/`).

## 11. .gitignore : relatif à son dossier
- Id : git-gitignore-relatif-dossier
- Sous-thème : gitignore
- Type : piège
- Niveau : 2
- Profils : web, ops
- Mots-clés : glob, .gitignore
- Source : revision-pwa · pwa-revision
- Définition : Un `.gitignore` de sous-dossier se lit depuis son propre dossier : ses motifs ne partent pas de la racine du dépôt.
- Contexte : Un motif avec un `/` au début ou au milieu (`/dist/`, `apps/revision/dist/`) est ancré au dossier du `.gitignore`. Recopier dans `apps/revision/.gitignore` un chemin écrit pour la racine vise donc `apps/revision/apps/revision/dist/` : rien n'est ignoré, sans message. Le `/` final seul ne compte pas : il dit seulement « un dossier ».
- Usage : ✅ motifs locaux au sous-projet (`/dist/`, `/coverage/`) dans son `.gitignore` · ❌ chemin écrit depuis la racine dans un sous-dossier : le mettre dans le `.gitignore` racine.

```bash
# Exemple 1 : chemin racine recopié
# apps/revision/.gitignore :
#   apps/revision/dist/
git status --short -uall
# → ?? apps/revision/dist/a.js
# pas ignoré : le motif vise
# apps/revision/apps/revision/dist/
```

```bash
# Exemple 2 : ancré au dossier
# apps/revision/.gitignore :
#   /dist/
git check-ignore -v \
  apps/revision/dist/a.js
# → apps/revision/.gitignore:1:/dist/
```

- Quiz : Dans `apps/revision/.gitignore`, la ligne `dist/` ignore-t-elle `apps/revision/apps/revision/dist/b.js` ?
- [ ] Non : seul `apps/revision/dist/` est visé
- [x] Oui : sans `/` intérieur, le motif vaut à toute profondeur
- [ ] Non : un sous-dossier n'accepte que des chemins complets
- Réponse : oui : sans `/` au début ou au milieu (le `/` final ne compte pas), le motif s'applique à tout niveau sous le dossier du `.gitignore` ; `/dist/` l'ancre.

## 12. credential helper : un par hôte
- Id : git-credential-helper-par-hote
- Sous-thème : config
- Type : concept
- Niveau : 2
- Profils : ops
- Mots-clés : forge, CodeCommit, dépôt git
- Source : data-platform · S1-01
- Définition : Un credential helper fournit à git le login d'un dépôt HTTPS ; `gh auth setup-git` déclare `gh` comme helper de `https://github.com` seulement.
- Contexte : La clé générique `credential.helper` (ici `osxkeychain`) sert à tous les hôtes ; une clé par URL, `credential.https://github.com.helper`, s'ajoute pour un hôte. `gh` y écrit d'abord une valeur vide, qui vide la liste héritée : seul `gh` répond pour GitHub, le keychain reste pour GitLab. Si « Authenticate Git » n'a pas été appliqué au `gh auth login`, `gh auth setup-git` le refait.
- Usage : ✅ un helper par forge : `gh` pour GitHub, `aws codecommit credential-helper` pour CodeCommit · ❌ remplacer le `credential.helper` global : les autres forges perdent leur login.

```bash
# Exemple 1 : ce que gh écrit
gh auth setup-git
git config --global --get-regexp \
  'credential.*github'
# credential.https://github.com.helper
#   (valeur vide : liste remise à zéro)
# credential.https://github.com.helper
#   !gh auth git-credential
```

```bash
# Exemple 2 : qui répond pour quel hôte
git config --get-urlmatch \
  credential.helper https://github.com
# → !gh auth git-credential
git config --get-urlmatch \
  credential.helper https://gitlab.com
# → osxkeychain
```

- Quiz : Après `gh auth setup-git`, que renvoie `git config --global --get-all credential.helper` ?
- [x] `osxkeychain` seul
- [ ] `!gh auth git-credential` seul
- [ ] `osxkeychain` puis `!gh auth git-credential`
- [ ] Rien : gh a vidé la liste
- Réponse : `osxkeychain` seul : gh écrit sous la clé par URL `credential.https://github.com.helper`, que `--get-all credential.helper` ne lit pas ; vérifier avec `--get-regexp credential`.

## 13. merge : fast-forward ou commit de merge
- Id : git-merge-fast-forward
- Sous-thème : branches
- Type : comparaison
- Niveau : 2
- Profils : ops
- Prérequis : git-branche-pointeur
- Voir aussi : git-rebase-rejouer-commits
- Mots-clés : commit, MR, rebase
- Définition : `git merge feat` avance simplement `main` si elle n'a pas bougé (fast-forward) ; sinon il crée un commit de merge à deux parents.
- Contexte : Fast-forward : aucun nouveau commit, l'historique reste linéaire et la trace de la branche disparaît. `--no-ff` force un commit de merge même quand l'avance suffirait : la fonctionnalité reste groupée et un seul `revert` l'annule. C'est le comportement d'une MR GitLab par défaut (« merge commit »). `--ff-only` fait l'inverse : avancer ou échouer, jamais de merge.
- Usage : ✅ `--no-ff` pour intégrer une branche de ticket, `--ff-only` pour suivre `main` en local · ❌ merge de `main` dans sa branche à chaque pull : historique illisible, préférer un rebase local.

```bash
# Exemple 1 : main n'a pas bougé
git merge feat
# → Updating d7cd8ae..9773d59
#   Fast-forward  (aucun commit créé)
```

```bash
# Exemple 2 : forcer le commit de merge
git merge --no-ff -m "merge feat" feat
git log --oneline --graph -3
# *   d2579c7 merge feat
# |\
# | * 9773d59 feat1
# |/
# * d7cd8ae rewrite
```

- Quiz : `main` et `feat` ont chacune un commit propre : que fait `git merge --ff-only feat` ?
- [ ] Crée un commit de merge
- [ ] Rejoue `feat` au-dessus de `main`
- [x] `fatal: Not possible to fast-forward, aborting.`
- [ ] Avance `main` et abandonne son commit
- Réponse : il échoue : avancer `main` jusqu'à `feat` perdrait le commit de `main` ; `--ff-only` refuse tout merge réel (mesuré).

## 14. rebase : rejouer ses commits
- Id : git-rebase-rejouer-commits
- Sous-thème : branches
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : git-branche-pointeur
- Voir aussi : git-push-force-with-lease, git-ours-theirs-rebase
- Mots-clés : commit, hash de commit, reflog, push forcé
- Définition : `git rebase main` rejoue les commits de la branche courante au-dessus de `main` : historique linéaire, mais chaque commit rejoué reçoit un nouveau hash.
- Contexte : Git calcule les commits de `feat` absents de `main`, se place sur `main` et réapplique chacun comme un nouveau commit (même message, autre parent, donc autre hash). Les anciens restent dans le reflog. Règle d'or : ne jamais rebaser des commits déjà poussés sur une branche partagée ; sur sa propre branche de MR, c'est courant, suivi d'un `push --force-with-lease`.
- Usage : ✅ remettre sa branche de ticket à jour de `main` avant la MR · ❌ rebaser `main` ou une branche où d'autres poussent : leurs commits divergent.

```bash
# Exemple 1 : le hash change
git switch feat
git rev-parse --short HEAD  # → 9773d59
git rebase main
git rev-parse --short HEAD  # → 7641396
# même message, autre parent
```

```bash
# Exemple 2 : conflit pendant le rebase
git rebase main
# → CONFLICT … Merge conflict in c
# corriger c, puis :
git add c && git rebase --continue
# ou tout annuler :
git rebase --abort
```

- Quiz : Sur `feat`, `git rebase main` réussit : que devient la branche `main` ?
- [ ] Elle avance sur le dernier commit de `feat`
- [x] Rien : seule `feat` est déplacée
- [ ] Elle reçoit les commits de `feat` réécrits
- [ ] Elle est rebasée sur `feat` en retour
- Réponse : rien : `rebase` ne déplace que la branche courante (`main` garde son hash, mesuré) ; il faut ensuite un merge, fast-forward, dans `main`.

## 15. conflit : marqueurs et résolution
- Id : git-conflit-marqueurs
- Sous-thème : branches
- Type : recette
- Niveau : 2
- Profils : débutant
- Prérequis : git-merge-fast-forward
- Voir aussi : git-ours-theirs-rebase, uv-lock-conflit-git
- Mots-clés : merge, rebase, hook, HEAD
- Définition : En conflit, Git écrit les deux versions entre `<<<<<<<`, `=======` et `>>>>>>>` ; on édite, puis `git add` marque le fichier résolu.
- Contexte : Le haut (`HEAD`) est la branche courante, le bas la branche fusionnée. `git status` marque le fichier `UU` (modifié des deux côtés). Résoudre = garder le bon contenu et supprimer les trois marqueurs, puis `git add` et `git commit` (ou `rebase --continue`). `git merge --abort` remet tout comme avant. L'IDE propose « Accept current / incoming » : mêmes deux côtés.
- Usage : ✅ résoudre fichier par fichier, relancer les tests avant le commit · ❌ `git add .` dès le conflit affiché : les marqueurs partent dans le commit.

```bash
# Exemple 1 : le fichier en conflit
git merge main
# → CONFLICT (content): Merge conflict in f
git status --short     # → UU f
cat f
# <<<<<<< HEAD
# feat           (branche courante)
# =======
# main           (branche fusionnée)
# >>>>>>> main
```

```bash
# Exemple 2 : résoudre ou annuler
printf "feat\nmain\n" > f  # le bon contenu
git add f && git commit --no-edit
# ou, pour tout défaire :
git merge --abort
```

- Quiz : On fait `git add f` sans retirer les marqueurs, puis `git commit` : que se passe-t-il ?
- [ ] Git refuse : marqueurs détectés
- [x] Le commit passe, marqueurs compris
- [ ] Git retire les marqueurs tout seul
- [ ] Le fichier reste `UU`, rien n'est commité
- Réponse : le commit passe : `git add` vaut « résolu » sans lire le contenu (mesuré) ; un hook (`check-merge-conflict` de pre-commit) ou les tests l'attrapent.

## 16. reset : --soft, --mixed, --hard
- Id : git-reset-trois-modes
- Sous-thème : historique
- Type : comparaison
- Niveau : 2
- Profils : ops
- Prérequis : git-diff-disque-index-head, git-branche-pointeur
- Voir aussi : git-reflog-commit-perdu, git-revert-commit-publie
- Mots-clés : index git, HEAD, push forcé, revert
- Définition : `git reset <commit>` recule la branche : `--soft` garde index et disque, `--mixed` (défaut) vide l'index, `--hard` écrase le disque.
- Contexte : Les trois déplacent le pointeur de branche : les commits « annulés » sortent de l'historique visible. `--soft HEAD~1` défait un commit en gardant tout stagé (re-commiter autrement) ; `--mixed` garde les modifs sur le disque, non stagées ; `--hard` perd aussi le travail non commité, sans retour possible pour celui-ci. Réécrire un historique déjà poussé impose un push forcé.
- Usage : ✅ `--soft HEAD~1` pour refaire le dernier commit local, `--hard` pour repartir de `origin/main` · ❌ `reset` sur un commit déjà partagé : `git revert`.

```bash
# Exemple 1 : les trois modes sur HEAD~1
git reset --soft HEAD~1
git status --short   # → M  f  (stagé)
git reset HEAD~1     # --mixed
git status --short   # →  M f  (disque)
git reset --hard HEAD~1
git status --short   # → (rien : perdu)
```

```bash
# Exemple 2 : s'aligner sur le distant
git fetch
git reset --hard origin/main
# branche = distant, travail local jeté
```

- Quiz : Après `git reset --hard`, que devient `notes.txt`, jamais ajouté à git ?
- [ ] Supprimé, comme les modifs suivies
- [x] Toujours là, en `??`
- [ ] Mis dans le stash automatiquement
- [ ] Restauré à sa version de `HEAD`
- Réponse : toujours là : `reset --hard` ne touche qu'aux fichiers suivis ; `git clean -n` liste les non suivis, `-f` les supprime (mesuré).

## 17. revert : annuler un commit publié
- Id : git-revert-commit-publie
- Sous-thème : historique
- Type : recette
- Niveau : 2
- Profils : ops
- Voir aussi : git-reset-trois-modes
- Mots-clés : commit, CI, rollback
- Définition : `git revert <commit>` crée un nouveau commit qui applique l'inverse de celui visé : l'historique n'est pas réécrit, le push reste normal.
- Contexte : C'est l'annulation des branches partagées : `main` déjà poussée, déployée par la CI. Le commit fautif reste visible, suivi de `Revert "…"` : la trace est complète et personne ne diverge. Pour un commit de merge, il faut dire quel parent garder (`-m 1` = la branche où l'on avait fusionné). Le revert d'un revert ré-applique le changement.
- Usage : ✅ défaire en prod un commit déjà poussé, rollback par Git puis pipeline · ❌ commit encore local : `reset` ou `--amend`, plus propre.

```bash
# Exemple 1 : nouveau commit inverse
git revert --no-edit HEAD
# → [main 4f7397e] Revert "c3"
git log --oneline -2
# 4f7397e Revert "c3"
# 5b9eb79 c3   (toujours là)
git push     # sans --force
```

- Quiz : `HEAD` est un commit de merge : que fait `git revert --no-edit HEAD` ?
- [ ] Annule les deux branches fusionnées
- [ ] Annule le dernier commit de la branche fusionnée
- [x] `error: commit … is a merge but no -m option was given.`
- [ ] Supprime le commit de merge de l'historique
- Réponse : erreur : un merge a deux parents, Git doit savoir lequel garder ; `git revert -m 1 HEAD` revient à l'état de `main` avant le merge (mesuré).

## 18. cherry-pick : recopier un commit
- Id : git-cherry-pick
- Sous-thème : historique
- Type : recette
- Niveau : 2
- Profils : ops
- Mots-clés : hotfix, hash de commit, commit
- Définition : `git cherry-pick <hash>` rejoue un commit d'une autre branche sur la branche courante, sous un nouveau hash.
- Contexte : Cas typique : un correctif fait sur une branche de ticket doit partir tout de suite sur `main` ou une branche de release, sans le reste de la branche. Le commit recopié a le même message et le même diff, mais un autre parent, donc un autre hash : les deux branches portent deux commits distincts. `-x` ajoute « (cherry picked from commit …) » au message pour la traçabilité.
- Usage : ✅ hotfix à porter sur une branche de release, commit poussé sur la mauvaise branche · ❌ ramener une branche entière commit par commit : `merge` ou `rebase`.

```bash
# Exemple 1 : porter un fix sur main
git switch main
git cherry-pick 6268473
# → [main 30fcaf6] fix urgent
# 6268473 sur fix, 30fcaf6 sur main
```

```bash
# Exemple 2 : garder la trace
git cherry-pick -x 6268473
git log -1 --format=%B
# fix urgent
#
# (cherry picked from commit 6268473…)
```

- Quiz : On relance `git cherry-pick 6268473` alors que le fix est déjà appliqué sur `main` : résultat ?
- [ ] Un second commit identique
- [ ] Rien, sans message
- [x] Arrêt : `The previous cherry-pick is now empty`
- [ ] Un conflit sur tous les fichiers du fix
- Réponse : il s'arrête : le diff est déjà présent, le commit serait vide ; `--skip` passe, `--allow-empty` commite quand même (mesuré).

## 19. push --force-with-lease : forcer prudemment
- Id : git-push-force-with-lease
- Sous-thème : remote
- Type : comparaison
- Niveau : 2
- Profils : ops
- Prérequis : git-fetch-ou-pull
- Voir aussi : git-commit-amend
- Mots-clés : rebase, dépôt distant, MR, branche protégée
- Définition : `git push --force-with-lease` écrase la branche distante seulement si elle est encore là où ton dernier fetch l'a vue.
- Contexte : `--force` écrase sans condition : le commit qu'un collègue vient de pousser disparaît. `--force-with-lease` compare la branche distante à `origin/<branche>` local : si quelqu'un a poussé entre-temps, refus `(stale info)`. Indispensable après un `rebase` ou un `--amend` de sa branche de MR. GitLab protège `main` contre tout push forcé par défaut.
- Usage : ✅ après rebase ou amend de sa propre branche de MR · ❌ `--force` nu ; tout push forcé sur `main` ou une branche partagée.

```bash
# Exemple 1 : un collègue a poussé
git rebase main     # sur feat : réécrit
git push --force-with-lease
# → ! [rejected] feat -> feat
#   (stale info)  : rien d'écrasé
```

- Quiz : Même situation, mais on lance `git fetch` juste avant `git push --force-with-lease` : résultat ?
- [ ] Refusé : `(stale info)`, comme sans fetch
- [x] Accepté : le commit du collègue est écrasé
- [ ] Accepté, en gardant le commit du collègue
- [ ] Refusé : `(fetch first)`
- Réponse : accepté, et le commit du collègue est perdu : le fetch a mis `origin/feat` à jour, la « lease » correspond ; relire `git log ..origin/feat` avant de forcer (mesuré).

## 20. tag : léger ou annoté, poussé à part
- Id : git-tag-leger-ou-annote
- Sous-thème : remote
- Type : concept
- Niveau : 2
- Profils : ops
- Mots-clés : commit, CI, release
- Définition : Un tag nomme un commit pour toujours (`v1.1.0`) ; annoté (`-a`), c'est un objet avec auteur, date et message ; léger, un simple pointeur.
- Contexte : Les tags marquent les versions déployées et servent de déclencheur de CI (pipeline de release). Annoté pour une release : `git describe` et `--follow-tags` les utilisent. Piège : `git push` n'envoie aucun tag ; il faut `git push origin v1.1.0` ou `--follow-tags`. Un tag déjà poussé ne se déplace pas : on en crée un nouveau.
- Usage : ✅ `git tag -a v1.2.0 -m …` à chaque release, poussé explicitement · ❌ déplacer un tag publié (`-f`) : les clones gardent l'ancien.

```bash
# Exemple 1 : léger ou annoté
git tag v1.0.0                  # léger
git tag -a v1.1.0 -m "release"  # annoté
git cat-file -t v1.0.0   # → commit
git cat-file -t v1.1.0   # → tag
```

```bash
# Exemple 2 : push ne pousse pas les tags
git push
git ls-remote --tags origin  # → (rien)
git push origin v1.1.0
# → * [new tag]  v1.1.0 -> v1.1.0
```

- Quiz : Avec ces deux tags locaux, que pousse `git push --follow-tags` ?
- [ ] Les deux tags
- [x] `v1.1.0` seulement
- [ ] `v1.0.0` seulement
- [ ] Aucun : il faut `--tags`
- Réponse : `v1.1.0` seulement : `--follow-tags` n'envoie que les tags annotés qui pointent sur des commits poussés ; `--tags` enverrait tout (mesuré).

## 21. reflog : retrouver un commit perdu
- Id : git-reflog-commit-perdu
- Sous-thème : historique
- Type : recette
- Niveau : 3
- Profils : ops, expert
- Prérequis : git-reset-trois-modes
- Mots-clés : HEAD, rebase, commit
- Définition : `git reflog` liste chaque position passée de `HEAD` (commit, reset, rebase) : un commit « perdu » s'y retrouve par `HEAD@{n}`.
- Contexte : Un commit n'est jamais effacé tout de suite : après `reset --hard` ou un rebase raté, il n'est plus référencé par une branche mais reste dans la base, et le reflog garde son hash (30 jours par défaut pour un commit devenu inaccessible, 90 sinon). Le reflog est local à ton dépôt : un clone neuf ne connaît pas ton historique de déplacements. C'est le filet de sécurité de `reset`, `amend` et `rebase`.
- Usage : ✅ annuler un `reset --hard`, un rebase ou un amend raté · ❌ chercher un travail jamais commité : seul un commit (ou un stash) laisse une trace.

```bash
# Exemple 1 : défaire un reset --hard
git reset --hard HEAD~1   # oups
git reflog -2
# a397966 HEAD@{0}: reset: moving to HEAD~1
# 5b9eb79 HEAD@{1}: commit: c3
git reset --hard HEAD@{1}
git log --oneline -1      # → 5b9eb79 c3
```

```bash
# Exemple 2 : rebase raté
git reset --hard ORIG_HEAD
# ORIG_HEAD : position avant le dernier
# rebase, merge ou reset
```

- Quiz : `reset --hard` vient d'effacer une modification jamais commitée de `f` : le reflog la retrouve-t-il ?
- [ ] Oui, dans `HEAD@{1}`
- [ ] Oui, avec `git reflog --all`
- [ ] Oui, dans `ORIG_HEAD`
- [x] Non : elle n'a jamais été un commit
- Réponse : non : le reflog ne trace que des commits ; une modif non commitée écrasée par `--hard` est perdue (mesuré : `HEAD@{1}` rend `c3`, pas la modif).

## 22. conflit : ours et theirs s'inversent en rebase
- Id : git-ours-theirs-rebase
- Sous-thème : branches
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : git-conflit-marqueurs, git-rebase-rejouer-commits
- Mots-clés : rebase, merge, conflit git
- Définition : En merge, `--ours` est ta branche courante ; en rebase, c'est la branche de base (`main`), car Git rejoue tes commits par-dessus.
- Contexte : Pendant `git rebase main`, Git se place sur `main` puis applique tes commits un à un : la branche « courante » est alors `main`, et tes commits sont « theirs ». Même inversion dans les marqueurs (`HEAD` = `main`) et dans les boutons « current / incoming » de l'IDE. Résoudre un conflit de rebase en prenant `--ours` par réflexe jette donc ton propre travail.
- Usage : ✅ vérifier le contenu (`git diff`) avant de choisir un côté · ❌ `git checkout --ours .` en masse pendant un rebase, en croyant garder son code.

```bash
# Exemple 1 : en merge, ours = moi
git switch feat
git merge main        # conflit sur c
git checkout --ours c
cat c                 # → feat
git merge --abort
```

- Quiz : Sur `feat`, `git rebase main` s'arrête en conflit sur `c` : que contient `c` après `git checkout --ours c` ?
- [x] La version de `main`
- [ ] La version de `feat`
- [ ] Les deux, avec les marqueurs
- [ ] La version de l'ancêtre commun
- Réponse : la version de `main` : en rebase, « ours » est la base sur laquelle on rejoue ; `--theirs` rend celle de `feat` (mesuré).

## 23. hook commit-msg : imposer le préfixe
- Id : git-hook-commit-msg
- Sous-thème : commit
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Voir aussi : pre-commit-install-par-clone
- Mots-clés : pre-commit, index git, CI
- Définition : Un hook est un script de `.git/hooks/` lancé par Git à un moment précis ; `commit-msg` lit le message et annule le commit s'il échoue.
- Contexte : Hooks locaux et non versionnés (`.git/` ne part jamais) : chaque clone doit les installer, d'où pre-commit, qui les génère depuis un fichier commité. `pre-commit` lit l'index, `commit-msg` le fichier du message (`$1`), `pre-push` les refs à pousser. `--no-verify` saute `pre-commit` et `commit-msg` : le hook est un confort, la CI reste le garde-fou.
- Usage : ✅ préfixe `RLINK-123: ` imposé, secret détecté avant le commit · ❌ seul contrôle d'une règle obligatoire : la refaire en CI.

```bash
# Exemple 1 : .git/hooks/commit-msg
#!/bin/sh
b=$(git branch --show-current)
grep -q "^$b: " "$1" || {
  echo "message sans préfixe $b:"
  exit 1; }
```

```bash
# Exemple 2 : en action
chmod +x .git/hooks/commit-msg
git commit -m "oubli"
# → message sans préfixe RLINK-123:
#   (code 1, pas de commit)
git commit -m "RLINK-123: ok"  # passe
git commit --no-verify -m "oubli"
# → passe : hook sauté
```

- Quiz : On oublie le `chmod +x` du hook : que fait `git commit -m "oubli"` ?
- [ ] Refusé : le hook bloque toujours
- [x] Commit créé, avec un `hint` : hook ignoré
- [ ] `Permission denied`, pas de commit
- [ ] Git lance le hook avec `sh` quand même
- Réponse : commit créé : Git ignore un hook non exécutable et l'indique (`hint: … hook was ignored because it's not set as executable`) ; mesuré.
