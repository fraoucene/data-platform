---
title: "Cartes · Tests Python (pytest)"
type: cartes
langage: Python
cours: Tests
created: 2026-10-24
updated: 2026-10-24
---

# Cartes · Tests Python (pytest)
Python · Tests : assertions, config, couverture, fixtures, marqueurs, mocks (format spec v3 de revision-pwa).

## 1. pytest : @fixture
- Sous-thème : fixtures
- Niveau : 1
- Définition : `@pytest.fixture` déclare une donnée de test ; pytest l'injecte dans chaque test qui a un paramètre du même nom.
- Contexte : L'injection se fait **par nom** : pytest lit les paramètres du test, trouve la fixture homonyme, l'exécute et passe le résultat. Chaque test reçoit une valeur neuve (portée `function` par défaut), donc un test qui modifie la donnée ne pollue pas le suivant. Les fixtures partagées vont dans `conftest.py`, visible sans import (≈ `beforeEach` qui renvoie une valeur).
- Usage : ✅ données de test réutilisées (annonce type, client HTTP mocké, dossier temporaire) · ❌ donnée utilisée par un seul test : la définir dans le test.

```python
# Exemple 1 : injectée par nom
import pytest
@pytest.fixture
def annonce():
    return {"siren": "483609327"}
def test_siren(annonce):  # même nom
    assert len(annonce["siren"]) == 9
# pytest -q : 1 passed
```

```python
# Exemple 2 : fixtures en chaîne
import pytest

@pytest.fixture
def siren():
    return "483609327"

@pytest.fixture
def annonce(siren):  # injectée
    return {"id": "A1", "siren": siren}

def test_id(annonce):
    assert annonce["id"] == "A1"
# pytest -q : 1 passed
```

- Quiz : Que se passe-t-il si un test appelle `annonce()` directement au lieu de la recevoir en paramètre ?
- [ ] Le test reçoit le dict, il passe
- [ ] Le test reçoit `None`
- [x] Le test échoue : fixture appelée directement
- [ ] pytest ignore le test
- Réponse : Le test échoue (`Fixture "annonce" called directly`) : une fixture ne s'appelle pas, pytest la crée et l'injecte.

## 2. assert : l'introspection de pytest
- Sous-thème : assertions
- Niveau : 1
- Définition : Un test pytest vérifie avec le simple `assert` de Python ; pytest le réécrit pour afficher les valeurs comparées en cas d'échec (≈ `expect(a).toEqual(b)`).
- Contexte : Pas de `assertEqual` ni de matchers : pytest réécrit les `assert` des fichiers de test à l'import et, en échec, détaille les deux côtés (éléments différents d'un dict, index d'une liste, diff de chaînes). Un message optionnel suit la virgule : `assert cond, "message"`. La réécriture ne vaut que pour les modules de test et `conftest.py`, pas pour le code applicatif.
- Usage : ✅ comparer directement le résultat attendu (`==` sur dicts, listes, modèles) · ❌ `assert` dans le code de production pour valider une entrée : `python -O` les supprime, lever `ValueError`.

```python
# Exemple 1 : un dict qui diffère
def test_tribunal():
    a = {"siren": "483609327",
         "tribunal": "Lyon"}
    assert a == {"siren": "483609327",
                 "tribunal": "Paris"}
# pytest affiche :
# Omitting 1 identical items
# Differing items:
# {'tribunal': 'Lyon'} != {'tribunal': 'Paris'}
```

```python
# Exemple 2 : un message en plus
def test_siren():
    s = "48360932"
    assert len(s) == 9, f"SIREN {s!r}"
# AssertionError: SIREN '48360932'
# assert 8 == 9
```

- Quiz : Que fait `assert (x == 1, "x doit valoir 1")` (parenthèses autour du tout) avec `x = 2` ?
- [ ] Le test échoue avec le message
- [x] Le test passe, avec un avertissement
- [ ] `SyntaxError` à la collecte
- [ ] `TypeError` : tuple non booléen
- Réponse : le test passe (`PytestAssertRewriteWarning: assertion is always true`) : un tuple non vide est toujours vrai ; ne pas parenthéser `assert`.

## 3. découverte : ce que pytest collecte
- Sous-thème : config
- Niveau : 1
- Définition : pytest collecte les fichiers `test_*.py` ou `*_test.py`, puis leurs fonctions `test*` et les méthodes `test*` des classes `Test*`.
- Contexte : Pas de registre ni d'import à écrire : la convention de nommage suffit, comme `*.test.ts` pour Jest. Une fonction mal nommée n'est jamais lancée, sans aucune erreur : le test « passe » parce qu'il n'existe pas. `pytest --co -q` liste ce qui est collecté avant toute exécution. Les règles se changent dans `[tool.pytest.ini_options]` (`python_files`, `python_functions`), rarement utile.
- Usage : ✅ `pytest --co -q` quand un nouveau test n'apparaît pas dans le compte · ❌ changer `python_functions` pour coller à un nommage maison : renommer les tests.

