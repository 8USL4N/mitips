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


def test_update_treatment_actions_persists(client) -> None:
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        treatment = next(item for item in service.list_treatments() if item["name"] == "Лечение холеры")
        original_actions = treatment["actions"]

        updated = service.update_treatment_actions(treatment["id"], [*original_actions, "Тестовый шаг"])
        assert updated is not None
        assert updated["actions"][-1] == "Тестовый шаг"

        restored = service.update_treatment_actions(treatment["id"], original_actions)
        assert restored is not None
        assert restored["actions"] == original_actions


def test_body_systems_crud(client) -> None:
    characteristics = client.get("/api/characteristics").json()
    temp = next(item for item in characteristics if item["name"] == "Температура тела")
    cough = next(item for item in characteristics if item["name"] == "Кашель")

    list_response = client.get("/api/body-systems")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 5

    created = client.post(
        "/api/body-systems",
        json={"name": "Тестовая система", "characteristic_ids": [temp["id"]]},
    )
    assert created.status_code == 200
    body_system_id = created.json()["id"]
    assert created.json()["characteristic_ids"] == [temp["id"]]

    updated = client.put(
        f"/api/body-systems/{body_system_id}",
        json={"name": "Тестовая система 2", "characteristic_ids": [temp["id"], cough["id"]]},
    )
    assert updated.status_code == 200
    assert sorted(updated.json()["characteristic_ids"]) == sorted([temp["id"], cough["id"]])

    deleted = client.delete(f"/api/body-systems/{body_system_id}")
    assert deleted.status_code == 200
