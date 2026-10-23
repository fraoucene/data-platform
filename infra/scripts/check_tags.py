# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Audit des tags d'un plan Terraform.

Usage :
    terraform -chdir=infra show -json tfplan | uv run infra/scripts/check_tags.py
    terraform -chdir=infra show -json tfplan | uv run infra/scripts/check_tags.py --require environment --require owner

Lit le JSON du plan sur stdin, parcourt `planned_values.root_module` et ses
`child_modules` récursivement, et exige pour chaque ressource taggable
(clé `tags_all` présente dans `values`) :
- `tags_all["project"] == "data-platform"` ;
- la présence de chaque tag de REQUIRED_TAGS (par défaut `environment`),
  quelle que soit sa valeur.

Sortie : une ligne par violation sur stderr, un résumé sur stdout
(`N ressources taggables auditées, M ignorées (non taggables), V violations`),
code 1 si au moins une violation, 0 sinon.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

REQUIRED_TAG = "project"
REQUIRED_VALUE = "data-platform"
REQUIRED_TAGS: tuple[str, ...] = ("environment",)


@dataclass
class Audit:
    """Résultat d'un audit : violations (adresse → raison) et compteurs."""

    violations: dict[str, str] = field(default_factory=dict)
    taggable: int = 0
    untaggable: int = 0

    @property
    def summary(self) -> str:
        return (
            f"{self.taggable} ressources taggables auditées, "
            f"{self.untaggable} ignorées (non taggables), "
            f"{len(self.violations)} violation(s)"
        )


def iter_resources(module: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Génère toutes les ressources d'un module et de ses sous-modules.

    `module` est un objet de la forme `planned_values.root_module` :
    clés optionnelles `resources` (liste) et `child_modules` (liste de modules
    de même forme). Récursif : la profondeur n'est pas bornée.

    Décision à prendre (indice carte) : filtrer ou non `mode == "data"`.
    """
    yield from module.get("resources", [])
    for child in module.get("child_modules", []):
        yield from iter_resources(child)


def audit(plan: dict[str, Any], required_tags: tuple[str, ...] = REQUIRED_TAGS) -> Audit:
    """Audite un plan : compte les ressources et relève les violations.

    Règles :
    - ressource sans clé `tags_all` dans `values` : non taggable, comptée, ignorée ;
    - `tags_all` présent mais `null` : taggable sans tag, fautive ;
    - `tags_all[REQUIRED_TAG] != REQUIRED_VALUE` : fautive ;
    - un tag de `required_tags` absent : fautive.
    """
    root = plan["planned_values"]["root_module"]
    result = Audit()
    for resource in iter_resources(root):
        values = resource["values"]
        if "tags_all" not in values:
            result.untaggable += 1
            continue
        result.taggable += 1
        tags = values["tags_all"] or {}  # null → {}
        if tags.get(REQUIRED_TAG) != REQUIRED_VALUE:
            result.violations[resource["address"]] = f"tag {REQUIRED_TAG!r} != {REQUIRED_VALUE!r}"
            continue
        missing = [t for t in required_tags if t not in tags]
        if missing:
            result.violations[resource["address"]] = f"tag(s) manquant(s) : {', '.join(missing)}"
    return result


def find_violations(plan: dict[str, Any], required_tags: tuple[str, ...] = REQUIRED_TAGS) -> list[str]:
    """Retourne les adresses (`address`) des ressources fautives. Conservé pour compatibilité."""
    return list(audit(plan, required_tags).violations)


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée : stdin → audit → stderr (violations) + stdout (résumé) + code retour."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--require",
        action="append",
        metavar="TAG",
        help=f"tag dont la présence est exigée (répétable). Défaut : {', '.join(REQUIRED_TAGS)}",
    )
    args = parser.parse_args(argv)
    required = tuple(args.require) if args.require else REQUIRED_TAGS

    plan = json.load(sys.stdin)
    result = audit(plan, required)
    for address, reason in result.violations.items():
        print(f"{address}: {reason}", file=sys.stderr)
    print(result.summary)
    return 1 if result.violations else 0


if __name__ == "__main__":
    sys.exit(main())
