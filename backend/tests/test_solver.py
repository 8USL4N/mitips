import pytest

from app import db
from app.services.knowledge_service import KnowledgeService
from app.solver import solve_by_symptoms, solve_validate_selected


def _characteristic_ids(service: KnowledgeService) -> dict[str, int]:
    return {item["name"]: item["id"] for item in service.list_characteristics()}


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


def test_determine_exact_match_returns_single(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        characteristic_ids = _characteristic_ids(service)
        values = {
            str(characteristic_ids["Температура тела"]): 36.8,
            str(characteristic_ids["Характер стула"]): "1",
            str(characteristic_ids["Боль в животе"]): "0",
        }

        result = solve_by_symptoms(session, values)

    assert result["status"] == "determined"
    assert result["primary"] is not None
    assert result["primary"]["diagnosis"] == "Холера"


def test_determine_all_normal_returns_healthy(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        characteristic_ids = _characteristic_ids(service)
        values = {
            str(characteristic_ids["Температура тела"]): 36.8,
            str(characteristic_ids["Характер стула"]): "0",
            str(characteristic_ids["Наличие и характер сыпи"]): "0",
            str(characteristic_ids["Кашель"]): "0",
            str(characteristic_ids["Цвет кожных покровов и склер"]): "0",
            str(characteristic_ids["Боль в животе"]): "0",
            str(characteristic_ids["Увеличение лимфоузлов"]): "0",
        }

        result = solve_by_symptoms(session, values)

    assert result["status"] == "determined"
    assert result["primary"] is not None
    assert result["primary"]["diagnosis"] == "Здоров"


def test_determine_partial_input_returns_likely(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        characteristic_ids = _characteristic_ids(service)
        values = {
            str(characteristic_ids["Кашель"]): "2",
        }

        result = solve_by_symptoms(session, values)

    assert result["status"] == "likely"
    assert result["primary"] is not None
    assert result["primary"]["diagnosis"] == "Туберкулез органов дыхания"
    assert result["primary"]["missing_characteristics"]


def test_determine_ambiguous_between_two(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        characteristic_ids = _characteristic_ids(service)
        values = {
            str(characteristic_ids["Температура тела"]): 37.0,
        }

        result = solve_by_symptoms(session, values)

    assert result["status"] == "ambiguous"
    assert result["primary"] is None
    assert len(result["alternatives"]) >= 2


def test_determine_nothing_matches_returns_top3(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        characteristic_ids = _characteristic_ids(service)
        values = {
            str(characteristic_ids["Температура тела"]): 42.0,
            str(characteristic_ids["Кашель"]): "2",
        }

        result = solve_by_symptoms(session, values)

    assert result["status"] == "not_determined"
    assert result["primary"] is None
    assert len(result["alternatives"]) == 3


def test_determine_empty_input_returns_error(client) -> None:
    with db.SessionLocal() as session:
        with pytest.raises(ValueError):
            solve_by_symptoms(session, {})
