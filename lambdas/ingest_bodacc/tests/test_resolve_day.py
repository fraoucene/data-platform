from datetime import date, datetime

import pytest

from ingest_bodacc.handler import PARIS, resolve_day

LUNDI_MATIN = datetime(2026, 10, 26, 8, 0, tzinfo=PARIS)


def test_date_fournie_rejouee_telle_quelle():
    assert resolve_day({"date": "2026-10-20"}, now=LUNDI_MATIN) == date(2026, 10, 20)


def test_sans_date_veille_a_paris_meme_si_utc_est_encore_la_veille():
    # 2026-10-24 22:30 UTC = 2026-10-25 00:30 à Paris (CEST, UTC+2) : en UTC, « J-1 » viserait le 23.
    now = datetime.fromisoformat("2026-10-24T22:30:00+00:00")

    assert resolve_day({}, now=now) == date(2026, 10, 24)


def test_lundi_vise_le_dimanche_sans_erreur():
    # Pas de parution le dimanche : journée vide (0 annonce), pas une erreur.
    assert resolve_day({}, now=LUNDI_MATIN) == date(2026, 10, 25)


def test_autres_cles_de_l_event_ignorees():
    event = {"date": "2026-10-20", "source": "step-functions"}

    assert resolve_day(event, now=LUNDI_MATIN) == date(2026, 10, 20)


@pytest.mark.parametrize("raw", ["2026-13-01", "20/10/2026", "hier", ""])
def test_date_invalide(raw):
    with pytest.raises(ValueError, match="date invalide"):
        resolve_day({"date": raw}, now=LUNDI_MATIN)


def test_date_qui_n_est_pas_une_chaine():
    with pytest.raises(ValueError, match="chaîne YYYY-MM-DD"):
        resolve_day({"date": 20261020}, now=LUNDI_MATIN)


@pytest.mark.parametrize("raw", ["2026-10-26", "2026-12-31"])
def test_jour_meme_et_futur_refuses(raw):
    with pytest.raises(ValueError, match="pas une journée terminée"):
        resolve_day({"date": raw}, now=LUNDI_MATIN)


def test_now_naif_refuse():
    with pytest.raises(ValueError, match="fuseau"):
        resolve_day({}, now=datetime(2026, 10, 26, 8, 0))
