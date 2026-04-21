import pytest

from app import db
from app.services.knowledge_service import KnowledgeService
import app.solver as solver_module
from app.solver import solve_by_symptoms, solve_validate_selected


def _pick_value_for_criterion(criterion: dict, characteristic: dict) -> str | float:
    if criterion["characteristic_type"] == "range":
        return (float(criterion["expected_min"]) + float(criterion["expected_max"])) / 2.0
    return str(criterion["expected_enum_key"])


def _make_values_from_detail(detail: dict, characteristic_map: dict[int, dict]) -> dict[str, str | float]:
    values: dict[str, str | float] = {}
    for criterion in detail.get("criteria", []):
        characteristic = characteristic_map[int(criterion["characteristic_id"])]
        values[str(criterion["characteristic_id"])] = _pick_value_for_criterion(criterion, characteristic)
    return values


def _find_multi_candidate_values(service: KnowledgeService, characteristic_map: dict[int, dict]) -> dict[str, str | float]:
    for diagnosis in service.list_diagnoses():
        detail = service.get_diagnosis_detail(diagnosis["id"])
        if not detail:
            continue
        for criterion in detail.get("criteria", []):
            characteristic = characteristic_map[int(criterion["characteristic_id"])]
            value = _pick_value_for_criterion(criterion, characteristic)
            candidate_input = {str(criterion["characteristic_id"]): value}
            result = solve_by_symptoms(service.session, candidate_input)
            if result["status"] == "ml_selected":
                return candidate_input
    raise AssertionError("Не найден вход, который приводит к ml_selected")


def _update_any_diagnosis_criteria(service: KnowledgeService) -> None:
    characteristics = {int(item["id"]): item for item in service.list_characteristics()}
    detail = service.get_diagnosis_detail(service.list_diagnoses()[0]["id"])
    assert detail is not None

    new_criteria = []
    changed = False
    for criterion in detail["criteria"]:
        row = {
            "characteristic_id": int(criterion["characteristic_id"]),
            "expected_enum_key": criterion["expected_enum_key"],
            "expected_min": criterion["expected_min"],
            "expected_max": criterion["expected_max"],
        }
        if changed:
            new_criteria.append(row)
            continue

        characteristic = characteristics[row["characteristic_id"]]
        if characteristic["type"] == "range":
            allowed_min = float(characteristic["allowed"][0])
            allowed_max = float(characteristic["allowed"][1])
            width = max(0.2, (allowed_max - allowed_min) * 0.1)
            row["expected_min"] = max(allowed_min, allowed_max - width)
            row["expected_max"] = allowed_max
            changed = True
        else:
            allowed_keys = list((characteristic["allowed"] or {}).keys())
            if len(allowed_keys) > 1:
                if str(row["expected_enum_key"]) == allowed_keys[0]:
                    row["expected_enum_key"] = allowed_keys[1]
                else:
                    row["expected_enum_key"] = allowed_keys[0]
                changed = True
        new_criteria.append(row)

    if not changed:
        return

    payload = {
        "name": detail["name"],
        "icd10": detail["icd10"],
        "treatment_id": detail["treatment_id"],
        "criteria": new_criteria,
    }
    updated = service.update_diagnosis(detail["id"], payload)
    assert updated is not None


def test_solver_returns_treatment_for_known_case(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        diagnosis = service.list_diagnoses()[0]
        detail = service.get_diagnosis_detail(diagnosis["id"])
        assert detail is not None
        characteristic_map = {int(item["id"]): item for item in service.list_characteristics()}
        values = _make_values_from_detail(detail, characteristic_map)
        result = solve_validate_selected(session, diagnosis["id"], values)

    assert result["diagnosis"] == diagnosis["name"]
    assert result["matched_count"] == result["total_count"]


def test_solver_raises_for_unknown_diagnosis(client) -> None:
    with db.SessionLocal() as session:
        with pytest.raises(ValueError):
            solve_validate_selected(session, 999999, {})


def test_determine_one_candidate_is_rules_based(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        diagnosis = service.list_diagnoses()[0]
        detail = service.get_diagnosis_detail(diagnosis["id"])
        assert detail is not None
        characteristic_map = {int(item["id"]): item for item in service.list_characteristics()}
        values = _make_values_from_detail(detail, characteristic_map)
        result = solve_by_symptoms(session, values)

    assert result["status"] in {"determined", "likely"}
    assert result["selection_method"] == "rules"
    assert result["primary"] is not None
    assert result["primary"]["diagnosis"] == diagnosis["name"]
    assert result["alternatives"] == []


def test_determine_multiple_candidates_uses_ml_ranker(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        characteristic_map = {int(item["id"]): item for item in service.list_characteristics()}
        values = _find_multi_candidate_values(service, characteristic_map)
        result = solve_by_symptoms(session, values)

    assert result["status"] == "ml_selected"
    assert result["primary"] is not None
    assert result["selection_method"] == "ml"
    assert isinstance(result["confidence"], float)
    assert result["alternatives"]
    assert result["ranked_candidates"]
    scores = [row["score"] for row in result["ranked_candidates"]]
    assert scores == sorted(scores, reverse=True)


def test_determine_nothing_matches_returns_not_determined(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        range_characteristic = next(item for item in service.list_characteristics() if item["type"] == "range")
        values = {str(range_characteristic["id"]): float(range_characteristic["allowed"][1]) + 100.0}
        result = solve_by_symptoms(session, values)

    assert result["status"] == "not_determined"
    assert result["selection_method"] == "fallback"
    assert result["primary"] is None
    assert len(result["alternatives"]) > 0


def test_determine_unknown_characteristic_returns_error(client) -> None:
    with db.SessionLocal() as session:
        with pytest.raises(ValueError):
            solve_by_symptoms(session, {"999999": "1"})


def test_determine_empty_input_returns_error(client) -> None:
    with db.SessionLocal() as session:
        with pytest.raises(ValueError):
            solve_by_symptoms(session, {})


def test_solver_retrains_after_knowledge_change(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        characteristic_map = {int(item["id"]): item for item in service.list_characteristics()}
        values = _find_multi_candidate_values(service, characteristic_map)
        first = solve_by_symptoms(session, values)
        assert first["status"] == "ml_selected"
        old_hash = solver_module._RANKER._snapshot_hash

        _update_any_diagnosis_criteria(service)
        second = solve_by_symptoms(session, values)
        assert second["status"] in {"ml_selected", "determined", "likely", "not_determined"}
        assert solver_module._RANKER._snapshot_hash != old_hash