```python
# Exemple 1 : tests/test_siren.py
def test_siren_valide():   # collecté
    assert len("483609327") == 9

def verifie_siren_court(): # ignoré
    assert False           # jamais lancé

class TestSiren:           # collectée
    def test_chiffres(self):
        assert "483609327".isdigit()
```

```bash
# Exemple 2 : lister sans lancer
# (-q déjà dans addopts : pas de -q)
uv run pytest --co tests/test_siren.py
# tests/test_siren.py::test_siren_valide
# tests/test_siren.py::TestSiren::test_chiffres
# 2 tests collected
```

- Quiz : `class TestSiren` reçoit un `__init__(self)` : ses méthodes `test_*` sont-elles lancées ?
- [ ] Oui, pytest appelle `__init__` d'abord
- [ ] Oui, `__init__` est ignoré
- [x] Non, classe ignorée avec un avertissement
- [ ] Non, erreur de collecte
- Réponse : non : `PytestCollectionWarning: cannot collect test class 'TestSiren' because it has a __init__ constructor` ; préparer l'état avec une fixture.

## 4. pytest.raises : attendre une exception
- Sous-thème : assertions
- Niveau : 1
- Définition : `with pytest.raises(ValueError, match="…")` réussit si le bloc lève cette exception (ou une sous-classe) dont le message correspond à la regex.
- Contexte : `match` est une **regex** cherchée avec `re.search` dans `str(exception)` : une sous-chaîne suffit, mais `(`, `.`, `[` ou `+` ont leur sens de regex ; `re.escape` les neutralise. `as exc` donne accès à l'exception (`exc.value`) après le bloc. Le code placé après la ligne qui lève, dans le `with`, ne s'exécute jamais : une ligne par `raises`.
- Usage : ✅ tester un refus (`max_attempts=0`, SIREN invalide, 429 épuisé) avec son message · ❌ `try/except` + `assert False` à la main : `raises` est plus court et plus clair.

```python
# Exemple 1 : type et message
import pytest
def client(max_attempts):
    if max_attempts < 1:
        raise ValueError(f"reçu {max_attempts}")
with pytest.raises(ValueError, match="reçu 0"):
    client(0)
```

```python
# Exemple 2 : parenthèses : re.escape
import re
import pytest

def client(n):
    raise ValueError(f"max_attempts (reçu {n})")

msg = re.escape("(reçu 0)")
with pytest.raises(ValueError,
                   match=msg) as exc:
    client(0)
str(exc.value)  # → "max_attempts (reçu 0)"
```

- Quiz : Dans un test, `client(1)` ne lève rien sous `with pytest.raises(ValueError):` : résultat ?
- [ ] Le test passe : aucune erreur
- [x] Le test échoue : `DID NOT RAISE`
- [ ] Le test est ignoré (`skipped`)
- [ ] `ValueError` levée par pytest
- Réponse : échec, `Failed: DID NOT RAISE ValueError` : `raises` exige que l'exception se produise dans le bloc.

## 5. tmp_path : un dossier par test
- Sous-thème : fixtures
- Niveau : 1
- Définition : La fixture intégrée `tmp_path` fournit un dossier temporaire vide, propre à chaque test, sous forme de `pathlib.Path`.
- Contexte : Chaque test reçoit un dossier distinct (`…/pytest-of-<user>/pytest-N/test_ecrit0`) : deux tests qui écrivent `a.json` ne se marchent pas dessus. pytest garde les 3 dernières sessions pour l'inspection, puis nettoie. Pour un dossier partagé par plusieurs tests (scope `session`), `tmp_path_factory.mktemp("raw")`. C'est un `Path`, pas une chaîne : on compose avec `/`.
- Usage : ✅ tester une écriture de fichier (JSONL, CSV, gzip) sans toucher au dépôt · ❌ écrire dans `/tmp/test.json` en dur : collisions entre tests et fichiers laissés derrière.

```python
# Exemple 1 : écrire puis relire
import json
def test_ecrit(tmp_path):
    f = tmp_path / "dt=2026-10-20.jsonl"
    f.write_text(json.dumps({"id": "A1"}))
    assert json.loads(f.read_text()) == {
        "id": "A1"}
# pytest -q : 1 passed
```

```python
# Exemple 2 : un dossier pour la session
import pytest

@pytest.fixture(scope="session")
def raw(tmp_path_factory):
    return tmp_path_factory.mktemp("raw")

def test_vide(raw):
    assert list(raw.iterdir()) == []
# pytest -q : 1 passed
```

- Quiz : Que donne `tmp_path + "/a.json"` dans un test ?
- [ ] `"…/test_x0/a.json"`, une chaîne
- [ ] Un `Path` vers `a.json`
- [x] `TypeError`
- [ ] `AttributeError`
- Réponse : `TypeError` : `tmp_path` est un `Path`, qui ne s'additionne pas à une chaîne ; écrire `tmp_path / "a.json"`.

