---
title: "Cartes · jq"
type: cartes
langage: DevOps
chapitre: Terminal
cours: jq
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · jq
DevOps · jq : lire, filtrer, sortie, scripts (format spec v4 de revision-pwa).

## 1. . et .clé : lire un champ
- Id : jq-lire-champ
- Sous-thème : lire
- Type : concept
- Niveau : 1
- Profils : débutant, ops, data
- Voir aussi : jq-cle-avec-tiret, Terraform/cli-output-json-jq
- Mots-clés : JSON, entrée standard, output, CLI
- Source : data-platform · S1-08
- Définition : `jq '.clé'` lit un champ d'un JSON reçu sur l'entrée standard ; `.a.b` descend dans les objets imbriqués (≈ `obj.a.b` en JS).
- Contexte : `jq` est le `JSON.parse` du terminal : il lit du JSON, applique un filtre, réécrit du JSON. `.` seul renvoie tout, joliment indenté. C'est le compagnon de toutes les CLI qui sortent du JSON : `aws`, `terraform output -json`, `gh api`. Le filtre se met toujours entre guillemets simples, pour que le shell ne touche ni aux `$` ni aux `[`.
- Usage : ✅ extraire une valeur d'une réponse `aws …` ou d'un output Terraform · ❌ filtrer une réponse `aws` : `--query` suffit souvent, sans outil de plus.

```bash
# Exemple 1 : un champ d'un output Terraform
terraform -chdir=infra output -json \
  bucket_names | jq '.raw'
# → "data-platform-dev-raw-<account_id>"
```

```bash
# Exemple 2 : descendre dans un objet
echo '{"a":{"b":1}}' | jq '.a.b'
# → 1
```

- Quiz : Que fait `echo '{"a":"x"}' | jq '.a.b'` ?
- [ ] Affiche `null`
- [x] Erreur : `Cannot index string with string "b"`
- [ ] Affiche `"x"`
- [ ] Affiche une chaîne vide
- Réponse : erreur (mesuré) : `.b` sur une chaîne n'a pas de sens ; `null` ne sort que si le champ manque dans un objet.

## 2. -r : la chaîne brute
- Id : jq-r-chaine-brute
- Sous-thème : sortie
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Prérequis : jq-lire-champ
- Voir aussi : Terraform/langage-hcl-output-raw
- Mots-clés : JSON, substitution de commande
- Source : data-platform · S1-08
- Définition : `jq -r` écrit les chaînes sans guillemets JSON : la forme à passer à une autre commande ou à une variable du shell.
- Contexte : Sans `-r`, `jq '.raw'` affiche `"dp-raw"`, guillemets compris : `aws s3 ls s3://"dp-raw"` recevrait les guillemets dans le nom. Avec `-r`, on obtient `dp-raw`. Piège : `-r` sur une valeur absente écrit le **texte** `null`, qui devient un nom de bucket ou de fonction plausible et fait échouer plus loin.
- Usage : ✅ `B=$(… | jq -r '.raw')`, toute valeur passée à une autre commande · ❌ sortie relue par un programme JSON : sans `-r`.

```bash
# Exemple 1 : avec et sans -r
J='{"raw":"dp-raw"}'
echo "$J" | jq '.raw'     # → "dp-raw"
echo "$J" | jq -r '.raw'  # → dp-raw
```

- Quiz : Que contient `B` après `B=$(echo '{"raw":"dp-raw"}' | jq -r '.row')` (faute de frappe) ?
- [ ] Une chaîne vide
- [x] Le texte `null`
- [ ] Rien : la ligne échoue
- [ ] `"null"` avec guillemets
- Réponse : le texte `null` (mesuré) : champ absent = `null`, et `-r` l'écrit tel quel, sans erreur ni code de sortie non nul.

