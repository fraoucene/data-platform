import gzip
import json
from collections.abc import Iterator
from datetime import UTC, date, datetime
from types import SimpleNamespace

import httpx
import pytest
import respx

from bodacc_client import BodaccClient, BodaccError
from bodacc_client.client import DEFAULT_BASE_URL, EXPORT_PATH
from ingest_bodacc import handler
from ingest_bodacc.handler import ingest_day, lambda_handler

EXPORT_URL = f"{DEFAULT_BASE_URL}{EXPORT_PATH}"
EXPORT_TEXT = '{"id": "A202602011", "familleavis": "collective"}\n{"id": "A202602012", "familleavis": "radiation"}\n'
EVENT = {"date": "2026-10-20"}
PART_KEY = "bodacc/date=2026-10-20/part-0001.jsonl.gz"
MANIFEST_KEY = "bodacc/date=2026-10-20/_MANIFEST.json"


@pytest.fixture
def lambda_env(monkeypatch, s3, bucket):
    """Ce que Terraform donnera à la fonction : le bucket en variable d'env, un client S3 neuf (celui de moto)."""
    monkeypatch.setenv("RAW_BUCKET", bucket)
    handler.s3_client.cache_clear()
    yield
    handler.s3_client.cache_clear()


@pytest.fixture
def export_route():
    with respx.mock(assert_all_called=False) as mock:
        yield mock.get(EXPORT_URL).mock(return_value=httpx.Response(200, text=EXPORT_TEXT))


def test_invocation_ecrit_fichier_et_manifest(lambda_env, export_route, s3, bucket):
    result = lambda_handler(EVENT, None)

    assert result["count"] == 2
    assert result["keys"] == [PART_KEY, MANIFEST_KEY]
    body = gzip.decompress(s3.get_object(Bucket=bucket, Key=PART_KEY)["Body"].read())
    assert [json.loads(line)["id"] for line in body.splitlines()] == ["A202602011", "A202602012"]
    manifest = json.loads(s3.get_object(Bucket=bucket, Key=MANIFEST_KEY)["Body"].read())
    assert manifest["count"] == 2
    assert manifest["sha256"] == result["sha256"]


def test_l_export_est_demande_pour_la_bonne_journee_et_trie(lambda_env, export_route):
    lambda_handler(EVENT, None)

    params = export_route.calls.last.request.url.params
    assert params["where"] == "dateparution=date'2026-10-20'"
    assert params["order_by"] == "id"


def test_deux_invocations_meme_resultat(lambda_env, export_route, s3, bucket):
    first = lambda_handler(EVENT, None)
    etag_1 = s3.head_object(Bucket=bucket, Key=PART_KEY)["ETag"]

    second = lambda_handler(EVENT, None)

    assert second["sha256"] == first["sha256"]
    assert s3.head_object(Bucket=bucket, Key=PART_KEY)["ETag"] == etag_1
    assert s3.list_objects_v2(Bucket=bucket, Prefix="bodacc/date=2026-10-20/")["KeyCount"] == 2


class _CutAfterFirstLine(httpx.SyncByteStream):
    """Corps qui envoie une annonce puis simule une coupure réseau."""

    def __iter__(self) -> Iterator[bytes]:
        yield b'{"id": "A202602011"}\n'
        raise httpx.ReadError("connexion coupée")


def test_coupure_en_plein_flux_rien_n_est_publie(lambda_env, s3, bucket):
    with respx.mock as mock:
        mock.get(EXPORT_URL).mock(return_value=httpx.Response(200, stream=_CutAfterFirstLine()))

        with pytest.raises(BodaccError, match="interrompu"):
            lambda_handler(EVENT, None)

    assert s3.list_objects_v2(Bucket=bucket, Prefix="bodacc/")["KeyCount"] == 0


def test_coupure_au_rejeu_laisse_la_partition_precedente_intacte(lambda_env, export_route, s3, bucket):
    lambda_handler(EVENT, None)
    etag_1 = s3.head_object(Bucket=bucket, Key=PART_KEY)["ETag"]
    export_route.mock(return_value=httpx.Response(200, stream=_CutAfterFirstLine()))

    with pytest.raises(BodaccError):
        lambda_handler(EVENT, None)

    assert s3.head_object(Bucket=bucket, Key=PART_KEY)["ETag"] == etag_1


def test_dossier_temporaire_supprime_meme_en_cas_d_erreur(s3, bucket, tmp_path):
    with respx.mock as mock:
        mock.get(EXPORT_URL).mock(return_value=httpx.Response(200, stream=_CutAfterFirstLine()))
        with BodaccClient() as client, pytest.raises(BodaccError):
            ingest_day(
                date(2026, 10, 20),
                s3=s3,
                bucket=bucket,
                client=client,
                fetched_at=datetime(2026, 10, 21, tzinfo=UTC),
                tmp_dir=str(tmp_path),
            )

    assert list(tmp_path.iterdir()) == []


def test_bucket_absent_erreur_explicite(monkeypatch, export_route):
    monkeypatch.delenv("RAW_BUCKET", raising=False)

    with pytest.raises(KeyError, match="RAW_BUCKET"):
        lambda_handler(EVENT, None)


def test_date_invalide_avant_tout_appel_reseau(lambda_env, export_route):
    with pytest.raises(ValueError, match="date invalide"):
        lambda_handler({"date": "20/10/2026"}, None)

    assert export_route.call_count == 0


def test_une_ligne_de_log_json_par_invocation(lambda_env, export_route, caplog):
    context = SimpleNamespace(aws_request_id="req-123")

    with caplog.at_level("INFO", logger="ingest_bodacc.handler"):
        lambda_handler(EVENT, context)

    [record] = [r for r in caplog.records if r.name == "ingest_bodacc.handler"]
    log = json.loads(record.getMessage())
    assert log["count"] == 2
    assert log["date"] == "2026-10-20"
    assert log["request_id"] == "req-123"
    assert log["duration_s"] >= 0
