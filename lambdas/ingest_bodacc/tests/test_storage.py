import gzip
import json
from datetime import UTC, date, datetime

import pytest

from ingest_bodacc.storage import build_manifest, partition_prefix, publish
from ingest_bodacc.writer import write_jsonl_gz

DAY = date(2026, 10, 20)
FETCHED_AT = datetime(2026, 10, 21, 5, 0, 12, tzinfo=UTC)
ROWS = [
    {"id": "A202602011", "familleavis": "collective"},
    {"id": "A202602012", "familleavis": "immatriculation"},
]


@pytest.fixture
def part(tmp_path):
    path = tmp_path / "part.jsonl.gz"
    return path, write_jsonl_gz(ROWS, path)


def manifest_for(part):
    _, stats = part
    return build_manifest(DAY, stats, FETCHED_AT)


def test_partition_prefix_au_format_hive():
    assert partition_prefix(DAY) == "bodacc/date=2026-10-20/"


def test_manifest_decrit_le_fichier(part):
    _, stats = part

    manifest = build_manifest(DAY, stats, FETCHED_AT)

    assert manifest["part"] == "bodacc/date=2026-10-20/part-0001.jsonl.gz"
    assert manifest["count"] == 2
    assert manifest["sha256"] == stats.sha256
    assert manifest["fetched_at"] == "2026-10-21T05:00:12+00:00"
    assert manifest["bodacc_client_version"] == "0.1.0"
    json.dumps(manifest)  # sérialisable tel quel


def test_publish_ecrit_le_fichier_et_le_manifest(s3, bucket, part):
    path, _ = part

    keys = publish(s3, bucket, DAY, path, manifest_for(part))

    assert keys == ["bodacc/date=2026-10-20/part-0001.jsonl.gz", "bodacc/date=2026-10-20/_MANIFEST.json"]
    body = s3.get_object(Bucket=bucket, Key=keys[0])["Body"].read()
    assert [json.loads(line) for line in gzip.decompress(body).splitlines()] == ROWS


def test_manifest_relu_donne_le_bon_nombre_d_annonces(s3, bucket, part):
    path, _ = part
    publish(s3, bucket, DAY, path, manifest_for(part))

    obj = s3.get_object(Bucket=bucket, Key="bodacc/date=2026-10-20/_MANIFEST.json")

    assert obj["ContentType"] == "application/json"
    assert json.loads(obj["Body"].read())["count"] == 2


def test_types_de_contenu(s3, bucket, part):
    path, _ = part
    publish(s3, bucket, DAY, path, manifest_for(part))

    head = s3.head_object(Bucket=bucket, Key="bodacc/date=2026-10-20/part-0001.jsonl.gz")

    assert head["ContentType"] == "application/gzip"
    assert "ContentEncoding" not in head


def test_rejeu_meme_resultat(s3, bucket, part, tmp_path):
    # Deuxième exécution : fichier réécrit sous un autre nom local, mêmes clés S3, mêmes octets.
    path, _ = part
    publish(s3, bucket, DAY, path, manifest_for(part))
    etag_1 = s3.head_object(Bucket=bucket, Key="bodacc/date=2026-10-20/part-0001.jsonl.gz")["ETag"]

    path_2 = tmp_path / "autre-nom.jsonl.gz"
    stats_2 = write_jsonl_gz(ROWS, path_2)
    publish(s3, bucket, DAY, path_2, build_manifest(DAY, stats_2, FETCHED_AT))

    listing = s3.list_objects_v2(Bucket=bucket, Prefix="bodacc/date=2026-10-20/")
    assert listing["KeyCount"] == 2
    assert s3.head_object(Bucket=bucket, Key="bodacc/date=2026-10-20/part-0001.jsonl.gz")["ETag"] == etag_1


class RecordingS3:
    """Faux client qui note l'ordre des appels ; `fail_upload` simule une coupure pendant l'envoi."""

    def __init__(self, fail_upload=False):
        self.calls, self.fail_upload = [], fail_upload

    def upload_file(self, filename, bucket, key, ExtraArgs=None):  # même signature que boto3
        self.calls.append(("upload_file", key))
        if self.fail_upload:
            raise ConnectionError("coupure réseau")

    def put_object(self, **kwargs):
        self.calls.append(("put_object", kwargs["Key"]))


def test_manifest_ecrit_en_dernier(part):
    path, _ = part
    s3 = RecordingS3()

    publish(s3, "raw", DAY, path, manifest_for(part))

    assert [name for name, _ in s3.calls] == ["upload_file", "put_object"]


def test_echec_du_fichier_pas_de_manifest(part):
    path, _ = part
    s3 = RecordingS3(fail_upload=True)

    with pytest.raises(ConnectionError):
        publish(s3, "raw", DAY, path, manifest_for(part))

    assert ("put_object", "bodacc/date=2026-10-20/_MANIFEST.json") not in s3.calls