## 3. ."clé-avec-tiret" : les guillemets obligatoires
- Id : jq-cle-avec-tiret
- Sous-thème : lire
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : code de sortie, output, locals
- Source : data-platform · S1-08
- Définition : Une clé avec un tiret, un point ou un espace se lit entre guillemets : `."ingest-bodacc"` ; `.ingest-bodacc` est lu comme une soustraction.
- Contexte : jq comprend `.ingest-bodacc` comme `.ingest - bodacc`, où `bodacc` serait une fonction : erreur de compilation, code 3. C'est le cas des clés de `local.lambdas` (`ingest-bodacc`), donc de l'output `lambda_functions`. Autre écriture : `.["ingest-bodacc"]` (≈ `obj["ingest-bodacc"]` en JS).
- Usage : ✅ toute clé qui n'est pas un identifiant simple (lettres, chiffres, `_`) · ❌ `.clé-avec-tiret` nu : toujours entre guillemets.

```bash
# Exemple 1 : l'output des Lambdas
J='{"ingest-bodacc":"data-platform-dev-ingest-bodacc"}'
echo "$J" | jq -r '."ingest-bodacc"'
# → data-platform-dev-ingest-bodacc
echo "$J" | jq -r '.ingest-bodacc'
# → jq: error: bodacc/0 is not defined
```

- Quiz : Quel code de sortie renvoie `jq '.ingest-bodacc'` ?
- [ ] `0`, avec `null`
- [ ] `1`
- [x] `3`
- [ ] `5`
- Réponse : `3` (mesuré) : erreur de compilation du filtre ; jq n'a même pas lu l'entrée.

## 4. champ absent : null, sans erreur
- Id : jq-champ-absent-null
- Sous-thème : lire
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : jq-lire-champ
- Voir aussi : jq-e-code-de-sortie, jq-valeur-par-defaut
- Mots-clés : JSON, code de sortie
- Source : data-platform · S1-08
- Définition : Un champ absent renvoie `null` et le code 0 : jq ne signale pas une faute de frappe (≈ `undefined` en JS).
- Contexte : `.x.y` sur un objet sans `x` donne aussi `null`, sans erreur : jq propage `null` comme l'opérateur `?.` de TS. Pratique pour lire des champs facultatifs, dangereux dans un script : une clé mal écrite passe en silence. D'où `-e` (carte « -e ») ou `//` (valeur par défaut) dès qu'une valeur est obligatoire.
- Usage : ✅ champ facultatif, lu sans planter · ❌ valeur obligatoire dans un script : `jq -e`, ou tester la sortie.

```bash
# Exemple 1 : absent, à tous les niveaux
echo '{"a":{"b":1}}' | jq '.x, .x.y'
# → null
#   null
echo $?   # → 0
```

- Quiz : Que fait `echo '{"a":1}' | jq '.b.c.d'` ?
- [x] Affiche `null`, code 0
- [ ] Erreur : `.b` est absent
- [ ] Affiche une ligne vide
- Réponse : `null`, code 0 : indexer `null` donne `null` ; seule l'indexation d'une chaîne ou d'un nombre lève une erreur.

## 5. .[] : itérer un tableau
- Id : jq-iterer-tableau
- Sous-thème : filtrer
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : jq-lire-champ
- Voir aussi : jq-map-transformer
- Mots-clés : JSON, manifest
- Source : data-platform · S1-08
- Définition : `.[]` sort chaque élément d'un tableau, un résultat par élément : la base de tout filtre sur une liste (≈ `for (const x of arr)`).
- Contexte : jq travaille en flux : un filtre peut produire plusieurs résultats, chacun écrit sur sa ligne. `.[] | .date` sort une date par élément. Sur un objet, `.[]` sort les valeurs. Pour regrouper les résultats dans un tableau, entourer de crochets : `[.[] | .date]`.
- Usage : ✅ parcourir une liste de manifests, de versions S3, de fonctions · ❌ compter : `length`, sans itérer.

```bash
# Exemple 1 : un élément par ligne
M='[{"date":"2026-10-03","count":0},
   {"date":"2026-10-04","count":17416}]'
echo "$M" | jq -c '.[]'
# → {"date":"2026-10-03","count":0}
#   {"date":"2026-10-04","count":17416}
```

```bash
# Exemple 2 : regrouper en tableau
echo "$M" | jq -c '[.[] | .count]'
# → [0,17416]
```

- Quiz : Combien de lignes affiche `echo '[{"a":1},{"a":2}]' | jq '.[]'` (sans `-c`) ?
- [ ] 2
- [x] 6
- [ ] 1
- [ ] 4
- Réponse : 6 (mesuré) : chaque objet est indenté sur 3 lignes (`{`, `"a": 1`, `}`) ; `-c` donnerait une ligne par objet.

