"""Tests de check_tags.py.

Lancer :
    uv run --with pytest pytest -q infra/scripts/test_check_tags.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import check_tags  # noqa: E402

SCRIPT = Path(__file__).with_name("check_tags.py")


def _res(address: str, values: dict, mode: str = "managed") -> dict:
    return {"address": address, "mode": mode, "type": address.split(".")[-2], "values": values}


@pytest.fixture
def plan() -> dict:
    """Plan synthétique : même forme que `terraform show -json tfplan`."""
    ok = {"tags_all": {"project": "data-platform", "environment": "dev"}}
    return {
        "format_version": "1.2",
        "planned_values": {
            "root_module": {
                "resources": [
                    _res("aws_sns_topic.ok", ok),
                    _res("aws_sns_topic.wrong", {"tags_all": {"project": "oops"}}),
                    _res("aws_sns_topic.missing_key", {"tags_all": {"env": "dev"}}),
                    _res("aws_sns_topic.null_tags", {"tags_all": None}),
                    _res("aws_sns_topic.no_environment", {"tags_all": {"project": "data-platform"}}),
                    _res("aws_sns_topic_subscription.untaggable", {"endpoint": "x"}),
                    _res("data.aws_caller_identity.current", {"account_id": "0"}, mode="data"),
                ],
                "child_modules": [
                    {
                        "address": "module.a",
                        "resources": [_res("module.a.aws_s3_bucket.ok", ok)],
                        "child_modules": [
                            {
                                "address": "module.a.module.b",
                                "resources": [
                                    _res("module.a.module.b.aws_s3_bucket.raw", {"tags_all": {}}),
                                ],
                            }
                        ],
                    },
                    {"address": "module.empty"},
                ],
            }
        },
    }


def test_iter_resources_recurse_dans_tous_les_modules(plan):
    addresses = {r["address"] for r in check_tags.iter_resources(plan["planned_values"]["root_module"])}
    assert "aws_sns_topic.ok" in addresses
    assert "module.a.aws_s3_bucket.ok" in addresses
    assert "module.a.module.b.aws_s3_bucket.raw" in addresses


def test_iter_resources_module_sans_resources_ni_enfants():
    assert list(check_tags.iter_resources({"address": "module.empty"})) == []


def test_find_violations_detecte_faux_absent_et_null(plan):
    assert sorted(check_tags.find_violations(plan)) == [
        "aws_sns_topic.missing_key",
        "aws_sns_topic.no_environment",
        "aws_sns_topic.null_tags",
        "aws_sns_topic.wrong",
        "module.a.module.b.aws_s3_bucket.raw",
    ]


def test_find_violations_ignore_ressource_sans_tags_all(plan):
    assert "aws_sns_topic_subscription.untaggable" not in check_tags.find_violations(plan)


def test_audit_tag_requis_absent_est_une_violation_avec_raison(plan):
    result = check_tags.audit(plan)
    assert result.violations["aws_sns_topic.no_environment"] == "tag(s) manquant(s) : environment"
    assert result.violations["aws_sns_topic.wrong"] == "tag 'project' != 'data-platform'"


def test_audit_tags_requis_configurables(plan):
    # Sans exigence sur environment, no_environment redevient conforme.
    assert "aws_sns_topic.no_environment" not in check_tags.find_violations(plan, required_tags=())
    # Avec un tag supplémentaire exigé, même les "ok" tombent.
    assert "aws_sns_topic.ok" in check_tags.find_violations(plan, required_tags=("environment", "owner"))


def test_audit_compte_taggables_et_non_taggables(plan):
    result = check_tags.audit(plan)
    # 7 ressources avec tags_all (ok, wrong, missing_key, null_tags, no_environment, module.a.ok, module.b.raw)
    assert result.taggable == 7
    # 2 sans tags_all (subscription, data source)
    assert result.untaggable == 2
    assert result.summary == "7 ressources taggables auditées, 2 ignorées (non taggables), 5 violation(s)"


def test_find_violations_plan_sans_ressource():
    assert check_tags.find_violations({"planned_values": {"root_module": {}}}) == []


@pytest.mark.skip(reason="Décision à prendre (indice carte) : ignorer mode == 'data' ou non.")
def test_find_violations_data_source():
    plan = {
        "planned_values": {
            "root_module": {
                "resources": [
                    _res("data.aws_x.y", {"tags_all": {"project": "oops"}}, mode="data"),
                ]
            }
        }
    }
    assert check_tags.find_violations(plan) == []


def _run(plan: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT)],
        input=json.dumps(plan),
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_exit_0_si_conforme():
    plan = {
        "planned_values": {
            "root_module": {
                "resources": [
                    _res("aws_sns_topic.ok", {"tags_all": {"project": "data-platform", "environment": "dev"}})
                ]
            }
        }
    }
    proc = _run(plan)
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr.strip() == ""
    assert proc.stdout.strip() == "1 ressources taggables auditées, 0 ignorées (non taggables), 0 violation(s)"


def test_cli_exit_1_et_affiche_adresses(plan):
    proc = _run(plan)
    assert proc.returncode == 1
    assert "aws_sns_topic.wrong" in proc.stderr
    assert "module.a.module.b.aws_s3_bucket.raw" in proc.stderr
    assert "aws_sns_topic.no_environment: tag(s) manquant(s) : environment" in proc.stderr
    assert "5 violation(s)" in proc.stdout


def test_cli_option_require_remplace_le_defaut(plan):
    proc = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--require", "owner"],
        input=json.dumps(plan),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "aws_sns_topic.ok: tag(s) manquant(s) : owner" in proc.stderr
