"""Publication d'une partition dans le bucket raw : le fichier de données, puis le manifest."""

import json
from datetime import date, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from ingest_bodacc.writer import PartStats

SOURCE = "bodacc"
PART_NAME = "part-0001.jsonl.gz"
MANIFEST_NAME = "_MANIFEST.json"


def partition_prefix(day: date) -> str:
    """`bodacc/date=YYYY-MM-DD/` : partition Hive, lue telle quelle par Athena et Spark (S2)."""
    return f"{SOURCE}/date={day.isoformat()}/"


def build_manifest(day: date, stats: PartStats, fetched_at: datetime) -> dict[str, Any]:
    """Contenu de `_MANIFEST.json` : ce que le lecteur doit savoir pour faire confiance à la partition.

    Tous les champs sauf `fetched_at` sont identiques d'un rejeu à l'autre si la source n'a pas changé.
    """
    return {
        "source": SOURCE,
        "date": day.isoformat(),
        "part": partition_prefix(day) + PART_NAME,
        "format": "jsonl.gz",
        "count": stats.count,
        "sha256": stats.sha256,
        "raw_bytes": stats.raw_bytes,
        "gz_bytes": stats.gz_bytes,
        "fetched_at": fetched_at.isoformat(timespec="seconds"),
        "bodacc_client_version": version("bodacc-client"),
    }


def publish(s3: Any, bucket: str, day: date, part_path: Path, manifest: dict[str, Any]) -> list[str]:
    """Envoie le fichier puis le manifest, aux mêmes clés à chaque rejeu ; renvoie les clés écrites.

    L'ordre est le contrat : S3 n'a pas de transaction entre deux objets. Le manifest, écrit en dernier,
    marque la partition complète ; si l'envoi du fichier échoue, il n'est jamais écrit.
    `ContentType` gzip sans `ContentEncoding` : l'objet est une archive, pas du JSON servi compressé
    (avec `ContentEncoding: gzip`, un client HTTP le décompresserait à la volée).
    """
    prefix = partition_prefix(day)
    part_key, manifest_key = prefix + PART_NAME, prefix + MANIFEST_NAME
    s3.upload_file(str(part_path), bucket, part_key, ExtraArgs={"ContentType": "application/gzip"})
    s3.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"),
        ContentType="application/json",
    )
    return [part_key, manifest_key]