## 6. keys et length : la forme d'un JSON
- Id : jq-keys-length-explorer
- Sous-thème : lire
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : JSON, JSONL, output
- Source : data-platform · S1-08
- Définition : `keys` liste les clés d'un objet, triées ; `length` compte les éléments d'un tableau, les clés d'un objet, ou les caractères d'une chaîne.
- Contexte : Premier réflexe devant une réponse inconnue : `jq 'keys'` pour voir ce qu'elle contient, avant d'écrire un chemin. `keys` trie par ordre alphabétique ; `keys_unsorted` garde l'ordre du document. `length` de `null` vaut `0`, sans erreur : un champ absent passe pour vide.
- Usage : ✅ explorer une sortie `aws` ou `terraform output -json`, compter des éléments · ❌ compter des lignes JSONL : `wc -l` ou `jq -s length`.

```bash
# Exemple 1 : explorer puis compter
J='{"z":1,"a":2}'
echo "$J" | jq -c 'keys'           # → ["a","z"]
echo "$J" | jq -c 'keys_unsorted'  # → ["z","a"]
echo "$J" | jq 'length'            # → 2
```

- Quiz : Que vaut `echo '"abc"' | jq length` ?
- [ ] `1`
- [x] `3`
- [ ] Erreur : pas un tableau
- [ ] `null`
- Réponse : `3` (mesuré) : sur une chaîne, `length` compte les caractères.

## 7. -e : un code de sortie qui dit si la valeur existe
- Id : jq-e-code-de-sortie
- Sous-thème : scripts
- Type : concept
- Niveau : 2
- Profils : ops
- Prérequis : jq-champ-absent-null
- Voir aussi : jq-codes-de-sortie
- Mots-clés : code de sortie, substitution de commande, Makefile
- Source : data-platform · S1-08
- Définition : `jq -e` sort avec le code 1 si le dernier résultat est `null` ou `false` : un champ absent fait enfin échouer la commande.
- Contexte : Sans `-e`, jq réussit toujours sur un JSON valide. Avec `-e`, `make replay` échoue si la clé de la Lambda n'existe pas dans l'output. Seuls `null` et `false` comptent comme échec : `0` et `""` réussissent. Piège : `-e` change le code mais **affiche quand même** `null` ; dans `$(…)`, le code est perdu et `null` est capturé.
- Usage : ✅ valeur obligatoire dans un script ou un Makefile, suivi d'un test du code · ❌ compter sur `-e` dans `$(…)` au milieu d'une autre commande : tester la variable obtenue.

```bash
# Exemple 1 : null et false échouent
echo '{}'        | jq -e '.x'  # → null, rc=1
echo '{"a":false}' | jq -e '.a'  # → false, rc=1
echo '{"a":0}'   | jq -e '.a'  # → 0, rc=0
```

```bash
# Exemple 2 : -e perdu dans $( )
echo "fn=[$(echo '{}' | jq -er '.x')]"
# → fn=[null]   (et echo réussit)
```

- Quiz : Que renvoie `echo '{"a":""}' | jq -e '.a'` ?
- [ ] Code 1 : chaîne vide
- [x] `""`, code 0
- [ ] Code 5
- Réponse : `""`, code 0 (mesuré) : pour `-e`, seuls `null` et `false` sont des échecs ; une chaîne vide est une vraie valeur.

## 8. select() : garder ce qui passe
- Id : jq-select-filtrer
- Sous-thème : filtrer
- Type : concept
- Niveau : 2
- Profils : data, ops
- Prérequis : jq-iterer-tableau
- Mots-clés : JSON, manifest
- Source : data-platform · S1-08
- Définition : `select(condition)` laisse passer un élément si la condition est vraie, et le supprime sinon (≈ `arr.filter(…)`, appliqué au flux).
- Contexte : S'utilise après `.[]` : `.[] | select(.count > 0)`. En jq, seuls `false` et `null` sont faux : `0` et `""` sont vrais, à l'inverse de JS. `select(.count)` garde donc les journées à 0 annonce. Écrire la comparaison complète.
- Usage : ✅ jours non vides, versions non courantes, erreurs d'un journal JSON · ❌ `select(.count)` pour « count non nul » : `select(.count > 0)`.

