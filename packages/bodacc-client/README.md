# bodacc-client

Client Python de l'API BODACC (dataset `annonces-commerciales` sur OpenDataSoft) : toutes les annonces d'une journée, en streaming, avec retries et modèle Pydantic.
Forme réelle des données et choix de conception : [`docs/source-bodacc.md`](../../docs/source-bodacc.md).

## Usage

```python
from datetime import date

from bodacc_client import BodaccClient

with BodaccClient() as client:
    attendu = client.count_day(date(2026, 10, 20))  # 32373, total_count de l'API
    for annonce in client.iter_annonces(date(2026, 10, 20)):
        print(annonce.id, annonce.familleavis, annonce.sirens)
```

| Méthode | Renvoie | Usage |
| --- | --- | --- |
| `fetch_day(day)` | `Iterator[dict]` brut, une annonce par ligne de l'export | écrire la donnée telle quelle en zone `raw` |
| `iter_annonces(day)` | `Iterator[Annonce]` validées, champs imbriqués décodés | usages typés |
| `fetch_day_paged(day)` | `Iterator[dict]`, même contenu que `fetch_day` | plan B si l'export est instable |
| `count_day(day)` | `int`, `total_count` exact | vérifier qu'une lecture n'a rien perdu |

Les trois méthodes `fetch_*` et `iter_*` sont des générateurs : aucune requête ne part tant qu'on n'itère pas.

## Stratégie de lecture

- **Par défaut, l'export JSONL** : 1 requête, environ 5 s et 59 Mo pour une journée, lus ligne par ligne sans tout charger en mémoire.
- **Plan B, `fetch_day_paged`** : pages de 100 sur `/records`, keyset `numeroannonce > N` par bulletin A, B, C. Aucun plafond d'offset, chaque page se réessaie sans doublon, mais 325 requêtes et environ 2 min.

## Modèle `Annonce`

- Champs JSON-dans-du-texte décodés en `dict` : `listepersonnes`, `jugement`, `acte`, `radiationaurcs`, `parutionavisprecedent`…
- `personnes` : toujours une liste, que l'API ait envoyé un objet ou une liste.
- `sirens` : SIREN des entreprises visées, lus **uniquement** dans `listepersonnes`, au RCS ou au Répertoire des Métiers pour les artisans. Une annonce peut en avoir deux, pour une procédure de groupe. `registre` n'est pas utilisé, car il contient aussi l'ancien propriétaire d'un fonds vendu.
- `siren` : le premier de `sirens`, ou `None` pour une personne non inscrite. Pour un traitement par entreprise, utiliser `sirens`.

## Erreurs et retries

| Situation | Comportement |
| --- | --- |
| 429, 502, 503, 504, timeout, erreur réseau **avant** la première annonce | jusqu'à `max_attempts` essais (5 par défaut), attente 1, 2, 4, 8 s plafonnée à 30 s ; `Retry-After` en secondes prime |
| 429 après toutes les tentatives | `BodaccRateLimitError` |
| autre échec après toutes les tentatives | `BodaccError`, avec `status_code` et `url` |
| 400, 404 | `BodaccError` immédiate, sans retry |

**Non géré : la reprise d'un export coupé en plein flux.** Une coupure après la première annonce rendue lève `BodaccError` sans retry, car réessayer redonnerait les annonces déjà émises. L'appelant doit rejouer la journée entière, ce qui suppose une écriture idempotente : écraser le fichier du jour, pas l'enrichir.

## Configuration

`BodaccClient(base_url=…, timeout=60.0, user_agent="data-platform-bodacc-client/0.1", http=None, sleep=time.sleep, max_attempts=5, base_delay=1.0, max_delay=30.0)`

- `timeout` : lecture, en secondes. Le défaut de `httpx` (5 s) est trop court pour l'export ; la connexion reste plafonnée à 5 s.
- `http`, `sleep` : injectables pour tester sans réseau ni attente. Un `httpx.Client` injecté n'est pas fermé par le client.

## Tests

```bash
make test               # tests sur réponses enregistrées (respx), hors ligne
make cov                # couverture lignes + branches, seuil 80 %
make test-integration   # vraie API : journée du 2026-10-20 complète (~6 s)
```

Les fixtures de `tests/fixtures/` sont de vraies réponses de l'API. `sanitize_fixtures.py` y tronque les adresses des personnes physiques au code postal et à la ville ; le relancer après tout réenregistrement.
