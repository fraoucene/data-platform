---
title: "Cartes · Ligne de commande Python"
type: cartes
langage: Python
chapitre: Système et réseau
cours: Ligne de commande
created: 2026-10-25
updated: 2026-10-26
---

# Cartes · Ligne de commande Python
Python · Ligne de commande : argparse, arguments, erreurs, script (format spec v3 de revision-pwa).

## 1. argparse : lire les options
- Id : ligne-de-commande-argparse-options
- Sous-thème : argparse
- Type : recette
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : CLI, argparse, Namespace
- Source : data-platform · S1-08
- Définition : `argparse.ArgumentParser` déclare les options d'un script, puis `parse_args` les lit et renvoie un `Namespace` à champs (≈ `commander` / `yargs`).
- Contexte : Chaque `add_argument("--to")` crée un champ `args.to`, chaîne par défaut. argparse génère aussi `--help`, les messages d'erreur et le code de sortie 2. `parse_args(liste)` lit une liste fournie : c'est ce qui rend un CLI testable sans terminal. `vars(args)` donne le dictionnaire.
- Usage : ✅ tout script lancé à la main ou par `make` (`replay.py`, `build_lambda.py`) · ❌ CLI riche à sous-commandes multiples : `typer` ou `click`, plus concis.

```python
# Exemple 1 : deux options
import argparse

p = argparse.ArgumentParser(prog="replay")
p.add_argument("--to")
p.add_argument("--function")
args = p.parse_args(["--to", "2026-10-19",
                     "--function", "f"])
args.to          # → '2026-10-19'
vars(args)
# → {'to': '2026-10-19', 'function': 'f'}
```

- Quiz : Option déclarée mais absente de la ligne : que vaut `p.parse_args([]).to` ?
- [ ] `''`
- [x] `None`
- [ ] `AttributeError`
- [ ] `SystemExit`
- Réponse : `None` : une option facultative sans `default` existe toujours dans le `Namespace`, à `None`.

## 2. parse_args(None) : lire sys.argv
- Id : ligne-de-commande-parse-args-none
- Sous-thème : argparse
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Prérequis : ligne-de-commande-argparse-options
- Voir aussi : ligne-de-commande-main-argv-teste
- Mots-clés : sys.argv, CLI
- Source : data-platform · S1-08
- Définition : Sans argument (ou avec `None`), `parse_args` lit la vraie ligne de commande, `sys.argv[1:]` (≈ `process.argv.slice(2)`).
- Contexte : `sys.argv[0]` est le chemin du script, les options suivent. D'où la signature `def parse_args(argv=None)` : en production `main()` passe `None` et argparse lit le terminal ; un test passe sa propre liste. Le même code sert aux deux, sans patcher `sys.argv`.
- Usage : ✅ `argv: list[str] | None = None` en paramètre de `parse_args` et de `main` · ❌ lire `sys.argv` à la main : pas de conversion, pas d'erreurs propres.

```python
# Exemple 1 : None lit sys.argv
import argparse, sys

sys.argv = ["replay.py", "--to", "z"]
p = argparse.ArgumentParser()
p.add_argument("--to")
p.parse_args().to        # → 'z'
p.parse_args(None).to    # → 'z'
p.parse_args(["--to", "y"]).to  # → 'y'
```

- Quiz : `sys.argv = ["replay.py"]`, puis `p.parse_args([])` avec `--to` obligatoire : que se passe-t-il ?
- [ ] `p.parse_args([])` lit quand même `sys.argv`
- [x] `SystemExit` : `--to` manque dans la liste vide
- [ ] `IndexError`
- Réponse : `SystemExit` : une liste, même vide, remplace `sys.argv` ; seule la valeur `None` le lit.

