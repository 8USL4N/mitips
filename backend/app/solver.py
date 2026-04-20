from typing import Any

from sqlalchemy.orm import Session

from app.services.knowledge_service import KnowledgeService


def _format_range(min_value: float | None, max_value: float | None, unit: str = "") -> str:
    if min_value is None or max_value is None:
        return "не задано"
    unit_part = f" {unit}" if unit else ""
    return f"{min_value}–{max_value}{unit_part}"


def _clean_patient_values(patient_values: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in patient_values.items():
        if value is None:
            continue
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                continue
            cleaned[str(key)] = trimmed
        else:
            cleaned[str(key)] = value
    return cleaned


def _build_enum_views(
    *,
    criterion: dict[str, Any],
    actual: Any,
    characteristic_map: dict[int, dict[str, Any]],
) -> tuple[str, str | None, bool]:
    expected_key = str(criterion["expected_enum_key"])
    characteristic = characteristic_map.get(criterion["characteristic_id"])
    allowed = characteristic["allowed"] if characteristic and isinstance(characteristic["allowed"], dict) else {}

    expected_view = allowed.get(expected_key, expected_key)
    if actual is None:
        return expected_view, None, False

    actual_key = str(actual)
    actual_view = allowed.get(actual_key, actual_key)
    return expected_view, actual_view, actual_key == expected_key


def solve_validate_selected(
    session: Session,
    diagnosis_id: int,
    patient_values: dict[str, Any],
) -> dict[str, Any]:
    service = KnowledgeService(session)
    diagnosis = service.get_solver_payload(diagnosis_id)
    if not diagnosis:
        raise ValueError(f"Диагноз id={diagnosis_id} не найден в базе знаний")

    explanation: list[dict[str, Any]] = []
    matched_count = 0
    characteristic_map = {item["id"]: item for item in service.list_characteristics()}

    for criterion in diagnosis["criteria"]:
        characteristic_id = criterion["characteristic_id"]
        key = str(characteristic_id)
        actual = patient_values.get(key)

        if criterion["characteristic_type"] == "range":
            try:
                actual_float = float(actual)
                expected_min = float(criterion["expected_min"])
                expected_max = float(criterion["expected_max"])
                match = expected_min <= actual_float <= expected_max
                actual_view: float | None = actual_float
            except (TypeError, ValueError):
                match = False
                actual_view = None

            explanation.append(
                {
                    "characteristic": criterion["characteristic_name"],
                    "expected": _format_range(
                        criterion["expected_min"],
                        criterion["expected_max"],
                        criterion.get("characteristic_unit") or "",
                    ),
                    "actual": actual_view,
                    "match": match,
                }
            )
        else:
            expected_view, actual_view, match = _build_enum_views(
                criterion=criterion,
                actual=actual,
                characteristic_map=characteristic_map,
            )
            explanation.append(
                {
                    "characteristic": criterion["characteristic_name"],
                    "expected": expected_view,
                    "actual": actual_view,
                    "match": match,
                }
            )

        if explanation[-1]["match"]:
            matched_count += 1

    return {
        "diagnosis": diagnosis["name"],
        "icd10": diagnosis.get("icd10"),
        "treatment_name": diagnosis["treatment_name"],
        "actions": diagnosis["actions"],
        "explanation": explanation,
        "matched_count": matched_count,
        "total_count": len(explanation),
    }


def _build_hypothesis(
    *,
    diagnosis: dict[str, Any],
    patient_values: dict[str, Any],
    characteristic_map: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    explanation: list[dict[str, Any]] = []
    missing_characteristics: list[str] = []
    matched_count = 0
    answered_count = 0

    for criterion in diagnosis["criteria"]:
        key = str(criterion["characteristic_id"])
        actual = patient_values.get(key)
        is_answered = actual is not None

        if is_answered:
            answered_count += 1
        else:
            missing_characteristics.append(criterion["characteristic_name"])

        if criterion["characteristic_type"] == "range":
            if actual is None:
                actual_view: float | str | None = None
                match = False
            else:
                try:
                    actual_float = float(actual)
                    actual_view = actual_float
                    expected_min = float(criterion["expected_min"])
                    expected_max = float(criterion["expected_max"])
                    match = expected_min <= actual_float <= expected_max
                except (TypeError, ValueError):
                    actual_view = str(actual)
                    match = False

            explanation.append(
                {
                    "characteristic": criterion["characteristic_name"],
                    "expected": _format_range(
                        criterion["expected_min"],
                        criterion["expected_max"],
                        criterion.get("characteristic_unit") or "",
                    ),
                    "actual": actual_view,
                    "match": match,
                }
            )
        else:
            expected_view, actual_view, match = _build_enum_views(
                criterion=criterion,
                actual=actual,
                characteristic_map=characteristic_map,
            )
            explanation.append(
                {
                    "characteristic": criterion["characteristic_name"],
                    "expected": expected_view,
                    "actual": actual_view,
                    "match": match,
                }
            )

        if match:
            matched_count += 1

    total_count = len(diagnosis["criteria"])
    exact_match = answered_count > 0 and matched_count == answered_count
    covered = (answered_count / total_count) if total_count else 0.0
    score = (matched_count / answered_count) if answered_count else 0.0

    hypothesis = {
        "diagnosis_id": diagnosis["id"],
        "diagnosis": diagnosis["name"],
        "icd10": diagnosis.get("icd10"),
        "treatment_name": diagnosis["treatment_name"],
        "actions": diagnosis["actions"],
        "explanation": explanation,
        "matched_count": matched_count,
        "answered_count": answered_count,
        "total_count": total_count,
        "missing_characteristics": missing_characteristics,
    }
    return {
        "hypothesis": hypothesis,
        "exact_match": exact_match,
        "covered": covered,
        "score": score,
    }


def solve_by_symptoms(session: Session, patient_values: dict[str, Any]) -> dict[str, Any]:
    cleaned_values = _clean_patient_values(patient_values)
    if not cleaned_values:
        raise ValueError("Нужно ввести хотя бы одно значение характеристики")

    service = KnowledgeService(session)
    characteristic_map = {item["id"]: item for item in service.list_characteristics()}

    evaluated: list[dict[str, Any]] = []
    for item in service.list_diagnoses():
        diagnosis = service.get_solver_payload(item["id"])
        if not diagnosis:
            continue
        evaluated.append(
            _build_hypothesis(
                diagnosis=diagnosis,
                patient_values=cleaned_values,
                characteristic_map=characteristic_map,
            )
        )

    if not evaluated:
        raise ValueError("Не удалось выполнить диагностику: нет доступных диагнозов")

    exact_matches = [item for item in evaluated if item["exact_match"]]
    exact_matches.sort(
        key=lambda item: (
            item["covered"],
            item["hypothesis"]["matched_count"],
            -item["hypothesis"]["total_count"],
            item["hypothesis"]["diagnosis"],
        ),
        reverse=True,
    )

    if len(exact_matches) == 1:
        candidate = exact_matches[0]
        if candidate["covered"] == 1.0:
            return {
                "status": "determined",
                "message": "Диагноз определён однозначно.",
                "primary": candidate["hypothesis"],
                "alternatives": [],
            }
        return {
            "status": "likely",
            "message": "Есть единственный подходящий диагноз, но данных недостаточно для точного вывода.",
            "primary": candidate["hypothesis"],
            "alternatives": [],
        }

    if len(exact_matches) > 1:
        return {
            "status": "ambiguous",
            "message": "Обнаружено несколько подходящих диагнозов. Уточните недостающие характеристики.",
            "primary": None,
            "alternatives": [item["hypothesis"] for item in exact_matches],
        }

    evaluated.sort(
        key=lambda item: (
            item["score"],
            item["hypothesis"]["matched_count"],
            item["hypothesis"]["answered_count"],
            -item["hypothesis"]["total_count"],
            item["hypothesis"]["diagnosis"],
        ),
        reverse=True,
    )
    return {
        "status": "not_determined",
        "message": "Однозначный диагноз не установлен. Показаны наиболее близкие гипотезы.",
        "primary": None,
        "alternatives": [item["hypothesis"] for item in evaluated[:3]],
    }
