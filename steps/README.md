# steps/

Définitions JSON des étapes de pipeline (Step Functions / EMR steps), pas de code Python ici.
Consommées par Terraform (`infra/`) via `file()` / `templatefile()` pour câbler les jobs de `jobs/`.
Exemple : `steps/bodacc-daily.json` (enchaînement ingest → normalize → publish).
