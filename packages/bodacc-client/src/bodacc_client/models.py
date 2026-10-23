"""Modèle Pydantic d'une annonce BODACC (dataset `annonces-commerciales`).

Voir `docs/source-bodacc.md` pour la forme réelle des données.
"""

import json
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

# Champs `text` côté API qui contiennent en réalité du JSON sérialisé.
NESTED_JSON_FIELDS = (
    "listepersonnes",
    "listeetablissements",
    "acte",
    "jugement",
    "radiationaurcs",
    "modificationsgenerales",
    "depot",
    "parutionavisprecedent",
)


def _clean_siren(value: str | None) -> str | None:
    """Retire les espaces ; renvoie le SIREN seulement s'il fait exactement 9 chiffres."""
    if not value:
        return None
    digits = value.replace(" ", "")
    return digits if len(digits) == 9 and digits.isdigit() else None


class Annonce(BaseModel):
    """Une annonce BODACC, avec les champs imbriqués décodés."""

    model_config = ConfigDict(extra="ignore")

    id: str
    dateparution: date
    typeavis: str
    familleavis: str
    familleavis_lib: str | None = None
    tribunal: str | None = None
    commercant: str | None = None
    registre: list[str] = []
    listepersonnes: dict[str, Any] | None = None
    listeetablissements: dict[str, Any] | None = None
    acte: dict[str, Any] | None = None
    jugement: dict[str, Any] | None = None
    radiationaurcs: dict[str, Any] | None = None
    modificationsgenerales: dict[str, Any] | None = None
    depot: dict[str, Any] | None = None
    parutionavisprecedent: dict[str, Any] | None = None
    url_complete: str | None = None

    @field_validator(*NESTED_JSON_FIELDS, mode="before")
    @classmethod
    def _decode_nested_json(cls, value: Any) -> Any:
        """Second `json.loads` : l'API renvoie ces champs sous forme de chaîne."""
        if isinstance(value, str):
            return json.loads(value) if value.strip() else None
        return value

    @field_validator("registre", mode="before")
    @classmethod
    def _registre_none_as_empty(cls, value: Any) -> Any:
        return [] if value is None else value

    @property
    def personnes(self) -> list[dict[str, Any]]:
        """`listepersonnes.personne` toujours sous forme de liste (l'API renvoie un objet ou une liste)."""
        personne = (self.listepersonnes or {}).get("personne")
        if personne is None:
            return []
        return personne if isinstance(personne, list) else [personne]

    @computed_field
    @property
    def sirens(self) -> list[str]:
        """SIREN des entreprises visées par l'annonce, sans doublon, dans l'ordre de `listepersonnes`.

        Source : pour chaque personne, le RCS (`numeroImmatriculation`) ou, pour un artisan,
        le Répertoire des Métiers (`inscriptionRM`). Une procédure peut viser plusieurs sociétés
        d'un même groupe (2 annonces le 2026-10-20). Liste vide pour un non-inscrit.

        `registre` n'est volontairement pas utilisé : pour une vente ou une immatriculation,
        il contient aussi l'ancien propriétaire ou exploitant du fonds (272 annonces le 2026-10-20),
        et parfois seulement lui quand l'acquéreur n'est pas inscrit (10 annonces).
        """
        found: list[str] = []
        for personne in self.personnes:
            rcs = (personne.get("numeroImmatriculation") or {}).get("numeroIdentification")
            rm = (personne.get("inscriptionRM") or {}).get("numeroIdentificationRM")
            if (siren := _clean_siren(rcs) or _clean_siren(rm)) and siren not in found:
                found.append(siren)
        return found

    @computed_field
    @property
    def siren(self) -> str | None:
        """Premier SIREN de `sirens`, ou `None`. Pour un traitement par entreprise, utiliser `sirens`."""
        return self.sirens[0] if self.sirens else None