## 6. lancer : -k, -x et --lf
- Sous-thème : config
- Niveau : 1
- Définition : `-k "expr"` filtre les tests par nom, `-x` s'arrête au premier échec, `--lf` relance seulement les tests en échec à la dernière exécution.
- Contexte : `-k` cherche des sous-chaînes dans les noms (fichier, classe, fonction) et accepte `and`, `or`, `not`. `--lf` lit le cache `.pytest_cache` (à ignorer dans git) : la boucle courante est `pytest -x`, corriger, `pytest --lf`, puis la suite complète. Un chemin précis cible aussi : `pytest tests/test_retry.py::test_429_puis_200`.
- Usage : ✅ itérer vite sur un test rouge (`-x`, `--lf`, `::nom`) · ❌ committer après `--lf` vert sans relancer toute la suite : un autre test a pu casser.

```bash
# Exemple 1 : filtrer par nom
uv run pytest -k "siren and not court"
# 1 passed, 3 deselected
uv run pytest -k "siren or date"
# 2 failed, 1 passed, 1 deselected
```

```bash
# Exemple 2 : la boucle de correction
uv run pytest -x     # stop au 1er échec
# 1 failed, 1 passed
uv run pytest --lf   # ce test seul
# 1 failed
```

- Quiz : Tests `test_siren_valide` et `test_siren_court` : combien `pytest -k Siren` (majuscule) en sélectionne-t-il ?
- [ ] `0` : `-k` respecte la casse
- [x] `2`
- [ ] `1`
- [ ] Erreur : expression invalide
- Réponse : `2` : depuis pytest 5.4, `-k` ignore la casse ; `Siren` trouve `siren` dans les deux noms.

## 7. pytest : @mark.parametrize
- Sous-thème : marqueurs
- Niveau : 2
- Définition : `@pytest.mark.parametrize("arg", valeurs)` lance le même test une fois par valeur, chacune comptée comme un test séparé.
- Contexte : Le premier argument liste les noms des paramètres (séparés par des virgules), le second les valeurs : un tuple par cas quand il y a plusieurs noms. Chaque cas a son propre identifiant (`test_valide[123-False]`) et échoue indépendamment : un cas rouge n'arrête pas les autres (≈ `test.each` en Jest). `pytest.param(..., id="court")` donne un nom lisible.
- Usage : ✅ même règle testée sur plusieurs entrées (SIREN valides et invalides, dates limites) · ❌ cas qui demandent des assertions différentes : tests séparés.

```python
# Exemple 1 : trois cas, un test
import pytest
@pytest.mark.parametrize("siren, ok", [
    ("483609327", True),
    ("123", False),
    ("48360932A", False),
])
def test_valide(siren, ok):
    assert (len(siren) == 9
            and siren.isdigit()) == ok
# pytest -q : 3 passed
```

- Quiz : Combien de tests lance pytest avec deux `@pytest.mark.parametrize` empilés, de 2 et 3 valeurs ?
- [ ] `5`
- [ ] `3`
- [ ] `2`
- [x] `6`
- Réponse : `6` : des parametrize empilés font le produit cartésien des valeurs (2 × 3).

## 8. pytest : fixture avec yield
- Sous-thème : fixtures
- Niveau : 2
- Définition : Une fixture qui fait `yield` prépare avant, livre la valeur au test, puis nettoie après (≈ `beforeEach` + `afterEach` réunis).
- Contexte : pytest exécute la fixture jusqu'au `yield`, passe la valeur au test, puis reprend après le `yield` une fois le test terminé, **qu'il passe ou échoue**. Le nettoyage reste ainsi à côté de la préparation. Avec `scope="module"` ou `"session"`, la préparation n'a lieu qu'une fois pour plusieurs tests (connexion, bucket S3 mocké par moto).
- Usage : ✅ ressource à libérer (fichier, connexion, mock `moto` démarré puis arrêté) · ❌ simple donnée sans nettoyage : `return`.

```python
# Exemple 1 : avant, pendant, après
import pytest
@pytest.fixture
def dossier(tmp_path):
    d = tmp_path / "raw"
    d.mkdir()     # avant le test
    yield d       # livré au test
    for f in d.iterdir():
        f.unlink()  # après le test

def test_ecrit(dossier):
    f = dossier / "a.json"
    f.write_text("{}")
    assert f.exists()
# pytest -q : 1 passed
```

- Quiz : Si `test_ecrit` échoue sur son `assert`, le code après `yield` s'exécute-t-il ?
- [ ] Non, seulement si le test passe
- [x] Oui, toujours
- [ ] Seulement avec un `try/finally`
- [ ] Non, la fixture est abandonnée
- Réponse : Oui, toujours : pytest exécute la partie après `yield` (teardown) que le test passe ou échoue ; pas besoin de `try/finally`.

