import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
EXPORT_FIXTURE = FIXTURES / "export_2026-10-20_collective_25.jsonl"
RECORDS_FIXTURE = FIXTURES / "records_2026-10-20_limit1.json"


@pytest.fixture
def export_text() -> str:
    """Corps brut de l'export JSONL enregistré (25 procédures collectives du 2026-10-20)."""
    return EXPORT_FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def export_rows(export_text: str) -> list[dict]:
    """Les 25 annonces de l'export, une par ligne, décodées en dict."""
    return [json.loads(line) for line in export_text.splitlines() if line.strip()]


@pytest.fixture
def records_payload() -> dict:
    """Réponse `/records?limit=1` enregistrée pour le 2026-10-20 (porte `total_count`)."""
    return json.loads(RECORDS_FIXTURE.read_text(encoding="utf-8"))
