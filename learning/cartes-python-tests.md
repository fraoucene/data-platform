---
title: "Cartes · Tests Python (pytest)"
type: cartes
langage: Python
chapitre: Qualité et outillage
cours: Tests
created: 2026-10-24
updated: 2026-10-26
---

# Cartes · Tests Python (pytest)
Python · Tests : assertions, config, couverture, fixtures, marqueurs, mocks (format spec v3 de revision-pwa).

## 1. pytest : @fixture
- Id : tests-fixture-injection-par-nom
- Sous-thème : fixtures
- Type : concept
- Niveau : 1
- Profils : débutant, data
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
- Id : tests-assert-introspection
- Sous-thème : assertions
- Type : concept
- Niveau : 1
- Profils : débutant, data
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
- Id : tests-decouverte-nommage
- Sous-thème : config
- Type : piège
- Niveau : 1
- Profils : débutant, data
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
- Id : tests-raises-exception
- Sous-thème : assertions
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Prérequis : exceptions-raise-lever
- Voir aussi : tests-raises-trop-large, tests-match-casse-ancres
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
- Id : tests-tmp-path
- Sous-thème : fixtures
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Prérequis : tests-fixture-injection-par-nom
- Voir aussi : fichiers-temporaires-temporarydirectory-jetable
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
- Id : tests-lancer-k-x-lf
- Sous-thème : config
- Type : recette
- Niveau : 1
- Profils : débutant, ops
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

## 7. pytest.raises : plusieurs types
- Id : tests-raises-plusieurs-types
- Sous-thème : assertions
- Type : concept
- Niveau : 1
- Profils : débutant, data
- Prérequis : tests-raises-exception
- Voir aussi : exceptions-except-plusieurs-types
- Source : data-platform · S1-07
- Définition : `pytest.raises((ValueError, TypeError))` accepte un tuple : le test passe si le bloc lève l'un des types listés.
- Contexte : Même règle que `except (A, B)` : le tuple entre parenthèses, sous-classes comprises. `exc.type` dit lequel a été levé, pour une assertion plus fine. Mais un contrat précis se teste précisément : si la fonction promet `ValueError` pour toute entrée invalide (comme `resolve_day`), le test doit l'exiger seule, sinon une `TypeError` non voulue passerait inaperçue.
- Usage : ✅ fonction qui documente deux types possibles, test de bas niveau sur la stdlib · ❌ masquer l'hésitation sur le type réellement levé : fixer le contrat, puis le tester.

```python
# Exemple 1 : l'un ou l'autre
import pytest
from datetime import date
with pytest.raises((ValueError,
                    TypeError)) as exc:
    date.fromisoformat(20261020)
exc.type.__name__   # → "TypeError"
```

- Quiz : `with pytest.raises(ValueError):` entoure `date.fromisoformat(20261020)`. Résultat du test ?
- [ ] Il passe : une erreur a été levée
- [x] Il échoue : la `TypeError` traverse
- [ ] Il échoue : `DID NOT RAISE`
- [ ] Il est ignoré (`skipped`)
- Réponse : échec sur `TypeError` : `raises` ne capture que le type demandé ; toute autre exception remonte et fait échouer le test.

## 8. instant de test : une constante aware
- Id : tests-instant-fixe-aware
- Sous-thème : mocks
- Type : recette
- Niveau : 1
- Profils : data
- Prérequis : dates-naif-ou-aware
- Voir aussi : tests-horloge-instants-limites
- Source : data-platform · S1-07
- Définition : Les tests passent un instant fixe et aware (`LUNDI_MATIN = datetime(2026, 10, 26, 8, tzinfo=PARIS)`), jamais l'horloge réelle.
- Contexte : Un test qui lit `datetime.now()` donne un résultat différent chaque jour et casse au changement d'heure ou à minuit. Avec `now` injecté, chaque cas fixe son instant et son résultat attendu : `resolve_day({}, now=LUNDI_MATIN) == date(2026, 10, 25)`. Une constante de module nommée (`LUNDI_MATIN`) dit ce que l'instant a de particulier.
- Usage : ✅ toute fonction qui dépend de l'heure, testée par paramètre `now` · ❌ un test qui calcule son attendu avec `datetime.now()` : il réécrit le code testé.

```python
# Exemple 1 : un lundi figé
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
LUNDI_MATIN = datetime(2026, 10, 26, 8,
                       tzinfo=P)
veille = LUNDI_MATIN.date() - timedelta(1)
veille   # → date(2026, 10, 25)  (dimanche)
```

- Quiz : On écrit `LUNDI_MATIN = datetime(2026, 10, 26, 8)` (sans `tzinfo`) : que fait `resolve_day({}, now=LUNDI_MATIN)` ?
- [ ] Renvoie le 25, comme avec `tzinfo`
- [x] `ValueError`
- [ ] Renvoie le 25 sur Mac, le 26 sur Lambda
- [ ] `TypeError`
- Réponse : `ValueError` : `resolve_day` refuse un `now` naïf, justement pour que le résultat ne dépende pas de la machine.

## 9. moto : mock_aws, AWS en mémoire
- Id : tests-moto-mock-aws
- Sous-thème : mocks
- Type : concept
- Niveau : 1
- Profils : débutant, data, ops
- Source : data-platform · S1-07
- Définition : `mock_aws()` intercepte les appels boto3 et les sert depuis une fausse AWS en mémoire, le temps d'un `with` ou d'une fonction décorée.
- Contexte : moto se branche dans botocore : la requête n'atteint jamais le réseau, un backend Python joue S3, SQS, DynamoDB… avec leurs vraies erreurs (`NoSuchKey`, `NoSuchBucket`). L'état part vide à chaque démarrage : le bucket se crée dans le test. Depuis moto 5, un seul `mock_aws` remplace `mock_s3`, `mock_sqs` et les autres. Équivalent TS : `aws-sdk-client-mock`, en plus complet.
- Usage : ✅ tester le code qui écrit ou relit S3, sans compte ni coût, en local et en CI · ❌ prouver les droits IAM du rôle, l'ordre des appels ou les latences : moto ne les montre pas.

```python
# Exemple 1 : écrire et relire sans AWS
import boto3
from moto import mock_aws
with mock_aws():
    s3 = boto3.client("s3", "us-east-1")
    s3.create_bucket(Bucket="dp-raw")
    s3.put_object(Bucket="dp-raw", Key="k", Body=b"A1")
    r = s3.get_object(Bucket="dp-raw", Key="k")
    corps = r["Body"].read()
corps   # → b"A1"
```

```python
# Exemple 2 : moto 5, un seul mock
from moto import mock_s3  # ❌ ImportError
```

- Quiz : Un client boto3 créé **avant** `with mock_aws():`, puis utilisé dedans : où partent ses appels ?
- [ ] Vers le vrai AWS : il a été créé hors du mock
- [x] Vers moto : le mock intercepte tous les clients
- [ ] `NoCredentialsError`
- [ ] `ProfileNotFound`
- Réponse : vers moto (mesuré avec moto 5.2) : le mock se branche dans botocore, pas dans le client ; la doc conseille quand même de créer les clients dans le mock.

