.PHONY: sync lint fmt test test-integration cov check tf-init tf-fmt tf-validate plan up down cards-validate cards-publish

# ---------- Python ----------

sync:
	uv sync --all-packages

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

# Appelle la vraie API BODACC (~10 s) : exclu de `make test` par le marqueur `integration`.
test-integration:
	uv run pytest -m integration -v

# Couverture lignes + branches de bodacc-client, sans le test d'intégration ; échoue sous 80 %.
cov:
	uv run pytest packages/bodacc-client --cov=bodacc_client --cov-branch --cov-report=term-missing --cov-fail-under=80

check: lint test

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
	  --exclude "*" --include "cartes-*.md" --delete \
	  --profile $(PUBLISH_PROFILE) --region eu-west-3
