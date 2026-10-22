---
card: "Règle d'or Python"
id_short: 60
learning_id: card-60
board: fMaiYRrn
url: https://trello.com/c/B5OA3CdY
created: 2026-10-20
updated: 2026-10-20
status: en-cours
---

# Règle d'or Python
Liste : Python — programme parallèle · Échéance : aucune · Étiquettes : bleu (sans nom) · [Carte Trello](https://trello.com/c/B5OA3CdY)

## Objectif
Installer une discipline mesurable : 30 min/jour de Python **sans IA** (Exercism, doc officielle, petits scripts), un exercice chronométré de 45 min chaque vendredi, et un contrat explicite avec Claude Code sur les tickets [Python] — Pourquoi ça compte dans le projet : en S8 tu dois pouvoir soutenir, lire et corriger seul le code PySpark / boto3 de la plateforme devant un recruteur ou un client ; une plateforme écrite par l'assistant que tu ne sais pas réécrire ne vaut rien en entretien.

Carte sans section « Critères d'acceptation » ni checklist Trello : les critères de validation ci-dessous sont déduits du « Détail ».

## Prérequis
### Exercism (track Python)
Plateforme d'exercices avec tests fournis et mentorat gratuit. Chaque exercice = un dossier avec `<slug>.py` (stub à compléter) + `<slug>_test.py` (pytest). La CLI télécharge et soumet (`exercism download`, `exercism submit`). Le token API est personnel : il vit dans `~/.config/exercism/user.json`, jamais dans le repo. ≈ Exercism TS track que tu connais peut-être, mais ici l'intérêt est de passer par les tests pytest **sans** autocomplétion IA.
Doc : https://exercism.org/docs/using/solving-exercises/working-locally · https://exercism.org/cli-walkthrough
Exercice 5 min : créer le compte sur https://exercism.org, rejoindre le track Python, copier le token depuis https://exercism.org/settings/api_cli dans ton gestionnaire de secrets.

### `uv run` et scripts autonomes (PEP 723)
Un script Python peut déclarer ses dépendances en tête de fichier dans un bloc `# /// script … # ///` ; `uv run script.py` crée un environnement éphémère et l'exécute. ≈ `npx tsx script.ts` avec un `package.json` inline. Idéal pour les « petits scripts » quotidiens : zéro projet à créer, zéro venv à gérer. Pour le bac à sable commun (`kata/`), un `pyproject.toml` classique avec pytest + ruff en dépendances de dev.
Doc : https://docs.astral.sh/uv/guides/scripts/ · https://peps.python.org/pep-0723/
Exercice 5 min : écrire `hello.py` avec un bloc PEP 723 déclarant `requires-python = ">=3.12"` et aucune dépendance, le lancer avec `uv run hello.py`.

### pytest comme harnais de vérification
`pytest` découvre les fichiers `test_*.py` / `*_test.py` et les fonctions `test_*` ; `assert` nu suffit (pas d'`expect().toBe()`). `-k <motif>` filtre, `-x` stoppe au premier échec, `-q` résume. Exercism Python livre déjà ses tests en pytest : tu auras la même boucle rouge → vert que Vitest, sans watcher.
Doc : https://docs.pytest.org/en/stable/how-to/usage.html
Exercice 5 min : dans `kata/`, écrire `tests/test_smoke.py` contenant un test qui vérifie `1 + 1 == 2`, puis `uv run pytest -q`.

### Mémoire projet Claude Code (`CLAUDE.md`)
Claude Code lit `./CLAUDE.md` à la racine du repo à chaque session : c'est l'endroit pour poser des règles de collaboration que l'assistant doit respecter (≈ `.cursorrules`, ≈ un `CONTRIBUTING.md` que l'outil lit vraiment). Une règle écrite là s'applique sans que tu la répètes, et elle est versionnée avec le projet.
Doc : https://docs.claude.com/en/docs/claude-code/memory
Exercice 5 min : lire la page « Memory », noter la différence de portée entre `./CLAUDE.md`, `./CLAUDE.local.md` et `~/.claude/CLAUDE.md`.

## Étapes

### [ ] Étape 1 — Installer et configurer la CLI Exercism
- À faire : installer la CLI depuis la source officielle. Option A : `brew install exercism`. Option B (machine sans Homebrew fonctionnel) : télécharger l'archive `exercism-<version>-darwin-x86_64.tar.gz` (Intel) ou `-arm64` depuis https://github.com/exercism/cli/releases/latest, extraire le binaire `exercism` dans `~/.local/bin` (déjà dans le `PATH` si `gh` y est). Puis `exercism configure --token=<token>` : le workspace par défaut est `~/Exercism` (les exercices y sont téléchargés) ; le token atterrit dans `~/.config/exercism/user.json`.
- Concept : CLI tierce installée hors du projet, configuration utilisateur sous `~/.config` (XDG), workspace dans le repo (pas de secret dedans).
- Indice : `exercism configure` sans argument affiche la config courante (token masqué, workspace).
- Vérifier : `exercism version` affiche la version ; `exercism configure | grep -i workspace` → `~/Exercism`.

### [ ] Étape 2 — Créer le bac à sable `kata/` avec `uv`
- À faire : à la racine du repo, `uv init kata --python 3.12 --no-workspace` (ou `uv init` depuis un dossier `kata/` créé à la main), puis dans `kata/` : `uv add --dev pytest ruff`. Supprimer le `main.py` généré si inutile, créer `kata/tests/test_smoke.py` (un seul test trivial) et `kata/README.md` qui explique la règle du dossier : **code tapé sans IA**.
- Concept : `pyproject.toml` ≈ `package.json`, `uv.lock` ≈ `pnpm-lock.yaml`, `.venv/` ≈ `node_modules/` (déjà dans `.gitignore`). `--dev` ≈ `devDependencies`.
- Indice : `uv init` crée aussi `.python-version` (≈ `.nvmrc`) et un `README.md`. Le `.venv/` se crée au premier `uv run`, pas avant.
- Vérifier : `uv run --directory kata pytest -q` → `1 passed` ; `uv run --directory kata ruff check .` → `All checks passed!`.

### [ ] Étape 3 — Premier exercice Exercism sans IA (hello-world + un facile)
- À faire : `exercism download --track=python --exercise=hello-world`, lire le stub et le test, compléter, lancer les tests depuis le dossier de l'exercice avec `uv run --with pytest pytest -q hello_world_test.py` (env jetable, rien installé dans le Python global ; `exercism test` seul échoue car il utilise le `python3` du PATH), soumettre avec `exercism submit hello_world.py`. Enchaîner avec un exercice « easy » (`leap`, `two-fer`, `raindrops`…). Règle absolue : aucun assistant IA ouvert pendant ces 30 min (fermer Claude Code, désactiver Copilot/inline suggestions dans l'éditeur).
- Concept : boucle rouge → vert pytest ; lecture d'un test Python (`assert`, classes `unittest.TestCase` dans les tests Exercism — pytest les exécute aussi).
- Indice : les tests Exercism attendent des **noms de fonction exacts** et parfois des exceptions précises (`raise ValueError("message")`). Lire le test avant d'écrire.
- Vérifier : `uv run --with pytest pytest -q` dans `~/Exercism/python/hello-world` puis dans `~/Exercism/python/<facile>` vert ; les deux exercices apparaissent « Completed » sur https://exercism.org/tracks/python.