```bash
# Exemple 1 : les jours avec parution
M='[{"date":"2026-10-03","count":0},
   {"date":"2026-10-04","count":17416}]'
echo "$M" | jq -r '.[] | select(.count > 0)
  | .date'
# → 2026-10-04
```

- Quiz : Que garde `jq -c '[.[] | select(.count)]'` sur `[{"count":0},{"count":null},{"count":3}]` ?
- [ ] `[{"count":3}]`
- [x] `[{"count":0},{"count":3}]`
- [ ] Les trois éléments
- [ ] `[]`
- Réponse : `[{"count":0},{"count":3}]` (mesuré) : `0` est vrai en jq ; seul `null` est écarté.

## 9. // : la valeur par défaut
- Id : jq-valeur-par-defaut
- Sous-thème : filtrer
- Type : comparaison
- Niveau : 2
- Profils : ops
- Prérequis : jq-champ-absent-null
- Mots-clés : JSON
- Source : data-platform · S1-08
- Définition : `a // b` vaut `a`, sauf si `a` est `null` ou `false` : alors `b` (≈ `??` en TS, mais `false` déclenche aussi).
- Contexte : `.profile // "default"` donne une valeur à un champ facultatif. Différence avec `??` : en TS, `false ?? "x"` vaut `false` ; en jq, `false // "x"` vaut `"x"`. Comme pour `select`, `0` n'est pas « vide » : `0 // 5` vaut `0`.
- Usage : ✅ champ facultatif avec repli, éviter le texte `null` en sortie `-r` · ❌ booléen dont `false` a un sens : tester `== null`.

```bash
# Exemple 1 : null, false, 0, absent
echo '{"a":null,"b":false,"c":0}' | jq -c \
  '[.a // "def", .b // "def",
    .c // "def", .z // "def"]'
# → ["def","def",0,"def"]
```

- Quiz : Que vaut `echo '{"actif":false}' | jq '.actif // true'` ?
- [ ] `false`
- [x] `true`
- [ ] `null`
- Réponse : `true` : `//` remplace `false` comme `null` ; le `false` voulu est perdu.

## 10. -c : un objet par ligne
- Id : jq-c-une-ligne-par-objet
- Sous-thème : sortie
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : jq-iterer-tableau
- Voir aussi : jq-slurp-tout-le-flux
- Mots-clés : JSONL, pipe
- Source : data-platform · S1-08
- Définition : `jq -c` écrit chaque résultat sur une seule ligne : la sortie devient du JSON Lines, pour `wc -l`, `grep` ou un autre `jq`.
- Contexte : Par défaut, jq indente : un objet prend plusieurs lignes, et `wc -l` compte des lignes d'affichage, pas des objets. `-c` donne exactement un objet par ligne, le format des fichiers `part-*.jsonl.gz` du bucket raw. À combiner avec `.[]` pour transformer un tableau en JSONL.
- Usage : ✅ produire du JSONL, compter, `grep` sur une ligne entière · ❌ lecture humaine d'un gros objet : sans `-c`.

```bash
# Exemple 1 : tableau → JSONL, puis compter
echo '[{"a":1},{"a":2}]' | jq -c '.[]'
# → {"a":1}
#   {"a":2}
echo '[{"a":1},{"a":2}]' | jq -c '.[]' \
  | wc -l
# → 2
```

- Quiz : `zcat part-0001.jsonl.gz | jq '.id' | wc -l` sur 32 373 annonces : combien ?
- [x] 32 373
- [ ] 64 746
- [ ] 1
- Réponse : 32 373 (mesuré sur le 2026-10-20) : chaque `.id` est une chaîne sur une seule ligne ; c'est l'objet entier qui s'étalerait sur plusieurs lignes sans `-c`.