## 9. conftest.py : des fixtures par dossier
- Sous-thème : fixtures
- Niveau : 2
- Définition : Les fixtures d'un `conftest.py` sont visibles, sans import, par tous les tests de son dossier et de ses sous-dossiers.
- Contexte : pytest charge chaque `conftest.py` sur le chemin d'un test, de la racine vers le test : la portée suit l'arborescence. Une fixture du même nom plus proche (sous-dossier ou module de test) masque celle du dessus. Un `conftest.py` ne s'importe jamais (`from conftest import …` casse en `importlib`). Dans un monorepo, chaque membre garde les siennes dans `packages/<membre>/tests/conftest.py`.
- Usage : ✅ fixtures partagées par plusieurs fichiers d'un dossier (`export_text`, `export_rows` de bodacc-client) · ❌ tout mettre dans un `conftest.py` racine : un membre voit des fixtures qui ne le concernent pas.

```bash
# Exemple 1 : la portée suit les dossiers
packages/bodacc-client/tests/
├── conftest.py      # export_rows
├── test_models.py   # la voit
└── fixtures/
packages/dp-common/tests/
└── test_smoke.py    # ne la voit pas
```

```python
# Exemple 2 : tests/conftest.py
import json
import pytest

@pytest.fixture
def export_text():
    return '{"id": "A1"}\n{"id": "A2"}\n'

@pytest.fixture
def export_rows(export_text):
    return [json.loads(l)
            for l in export_text.splitlines()]
```

- Quiz : `packages/dp-common/tests/test_smoke.py` demande `export_rows` (du conftest de bodacc-client) : résultat ?
- [ ] Le test reçoit les annonces
- [ ] Le test reçoit `None`
- [x] Erreur : `fixture 'export_rows' not found`
- [ ] `ImportError` sur `conftest`
- Réponse : `fixture 'export_rows' not found` : un `conftest.py` ne sert que son dossier et ses sous-dossiers ; les dossiers frères ne le voient pas.

## 10. caplog : vérifier les logs
- Sous-thème : fixtures
- Niveau : 2
- Définition : La fixture `caplog` capture les logs émis pendant le test : `caplog.records` (objets `LogRecord`), `caplog.text` (texte formaté).
- Contexte : Utile quand le log fait partie du contrat : un rejet doit être journalisé avec le SIREN, un retry avec son délai. `caplog` ne voit que ce que le logger émet : si le niveau effectif est `WARNING` (défaut du root), un `info` n'existe même pas. `caplog.set_level(logging.INFO)` abaisse le niveau pendant le test seulement ; `logger=` le cible sur un logger précis.
- Usage : ✅ vérifier qu'un rejet ou un retry est journalisé, avec ses champs · ❌ tester le texte exact d'un message de debug : fragile, préférer `levelname` et quelques mots-clés.

```python
# Exemple 1 : le retry est journalisé
import logging
log = logging.getLogger("bodacc")
def test_log_retry(caplog):
    caplog.set_level(logging.INFO)
    log.info("retry dans %s s", 2)
    r = caplog.records[0]
    assert r.getMessage() == "retry dans 2 s"
    assert r.levelname == "INFO"
# pytest -q : 1 passed
```

- Quiz : Même test **sans** `caplog.set_level(...)` (aucune config de logging) : que vaut `caplog.records` ?
- [ ] La liste avec le message `INFO`
- [x] `[]`
- [ ] `None`
- [ ] `AttributeError`
- Réponse : `[]` : le logger hérite du niveau `WARNING` du root, l'`info` est filtré avant d'atteindre le handler de `caplog`.

## 11. --import-mode=importlib : des tests homonymes
- Sous-thème : config
- Niveau : 2
- Définition : `--import-mode=importlib` importe chaque fichier de test sous un nom tiré de son chemin, sans toucher `sys.path` : deux `test_smoke.py` cohabitent.
- Contexte : En mode par défaut (`prepend`), pytest ajoute le dossier du test à `sys.path` et l'importe comme module nu `test_smoke`. Un second membre avec son `tests/test_smoke.py`, sans `__init__.py`, donne le même nom : `import file mismatch`. Dans un monorepo, chaque membre a ses `tests/` : le mode se pose dans `addopts` dès le premier membre.
- Usage : ✅ monorepo, `tests/` homonymes dans plusieurs membres · ❌ s'en remettre à des noms de fichiers uniques entre membres : fragile dès le deuxième.

```bash
# Exemple 1 : mode par défaut
# packages/a/tests/test_smoke.py
# packages/b/tests/test_smoke.py
pytest
# ERROR collecting packages/b/tests/…
# import file mismatch
```

```toml
# Exemple 2 : pyproject.toml racine
[tool.pytest.ini_options]
testpaths = ["packages", "lambdas", "jobs"]
addopts = "-q --import-mode=importlib"
# pytest → 2 passed
```

- Quiz : En mode `importlib`, `tests/test_h.py` fait `from helpers import SIREN` (`helpers.py` à côté) : résultat ?
- [ ] Import réussi : même dossier
- [x] `ModuleNotFoundError: No module named 'helpers'`
- [ ] `import file mismatch`
- [ ] Import réussi, avec un avertissement
- Réponse : `ModuleNotFoundError` : `importlib` ne met plus le dossier du test dans `sys.path` ; partager via une fixture de `conftest.py` ou un vrai module.

