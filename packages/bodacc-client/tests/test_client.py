from datetime import date
from itertools import islice

import httpx
import pytest
import respx

from bodacc_client import Annonce, BodaccClient
from bodacc_client.client import DEFAULT_BASE_URL, DEFAULT_USER_AGENT, EXPORT_PATH

DAY = date(2026, 10, 20)
EXPORT_URL = f"{DEFAULT_BASE_URL}{EXPORT_PATH}"


@pytest.fixture
def export_route(export_text):
    """Route respx qui sert l'export JSONL enregistré, active le temps du test."""
    with respx.mock(assert_all_called=False) as mock:
        yield mock.get(EXPORT_URL).mock(return_value=httpx.Response(200, text=export_text))


def test_day_params_utilise_le_litteral_date():
    assert BodaccClient._day_params(date(2026, 10, 20)) == {"where": "dateparution=date'2026-10-20'"}


@respx.mock
def test_user_agent_et_base_url_envoyes():
    route = respx.get(f"{DEFAULT_BASE_URL}/records").mock(return_value=httpx.Response(200, json={}))

    with BodaccClient() as client:
        client._http.get("/records")

    request = route.calls.last.request
    assert request.headers["user-agent"] == DEFAULT_USER_AGENT


def test_timeout_explicite_et_plus_long_que_le_defaut_httpx():
    with BodaccClient(timeout=60.0) as client:
        timeout = client._http.timeout

    assert timeout.read == 60.0
    assert timeout.connect == 5.0


def test_le_context_manager_ferme_le_client_qu_il_a_cree():
    with BodaccClient() as client:
        http = client._http

    assert http.is_closed


def test_un_client_http_injecte_n_est_pas_ferme():
    http = httpx.Client()

    with BodaccClient(http=http):
        pass

    assert not http.is_closed
    http.close()


@pytest.mark.parametrize("max_attempts", [0, -1])
def test_max_attempts_inferieur_a_1_refuse(max_attempts):
    # Sinon fetch_day renverrait une journée vide sans requête ni erreur.
    with pytest.raises(ValueError, match="max_attempts"):
        BodaccClient(max_attempts=max_attempts)


def test_fetch_day_renvoie_les_25_annonces_enregistrees(export_route):
    with BodaccClient() as client:
        rows = list(client.fetch_day(DAY))

    assert len(rows) == 25
    assert all(isinstance(row, dict) for row in rows)
    assert export_route.call_count == 1


def test_fetch_day_envoie_le_filtre_de_la_journee(export_route):
    with BodaccClient() as client:
        list(client.fetch_day(DAY))

    assert export_route.calls.last.request.url.params["where"] == "dateparution=date'2026-10-20'"


def test_fetch_day_lazy_aucune_requete_sans_iteration(export_route):
    with BodaccClient() as client:
        generator = client.fetch_day(DAY)

        assert export_route.call_count == 0
        next(generator)
        assert export_route.call_count == 1
        generator.close()


def test_fetch_day_islice_ne_consomme_que_3_annonces(export_route):
    with BodaccClient() as client:
        first_three = list(islice(client.fetch_day(DAY), 3))

    assert len(first_three) == 3


def test_fetch_day_ignore_les_lignes_vides():
    body = '{"id": "A1"}\n\n   \n{"id": "A2"}\n'
    with respx.mock:
        respx.get(EXPORT_URL).mock(return_value=httpx.Response(200, text=body))
        with BodaccClient() as client:
            ids = [row["id"] for row in client.fetch_day(DAY)]

    assert ids == ["A1", "A2"]


def test_iter_annonces_renvoie_des_annonces_validees(export_route):
    with BodaccClient() as client:
        annonces = list(client.iter_annonces(DAY))

    assert len(annonces) == 25
    assert all(isinstance(a, Annonce) for a in annonces)
    assert all(a.jugement is not None for a in annonces)
