# AGENTS.md — règles pour les agents de code

Plateforme data serverless AWS (ingestion BODACC → S3, puis PySpark/Iceberg et agent). Monorepo Python `uv`,
infrastructure Terraform, un environnement = `infra/envs/<env>/`. Architecture et démarrage : `README.md`.
Langue du dépôt : français (code, commentaires, docs, messages de commit).

## Structure

- `packages/<nom>/src/<module>/` : libs partagées (`bodacc-client`, `dp-common`), tests dans `packages/<nom>/tests/`.
- `lambdas/<dossier>/` : une Lambda = un membre uv (`name` du `pyproject.toml` = identifiant partout : zip,
  clé de `local.lambdas`, nom `data-platform-<env>-<name>`), tests dans `lambdas/<dossier>/tests/`.
- `infra/` : root Terraform (`main.tf`, `lambdas.tf`, `schedules.tf`, `alerts.tf`…), `modules/` (un module par
  ressource récurrente), `envs/<env>/`, `scripts/` (Python + tests à côté), `bootstrap/` (root séparé, état local).
- `docs/` : architecture, `source-bodacc.md` (contrat de la source, mesures). `learning/` : cours et cartes.

## Vérifier avant de rendre la main

```bash
make sync     # uv sync --all-packages (jamais `uv sync` seul : les membres ne seraient pas installés)
make check    # ruff check + ruff format --check + pytest ; doit être vert
make plan     # si un .tf a changé : plan + audit des tags ; lire le diff, 0 violation
```

- Toute ressource ajoutée à `infra/` passe par `make plan` ; décrire ce que le plan ajoute, change, détruit.
- Un comportement AWS ou de la source BODACC s'affirme après mesure (commande lancée, sortie lue), pas de mémoire.
  Les règles d'extraction se valident sur une journée complète (~32 000 annonces), jamais sur la seule fixture.

## Conventions

- Python 3.12, ruff (120 colonnes, règles `E F I UP B`), type hints, `pytest` avec `--import-mode=importlib`.
- Tests sans réseau ni AWS : faux clients injectés (`respx` pour HTTP, `moto` pour S3, objets à la forme exacte
  des réponses boto3). Les tests réseau sont marqués `integration` (`make test-integration`).
- Terraform : nommage `data-platform-<env>-…` via `local.prefix`, jamais d'ARN ni de nom de compte en dur
  (outputs de modules, `data.aws_caller_identity`) ; une entrée de map (`local.lambdas`, `local.schedules`) plutôt
  qu'une ressource copiée ; limites des services dans des blocs `validation`.
- Écritures S3 de données : idempotentes (mêmes clés, mêmes octets au rejeu), fichier puis `_MANIFEST.json` en dernier.
- Commits : message préfixé par la branche courante (`main: …`, `RLINK-123: …`), sans footer d'attribution d'outil
  (`Co-Authored-By`, « Generated with ») ; `git add` de fichiers nommés, jamais `git add -A`.

## Interdits

