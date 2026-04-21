import random
from typing import Any


def _sample_value_from_criterion(
    criterion: dict[str, Any],
    characteristic: dict[str, Any],
    rng: random.Random,
) -> str | float:
    if criterion["characteristic_type"] == "range":
        expected_min = float(criterion["expected_min"])
        expected_max = float(criterion["expected_max"])
        if expected_min == expected_max:
            return expected_min
        margin = (expected_max - expected_min) * 0.05
        return rng.uniform(expected_min - margin, expected_max + margin)
    return str(criterion["expected_enum_key"])


def generate_synthetic_cases(
    *,
    diagnoses: list[dict[str, Any]],
    characteristic_map: dict[int, dict[str, Any]],
    samples_per_diagnosis: int = 48,
    missing_prob: float = 0.2,
    noise_prob: float = 0.08,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[int]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    labels: list[int] = []

    for diagnosis in diagnoses:
        criteria = diagnosis.get("criteria", [])
        if not criteria:
            continue

        for _ in range(samples_per_diagnosis):
            patient_values: dict[str, Any] = {}
            for criterion in criteria:
                characteristic_id = int(criterion["characteristic_id"])
                characteristic = characteristic_map.get(characteristic_id)
                if not characteristic:
                    continue

                if rng.random() < missing_prob:
                    continue

                value = _sample_value_from_criterion(criterion, characteristic, rng)

                if rng.random() < noise_prob:
                    if characteristic["type"] == "range":
                        allowed_min = float(characteristic["allowed"][0])
                        allowed_max = float(characteristic["allowed"][1])
                        spread = (allowed_max - allowed_min) * 0.08
                        value = float(value) + rng.uniform(-spread, spread)
                    else:
                        allowed = characteristic["allowed"] if isinstance(characteristic["allowed"], dict) else {}
                        keys = sorted(allowed.keys())
                        if keys:
                            value = rng.choice(keys)

                patient_values[str(characteristic_id)] = value

            if patient_values:
                rows.append(patient_values)
                labels.append(int(diagnosis["id"]))

    return rows, labels
