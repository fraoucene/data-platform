from collections.abc import Iterator
from datetime import date

import httpx
import pytest
import respx

from bodacc_client import BodaccClient, BodaccError, BodaccRateLimitError
from bodacc_client.client import DEFAULT_BASE_URL, EXPORT_PATH

DAY = date(2026, 10, 20)
EXPORT_URL = f"{DEFAULT_BASE_URL}{EXPORT_PATH}"


@pytest.fixture
def delays() -> list[float]:
    """Remplace `time.sleep` : enregistre les attentes demandées au lieu de dormir."""
    return []


@pytest.fixture
def client(delays):
    with BodaccClient(sleep=delays.append) as c:
        yield c


def _mock_export(*responses):
    """Route l'export vers une suite de réponses ou d'exceptions, une par appel."""
    return respx.get(EXPORT_URL).mock(side_effect=list(responses))


@respx.mock
def test_429_puis_200_reessaie_une_fois(client, delays, export_text):
    route = _mock_export(httpx.Response(429), httpx.Response(200, text=export_text))

    rows = list(client.fetch_day(DAY))

    assert len(rows) == 25
    assert route.call_count == 2
    assert delays == [1.0]


@respx.mock
def test_retry_after_numerique_prime_sur_le_backoff(client, delays, export_text):
    _mock_export(httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, text=export_text))

    list(client.fetch_day(DAY))

    assert delays == [7.0]


@respx.mock
def test_retry_after_non_numerique_ignore(client, delays, export_text):
    _mock_export(
        httpx.Response(429, headers={"Retry-After": "Fri, 24 Oct 2026 00:00:00 GMT"}),
        httpx.Response(200, text=export_text),
    )

    list(client.fetch_day(DAY))

    assert delays == [1.0]


@respx.mock
def test_429_persistant_leve_rate_limit_apres_max_attempts(client, delays):
    route = _mock_export(*[httpx.Response(429, text="quota")] * 5)

    with pytest.raises(BodaccRateLimitError) as excinfo:
        list(client.fetch_day(DAY))

    assert route.call_count == 5
    assert delays == [1.0, 2.0, 4.0, 8.0]
    assert excinfo.value.status_code == 429
    assert "quota" in str(excinfo.value)


@respx.mock
def test_503_persistant_leve_bodacc_error_pas_rate_limit(client, delays):
    _mock_export(*[httpx.Response(503)] * 5)

    with pytest.raises(BodaccError) as excinfo:
        list(client.fetch_day(DAY))

    assert not isinstance(excinfo.value, BodaccRateLimitError)
    assert excinfo.value.status_code == 503
    assert len(delays) == 4


@respx.mock
def test_400_echoue_immediatement_sans_retry(client, delays):
    route = _mock_export(httpx.Response(400, json={"error_code": "IncompatibleTypesInComparisonFilter"}))

    with pytest.raises(BodaccError) as excinfo:
        list(client.fetch_day(DAY))

    assert route.call_count == 1
    assert delays == []
    assert excinfo.value.status_code == 400
    assert "IncompatibleTypesInComparisonFilter" in str(excinfo.value)


@respx.mock
def test_timeout_de_connexion_puis_200_reessaie(client, delays, export_text):
    _mock_export(httpx.ConnectTimeout("boom"), httpx.Response(200, text=export_text))

    rows = list(client.fetch_day(DAY))

    assert len(rows) == 25
    assert delays == [1.0]


@respx.mock
def test_erreur_reseau_persistante_leve_bodacc_error(client, delays):
    _mock_export(*[httpx.ConnectError("refusé")] * 5)

    with pytest.raises(BodaccError, match="5 tentatives"):
        list(client.fetch_day(DAY))

    assert len(delays) == 4


class _CutAfterFirstLine(httpx.SyncByteStream):
    """Corps qui envoie une annonce puis simule une coupure réseau."""

    def __iter__(self) -> Iterator[bytes]:
        yield b'{"id": "A1"}\n'
        raise httpx.ReadError("connexion coupée")


@respx.mock
def test_coupure_apres_le_debut_du_flux_n_est_pas_reessayee(client, delays):
    route = _mock_export(httpx.Response(200, stream=_CutAfterFirstLine()))
    received = []

    with pytest.raises(BodaccError, match="interrompu"):
        for row in client.fetch_day(DAY):
            received.append(row)

    assert received == [{"id": "A1"}]
    assert route.call_count == 1
    assert delays == []


def test_backoff_plafonne_a_max_delay():
    with BodaccClient(base_delay=1.0, max_delay=30.0) as client:
        assert [client._backoff(attempt, None) for attempt in range(7)] == [1, 2, 4, 8, 16, 30, 30]
