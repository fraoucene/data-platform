"""Tronque les adresses des personnes physiques dans une fixture JSONL BODACC.

Les annonces sont publiques, mais le repo l'est aussi : pour une personne physique
(`typePersonne == "pp"`), toute adresse imbriquée est réduite à `codePostal` + `ville`.
Les personnes morales sont laissées intactes. Le script est idempotent.

Usage : python3 sanitize_fixtures.py export_2026-10-20_collective_25.jsonl
"""

import json
import sys
from pathlib import Path

KEEP = ("codePostal", "ville")
NESTED_FIELDS = ("listepersonnes", "listeetablissements")


def _truncate_addresses(node: object) -> int:
    """Réduit en place chaque objet dont la clé contient « adresse ». Renvoie le nombre d'adresses modifiées."""
    changed = 0
    if isinstance(node, dict):
        for key, value in node.items():
            if "adresse" in key.lower() and isinstance(value, dict):
                short = {k: value[k] for k in KEEP if k in value}
                if short != value:
                    node[key] = short
                    changed += 1
            else:
                changed += _truncate_addresses(value)
    elif isinstance(node, list):
        for item in node:
            changed += _truncate_addresses(item)
    return changed


def _is_physical_person(annonce: dict) -> bool:
    personnes = json.loads(annonce.get("listepersonnes") or "{}").get("personne") or {}
    if isinstance(personnes, dict):
        personnes = [personnes]
    return any(p.get("typePersonne") == "pp" for p in personnes)


def sanitize(path: Path) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    total = 0
    out = []
    for line in lines:
        if not line.strip():
            continue
        annonce = json.loads(line)
        if _is_physical_person(annonce):
            for field in NESTED_FIELDS:
                raw = annonce.get(field)
                if not raw:
                    continue
                nested = json.loads(raw)
                changed = _truncate_addresses(nested)
                if changed:
                    annonce[field] = json.dumps(nested, ensure_ascii=False)
                    total += changed
            line = json.dumps(annonce, ensure_ascii=False)
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return total


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(f"{arg} : {sanitize(Path(arg))} adresse(s) tronquée(s)")