- **Jamais de numéro de compte AWS (12 chiffres) dans un fichier suivi** : le dépôt est public sur GitHub. Écrire
  `<account_id>` ; avant tout commit, `git diff --cached | grep -E '[0-9]{12}'` doit être vide (hors comptes
  d'exemple de la doc AWS comme `123456789012`).
- **Jamais `terraform apply` / `destroy`, `make up` / `make down`, ni commande AWS qui écrit** (`invoke`, `put-*`,
  `delete-*`, `set-alarm-state`…) sans accord explicite de l'humain : le compte de dev est partagé et réel.
- Ne pas modifier ni commiter : `*.tfstate*`, `infra/envs/*/backend.hcl`, `infra/envs/*/local.tfvars`,
  `infra/bootstrap/local.auto.tfvars` (gitignorés, propres à chaque poste) ; les `.example` servent de modèle.
- Ne pas éditer `uv.lock` à la main : `uv add` / `uv lock`. Ne pas éditer `build/` (généré).
- Ne pas supprimer avec `rm -rf` : `trash` (réversible).
- Ne pas réécrire l'historique git ni forcer un push sans demande explicite.
- `learning/` est la source d'un miroir Notion et des cartes de l'app de révision : ne pas renommer ni supprimer
  ces fichiers ; cartes au format de la spec de revision-pwa, validées par `make cards-validate`.

## Contexte AWS

- Profil CLI `data-platform`, région `eu-west-3`, un seul environnement déployé (`dev`) dans un compte partagé
  avec d'autres projets : ne toucher qu'aux ressources préfixées `data-platform-`.
- Noms réels toujours lus dans les outputs : `terraform -chdir=infra output -json bucket_names | jq -r .raw`,
  `… output -json lambda_functions`. Dans un exemple ou une doc : `$RAW_BUCKET`, `<account_id>`.

## Données : ce qu'il faut savoir avant de toucher l'ingestion

- Partition : `s3://<raw>/bodacc/date=YYYY-MM-DD/part-0001.jsonl.gz` puis `_MANIFEST.json` (`count`, `sha256` du
  JSONL non compressé). Un lecteur ne lit une partition que si son manifest existe.
- Octets reproductibles : export trié (`order_by=id`), gzip `mtime=0` sans nom de fichier. Preuve d'un rejeu :
  `sha256` du manifest ou `cmp` des versions S3 ; **jamais l'ETag** (SSE-KMS : il change à chaque PUT).
- Calendrier de la source : 5 bulletins par semaine, `count` 0 normal le samedi et le lundi (bulletins jumelés
  datés du dimanche et du mardi) ; un 0 un autre jour se signale. Détail mesuré : `docs/source-bodacc.md`.
- Une journée vide est une partition complète (`count` 0 + manifest) ; une journée absente n'a pas de manifest.

## Apprentissage : `learning/`, `/tuteur`, `/cartes`

Ce projet est aussi un parcours de formation : l'humain apprend Terraform, Python et le data engineering AWS
(senior TypeScript/Next, novice Terraform et Python). Chaque carte Trello du board « Plateforme data + agent »
(lecture seule pour les agents) devient un cours, et chaque étape validée produit des cartes de révision.
Les skills `/tuteur` et `/cartes` et le dépôt revision-pwa sont locaux au poste de l'auteur (`~/.claude/skills/`,
`~/Desktop/workspace/revision-pwa/`) : sans eux, respecter le format ci-dessous à la main, et ne pas publier.

- **Cours** : `learning/<id>.md` (`s1-08.md`…), créé par le skill `/tuteur <carte>`. Format : frontmatter
  (`status: en-cours | termine`), Objectif, Prérequis, `### [ ] Étape N — …` avec `À faire` (déroulé numéroté
  indenté de 2 espaces), `Concept`, `Indice`, `Vérifier` (commandes entre backticks, `→ attendu`), puis, une fois
  l'étape validée : `- Question : … → …`, `- Erreur vue : <message exact> → <cause>`, `- Cartes : …`,
  `- Résultat : …` ; Critères de validation, Question de compréhension, Journal daté (on n'en supprime rien).
- **Ouvrir une étape** : d'abord le contexte (c'est quoi, pourquoi ici, objectif vérifiable, schéma du flux), puis
  les fichiers avec « à remarquer en relisant », puis les commandes. L'agent écrit le code quand on le lui demande
  (« go », « fait le ») ; l'humain lance lui-même `make up`, `terraform`, et les commandes AWS en écriture.
- **Notion** : chaque `learning/*.md` est miroité dans une page Notion (mapping `learning/.notion-sync.json`,
  conversion `~/.claude/skills/tuteur/scripts/md_to_notion.py`). Le `.md` est la source : resynchroniser la page
  après chaque modification, ne jamais éditer Notion à la main.
- **Cartes de révision** : `learning/cartes-<domaine>-<thème>.md`, une notion par fichier (un thème = un fichier),
  format v3 de l'app revision-pwa (spec : `~/Desktop/workspace/revision-pwa/spec/cartes.md`, registre des domaines
  `spec/domaines.json`). Générées par le skill `/cartes` en mode étape, à chaque étape validée, sans question :
  notions de l'étape classées en domaine / thème, nouvelles cartes sans doublon, `- Source : data-platform · <id>`,
  exemples Python exécutés, propositions fausses vérifiées fausses.
- **Exécution des cartes** : par des agents en arrière-plan, sur des fichiers disjoints (validation isolée avec
  `CARDS_DIR=<dossier temporaire>`), pour ne jamais bloquer le travail principal ; une seule publication à la fin :
  `make cards-validate` (format + exécution des exemples, 0 erreur exigée) puis `make cards-publish`.
- Dans `learning/` comme ailleurs : aucun numéro de compte, aucun secret, aucun identifiant personnel.

## Ajouter une Lambda

1. `uv init --lib lambdas/<dossier>`, dépendances avec `uv add --package <name> …`, tests à côté.
2. `make lambdas-publish LAMBDA=<name>` (zip reproductible, roues Linux aarch64, publié par hash).
3. Une entrée dans `local.lambdas` (`infra/lambdas.tf`) avec sa politique IAM minimale ; l'alarme `Errors` est
   créée d'office. Planification éventuelle : une entrée dans `local.schedules` (`infra/schedules.tf`).
4. `make plan`, puis l'humain lance `make up`.
