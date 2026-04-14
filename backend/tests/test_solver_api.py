from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from app import knowledge


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    source = Path(__file__).resolve().parents[1] / "data" / "knowledge_base.json"
    target = tmp_path / "knowledge_base.json"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(knowledge, "KB_PATH", target)
    return TestClient(main.app)


def test_solve_endpoint_success(client: TestClient) -> None:
    response = client.post(
        "/api/solver/solve",
        json={
            "diagnosis": "Холера",
            "patient_values": {
                "Температура тела": 36.5,
                "Характер стула": "1",
                "Боль в животе": "0",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["diagnosis"] == "Холера"
    assert payload["matched_count"] == payload["total_count"]


def test_add_and_delete_diagnosis(client: TestClient) -> None:
    diagnosis = {
        "icd10": "Z99",
        "characteristics": {"Кашель": "1"},
        "treatment": "Лечение не требуется",
    }

    created = client.post("/api/knowledge/diagnoses/Тестовый", json=diagnosis)
    assert created.status_code == 200

    deleted = client.delete("/api/knowledge/diagnoses/Тестовый")
    assert deleted.status_code == 200
