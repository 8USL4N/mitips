import math
from typing import Any

from sqlalchemy.orm import Session

from app.neural import NeuralDiagnosisRanker
from app.services.knowledge_service import KnowledgeService

_NEURAL_RANKER = NeuralDiagnosisRanker()


def _format_range(min_value: float | None, max_value: float | None, unit: str = "") -> str:
    if min_value is None or max_value is None:
        return "не указано"
    unit_part = f" {unit}" if unit else ""
    return f"{min_value}-{max_value}{unit_part}"


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


def _load_solver_context(service: KnowledgeService) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    characteristics = service.list_characteristics()
    characteristic_map = {int(item["id"]): item for item in characteristics}
    diagnoses: list[dict[str, Any]] = []

    for item in service.list_diagnoses():
        diagnosis = service.get_solver_payload(item["id"])
        if diagnosis:
            diagnoses.append(diagnosis)

    return diagnoses, characteristic_map


def _with_diagnosis_action(diagnosis_name: str, actions: list[str]) -> list[str]:
    diagnosis_action = f"Диагноз: {diagnosis_name}"
    treatment_actions = [action for action in actions if action != diagnosis_action]
    return [diagnosis_action, *treatment_actions]


def _clean_patient_values(
    patient_values: dict[str, Any],
    characteristic_map: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in patient_values.items():
        if value is None:
            continue
        key_str = str(key).strip()
        if not key_str:
            continue
        try:
            characteristic_id = int(key_str)
        except ValueError as exc:
            raise ValueError(f"Некорректный id характеристики: '{key}'") from exc
        characteristic = characteristic_map.get(characteristic_id)
        if not characteristic:
            raise ValueError(f"Неизвестная характеристика id={characteristic_id}")
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                continue
            raw_value: Any = trimmed
        else:
            raw_value = value
        if characteristic["type"] == "range":
            allowed = characteristic.get("allowed")
            if not isinstance(allowed, (list, tuple)) or len(allowed) != 2:
                raise ValueError(
                    f"Некорректная конфигурация характеристики '{characteristic['name']}': "
                    "allowed должен быть [min, max]"
                )
            try:
                allowed_min = float(allowed[0])
                allowed_max = float(allowed[1])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Некорректная конфигурация характеристики '{characteristic['name']}': "
                    "allowed должен содержать числа"
                ) from exc
            if not math.isfinite(allowed_min) or not math.isfinite(allowed_max):
                raise ValueError(
                    f"Некорректная конфигурация характеристики '{characteristic['name']}': "
                    "allowed должен содержать конечные числа"
                )
            if allowed_min > allowed_max:
                raise ValueError(
                    f"Некорректная конфигурация характеристики '{characteristic['name']}': "
                    "allowed_min не может быть больше allowed_max"
                )
            try:
                value_float = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Значение характеристики '{characteristic['name']}' должно быть числом") from exc
            if not math.isfinite(value_float):
                raise ValueError(f"Значение характеристики '{characteristic['name']}' должно быть конечным числом")
            if value_float < allowed_min or value_float > allowed_max:
                unit = str(characteristic.get("unit") or "")
                unit_part = f" {unit}" if unit else ""
                raise ValueError(
                    f"Значение характеристики '{characteristic['name']}' должно быть в диапазоне "
                    f"{allowed_min}-{allowed_max}{unit_part}"
                )
            cleaned[key_str] = value_float
        else:
            enum_key = str(raw_value)
            allowed = characteristic["allowed"] if isinstance(characteristic["allowed"], dict) else {}
            if enum_key not in allowed:
                raise ValueError(
                    f"Значение '{enum_key}' не входит в допустимые варианты характеристики "
                    f"'{characteristic['name']}'"
                )
            cleaned[key_str] = enum_key
    return cleaned

