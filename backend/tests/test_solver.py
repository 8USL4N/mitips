import pytest

from app import db
from app.orm import Treatment
from app.services.knowledge_service import KnowledgeService
import app.solver as solver_module
from app.solver import solve_by_symptoms, solve_validate_selected


def _range_char(char_id: int, name: str, allowed: tuple[float, float] = (0.0, 100.0)) -> dict:
    return {
        "id": char_id,
        "name": name,
        "type": "range",
        "unit": "",
        "allowed": [float(allowed[0]), float(allowed[1])],
        "normal": [float(allowed[0]), float(allowed[1])],
    }


def _range_criterion(char_id: int, name: str, expected_min: float = 10.0, expected_max: float = 20.0) -> dict:
    return {
        "id": char_id,
        "characteristic_id": char_id,
        "characteristic_name": name,
        "characteristic_type": "range",
        "characteristic_unit": "",
        "expected_enum_key": None,
        "expected_min": float(expected_min),
        "expected_max": float(expected_max),
    }


def _diagnosis(diagnosis_id: int, name: str, criteria: list[dict]) -> dict:
    return {
        "id": diagnosis_id,
        "name": name,
        "icd10": None,
        "treatment_name": f"Treatment {name}",
        "actions": [f"Action {name}"],
        "criteria": criteria,
    }


def _run_synthetic_determine(
    monkeypatch: pytest.MonkeyPatch,
    session,
    *,
    diagnoses: list[dict],
    characteristics: list[dict],
    patient_values: dict[str, float],
    ranked: list[dict] | None = None,
    candidate_ids_out: list[list[int]] | None = None,
) -> dict:
    characteristic_map = {int(item["id"]): item for item in characteristics}

    monkeypatch.setattr(
        solver_module,
        "_load_solver_context",
        lambda _service: (diagnoses, characteristic_map),
    )

    if ranked is not None or candidate_ids_out is not None:
        def fake_rank(*, patient_values, candidate_ids, knowledge_snapshot):  # noqa: ANN001
            if candidate_ids_out is not None:
                candidate_ids_out.append([int(item) for item in candidate_ids])
            return ranked or []

        monkeypatch.setattr(solver_module._NEURAL_RANKER, "rank", fake_rank)

    return solve_by_symptoms(session, patient_values)


def test_2_of_2_beats_2_of_3_rules_determined(monkeypatch: pytest.MonkeyPatch, client) -> None:
    chars = [_range_char(1, "c1"), _range_char(2, "c2"), _range_char(3, "c3")]
    diag_a = _diagnosis(1, "A", [_range_criterion(1, "c1"), _range_criterion(2, "c2")])
    diag_b = _diagnosis(
        2,
        "B",
        [_range_criterion(1, "c1"), _range_criterion(2, "c2"), _range_criterion(3, "c3")],
    )

    with db.SessionLocal() as session:
        result = _run_synthetic_determine(
            monkeypatch,
            session,
            diagnoses=[diag_a, diag_b],
            characteristics=chars,
            patient_values={"1": 15.0, "2": 15.0},
        )

    assert result["selection_method"] == "rules"
    assert result["status"] == "determined"
    assert result["primary"]["diagnosis"] == "A"


def test_multiple_full_matches_use_neural(monkeypatch: pytest.MonkeyPatch, client) -> None:
    chars = [_range_char(1, "c1"), _range_char(2, "c2")]
    diag_a = _diagnosis(1, "A", [_range_criterion(1, "c1"), _range_criterion(2, "c2")])
    diag_b = _diagnosis(2, "B", [_range_criterion(1, "c1"), _range_criterion(2, "c2")])
    candidate_ids_out: list[list[int]] = []

    with db.SessionLocal() as session:
        result = _run_synthetic_determine(
            monkeypatch,
            session,
            diagnoses=[diag_a, diag_b],
            characteristics=chars,
            patient_values={"1": 15.0, "2": 15.0},
            ranked=[
                {"diagnosis_id": 2, "probability": 0.7},
                {"diagnosis_id": 1, "probability": 0.3},
            ],
            candidate_ids_out=candidate_ids_out,
        )

    assert result["selection_method"] == "neural"
    assert result["status"] == "neural_selected"
    assert candidate_ids_out == [[1, 2]]


def test_equal_best_partials_use_neural_and_only_top_group(monkeypatch: pytest.MonkeyPatch, client) -> None:
    chars = [
        _range_char(1, "c1"),
        _range_char(2, "c2"),
        _range_char(3, "c3"),
        _range_char(4, "c4"),
        _range_char(5, "c5"),
        _range_char(6, "c6"),
    ]
    diag_a = _diagnosis(
        1,
        "A",
        [_range_criterion(1, "c1"), _range_criterion(2, "c2"), _range_criterion(3, "c3")],
    )
    diag_b = _diagnosis(
        2,
        "B",
        [
            _range_criterion(1, "c1"),
            _range_criterion(2, "c2"),
            _range_criterion(4, "c4"),
            _range_criterion(5, "c5"),
        ],
    )
    diag_c = _diagnosis(3, "C", [_range_criterion(1, "c1"), _range_criterion(6, "c6")])
    candidate_ids_out: list[list[int]] = []

    with db.SessionLocal() as session:
        result = _run_synthetic_determine(
            monkeypatch,
            session,
            diagnoses=[diag_a, diag_b, diag_c],
            characteristics=chars,
            patient_values={"1": 15.0, "2": 15.0},
            ranked=[
                {"diagnosis_id": 1, "probability": 0.55},
                {"diagnosis_id": 2, "probability": 0.45},
            ],
            candidate_ids_out=candidate_ids_out,
        )

    assert result["selection_method"] == "neural"
    assert result["status"] == "neural_selected"
    assert candidate_ids_out == [[1, 2]]


