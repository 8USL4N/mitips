from typing import Any

from app.knowledge import load_kb


def _format_range(value: list[float], unit: str = "") -> str:
    unit_part = f" {unit}" if unit else ""
    return f"{value[0]}–{value[1]}{unit_part}"


def solve_validate_selected(diagnosis_name: str, patient_values: dict[str, Any]) -> dict[str, Any]:
    kb = load_kb()

    diagnosis = kb["diagnoses"].get(diagnosis_name)
    if not diagnosis:
        raise ValueError(f"Диагноз '{diagnosis_name}' не найден в базе знаний")

    treatment_name = diagnosis["treatment"]
    actions = kb["treatments"].get(treatment_name, [])

    explanation: list[dict[str, Any]] = []
    matched_count = 0

    for char_name, expected in diagnosis["characteristics"].items():
        char_info = kb["characteristics"].get(char_name)
        actual = patient_values.get(char_name)

        if not char_info:
            explanation.append(
                {
                    "characteristic": char_name,
                    "expected": str(expected),
                    "actual": actual,
                    "match": False,
                }
            )
            continue

        if char_info["type"] == "range":
            try:
                actual_float = float(actual)
                match = float(expected[0]) <= actual_float <= float(expected[1])
                actual_view: float | None = actual_float
            except (TypeError, ValueError):
                match = False
                actual_view = None

            expected_view = _format_range(expected, char_info.get("unit", ""))
            explanation.append(
                {
                    "characteristic": char_name,
                    "expected": expected_view,
                    "actual": actual_view,
                    "match": match,
                }
            )
        else:
            allowed = char_info.get("allowed", {})
            expected_key = str(expected)
            actual_key = str(actual) if actual is not None else ""
            expected_view = allowed.get(expected_key, expected_key)
            actual_view = allowed.get(actual_key, "не указано" if actual is None else actual_key)
            match = actual_key == expected_key
            explanation.append(
                {
                    "characteristic": char_name,
                    "expected": expected_view,
                    "actual": actual_view,
                    "match": match,
                }
            )

        if explanation[-1]["match"]:
            matched_count += 1

    return {
        "diagnosis": diagnosis_name,
        "icd10": diagnosis.get("icd10"),
        "treatment_name": treatment_name,
        "actions": actions,
        "explanation": explanation,
        "matched_count": matched_count,
        "total_count": len(explanation),
    }


def rank_all(patient_values: dict[str, Any]) -> list[dict[str, Any]]:
    """Non-MVP helper: score every diagnosis by number of matched characteristics."""
    kb = load_kb()
    results = []

    for diagnosis_name in kb["diagnoses"].keys():
        solved = solve_validate_selected(diagnosis_name, patient_values)
        total = max(solved["total_count"], 1)
        score = solved["matched_count"] / total
        results.append({"diagnosis": diagnosis_name, "score": round(score, 3), **solved})

    results.sort(key=lambda item: item["score"], reverse=True)
    return results