## 12. addopts : des options invisibles
- Sous-thème : config
- Niveau : 2
- Définition : `addopts` ajoute ses options à chaque lancement de pytest, avant celles de la ligne de commande : invisibles, mais toujours actives.
- Contexte : Un `-q` dans `addopts` masque déjà l'en-tête (`rootdir`, `configfile`) ; en taper un second donne `-qq`. Quand une sortie surprend, `-o addopts=""` relance sans elles, en-tête compris : il prouve quel `pyproject.toml` est lu. Attention : cela retire aussi `--import-mode=importlib`, et les membres homonymes se percutent à nouveau.
- Usage : ✅ options de projet (`-q`, `--import-mode`, `-m 'not integration'`) · ❌ y mettre une option qu'on doit parfois retirer à la main : un marqueur ou une cible Makefile dédiée.

```bash
# Exemple 1 : -q + -q = -qq
# addopts = "-q --import-mode=importlib"
pytest --collect-only -q
# packages/a/tests/test_smoke.py: 1
# packages/b/tests/test_smoke.py: 1
# (un compte par fichier : -qq)
```

```bash
# Exemple 2 : relancer sans addopts
pytest -o addopts="" \
  --import-mode=importlib --collect-only
# rootdir: /…/data-platform
# configfile: pyproject.toml
# testpaths: packages, lambdas, jobs
```

- Quiz : Avec `addopts = "-q"`, `pytest -q` sur deux tests verts : que reste-t-il de la sortie ?
- [ ] `..` puis `2 passed in 0.02s`
- [ ] L'en-tête `rootdir`, puis `2 passed`
- [x] `..` seul, sans résumé
- [ ] Rien du tout
- Réponse : `..` seul : en `-qq`, pytest supprime aussi la ligne de résumé ; le code retour (0) reste le seul verdict.

## 13. pytest.approx : comparer des flottants
- Sous-thème : assertions
- Niveau : 2
- Définition : `x == pytest.approx(attendu)` compare des flottants à une tolérance près (relative `1e-6` par défaut), aussi dans des listes et des dicts.
- Contexte : `0.1 + 0.2 == 0.3` est faux en Python comme en JS (binaire IEEE 754). `approx` accepte un écart relatif de `1e-6` de l'attendu, ou absolu de `1e-12` : la plus large des deux. Près de zéro, c'est donc l'absolu qui joue, très serré. `rel=` et `abs=` ajustent. Il fonctionne sur des listes, tuples et dicts de nombres (≈ `toBeCloseTo`, en plus général).
- Usage : ✅ taux, montants calculés, moyennes, scores de similarité · ❌ montants financiers exacts : `Decimal` et égalité stricte.

```python
# Exemple 1 : le classique 0.1 + 0.2
import pytest
0.1 + 0.2 == 0.3                 # → False
0.1 + 0.2 == pytest.approx(0.3)  # → True
1000.0001 == pytest.approx(1000) # → True
```

```python
# Exemple 2 : dans une structure
import pytest

taux = {"rejet": 0.1 + 0.2, "ok": 0.7}
taux == pytest.approx(
    {"rejet": 0.3, "ok": 0.7})  # → True
[0.1 + 0.2] == pytest.approx([0.3])
# → True
```

- Quiz : Que vaut `1e-9 == pytest.approx(0)` ?
- [ ] `True` : `1e-9` est négligeable
- [x] `False`
- [ ] `ValueError` : approx de zéro
- Réponse : `False` : relatif à zéro, la tolérance tombe à l'absolu `1e-12` ; passer `abs=1e-6` pour comparer à zéro.

## 14. @pytest.mark : exclure par défaut
- Sous-thème : marqueurs
- Niveau : 2
- Définition : Un marqueur (`@pytest.mark.integration`) étiquette des tests ; `-m 'not integration'` dans `addopts` les exclut de la suite par défaut.
- Contexte : Un test sur la vraie API est lent et dépend du réseau : il doit être opt-in. On déclare le nom dans `markers`, on l'exclut dans `addopts`, et `pytest -m integration` en ligne de commande **remplace** le `-m` d'`addopts` : seuls les tests marqués tournent. `pytestmark = pytest.mark.integration` marque tout un module. Les tests écartés apparaissent en `deselected`.
- Usage : ✅ tests d'intégration réseau, tests lents, cible `make test-integration` · ❌ marquer un test cassé pour l'oublier : `@pytest.mark.skip(reason=…)`, ou le corriger.

```toml
# Exemple 1 : déclarer et exclure
[tool.pytest.ini_options]
markers = ["integration: vraie API"]
addopts = "-q -m 'not integration'"
```

```bash
# Exemple 2 : 2 tests unitaires, 1 marqué
uv run pytest
# → 2 passed, 1 deselected
uv run pytest -m integration
# → 1 passed, 2 deselected
```

- Quiz : Un test marqué `@pytest.mark.integraton` (faute de frappe) : `uv run pytest` le lance-t-il ?
- [ ] Non, il est exclu comme `integration`
- [x] Oui, avec un avertissement
- [ ] Non, erreur de collecte
- [ ] Oui, sans rien signaler
- Réponse : oui, avec `PytestUnknownMarkWarning` : le marqueur inconnu ne matche pas `not integration` ; `--strict-markers` en fait une erreur de collecte.

