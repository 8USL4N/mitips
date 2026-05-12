import pytest


def _characteristics(client):
    return client.get("/api/characteristics").json()


def _diagnoses(client):
    return client.get("/api/diagnoses").json()


def _first_diagnosis_payload(client) -> tuple[dict, dict]:
    diagnosis = _diagnoses(client)[0]
    detail = client.get(f"/api/diagnoses/{diagnosis['id']}").json()
    characteristics = {item["id"]: item for item in _characteristics(client)}

    values = {}
    for criterion in detail["criteria"]:
        char = characteristics[criterion["characteristic_id"]]
        if char["type"] == "range":
            values[str(criterion["characteristic_id"])] = (
                float(criterion["expected_min"]) + float(criterion["expected_max"])
            ) / 2.0
        else:
            values[str(criterion["characteristic_id"])] = str(criterion["expected_enum_key"])
    return diagnosis, values


def _find_hypothesis_refutation_selected_payload(client) -> tuple[str, dict]:
    diagnoses = _diagnoses(client)
    characteristics = {item["id"]: item for item in _characteristics(client)}
    for diagnosis in diagnoses:
        detail = client.get(f"/api/diagnoses/{diagnosis['id']}").json()
        values = {}
        for criterion in detail["criteria"]:
            char = characteristics[criterion["characteristic_id"]]
            if char["type"] == "range":
                values[str(criterion["characteristic_id"])] = (
                    float(criterion["expected_min"]) + float(criterion["expected_max"])
                ) / 2.0
            else:
                values[str(criterion["characteristic_id"])] = str(criterion["expected_enum_key"])

        payload = {"patient_values": values}
        response = client.post("/api/solver/determine", json=payload)
        if response.status_code != 200:
            continue
        body = response.json()
        if body["selection_method"] == "hypothesis_refutation" and body["status"] in {"determined", "likely"}:
            return diagnosis["name"], payload

    raise AssertionError("No payload found for hypothesis-refutation-based selection")


def _find_neural_selected_payload(client) -> dict:
    diagnoses = _diagnoses(client)
    characteristics = {item["id"]: item for item in _characteristics(client)}
    for diagnosis in diagnoses:
        detail = client.get(f"/api/diagnoses/{diagnosis['id']}").json()
        for criterion in detail["criteria"]:
            char = characteristics[criterion["characteristic_id"]]
            if char["type"] == "range":
                value = (float(criterion["expected_min"]) + float(criterion["expected_max"])) / 2.0
            else:
                value = str(criterion["expected_enum_key"])

            payload = {"patient_values": {str(criterion["characteristic_id"]): value}}
            response = client.post("/api/solver/determine", json=payload)
            if response.status_code == 200 and response.json()["status"] == "neural_selected":
                return payload
    raise AssertionError("No payload found that returns neural_selected")


def test_diagnoses_endpoint_returns_list(client) -> None:
    response = client.get("/api/diagnoses")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 9


