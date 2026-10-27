"""Point d'entrée : arguments, puis un run de bout en bout sur la fixture (getOrCreate réutilise la session de test)."""

import logging
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

from bodacc_normalize.main import main, parse_args

RAW_3 = Path(__file__).parent / "fixtures" / "raw_3.jsonl"


def test_parse_args_input_obligatoire() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_main_bout_en_bout(spark: SparkSession, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="bodacc_normalize"):
        main(["--input", str(RAW_3)])

    assert "événements normalisés : 3" in caplog.text
