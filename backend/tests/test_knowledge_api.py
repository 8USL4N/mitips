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
