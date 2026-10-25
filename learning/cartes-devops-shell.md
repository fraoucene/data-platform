---
title: "Cartes · Shell"
type: cartes
langage: DevOps
cours: Shell
created: 2026-10-25
updated: 2026-10-25
---

# Cartes · Shell
DevOps · Shell (zsh, bash) : redirections, guillemets, expansion, enchaînement, variables (format spec v3 de revision-pwa).

## 1. < : lire un fichier en entrée
- Sous-thème : redirections
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `cmd < fichier` branche le fichier sur l'entrée standard de la commande ; le shell l'ouvre avant de lancer la commande.
- Contexte : Le `<` est lu par le shell, pas par la commande : où qu'il soit dans la ligne, le mot collé derrière est un nom de fichier. Un placeholder de doc comme `<raw>` devient donc « lire le fichier `raw` », et zsh échoue avant même d'appeler `aws` : `no such file or directory: raw`. Remplacer le placeholder, ou le mettre entre guillemets s'il doit rester littéral.
- Usage : ✅ donner un fichier à une commande qui lit stdin (`wc -l < f`, `psql < schema.sql`) · ❌ recopier tel quel un `<placeholder>` de doc : le remplacer par la vraie valeur.

```bash
# Exemple 1 : le placeholder lu comme une redirection
aws s3api head-object \
  --bucket <raw> --key k
# → zsh: no such file or directory: raw
#   (aws n'est jamais lancé)
```

```bash
# Exemple 2 : la vraie valeur, lue d'un output
B=$(terraform -chdir=infra output \
  -json bucket_names | jq -r .raw)
aws s3api head-object \
  --bucket "$B" --key k
```

- Quiz : Le fichier `raw` existe. Que fait `cat --bucket <raw> --key x` en plus de lancer `cat` ?
- [ ] Rien : `<raw>` est passé tel quel à `cat`
- [x] Crée un fichier vide nommé `--key`
- [ ] Écrit le contenu de `raw` dans `x`
- [ ] Refuse : `<` doit être en fin de ligne
- Réponse : crée `--key` : `<raw` lit le fichier `raw`, puis `>` redirige la sortie vers le mot suivant, `--key`, créé ou vidé (mesuré).

## 2. > et >> : écraser ou ajouter
- Sous-thème : redirections
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `cmd > f` écrit la sortie standard dans `f` en l'écrasant ; `cmd >> f` l'ajoute à la fin.
- Contexte : Le fichier est vidé par le shell avant que la commande démarre : `sort f > f` donne un fichier vide, car `sort` lit un fichier déjà tronqué. Seule la sortie standard est redirigée ; les erreurs (stderr) restent à l'écran. zsh peut refuser d'écraser avec `setopt noclobber` (`>|` force).
- Usage : ✅ `>` pour un résultat régénéré (`out.json`), `>>` pour un journal · ❌ `cmd f > f` : écrire dans un fichier temporaire puis `mv`.

```bash
# Exemple 1 : écraser puis ajouter
echo 1 > g
echo 2 > g      # 1 est perdu
echo 3 >> g
cat g
# → 2
#   3
```

- Quiz : Que contient `f` après `sort f > f`, si `f` contenait trois lignes ?
- [ ] Les trois lignes triées
- [x] Rien : `f` est vide
- [ ] Les trois lignes d'origine
- [ ] Erreur : fichier déjà ouvert
- Réponse : rien : le shell vide `f` en ouvrant la redirection, avant que `sort` ne le lise.

## 3. /dev/null : jeter une sortie
- Sous-thème : redirections
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `/dev/null` est un fichier spécial qui avale tout ce qu'on y écrit ; `2>/dev/null` fait taire les erreurs d'une commande.
- Contexte : `2` est le numéro de stderr, `1` celui de stdout. Jeter stderr cache le message, pas l'échec : le code de sortie `$?` reste non nul. Jeter les erreurs d'une commande dont le résultat sert ensuite masque souvent la vraie cause d'un bug.
- Usage : ✅ commande bavarde dont seul le code de retour compte, `test -f x 2>/dev/null` · ❌ cacher les erreurs d'un `aws …` dont on lit ensuite la sortie : garder stderr.