## 15. xfail : un échec attendu
- Sous-thème : marqueurs
- Niveau : 2
- Définition : `@pytest.mark.xfail(reason=…)` déclare un test qui doit échouer (bug connu) : son échec ne casse pas la suite, il est compté `xfailed`.
- Contexte : À la différence de `skip`, le test tourne : on voit le jour où il se met à passer. Par défaut, un xfail qui passe devient `XPASS` et la suite reste verte, en silence. `strict=True` (ou `xfail_strict = true` dans la config) en fait un échec : on est forcé de retirer le marqueur une fois le bug corrigé. `raises=` limite l'échec attendu à un type d'exception.
- Usage : ✅ documenter un bug connu par un test, en attendant le correctif (cas BODACC non géré) · ❌ cacher un test instable : le corriger ou le supprimer ; test sans objet ici : `skip` / `skipif`.

```python
# Exemple 1 : bug connu, test rouge attendu
import pytest
@pytest.mark.xfail(reason="siren RM absent",
                   strict=True)
def test_artisan_sans_rm():
    sirens = []   # bug : liste vide
    assert sirens == ["922795315"]
# pytest -q : 1 xfailed
```

```toml
# Exemple 2 : strict pour tout le projet
[tool.pytest.ini_options]
xfail_strict = true
```

- Quiz : Sans `strict`, le bug est corrigé et le test `xfail` passe : que rend `pytest` ?
- [ ] `1 failed`, code retour 1
- [ ] `1 passed`
- [x] `1 xpassed`, code retour 0
- [ ] `1 skipped`
- Réponse : `1 xpassed`, code retour 0 : sans `strict`, un xfail qui passe reste vert ; le marqueur oublié ment ensuite sur l'état du code.

## 16. respx : une réponse par appel
- Sous-thème : mocks
- Niveau : 2
- Définition : `respx` intercepte les requêtes `httpx` (≈ `msw`) ; `side_effect=[r1, r2]` rend une réponse différente à chaque appel, ou lève l'exception placée dans la liste.
- Contexte : `return_value` rend toujours la même réponse ; une liste en `side_effect` rejoue un scénario : 429 puis 200, timeout puis 200. Une exception dans la liste (`httpx.ConnectTimeout("boom")`) est levée au lieu de répondre. `route.call_count` et `route.calls.last.request` vérifient ce qui est parti. Sous `respx.mock`, une requête sans route échoue : aucun appel réseau réel ne s'échappe.
- Usage : ✅ tester retries, erreurs HTTP et paramètres envoyés, sans réseau · ❌ client qui n'est pas httpx (`requests`, boto3) : `responses`, `moto`.

```python
# Exemple 1 : 429 puis 200
import httpx, respx
URL = "https://bodacc.test/exports/jsonl"
with respx.mock:
    route = respx.get(URL).mock(side_effect=[
        httpx.Response(429),
        httpx.Response(200, text="{}")])
    s = [httpx.get(URL).status_code
         for _ in range(2)]
s                  # → [429, 200]
route.call_count   # → 2
```

```python
# Exemple 2 : une exception dans la liste
import httpx, respx
URL = "https://bodacc.test/records"
with respx.mock:
    respx.get(URL).mock(side_effect=[
        httpx.ConnectTimeout("boom"),
        httpx.Response(200)])
    try:
        httpx.get(URL)
    except httpx.TimeoutException as e:
        err = type(e).__name__
    ok = httpx.get(URL).status_code
(err, ok)   # → ("ConnectTimeout", 200)
```

- Quiz : Dans l'exemple 1, que fait un 3e `httpx.get(URL)` dans le `with` ?
- [ ] Renvoie à nouveau `200`
- [ ] Renvoie `429`
- [x] `StopIteration`
- [ ] `AllMockedAssertionError`
- Réponse : `StopIteration` : la liste de `side_effect` est épuisée ; elle ne reboucle pas et ne réutilise pas la dernière réponse.

## 17. monkeypatch : env et attributs
- Sous-thème : mocks
- Niveau : 2
- Définition : La fixture `monkeypatch` remplace le temps d'un test une variable d'environnement (`setenv`) ou un attribut (`setattr`), et restaure tout après.
- Contexte : Pas besoin de `try/finally` : la restauration est automatique, que le test passe ou échoue (≈ `jest.spyOn` + `restoreAllMocks`). `delenv` simule une variable absente. Le piège : `setattr` remplace le nom dans un module donné ; si le code testé a fait `from lib import now`, il garde sa propre référence, c'est donc dans **son** module qu'il faut patcher. Hors d'un test : `pytest.MonkeyPatch.context()`.
- Usage : ✅ `RAW_BUCKET`, faux identifiants AWS, horloge ou fonction réseau remplacée · ❌ dépendance qu'on peut passer en paramètre (`sleep=`, `http=`) : l'injecter, plus simple qu'un patch.

