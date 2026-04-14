import json
from pathlib import Path

import pytest

from app import knowledge


@pytest.fixture()
def temp_kb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = Path(__file__).resolve().parents[1] / "data" / "knowledge_base.json"
    target = tmp_path / "knowledge_base.json"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(knowledge, "KB_PATH", target)
    return target


def test_load_kb_has_expected_sections(temp_kb: Path) -> None:
    data = knowledge.load_kb()
    assert set(data.keys()) == {"body_systems", "characteristics", "diagnoses", "treatments"}


def test_save_kb_writes_backup(temp_kb: Path) -> None:
    data = knowledge.load_kb()
    data["treatments"]["Лечение холеры"].append("Тестовый шаг")
    knowledge.save_kb(data)

    backup = Path(f"{temp_kb}.bak")
    assert backup.exists()

    new_payload = json.loads(temp_kb.read_text(encoding="utf-8"))
    assert "Тестовый шаг" in new_payload["treatments"]["Лечение холеры"]
