# packages/

Bibliothèques Python importables, membres du workspace `uv`, en src layout (`packages/<nom>/src/<module>/`).
Consommées par `lambdas/` et `jobs/` via `[tool.uv.sources] x = { workspace = true }` ; jamais déployées seules.
Exemple : `dp-common` (constantes, tags, helpers partagés), futur `dp-bodacc` (client API BODACC, S1-06).