def test_solve_endpoint_success(client) -> None:
    diagnosis, values = _first_diagnosis_payload(client)
    response = client.post(
        "/api/solver/solve",
        json={"diagnosis_id": diagnosis["id"], "patient_values": values},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["diagnosis"] == diagnosis["name"]
    assert payload["matched_count"] == payload["total_count"]
    assert payload["actions"][0] == f"Диагноз: {diagnosis['name']}"


def test_determine_endpoint_exact_match_hypothesis_refutation_based(client) -> None:
    diagnosis_name, payload = _find_hypothesis_refutation_selected_payload(client)
    response = client.post("/api/solver/determine", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"determined", "likely"}
    assert body["selection_method"] == "hypothesis_refutation"
    assert body["primary"]["diagnosis"] == diagnosis_name
    assert body["primary"]["actions"][0] == f"Диагноз: {diagnosis_name}"
    assert body["ranked_candidates"][0]["source"] == "hypothesis_refutation"
    assert body["alternatives"] == []


def test_determine_endpoint_multiple_candidates_uses_neural(client) -> None:
    payload = _find_neural_selected_payload(client)
    response = client.post("/api/solver/determine", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "neural_selected"
    assert result["selection_method"] == "neural"
    assert result["primary"] is not None
    assert result["alternatives"]
    assert result["confidence"] is not None
    assert result["ranked_candidates"]
    assert result["primary"]["actions"][0] == f"Диагноз: {result['primary']['diagnosis']}"
    assert all(item["actions"][0] == f"Диагноз: {item['diagnosis']}" for item in result["alternatives"])


def test_determine_endpoint_nothing_matches_returns_not_determined(client) -> None:
    range_characteristic = next(item for item in _characteristics(client) if item["type"] == "range")
    response = client.post(
        "/api/solver/determine",
        json={
            "patient_values": {
                str(range_characteristic["id"]): 41.5
            }
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_determined"
    assert payload["selection_method"] == "fallback"
    assert all(item["actions"][0] == f"Диагноз: {item['diagnosis']}" for item in payload["alternatives"])


def test_determine_endpoint_empty_input_returns_400(client) -> None:
    response = client.post("/api/solver/determine", json={"patient_values": {}})
    assert response.status_code == 400


def test_determine_endpoint_unknown_characteristic_returns_400(client) -> None:
    response = client.post("/api/solver/determine", json={"patient_values": {"999999": "1"}})
    assert response.status_code == 400


def test_determine_endpoint_range_value_above_allowed_returns_400(client) -> None:
    range_characteristic = next(item for item in _characteristics(client) if item["type"] == "range")
    response = client.post(
        "/api/solver/determine",
        json={
            "patient_values": {
                str(range_characteristic["id"]): float(range_characteristic["allowed"][1]) + 1.0
            }
        },
    )
    assert response.status_code == 400


def test_determine_endpoint_range_value_below_allowed_returns_400(client) -> None:
    range_characteristic = next(item for item in _characteristics(client) if item["type"] == "range")
    response = client.post(
        "/api/solver/determine",
        json={
            "patient_values": {
                str(range_characteristic["id"]): float(range_characteristic["allowed"][0]) - 1.0
            }
        },
    )
    assert response.status_code == 400


@pytest.mark.parametrize("bad_value", ["NaN", "Infinity", "-Infinity"])
def test_determine_endpoint_non_finite_value_returns_400(client, bad_value: str) -> None:
    range_characteristic = next(item for item in _characteristics(client) if item["type"] == "range")
    response = client.post(
        "/api/solver/determine",
        json={"patient_values": {str(range_characteristic["id"]): bad_value}},
    )
    assert response.status_code == 400


def test_solve_endpoint_range_value_above_allowed_returns_400(client) -> None:
    diagnosis, _ = _first_diagnosis_payload(client)
    range_characteristic = next(item for item in _characteristics(client) if item["type"] == "range")
    response = client.post(
        "/api/solver/solve",
        json={
            "diagnosis_id": diagnosis["id"],
            "patient_values": {str(range_characteristic["id"]): float(range_characteristic["allowed"][1]) + 1.0},
        },
    )
    assert response.status_code == 400


def test_solve_endpoint_range_value_below_allowed_returns_400(client) -> None:
    diagnosis, _ = _first_diagnosis_payload(client)
    range_characteristic = next(item for item in _characteristics(client) if item["type"] == "range")
    response = client.post(
        "/api/solver/solve",
        json={
            "diagnosis_id": diagnosis["id"],
            "patient_values": {str(range_characteristic["id"]): float(range_characteristic["allowed"][0]) - 1.0},
        },
    )
    assert response.status_code == 400


@pytest.mark.parametrize("bad_value", ["NaN", "Infinity", "-Infinity"])
def test_solve_endpoint_non_finite_value_returns_400(client, bad_value: str) -> None:
    diagnosis, _ = _first_diagnosis_payload(client)
    range_characteristic = next(item for item in _characteristics(client) if item["type"] == "range")
    response = client.post(
        "/api/solver/solve",
        json={
            "diagnosis_id": diagnosis["id"],
            "patient_values": {str(range_characteristic["id"]): bad_value},
        },
    )
    assert response.status_code == 400


def test_create_and_delete_diagnosis(client) -> None:
    characteristics = _characteristics(client)
    enum_char = next(item for item in characteristics if item["type"] == "enum")
    enum_key = next(iter(enum_char["allowed"].keys()))

    diagnosis = {
        "name": "Test diagnosis API",
        "icd10": "Z99",
        "criteria": [
            {
                "characteristic_id": enum_char["id"],
                "expected_enum_key": enum_key,
                "expected_min": None,
                "expected_max": None,
            }
        ],
    }

    created = client.post("/api/diagnoses", json=diagnosis)
    assert created.status_code == 200
    assert created.json()["treatment_name"] == "Лечение не назначено"

    diagnosis_id = created.json()["id"]
    deleted = client.delete(f"/api/diagnoses/{diagnosis_id}")
    assert deleted.status_code == 200