## 11. --arg : passer une variable du shell
- Id : jq-arg-variable-shell
- Sous-thème : scripts
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : jq-lire-champ
- Voir aussi : shell-guillemets-simples
- Mots-clés : shell, JSON
- Source : data-platform · S1-08
- Définition : `jq --arg nom valeur` rend la valeur disponible dans le filtre sous `$nom`, toujours comme chaîne ; `--argjson` la passe comme JSON.
- Contexte : Insérer la variable dans le filtre (`jq ".\"$L\""`) casse dès qu'elle contient un guillemet, et oblige à jongler avec les guillemets doubles. `--arg` transmet la valeur à part, sans interprétation. Piège : `--arg n 5` donne la **chaîne** `"5"`, qui n'est pas égale au nombre `5` ; pour un nombre, `--argjson`.
- Usage : ✅ clé ou valeur variable dans un filtre (`.[$k]`), script réutilisable · ❌ filtre construit par concaténation de chaînes du shell.

```bash
# Exemple 1 : la clé dans une variable
L=ingest-bodacc
J='{"ingest-bodacc":"data-platform-dev-ingest-bodacc"}'
echo "$J" | jq -r --arg k "$L" '.[$k]'
# → data-platform-dev-ingest-bodacc
```

- Quiz : Que vaut `echo '{"count":5}' | jq --arg n 5 '.count == $n'` ?
- [ ] `true`
- [x] `false`
- [ ] Erreur de type
- Réponse : `false` (mesuré) : `$n` est la chaîne `"5"` ; `--argjson n 5` donnerait `true`.

## 12. map : transformer chaque élément
- Id : jq-map-transformer
- Sous-thème : filtrer
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : jq-iterer-tableau
- Mots-clés : JSON, manifest
- Source : data-platform · S1-08
- Définition : `map(f)` applique `f` à chaque élément d'un tableau et rend un tableau de résultats (≈ `arr.map(f)`).
- Contexte : `map(f)` est un raccourci de `[.[] | f]` : il garde la forme tableau, contrairement à `.[] | f` qui sort un flux de valeurs séparées. `map(.count)` extrait une colonne d'une liste de manifests, prête à être sommée, triée ou comptée. Dans `f`, `.` désigne l'élément courant.
- Usage : ✅ extraire une colonne, convertir un champ de chaque élément · ❌ objet dont on veut modifier les valeurs : `map_values` ou `with_entries`.

```bash
# Exemple 1 : une colonne de manifests
M='[{"date":"2026-10-04","count":17416},
   {"date":"2026-10-05","count":0}]'
echo "$M" | jq -c 'map(.count)'
# → [17416,0]
```

```bash
# Exemple 2 : flux ou tableau
echo '[1,2]' | jq -c '.[] | . + 1'
# → 2
#   3
echo '[1,2]' | jq -c 'map(. + 1)'
# → [2,3]
```

- Quiz : Que vaut `echo '[3,5]' | jq -c 'map(. * 2)'` ?
- [ ] `16`
- [x] `[6,10]`
- [ ] `[3,5,3,5]`
- Réponse : `[6,10]` (mesuré) : `map` garde un tableau ; `.` y désigne chaque élément.

## 13. add : sommer, null sur liste vide
- Id : jq-add-sommer
- Sous-thème : filtrer
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : jq-map-transformer
- Mots-clés : manifest, rejeu
- Source : data-platform · S1-08
- Définition : `add` additionne les nombres d'un tableau, concatène chaînes ou tableaux, fusionne des objets ; sur un tableau vide, il vaut `null`.
- Contexte : `map(.count) | add` additionne les `count` d'une liste de manifests : la vérification d'un rejeu tient en une ligne. Piège : sur un tableau vide, `add` vaut `null`, pas `0` ; avec `-r`, un script lit alors le texte `null`. Protéger avec `add // 0`. Le comportement suit le type des éléments : `+` de jq sur chacun.
- Usage : ✅ total d'un rejeu, concaténer des listes · ❌ somme d'une liste peut-être vide sans `// 0`.

```bash
# Exemple 1 : total d'un rejeu
M='[{"date":"2026-10-04","count":17416},
   {"date":"2026-10-05","count":0}]'
echo "$M" | jq 'map(.count) | add'
# → 17416
```

```bash
# Exemple 2 : la liste vide
echo '[]' | jq 'add'        # → null
echo '[]' | jq 'add // 0'   # → 0
```