## 3. type= : convertir à la lecture
- Id : ligne-de-commande-type-conversion
- Sous-thème : arguments
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Prérequis : ligne-de-commande-argparse-options
- Voir aussi : ligne-de-commande-type-exceptions
- Mots-clés : argparse, code de sortie
- Source : data-platform · S1-08
- Définition : `type=f` applique `f` au texte reçu : `type=int`, `type=date.fromisoformat` rendent directement un `int` ou une `date`.
- Contexte : Sans `type`, tout arrive en chaîne, comme dans `process.argv`. La conversion a lieu à la lecture, donc une valeur invalide est refusée avant tout traitement : message `invalid fromisoformat value: '2026-13-01'`, code 2. N'importe quelle fonction d'une chaîne convient, y compris la sienne.
- Usage : ✅ dates, entiers, chemins (`type=Path`) · ❌ convertir après coup dans le code : l'erreur arriverait loin de la saisie, sans message d'usage.

```python
# Exemple 1 : une vraie date
import argparse
from datetime import date

p = argparse.ArgumentParser()
p.add_argument("--from", dest="start",
               type=date.fromisoformat)
a = p.parse_args(["--from", "2026-10-01"])
a.start          # → date(2026, 10, 1)
try:
    p.parse_args(["--from", "2026-13-01"])
except SystemExit as e:
    code = e.code
code             # → 2
```

- Quiz : `add_argument("--n", type=int, default="5")`, option absente : que vaut `args.n` ?
- [ ] `'5'`
- [x] `5`
- [ ] `None`
- [ ] `TypeError`
- Réponse : `5` (mesuré) : un `default` en chaîne passe aussi par `type` ; un `default` d'un autre type est gardé tel quel.

## 4. required=True : option obligatoire
- Id : ligne-de-commande-required
- Sous-thème : arguments
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : argparse, SystemExit, argument positionnel
- Source : data-platform · S1-08
- Définition : `required=True` rend une option `--x` obligatoire : absente, argparse affiche l'usage, l'erreur, et quitte avec le code 2.
- Contexte : Le message liste toutes les options manquantes d'un coup : `the following arguments are required: --to, --function`. La sortie passe par `SystemExit(2)`, qu'un test attrape avec `pytest.raises(SystemExit)`. Un argument positionnel est obligatoire par nature, sans `required`.
- Usage : ✅ ce sans quoi le script n'a pas de sens (`--from`, `--to`, `--function`) · ❌ `required` sur un réglage qui a une valeur raisonnable : `default=`.

```python
# Exemple 1 : manquante, code 2
import argparse

p = argparse.ArgumentParser(prog="replay")
p.add_argument("--to", required=True)
try:
    p.parse_args([])
except SystemExit as e:
    code = e.code
code             # → 2
```

- Quiz : `add_argument("--to", required=True, default="x")`, option absente : résultat ?
- [ ] `args.to == "x"`
- [x] `SystemExit` 2 : `--to` manque
- [ ] `args.to is None`
- [ ] `ValueError` à la déclaration
- Réponse : `SystemExit` 2 (mesuré) : `required` l'emporte, le `default` n'est jamais utilisé ; choisir l'un ou l'autre.

## 5. dest= : le nom du champ
- Id : ligne-de-commande-dest-mot-reserve
- Sous-thème : arguments
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Prérequis : ligne-de-commande-argparse-options
- Voir aussi : ligne-de-commande-tiret-souligne
- Mots-clés : Namespace, mot réservé
- Source : data-platform · S1-08
- Définition : `dest="start"` choisit le nom du champ dans le `Namespace`, indépendamment du nom de l'option tapée (`--from`).
- Contexte : Par défaut le champ reprend l'option sans tirets. Pour `--from`, cela donne un champ `from`, mot réservé de Python : `args.from` est une erreur de syntaxe, seul `getattr(args, "from")` le lit. `dest` règle le problème et donne un nom parlant (`start`, `end`) au code.
- Usage : ✅ option dont le nom est un mot réservé (`--from`, `--class`, `--import`) ou peu parlant dans le code · ❌ renommer sans raison : le lecteur cherche `args.to` et trouve `args.fin`.

```python
# Exemple 1 : from, mot réservé
import argparse

p = argparse.ArgumentParser()
p.add_argument("--from")
a = p.parse_args(["--from", "x"])
getattr(a, "from")   # → 'x'
q = argparse.ArgumentParser()
q.add_argument("--from", dest="start")
q.parse_args(["--from", "x"]).start  # → 'x'
```

