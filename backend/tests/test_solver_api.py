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
