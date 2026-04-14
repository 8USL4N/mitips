from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import CharacteristicRead
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/characteristics", tags=["characteristics"])


@router.get("", response_model=list[CharacteristicRead])
def list_characteristics(session: Session = Depends(get_session)) -> list[CharacteristicRead]:
    service = KnowledgeService(session)
    return [CharacteristicRead.model_validate(row) for row in service.list_characteristics()]