## 10. aws_credentials : de faux identifiants
- Id : tests-faux-identifiants-aws
- Sous-thème : fixtures
- Type : recette
- Niveau : 1
- Profils : data, ops
- Prérequis : tests-fixture-injection-par-nom
- Voir aussi : tests-aws-profile-absent
- Source : data-platform · S1-07
- Définition : Une fixture pose de faux identifiants (`AWS_ACCESS_KEY_ID=testing`) et retire `AWS_PROFILE`, pour qu'aucun appel du test ne puisse viser le vrai compte.
- Contexte : boto3 cherche ses identifiants dans l'ordre : variables d'environnement, puis profil de `~/.aws`, puis rôle. Les variables gagnent donc sur le profil. Un appel qui échapperait au mock (client créé à l'import, test sans fixture `s3`) partirait avec ces clés bidon et échouerait, au lieu d'écrire dans `dev`. `AWS_DEFAULT_REGION` évite l'erreur de région manquante.
- Usage : ✅ fixture dont dépend `s3` (`def s3(aws_credentials)`), dans `conftest.py`, avec `monkeypatch.setenv` · ❌ `os.environ[...] = ...` dans un test : rien n'est restauré après.

```python
# Exemple 1 : les variables gagnent
import os, boto3
os.environ.pop("AWS_PROFILE", None)
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
c = boto3.Session().get_credentials()
c.access_key    # → "testing"
c.method        # → "env"
del os.environ["AWS_ACCESS_KEY_ID"]
del os.environ["AWS_SECRET_ACCESS_KEY"]
```

```python
# Exemple 2 : la fixture du projet
import pytest

@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    for k in ("AWS_ACCESS_KEY_ID",
              "AWS_SECRET_ACCESS_KEY",
              "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(k, "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION",
                       "eu-west-3")
```

- Quiz : `AWS_PROFILE=dp-dev`, profil qui existe sur le poste, **et** les clés `testing` : lesquelles boto3 utilise-t-il ?
- [ ] Celles du profil `dp-dev`
- [x] `testing`, les variables d'environnement
- [ ] Aucune : `ProfileNotFound` pour conflit
- [ ] Celles du profil, si c'est un profil SSO
- Réponse : `testing` (mesuré) : les variables d'environnement passent avant le fichier `~/.aws/credentials`, même avec `AWS_PROFILE` défini.

## 11. fixture s3 : yield dans le with
- Id : tests-fixture-yield-dans-with
- Sous-thème : fixtures
- Type : piège
- Niveau : 1
- Profils : data, ops
- Prérequis : tests-moto-mock-aws, tests-fixture-injection-par-nom
- Voir aussi : tests-fixture-yield-teardown
- Source : data-platform · S1-07
- Définition : La fixture `s3` fait `yield` du client **dans** `with mock_aws()` : le mock reste actif tout le test, puis s'arrête et efface son état.
- Contexte : Avec `return` à la place, la fonction quitte le `with` avant que le test commence : le mock est déjà arrêté, ses objets effacés, et le client parle au vrai AWS (avec les faux identifiants : `InvalidAccessKeyId`). La chaîne `bucket(s3)` → `s3(aws_credentials)` fixe l'ordre : identifiants, puis mock, puis bucket. Après le test, pytest reprend après le `yield` et ferme le `with`.
- Usage : ✅ toute ressource à durée de vie (mock, connexion, serveur) : `yield` dans son `with` · ❌ `return` dans un `with` : la ressource est fermée avant d'être utilisée.

```python
# Exemple 1 : return ferme trop tôt
from contextlib import contextmanager
journal = []
@contextmanager
def faux_mock():
    journal.append("start")
    yield
    journal.append("stop")
def fixture_return():
    with faux_mock():
        return "client"
client = fixture_return()
journal  # → ["start", "stop"] : déjà arrêté
```

```python
# Exemple 2 : la fixture du projet
import boto3, pytest
from moto import mock_aws

@pytest.fixture
def s3(aws_credentials):
    with mock_aws():
        yield boto3.client("s3", "eu-west-3")

@pytest.fixture
def bucket(s3):
    s3.create_bucket(Bucket="data-platform-test-raw",
        CreateBucketConfiguration={
            "LocationConstraint": "eu-west-3"})
    return "data-platform-test-raw"
```

- Quiz : `def test_x(bucket):` ne demande pas `s3` : le mock est-il actif pendant le test ?
- [ ] Non : il faut demander `s3` aussi
- [x] Oui : `bucket` dépend de `s3`
- [ ] Erreur : fixture `s3` introuvable
- [ ] Seulement si `s3` est `autouse`
- Réponse : oui : pytest instancie les dépendances de `bucket`, donc `s3` et `aws_credentials` ; on ne demande `s3` que pour s'en servir dans le test.

## 12. SimpleNamespace : un faux objet en une ligne
- Id : tests-simplenamespace-faux-objet
- Sous-thème : mocks
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Source : data-platform · S1-07
- Définition : `types.SimpleNamespace(aws_request_id="req-123")` crée un objet dont les attributs sont ceux passés en arguments : un faux `context` Lambda sans classe.
- Contexte : Le code testé lit `context.aws_request_id` : un dict ne convient pas (`ctx["…"]` contre `ctx.…`), une classe est verbeuse, un `MagicMock` répond à tout, même aux fautes de frappe. `SimpleNamespace` n'a que ce qu'on lui donne : un attribut absent lève `AttributeError`, comme le vrai objet le ferait. Pour une méthode, passer une `lambda`.
- Usage : ✅ faux `context`, faux événement à attributs, réponse d'API simplifiée · ❌ faux qui doit vérifier ses appels : `MagicMock` ou un faux écrit à la main.

```python
# Exemple 1 : un faux context Lambda
from types import SimpleNamespace
ctx = SimpleNamespace(
    aws_request_id="req-123",
    get_remaining_time_in_millis=lambda: 5000)
ctx.aws_request_id  # → "req-123"
ctx.get_remaining_time_in_millis()  # → 5000
ctx.function_name  # ❌ AttributeError
```

- Quiz : Que vaut `SimpleNamespace(a=1) == SimpleNamespace(a=1)` ?
- [ ] `False` : deux objets distincts
- [x] `True`
- [ ] `TypeError` : pas de comparaison définie
- Réponse : `True` : `SimpleNamespace` compare ses attributs, contrairement à un objet ordinaire comparé par identité.

## 13. [record] = … : exactement un élément
- Id : tests-destructurer-un-element
- Sous-thème : assertions
- Type : recette
- Niveau : 1
- Profils : débutant, data
- Prérequis : collections-tuple-deballer
- Voir aussi : tests-caplog-filtrer-logger
- Source : data-platform · S1-07
- Définition : `[record] = [r for r in caplog.records if …]` déstructure une liste d'un seul élément : il en faut exactement un, sinon `ValueError`.
- Contexte : Une seule ligne fait deux vérifications : « il y a un log de ce module » et « il n'y en a pas deux ». Plus court que `assert len(lst) == 1` suivi de `lst[0]`, et le message dit ce qui ne va pas (`not enough values` / `too many values`). ≈ `const [r] = lst` en TS, qui lui ne vérifie rien et donne `undefined`.
- Usage : ✅ récupérer l'unique log, appel ou objet attendu dans un test · ❌ hors des tests, sur une donnée externe : un `if len(…) != 1` avec un message métier.

```python
# Exemple 1 : un seul élément attendu
logs = ["ingestion terminée"]
[record] = logs
record  # → "ingestion terminée"
[r] = []  # ❌ ValueError
```

- Quiz : Que fait `[record] = ["fin", "fin"]` ?
- [ ] `record` vaut `"fin"`, le second est ignoré
- [ ] `record` vaut `["fin", "fin"]`
- [x] `ValueError: too many values to unpack`
- Réponse : `ValueError` (mesuré : too many values to unpack (expected 1)) : la déstructuration exige autant de valeurs que de noms.

## 14. pytest : @mark.parametrize
- Id : tests-parametrize
- Sous-thème : marqueurs
- Type : concept
- Niveau : 2
- Profils : débutant, data
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

## 15. pytest : fixture avec yield
- Id : tests-fixture-yield-teardown
- Sous-thème : fixtures
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : tests-fixture-injection-par-nom, generateurs-yield-a-la-demande
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

## 16. conftest.py : des fixtures par dossier
- Id : tests-conftest-portee
- Sous-thème : fixtures
- Type : concept
- Niveau : 2
- Profils : data, ops
- Prérequis : tests-fixture-injection-par-nom
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

## 17. caplog : vérifier les logs
- Id : tests-caplog
- Sous-thème : fixtures
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : tests-fixture-injection-par-nom
- Voir aussi : tests-caplog-at-level-logger
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

## 18. --import-mode=importlib : des tests homonymes
- Id : tests-import-mode-importlib
- Sous-thème : config
- Type : choisir
- Niveau : 2
- Profils : ops
- Prérequis : tests-decouverte-nommage
- Source : data-platform · S1-03
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

## 19. addopts : des options invisibles
- Id : tests-addopts-invisibles
- Sous-thème : config
- Type : piège
- Niveau : 2
- Profils : ops
- Prérequis : tests-lancer-k-x-lf
- Source : data-platform · S1-03
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

## 20. pytest.approx : comparer des flottants
- Id : tests-approx-flottants
- Sous-thème : assertions
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : tests-assert-introspection
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

## 21. @pytest.mark : exclure par défaut
- Id : tests-marqueur-exclure-integration
- Sous-thème : marqueurs
- Type : recette
- Niveau : 2
- Profils : ops, data
- Prérequis : tests-lancer-k-x-lf
- Source : data-platform · S1-06
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

## 22. xfail : un échec attendu
- Id : tests-xfail-strict
- Sous-thème : marqueurs
- Type : concept
- Niveau : 2
- Profils : data, ops
- Prérequis : tests-marqueur-exclure-integration
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

## 23. respx : une réponse par appel
- Id : tests-respx-side-effect
- Sous-thème : mocks
- Type : recette
- Niveau : 2
- Profils : web, data
- Prérequis : http-respx-routes
- Source : data-platform · S1-06
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

## 24. monkeypatch : env et attributs
- Id : tests-monkeypatch
- Sous-thème : mocks
- Type : piège
- Niveau : 2
- Profils : data, web
- Prérequis : tests-fixture-injection-par-nom
- Voir aussi : tests-injection-dependance
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

## 25. injection : un faux plutôt qu'un patch
- Id : tests-injection-dependance
- Sous-thème : mocks
- Type : choisir
- Niveau : 2
- Profils : data, web
- Voir aussi : tests-monkeypatch, dates-now-none-injectable
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

## 26. raises : vérifier la cause
- Id : tests-raises-cause
- Sous-thème : assertions
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : tests-raises-exception, exceptions-raise-from-cause
- Source : data-platform · S1-07
- Définition : Après `with pytest.raises(…) as exc:`, `exc.value.__cause__` donne l'exception d'origine d'un `raise … from` : le chaînage se teste aussi.
- Contexte : `match=` ne lit que `str(exc.value)`, le message de l'erreur levée. Pour vérifier que la traduction garde bien sa cause (et qu'un refactoring n'a pas supprimé le `from exc`), on teste `exc.value.__cause__` : son type, ou son message. Utile quand l'appelant ou les logs comptent sur cette cause.
- Usage : ✅ fonction qui traduit une erreur technique en erreur métier · ❌ tester la cause partout : seulement là où elle fait partie du contrat.

```python
# Exemple 1 : la cause d'origine
import pytest
from datetime import date
def lire(raw):
    try:
        return date.fromisoformat(raw)
    except ValueError as e:
        raise ValueError("date invalide") from e
with pytest.raises(ValueError) as exc:
    lire("hier")
type(exc.value.__cause__).__name__
# → "ValueError"
```

- Quiz : Même `lire`, `pytest.raises(ValueError, match="Invalid isoformat")` : le test passe-t-il ?
- [ ] Oui : la cause contient ce texte
- [x] Non : `match` ne lit que le message levé
- [ ] Oui, `match` cherche dans toute la trace
- [ ] Non : `TypeError`
- Réponse : non : `match` cherche dans `str(exc.value)` (`date invalide`) ; la cause se vérifie via `exc.value.__cause__`.

## 27. match : casse et ancres
- Id : tests-match-casse-ancres
- Sous-thème : assertions
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : tests-raises-exception
- Voir aussi : tests-keyerror-guillemets
- Source : data-platform · S1-07
- Définition : `match=` applique `re.search` au message : sensible à la casse, sans ancre implicite ; `(?i)` ignore la casse, `^` et `$` ancrent.
- Contexte : `match="date invalide"` passe sur `date invalide 'hier', attendu YYYY-MM-DD` : une sous-chaîne suffit. Mais `"Date invalide"` échoue : la casse compte. Viser un fragment stable du message (`"date invalide"`, `"fuseau"`), pas la phrase entière, laisse le message évoluer sans casser les tests ; les valeurs reçues (`'hier'`) se vérifient à part si besoin.
- Usage : ✅ fragment court et stable du message · ❌ message complet recopié : chaque reformulation casse le test.

```python
# Exemple 1 : la casse compte
import pytest
def f():
    raise ValueError("date invalide 'hier'")
with pytest.raises(ValueError,
                   match="Date invalide"):
    f()   # ❌ AssertionError
```

```python
# Exemple 2 : (?i) ignore la casse
import pytest

def f():
    raise ValueError("date invalide 'hier'")

with pytest.raises(ValueError,
                   match="(?i)Date INVALIDE"):
    f()
"ok"   # → "ok"
```

- Quiz : Le message vaut `date invalide 'hier'`. `match="^invalide"` : le test passe-t-il ?
- [ ] Oui : `invalide` est dans le message
- [x] Non : `^` exige le début du message
- [ ] Oui : `match` ignore les ancres
- [ ] Non : `^` est interdit dans `match`
- Réponse : non : `re.search` respecte `^`, qui ancre au début ; le message commence par `date`.

## 28. ExceptionInfo : type, value, match()
- Id : tests-exceptioninfo
- Sous-thème : assertions
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : tests-raises-exception
- Source : data-platform · S1-07
- Définition : `with pytest.raises(E) as exc:` remplit `exc` à la sortie du bloc : `exc.type`, `exc.value` (l'exception), `exc.match(regex)`.
- Contexte : `exc.match()` vérifie le message après coup, utile pour plusieurs assertions sur la même erreur ; il lève `AssertionError` si la regex ne trouve rien. `exc.value` permet de lire les attributs d'une exception métier (`exc.value.raw == "hier"`). Les assertions se placent **après** le `with`, jamais dedans : la ligne qui lève termine le bloc.
- Usage : ✅ vérifier plusieurs propriétés d'une erreur (message, attribut, cause) · ❌ assertion dans le `with` après la ligne qui lève : jamais exécutée.

```python
# Exemple 1 : lire l'erreur après le bloc
import pytest
from datetime import date
with pytest.raises(ValueError) as exc:
    date.fromisoformat("2026-13-01")
exc.type is ValueError   # → True
exc.match("month")       # → True
str(exc.value)  # → "month must be in 1..12"
```

- Quiz : Que fait `exc.value` lu **dans** le bloc `with pytest.raises(ValueError) as exc:`, avant la ligne qui lève ?
- [ ] Renvoie `None`
- [x] `AssertionError`
- [ ] Renvoie l'exception à venir
- [ ] `NameError`
- Réponse : `AssertionError` (`.value can only be used after the context manager exits`) : `exc` n'est rempli qu'à la sortie du bloc.

## 29. parametrize : les ids générés
- Id : tests-parametrize-ids
- Sous-thème : marqueurs
- Type : concept
- Niveau : 2
- Profils : data
- Prérequis : tests-parametrize
- Source : data-platform · S1-07
- Définition : Chaque cas d'un `parametrize` reçoit un id (`test_x[hier]`) : la chaîne elle-même pour un texte ou un nombre, `nom` + index pour un objet.
- Contexte : `test_date_invalide[2026-13-01]` se lit directement dans le rapport et se relance avec `-k`. Pour une `date`, un tuple ou un dict, pytest génère `d0`, `d1`… : illisible. `ids=["mois-13", "vide"]` (ou `pytest.param(…, id=…)`) nomme les cas à la main. Les ids servent aussi à cibler un cas : `pytest "test_x.py::test_x[hier]"`.
- Usage : ✅ `ids=` dès que les valeurs sont des objets ou des chaînes peu parlantes · ❌ ids recopiés à la main pour des valeurs déjà lisibles.

```python
# Exemple 1 : des ids nommés
import pytest
@pytest.mark.parametrize(
    "raw", ["2026-13-01", "20/10/2026"],
    ids=["mois-13", "format-fr"])
def test_invalide(raw):
    assert raw
# test_invalide[mois-13]
# test_invalide[format-fr]
```

```python
# Exemple 2 : objets : nom + index
import pytest
from datetime import date

@pytest.mark.parametrize("d", [
    date(2026, 10, 24), None, 3])
def test_ids(d):
    assert d != 0
# test_ids[d0] test_ids[None] test_ids[3]
```

- Quiz : `parametrize("raw", ["hier", ""])` : quel id prend le cas de la chaîne vide ?
- [ ] `test_x[raw1]`
- [ ] `test_x['']`
- [x] `test_x[]`
- [ ] `test_x[1]`
- Réponse : `test_x[]` : une chaîne sert telle quelle d'id, même vide ; d'où `ids=` pour un cas lisible (`"vide"`).

## 30. pytest.param : un cas marqué
- Id : tests-pytest-param-marque
- Sous-thème : marqueurs
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : tests-parametrize, tests-xfail-strict
- Source : data-platform · S1-07
- Définition : `pytest.param(valeur, marks=pytest.mark.xfail, id="…")` attache un marqueur ou un id à un seul cas d'un `parametrize`.
- Contexte : Les autres cas restent normaux. Cas typique : documenter une limite connue sans casser la suite (`"2026-W43-1"` accepté par `fromisoformat` alors que le contrat dit `AAAA-MM-JJ`), ou sauter un cas sur une plateforme (`marks=pytest.mark.skipif(…)`). `pytest.param` prend autant de valeurs positionnelles que de noms de paramètres.
- Usage : ✅ un cas en échec connu, un cas propre à une plateforme · ❌ marquer tout le test : décorateur `@pytest.mark.xfail` au-dessus.

```python
# Exemple 1 : le contrat, une limite connue
import pytest
from datetime import date

def lire(raw):           # contrat : AAAA-MM-JJ
    return date.fromisoformat(raw)

@pytest.mark.parametrize("raw", [
    "2026-13-01", "20/10/2026",
    pytest.param("2026-W43-1", id="semaine",
        marks=pytest.mark.xfail(
            reason="fromisoformat l'accepte")),
])
def test_refuse(raw):
    with pytest.raises(ValueError):
        lire(raw)
# 2 passed, 1 xfailed
```

- Quiz : `parametrize("raw", [pytest.param("2026-W43-1", "2026-10-19")])` : que se passe-t-il ?
- [ ] Deux cas : un par valeur
- [ ] Le second argument devient l'id
- [x] Erreur à la collecte
- [ ] Un cas avec un tuple
- Réponse : erreur à la collecte : un nom de paramètre (`raw`) pour deux valeurs ; le nombre de valeurs doit égaler le nombre de noms.

## 31. horloge injectée : choisir les instants
- Id : tests-horloge-instants-limites
- Sous-thème : mocks
- Type : recette
- Niveau : 2
- Profils : data
- Prérequis : dates-now-none-injectable, tests-instant-fixe-aware
- Source : data-platform · S1-07
- Définition : Avec `now` injecté, on teste les instants où le code peut se tromper : minuit passé à Paris, un lundi, un changement d'heure.
- Contexte : Un test à 12:00 UTC ne verrait jamais le bug `.date()` sans conversion : à midi, UTC et Paris ont la même date. `resolve_day` est testé à 22:30 UTC le 24 (00:30 le 25 à Paris) : seul un instant entre 22:00 et minuit UTC (l'été) révèle l'écart. Chaque test nomme le piège qu'il vise : `test_sans_date_veille_a_paris_meme_si_utc_est_encore_la_veille`.
- Usage : ✅ cas limites nommés : minuit, lundi, DST, fin de mois, 1er janvier · ❌ un seul instant « au hasard » en milieu de journée.

```python
# Exemple 1 : l'instant qui révèle le bug
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
P = ZoneInfo("Europe/Paris")
def bug(now):    # .date() sans conversion
    return now.date() - timedelta(1)
def juste(now):
    return now.astimezone(P).date() - timedelta(1)
t = datetime(2026, 10, 24, 22, 30,
             tzinfo=timezone.utc)
bug(t) == juste(t)   # → False
```

- Quiz : Quel instant de test fait échouer `bug` (exemple 1) en hiver ?
- [ ] 08:00 à Paris
- [ ] 12:00 UTC
- [ ] 01:00 UTC
- [x] 23:30 UTC
- Réponse : 23:30 UTC : en hiver (UTC+1) il est 00:30 le lendemain à Paris ; les autres instants ont la même date en UTC et à Paris.

## 32. raises(Exception) : trop large
- Id : tests-raises-trop-large
- Sous-thème : assertions
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : tests-raises-exception
- Voir aussi : exceptions-except-exception-limites
- Source : data-platform · S1-07
- Définition : `pytest.raises(Exception)` passe pour n'importe quelle erreur, y compris une faute de frappe dans le test : un faux vert.
- Contexte : Un `NameError` (fonction mal nommée), un `TypeError` (mauvais argument), un `KeyError` dans un fixture : tous héritent d'`Exception` et satisfont le test. Le code n'a peut-être jamais été appelé. Viser le type exact, plus `match=` sur un fragment du message, garantit qu'on teste bien le refus voulu. Ruff le signale (règle `PT011`, `raises` trop large sans `match`).
- Usage : ✅ type précis + `match` · ❌ `raises(Exception)` ou `raises(BaseException)` dans un test métier.

```python
# Exemple 1 : faute de frappe, test vert
import pytest
with pytest.raises(Exception):
    resolve_dya({})   # NameError
"vert"   # → "vert"  (faux positif)
```

- Quiz : Même faute de frappe, mais `pytest.raises(ValueError)` : résultat ?
- [ ] Vert : une erreur a été levée
- [x] Rouge : `NameError` remonte
- [ ] Rouge : `DID NOT RAISE`
- [ ] Ignoré
- Réponse : rouge sur `NameError` : seul `ValueError` est attendu ; la faute de frappe devient visible.

## 33. AWS_PROFILE : un profil absent plante
- Id : tests-aws-profile-absent
- Sous-thème : fixtures
- Type : piège
- Niveau : 2
- Profils : ops, data
- Source : data-platform · S1-07
- Définition : Un `AWS_PROFILE` qui nomme un profil inconnu de la machine fait lever `ProfileNotFound` à la création du client, même sous `mock_aws`.
- Contexte : moto remplace les clés (`FOOBARKEY`) mais laisse `AWS_PROFILE` : boto3 charge ce profil dès `boto3.client(...)` et plante s'il n'existe pas. Sur ton poste, `AWS_PROFILE=dp-dev` exporté dans le shell passe ; en CI ou chez un collègue, les tests cassent avant le premier `assert`. Le retirer rend les tests indépendants de la machine.
- Usage : ✅ `monkeypatch.delenv("AWS_PROFILE", raising=False)` dans la fixture de faux identifiants · ❌ compter sur le profil du poste pour faire tourner les tests.

```python
# Exemple 1 : moto ne sauve pas le profil
import os, boto3
from moto import mock_aws
os.environ["AWS_PROFILE"] = "ci-absent"
m = mock_aws(); m.start()
boto3.client("s3", "eu-west-3")  # ❌ ProfileNotFound
m.stop()
del os.environ["AWS_PROFILE"]
```

- Quiz : `monkeypatch.delenv("AWS_PROFILE")`, sans `raising=False`, sur une machine où la variable n'existe pas : que se passe-t-il ?
- [ ] Rien, la variable est déjà absente
- [x] `KeyError` : le test échoue
- [ ] Un avertissement pytest
- [ ] `ProfileNotFound`
- Réponse : `KeyError` (mesuré) : par défaut `delenv` exige que la variable existe ; `raising=False` rend l'appel sûr partout, CI comprise.

## 34. moto ne prouve pas l'ordre : un faux qui enregistre
- Id : tests-faux-qui-enregistre-ordre
- Sous-thème : mocks
- Type : choisir
- Niveau : 2
- Profils : data, ops
- Prérequis : tests-moto-mock-aws, tests-injection-dependance
- Source : data-platform · S1-07
- Définition : Un faux client qui note chaque appel (`calls.append`) prouve l'ordre des écritures, que l'état final de moto ne montre pas.
- Contexte : Après le test, moto contient les deux objets, quel que soit leur ordre d'arrivée : l'état final est le même. Or le contrat de `publish` est « données puis manifest ». Comme `sleep` injecté dans le client BODACC, le client S3 est un paramètre : le test passe un objet maison avec les deux seules méthodes utilisées. Le duck typing suffit, sans héritage ni patch.
- Usage : ✅ ordre, nombre d'appels, arguments envoyés · ❌ contenu relu, types de contenu, vraies erreurs S3 (`NoSuchKey`) : moto.

```python
# Exemple 1 : l'ordre, enregistré
class RecordingS3:
    def __init__(self):
        self.calls = []
    def upload_file(self, f, bucket, key,
                    ExtraArgs=None):
        self.calls.append(("upload_file", key))
    def put_object(self, **kwargs):
        self.calls.append(("put_object", kwargs["Key"]))

def publish(s3):
    s3.upload_file("p.gz", "raw", "part-0001.jsonl.gz")
    s3.put_object(Bucket="raw", Key="_MANIFEST.json")

s3 = RecordingS3()
publish(s3)
[nom for nom, _ in s3.calls]
# → ["upload_file", "put_object"]
```

- Quiz : Un `publish` bogué écrit le manifest **puis** le fichier : quel test moto le détecte ?
- [ ] Le test qui relit le `count` du manifest
- [ ] Le test du rejeu (`KeyCount == 2`)
- [ ] Le test des types de contenu
- [x] Aucun : l'état final est identique
- Réponse : aucun : les deux objets existent avec le bon contenu, seul un faux qui enregistre les appels voit l'ordre inversé.

## 35. faux client : la signature de boto3
- Id : tests-faux-client-signature
- Sous-thème : mocks
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : tests-injection-dependance
- Source : data-platform · S1-07
- Définition : Le faux client reprend la signature exacte des méthodes boto3 utilisées : `upload_file(filename, bucket, key, ExtraArgs=None)` et `put_object(**kwargs)`.
- Contexte : Un faux plus permissif que le vrai fait passer le test et planter la production : `put_object("raw", "k")` en positionnel marche sur `def put_object(self, *args)`, alors que boto3 lève `TypeError`. `**kwargs` reproduit « nommés seulement », et lire `kwargs["Key"]` échoue si le code oublie `Key=`. Reprendre les noms (`ExtraArgs`) attrape aussi les fautes de frappe.
- Usage : ✅ faux minimal : une méthode par appel réel, mêmes noms de paramètres · ❌ `MagicMock()` comme client : il accepte n'importe quel nom et n'importe quels arguments.

```python
# Exemple 1 : nommés seulement, comme boto3
class FauxS3:
    def put_object(self, **kwargs):
        return kwargs["Key"]

s3 = FauxS3()
s3.put_object(Bucket="raw", Key="_MANIFEST.json")
# → "_MANIFEST.json"
s3.put_object("raw", "_MANIFEST.json")  # ❌ TypeError
```

- Quiz : `s3 = MagicMock()` ; le code appelle `s3.put_objet(...)` (faute de frappe) : que fait le test ?
- [ ] `AttributeError` : méthode inconnue
- [ ] `TypeError` à l'appel
- [x] Il passe sans erreur
- [ ] `ParamValidationError`
- Réponse : il passe (mesuré) : un `MagicMock` crée tout attribut demandé ; `create_autospec` ou un faux explicite fait échouer la faute.

## 36. faux client : simuler une panne
- Id : tests-faux-client-panne
- Sous-thème : mocks
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : tests-faux-client-signature
- Source : data-platform · S1-07
- Définition : Un drapeau du faux (`fail_upload=True`) lève une exception au milieu du flux, pour vérifier ce qui ne doit **pas** arriver ensuite.
- Contexte : moto réussit tout appel valide : il ne coupe jamais le réseau. Pour prouver « échec du fichier → pas de manifest », le faux lève `ConnectionError` dans `upload_file` ; le test attend l'exception (`pytest.raises`), puis vérifie que `put_object` n'a jamais été appelé. On teste l'absence d'un effet, pas seulement la remontée de l'erreur.
- Usage : ✅ ordre de publication, nettoyage après échec, absence d'écriture partielle · ❌ couper le réseau ou modifier moto pour simuler une panne : injecter le faux.

```python
# Exemple 1 : l'upload échoue, rien après
import pytest

class RecordingS3:
    def __init__(self, fail_upload=False):
        self.calls, self.fail = [], fail_upload
    def upload_file(self, f, b, key, ExtraArgs=None):
        self.calls.append("upload_file")
        if self.fail:
            raise ConnectionError("coupure réseau")
    def put_object(self, **kwargs):
        self.calls.append("put_object")
def publish(s3):
    s3.upload_file("p.gz", "raw", "part")
    s3.put_object(Bucket="raw", Key="_MANIFEST.json")

s3 = RecordingS3(fail_upload=True)
with pytest.raises(ConnectionError):
    publish(s3)
s3.calls   # → ["upload_file"]
```

- Quiz : Le test ne garde que `pytest.raises(ConnectionError)`, sans regarder `s3.calls` : quel bug laisse-t-il passer ?
- [ ] Une exception d'un autre type
- [x] Un manifest écrit avant le fichier qui échoue
- [ ] Un fichier envoyé deux fois
- [ ] Aucun : l'exception suffit
- Réponse : un manifest écrit avant le fichier : `publish` lève toujours `ConnectionError`, mais la partition est déjà déclarée complète ; seul `s3.calls` le montre.

## 37. caplog.at_level(logger=…) : le niveau du bon logger
- Id : tests-caplog-at-level-logger
- Sous-thème : fixtures
- Type : piège
- Niveau : 2
- Profils : data, ops
- Prérequis : tests-caplog, logging-warning-par-defaut
- Source : data-platform · S1-07
- Définition : `with caplog.at_level(logging.INFO, logger="ingest_bodacc.handler"):` abaisse le niveau de ce logger le temps du bloc, puis remet l'ancien.
- Contexte : Sans `logger=`, `caplog.set_level` règle le root. Or un module qui fait lui-même `logger.setLevel(WARNING)` ne regarde plus le root : son `info` reste filtré, `caplog.records` est vide. `logger=` vise le logger qui émet. La forme `with` limite le changement au bloc ; `set_level` dure jusqu'à la fin du test. Dans les deux cas pytest remet le niveau d'origine.
- Usage : ✅ `at_level(…, logger=__name__ du module testé)` autour de l'appel · ❌ `set_level(INFO)` sans `logger=` sur un module qui fixe son propre niveau.

```python
# Exemple 1 : le root ne suffit pas
import logging
log = logging.getLogger("ingest.h")
log.setLevel(logging.WARNING)  # module

def test_root(caplog):
    caplog.set_level(logging.INFO)
    log.info("x")
    assert caplog.records == []

def test_logger(caplog):
    with caplog.at_level(logging.INFO,
                         logger="ingest.h"):
        log.info("x")
    assert len(caplog.records) == 1
    assert log.level == logging.WARNING
# pytest -q : 2 passed
```

- Quiz : Après le `with caplog.at_level(…, logger="ingest.h")` de l'exemple, que vaut `log.level` ?
- [ ] `20` : `INFO` reste en place
- [x] `30` : remis à `WARNING`
- [ ] `0` : remis à `NOTSET`
- Réponse : `30` (mesuré) : `at_level` mémorise le niveau du logger visé et le restaure à la sortie du bloc.

## 38. caplog.records : filtrer par nom de logger
- Id : tests-caplog-filtrer-logger
- Sous-thème : fixtures
- Type : piège
- Niveau : 2
- Profils : data, web
- Prérequis : tests-caplog, logging-getlogger-name
- Source : data-platform · S1-07
- Définition : `caplog.records` contient les logs de **tous** les loggers ; filtrer par `r.name == "ingest_bodacc.handler"` isole ceux du module testé.
- Contexte : Dès que le niveau passe à `INFO`, les bibliothèques parlent aussi : httpx écrit `HTTP Request: GET … "HTTP/1.1 200 OK"` à chaque requête, même mockée par respx (mesuré). Un `caplog.records[0]` lit alors la ligne de httpx, pas la vôtre. Filtrer par nom rend le test indépendant de ce que font les dépendances.
- Usage : ✅ `[r for r in caplog.records if r.name == "…"]` avant tout `assert` · ❌ `caplog.records[0]` ou `len(caplog.records)` dans un test qui fait des appels httpx ou boto3.

```python
# Exemple 1 : httpx parle aussi
import logging, httpx, respx
def test_bruit(caplog):
    caplog.set_level(logging.INFO)
    with respx.mock:
        respx.get("https://b.test/x").mock(
            return_value=httpx.Response(200))
        httpx.get("https://b.test/x")
    noms = [r.name for r in caplog.records]
    assert noms == ["httpx"]
# pytest -q : 1 passed
```

- Quiz : Test de l'exemple, mais `logger="ingest_bodacc.handler"` passé à `set_level` : que vaut `noms` ?
- [ ] `["httpx"]`
- [x] `[]`
- [ ] `["ingest_bodacc.handler"]`
- Réponse : `[]` : seul le module testé passe à `INFO` ; httpx garde le `WARNING` hérité du root et son `info` est filtré.

## 39. respx.mock(…) : toutes les routes doivent servir
- Id : tests-respx-assert-all-called
- Sous-thème : mocks
- Type : concept
- Niveau : 2
- Profils : web, data
- Prérequis : http-respx-routes
- Source : data-platform · S1-07
- Définition : `respx.mock(...)` (appelé) crée un routeur qui vérifie à la sortie que chaque route a été appelée ; `assert_all_called=False` lève cette vérification.
- Contexte : Mesuré : `with respx.mock() as m:` avec une route jamais appelée échoue à la sortie (`AssertionError: RESPX: some routes were not called!`), utile pour prouver qu'une requête part. Une fixture partagée qui déclare la route pour tous les tests doit mettre `assert_all_called=False` : le test « date invalide, aucun appel réseau » ne l'appelle pas. Le routeur global `with respx.mock:` (sans parenthèses) ne vérifie pas.
- Usage : ✅ défaut `True` dans un test qui doit appeler l'API, `False` dans une fixture commune · ❌ `False` partout : une requête oubliée passe inaperçue.

```python
# Exemple 1 : la route non appelée échoue
import httpx, respx
try:
    with respx.mock() as m:
        m.get("https://b.test/x").mock(
            return_value=httpx.Response(200))
except AssertionError as e:
    msg = str(e)
msg  # → "RESPX: some routes were not called!"
```

```python
# Exemple 2 : la fixture commune
import httpx, respx
with respx.mock(assert_all_called=False) as m:
    m.get("https://b.test/x").mock(
        return_value=httpx.Response(200))
"sortie sans erreur"  # → "sortie sans erreur"
```

- Quiz : `with respx.mock as m:` (sans parenthèses), une route jamais appelée : le bloc échoue-t-il à la sortie ?
- [ ] Oui : `AssertionError`
- [x] Non : le routeur global ne vérifie pas
- [ ] Oui : `AllMockedAssertionError`
- Réponse : non (mesuré) : seul un routeur créé par l'appel `respx.mock(...)` vérifie par défaut ; le global sert sans contrôle.

## 40. respx : lire les paramètres envoyés
- Id : tests-respx-params-envoyes
- Sous-thème : mocks
- Type : recette
- Niveau : 2
- Profils : web, data
- Prérequis : http-respx-routes, http-params-query-string
- Source : data-platform · S1-07
- Définition : `route.calls.last.request.url.params` donne les paramètres de requête du dernier appel, pour vérifier ce que le client a vraiment demandé.
- Contexte : Une route sans `params=` répond à toute requête vers l'URL, quels que soient les paramètres : la réponse ne prouve rien sur `where` ou `order_by`. Lire la requête enregistrée le prouve : `params["where"] == "dateparution=date'2026-10-20'"`. `params` est un `QueryParams` : `["clé"]` lève `KeyError` si absent, `.get` renvoie `None`.
- Usage : ✅ vérifier date, filtre, tri, pagination envoyés · ❌ comparer l'URL complète en chaîne : l'ordre et l'encodage des paramètres la rendent fragile.

```python
# Exemple 1 : ce qui est parti
import httpx, respx
URL = "https://b.test/exports/jsonl"
with respx.mock:
    route = respx.get(URL).mock(
        return_value=httpx.Response(200))
    httpx.get(URL, params={"order_by": "id",
        "where": "dateparution=date'2026-10-20'"})
p = route.calls.last.request.url.params
p["order_by"]  # → "id"
p.get("limit")  # → None
```

- Quiz : Même route, mais le client oublie `order_by` : que fait `p["order_by"]` dans le test ?
- [ ] Renvoie `None`
- [ ] Renvoie `""`
- [x] `KeyError`
- Réponse : `KeyError` (mesuré) : comme un dict, `QueryParams[...]` lève si la clé manque, et le test échoue en le disant.

## 41. respx : prouver qu'aucun appel n'est parti
- Id : tests-respx-aucun-appel
- Sous-thème : mocks
- Type : recette
- Niveau : 2
- Profils : web, data
- Prérequis : http-respx-routes
- Source : data-platform · S1-07
- Définition : `assert route.call_count == 0` après un appel qui doit échouer prouve que la validation a eu lieu avant toute requête réseau.
- Contexte : Test « date invalide » du handler : `pytest.raises(ValueError)` montre qu'il échoue, `call_count == 0` montre qu'il échoue **avant** l'export, donc sans coût ni effet. C'est la preuve du fail fast. Sous `respx.mock`, une requête vers une URL sans route lève `AllMockedAssertionError` : aucun appel réel ne s'échappe, mais il faut une route pour compter.
- Usage : ✅ toute erreur de paramètre qui doit sortir avant le réseau ou S3 · ❌ seulement `pytest.raises` : une validation placée après l'appel passerait aussi.

```python
# Exemple 1 : la validation passe d'abord
import httpx, respx
from datetime import date
URL = "https://b.test/x"
def lire(raw):
    jour = date.fromisoformat(raw)
    return httpx.get(URL, params={"d": str(jour)})
with respx.mock:
    route = respx.get(URL).mock(
        return_value=httpx.Response(200))
    try:
        lire("20/10/2026")
    except ValueError:
        pass
route.call_count  # → 0
```

- Quiz : Sous `with respx.mock:`, `httpx.get("https://autre.test/")` sans route correspondante : que se passe-t-il ?
- [ ] La requête part sur le vrai réseau
- [ ] Réponse `404` simulée
- [x] `AllMockedAssertionError`
- [ ] `httpx.ConnectError`
- Réponse : `AllMockedAssertionError` (mesuré) : tout est intercepté ; une requête sans route est une erreur de test, pas un appel réel.

## 42. respx : changer la réponse en cours de test
- Id : tests-respx-changer-reponse
- Sous-thème : mocks
- Type : recette
- Niveau : 2
- Profils : web, data
- Prérequis : http-respx-routes
- Voir aussi : tests-respx-side-effect
- Source : data-platform · S1-07
- Définition : Rappeler `route.mock(return_value=…)` sur une route existante remplace sa réponse pour les appels suivants, sans perdre l'historique des appels.
- Contexte : Sert au test « coupure au rejeu » : la fixture renvoie l'export complet, une première invocation publie, puis `export_route.mock(…)` fait couper le flux, et la seconde invocation doit échouer sans toucher la partition. `call_count` cumule les deux phases. Plus lisible qu'un `side_effect=[…]` quand les deux phases sont séparées par des `assert`.
- Usage : ✅ scénario en deux temps (succès puis panne, ou l'inverse) autour d'assertions intermédiaires · ❌ suite d'appels rapides dans une même fonction : `side_effect=[r1, r2]`.

```python
# Exemple 1 : 200, puis 503
import httpx, respx
URL = "https://b.test/x"
with respx.mock:
    route = respx.get(URL).mock(
        return_value=httpx.Response(200))
    a = httpx.get(URL).status_code
    route.mock(return_value=httpx.Response(503))
    b = httpx.get(URL).status_code
(a, b)  # → (200, 503)
route.call_count  # → 2
```

- Quiz : Après le second `route.mock(…)`, `route.calls[0].response.status_code` vaut…
- [x] `200` : l'historique garde la réponse d'alors
- [ ] `503` : la nouvelle réponse remplace tout
- [ ] `IndexError` : l'historique est remis à zéro
- Réponse : `200` : chaque appel enregistre la réponse rendue à ce moment ; `mock` ne change que les appels à venir.

## 43. respx + moto : deux mocks qui cohabitent
- Id : tests-respx-et-moto
- Sous-thème : mocks
- Type : concept
- Niveau : 2
- Profils : data, ops
- Prérequis : http-respx-routes, tests-moto-mock-aws
- Source : data-platform · S1-07
- Définition : respx n'intercepte que httpx, moto que botocore : dans un même test, l'API BODACC est mockée par l'un et S3 par l'autre, sans interférence.
- Contexte : Les deux se branchent à des endroits différents : respx remplace le transport de httpx, moto s'insère dans botocore (qui n'utilise pas httpx). Sous `respx.mock`, un appel boto3 n'est donc pas une « requête sans route ». C'est ce qui permet le test de bout en bout du handler : vraie lecture du flux, vraie écriture gzip, faux S3, sans réseau.
- Usage : ✅ test bout en bout d'une Lambda qui lit une API (httpx) et écrit dans S3 (boto3) · ❌ espérer que respx bloque un appel `requests` ou boto3 : il ne les voit pas.

```python
# Exemple 1 : les deux mocks à la fois
import os, boto3, httpx, respx
from moto import mock_aws
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
with respx.mock, mock_aws():
    respx.get("https://b.test/x").mock(
        return_value=httpx.Response(200))
    s3 = boto3.client("s3", "eu-west-3")
    s3.create_bucket(Bucket="dp-raw",
        CreateBucketConfiguration={
            "LocationConstraint": "eu-west-3"})
    httpx.get("https://b.test/x").status_code
    noms = [b["Name"] for b in
            s3.list_buckets()["Buckets"]]
noms  # → ["dp-raw"]
```

- Quiz : Sous `with respx.mock:` seul (sans `mock_aws`), un `s3.list_buckets()` boto3 : que se passe-t-il ?
- [ ] `AllMockedAssertionError` : requête sans route
- [x] Il part vers AWS : respx ne voit pas boto3
- [ ] Il renvoie une liste vide simulée
- Réponse : il part vers AWS (ou échoue faute d'identifiants) : respx ne mocke que httpx ; d'où `mock_aws` et de faux identifiants dans la fixture.

## 44. fixture : cache_clear avant et après
- Id : tests-fixture-cache-clear
- Sous-thème : fixtures
- Type : piège
- Niveau : 2
- Profils : data
- Prérequis : tests-fixture-yield-teardown, decorateurs-cache-memoriser
- Source : data-platform · S1-07
- Définition : Une fixture qui appelle `fn.cache_clear()` avant `yield` et après donne à chaque test un état neuf pour une fonction en cache (`s3_client`).
- Contexte : Le cache vit dans le module, donc dure toute la session pytest. Sans `cache_clear`, le premier test qui appelle `s3_client()` fige un client (créé sous son `mock_aws`, avec son environnement) que tous les suivants réutilisent. Avant : ne pas hériter d'un test précédent ; après : ne rien laisser au suivant, même s'il ne passe pas par la fixture.
- Usage : ✅ toute fonction `@cache` qui dépend de l'environnement ou d'un mock · ❌ vider le cache dans le test lui-même : un oubli, et l'ordre des tests change le résultat.

```python
# Exemple 1 : un client neuf par test
import pytest
from functools import cache
@cache
def s3_client():
    return object()  # ≈ boto3.client
@pytest.fixture
def client_neuf():
    s3_client.cache_clear()
    yield s3_client()
    s3_client.cache_clear()
s3_client.cache_clear()
s3_client.cache_info().currsize  # → 0
```

- Quiz : Sans la ligne `cache_clear()` d'après `yield`, un test suivant qui **n'utilise pas** la fixture appelle `s3_client()` : que reçoit-il ?
- [ ] Un client neuf
- [x] Le client créé pendant le test précédent
- [ ] `None`
- Réponse : le client du test précédent : le cache garde l'objet créé dans la fixture, éventuellement sous un `mock_aws` déjà arrêté.

## 45. faux client Lambda : un Payload qui se lit
- Id : tests-faux-lambda-payload
- Sous-thème : mocks
- Type : recette
- Niveau : 2
- Profils : data, ops
- Prérequis : tests-faux-client-signature
- Voir aussi : AWS/lambda-boto3-invoke-function-error
- Source : data-platform · S1-08
- Définition : Le faux `invoke` rend la forme exacte de boto3 : `StatusCode`, `Payload` en `io.BytesIO`, et `FunctionError` seulement en cas d'échec.
- Contexte : Un faux qui rend `Payload` sous forme de dictionnaire fait passer un code qui ne fait jamais `.read()`, puis plante sur AWS. `BytesIO` reproduit le flux lu une fois ; une clé `FunctionError` présente seulement en échec reproduit le test `"FunctionError" in resp`. Le faux enregistre aussi les payloads envoyés, pour vérifier l'ordre des jours.
- Usage : ✅ tester un script qui invoque une Lambda, sans AWS ni moto · ❌ `Payload` en `dict` ou `str` : le code de production n'est pas exercé.

```python
# Exemple 1 : succès ou échec par date
import io, json

class FakeLambda:
    def __init__(self, failing=()):
        self.failing, self.sent = failing, []
    def invoke(self, FunctionName, Payload):
        ev = json.loads(Payload)
        self.sent.append(ev["date"])
        ok = ev["date"] not in self.failing
        r = {"StatusCode": 200, "Payload":
             io.BytesIO(b'{"count": 3}')}
        return r if ok else {**r,
            "FunctionError": "Unhandled"}

f = FakeLambda(failing={"2026-10-02"})
"FunctionError" in f.invoke("f", b'{"date": "2026-10-02"}')
# → True
f.sent           # → ['2026-10-02']
```

- Quiz : Le faux rend `"Payload": {"count": 3}` (un dict). Que fait `json.loads(resp["Payload"].read())` ?
- [ ] Rend `{"count": 3}`
- [x] `AttributeError` : un dict n'a pas `.read`
- [ ] `TypeError` dans `json.loads`
- Réponse : `AttributeError` : seul un objet fichier a `.read()` ; le faux doit rendre un flux, comme boto3.

## 46. couverture : lignes ou branches
- Id : tests-couverture-branches
- Sous-thème : couverture
- Type : comparaison
- Niveau : 3
- Profils : ops, expert
- Source : data-platform · S1-06
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

## 47. scope : partager une fixture coûteuse
- Id : tests-fixture-scope
- Sous-thème : fixtures
- Type : concept
- Niveau : 3
- Profils : data, expert
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

## 48. fixture paramétrée : params et request.param
- Id : tests-fixture-params
- Sous-thème : fixtures
- Type : concept
- Niveau : 3
- Profils : expert
- Prérequis : tests-fixture-injection-par-nom, tests-parametrize
- Voir aussi : tests-parametrize-indirect
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

## 49. autouse : une fixture pour tous
- Id : tests-fixture-autouse
- Sous-thème : fixtures
- Type : concept
- Niveau : 3
- Profils : ops, expert
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

## 50. parametrize sur une classe
- Id : tests-parametrize-classe
- Sous-thème : marqueurs
- Type : concept
- Niveau : 3
- Profils : expert
- Source : data-platform · S1-07
- Définition : `@pytest.mark.parametrize` posé sur une classe `Test…` s'applique à chacune de ses méthodes de test.
- Contexte : Toutes les méthodes reçoivent le paramètre, en argument après `self`. Pratique quand plusieurs vérifications partagent le même jeu d'entrées (plusieurs instants testés sur plusieurs propriétés). Chaque méthode est multipliée par le nombre de valeurs. Même effet au niveau du module avec `pytestmark = pytest.mark.parametrize(…)`, plus rare.
- Usage : ✅ même jeu d'entrées pour plusieurs assertions séparées · ❌ une seule méthode : décorer la fonction.

```python
# Exemple 1 : deux méthodes, deux instants
import pytest
@pytest.mark.parametrize("h", [0, 23])
class TestVeille:
    def test_entier(self, h):
        assert isinstance(h, int)
    def test_borne(self, h):
        assert 0 <= h < 24
# 4 passed : test_entier[0], [23]…
```

- Quiz : Une classe paramétrée de 4 valeurs contient 2 méthodes de test : combien de tests ?
- [ ] 4
- [ ] 6
- [x] 8
- [ ] 2
- Réponse : 8 : chaque méthode est lancée une fois par valeur, soit 2 × 4.

## 51. parametrize indirect : passer par une fixture
- Id : tests-parametrize-indirect
- Sous-thème : fixtures
- Type : concept
- Niveau : 3
- Profils : expert
- Prérequis : tests-parametrize, tests-fixture-injection-par-nom
- Source : data-platform · S1-07
- Définition : `parametrize("jour", [...], indirect=True)` envoie chaque valeur à la fixture `jour` (dans `request.param`) au lieu du test.
- Contexte : La fixture transforme la valeur brute (`"2026-10-24"`) en objet prêt (`date`, client, fichier) avant le test. Utile quand la préparation est commune et coûteuse, et que seuls quelques tests veulent la varier. `indirect=["jour"]` ne vise que certains noms. Sans `indirect`, une valeur de `parametrize` prend le pas sur la fixture de même nom.
- Usage : ✅ varier l'entrée d'une fixture pour quelques tests · ❌ tous les tests veulent les variantes : `@pytest.fixture(params=…)`.

```python
# Exemple 1 : la chaîne devient une date
import pytest
from datetime import date
@pytest.fixture
def jour(request):
    return date.fromisoformat(request.param)
@pytest.mark.parametrize(
    "jour", ["2026-10-24"], indirect=True)
def test_jour(jour):
    assert jour == date(2026, 10, 24)
# 1 passed
```

- Quiz : Même test **sans** `indirect=True` : que reçoit `test_jour(jour)` ?
- [ ] `date(2026, 10, 24)` : la fixture s'applique
- [x] La chaîne `"2026-10-24"`
- [ ] Une erreur : nom en double
- [ ] `request.param`
- Réponse : la chaîne : la valeur de `parametrize` remplace la fixture de même nom ; le test échoue alors sur `==`.

## 52. parametrize : un objet partagé entre cas
- Id : tests-parametrize-objet-partage
- Sous-thème : marqueurs
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : tests-parametrize
- Voir aussi : collections-alias-pas-de-copie
- Source : data-platform · S1-07
- Définition : Les valeurs de `parametrize` sont créées une fois, à la collecte : un objet mutable modifié par un cas est vu modifié par les suivants.
- Contexte : `pytest` ne copie pas les valeurs. Une même liste passée deux fois, ou un dict de module réutilisé, fuit d'un cas à l'autre : le second échoue seul, ou pire, passe grâce au premier. Comme les valeurs par défaut mutables d'une fonction. Parade : valeurs immuables (tuples, chaînes), ou fixture qui fabrique un objet neuf par test.
- Usage : ✅ valeurs immuables dans `parametrize` · ❌ liste ou dict modifié par le test : le fabriquer dans le test ou une fixture.

```python
# Exemple 1 : la même liste, deux cas
import pytest
LOT = []
@pytest.mark.parametrize("lot", [LOT, LOT])
def test_ajout(lot):
    lot.append("A1")
    assert lot == ["A1"]
# test_ajout[lot0] passed
# test_ajout[lot1] FAILED : ['A1', 'A1']
```

- Quiz : `parametrize("lot", [[]] * 2)` et chaque cas fait `lot.append(1)` puis `assert lot == [1]` : résultat ?
- [ ] 2 passed : deux listes vides
- [x] 1 passed, 1 failed
- [ ] 2 failed
- [ ] Erreur à la collecte
- Réponse : 1 passed, 1 failed : `[[]] * 2` répète la même liste ; le second cas la reçoit déjà remplie.

## 53. moto : les droits du rôle ne sont pas vérifiés
- Id : tests-moto-droits-iam
- Sous-thème : mocks
- Type : piège
- Niveau : 3
- Profils : ops, expert
- Prérequis : tests-moto-mock-aws
- Voir aussi : AWS/iam-simulate-principal-policy
- Source : data-platform · S1-07
- Définition : moto n'évalue pas les politiques IAM de l'appelant : un test vert ne prouve pas que le rôle de la Lambda a les droits.
- Contexte : Les identifiants bidon sont acceptés tels quels, l'appelant est le compte `123456789012`, et un utilisateur sans aucune politique écrit partout. Les droits se vérifient ailleurs : relecture du `terraform plan`, IAM Access Analyzer, test d'intégration sur `dev` avec le vrai rôle. moto a un mode d'autorisation expérimental (`INITIAL_NO_AUTH_ACTION_COUNT`), rarement utilisé.
- Usage : ✅ tester la logique : clés, contenu, erreurs S3 · ❌ conclure qu'un rôle à moindre privilège pourra écrire dans `raw` : test d'intégration.

```python
# Exemple 1 : un utilisateur sans politique
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
iam = boto3.client("iam", "us-east-1")
iam.create_user(UserName="ingest")
k = iam.create_access_key(
    UserName="ingest")["AccessKey"]
s3 = boto3.client("s3", "us-east-1",
    aws_access_key_id=k["AccessKeyId"],
    aws_secret_access_key=k["SecretAccessKey"])
s3.create_bucket(Bucket="dp-raw")
r = s3.put_object(Bucket="dp-raw", Key="k", Body=b"x")
r["ResponseMetadata"]["HTTPStatusCode"]  # → 200
m.stop()
```

- Quiz : Le test pose une politique de **bucket** `Deny s3:PutObject` pour `"*"`, puis écrit : que se passe-t-il sous moto ?
- [ ] L'écriture réussit : moto ignore toute politique
- [x] L'écriture est refusée (403)
- [ ] `NoSuchBucket`
- [ ] `MalformedPolicy` : `"*"` interdit
- Réponse : refusée en 403 (mesuré avec moto 5.2) : moto applique un `Deny` de politique de bucket, mais pas les politiques IAM de l'appelant.

## 54. moto : start et stop sans with
- Id : tests-moto-start-stop
- Sous-thème : mocks
- Type : recette
- Niveau : 3
- Profils : ops, expert
- Source : data-platform · S1-07
- Définition : `m = mock_aws(); m.start()` puis `m.stop()` active moto hors d'un `with`, par exemple dans `setUp` / `tearDown` ou pour toute une session.
- Contexte : `stop()` efface l'état : buckets et objets disparaissent, le démarrage suivant repart de zéro. Oublier `stop()` (exception avant, pas de `finally`) laisse le mock actif pour les tests suivants, qui partagent alors un état. Un mock de portée `session` partage volontairement l'état : chaque test doit utiliser ses propres clés ou nettoyer.
- Usage : ✅ `unittest.TestCase` (`setUp` / `tearDown`), mock global d'une session de tests · ❌ test pytest ordinaire : fixture à `yield` dans `with mock_aws()`, qui arrête toujours.

```python
# Exemple 1 : stop efface tout
import boto3
from moto import mock_aws
m = mock_aws(); m.start()
s3 = boto3.client("s3", "us-east-1")
s3.create_bucket(Bucket="dp-raw")
len(s3.list_buckets()["Buckets"])  # → 1
m.stop()
m.start()
len(s3.list_buckets()["Buckets"])  # → 0
m.stop()
```

- Quiz : `@mock_aws` sur une fonction qui crée `dp-raw` en `eu-west-3`, appelée deux fois : que fait le second appel ?
- [ ] `BucketAlreadyOwnedByYou`
- [ ] `BucketAlreadyExists`
- [x] Il réussit : l'état repart vide
- [ ] Il n'est pas mocké : le décorateur ne sert qu'une fois
- Réponse : il réussit (mesuré) : chaque appel de la fonction décorée démarre et arrête le mock, donc repart d'un compte vide.

## 55. Stubber : des réponses écrites d'avance
- Id : tests-stubber-botocore
- Sous-thème : mocks
- Type : comparaison
- Niveau : 3
- Profils : ops, expert
- Voir aussi : tests-faux-client-signature, tests-moto-mock-aws
- Source : data-platform · S1-07
- Définition : `botocore.stub.Stubber` remplace les réponses d'un client par une file de réponses déclarées, et vérifie les paramètres attendus de chaque appel.
- Contexte : Rien n'est simulé, contrairement à moto : chaque appel consomme la réponse suivante (`add_response`) ou une erreur (`add_client_error`), dans l'ordre déclaré. Des paramètres différents lèvent `StubAssertionError`, un appel en trop `UnStubbedResponseError`. Pas d'état : écrire puis relire demande deux réponses écrites à la main. Mal adapté à `upload_file`, qui enchaîne plusieurs appels.
- Usage : ✅ vérifier les paramètres exacts d'un appel, provoquer une erreur rare (`SlowDown`, `500`) · ❌ code qui écrit puis relit, ou qui passe par `upload_file` : moto.

```python
# Exemple 1 : une réponse, des paramètres
import boto3
from botocore.stub import Stubber
s3 = boto3.client("s3", "eu-west-3",
    aws_access_key_id="x", aws_secret_access_key="x")
st = Stubber(s3)
st.add_response("head_object", {"ContentLength": 6},
    {"Bucket": "dp-raw", "Key": "k"})
st.activate()
s3.head_object(Bucket="dp-raw",
               Key="k")["ContentLength"]  # → 6
```

```python
# Exemple 2 : provoquer une erreur rare
import boto3
from botocore.stub import Stubber
from botocore.exceptions import ClientError
s3 = boto3.client("s3", "eu-west-3",
    aws_access_key_id="x", aws_secret_access_key="x")
st = Stubber(s3)
st.add_client_error("put_object", "SlowDown",
                    http_status_code=503)
st.activate()
s3.put_object(Bucket="dp-raw", Key="k",
              Body=b"x")  # ❌ ClientError
```

- Quiz : Dans l'exemple 1, que fait un `head_object(Bucket="dp-raw", Key="autre")` à la place de l'appel prévu ?
- [ ] Il renvoie quand même `ContentLength: 6`
- [ ] `ClientError` au code `"404"`
- [x] `StubAssertionError` : paramètres inattendus
- [ ] `UnStubbedResponseError`
- Réponse : `StubAssertionError` (mesuré) : les paramètres attendus sont comparés à l'appel ; `UnStubbedResponseError` arrive quand la file de réponses est vide.

## 56. raises(KeyError, match=…) : les guillemets du message
- Id : tests-keyerror-guillemets
- Sous-thème : assertions
- Type : piège
- Niveau : 3
- Profils : expert
- Prérequis : tests-match-casse-ancres, exceptions-str-et-args
- Source : data-platform · S1-07
- Définition : `str(KeyError("RAW_BUCKET"))` vaut `"'RAW_BUCKET'"`, avec guillemets : `match="RAW_BUCKET"` passe, `match="^RAW_BUCKET$"` échoue.
- Contexte : `KeyError` est la seule exception courante dont `str()` renvoie le `repr` de la clé, pour distinguer `KeyError('')` d'un message vide. `match` applique `re.search` à `str(exc)` : une recherche sans ancre trouve le nom au milieu des guillemets, une ancre stricte non. Même piège en comparant `str(e) == "RAW_BUCKET"`.
- Usage : ✅ `match="RAW_BUCKET"` sans ancres, ou `exc.value.args[0] == "RAW_BUCKET"` · ❌ `match="^RAW_BUCKET$"` ou `str(e) ==` sur une `KeyError`.

```python
# Exemple 1 : la clé et son repr
e = KeyError("RAW_BUCKET")
str(e)  # → "'RAW_BUCKET'"
e.args[0]  # → "RAW_BUCKET"
str(ValueError("x"))  # → "x"
```

```python
# Exemple 2 : match = re.search
import re
re.search("RAW_BUCKET", "'RAW_BUCKET'") is None
# → False
re.search("^RAW_BUCKET$", "'RAW_BUCKET'") is None
# → True
```

- Quiz : `pytest.raises(KeyError, match="'RAW_BUCKET'")` (guillemets dans le motif) autour de `os.environ["RAW_BUCKET"]` absente : le test passe-t-il ?
- [x] Oui
- [ ] Non : `match` compare à la clé sans guillemets
- [ ] Non : `os.environ` lève une autre exception
- Réponse : oui : `str(exc)` contient les guillemets, le motif aussi ; `os.environ[...]` lève bien une `KeyError`.

## 57. SyncByteStream : couper le flux en plein milieu
- Id : tests-syncbytestream-coupure
- Sous-thème : mocks
- Type : recette
- Niveau : 3
- Profils : data, expert
- Prérequis : http-stream-iter-lines
- Voir aussi : tests-faux-client-panne
- Source : data-platform · S1-07
- Définition : Une sous-classe de `httpx.SyncByteStream` dont `__iter__` rend quelques octets puis lève `httpx.ReadError` simule une coupure réseau après le début de la réponse.
- Contexte : `side_effect=httpx.ReadError(…)` fait échouer la requête avant toute réponse ; une coupure réelle arrive après le `200`, en pleine lecture. Passée en `stream=` à `httpx.Response`, la classe fait lire une première annonce, puis lève : c'est le seul moyen de tester « rien n'est publié si le flux casse après la première ligne ». Un `httpx.get` non streamé lit tout et lève aussi.
- Usage : ✅ tester la reprise ou l'abandon d'une lecture en flux (`iter_lines`) · ❌ simuler une erreur de connexion avant la réponse : `side_effect=httpx.ConnectError(…)`.

```python
# Exemple 1 : une ligne, puis la coupure
import httpx, respx
class Coupe(httpx.SyncByteStream):
    def __iter__(self):
        yield b"A202602011\n"
        raise httpx.ReadError("coupé")
URL = "https://b.test/x"
lus = []
with respx.mock:
    respx.get(URL).mock(return_value=
        httpx.Response(200, stream=Coupe()))
    try:
        with httpx.stream("GET", URL) as r:
            for ligne in r.iter_lines():
                lus.append(ligne)
    except httpx.ReadError:
        pass
lus  # → ["A202602011"]
```

- Quiz : Même route, mais `httpx.get(URL)` (non streamé) à la place de `httpx.stream` : que se passe-t-il ?
- [ ] Réponse `200` avec le corps partiel
- [x] `httpx.ReadError`
- [ ] Réponse `200` avec un corps vide
- Réponse : `httpx.ReadError` (mesuré) : `get` lit tout le corps avant de rendre la réponse, et la coupure survient pendant cette lecture.
