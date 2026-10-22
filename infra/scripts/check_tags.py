# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Audit des tags d'un plan Terraform.

Usage :
    terraform -chdir=infra show -json tfplan | uv run infra/scripts/check_tags.py

Lit le JSON du plan sur stdin, parcourt `planned_values.root_module` et ses
`child_modules` récursivement, et exige pour chaque ressource taggable
(clé `tags_all` présente dans `values`) que `tags_all["project"] == "data-platform"`.

Sortie : une ligne par adresse fautive sur stderr, code 1 si au moins une,
0 sinon.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from typing import Any

REQUIRED_TAG = "project"
REQUIRED_VALUE = "data-platform"


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


def find_violations(plan: dict[str, Any]) -> list[str]:
    """Retourne les adresses (`address`) des ressources dont le tag est absent ou faux.

    Règles :
    - ressource sans clé `tags_all` dans `values` : non taggable, ignorée ;
    - `tags_all` présent mais `null` : taggable sans tag, fautive ;
    - `tags_all[REQUIRED_TAG] != REQUIRED_VALUE` : fautive.
    """
    root = plan["planned_values"]["root_module"]
    violations: list[str] = []
    for resource in iter_resources(root):
        values = resource["values"]
        if "tags_all" not in values:
            continue  # ressource non taggable
        tags = values["tags_all"] or {}  # null → {}
        if tags.get(REQUIRED_TAG) != REQUIRED_VALUE:
            violations.append(resource["address"])
    return violations


def main() -> int:
    """Point d'entrée : stdin → violations → stderr + code retour."""
    plan = json.load(sys.stdin)
    violations = find_violations(plan)
    for address in violations:
        print(f"{address}: tag {REQUIRED_TAG!r} != {REQUIRED_VALUE!r}", file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
