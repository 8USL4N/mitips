from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.orm import Base
from app.services.knowledge_service import KnowledgeService
import main


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test.sqlite3"
    db_url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    db.reconfigure_engine(db_url)
    Base.metadata.drop_all(bind=db.engine)
    Base.metadata.create_all(bind=db.engine)

    seed_path = Path(__file__).resolve().parents[1] / "data" / "knowledge_base.json"
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        service.seed_from_json_if_empty(seed_path)

    with TestClient(main.app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=db.engine)