```python
# Exemple 1 : variable d'environnement
import os, pytest
def bucket():
    return os.environ["RAW_BUCKET"]
with pytest.MonkeyPatch.context() as mp:
    mp.setenv("RAW_BUCKET", "data-platform-dev-raw")
    b = bucket()
b  # → "data-platform-dev-raw"
"RAW_BUCKET" in os.environ  # → False
```

```python
# Exemple 2 : remplacer un attribut
import time, pytest

with pytest.MonkeyPatch.context() as mp:
    mp.setattr(time, "time", lambda: 0.0)
    t = time.time()

t                # → 0.0
time.time() > 0  # → True  (restauré)
```

- Quiz : `use.py` fait `from lib import now` ; le test patche `monkeypatch.setattr(lib, "now", faux)` : que voit `use.stamp()` ?
- [ ] `faux` : `lib.now` est remplacé partout
- [x] Le vrai `now`
- [ ] `AttributeError`
- [ ] `ImportError`
- Réponse : le vrai `now` : `use` a copié la référence à l'import ; patcher `use.now`, là où le nom est utilisé.

## 18. injection : un faux plutôt qu'un patch
- Sous-thème : mocks
- Niveau : 2
- Définition : Passer la dépendance en paramètre (`sleep=`, `http=`) permet au test d'injecter un faux simple, sans patcher de module.
- Contexte : `BodaccClient(sleep=delays.append)` : en production `time.sleep`, en test une liste qui enregistre les attentes. Le test ne dort pas et vérifie les délais exacts (`[1.0, 2.0]`). Pas de chemin d'import à viser comme avec `monkeypatch`, pas de restauration : le faux ne vit que dans l'objet testé. C'est de l'injection de dépendances par défaut de paramètre, sans framework.
- Usage : ✅ horloge, attente, client HTTP, client boto3 : tout ce qui est lent ou externe · ❌ ajouter un paramètre à chaque fonction interne : injecter à la frontière (le client), une fois.

```python
# Exemple 1 : sleep remplacé par append
import time
def fetch(get, sleep=time.sleep, essais=3):
    for i in range(essais):
        if (r := get()) != 429:
            return r
        sleep(2 ** i)       # 1 s, 2 s…
reps = iter([429, 429, 200])
delais = []
fetch(lambda: next(reps), delais.append)
# → 200
delais  # → [1, 2]  (aucune attente réelle)
```

- Quiz : Le test passe `sleep=delais.append()` (avec parenthèses) : que se passe-t-il ?
- [ ] Même résultat : `delais` vaut `[1, 2]`
- [ ] `delais` reste vide, le test passe
- [x] `TypeError` dès l'appel de `append()`
- [ ] Le test dort vraiment 3 s
- Réponse : `TypeError` (`list.append() takes exactly one argument (0 given)`) : on passe la fonction elle-même, sans l'appeler.

## 19. couverture : lignes ou branches
- Sous-thème : couverture
- Niveau : 3
- Définition : `--cov-branch` mesure aussi les chemins pris (`if` faux, boucle sautée ou épuisée), pas seulement les lignes exécutées (≈ `branches` de `jest --coverage`).
- Contexte : Une ligne `for` exécutée ne dit pas si la boucle a déjà été sautée. Dans `fetch_day`, la sortie de la boucle de retry sans `return` ni `raise` n'était jamais prise : avec `max_attempts=0`, la fonction rendait une journée vide, sans requête ni erreur. Dans `Missing`, `195-196` = lignes jamais exécutées, `2->exit` = branche jamais prise. Un `# pragma: no branch` seulement après avoir rendu le chemin impossible.
- Usage : ✅ `--cov-branch --cov-report=term-missing --cov-fail-under=80` en CI, viser les branches d'erreur · ❌ `# pragma: no cover` pour atteindre le seuil : ça cache le défaut au lieu de le corriger.

```python
# Exemple 1 : le chemin jamais testé
def fetch_day(max_attempts=5):
    for essai in range(max_attempts):
        return ["A1", "A2"]  # 1er essai
    # sortie de boucle : jamais testée
fetch_day()    # → ["A1", "A2"]
fetch_day(0)   # → None  (en silence)
```

```bash
# Exemple 2 : seul test : fetch_day()
uv run pytest --cov=retry --cov-branch \
  --cov-report=term-missing
# Stmts Miss Branch BrPart Cover Missing
#     3    0      2      1   80% 2->exit
```

```python
# Exemple 3 : rendre le chemin impossible
def fetch_day(max_attempts=5):
    if max_attempts < 1:
        raise ValueError("max_attempts ≥ 1")
    for essai in range(max_attempts):
        return ["A1", "A2"]

fetch_day(0)   # ❌ ValueError
```

- Quiz : Même code et même seul test, **sans** `--cov-branch` : quelle couverture ?
- [x] `100%`
- [ ] `80%`
- [ ] `67%`
- [ ] `50%`
- Réponse : `100%` : les 3 lignes sont exécutées par `fetch_day()` ; seule la mesure des branches voit la sortie de boucle jamais prise.

