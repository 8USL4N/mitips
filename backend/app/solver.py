from typing import Any

from sqlalchemy.orm import Session

from app.services.knowledge_service import KnowledgeService


def _format_range(min_value: float | None, max_value: float | None, unit: str = "") -> str:
    if min_value is None or max_value is None:
        return "не задано"
    unit_part = f" {unit}" if unit else ""
    return f"{min_value}–{max_value}{unit_part}"


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
            expected_key = criterion["expected_enum_key"]

            characteristic = characteristic_map.get(criterion["characteristic_id"])
            if not characteristic:
                explanation.append(
                    {
                        "characteristic": criterion["characteristic_name"],
                        "expected": str(expected_key),
                        "actual": actual,
                        "match": False,
                    }
                )
                continue
            allowed = characteristic["allowed"] if isinstance(characteristic["allowed"], dict) else {}

            actual_key = str(actual) if actual is not None else ""
            expected_view = allowed.get(str(expected_key), str(expected_key))
            actual_view = allowed.get(actual_key, "не указано" if actual is None else actual_key)
            match = actual_key == str(expected_key)

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


def rank_all(session: Session, patient_values: dict[str, Any]) -> list[dict[str, Any]]:
    service = KnowledgeService(session)
    results = []

    for diagnosis in service.list_diagnoses():
        solved = solve_validate_selected(session, diagnosis["id"], patient_values)
        total = max(solved["total_count"], 1)
        score = solved["matched_count"] / total
        results.append({"diagnosis_id": diagnosis["id"], "score": round(score, 3), **solved})

    results.sort(key=lambda item: item["score"], reverse=True)
    return results