- Quiz : Sans `dest`, que donne `args.from` dans le code ?
- [ ] `'x'`
- [ ] `None`
- [ ] `AttributeError`
- [x] `SyntaxError` à la lecture du fichier
- Réponse : `SyntaxError` : `from` est un mot-clé ; le fichier ne compile même pas, avant toute exécution.

## 6. --dry-run : le tiret devient un souligné
- Id : ligne-de-commande-tiret-souligne
- Sous-thème : arguments
- Type : piège
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : Namespace, kebab-case, snake_case
- Source : data-platform · S1-08
- Définition : Une option `--dry-run` donne le champ `args.dry_run` : argparse remplace les tirets internes par des soulignés.
- Contexte : Un nom Python ne peut pas contenir `-`. La règle vaut pour toutes les options longues (`--max-days` → `args.max_days`). `dest=` permet de choisir un autre nom si besoin.
- Usage : ✅ options en kebab-case côté terminal, snake_case côté code · ❌ chercher `args["dry-run"]` : le `Namespace` n'est pas un dictionnaire.

```python
# Exemple 1 : kebab-case → snake_case
import argparse

p = argparse.ArgumentParser()
p.add_argument("--max-days", type=int)
a = p.parse_args(["--max-days", "3"])
a.max_days       # → 3
vars(a)          # → {'max_days': 3}
```

- Quiz : Que donne `args.dry-run` dans le code ?
- [ ] La valeur de `--dry-run`
- [x] `AttributeError` : pas d'attribut `dry`
- [ ] `SyntaxError`
- [ ] `NameError` : `dry-run` inconnu
- Réponse : `AttributeError` (mesuré) : Python lit `args.dry - run` et cherche d'abord `args.dry`, qui n'existe pas.

## 7. store_true : un drapeau booléen
- Id : ligne-de-commande-store-true
- Sous-thème : arguments
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Mots-clés : drapeau, argparse
- Source : data-platform · S1-08
- Définition : `action="store_true"` fait d'une option un drapeau : `False` si absente, `True` si présente, sans valeur à taper (≈ `--flag` booléen de yargs).
- Contexte : Le drapeau ne consomme aucun argument : `--dry-run` suffit. `store_false` fait l'inverse (vrai par défaut). Pour un booléen désactivable des deux côtés (`--color` / `--no-color`), `action=argparse.BooleanOptionalAction`.
- Usage : ✅ modes on/off (`--dry-run`, `--verbose`) · ❌ `type=bool` : `bool("False")` vaut `True`, toute chaîne non vide est vraie.

```python
# Exemple 1 : drapeau booléen
import argparse

p = argparse.ArgumentParser()
p.add_argument("--dry-run",
               action="store_true")
p.parse_args([]).dry_run       # → False
p.parse_args(["--dry-run"]).dry_run
# → True
```

- Quiz : `p.parse_args(["--dry-run", "oui"])` avec `action="store_true"` : que se passe-t-il ?
- [ ] `dry_run == "oui"`
- [ ] `dry_run is True`, `oui` ignoré
- [x] `SystemExit` : argument `oui` non reconnu
- Réponse : `SystemExit` : un drapeau ne prend pas de valeur ; `oui` devient un argument inconnu, refusé avec le code 2.

## 8. if __name__ == "__main__" : lancé ou importé
- Id : ligne-de-commande-garde-main
- Sous-thème : script
- Type : concept
- Niveau : 1
- Profils : débutant, ops
- Voir aussi : ligne-de-commande-code-de-sortie, packaging-python-m
- Mots-clés : module, import Python, __name__
- Source : data-platform · S1-08
- Définition : `if __name__ == "__main__":` n'exécute son bloc que si le fichier est lancé comme script, pas quand il est importé (≈ `require.main === module`).
- Contexte : Lancé (`uv run replay.py`), le module s'appelle `"__main__"` ; importé (`import replay` dans un test), il s'appelle `"replay"`. Sans cette garde, importer le fichier pour tester `days()` lancerait le rejeu réel, appels AWS compris. On y met seulement `sys.exit(main())`, le reste vit dans des fonctions.
- Usage : ✅ tout fichier à la fois script et module importable (scripts `infra/scripts/`) · ❌ du code de traitement au niveau du module : il tourne à chaque import.

