from __future__ import annotations

import random
from typing import Any


def _sample_value_from_criterion(
    criterion: dict[str, Any],
    characteristic: dict[str, Any],
    rng: random.Random,
    noise_prob: float,
) -> str | float:
    if criterion["characteristic_type"] == "range":
        expected_min = float(criterion["expected_min"])
        expected_max = float(criterion["expected_max"])
        if expected_min == expected_max:
            value = expected_min
        else:
            value = rng.uniform(expected_min, expected_max)

        if rng.random() < noise_prob:
            allowed_min = float(characteristic["allowed"][0])
            allowed_max = float(characteristic["allowed"][1])
            spread = max(0.05, (allowed_max - allowed_min) * 0.07)
            value = float(value) + rng.uniform(-spread, spread)
            value = min(max(value, allowed_min), allowed_max)
        return float(value)

    expected_key = str(criterion["expected_enum_key"])
    if rng.random() >= noise_prob:
        return expected_key

    allowed = characteristic["allowed"] if isinstance(characteristic["allowed"], dict) else {}
    keys = [key for key in sorted(allowed.keys()) if key != expected_key]
    if not keys:
        return expected_key
    return rng.choice(keys)


def _sample_normal_value(characteristic: dict[str, Any], rng: random.Random) -> str | float | None:
    if characteristic["type"] == "range":
        normal = characteristic.get("normal")
        if not isinstance(normal, list) or len(normal) != 2:
            return None
        normal_min = float(normal[0])
        normal_max = float(normal[1])
        if normal_min == normal_max:
            return normal_min
        return rng.uniform(normal_min, normal_max)

    normal_key = characteristic.get("normal")
    if normal_key is None:
        return None
    return str(normal_key)


def generate_synthetic_cases(
    *,
    diagnoses: list[dict[str, Any]],
    characteristic_map: dict[int, dict[str, Any]],
    samples_per_diagnosis: int = 200,
    missing_prob: float = 0.2,
    normal_fill_prob: float = 0.35,
    noise_prob: float = 0.05,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[int]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    labels: list[int] = []

    characteristic_ids = sorted(characteristic_map.keys())

    for diagnosis in diagnoses:
        criteria = diagnosis.get("criteria", [])
        if not criteria:
            continue

        criteria_by_id = {int(item["characteristic_id"]): item for item in criteria}

        for _ in range(samples_per_diagnosis):
            patient_values: dict[str, Any] = {}
            for characteristic_id in characteristic_ids:
                characteristic = characteristic_map[characteristic_id]
                criterion = criteria_by_id.get(characteristic_id)

                if criterion is not None:
                    if rng.random() < missing_prob:
                        continue
                    value = _sample_value_from_criterion(
                        criterion=criterion,
                        characteristic=characteristic,
                        rng=rng,
                        noise_prob=noise_prob,
                    )
                    patient_values[str(characteristic_id)] = value
                    continue

                if rng.random() >= normal_fill_prob:
                    continue
                normal_value = _sample_normal_value(characteristic, rng)
                if normal_value is None:
                    continue
                patient_values[str(characteristic_id)] = normal_value

            if patient_values:
                rows.append(patient_values)
                labels.append(int(diagnosis["id"]))

    return rows, labels
