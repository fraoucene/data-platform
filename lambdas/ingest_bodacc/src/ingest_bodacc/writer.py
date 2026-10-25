"""Écriture d'une partition : JSONL gzip reproductible octet pour octet, avec ses statistiques."""

import gzip
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 6 = défaut de la commande gzip. Mesuré sur une journée (55,6 Mo) :
# 4,44 Mo en 0,8 s, contre 4,30 Mo en 1,3 s au niveau 9.
COMPRESS_LEVEL = 6


@dataclass(frozen=True)
class PartStats:
    """Ce que le manifest dira du fichier écrit."""

    count: int
    sha256: str  # du JSONL non compressé : l'identité de la donnée, indépendante de la compression
    raw_bytes: int
    gz_bytes: int


def serialize(row: dict[str, Any]) -> bytes:
    """Une annonce = une ligne JSON compacte, clés triées, accents conservés."""
    return (json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def write_jsonl_gz(rows: Iterable[dict[str, Any]], path: Path) -> PartStats:
    """Écrit les annonces dans `path` au fil de l'eau, sans les garder en mémoire.

    Mêmes annonces, même ordre → mêmes octets, quel que soit le moment ou le nom du fichier :
    `mtime=0` et `filename=""` vident les deux champs variables de l'en-tête gzip.
    """
    digest = hashlib.sha256()
    count = raw_bytes = 0
    with (
        path.open("wb") as f,
        gzip.GzipFile(filename="", mode="wb", fileobj=f, compresslevel=COMPRESS_LEVEL, mtime=0) as gz,
    ):
        for row in rows:
            line = serialize(row)
            gz.write(line)
            digest.update(line)
            count += 1
            raw_bytes += len(line)
    return PartStats(count=count, sha256=digest.hexdigest(), raw_bytes=raw_bytes, gz_bytes=path.stat().st_size)