```python
# Exemple 1 : la garde, deux cas
def garde(nom):
    # nom = __name__ du module
    if nom == "__main__":
        return "main() appelée"
    return "rien"

garde("__main__")  # → 'main() appelée'
garde("replay")    # → 'rien' (import)
```

- Quiz : `test_replay.py` fait `import replay`. Que vaut `replay.__name__` ?
- [ ] `"__main__"`
- [x] `"replay"`
- [ ] `"test_replay"`
- [ ] `"replay.py"`
- Réponse : `"replay"` (mesuré) : importé, un module porte son nom ; la garde est fausse, `main()` n'est pas appelée.

## 9. positionnel ou option
- Id : ligne-de-commande-positionnel-vs-option
- Sous-thème : arguments
- Type : comparaison
- Niveau : 1
- Profils : débutant, ops
- Prérequis : ligne-de-commande-argparse-options
- Mots-clés : argument positionnel, argparse
- Source : data-platform · S1-08
- Définition : `add_argument("jour")` (sans tiret) déclare un argument positionnel, obligatoire et lu par sa place ; `--jour` déclare une option nommée.
- Contexte : Les positionnels conviennent à une ou deux valeurs évidentes (`cp source destination`). Dès qu'il y a deux dates, les options nommées évitent l'inversion : `--from 2026-10-01 --to 2026-10-19` se lit sans doc. Les options s'écrivent dans n'importe quel ordre, aussi `--to=2026-10-19`.
- Usage : ✅ positionnel pour la valeur principale unique (`LAMBDA` de `build_lambda.py`) · ❌ deux positionnels de même type (deux dates) : options nommées.

```python
# Exemple 1 : par la place, par le nom
import argparse

p = argparse.ArgumentParser()
p.add_argument("jour")
p.parse_args(["2026-10-01"]).jour
# → '2026-10-01'
q = argparse.ArgumentParser()
q.add_argument("--to")
q.parse_args(["--to=2026-10-19"]).to
# → '2026-10-19'
```

- Quiz : `add_argument("jour")`, puis `parse_args([])` : résultat ?
- [ ] `args.jour is None`
- [ ] `args.jour == ''`
- [x] `SystemExit` 2 : `jour` est requis
- [ ] `IndexError`
- Réponse : `SystemExit` 2 (mesuré) : un positionnel est obligatoire par nature ; `nargs="?"` le rendrait facultatif.

## 10. parser.error : une règle entre deux options
- Id : ligne-de-commande-parser-error
- Sous-thème : erreurs
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : ligne-de-commande-argparse-options
- Voir aussi : ligne-de-commande-code-de-sortie
- Mots-clés : argparse, code de sortie
- Source : data-platform · S1-08
- Définition : `parser.error("…")` affiche l'usage et le message au format argparse, puis quitte avec le code 2, comme une erreur d'option.
- Contexte : argparse valide chaque option seule ; une règle qui en relie deux (début ≤ fin) s'écrit juste après `parse_args`. Passer par `parser.error` plutôt que `raise ValueError` donne le même rendu et le même code que les autres erreurs de saisie, et refuse avant le moindre appel AWS.
- Usage : ✅ cohérence entre options (`--from` ≤ `--to`, options exclusives) · ❌ `print` + `sys.exit(1)` : code 1 = échec du traitement, pas erreur d'usage.

```python
# Exemple 1 : début après fin
import argparse
from datetime import date

p = argparse.ArgumentParser(prog="replay")
d = date.fromisoformat
p.add_argument("--from", dest="s", type=d)
p.add_argument("--to", dest="e", type=d)
a = p.parse_args(["--from", "2026-10-19",
                  "--to", "2026-10-01"])
a.s > a.e        # → True
try:
    p.error("--from est après --to")
except SystemExit as e:
    code = e.code
code             # → 2
```

