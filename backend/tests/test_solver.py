import pytest

from app import db
from app.services.knowledge_service import KnowledgeService
from app.solver import solve_validate_selected


def test_solver_returns_treatment_for_known_case(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        diagnosis = next(item for item in service.list_diagnoses() if item["name"] == "Холера")
        detail = service.get_diagnosis_detail(diagnosis["id"])

        assert detail is not None
        values = {}
        for criterion in detail["criteria"]:
            if criterion["characteristic_type"] == "range":
                values[str(criterion["characteristic_id"])] = 36.5
            elif criterion["characteristic_name"] == "Характер стула":
                values[str(criterion["characteristic_id"])] = "1"
            elif criterion["characteristic_name"] == "Боль в животе":
                values[str(criterion["characteristic_id"])] = "0"

        result = solve_validate_selected(
            session,
            diagnosis["id"],
            values,
        )

    assert result["treatment_name"] == "Лечение холеры"
    assert result["matched_count"] == result["total_count"]


def test_solver_raises_for_unknown_diagnosis(client) -> None:
    with db.SessionLocal() as session:
        with pytest.raises(ValueError):
            solve_validate_selected(session, 999999, {})