- Quiz : Que vaut `echo '["a","b"]' | jq add` ?
- [ ] Erreur : pas des nombres
- [x] `"ab"`
- [ ] `2`
- [ ] `null`
- Réponse : `"ab"` (mesuré) : `add` applique `+` entre les éléments, qui concatène des chaînes.

## 14. to_entries : parcourir une map
- Id : jq-to-entries-parcourir-objet
- Sous-thème : filtrer
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : jq-keys-length-explorer
- Mots-clés : JSON, output
- Source : data-platform · S1-08
- Définition : `to_entries` change un objet en liste de `{key, value}` (≈ `Object.entries`) ; `from_entries` fait l'inverse.
- Contexte : Indispensable quand les clés sont des données, comme `lambda_functions` ou `bucket_names` : on boucle sur les paires sans connaître les noms. `with_entries(f)` combine les deux (`to_entries | map(f) | from_entries`) pour modifier les clés ou les valeurs d'un objet.
- Usage : ✅ lister « clé = valeur » d'un output Terraform, renommer des clés · ❌ lire une seule clé connue : `.clé`.

```bash
# Exemple 1 : une ligne par entrée
J='{"ingest-bodacc":"data-platform-dev-ingest-bodacc",
   "raw":"dp-raw"}'
echo "$J" | jq -r 'to_entries[]
  | "\(.key)=\(.value)"'
# → ingest-bodacc=data-platform-dev-ingest-bodacc
#   raw=dp-raw
```

- Quiz : Que vaut `echo '{"a":1}' | jq -c 'with_entries(.value += 1)'` ?
- [x] `{"a":2}`
- [ ] `[{"key":"a","value":2}]`
- [ ] `{"a":1,"value":1}`
- Réponse : `{"a":2}` (mesuré) : `with_entries` repasse en objet après avoir modifié chaque paire.

## 15. -s : lire tout le flux en un tableau
- Id : jq-slurp-tout-le-flux
- Sous-thème : scripts
- Type : concept
- Niveau : 3
- Profils : data
- Prérequis : jq-c-une-ligne-par-objet
- Mots-clés : JSONL, DuckDB
- Source : data-platform · S1-08
- Définition : `jq -s` (slurp) lit tous les JSON de l'entrée et les met dans un seul tableau, avant d'appliquer le filtre.
- Contexte : Sans `-s`, jq applique le filtre à chaque objet d'un JSONL, séparément : impossible de faire une somme ou un tri global. Avec `-s`, tout est chargé en mémoire : pratique pour quelques milliers de lignes, à éviter sur un fichier de 55 Mo, où `reduce` ou `--stream` lisent en flux.
- Usage : ✅ total ou tri sur un petit JSONL, plusieurs réponses `aws` concaténées · ❌ gros fichier : `jq -n 'reduce inputs …'`, ou DuckDB.

```bash
# Exemple 1 : avec et sans -s
printf '{"count":3}\n{"count":5}\n' \
  | jq '.count'
# → 3
#   5
printf '{"count":3}\n{"count":5}\n' \
  | jq -s 'map(.count) | add'
# → 8
```

- Quiz : Que vaut `printf '{"a":1}\n{"a":2}\n{"a":3}\n' | jq -s length` ?
- [ ] `1`
- [x] `3`
- [ ] Trois lignes `1`
- Réponse : `3` (mesuré) : `-s` fait un tableau des trois objets, `length` le compte.

## 16. @tsv et @csv : une sortie tabulaire
- Id : jq-sortie-tsv-csv
- Sous-thème : sortie
- Type : recette
- Niveau : 3
- Profils : data
- Prérequis : jq-r-chaine-brute, jq-iterer-tableau
- Voir aussi : shell-column-aligner
- Mots-clés : CSV, Parquet
- Source : data-platform · S1-08
- Définition : `[…] | @tsv` ou `@csv` change un tableau de valeurs en ligne de tableur (tabulations ou virgules), avec `-r`.
- Contexte : Pour lire un résultat en colonnes ou l'ouvrir dans un tableur. `@csv` met les chaînes entre guillemets et double les guillemets internes ; `@tsv` échappe tabulations et retours à la ligne (`\t`, `\n`) au lieu de casser les colonnes. Les deux n'acceptent que des valeurs simples, pas d'objets imbriqués.
- Usage : ✅ tableau date / count d'un rejeu, export rapide · ❌ données à recharger fidèlement : JSON ou Parquet.