```bash
# Exemple 1 : message caché, échec gardé
ls /nope 2>/dev/null
echo "rc=$?"
# → rc=1   (rien d'autre affiché)
```

```bash
# Exemple 2 : seulement le résultat
aws s3 ls s3://"$B"/bodacc/ \
  2>/dev/null | wc -l
```

- Quiz : Que fait `ls /nope > /dev/null` ?
- [ ] N'affiche rien
- [x] Affiche quand même l'erreur
- [ ] Crée un fichier `/nope`
- [ ] Échoue : `/dev/null` est en lecture seule
- Réponse : affiche l'erreur : `>` ne redirige que stdout (1) ; le message passe par stderr (2).

## 4. guillemets simples : rien n'est interprété
- Sous-thème : guillemets
- Niveau : 1
- Source : data-platform · S1-07
- Définition : Entre guillemets simples, le shell ne touche à rien : `$`, `` ` ``, `*`, `[` et `"` restent des caractères ordinaires.
- Contexte : C'est l'écriture des payloads JSON et des requêtes JMESPath : leurs `"`, `[` et `` ` `` passent intacts à la commande. Revers : impossible d'y insérer une variable, ni un guillemet simple (on ferme, on écrit `\'`, on rouvre). Contrairement à JS, `'` et `"` ne sont pas interchangeables.
- Usage : ✅ `--payload '{"date":"2026-10-20"}'`, `--query 'Versions[?IsLatest]'`, `jq '.count'` · ❌ texte qui doit contenir une variable : guillemets doubles.

```bash
# Exemple 1 : le JSON passe intact
aws lambda invoke \
  --function-name "$F" \
  --payload '{"date":"2026-10-20"}' \
  --cli-binary-format raw-in-base64-out \
  out.json
```

```bash
# Exemple 2 : la variable reste du texte
B=dp-raw
echo '$B' "$B"
# → $B dp-raw
```

- Quiz : Que reçoit `aws` avec `--payload '{"date":"$D"}'`, si `D=2026-10-20` ?
- [ ] `{"date":"2026-10-20"}`
- [x] `{"date":"$D"}`
- [ ] `{date:2026-10-20}`
- [ ] Une erreur de syntaxe du shell
- Réponse : `{"date":"$D"}` : rien n'est développé entre guillemets simples ; Lambda reçoit la chaîne `$D`.

## 5. $( ) : le résultat d'une commande
- Sous-thème : expansion
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `$(cmd)` est remplacé par ce que `cmd` écrit sur stdout, sans le retour à la ligne final (≈ un `await exec()` inline).
- Contexte : Sert à lire une valeur calculée ailleurs : nom de bucket dans les outputs Terraform, branche git, date. Seul stdout est capturé : un message d'erreur s'affiche, la variable reste vide et la ligne suivante tourne quand même (sauf `set -e`). Entourer de guillemets (`"$(…)"`) garde les espaces. L'ancienne écriture `` `cmd` `` fait la même chose mais s'imbrique mal.
- Usage : ✅ `B=$(terraform output -raw …)`, `git branch --show-current` · ❌ résultat sur plusieurs lignes à parcourir : `while read` sur un pipe.

```bash
# Exemple 1 : capturer une valeur
BR=$(git branch --show-current)
echo "$BR: message"
# → main: message
```

```bash
# Exemple 2 : un output Terraform
B=$(terraform -chdir=infra output \
  -json bucket_names | jq -r .raw)
echo "$B"
# → data-platform-dev-raw-<account_id>
```

- Quiz : `terraform output` échoue (état absent) : que vaut `$B` après `B=$(terraform output -raw x)` ?
- [ ] Le message d'erreur
- [x] Une chaîne vide
- [ ] `null`
- [ ] La ligne s'arrête, `B` n'existe pas
- Réponse : une chaîne vide : l'erreur part sur stderr, non capturée ; `$?` vaut le code de la commande (mesuré : `1`), mais rien ne s'arrête.

## 6. && et || : enchaîner selon le résultat
- Sous-thème : enchaînement
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `a && b` lance `b` si `a` réussit (code 0), `a || b` si `a` échoue, `a ; b` dans tous les cas.
- Contexte : Réussite = code de sortie 0, échec = tout le reste : l'inverse de la vérité en JS, où `0` est faux. `a && b || c` n'est pas un if/else : `c` part aussi si `b` échoue. Dans un Makefile, chaque ligne s'arrête déjà au premier échec.
- Usage : ✅ `invoke … && cat out.json`, `cd d && make` · ❌ `a && b || c` comme if/else : écrire un vrai `if`.

```bash
# Exemple 1 : trois enchaînements
false && echo A   # rien
false || echo B   # → B
false ; echo C    # → C
```

```bash
# Exemple 2 : lire la réponse si OK
aws lambda invoke … out.json \
  && cat out.json
```

- Quiz : Que fait `true && false || echo X` ?
- [ ] N'affiche rien
- [x] Affiche `X`
- [ ] Erreur de syntaxe
- Réponse : affiche `X` : `false` échoue, donc le `||` s'applique, même si la première commande a réussi.

## 7. $? : le code de sortie
- Sous-thème : enchaînement
- Niveau : 1
- Source : data-platform · S1-07
- Définition : `$?` vaut le code de sortie de la dernière commande : `0` en cas de succès, de `1` à `255` sinon.
- Contexte : Il est écrasé par chaque commande, `echo` compris : le lire tout de suite, ou le copier (`rc=$?`). Le code ne dit pas toujours ce qui a échoué : `aws s3api` renvoie `254` pour une erreur de service, `252` pour un paramètre invalide (mesurés), `grep` renvoie `1` quand rien ne correspond, sans erreur.
- Usage : ✅ script qui décide selon le résultat, CI · ❌ deux lectures de `$?` d'affilée : la seconde lit le code du premier `echo`.

```bash
# Exemple 1 : lire tout de suite
ls /nope 2>/dev/null
echo $?   # → 1
echo $?   # → 0  (code du echo)
```

- Quiz : `grep -q SIREN f.txt` ne trouve rien, sans erreur de lecture : que vaut `$?` ?
- [ ] `0`
- [x] `1`
- [ ] `2`
- [ ] `127`
- Réponse : `1` : pour `grep`, 1 = aucune ligne trouvée, 2 = vraie erreur (fichier illisible).

## 8. 2>&1 : l'ordre compte
- Sous-thème : redirections
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `2>&1` envoie stderr là où va stdout **à ce moment** ; les redirections s'appliquent de gauche à droite.
- Contexte : `cmd > f 2>&1` : stdout va dans `f`, puis stderr suit stdout, donc dans `f`. `cmd 2>&1 > f` : stderr copie stdout quand il pointe encore vers l'écran, puis seul stdout part dans `f`. Raccourci zsh et bash : `cmd &> f`. Pour un pipe, `cmd 2>&1 | tail` capture les deux.
- Usage : ✅ `make check 2>&1 | tail -15`, journal complet d'une commande · ❌ `2>&1` placé avant `> f` : les erreurs restent à l'écran.

```bash
# Exemple 1 : deux ordres, deux résultats
ls /nope > f1 2>&1
ls /nope 2>&1 > f2
# → ls: /nope: No such file…  (f2)
wc -c < f1   # → 37
wc -c < f2   # → 0
```

- Quiz : `aws s3 ls s3://nope 2>&1 | grep -c Error` : qu'est-ce que `grep` reçoit ?
- [ ] Rien : les erreurs ne passent pas dans un pipe
- [x] stdout et stderr de `aws`
- [ ] Seulement stderr
- Réponse : les deux : `2>&1` est appliqué après le branchement du pipe, stderr suit donc stdout dans le pipe.

## 9. guillemets doubles : $ et ` restent actifs
- Sous-thème : guillemets
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Entre guillemets doubles, le shell développe `$VAR`, `$(cmd)` et `` `cmd` `` ; espaces et `*` restent littéraux.
- Contexte : Piège JMESPath : `--query "Versions[?IsLatest==`false`]"` lance la commande `false` à cause des accents graves ; le littéral devient vide et la CLI refuse la requête. Règle : guillemets simples pour JSON et JMESPath, doubles pour insérer une variable. Échapper avec `\$` ou `` \` `` quand il faut mélanger.
- Usage : ✅ `--bucket "$B"`, `"$BR: message"` · ❌ requête JMESPath ou payload JSON entre guillemets doubles : guillemets simples.

```bash
# Exemple 1 : la variable est développée
D=2026-10-20
echo "date=$D"
# → date=2026-10-20
```

```bash
# Exemple 2 : l'accent grave exécuté
echo "a==`false`b"
# → a==b   (false a été lancée)
echo 'a==`false`b'
# → a==`false`b
```

- Quiz : Que répond `aws s3api list-object-versions … --query "Versions[?IsLatest==`false`].VersionId"` ?
- [ ] Les VersionId non courants
- [ ] Une liste vide
- [x] `ParamValidation` : requête invalide
- [ ] Les VersionId courants
- Réponse : `ParamValidation` (mesuré) : le shell remplace `` `false` `` par rien, la CLI reçoit `IsLatest==]`, illisible.

## 10. glob zsh : no matches found
- Sous-thème : expansion
- Niveau : 2
- Source : data-platform · S1-07
- Définition : En zsh, un mot avec `*`, `?` ou `[…]` qui ne correspond à aucun fichier arrête la commande : `no matches found`.
- Contexte : bash passe le mot tel quel s'il ne trouve rien ; zsh refuse, par sécurité. D'où `uv add --dev "moto[s3]"` entre guillemets : sans eux, zsh cherche un fichier `moto` suivi de `s`, `3`. Même piège avec une URL contenant `?`, une clé S3 avec `*`, un `echo [x]`. Guillemets, ou `noglob` devant la commande.
- Usage : ✅ guillemets autour de tout argument avec `[`, `*` ou `?` qui n'est pas un motif de fichiers · ❌ `setopt nonomatch` global : masque les vrais globs ratés.

```bash
# Exemple 1 : extra pip en zsh
uv add --dev moto[s3]
# → zsh: no matches found: moto[s3]
uv add --dev "moto[s3]"   # OK
```

```bash
# Exemple 2 : bash ne bronche pas
bash -c 'echo moto[s3]'
# → moto[s3]
zsh -c 'echo moto[s3]'
# → no matches found: moto[s3]
```

- Quiz : En zsh, que fait `curl https://api.example/x?date=2026-10-20` ?
- [ ] Envoie la requête normalement
- [x] `no matches found` : `?` est un glob
- [ ] Coupe l'URL au `?`
- [ ] Ignore la query string
- Réponse : `no matches found` : `?` remplace un caractère dans un motif de fichiers ; aucun fichier ne correspond, zsh refuse.

## 11. pipe : seul le dernier code compte
- Sous-thème : enchaînement
- Niveau : 2
- Source : data-platform · S1-07
- Définition : Le code de sortie d'un pipe `a | b` est celui de `b` ; un échec de `a` passe inaperçu, sauf avec `set -o pipefail`.
- Contexte : `aws s3 cp … - | zcat | wc -l` peut afficher `0` et réussir alors que le téléchargement a échoué. Avec `pipefail`, le pipe échoue si une commande échoue. Côté Make, GitLab CI ou un script, l'activer (`set -o pipefail`) évite un job vert sur un résultat vide. Bonus zsh : `$pipestatus` donne le code de chaque étage.
- Usage : ✅ `set -euo pipefail` en tête de script, pipes dans la CI · ❌ conclure « OK » d'un pipe sans `pipefail` : le premier étage a pu échouer.

```bash
# Exemple 1 : l'échec du début est perdu
false | true
echo $?    # → 0
set -o pipefail
false | true
echo $?    # → 1
```

- Quiz : Sans `pipefail`, que vaut `$?` après `aws s3 cp s3://nope/k - | wc -l`, la clé n'existant pas ?
- [ ] `1`
- [ ] `254`
- [x] `0`
- Réponse : `0` : c'est le code de `wc`, qui a bien compté zéro ligne ; l'erreur de `aws` est perdue.

## 12. heredoc : <<'EOF' fige le texte
- Sous-thème : redirections
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `<<EOF … EOF` envoie un bloc de texte sur l'entrée standard ; avec `<<'EOF'`, rien n'y est développé.
- Contexte : Sans guillemets, `$X`, `$(…)` et `` ` `` sont développés dans le bloc ; avec `'EOF'`, le texte part tel quel. Le choix change tout pour un message de commit, un script Python ou un SQL injectés par `cat <<…` : un `$` ou un accent grave du contenu serait sinon remplacé. La ligne de fin doit être `EOF` seul, sans espace.
- Usage : ✅ `git commit -F - <<'EOF'`, `python - <<'EOF'` · ❌ `<<EOF` sur un contenu qui contient `$` ou `` ` `` : `<<'EOF'`.

```bash
# Exemple 1 : développé ou figé
X=1
cat <<EOF
v=$X
EOF
# → v=1
cat <<'EOF'
v=$X
EOF
# → v=$X
```

- Quiz : Message de commit écrit avec `<<EOF` contenant `` `make check` vert `` : que devient-il ?
- [ ] Reste tel quel
- [x] `make check` est lancé, sa sortie remplace le texte
- [ ] Erreur : accent grave interdit
- [ ] Les accents graves sont retirés
- Réponse : `make check` est lancé : sans `'EOF'`, `` `…` `` est une substitution de commande.

## 13. export : visible des commandes lancées
- Sous-thème : variables
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `A=1` crée une variable du shell seul ; `export A` la passe aux programmes lancés ensuite (≈ `process.env`).
- Contexte : Sans `export`, `aws`, `terraform` ou `python` ne voient pas la variable : `os.environ["A"]` lève `KeyError`. `export` vaut pour le reste de la session, pas pour les autres terminaux. `AWS_PROFILE`, `TF_VAR_x` ou `RAW_BUCKET` doivent être exportés (ou passés en préfixe) pour servir.
- Usage : ✅ `export AWS_PROFILE=data-platform` pour une session de travail · ❌ variable posée sans `export` puis lue par un script : rien ne passe.

```bash
# Exemple 1 : sans puis avec export
A=1
zsh -c 'echo "A=$A"'
# → A=
export A
zsh -c 'echo "A=$A"'
# → A=1
```

- Quiz : Un script lance `source vars.sh` qui contient `B=x` (sans `export`). Le script voit-il `B` ?
- [x] Oui : `source` exécute dans le shell courant
- [ ] Non : il faut `export`
- [ ] Seulement dans les sous-processus
- Réponse : oui : `source` lit le fichier dans le shell courant ; `export` ne compte que pour les programmes lancés ensuite.

## 14. VAR=x cmd : une variable pour une seule commande
- Sous-thème : variables
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `VAR=x cmd` passe `VAR` dans l'environnement de `cmd` seulement ; le shell courant ne la garde pas.
- Contexte : C'est la forme du Makefile pour DuckDB (`RAW_BUCKET=$$(terraform output …) duckdb`) : la variable n'existe que pour ce processus, rien ne fuit dans la session. Plusieurs affectations peuvent précéder la commande. Piège : `B=x echo $B` affiche vide, car `$B` est développé par le shell avant que l'affectation n'existe.
- Usage : ✅ configuration ponctuelle (`AWS_PROFILE=x aws …`, `RAW_BUCKET=… duckdb`) · ❌ variable utile à plusieurs commandes : `export`.

```bash
# Exemple 1 : vue par la commande seule
B=x zsh -c 'echo "B=$B"'
# → B=x
echo "B=$B"
# → B=
```

- Quiz : Que fait `D=2026-10-20 echo "$D"`, si `D` n'était pas définie ?
- [ ] Affiche `2026-10-20`
- [x] Affiche une ligne vide
- [ ] Erreur : affectation interdite
- Réponse : une ligne vide : `"$D"` est développé avant le lancement d'`echo`, quand `D` n'existe pas encore.

## 15. ~ : jamais entre guillemets
- Sous-thème : expansion
- Niveau : 2
- Source : data-platform · S1-07
- Définition : `~` devient le dossier personnel seulement s'il est hors guillemets et en début de mot ; `"~/x"` reste un tilde littéral.
- Contexte : `cd "~/Desktop"` cherche un dossier nommé `~` dans le dossier courant. Dans un script ou un `.env`, préférer `$HOME`, développé aussi entre guillemets doubles. Python ne développe pas non plus `~` : `Path("~/x").exists()` est faux sans `.expanduser()`.
- Usage : ✅ `~/x` sans guillemets, `"$HOME/x"` avec · ❌ `"~/…"` dans une config ou un argument : `"$HOME/…"`.

```bash
# Exemple 1 : développé ou non
echo "~" ~
# → ~ /Users/<moi>
echo "$HOME"
# → /Users/<moi>
```

```python
# Exemple 2 : Python non plus
from pathlib import Path

str(Path("~/x"))          # → '~/x'
str(Path("~/x").expanduser()).startswith("~")
# → False
```

- Quiz : Que vaut `ls "~"/Desktop` ?
- [ ] La liste de `~/Desktop`
- [x] Erreur : pas de dossier `~` ici
- [ ] La liste du dossier courant
- Réponse : erreur : entre guillemets, `~` est un caractère ordinaire ; `ls` cherche `./~/Desktop`.

## 16. zsh ne découpe pas $VAR
- Sous-thème : variables
- Niveau : 3
- Source : data-platform · S1-07
- Définition : En zsh, `$VAR` contenant des espaces reste un seul argument ; bash le découpe en plusieurs mots si on oublie les guillemets.
- Contexte : Un script testé dans le terminal zsh d'un Mac peut casser en CI, où `sh` ou `bash` découpe `$FICHIER` sur les espaces. Toujours écrire `"$VAR"` : correct dans les deux shells. Le shebang (`#!/usr/bin/env bash`) décide du shell, pas le terminal d'où on lance.
- Usage : ✅ `"$VAR"` partout dans un script, même sous zsh · ❌ compter sur le comportement zsh dans un script lancé par bash, `sh` ou la CI.

```bash
# Exemple 1 : même ligne, deux shells
V="a b"
printf '[%s]\n' $V
# zsh  → [a b]
# bash → [a]
#        [b]
```

- Quiz : Script `#!/usr/bin/env bash` lancé depuis zsh : `rm $F` avec `F="mes notes.txt"` supprime quoi ?
- [ ] `mes notes.txt`
- [x] Tente `mes` puis `notes.txt`
- [ ] Rien : erreur de syntaxe
- Réponse : `mes` puis `notes.txt` : le shebang lance bash, qui découpe `$F` non protégé en deux arguments.

## 17. set -euo pipefail : échouer tôt
- Sous-thème : enchaînement
- Niveau : 3
- Source : data-platform · S1-07
- Définition : En tête de script : `set -e` arrête au premier échec, `-u` refuse une variable non définie, `-o pipefail` propage l'échec d'un étage de pipe.
- Contexte : Par défaut, un script continue après une erreur et `$NOPE` vaut vide : `aws s3 rm s3://$B/$PREFIX --recursive` avec `PREFIX` vide vise tout le bucket. `-u` coupe avant. `-e` ne s'applique pas à une commande testée (`if`, `&&`, `||`). En CI, l'écrire explicitement plutôt que supposer les options du runner.
- Usage : ✅ tout script bash de build, de déploiement ou de CI · ❌ s'y fier dans une condition (`if cmd`) : tester `$?` ou le résultat soi-même.

```bash
# Exemple 1 : -u coupe avant le danger
set -u
echo "[${NOPE}]"
# → zsh: NOPE: parameter not set
#   rc=1, la suite n'est pas lancée
```

```bash
# Exemple 2 : -e arrête le script
set -e
false
echo apres   # jamais affiché
```

- Quiz : Avec `set -e`, que fait `false || echo X; echo Y` ?
- [ ] S'arrête sur `false`
- [x] Affiche `X` puis `Y`
- [ ] Affiche `Y` seulement
- Réponse : `X` puis `Y` : une commande suivie de `||` est testée, `set -e` ne s'applique pas à elle.