- Quiz : Où `parser.error("--from est après --to")` écrit-il son message ?
- [ ] Sur stdout, avec l'usage
- [x] Sur stderr, après l'usage
- [ ] Dans le message de l'exception, sans rien afficher
- [ ] Dans les logs (`logging.error`)
- Réponse : sur stderr : l'usage puis `prog: error: …` ; stdout reste propre pour la sortie utile du script, et `capsys.readouterr().err` le relit en test.

## 11. choices= : une liste fermée
- Id : ligne-de-commande-choices
- Sous-thème : arguments
- Type : concept
- Niveau : 2
- Profils : ops
- Mots-clés : argparse, bucket S3
- Source : data-platform · S1-08
- Définition : `choices=["dev", "prod"]` refuse toute valeur hors liste, avec un message qui rappelle les valeurs permises.
- Contexte : La vérification a lieu après `type` : avec `type=int`, `choices` contient des entiers. Le message (`invalid choice: 'int' (choose from dev, prod)`) évite d'aller lire le code. Pour un environnement, c'est la garantie qu'une faute de frappe ne vise pas un bucket inexistant.
- Usage : ✅ environnement, mode, format de sortie · ❌ liste longue ou dynamique (noms de fonctions) : valider après lecture, ou lire la liste depuis Terraform.

```python
# Exemple 1 : env hors liste
import argparse

p = argparse.ArgumentParser(prog="replay")
p.add_argument("--env",
               choices=["dev", "prod"])
p.parse_args(["--env", "dev"]).env
# → 'dev'
try:
    p.parse_args(["--env", "int"])
except SystemExit as e:
    code = e.code
code             # → 2
```

- Quiz : `add_argument("--n", type=int, choices=["1", "2"])`, puis `--n 1` : résultat ?
- [ ] `args.n == 1`
- [ ] `args.n == "1"`
- [x] `SystemExit` : `1` n'est pas dans `["1", "2"]`
- Réponse : `SystemExit` : `type` convertit d'abord en `1` (entier), puis `choices` compare à des chaînes.

## 12. type= : quelles exceptions deviennent un message
- Id : ligne-de-commande-type-exceptions
- Sous-thème : erreurs
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : ligne-de-commande-type-conversion, exceptions-typeerror-ou-valueerror
- Mots-clés : argparse, trace d'erreur
- Source : data-platform · S1-08
- Définition : argparse transforme en message d'usage (code 2) les `ValueError`, `TypeError` et `ArgumentTypeError` levées par `type` ; toute autre exception remonte telle quelle.
- Contexte : `date.fromisoformat` lève `ValueError` : message propre. Une fonction maison qui lève `KeyError` ou une exception métier fait planter le script avec une trace Python. Pour un message lisible, lever `argparse.ArgumentTypeError("pas un SIREN")`.
- Usage : ✅ validateur maison qui lève `ArgumentTypeError` (SIREN à 9 chiffres) · ❌ laisser fuir une exception métier depuis `type` : trace au lieu d'un message.

```python
# Exemple 1 : message propre ou trace
import argparse

def siren(s):
    if len(s) != 9:
        raise argparse.ArgumentTypeError(
            "pas un SIREN")
    return s

p = argparse.ArgumentParser()
p.add_argument("--siren", type=siren)
p.parse_args(["--siren", "552100554"]).siren
# → '552100554'
try:
    p.parse_args(["--siren", "12"])
except SystemExit as e:
    code = e.code
code             # → 2
```

- Quiz : La fonction `type` lève `KeyError("x")`. Que fait `parse_args` ?
- [ ] `SystemExit` code 2
- [x] Laisse remonter `KeyError`
- [ ] Ignore l'option
- Réponse : laisse remonter `KeyError` (mesuré) : seules `ValueError`, `TypeError` et `ArgumentTypeError` deviennent un message d'usage.

