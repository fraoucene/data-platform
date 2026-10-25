"""Point d'entrée de la Lambda : une journée de parution BODACC vers le bucket raw."""

import json
import logging
import os
import tempfile
import time
from datetime import UTC, date, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import boto3

from bodacc_client import BodaccClient
from ingest_bodacc.storage import PART_NAME, build_manifest, publish
from ingest_bodacc.writer import write_jsonl_gz

PARIS = ZoneInfo("Europe/Paris")

# Le runtime Lambda installe un handler sur le logger racine, au niveau WARNING : sans ce réglage,
# les `logger.info` n'apparaîtraient pas dans CloudWatch.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def resolve_day(event: dict[str, Any], now: datetime | None = None) -> date:
    """Jour de parution à ingérer.

    `{"date": "YYYY-MM-DD"}` rejoue ce jour ; sans date, la veille à Paris. La Lambda tourne en UTC :
    juste après minuit à Paris, la date UTC est encore celle de la veille, d'où le calcul en heure de Paris.
    Le jour même est refusé : sa parution peut être incomplète, et le manifest la déclarerait complète.

    `now` est injectable pour tester sans dépendre de l'horloge ; il doit porter un fuseau.
    """
    if now is not None and now.tzinfo is None:
        raise ValueError("now doit porter un fuseau (datetime aware), reçu un datetime naïf")
    today = (now or datetime.now(PARIS)).astimezone(PARIS).date()

    raw = event.get("date")
    if raw is None:
        return today - timedelta(days=1)
    if not isinstance(raw, str):
        raise ValueError(f"date attendue en chaîne YYYY-MM-DD, reçu {raw!r}")
    try:
        day = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"date invalide {raw!r}, attendu YYYY-MM-DD") from exc
    if day >= today:
        raise ValueError(f"{day} n'est pas une journée terminée à Paris (aujourd'hui : {today})")
    return day


@cache
def s3_client() -> Any:
    """Client S3 créé au premier appel puis réutilisé par les invocations suivantes du même conteneur.

    Pas au niveau du module : le client fige région et profil à sa création. À l'import, les fixtures n'ont pas
    encore posé leur environnement (région `us-east-1` par défaut, `ProfileNotFound` si `AWS_PROFILE` vise un
    profil absent, comme en CI).
    """
    return boto3.client("s3")


def ingest_day(
    day: date,
    *,
    s3: Any,
    bucket: str,
    client: BodaccClient,
    fetched_at: datetime,
    tmp_dir: str | None = None,
) -> dict[str, Any]:
    """Lit la journée, l'écrit dans un fichier temporaire, puis publie fichier et manifest.

    Rien n'est envoyé à S3 avant la fin de la lecture : une coupure en plein flux lève une exception
    et laisse la partition telle qu'elle était. Le dossier temporaire est supprimé même en cas d'erreur
    (`/tmp` est réutilisé d'une invocation à l'autre et limité à 512 Mo par défaut).
    """
    with tempfile.TemporaryDirectory(dir=tmp_dir) as work_dir:
        part_path = Path(work_dir) / PART_NAME
        stats = write_jsonl_gz(client.fetch_day(day), part_path)
        keys = publish(s3, bucket, day, part_path, build_manifest(day, stats, fetched_at))
    return {"date": day.isoformat(), "count": stats.count, "sha256": stats.sha256, "keys": keys}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Appelé par le runtime Lambda. Une exception fait échouer l'invocation : l'appelant rejoue la journée."""
    started = time.perf_counter()
    now = datetime.now(PARIS)  # une seule lecture de l'horloge par invocation
    day = resolve_day(event, now)
    bucket = os.environ["RAW_BUCKET"]

    with BodaccClient() as client:
        result = ingest_day(day, s3=s3_client(), bucket=bucket, client=client, fetched_at=now.astimezone(UTC))

    log = {
        "message": "ingestion terminée",
        **result,
        "bucket": bucket,
        "duration_s": round(time.perf_counter() - started, 2),
        "request_id": getattr(context, "aws_request_id", None),
    }
    logger.info(json.dumps(log, ensure_ascii=False))
    return result
