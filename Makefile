.PHONY: sync lint fmt test test-integration cov check spark-jars tf-init tf-fmt tf-validate plan up down lambdas-build lambdas-publish deploy replay duckdb cards-validate cards-publish

# ---------- Python ----------

sync:
	uv sync --all-packages

lint:
	uv run ruff check .
	uv run ruff format --check .

# check --fix d'abord : retirer un import peut laisser une ligne vide que seul format nettoie
# (dans l'autre ordre, `make lint` échoue juste après). Même ordre que le hook pre-commit.
fmt:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest

# Appelle la vraie API BODACC (~10 s) : exclu de `make test` par le marqueur `integration`.
test-integration:
	uv run pytest -m integration -v

# Couverture lignes + branches de bodacc-client, sans le test d'intégration ; échoue sous 80 %.
cov:
	uv run pytest packages/bodacc-client --cov=bodacc_client --cov-branch --cov-report=term-missing --cov-fail-under=80

check: lint test

# ---------- Spark ----------
# Jar Iceberg pour Spark 3.5 / Scala 2.12 (même Spark qu'EMR 7.14), téléchargé une fois dans build/jars/ :
# la fixture `spark` des tests le charge depuis le disque, jamais depuis Maven (pas de réseau dans les tests).
# Idempotent : jar présent et SHA-1 conforme au .sha1 de Maven Central → rien n'est téléchargé.
# Écrit dans un .part renommé seulement après vérification : un téléchargement coupé ne laisse pas de jar corrompu.
ICEBERG_VERSION ?= 1.11.0
SPARK_SCALA      = 3.5_2.12
ICEBERG_JAR      = iceberg-spark-runtime-$(SPARK_SCALA)-$(ICEBERG_VERSION).jar
ICEBERG_URL      = https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-$(SPARK_SCALA)/$(ICEBERG_VERSION)/$(ICEBERG_JAR)
JARS_DIR         = build/jars

spark-jars:
	@mkdir -p $(JARS_DIR)
	@expected=$$(curl -fsSL "$(ICEBERG_URL).sha1" | cut -c1-40) || { echo "sha1 introuvable : $(ICEBERG_URL).sha1"; exit 1; }; \
	jar="$(JARS_DIR)/$(ICEBERG_JAR)"; \
	if [ -f "$$jar" ] && [ "$$(shasum -a 1 "$$jar" | cut -c1-40)" = "$$expected" ]; then \
		echo "déjà présent : $$jar"; exit 0; \
	fi; \
	echo "téléchargement : $(ICEBERG_URL)"; \
	curl -fsSL -o "$$jar.part" "$(ICEBERG_URL)" || { rm -f "$$jar.part"; exit 1; }; \
	actual=$$(shasum -a 1 "$$jar.part" | cut -c1-40); \
	if [ "$$actual" != "$$expected" ]; then \
		echo "sha1 KO : attendu $$expected, obtenu $$actual"; rm -f "$$jar.part"; exit 1; \
	fi; \
	mv "$$jar.part" "$$jar" && echo "sha1 OK : $$jar"

# ---------- Lambdas ----------
# Une Lambda = un membre uv dans lambdas/<dossier>/ (son `name` est son identifiant partout).
# Zip reproductible, roues Linux arm64 du lock ; publié dans le bucket artefacts du bootstrap
# sous lambdas/<name>/<sha256>.zip, puis pointeur current.json lu par Terraform.
#   make lambdas-publish                      -> toutes les Lambdas
#   make lambdas-publish LAMBDA=ingest-bodacc -> une seule
#   make deploy                               -> publier puis appliquer (ce que fera la CI)
# PROFILE vide en CI : identifiants OIDC de l'environnement.
LAMBDA  ?=
PROFILE ?= data-platform

lambdas-build:
	uv run infra/scripts/build_lambda.py $(LAMBDA)

lambdas-publish:
	uv run infra/scripts/build_lambda.py --publish $(if $(PROFILE),--profile $(PROFILE)) $(LAMBDA)

deploy: lambdas-publish up

