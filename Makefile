.PHONY: sync lint fmt test test-integration cov check tf-init tf-fmt tf-validate plan up down

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
