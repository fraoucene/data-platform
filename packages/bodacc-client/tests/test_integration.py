"""Tests sur la vraie API BODACC : lents, dépendants du réseau, exclus par défaut.

Lancer avec `make test-integration` ou `uv run pytest -m integration packages/bodacc-client`.
"""

from collections import Counter
from datetime import date

import pytest

from bodacc_client import BodaccClient

pytestmark = pytest.mark.integration

PAST_DAY = date(2026, 10, 20)


@pytest.fixture(scope="module")
def client():
    with BodaccClient() as c:
        yield c


def test_fetch_day_renvoie_exactement_total_count(client):
    expected = client.count_day(PAST_DAY)  # lu au moment du test : une date passée peut encore bouger

    received = sum(1 for _ in client.fetch_day(PAST_DAY))

    assert received == expected


def test_le_modele_tient_sur_une_journee_complete(client):
    """Règle ajoutée après l'erreur `registre` (étape 3) : valider l'extraction sur toute une journée."""
    sirens_par_annonce = Counter()
    for annonce in client.iter_annonces(PAST_DAY):  # une ValidationError ferait échouer le test
        sirens_par_annonce[len(annonce.sirens)] += 1

    total = sum(sirens_par_annonce.values())
    assert max(sirens_par_annonce) <= 2, sirens_par_annonce  # 2 = procédures de groupe ; plus = régression
    assert sirens_par_annonce[0] / total < 0.01, sirens_par_annonce  # non-inscrits : ~0,3 % le 2026-10-20
