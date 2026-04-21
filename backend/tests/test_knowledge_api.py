from app import db
from app.services.knowledge_service import KnowledgeService


def test_service_lists_have_expected_sizes(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        diagnoses = service.list_diagnoses()
        characteristics = service.list_characteristics()
        treatments = service.list_treatments()

    assert len(diagnoses) == 9
    assert len(characteristics) >= 7
    assert len(treatments) >= 9


def test_body_systems_crud(client) -> None:
    characteristics = client.get("/api/characteristics").json()
    c1 = characteristics[0]
    c2 = characteristics[1]

    list_response = client.get("/api/body-systems")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1

    created = client.post(
        "/api/body-systems",
        json={"name": "Тестовая система", "characteristic_ids": [c1["id"]]},
    )
    assert created.status_code == 200
    body_system_id = created.json()["id"]
    assert created.json()["characteristic_ids"] == [c1["id"]]

    updated = client.put(
        f"/api/body-systems/{body_system_id}",
        json={"name": "Тестовая система 2", "characteristic_ids": [c1["id"], c2["id"]]},
    )
    assert updated.status_code == 200
    assert sorted(updated.json()["characteristic_ids"]) == sorted([c1["id"], c2["id"]])

    deleted = client.delete(f"/api/body-systems/{body_system_id}")
    assert deleted.status_code == 200


def test_characteristics_crud_and_guards(client) -> None:
    list_response = client.get("/api/characteristics")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1

    create_range = client.post(
        "/api/characteristics",
        json={
            "name": "Частота дыхания",
            "type": "range",
            "allowed": [0, 80],
            "normal": [12, 20],
            "unit": "в мин",
        },
    )
    assert create_range.status_code == 200
    range_id = create_range.json()["id"]

    create_enum = client.post(
        "/api/characteristics",
        json={
            "name": "Озноб",
            "type": "enum",
            "allowed": {"0": "нет", "1": "умеренный", "2": "сильный"},
            "normal": "0",
            "unit": "",
        },
    )
    assert create_enum.status_code == 200
    enum_id = create_enum.json()["id"]

    update_range = client.put(
        f"/api/characteristics/{range_id}",
        json={
            "name": "Частота дыхания (обновлено)",
            "type": "range",
            "allowed": [0, 90],
            "normal": [14, 22],
            "unit": "в минуту",
        },
    )
    assert update_range.status_code == 200
    assert update_range.json()["name"] == "Частота дыхания (обновлено)"

    update_enum = client.put(
        f"/api/characteristics/{enum_id}",
        json={
            "name": "Озноб",
            "type": "enum",
            "allowed": {"0": "нет", "1": "умеренный", "2": "сильный", "3": "очень сильный"},
            "normal": "1",
            "unit": "",
        },
    )
    assert update_enum.status_code == 200
    assert update_enum.json()["normal"] == "1"

    delete_enum = client.delete(f"/api/characteristics/{enum_id}")
    assert delete_enum.status_code == 200
    delete_range = client.delete(f"/api/characteristics/{range_id}")
    assert delete_range.status_code == 200

    diagnosis = client.get("/api/diagnoses").json()[0]
    detail = client.get(f"/api/diagnoses/{diagnosis['id']}").json()
    used_characteristic_id = detail["criteria"][0]["characteristic_id"]
    used_characteristic = client.get(f"/api/characteristics/{used_characteristic_id}").json()

    type_change_blocked = client.put(
        f"/api/characteristics/{used_characteristic_id}",
        json={
            "name": used_characteristic["name"],
            "type": "enum" if used_characteristic["type"] == "range" else "range",
            "allowed": {"0": "нет", "1": "да"} if used_characteristic["type"] == "range" else [0, 100],
            "normal": "0" if used_characteristic["type"] == "range" else [10, 20],
            "unit": used_characteristic["unit"],
        },
    )
    assert type_change_blocked.status_code == 400

    delete_used = client.delete(f"/api/characteristics/{used_characteristic_id}")
    assert delete_used.status_code == 400

    usage = client.get(f"/api/characteristics/{used_characteristic_id}/usage")
    assert usage.status_code == 200
    assert usage.json()["diagnosis_count"] >= 1


def test_treatments_crud_and_delete_guard(client) -> None:
    create = client.post(
        "/api/treatments",
        json={"name": "Тестовое лечение", "actions": ["Шаг 1", "Шаг 2"]},
    )
    assert create.status_code == 200
    treatment_id = create.json()["id"]

    update = client.put(
        f"/api/treatments/{treatment_id}",
        json={"name": "Тестовое лечение v2", "actions": ["Шаг A", "Шаг B", "Шаг C"]},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Тестовое лечение v2"
    assert update.json()["actions"] == ["Шаг A", "Шаг B", "Шаг C"]

    fetched = client.get(f"/api/treatments/{treatment_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Тестовое лечение v2"

    deleted = client.delete(f"/api/treatments/{treatment_id}")
    assert deleted.status_code == 200

    linked_treatment_id = client.get("/api/diagnoses").json()[0]["treatment_id"]
    blocked = client.delete(f"/api/treatments/{linked_treatment_id}")
    assert blocked.status_code == 400