# Rejouer une plage de jours : une invocation synchrone par jour, bornes incluses (infra/scripts/replay.py).
# Nom de la fonction lu dans les outputs Terraform : le même appel vise dev ou prod selon l'état courant.
#   make replay FROM=2026-10-01 TO=2026-10-19
#   make replay FROM=2026-10-01 TO=2026-10-19 LAMBDA=ingest-bodacc
REPLAY_LAMBDA = $(or $(LAMBDA),ingest-bodacc)

replay:
	@test -n "$(FROM)" -a -n "$(TO)" || { echo "usage : make replay FROM=YYYY-MM-DD TO=YYYY-MM-DD [LAMBDA=…]"; exit 2; }
	@# Nom résolu et testé avant l'appel : dans un `$$(…)` passé en argument, l'échec de jq serait perdu
	@# et replay.py recevrait `--function null`.
	@fn=$$($(TF) output -json lambda_functions | jq -er '."$(REPLAY_LAMBDA)"') \
		|| { echo "Lambda inconnue : $(REPLAY_LAMBDA) (voir terraform -chdir=infra output lambda_functions)"; exit 2; }; \
	set -x; uv run infra/scripts/replay.py --from $(FROM) --to $(TO) --function "$$fn" \
		$(if $(PROFILE),--profile $(PROFILE))

# ---------- Terraform ----------
# Un seul code (infra/), une config par environnement (infra/envs/<ENV>/).
#   make plan            -> dev
#   make plan ENV=prod   -> prod
ENV      ?= dev
TF        = terraform -chdir=infra
ENV_DIR   = envs/$(ENV)
TF_VARS   = -var-file=$(ENV_DIR)/$(ENV).tfvars -var-file=$(ENV_DIR)/local.tfvars

tf-init:
	$(TF) init -backend-config=$(ENV_DIR)/backend.hcl -input=false -reconfigure

tf-fmt:
	terraform fmt -check -recursive infra

tf-validate: tf-init
	$(TF) validate

plan: tf-init
	$(TF) plan -input=false -out=tfplan $(TF_VARS)
	$(TF) show -json tfplan | uv run infra/scripts/check_tags.py

up: tf-init
	$(TF) apply -input=false -auto-approve $(TF_VARS)

down: tf-init
	$(TF) destroy -input=false -auto-approve $(TF_VARS)

# ---------- Exploration ----------
# DuckDB prêt à interroger le data lake : macros `raw('<source>')` (toutes les partitions brutes) et
# `manifests('<source>')`. Bucket lu dans les outputs Terraform, identifiants du profil AWS.
#   make duckdb   puis   SELECT familleavis, count(*) FROM raw('bodacc') GROUP BY 1;
duckdb:
	RAW_BUCKET=$$(terraform -chdir=infra output -json bucket_names | jq -r .raw) \
	AWS_PROFILE=$(PROFILE) duckdb -init tools/duckdb_init.sql

# ---------- Cartes de révision (consommées par revision-pwa) ----------
# learning/cartes-*.md → s3://<content>/sources/data-platform/ ; la Lambda de revision-pwa
# reconstruit le catalogue, l'app l'affiche à l'ouverture suivante (pas de redéploiement).
# Format : ../revision-pwa/spec/cartes.md. Écrites par l'agent /cartes.
REVISION_PWA    ?= ../revision-pwa
PUBLISH_PROFILE ?= revision-publish-data-platform
CARDS_BUCKET    ?= $(shell terraform -chdir=$(REVISION_PWA)/infra output -raw content_bucket)

# Parser + exécution de chaque exemple Python, avec le code de revision-pwa (cloné à côté).
cards-validate:
	$(MAKE) -C $(REVISION_PWA) cards-validate PRODUCER=$(CURDIR)

# Rien n'est envoyé si une carte est invalide. Rôle limité à sources/data-platform/* :
# --delete ne peut retirer que nos propres cartes. sync n'envoie que les fichiers modifiés.
cards-publish: cards-validate
	aws s3 sync learning/ s3://$(CARDS_BUCKET)/sources/data-platform/ \
	  --exclude "*" --include "cartes-*.md" --include "glossaire-*.md" --delete \
	  --profile $(PUBLISH_PROFILE) --region eu-west-3
