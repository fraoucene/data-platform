"""Tests de replay.py, sans AWS : un faux client Lambda rejoue les réponses de `invoke`."""

import io
import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import replay  # noqa: E402


class FakeLambda:
    """Même forme de réponse que boto3 : `Payload` est un flux, `FunctionError` présent seulement en échec."""

    def __init__(self, failing: set[str] = frozenset()):
        self.failing = failing
        self.payloads: list[dict] = []

    def invoke(self, FunctionName: str, Payload: bytes) -> dict:  # noqa: N803 (noms de l'API boto3)
        event = json.loads(Payload)
        self.payloads.append(event)
        if event["date"] in self.failing:
            body = {"errorType": "ConnectError", "errorMessage": "coupé"}
            return {"StatusCode": 200, "FunctionError": "Unhandled", "Payload": io.BytesIO(json.dumps(body).encode())}
        body = {"date": event["date"], "count": 3}
        return {"StatusCode": 200, "Payload": io.BytesIO(json.dumps(body).encode())}


def test_days_bornes_incluses():
    jours = list(replay.days(date(2026, 10, 1), date(2026, 10, 19)))
    assert len(jours) == 19
    assert (jours[0], jours[-1]) == (date(2026, 10, 1), date(2026, 10, 19))


def test_days_un_seul_jour():
    assert list(replay.days(date(2026, 10, 20), date(2026, 10, 20))) == [date(2026, 10, 20)]


def test_days_refuse_une_plage_inversee():
    with pytest.raises(ValueError, match="après la fin"):
        list(replay.days(date(2026, 10, 2), date(2026, 10, 1)))


def test_replay_un_appel_par_jour_dans_l_ordre():
    client, lignes = FakeLambda(), []
    failed = replay.replay(client, "f", date(2026, 10, 1), date(2026, 10, 3), out=lignes.append)
    assert failed == 0
    assert [p["date"] for p in client.payloads] == ["2026-10-01", "2026-10-02", "2026-10-03"]
    assert lignes[-1] == "3/3 jours ingérés"


def test_replay_continue_apres_un_echec_et_le_compte():
    client, lignes = FakeLambda(failing={"2026-10-02"}), []
    failed = replay.replay(client, "f", date(2026, 10, 1), date(2026, 10, 3), out=lignes.append)
    assert failed == 1
    assert len(client.payloads) == 3  # le 3 est quand même rejoué
    assert "2026-10-02  ÉCHEC  ConnectError: coupé" in lignes
    assert lignes[-1] == "2/3 jours ingérés"


def test_parse_args_refuse_from_apres_to(capsys):
    with pytest.raises(SystemExit) as exc:
        replay.parse_args(["--from", "2026-10-19", "--to", "2026-10-01", "--function", "f"])
    assert exc.value.code == 2
    assert "est après" in capsys.readouterr().err


def test_parse_args_refuse_une_date_invalide():
    with pytest.raises(SystemExit):
        replay.parse_args(["--from", "2026-13-01", "--to", "2026-10-01", "--function", "f"])
