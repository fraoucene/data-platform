from datetime import date

import pytest
from pydantic import ValidationError

from bodacc_client.models import Annonce


def test_toutes_les_annonces_enregistrees_se_valident(export_rows):
    annonces = [Annonce.model_validate(row) for row in export_rows]

    assert len(annonces) == 25
    assert all(a.familleavis == "collective" for a in annonces)
    assert all(a.dateparution == date(2026, 10, 20) for a in annonces)


def test_champs_imbriques_decodes_en_dict(export_rows):
    annonce = Annonce.model_validate(export_rows[0])

    assert isinstance(annonce.listepersonnes, dict)
    assert isinstance(annonce.jugement, dict)
    assert {"famille", "nature", "date"} <= annonce.jugement.keys()


def test_siren_sur_9_chiffres_pour_chaque_annonce_rattachable(export_rows):
    sirens = [Annonce.model_validate(row).siren for row in export_rows]

    rattaches = [s for s in sirens if s is not None]
    assert rattaches, "au moins une annonce doit avoir un SIREN"
    assert all(len(s) == 9 and s.isdigit() for s in rattaches)


def test_siren_artisan_lu_dans_le_repertoire_des_metiers(export_rows):
    row = next(r for r in export_rows if r["id"] == "A202602018278")

    annonce = Annonce.model_validate(row)

    assert annonce.registre == []
    assert annonce.siren == "922795315"


def test_siren_absent_pour_un_non_inscrit():
    annonce = Annonce.model_validate(
        {
            "id": "X1",
            "dateparution": "2026-10-20",
            "typeavis": "annonce",
            "familleavis": "collective",
            "registre": None,
            "listepersonnes": '{"personne": {"typePersonne": "pp", "nonInscrit": "N", "nom": "DUPONT"}}',
        }
    )

    assert annonce.siren is None


def test_personne_en_liste_est_geree():
    annonce = Annonce.model_validate(
        {
            "id": "X2",
            "dateparution": "2026-10-20",
            "typeavis": "annonce",
            "familleavis": "creation",
            "listepersonnes": (
                '{"personne": [{"typePersonne": "pm", "numeroImmatriculation": '
                '{"numeroIdentification": "123 456 789"}}, {"typePersonne": "pp"}]}'
            ),
        }
    )

    assert len(annonce.personnes) == 2
    assert annonce.siren == "123456789"


def test_procedure_visant_deux_societes_garde_les_deux_siren():
    # Reproduit la forme de A202602018045 (collective, 2026-10-20) : deux sociétés d'un même groupe.
    annonce = Annonce.model_validate(
        {
            "id": "A202602018045",
            "dateparution": "2026-10-20",
            "typeavis": "annonce",
            "familleavis": "collective",
            "registre": ["950820969", "950 820 969", "528633175", "528 633 175"],
            "listepersonnes": (
                '{"personne": ['
                '{"typePersonne": "pm", "denomination": "HORIZON DU LION", '
                '"numeroImmatriculation": {"numeroIdentification": "950 820 969"}}, '
                '{"typePersonne": "pm", "denomination": "GROUPE DELTA OUEST", '
                '"numeroImmatriculation": {"numeroIdentification": "528 633 175"}}]}'
            ),
        }
    )

    assert annonce.sirens == ["950820969", "528633175"]
    assert annonce.siren == "950820969"


def test_vente_ignore_le_siren_du_vendeur_present_dans_registre():
    # Forme de A20260201130 (vente) : registre contient l'acquéreur ET l'ancien propriétaire.
    annonce = Annonce.model_validate(
        {
            "id": "A20260201130",
            "dateparution": "2026-10-20",
            "typeavis": "annonce",
            "familleavis": "vente",
            "registre": ["109086215", "109 086 215", "483334793", "483 334 793"],
            "listepersonnes": (
                '{"personne": {"typePersonne": "pm", "numeroImmatriculation": {"numeroIdentification": "109 086 215"}}}'
            ),
        }
    )

    assert annonce.sirens == ["109086215"]


def test_acquereur_non_inscrit_n_herite_pas_du_siren_du_vendeur():
    # Forme de A20260201541 (vente) : seul le vendeur a un SIREN, dans registre.
    annonce = Annonce.model_validate(
        {
            "id": "A20260201541",
            "dateparution": "2026-10-20",
            "typeavis": "annonce",
            "familleavis": "vente",
            "registre": ["889305298", "889 305 298"],
            "listepersonnes": '{"personne": {"typePersonne": "pm", "nonInscrit": "N"}}',
        }
    )

    assert annonce.sirens == []
    assert annonce.siren is None


def test_sirens_vide_pour_un_non_inscrit():
    annonce = Annonce.model_validate(
        {
            "id": "X4",
            "dateparution": "2026-10-20",
            "typeavis": "annonce",
            "familleavis": "collective",
            "listepersonnes": '{"personne": {"typePersonne": "pp", "nonInscrit": "N"}}',
        }
    )

    assert annonce.sirens == []


def test_annonce_sans_listepersonnes_n_a_ni_personne_ni_siren():
    annonce = Annonce.model_validate(
        {"id": "X5", "dateparution": "2026-10-20", "typeavis": "annonce", "familleavis": "dpc"}
    )

    assert annonce.listepersonnes is None
    assert annonce.personnes == []
    assert annonce.sirens == []


def test_champ_imbrique_chaine_vide_devient_none():
    annonce = Annonce.model_validate(
        {"id": "X6", "dateparution": "2026-10-20", "typeavis": "annonce", "familleavis": "dpc", "jugement": "  "}
    )

    assert annonce.jugement is None


def test_champ_obligatoire_manquant_leve_une_erreur():
    with pytest.raises(ValidationError):
        Annonce.model_validate({"id": "X3", "typeavis": "annonce", "familleavis": "creation"})


def test_siren_present_dans_le_dump(export_rows):
    dumped = Annonce.model_validate(export_rows[0]).model_dump()

    assert "siren" in dumped
    assert "sirens" in dumped
