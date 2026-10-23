from datetime import date

import httpx
import pytest
import respx

from bodacc_client import BodaccClient
from bodacc_client.client import DEFAULT_BASE_URL, RECORDS_PATH

DAY = date(2026, 10, 20)
RECORDS_URL = f"{DEFAULT_BASE_URL}{RECORDS_PATH}"


def _page(bulletin: str, first: int, count: int) -> httpx.Response:
    """Page `/records` simulée : `count` annonces du bulletin, numéros consécutifs à partir de `first`."""
    results = [
        {"id": f"{bulletin}20260201{n}", "publicationavis": bulletin, "numeroannonce": n}
        for n in range(first, first + count)
    ]
    return httpx.Response(200, json={"total_count": count, "results": results})


@pytest.fixture
def delays() -> list[float]:
    return []


@respx.mock
def test_paged_parcourt_les_trois_bulletins_jusqu_a_la_page_incomplete(delays):
    route = respx.get(RECORDS_URL).mock(
        side_effect=[
            _page("A", 1, 100),
            _page("A", 101, 100),
            _page("A", 201, 37),  # page incomplète : fin du bulletin A
            _page("B", 1, 0),  # bulletin vide
            _page("C", 1, 12),
        ]
    )

    with BodaccClient(sleep=delays.append) as client:
        rows = list(client.fetch_day_paged(DAY))

    assert len(rows) == 249
    assert len({row["id"] for row in rows}) == 249  # aucun doublon
    assert route.call_count == 5


@respx.mock
def test_paged_avance_le_curseur_au_dernier_numero_recu():
    route = respx.get(RECORDS_URL).mock(
        side_effect=[_page("A", 1, 100), _page("A", 101, 5), _page("B", 1, 0), _page("C", 1, 0)]
    )

    with BodaccClient() as client:
        list(client.fetch_day_paged(DAY))

    wheres = [call.request.url.params["where"] for call in route.calls]
    assert wheres[0] == "dateparution=date'2026-10-20' and publicationavis='A' and numeroannonce > 0"
    assert wheres[1].endswith("publicationavis='A' and numeroannonce > 100")
    assert wheres[2].endswith("publicationavis='B' and numeroannonce > 0")
    assert all(call.request.url.params["order_by"] == "numeroannonce" for call in route.calls)
    assert all(call.request.url.params["limit"] == "100" for call in route.calls)


@respx.mock
def test_paged_une_page_en_429_est_reessayee_sans_doublon(delays):
    respx.get(RECORDS_URL).mock(
        side_effect=[
            _page("A", 1, 100),
            httpx.Response(429),  # échec au milieu du parcours…
            _page("A", 101, 3),  # …la même page est redemandée
            _page("B", 1, 0),
            _page("C", 1, 0),
        ]
    )

    with BodaccClient(sleep=delays.append) as client:
        rows = list(client.fetch_day_paged(DAY))

    assert len(rows) == 103
    assert len({row["id"] for row in rows}) == 103
    assert delays == [1.0]


@respx.mock
def test_paged_erreur_reseau_sur_une_page_est_reessayee(delays):
    respx.get(RECORDS_URL).mock(
        side_effect=[httpx.ConnectTimeout("boom"), _page("A", 1, 4), _page("B", 1, 0), _page("C", 1, 0)]
    )

    with BodaccClient(sleep=delays.append) as client:
        rows = list(client.fetch_day_paged(DAY))

    assert len(rows) == 4
    assert delays == [1.0]


@respx.mock
def test_paged_respecte_page_size():
    route = respx.get(RECORDS_URL).mock(
        side_effect=[_page("A", 1, 2), _page("A", 3, 1), _page("B", 1, 0), _page("C", 1, 0)]
    )

    with BodaccClient() as client:
        rows = list(client.fetch_day_paged(DAY, page_size=2))

    assert len(rows) == 3
    assert route.calls[0].request.url.params["limit"] == "2"


@respx.mock
def test_count_day_lit_total_count(records_payload):
    route = respx.get(RECORDS_URL).mock(return_value=httpx.Response(200, json=records_payload))

    with BodaccClient() as client:
        assert client.count_day(DAY) == 32373

    assert route.calls.last.request.url.params["limit"] == "1"
    assert route.calls.last.request.url.params["where"] == "dateparution=date'2026-10-20'"


@pytest.mark.parametrize("page_size", [0, 101])
def test_paged_refuse_un_page_size_hors_limites(page_size):
    with BodaccClient() as client, pytest.raises(ValueError):
        next(client.fetch_day_paged(DAY, page_size=page_size))