## 13. sys.exit(main()) : le code de sortie
- Id : ligne-de-commande-code-de-sortie
- Sous-thème : script
- Type : concept
- Niveau : 2
- Profils : ops, data
- Prérequis : ligne-de-commande-garde-main
- Mots-clés : code de sortie, SystemExit, CI, REPL
- Source : data-platform · S1-08
- Définition : `sys.exit(main())` fait de la valeur renvoyée par `main` le code de sortie : 0 succès, 1 échec du traitement, 2 erreur d'usage.
- Contexte : `make`, le shell (`&&`, `$?`) et la CI ne lisent que ce code. `main` décide donc d'un entier explicite (`return 1 if failed else 0`) au lieu de renvoyer un compte : `sys.exit(3)` signalerait un échec. `sys.exit` lève `SystemExit`, qu'un test attrape pour lire `.code`.
- Usage : ✅ `return 1 if échecs else 0` dans `main`, `sys.exit(main())` sous la garde `__main__` · ❌ `exit()` (fonction du REPL) dans un script.

```python
# Exemple 1 : 2 jours en échec
def main(failed=2):
    return 1 if failed else 0

try:
    raise SystemExit(main())
except SystemExit as e:
    code = e.code
code             # → 1
```

- Quiz : `main()` renvoie `None` (pas de `return`). Quel code donne `sys.exit(main())` ?
- [x] `0`
- [ ] `1`
- [ ] `None`, affiché tel quel
- [ ] `2`
- Réponse : `0` : `sys.exit(None)` est un succès ; c'est pourquoi un `return` oublié passe inaperçu.

## 14. main(argv=None) : tester le vrai point d'entrée
- Id : ligne-de-commande-main-argv-teste
- Sous-thème : script
- Type : recette
- Niveau : 2
- Profils : ops
- Prérequis : ligne-de-commande-parse-args-none
- Mots-clés : SystemExit, capsys, stderr, monkeypatch
- Source : data-platform · S1-08
- Définition : Donner `argv=None` à `main` et le passer à `parse_args` permet d'appeler `main(["--from", …])` dans un test, comme si on tapait la commande.
- Contexte : Le test exerce alors le vrai chemin : lecture des options, validation, code de sortie. Un `SystemExit` d'argparse s'attrape avec `pytest.raises(SystemExit)` puis `exc.value.code == 2`, et `capsys` lit le message sur stderr. On évite de modifier `sys.argv`, état global partagé par tous les tests.
- Usage : ✅ tests des erreurs d'usage et du code de sortie · ❌ `monkeypatch.setattr(sys, "argv", …)` quand passer une liste suffit.

```python
# Exemple 1 : main testable
import argparse

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--to", required=True)
    p.parse_args(argv)
    return 0

main(["--to", "2026-10-19"])   # → 0
try:
    main([])     # --to manque
except SystemExit as e:
    code = e.code
code             # → 2
```

- Quiz : Dans un test pytest, `main()` est appelée sans liste. Que lit argparse ?
- [ ] Une liste vide
- [x] Le `sys.argv` de pytest (ses options et chemins)
- [ ] Rien : `argv=None` désactive la lecture
- [ ] Les arguments du dernier `main([...])`
- Réponse : le `sys.argv` de pytest : `None` veut dire « lire le vrai terminal », donc souvent `SystemExit` 2 sur `-q` ou un chemin ; toujours passer une liste en test.

## 15. import différé : --help sans boto3
- Id : ligne-de-commande-import-differe
- Sous-thème : script
- Type : recette
- Niveau : 3
- Profils : ops, expert
- Prérequis : ligne-de-commande-garde-main
- Mots-clés : import Python, boto3, fonction pure, Ruff
- Source : data-platform · S1-08
- Définition : Importer une bibliothèque lourde dans `main()` plutôt qu'en haut du fichier évite de la charger pour `--help`, une erreur d'usage ou les tests.
- Contexte : `import replay` dans les tests n'importe pas boto3 (mesuré : `'boto3' in sys.modules` faux). `--help` répond donc instantanément, et les tests des fonctions pures n'en dépendent pas. Le prix : l'import n'est plus visible en tête, et Ruff (`PLC0415`) le signale si la règle est active ; le commenter.
- Usage : ✅ CLI dont l'aide et la validation doivent marcher sans dépendance réseau ou lourde · ❌ module de bibliothèque : imports en tête, lisibles.

