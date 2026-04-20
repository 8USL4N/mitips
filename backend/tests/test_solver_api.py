def _characteristic_ids(client) -> dict[str, int]:
    characteristics = client.get("/api/characteristics").json()
    return {item["name"]: item["id"] for item in characteristics}


def test_diagnoses_endpoint_returns_list(client) -> None:
    response = client.get("/api/diagnoses")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 9


def test_solve_endpoint_success(client) -> None:
    diagnoses = client.get("/api/diagnoses").json()
    cholera = next(item for item in diagnoses if item["name"] == "Холера")
    detail = client.get(f"/api/diagnoses/{cholera['id']}").json()

    values = {}
    for criterion in detail["criteria"]:
        if criterion["characteristic_type"] == "range":
            values[str(criterion["characteristic_id"])] = 36.5
        elif criterion["characteristic_name"] == "Характер стула":
            values[str(criterion["characteristic_id"])] = "1"
        elif criterion["characteristic_name"] == "Боль в животе":
            values[str(criterion["characteristic_id"])] = "0"

    response = client.post(
        "/api/solver/solve",
        json={
            "diagnosis_id": cholera["id"],
            "patient_values": values,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["diagnosis"] == "Холера"
    assert payload["matched_count"] == payload["total_count"]


def test_determine_endpoint_exact_match_returns_single(client) -> None:
    characteristic_ids = _characteristic_ids(client)
    response = client.post(
        "/api/solver/determine",
        json={
            "patient_values": {
                str(characteristic_ids["Температура тела"]): 36.8,
                str(characteristic_ids["Характер стула"]): "1",
                str(characteristic_ids["Боль в животе"]): "0",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "determined"
    assert payload["primary"]["diagnosis"] == "Холера"
    assert payload["alternatives"] == []


def test_determine_endpoint_nothing_matches_returns_top3(client) -> None:
    characteristic_ids = _characteristic_ids(client)
    response = client.post(
        "/api/solver/determine",
        json={
            "patient_values": {
                str(characteristic_ids["Температура тела"]): 42.0,
                str(characteristic_ids["Кашель"]): "2",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_determined"
    assert payload["primary"] is None
    assert len(payload["alternatives"]) == 3


def test_determine_endpoint_empty_input_returns_400(client) -> None:
    response = client.post("/api/solver/determine", json={"patient_values": {}})

    assert response.status_code == 400


def test_create_and_delete_diagnosis(client) -> None:
    treatments = client.get("/api/treatments").json()
    characteristics = client.get("/api/characteristics").json()

    cough = next(item for item in characteristics if item["name"] == "Кашель")
    treatment = next(item for item in treatments if item["name"] == "Лечение не требуется")

    diagnosis = {
        "name": "Тестовый",
        "icd10": "Z99",
        "treatment_id": treatment["id"],
        "criteria": [
            {
                "characteristic_id": cough["id"],
                "expected_enum_key": "1",
                "expected_min": None,
                "expected_max": None,
            }
        ],
    }

    created = client.post("/api/diagnoses", json=diagnosis)
    assert created.status_code == 200

    diagnosis_id = created.json()["id"]
    deleted = client.delete(f"/api/diagnoses/{diagnosis_id}")
    assert deleted.status_code == 200