## 20. scope : partager une fixture coûteuse
- Sous-thème : fixtures
- Niveau : 3
- Définition : `scope="module"` ou `"session"` crée la fixture une seule fois pour plusieurs tests, au lieu d'une fois par test (`function`).
- Contexte : Pour une ressource lente (gros fichier lu, mock S3 démarré, client HTTP), une création par module ou par session divise le temps. En échange, l'état est partagé : un test qui modifie la valeur pollue les suivants. Règle : une fixture ne peut dépendre que de fixtures de portée égale ou plus large ; demander une `function` depuis une `module` lève `ScopeMismatch`.
- Usage : ✅ ressource lente et en lecture seule (fixture enregistrée de 59 Mo, `moto` en session) · ❌ donnée que les tests modifient : portée `function`, ou copie dans chaque test.

```python
# Exemple 1 : créée une seule fois
import pytest
creations = []
@pytest.fixture(scope="module")
def client():
    creations.append(1)
    return object()
def test_1(client): pass
def test_2(client):
    assert len(creations) == 1
# pytest -q : 2 passed
```

- Quiz : `client` (scope `module`) demande en paramètre une fixture `annonce` de portée `function` : que se passe-t-il ?
- [ ] `annonce` devient `module` elle aussi
- [ ] `annonce` est recréée à chaque test
- [x] Erreur `ScopeMismatch` à la préparation
- [ ] Avertissement, puis le test passe
- Réponse : `ScopeMismatch` : une fixture large ne peut pas dépendre d'une plus étroite, qui serait détruite avant elle.

## 21. fixture paramétrée : params et request.param
- Sous-thème : fixtures
- Niveau : 3
- Définition : `@pytest.fixture(params=[...])` rejoue chaque test qui l'utilise une fois par valeur, lue dans la fixture par `request.param`.
- Contexte : `parametrize` paramètre un test ; une fixture paramétrée paramètre **tous** les tests qui la demandent, sans les toucher. Utile quand la valeur demande une préparation (un client par bulletin A, B, C, un format de fichier). Chaque cas porte un identifiant (`test_x[A]`), personnalisable par `ids=`. `request` est la fixture intégrée qui décrit la demande en cours.
- Usage : ✅ même batterie de tests sur plusieurs variantes d'une ressource (bulletins, formats, backends) · ❌ simple liste de valeurs d'entrée pour un seul test : `@pytest.mark.parametrize`.

```python
# Exemple 1 : un test, trois bulletins
import pytest
@pytest.fixture(params=["A", "B", "C"])
def bulletin(request):
    return request.param
def test_bulletin(bulletin):
    assert bulletin in "ABC"
# pytest -q : 3 passed
# test_bulletin[A] [B] [C]
```

- Quiz : Une fixture **sans** `params` lit `request.param` : que se passe-t-il au lancement du test ?
- [ ] `request.param` vaut `None`
- [x] `AttributeError` à la préparation
- [ ] Le test est ignoré
- [ ] `TypeError` à la collecte
- Réponse : `AttributeError` (`'SubRequest' object has no attribute 'param'`) : `param` n'existe que pour une fixture paramétrée.

## 22. autouse : une fixture pour tous
- Sous-thème : fixtures
- Niveau : 3
- Définition : `@pytest.fixture(autouse=True)` s'applique à tous les tests de sa portée sans qu'ils la demandent : un `beforeEach` global.
- Contexte : Placée dans un `conftest.py`, elle couvre tout le dossier ; dans un module de test, seulement ce module. Cas typique : poser de faux identifiants AWS (`AWS_ACCESS_KEY_ID=testing`) pour qu'aucun test ne touche un vrai compte, même par oubli d'un mock. Le revers : invisible dans la signature du test, elle surprend à la lecture ; à réserver aux garde-fous.
- Usage : ✅ garde-fou global (faux identifiants AWS, pas de réseau, fuseau fixé) · ❌ donnée de test utilisée par quelques tests : fixture ordinaire, demandée explicitement.

```python
# Exemple 1 : conftest.py, faux AWS
import os
import pytest

@pytest.fixture(autouse=True)
def faux_aws(monkeypatch):
    monkeypatch.setenv(
        "AWS_ACCESS_KEY_ID", "testing")

def test_lambda():   # sans paramètre
    assert os.environ[
        "AWS_ACCESS_KEY_ID"] == "testing"
# pytest -q : 1 passed
```

- Quiz : `faux_aws` est définie dans `test_a.py`, pas dans un conftest : s'applique-t-elle aux tests de `test_b.py` ?
- [ ] Oui, autouse vaut pour toute la session
- [x] Non, seulement aux tests de `test_a.py`
- [ ] Oui, si `test_b.py` est dans le même dossier
- [ ] Non, et `test_a.py` lève une erreur
- Réponse : non : une fixture `autouse` a la portée de l'endroit où elle est définie ; pour tout un dossier, la mettre dans son `conftest.py`.