def test_single_best_partial_is_rules_likely(monkeypatch: pytest.MonkeyPatch, client) -> None:
    chars = [_range_char(1, "c1"), _range_char(2, "c2"), _range_char(3, "c3"), _range_char(4, "c4"), _range_char(5, "c5")]
    diag_a = _diagnosis(
        1,
        "A",
        [
            _range_criterion(1, "c1"),
            _range_criterion(2, "c2"),
            _range_criterion(3, "c3"),
            _range_criterion(4, "c4"),
            _range_criterion(5, "c5"),
        ],
    )
    diag_b = _diagnosis(
        2,
        "B",
        [_range_criterion(1, "c1"), _range_criterion(2, "c2"), _range_criterion(4, "c4"), _range_criterion(5, "c5")],
    )

    with db.SessionLocal() as session:
        result = _run_synthetic_determine(
            monkeypatch,
            session,
            diagnoses=[diag_a, diag_b],
            characteristics=chars,
            patient_values={"1": 15.0, "2": 15.0, "3": 15.0},
        )

    assert result["selection_method"] == "rules"
    assert result["status"] == "likely"
    assert result["primary"]["diagnosis"] == "A"


def test_2_of_2_beats_3_of_5_by_full_match_priority(monkeypatch: pytest.MonkeyPatch, client) -> None:
    chars = [_range_char(1, "c1"), _range_char(2, "c2"), _range_char(3, "c3"), _range_char(4, "c4"), _range_char(5, "c5")]
    diag_a = _diagnosis(1, "A", [_range_criterion(1, "c1"), _range_criterion(2, "c2")])
    diag_b = _diagnosis(
        2,
        "B",
        [
            _range_criterion(1, "c1"),
            _range_criterion(2, "c2"),
            _range_criterion(3, "c3"),
            _range_criterion(4, "c4"),
            _range_criterion(5, "c5"),
        ],
    )

    with db.SessionLocal() as session:
        result = _run_synthetic_determine(
            monkeypatch,
            session,
            diagnoses=[diag_a, diag_b],
            characteristics=chars,
            patient_values={"1": 15.0, "2": 15.0, "3": 15.0},
        )

    assert result["selection_method"] == "rules"
    assert result["status"] == "determined"
    assert result["primary"]["diagnosis"] == "A"


@pytest.mark.parametrize("value", [101.0, -1.0, float("nan"), float("inf"), float("-inf")])
def test_out_of_range_or_non_finite_values_raise_error(monkeypatch: pytest.MonkeyPatch, client, value: float) -> None:
    chars = [_range_char(1, "temp", (0.0, 100.0))]
    diag = _diagnosis(1, "A", [_range_criterion(1, "temp")])

    with db.SessionLocal() as session:
        with pytest.raises(ValueError):
            _run_synthetic_determine(
                monkeypatch,
                session,
                diagnoses=[diag],
                characteristics=chars,
                patient_values={"1": value},
            )


def test_solve_validate_selected_uses_cleaning_for_range_bounds(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        diagnosis = service.list_diagnoses()[0]
        range_char = next(item for item in service.list_characteristics() if item["type"] == "range")

        with pytest.raises(ValueError):
            solve_validate_selected(
                session,
                diagnosis["id"],
                {str(range_char["id"]): float(range_char["allowed"][1]) + 1.0},
            )


def test_repair_mojibake_text_variants(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        original = "Госпитализировать пациента"
        bad_latin = original.encode("utf-8").decode("latin1")
        bad_double = bad_latin.encode("utf-8").decode("latin1")
        bad_triple = bad_double.encode("utf-8").decode("latin1")
        bad_cp1251 = original.encode("utf-8").decode("cp1251")

        assert service._repair_mojibake_text(bad_latin) == original
        assert service._repair_mojibake_text(bad_double) == original
        assert service._repair_mojibake_text(bad_triple) == original
        assert service._repair_mojibake_text(bad_cp1251) == original


def test_repair_mojibake_in_db_fixes_persisted_text(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        treatment = session.query(Treatment).order_by(Treatment.id).first()
        assert treatment is not None
        assert treatment.actions

        original_action = treatment.actions[0].action
        treatment.actions[0].action = original_action.encode("utf-8").decode("latin1")
        session.commit()

        changed = service.repair_mojibake_in_db()
        assert changed >= 1

        reloaded = service.get_treatment_detail(treatment.id)
        assert reloaded is not None
        assert reloaded["actions"][0] == original_action
