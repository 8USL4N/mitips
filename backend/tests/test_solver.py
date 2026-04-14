from pathlib import Path

import pytest

from app import knowledge
from app.solver import solve_validate_selected


@pytest.fixture()
def temp_kb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = Path(__file__).resolve().parents[1] / "data" / "knowledge_base.json"
    target = tmp_path / "knowledge_base.json"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(knowledge, "KB_PATH", target)
    return target


def test_solver_returns_treatment_for_known_case(temp_kb: Path) -> None:
    result = solve_validate_selected(
        "Холера",
        {
            "Температура тела": 36.5,
            "Характер стула": "1",
            "Боль в животе": "0",
        },
    )

    assert result["treatment_name"] == "Лечение холеры"
    assert result["matched_count"] == result["total_count"]


def test_solver_raises_for_unknown_diagnosis(temp_kb: Path) -> None:
    with pytest.raises(ValueError):
        solve_validate_selected("Неизвестно", {})