def _matches_criterion(criterion: dict[str, Any], actual: Any) -> bool:
    if criterion["characteristic_type"] == "range":
        try:
            value = float(actual)
            expected_min = float(criterion["expected_min"])
            expected_max = float(criterion["expected_max"])
        except (TypeError, ValueError):
            return False
        return expected_min <= value <= expected_max
    return str(actual) == str(criterion["expected_enum_key"])


def _hypothesis_score(row: dict[str, Any]) -> float:
    return (
        (row["specificity"] * 0.65)
        + (row["coverage"] * 0.35)
        - (row["contradiction_count"] * 1.0)
    )


def evaluate_hypotheses_by_refutation(
    diagnoses: list[dict[str, Any]],
    patient_values: dict[str, Any],
    characteristic_map: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []

    for diagnosis in diagnoses:
        criteria_by_id = {int(item["characteristic_id"]): item for item in diagnosis["criteria"]}
        matched_count = 0
        contradiction_count = 0
        answered_count = 0
        diagnosis_trace: list[dict[str, Any]] = []

        for key, actual in patient_values.items():
            answered_count += 1
            characteristic_id = int(key)
            criterion = criteria_by_id.get(characteristic_id)
            if not criterion:
                diagnosis_trace.append(
                    {
                        "characteristic_id": characteristic_id,
                        "result": "no_criterion",
                    }
                )
                continue

            if _matches_criterion(criterion, actual):
                matched_count += 1
                diagnosis_trace.append(
                    {
                        "characteristic_id": characteristic_id,
                        "result": "matched",
                    }
                )
            else:
                contradiction_count += 1
                diagnosis_trace.append(
                    {
                        "characteristic_id": characteristic_id,
                        "result": "contradiction",
                    }
                )

        criteria_count = len(diagnosis["criteria"])
        missing_characteristics = [
            item["characteristic_name"]
            for item in diagnosis["criteria"]
            if str(item["characteristic_id"]) not in patient_values
        ]
        row = {
            "diagnosis_id": int(diagnosis["id"]),
            "matched_count": matched_count,
            "contradiction_count": contradiction_count,
            "answered_count": answered_count,
            "criteria_count": criteria_count,
            "coverage": (matched_count / answered_count) if answered_count else 0.0,
            "specificity": (matched_count / criteria_count) if criteria_count else 0.0,
            "missing_characteristics": missing_characteristics,
            "trace": diagnosis_trace,
            "hypothesis_score": 0.0,
        }
        row["hypothesis_score"] = _hypothesis_score(row)
        all_rows.append(row)
        trace.append({"diagnosis_id": row["diagnosis_id"], "events": diagnosis_trace})

        if contradiction_count == 0:
            candidates.append(row)
        else:
            rejected.append(row)

    return {
        "candidates": candidates,
        "rejected": rejected,
        "trace": trace,
        "all": all_rows,
    }

def _select_candidate_group(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    viable = [
        row
        for row in candidates
        if row["contradiction_count"] == 0
        and row["matched_count"] > 0
        and row["criteria_count"] > 0
    ]
    full_matches = [row for row in viable if row["matched_count"] == row["criteria_count"]]
    if len(full_matches) == 1:
        return {"method": "hypothesis_refutation", "status": "determined", "rows": full_matches}
    if len(full_matches) > 1:
        return {"method": "neural", "status": "neural_selected", "rows": full_matches}
    if not viable:
        return {"method": "fallback", "status": "not_determined", "rows": []}
    max_matched = max(row["matched_count"] for row in viable)
    top_rows = [row for row in viable if row["matched_count"] == max_matched]
    if len(top_rows) == 1:
        return {"method": "hypothesis_refutation", "status": "likely", "rows": top_rows}
    return {"method": "neural", "status": "neural_selected", "rows": top_rows}

def _build_hypothesis(
    *,
    diagnosis: dict[str, Any],
    patient_values: dict[str, Any],
    characteristic_map: dict[int, dict[str, Any]],
    answered_count: int,
) -> dict[str, Any]:
    explanation: list[dict[str, Any]] = []
    missing_characteristics: list[str] = []
    matched_count = 0

    for criterion in diagnosis["criteria"]:
        key = str(criterion["characteristic_id"])
        actual = patient_values.get(key)

        if actual is None:
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

    return {
        "diagnosis_id": int(diagnosis["id"]),
        "diagnosis": diagnosis["name"],
        "icd10": diagnosis.get("icd10"),
        "treatment_name": diagnosis["treatment_name"],
        "actions": _with_diagnosis_action(diagnosis["name"], diagnosis["actions"]),
        "explanation": explanation,
        "matched_count": matched_count,
        "answered_count": answered_count,
        "total_count": len(diagnosis["criteria"]),
        "missing_characteristics": missing_characteristics,
    }


def solve_validate_selected(
    session: Session,
    diagnosis_id: int,
    patient_values: dict[str, Any],
) -> dict[str, Any]:
    service = KnowledgeService(session)
    diagnosis = service.get_solver_payload(diagnosis_id)
    if not diagnosis:
        raise ValueError(f"Диагноз id={diagnosis_id} не найден в базе знаний")
    characteristic_map = {item["id"]: item for item in service.list_characteristics()}
    cleaned_values = _clean_patient_values(patient_values, characteristic_map)
    explanation: list[dict[str, Any]] = []
    matched_count = 0
    for criterion in diagnosis["criteria"]:
        characteristic_id = criterion["characteristic_id"]
        key = str(characteristic_id)
        actual = cleaned_values.get(key)
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
        "actions": _with_diagnosis_action(diagnosis["name"], diagnosis["actions"]),
        "explanation": explanation,
        "matched_count": matched_count,
        "total_count": len(explanation),
    }

def solve_by_symptoms(session: Session, patient_values: dict[str, Any]) -> dict[str, Any]:
    service = KnowledgeService(session)
    diagnoses, characteristic_map = _load_solver_context(service)
    cleaned_values = _clean_patient_values(patient_values, characteristic_map)
    if not cleaned_values:
        raise ValueError("Нужно ввести хотя бы одно значение характеристики")
    if not diagnoses:
        raise ValueError("Не удалось выполнить диагностику: нет доступных диагнозов")
    filter_result = evaluate_hypotheses_by_refutation(
        diagnoses=diagnoses,
        patient_values=cleaned_values,
        characteristic_map=characteristic_map,
    )
    diagnosis_by_id = {int(item["id"]): item for item in diagnoses}
    selection = _select_candidate_group(filter_result["all"])
    selected_rows = selection["rows"]
    if selection["method"] == "hypothesis_refutation":
        row = selected_rows[0]
        diagnosis = diagnosis_by_id[row["diagnosis_id"]]
        hypothesis = _build_hypothesis(
            diagnosis=diagnosis,
            patient_values=cleaned_values,
            characteristic_map=characteristic_map,
            answered_count=row["answered_count"],
        )
        status = selection["status"]
        confidence = 1.0
        if status == "likely":
            confidence = (
                float(row["matched_count"]) / float(row["criteria_count"]) if row["criteria_count"] else 0.0
            )
        message = (
            "Гипотеза не опровергнута: введённые признаки подтверждают все критерии диагноза."
            if status == "determined"
            else "Гипотеза не опровергнута и имеет наибольшее число совпадений среди неполных гипотез."
        )
        return {
            "status": status,
            "message": message,
            "primary": hypothesis,
            "alternatives": [],
            "selection_method": "hypothesis_refutation",
            "confidence": float(confidence),
            "ranked_candidates": [
                {
                    "diagnosis_id": int(diagnosis["id"]),
                    "diagnosis": diagnosis["name"],
                    "score": float(max(0.0, row["hypothesis_score"])),
                    "source": "hypothesis_refutation",
                }
            ],
        }
    if selection["method"] == "neural":
        snapshot = {
            "characteristics": list(characteristic_map.values()),
            "diagnoses": diagnoses,
        }
        candidate_ids = [int(item["diagnosis_id"]) for item in selected_rows]
        ranked = _NEURAL_RANKER.rank(
            patient_values=cleaned_values,
            candidate_ids=candidate_ids,
            knowledge_snapshot=snapshot,
        )
        if not ranked:
            fallback_rows = sorted(selected_rows, key=lambda item: item["hypothesis_score"], reverse=True)[:3]
            fallback_alternatives = [
                _build_hypothesis(
                    diagnosis=diagnosis_by_id[int(item["diagnosis_id"])],
                    patient_values=cleaned_values,
                    characteristic_map=characteristic_map,
                    answered_count=item["answered_count"],
                )
                for item in fallback_rows
            ]
            fallback_ranked = [
                {
                    "diagnosis_id": int(item["diagnosis_id"]),
                    "diagnosis": diagnosis_by_id[int(item["diagnosis_id"])]["name"],
                    "score": float(max(0.0, item["hypothesis_score"])),
                    "source": "hypothesis_refutation",
                }
                for item in fallback_rows
            ]
            return {
                "status": "not_determined",
                "message": "Все диагностические гипотезы опровергнуты противоречиями или не имеют совпадений. Показаны ближайшие альтернативы.",
                "primary": None,
                "alternatives": fallback_alternatives,
                "selection_method": "fallback",
                "confidence": None,
                "ranked_candidates": fallback_ranked,
            }
        candidate_stats = {int(item["diagnosis_id"]): item for item in selected_rows}
        primary_id = int(ranked[0]["diagnosis_id"])
        primary_hypothesis = _build_hypothesis(
            diagnosis=diagnosis_by_id[primary_id],
            patient_values=cleaned_values,
            characteristic_map=characteristic_map,
            answered_count=candidate_stats[primary_id]["answered_count"],
        )
        alternatives: list[dict[str, Any]] = []
        for row in ranked[1:]:
            diagnosis_id = int(row["diagnosis_id"])
            hypothesis = _build_hypothesis(
                diagnosis=diagnosis_by_id[diagnosis_id],
                patient_values=cleaned_values,
                characteristic_map=characteristic_map,
                answered_count=candidate_stats[diagnosis_id]["answered_count"],
            )
            alternatives.append(hypothesis)
        ranked_candidates = [
            {
                "diagnosis_id": int(row["diagnosis_id"]),
                "diagnosis": diagnosis_by_id[int(row["diagnosis_id"])]["name"],
                "score": float(row["probability"]),
                "source": "neural",
            }
            for row in ranked
        ]
        return {
            "status": "neural_selected",
            "message": "Найдено несколько равных не опровергнутых гипотез. Нейронная сеть выбрала наиболее вероятную.",
            "primary": primary_hypothesis,
            "alternatives": alternatives,
            "selection_method": "neural",
            "confidence": float(ranked[0]["probability"]),
            "ranked_candidates": ranked_candidates,
        }
    ranked_hypotheses = sorted(filter_result["all"], key=lambda row: row["hypothesis_score"], reverse=True)
    top_rows = ranked_hypotheses[:3]
    alternatives = [
        _build_hypothesis(
            diagnosis=diagnosis_by_id[int(row["diagnosis_id"])],
            patient_values=cleaned_values,
            characteristic_map=characteristic_map,
            answered_count=row["answered_count"],
        )
        for row in top_rows
    ]
    ranked_candidates = [
        {
            "diagnosis_id": int(row["diagnosis_id"]),
            "diagnosis": diagnosis_by_id[int(row["diagnosis_id"])]["name"],
            "score": float(max(0.0, row["hypothesis_score"])),
            "source": "hypothesis_refutation",
        }
        for row in top_rows
    ]
    return {
        "status": "not_determined",
        "message": "Все диагностические гипотезы опровергнуты противоречиями или не имеют совпадений. Показаны ближайшие альтернативы.",
        "primary": None,
        "alternatives": alternatives,
        "selection_method": "fallback",
        "confidence": None,
        "ranked_candidates": ranked_candidates,
    }

