---
card: "Py S1 · Bases modernes + client HTTP"
id_short: 61
learning_id: py-s1
board: fMaiYRrn
url: https://trello.com/c/VOlSteeS
created: 2026-10-20
updated: 2026-10-20
status: en-cours
---

# Py S1 · Bases modernes + client HTTP
Liste : Python — programme parallèle · Échéance : 2026-11-01 · Étiquettes : violet (sans nom) · [Carte Trello](https://trello.com/c/VOlSteeS)

## Objectif
Construire seul, dans un mini-projet d'entraînement `kata/py-s1/`, un client HTTP paginé complet (projet `uv`, type hints, dataclass + Pydantic, `httpx`, retries exponentiels, générateur, `pytest` + fixtures + `respx`) — Pourquoi ça compte dans le projet : ce sont exactement les briques de S1-03 (monorepo `uv`, ruff, pytest) et de S1-06 (`BodaccClient.fetch_day(date) -> Iterator[dict]`, pagination, 429, respx, couverture ≥ 80 %) ; ici tu les apprends sur une API neutre pour ne pas les découvrir sur le ticket.

Carte sans « Critères d'acceptation » ni checklist : les critères ci-dessous sont déduits des Notions et du Vendredi de la carte, croisés avec S1-06.

Choix d'API : semaine = PokéAPI (`https://pokeapi.co/api/v2/pokemon?limit=100&offset=0`, pagination par URL `next`, sans auth, pas de quota gênant). Vendredi = API Recherche d'entreprises (`https://recherche-entreprises.api.gouv.fr/search?q=…&page=1&per_page=25`, pagination `page`/`total_pages`) : autre style de pagination, pour tester le transfert. BODACC reste réservé à S1-06.

## Prérequis
### Projet `uv` en layout `src/`
`uv init --package` crée `pyproject.toml` (`[project]` ≈ `package.json`, `[build-system]`, `[dependency-groups] dev = […]` ≈ `devDependencies`), `src/<pkg>/__init__.py`, `.python-version`. `uv add` / `uv add --dev` modifient le `pyproject` et `uv.lock` ; `uv sync` ≈ `pnpm install --frozen-lockfile` ; `uv run <cmd>` exécute dans le `.venv/` sans l'activer. Le layout `src/` empêche d'importer le package depuis le dossier courant par accident : seul le package installé (en editable) est importable.
Doc : https://docs.astral.sh/uv/concepts/projects/layout/ · https://docs.astral.sh/uv/concepts/projects/dependencies/
Exercice 5 min : lire « Project structure » et noter la différence `uv init` (application) vs `uv init --package` vs `uv init --lib`.

### Type hints modernes (3.12)
`list[str]`, `dict[str, int]` (plus `List`/`Dict`), `X | None` (plus `Optional`), `collections.abc.Iterator` / `Iterable` / `Callable`, `typing.Protocol` ≈ interface structurelle TS, `TypedDict` ≈ type d'objet littéral. Les hints ne font **rien** à l'exécution : pas de compilateur, c'est `ruff` (règles `UP`, `ANN`) et un type checker (`mypy`, `pyright`, `ty`) qui les lisent.
Doc : https://docs.python.org/3/library/typing.html · https://docs.python.org/3/library/collections.abc.html
Exercice 5 min : écrire la signature d'une fonction qui prend un `Iterable[str]` et un `Callable[[str], bool]` et renvoie `list[str]`, sans corps (`...`), puis `uv run ruff check`.

### `dataclass` vs Pydantic
`@dataclass(frozen=True, slots=True)` = classe avec `__init__`, `__eq__`, `__repr__` générés, **sans validation** (≈ interface TS + constructeur). Pydantic `BaseModel` = `zod` : `Model.model_validate(dict)` parse et coerce, lève `ValidationError`, `model_dump()` sérialise. Règle : dataclass pour les types internes que tu construis toi-même, Pydantic à la frontière (JSON d'une API, config, événements).
Doc : https://docs.python.org/3/library/dataclasses.html · https://docs.pydantic.dev/latest/concepts/models/
Exercice 5 min : dans un REPL `uv run python`, créer un `BaseModel` avec un champ `count: int` et appeler `model_validate({"count": "12"})` puis `{"count": "douze"}` : observer la coercition puis l'erreur.

### `httpx`
Client HTTP sync et async, API proche de `fetch` + `requests`. `httpx.Client(base_url=…, timeout=httpx.Timeout(10.0))` garde un pool de connexions : à créer une fois, à fermer (`with` ou `.close()`), pas un `Client` par requête. `response.raise_for_status()` lève `httpx.HTTPStatusError` sur 4xx/5xx ; sans cet appel, un 500 passe silencieusement (même piège que `fetch`). Erreurs réseau : `httpx.TransportError` (timeout, connexion).
Doc : https://www.python-httpx.org/advanced/clients/ · https://www.python-httpx.org/exceptions/
Exercice 5 min : `uv run python -c "import httpx; r = httpx.get('https://pokeapi.co/api/v2/pokemon?limit=1'); print(r.status_code, r.json()['count'])"`.

### Itérateurs et générateurs
Une fonction avec `yield` renvoie un générateur : paresseux, consommé une seule fois, rien n'est exécuté avant le premier `next()`. `yield from iterable` délègue. `itertools.islice(gen, n)` prend les `n` premiers sans tout matérialiser. ≈ `function*` en JS, mais omniprésent en Python (fichiers, DataFrames Spark, `boto3` paginators). Annoter `-> Iterator[T]`.
Doc : https://docs.python.org/3/tutorial/classes.html#generators · https://docs.python.org/3/library/itertools.html
Exercice 5 min : écrire un générateur `countdown(n)` qui `print("tick")` avant chaque `yield`, puis `g = countdown(3)` : constater que rien ne s'affiche avant `next(g)`.

### `pytest` fixtures et `respx`
Une fixture = fonction décorée `@pytest.fixture` ; un test la reçoit **par son nom de paramètre** (≈ `beforeEach` + injection de dépendances). `yield` dans une fixture = setup / teardown. `conftest.py` = fixtures partagées du dossier. `respx` mocke `httpx` au niveau transport (≈ `msw` / `nock`) : fixture `respx_mock`, `respx_mock.get("/path").mock(return_value=httpx.Response(200, json=…))`, `side_effect=[…]` pour une séquence, `route.called` / `route.call_count` pour asserter.
Doc : https://docs.pytest.org/en/stable/how-to/fixtures.html · https://lundberg.github.io/respx/guide/
Exercice 5 min : lire « Mocking HTTPX » de respx et noter comment limiter le mock à un `base_url` et faire échouer tout appel non mocké (`assert_all_mocked`).

## Étapes

### [ ] Étape 1 — Projet `uv` en layout `src/` et dépendances
- À faire : à la racine du repo, `uv init --package --python 3.12 --no-workspace kata/py-s1` (crée `kata/py-s1/pyproject.toml`, `src/py_s1/__init__.py`, `.python-version`, `README.md`). Dans `kata/py-s1/` : `uv add httpx pydantic` puis `uv add --dev pytest respx ruff`. Lire le `pyproject.toml` généré ligne par ligne. Ajouter `[tool.ruff] line-length = 120` et `[tool.ruff.lint] select = ["E", "F", "I", "UP", "B"]`. Créer `tests/test_smoke.py` avec un test qui importe `py_s1`.
- Concept : `pyproject.toml` ≈ `package.json`, `uv.lock` ≈ `pnpm-lock.yaml`, `[dependency-groups]` ≈ `devDependencies`, layout `src/` et installation editable du package.
- Indice : si `import py_s1` échoue dans le test, c'est que le package n'est pas installé dans le venv : `uv sync` le fait ; vérifier que `[build-system]` existe dans le `pyproject` (c'est lui qui rend le projet installable).
- Vérifier : `uv run --directory kata/py-s1 python -c "import py_s1, httpx, pydantic; print(py_s1.__file__)"` affiche un chemin dans `src/` ; `uv run --directory kata/py-s1 pytest -q` → `1 passed` ; `uv run --directory kata/py-s1 ruff check .` → `All checks passed!`.

### [ ] Étape 2 — Type hints modernes sur une fonction pure
- À faire : `src/py_s1/pagination.py` : `def next_offset(url: str | None) -> int | None` qui extrait le paramètre `offset` d'une URL `next` de PokéAPI (`…/pokemon?offset=100&limit=100`) avec `urllib.parse.urlparse` + `parse_qs`, et renvoie `None` si l'URL est `None` ou sans `offset`. Tests dans `tests/test_pagination.py` : URL normale, `None`, URL sans `offset`, `offset` non numérique (décider : lever ou `None`, et le tester).
- Concept : `X | None`, `str | None` en entrée, `urllib.parse`, règles ruff `UP` qui réécrivent `Optional[int]` → `int | None`.
- Indice : `parse_qs` renvoie `dict[str, list[str]]`, pas `dict[str, str]`. Regarde la signature avant d'indexer.
- Vérifier : `uv run --directory kata/py-s1 pytest -q -k pagination` vert (≥ 4 tests) ; `uv run --directory kata/py-s1 ruff check .` vert.

### [ ] Étape 3 — `dataclass` interne, `BaseModel` à la frontière
- À faire : `src/py_s1/models.py` : `PokemonRef` en `@dataclass(frozen=True, slots=True)` (`name: str`, `url: str`) et `PokemonPage(BaseModel)` (`count: int`, `next: str | None`, `previous: str | None`, `results: list[PokemonRef]`). Tests : `PokemonPage.model_validate(payload)` sur un dict copié d'une vraie réponse (dans `tests/fixtures/page_0.json`, chargé via `pathlib` + `json`), `ValidationError` si `count` manque, `PokemonRef` immuable (`FrozenInstanceError` à l'affectation).
- Concept : dataclass (≈ interface + constructeur) vs Pydantic (≈ `zod.parse`) ; `frozen` ; Pydantic sait valider un `list[<dataclass>]`.
- Indice : `pytest.raises(ValidationError)` est le `expect(() => …).toThrow()` ; pour l'immutabilité, l'exception vient de `dataclasses`, pas de Pydantic.
- Vérifier : `uv run --directory kata/py-s1 pytest -q -k models` vert (≥ 3 tests).

### [ ] Étape 4 — Client `httpx` : `Client` réutilisé, timeout, context manager
- À faire : `src/py_s1/client.py` : classe `PokeClient` qui crée un `httpx.Client(base_url="https://pokeapi.co/api/v2", timeout=httpx.Timeout(10.0))` dans `__init__`, expose `get_page(offset: int = 0, limit: int = 100) -> PokemonPage` (GET `/pokemon` avec `params`, `raise_for_status()`, `PokemonPage.model_validate(r.json())`), et se ferme proprement via `__enter__` / `__exit__` (ou `close()`). Un appel réel une fois, pour voir.
- Concept : pool de connexions (un `Client` par application, pas par requête), timeout explicite, protocole context manager ≈ `try/finally` + `using` ; `raise_for_status()` obligatoire.
- Indice : `__exit__` reçoit trois arguments (type, valeur, traceback) même si tu ne les utilises pas ; renvoyer `None` (ne pas avaler l'exception).
- Vérifier : `uv run --directory kata/py-s1 python -c "from py_s1.client import PokeClient; from contextlib import closing; c = PokeClient(); print(c.get_page(limit=1).count); c.close()"` affiche un entier > 1000 ; `ruff check` vert.

### [ ] Étape 5 — Tests sans réseau : fixtures + `respx`
- À faire : `tests/conftest.py` : fixture `page_payload` (charge `fixtures/page_0.json`), fixture `client` qui `yield` un `PokeClient` puis le ferme. `tests/test_client.py` : avec la fixture `respx_mock`, mocker `GET https://pokeapi.co/api/v2/pokemon` → 200 + payload, appeler `get_page`, asserter le type de retour, `route.called`, et les `params` reçus (`route.calls.last.request.url`). Deuxième test : mock 500 → `httpx.HTTPStatusError` attendu.
- Concept : fixtures par nom de paramètre, `yield` = teardown, `conftest.py` ; `respx` ≈ `msw`, `assert_all_called` / `assert_all_mocked`.
- Indice : respx matche l'URL complète ; avec un `base_url` sur le client, mocke l'URL absolue ou utilise `respx.mock(base_url=…)` comme décorateur / context manager. Regarde `route.calls.last.request.url.params`.
- Vérifier : `uv run --directory kata/py-s1 pytest -q -k client` vert ; couper le Wi-Fi et relancer : toujours vert (preuve zéro réseau).

### [ ] Étape 6 — Générateur paginé paresseux
- À faire : dans `client.py`, `iter_pokemon(self, limit: int = 100) -> Iterator[PokemonRef]` : boucle `get_page` → `yield from page.results` → `offset = next_offset(page.next)` → stop quand `None`. Tests respx avec deux pages (`page_0.json` avec `next`, `page_1.json` avec `next: null`) : (a) `list(client.iter_pokemon())` renvoie la somme des deux pages ; (b) `itertools.islice(client.iter_pokemon(), 3)` consomme **une seule** requête (`route.call_count == 1`).
- Concept : `yield` / `yield from`, paresse (aucun appel HTTP avant le premier `next()`), `Iterator[T]` en type de retour, `islice`. C'est la forme exacte de `fetch_day(date) -> Iterator[dict]` de S1-06.
- Indice : si le test (b) voit 2 appels, c'est que la requête de la page suivante part **avant** que les items de la page courante soient tous rendus : place l'appel réseau au bon endroit dans la boucle.
- Vérifier : `uv run --directory kata/py-s1 pytest -q -k iter` vert (2 tests).

### [ ] Étape 7 — Retries exponentiels sur 429 / 5xx, `sleep` injecté
- À faire : dans `client.py`, `_get(path, params)` avec `max_retries: int = 3` et `sleep: Callable[[float], None] = time.sleep` passés au constructeur. Boucle `for attempt in range(max_retries + 1)` : si statut 429 ou ≥ 500 → délai = `Retry-After` si présent sinon `base * 2 ** attempt`, `sleep(délai)`, recommencer ; sinon `raise_for_status()` et retour. Après le dernier essai : relever l'erreur. Tests respx avec `side_effect=[Response(429, headers={"Retry-After": "2"}), Response(200, json=…)]` ; `sleep` remplacé par une liste qui enregistre les délais ; test « 4 × 500 » → exception et `call_count == 4`.
- Concept : backoff exponentiel, `Retry-After`, injection de dépendance par paramètre (≈ fake timers), `httpx` ne retente pas les erreurs HTTP par lui-même (`transport=httpx.HTTPTransport(retries=…)` ne couvre que la connexion). `tenacity` existe : on l'utilisera peut-être en S1-06, après avoir compris la version manuelle.
- Indice : ne pas `sleep` après le dernier échec ; ne pas retenter les 4xx autres que 429 (un 404 ne se répare pas en attendant).
- Vérifier : `uv run --directory kata/py-s1 pytest -q -k retry` vert ; le test asserte la liste exacte des délais (ex. `[2.0]` puis `[0.5, 1.0, 2.0]`).

### [ ] Étape 8 — Couverture ≥ 80 % et finition
- À faire : `uv add --dev pytest-cov`, `uv run pytest --cov=py_s1 --cov-report=term-missing`, lire les lignes manquantes, ajouter les tests qui manquent (branches `None`, `Retry-After` absent). `uv run ruff format .` puis `ruff check`. Mettre à jour `kata/py-s1/README.md` : comment lancer, ce que le client fait, ce que tu referais autrement.
- Concept : couverture par branche vs par ligne, `term-missing`, `ruff format` ≈ prettier. S1-06 exige ≥ 80 %.
- Indice : une couverture à 100 % obtenue en testant `__repr__` ne vaut rien ; vise les branches d'erreur.
- Vérifier : `uv run --directory kata/py-s1 pytest -q --cov=py_s1 --cov-report=term` → `TOTAL … ≥ 80%` ; `uv run --directory kata/py-s1 ruff check .` et `ruff format --check .` verts.

### [ ] Étape 9 — Vendredi : client paginé en 45 min, sans aide
- À faire : nouveau projet `kata/py-s1-vendredi/` créé **de mémoire** (`uv init --package`, deps). Cible : `https://recherche-entreprises.api.gouv.fr/search?q=<terme>&page=1&per_page=25` → `results`, `total_results`, `page`, `total_pages`, `per_page`. Livrer : modèle Pydantic minimal (`siren`, `nom_complet`), client `httpx` avec timeout, générateur `iter_results(q) -> Iterator[Entreprise]` qui enchaîne les pages jusqu'à `total_pages`, retry sur 429, tests respx (2 pages + 429). Minuteur 45 min, pas d'IA, pas de doc web ; REPL et `help()` autorisés. Commit avec temps réel et verdict ; ligne dans `kata/JOURNAL.md`.
- Concept : transfert : même architecture, autre style de pagination (`page`/`total_pages` au lieu de `next`). Rythme d'entretien.
- Indice : décide l'ordre avant de lancer le chrono : modèle → client → générateur → tests, ou tests d'abord. Pas de retouche d'ordre pendant.
- Vérifier : `uv run --directory kata/py-s1-vendredi pytest -q` (vert ou rouge : verdict consigné) ; `git log --grep='vendredi' --oneline -- kata/py-s1-vendredi` ≥ 1.

## Pièges courants (dev TS → Python)
1. **Un générateur se consomme une fois** : `items = client.iter_pokemon(); len(list(items)); list(items)` → la seconde liste est vide. Pas de `.map()` / `.filter()` dessus : compréhension ou `itertools`. `list(gen)` matérialise, et perd la paresse.
2. **Les hints ne valident rien** : `def f(n: int)` accepte `"12"` sans broncher. Seul Pydantic (ou un type checker avant exécution) attrape l'erreur. Une `dataclass` n'est pas un `zod`.
3. **`fetch` et `httpx` partagent le même piège** : un 404 ou 500 ne lève rien tant que tu n'appelles pas `raise_for_status()`. Et `httpx.Client` est synchrone : pas d'`await`, pas de promesse, `AsyncClient` seulement si tu es dans `asyncio`.
4. **Un `Client` par requête** = handshake TLS à chaque appel et sockets qui traînent. Un seul `Client`, fermé dans `__exit__` ou `close()`. Même logique que réutiliser un `Agent` Node ou un client `boto3`.
5. **Imports en layout `src/`** : toujours `from py_s1.models import …` (absolu, nom du package), jamais `from models import …` ni chemins relatifs à la `../`. Si ça marche dans le REPL mais pas sous pytest, c'est un problème d'installation du package, pas d'import.

## Critères de validation
(déduits des Notions et du Vendredi de la carte, croisés avec S1-06 ; pas de « Critères d'acceptation » sur la carte)
- [ ] `kata/py-s1/` en layout `src/` : `uv sync` passe, `uv run ruff check .` vert, `httpx` + `pydantic` en deps, `pytest` + `respx` + `ruff` en dev.
- [ ] Une `dataclass` gelée et un `BaseModel` Pydantic testés (validation OK, `ValidationError`, immutabilité).
- [ ] Client `httpx` avec `Client` unique, timeout explicite, `raise_for_status`, fermeture propre ; tests `respx` verts sans réseau.
- [ ] Générateur paginé `-> Iterator[PokemonRef]` dont la paresse est prouvée par un test (`islice` → 1 appel).
- [ ] Retries exponentiels sur 429 / 5xx avec `Retry-After` et `sleep` injecté, délais assertés.
- [ ] Couverture ≥ 80 % (`pytest --cov=py_s1`).
- [ ] Vendredi : client paginé Recherche d'entreprises + tests en 45 min sans aide, verdict et temps dans le commit et `kata/JOURNAL.md`.

## Question de compréhension
S1-06 impose `fetch_day(date) -> Iterator[dict]` et non `-> list[dict]`. Qu'est-ce que ça change (a) pour la mémoire sur une journée à 50 000 annonces, (b) pour le **moment** où une erreur réseau ou un 429 surgit chez l'appelant, (c) pour la façon d'écrire les tests ?

## Journal
- 2026-10-20 — Plan généré. Carte sans checklist ni « Critères d'acceptation » : 7 critères déduits (Notions + Vendredi + S1-06). Pas de `pyproject.toml` ni de `kata/` dans le repo : mini-projet `kata/py-s1/` créé à l'étape 1. API d'entraînement : PokéAPI (semaine), Recherche d'entreprises (vendredi), BODACC réservé à S1-06.
