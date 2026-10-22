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
    ok = {"tags_all": {"project": "data-platform"}}
    return {
        "format_version": "1.2",
        "planned_values": {
            "root_module": {
                "resources": [
                    _res("aws_sns_topic.ok", ok),
                    _res("aws_sns_topic.wrong", {"tags_all": {"project": "oops"}}),
                    _res("aws_sns_topic.missing_key", {"tags_all": {"env": "dev"}}),
                    _res("aws_sns_topic.null_tags", {"tags_all": None}),
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
        "aws_sns_topic.null_tags",
        "aws_sns_topic.wrong",
        "module.a.module.b.aws_s3_bucket.raw",
    ]


def test_find_violations_ignore_ressource_sans_tags_all(plan):
    assert "aws_sns_topic_subscription.untaggable" not in check_tags.find_violations(plan)


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
            "root_module": {"resources": [_res("aws_sns_topic.ok", {"tags_all": {"project": "data-platform"}})]}
        }
    }
    proc = _run(plan)
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr.strip() == ""


def test_cli_exit_1_et_affiche_adresses(plan):
    proc = _run(plan)
    assert proc.returncode == 1
    assert "aws_sns_topic.wrong" in proc.stderr
    assert "module.a.module.b.aws_s3_bucket.raw" in proc.stderr