```bash
# Exemple 1 : date et count en colonnes
M='[{"date":"2026-10-03","count":0},
   {"date":"2026-10-04","count":17416}]'
echo "$M" | jq -r '.[] | [.date, .count]
  | @tsv'
# → 2026-10-03	0
#   2026-10-04	17416
```

- Quiz : Avec `@tsv`, que devient une valeur qui contient une tabulation (`"a<TAB>b"`) ?
- [ ] Elle crée une colonne de plus
- [x] Elle s'écrit `a\tb` (échappée)
- [ ] Erreur
- [ ] La tabulation est supprimée
- Réponse : échappée en `a\tb` (mesuré avec `od -c`) : les colonnes restent alignées.

## 17. codes de sortie : 2, 3, 5
- Id : jq-codes-de-sortie
- Sous-thème : scripts
- Type : concept
- Niveau : 3
- Profils : ops, expert
- Prérequis : jq-e-code-de-sortie
- Mots-clés : code de sortie, pipe, JSON
- Source : data-platform · S1-08
- Définition : Codes de jq : `0` succès, `1` `-e` sur `null`/`false`, `2` fichier ou option, `3` filtre invalide, `5` entrée non JSON.
- Contexte : Un script distingue ainsi « la valeur manque » (1) de « la réponse n'est pas du JSON » (5), par exemple une page d'erreur HTML renvoyée par une API à la place du JSON. `set -o pipefail` reste nécessaire : dans `aws … | jq …`, seul le code de jq compte sans lui.
- Usage : ✅ script de CI qui doit échouer sur une réponse invalide · ❌ `jq … || true` : masque aussi le JSON cassé.

```bash
# Exemple 1 : trois échecs, trois codes
echo '{}' | jq -e '.x' >/dev/null
echo $?   # → 1
echo '{pas du json' | jq . 2>/dev/null
echo $?   # → 5
jq . /nope 2>/dev/null
echo $?   # → 2
```

- Quiz : Quel code renvoie `echo '{pas du json' | jq -e '.x'` ?
- [ ] `1`
- [ ] `3`
- [x] `5`
- Réponse : `5` : l'entrée ne se lit pas ; le filtre n'est jamais appliqué, `-e` n'entre pas en jeu.

## 18. jq dans un Makefile : guillemets et $$
- Id : jq-makefile-dollar-double
- Sous-thème : scripts
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : make-double-dollar-shell, shell-guillemets-simples
- Mots-clés : recette, Makefile, output
- Source : data-platform · S1-08
- Définition : Dans une recette, le filtre jq reste entre guillemets simples ; une variable Make s'y insère par `$(VAR)`, une variable du shell par `$$VAR`.
- Contexte : Make développe `$(REPLAY_LAMBDA)` avant le shell : `'."$(REPLAY_LAMBDA)"'` devient `'."ingest-bodacc"'`, que le shell passe tel quel à jq. Un `$` de jq (`$k` avec `--arg`) doit être doublé (`$$k`), sinon Make le prend pour sa variable `k`, vide. `make -n` montre le filtre final.
- Usage : ✅ lire un output Terraform dans une cible (`make replay`, `make duckdb`) · ❌ `.[$k]` avec un seul `$` dans une recette : `.[$$k]`.

```makefile
# Exemple 1 : la cible replay
REPLAY_LAMBDA = $(or $(LAMBDA),ingest-bodacc)
replay:
	echo $$($(TF) output -json \
	  lambda_functions \
	  | jq -er '."$(REPLAY_LAMBDA)"')
# make -n → … | jq -er '."ingest-bodacc"'
```

- Quiz : Dans une recette, que reçoit jq avec `jq --arg k x '.[$k]'` (un seul `$`) ?
- [ ] `.[$k]`
- [x] `.[]`
- [ ] Une erreur de Make
- Réponse : `.[]` : Make remplace `$k` par sa variable `k`, vide ; jq itère alors tout l'objet au lieu de lire une clé.