```python
# Exemple 1 : rien n'est chargé à l'import
import sys

def main():
    import json  # chargé à l'appel seulement
    return json.dumps({"ok": 1})

main()           # → '{"ok": 1}'
"json" in dir()  # → False
```

- Quiz : Pourquoi `"json" in dir()` vaut `False` après `main()` ?
- [ ] `json` est déchargé à la fin de `main`
- [x] Le nom `json` est local à `main`
- [ ] L'import a échoué
- Réponse : le nom est local à `main` : le module est bien chargé (`sys.modules`), mais le nom n'existe que dans la fonction.

## 16. allow_abbrev : --func vaut --function
- Id : ligne-de-commande-allow-abbrev
- Sous-thème : arguments
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Mots-clés : argparse, Makefile, CI
- Source : data-platform · S1-08
- Définition : Par défaut argparse accepte tout préfixe non ambigu d'une option longue : `--func f` remplit `--function`.
- Contexte : Pratique au terminal, piège en script : un ajout d'option `--functions` plus tard rend `--func` ambigu et casse un appel qui marchait. `ArgumentParser(allow_abbrev=False)` exige le nom complet ; à faire dès qu'un script est appelé par `make` ou la CI, où le nom complet ne coûte rien.
- Usage : ✅ `allow_abbrev=False` pour un CLI appelé par d'autres outils · ❌ compter sur une abréviation dans un Makefile.

```python
# Exemple 1 : préfixe accepté ou refusé
import argparse

p = argparse.ArgumentParser()
p.add_argument("--function")
p.parse_args(["--func", "f"]).function
# → 'f'
q = argparse.ArgumentParser(
    allow_abbrev=False)
q.add_argument("--function")
try:
    q.parse_args(["--func", "f"])
except SystemExit as e:
    code = e.code
code             # → 2
```

- Quiz : Avec `--function` et `--functions` déclarées, `--func f` donne ?
- [ ] `function == 'f'`
- [ ] `functions == 'f'`
- [x] `SystemExit` : option ambiguë
- Réponse : `SystemExit` : deux options commencent par `--func`, argparse refuse de choisir.

## 17. valeur négative : -1 n'est pas une option
- Id : ligne-de-commande-valeur-negative
- Sous-thème : arguments
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : ligne-de-commande-argparse-options
- Mots-clés : argparse, Makefile
- Source : data-platform · S1-08
- Définition : `--n -1` est lu comme la valeur `-1` tant qu'aucune option déclarée ne ressemble à un nombre négatif.
- Contexte : argparse distingue `-1` (nombre) de `-v` (option courte) par sa forme. Si le parseur déclare une option courte numérique (`-1`), les nombres négatifs deviennent ambigus et il faut écrire `--n=-1`. La forme `--opt=valeur` lève toute ambiguïté, y compris pour une valeur qui commence par `--`.
- Usage : ✅ `--opt=valeur` dans les scripts générés (Makefile), surtout pour des valeurs calculées · ❌ options courtes numériques (`-1`, `-2`).

```python
# Exemple 1 : nombre négatif
import argparse

p = argparse.ArgumentParser()
p.add_argument("--n", type=int)
p.parse_args(["--n", "-1"]).n   # → -1
p.parse_args(["--n=-3"]).n      # → -3
```

- Quiz : Valeur calculée `--to $(cmd)` où `cmd` sort `--help` : que fait argparse ?
- [ ] `args.to == "--help"`
- [ ] Affiche l'aide, code 0
- [x] `SystemExit` 2 : `--to` attend une valeur
- Réponse : `SystemExit` 2 (mesuré : `expected one argument`) : `--help` est lu comme une option ; `--to=$(cmd)` l'aurait gardé en valeur.