### [ ] Étape 4 — Le rituel quotidien (30 min) et son journal
- À faire : fixer un créneau fixe (même heure chaque jour), un minuteur (`sleep 1800 && say "stop"` suffit), un seul support par jour parmi : un exercice Exercism, un chapitre du Tutorial officiel (https://docs.python.org/3/tutorial/, sections 3 à 9 dans l'ordre), un petit script PEP 723. Créer `kata/JOURNAL.md` : une ligne par session `- YYYY-MM-DD — <support> — <ce que j'ai appris en 1 phrase> — <ce que je n'ai pas su faire>`. Commit à chaque session (`git add kata && git commit`).
- Concept : apprentissage espacé et traçabilité ; la ligne « ce que je n'ai pas su faire » alimente les tickets [Python] et les vendredis.
- Indice : si une session dérive vers « demander à Claude », noter la question dans le journal et la poser **après** le minuteur, en session tuteur. La question survit, l'habitude aussi.
- Vérifier : `grep -c '^- 2026-' kata/JOURNAL.md` ≥ 5 ; `git log --since='7 days ago' --oneline -- kata | wc -l` ≥ 5.

### [ ] Étape 5 — Petits scripts stdlib orientés data (PEP 723)
- À faire : dans `kata/scripts/`, écrire sur 2 à 3 sessions des scripts autonomes qui préfigurent S1 (ingestion BODACC) : (a) lire un CSV avec `csv.DictReader` et compter les lignes par valeur d'une colonne ; (b) lire un JSON avec `json` + `pathlib.Path.read_text` et en extraire une liste de champs ; (c) un `argparse` qui prend `--input` et `--column`. Aucune dépendance externe : stdlib uniquement, bloc PEP 723 avec `requires-python`.
- Concept : `pathlib` (≈ `node:path` + `fs` en objet), `csv`/`json` (≈ `JSON.parse` + un parser CSV intégré), `argparse` (≈ `commander`), `collections.Counter`.
- Indice : `Counter(row[col] for row in reader)` fait tout le comptage ; si tu écris une boucle avec un dict et `if key in d`, relis la doc de `collections`.
- Vérifier : `uv run kata/scripts/count_by_column.py --input <fichier.csv> --column <col>` affiche un comptage ; `uv run --directory kata ruff check scripts/` vert.

### [ ] Étape 6 — Contrat Claude Code sur les tickets [Python]
- À faire : créer `CLAUDE.md` à la racine du repo (il n'existe pas encore) avec une section « Tickets [Python] » qui formalise la règle de la carte : l'assistant explique, relit, propose des indices et des tests, ne produit jamais le corps d'une fonction ou d'un fichier de solution ; il peut écrire les tests, le Terraform, la CI. Ajouter la règle de la réécriture de mémoire (étape 7). Commiter.
- Concept : mémoire projet Claude Code versionnée ; séparer ce que l'assistant **peut** écrire (infra, tests, glue) de ce qu'il **ne doit pas** écrire (le Python métier que tu dois savoir refaire).
- Indice : une règle floue (« aide-moi ») ne tient pas ; une règle testable tient (« jamais plus de 3 lignes de Python par réponse sur un ticket [Python] », « toujours proposer un test avant un indice »). Formule-la comme une spec.
- Vérifier : `grep -n '\[Python\]' CLAUDE.md` renvoie la section ; `git log --oneline -1 -- CLAUDE.md` montre le commit.

### [ ] Étape 7 — Test de réécriture de mémoire
- À faire : prendre une fonction écrite **avec** l'assistant dans un ticket [Python] (ou, en attendant le premier ticket, la solution d'un exercice Exercism de la veille). Fermer le fichier. Dans `kata/rewrite/`, la réécrire de mémoire en 10 min max, avec ses tests. Lancer les tests originaux contre ta version. Si rouge ou impossible : la fonction n'est pas apprise → noter dans `JOURNAL.md` et la remettre au rituel du lendemain.
- Concept : rappel actif (vs relecture passive) ; les tests comme oracle neutre.
- Indice : copier le fichier de test original à côté de ta réécriture et ajuster uniquement l'`import`. Tout le reste doit passer sans modification.
- Vérifier : `uv run --directory kata pytest -q rewrite/` vert ; une ligne « réécriture » dans `kata/JOURNAL.md`.

### [ ] Étape 8 — Vendredi : 45 min chronométré type entretien
- À faire : choisir à l'avance (jeudi) un exercice Exercism « medium » que tu n'as pas ouvert (`clock`, `matrix`, `word-count`, `robot-name`, `isogram`…) ou un problème type entretien (parser de logs, dédoublonnage, agrégation). Vendredi : minuteur 45 min, **sans aide** : pas d'IA, pas de doc web, uniquement l'interpréteur (`uv run python` et `help(obj)` dans le REPL sont autorisés, comme en entretien live). À la fin : tests, commit avec le temps réel et le verdict dans le message, ligne dédiée dans `JOURNAL.md` avec ce qui a bloqué.
- Concept : résolution sous contrainte de temps ; `help()`, `dir()`, docstrings comme seule documentation.
- Indice : commencer par écrire 2 ou 3 `assert` toi-même avant de coder, même si les tests Exercism existent : ça force à lire l'énoncé une seule fois.
- Vérifier : `git log --grep='vendredi' --oneline -- kata` ≥ 1 ; `uv run --with pytest pytest -q` dans `~/Exercism/python/<medium>` (vert ou rouge : le verdict est consigné, pas maquillé).

## Pièges courants (dev TS → Python)
1. **Pas de `const`** : tout nom est réassignable ; l'immutabilité vient du type (`tuple`, `frozenset`) ou de la convention (`Final` n'est qu'une annotation). Ne cherche pas `readonly`.
2. **`==` vs `is`** : `==` compare les valeurs (≈ `===` sans coercition), `is` compare l'identité. `x is None` est idiomatique ; `x == None` ne l'est pas.
3. **Arguments par défaut mutables** : `def f(items=[])` partage la même liste entre tous les appels. Utiliser `None` + création dans le corps.
4. **Truthiness étendue** : `[]`, `{}`, `""`, `0`, `None` sont falsy ; `if not items:` remplace `if (items.length === 0)`. Pas de `undefined` : un attribut manquant lève `AttributeError`, une clé manquante `KeyError` (`.get()` pour l'équivalent de `?.`).
5. **Compréhensions, pas `map`/`filter` chaînés** : `[f(x) for x in xs if cond(x)]` est la forme attendue ; `map`/`filter` retournent des itérateurs paresseux (pas des listes). Et `self` est explicite dans les méthodes.

## Critères de validation
(déduits du Détail de la carte, qui n'a pas de « Critères d'acceptation »)
- [ ] CLI Exercism installée et configurée (workspace `~/Exercism`), track Python rejoint, au moins 2 exercices soumis sans IA (`exercism version`, page du track).
- [ ] `kata/` initialisé avec `uv` (Python 3.12, pytest + ruff en dev), `uv run --directory kata pytest -q` vert.
- [ ] 5 sessions quotidiennes de 30 min tracées dans `kata/JOURNAL.md` et commitées (une par jour ouvré).
- [ ] 3 petits scripts stdlib PEP 723 dans `kata/scripts/` lançables avec `uv run`.
- [ ] `CLAUDE.md` du repo contient la règle « Claude écrit avec toi, jamais à ta place » pour les tickets [Python], commité.
- [ ] 1 réécriture de mémoire effectuée et vérifiée par les tests originaux (`kata/rewrite/`).
- [ ] 1 exercice chronométré de 45 min réalisé un vendredi, verdict et temps consignés dans le commit et le journal.

## Question de compréhension
La carte dit : « Si tu ne peux pas réécrire une fonction de mémoire, tu ne l'as pas apprise. » En quoi cette règle est-elle **plus** nécessaire pour un senior TS qui apprend Python avec un assistant que pour un débutant complet sans assistant ? Quel biais précis vise-t-elle ?

## Journal
- 2026-10-20 — Plan généré. Carte sans checklist ni « Critères d'acceptation » : 7 critères déduits du Détail. Repo sans `pyproject.toml` : bac à sable `kata/` à créer à l'étape 2.
- 2026-10-20 — Exercism installé par l'utilisateur via le site (workspace par défaut `~/Exercism`, pas `kata/exercism`) : étape 1 et commandes des étapes 3 et 8 adaptées. `exercism test` échoue (`No module named pytest`, python3 = pyenv) : utiliser `uv run --with pytest pytest -q` dans le dossier de l'exercice. Étape 2 (`kata/`) pas encore faite, non bloquante pour l'étape 3.
