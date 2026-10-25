"""Rejoue l'ingestion d'une plage de jours : une invocation synchrone de la Lambda par jour, puis un bilan.

    uv run infra/scripts/replay.py --from 2026-10-01 --to 2026-10-19 \\
        --function data-platform-dev-ingest-bodacc --profile data-platform

En pratique, passer par `make replay FROM=… TO=…` (nom de la fonction lu dans les outputs Terraform).

Synchrone et séquentiel : chaque jour rend son `count` ou son erreur, et l'API BODACC ne reçoit jamais de rafale.
Un jour en échec n'arrête pas les suivants ; le code de sortie vaut 1 s'il y en a eu au moins un.
Rejouer un jour déjà ingéré est sans risque : la Lambda réécrit les mêmes clés avec les mêmes octets.
"""

import argparse
import json
import sys
from collections.abc import Callable, Iterator
from datetime import date, timedelta
from typing import Any

REGION = "eu-west-3"
# Au-delà du timeout de la Lambda (300 s, infra/lambdas.tf) : par défaut boto3 abandonne la lecture au bout
# de 60 s, alors que l'invocation continue côté AWS.
READ_TIMEOUT = 330


class ReplayError(Exception):
    """Le handler a levé une exception pour ce jour (`FunctionError` dans la réponse)."""


def days(start: date, end: date) -> Iterator[date]:
    """Chaque jour de `start` à `end`, bornes incluses."""
    if start > end:
        raise ValueError(f"début {start} après la fin {end}")
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def invoke_day(client: Any, function: str, day: date) -> dict[str, Any]:
    """Invoque la fonction pour un jour et renvoie la valeur de retour du handler.

    Une erreur du handler n'est pas une exception boto3 : l'appel répond `StatusCode` 200, avec
    `FunctionError` et, dans `Payload`, `errorType` / `errorMessage`.
    """
    response = client.invoke(FunctionName=function, Payload=json.dumps({"date": day.isoformat()}).encode())
    body = json.loads(response["Payload"].read())  # flux lisible une seule fois
    if "FunctionError" in response:
        raise ReplayError(f"{body.get('errorType')}: {body.get('errorMessage')}")
    return body


def replay(client: Any, function: str, start: date, end: date, out: Callable[[str], None] = print) -> int:
    """Rejoue chaque jour de la plage, affiche une ligne par jour puis le bilan ; renvoie le nombre d'échecs."""
    total = failed = 0
    for day in days(start, end):
        total += 1
        try:
            result = invoke_day(client, function, day)
        except ReplayError as exc:
            failed += 1
            out(f"{day}  ÉCHEC  {exc}")
            continue
        out(f"{day}  ok     {result['count']} annonces")
    out(f"{total - failed}/{total} jours ingérés")
    return failed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rejoue l'ingestion BODACC sur une plage de jours.")
    parser.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="premier jour, YYYY-MM-DD")
    parser.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="dernier jour inclus")
    parser.add_argument("--function", required=True, help="nom de la fonction Lambda")
    parser.add_argument("--profile", default=None, help="profil AWS (absent en CI : identifiants de l'environnement)")
    args = parser.parse_args(argv)
    if args.start > args.end:
        parser.error(f"--from {args.start} est après --to {args.end}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    import boto3  # importé ici : --help et les tests n'en ont pas besoin
    from botocore.config import Config

    # Pas de retry boto3 : après une coupure, il relancerait l'invocation et le jour s'exécuterait deux fois
    # sans que le bilan le dise. Un jour en échec se rejoue avec une nouvelle commande.
    config = Config(read_timeout=READ_TIMEOUT, retries={"total_max_attempts": 1})
    client = boto3.Session(profile_name=args.profile, region_name=REGION).client("lambda", config=config)
    return 1 if replay(client, args.function, args.start, args.end) else 0


if __name__ == "__main__":
    sys.exit(main())
