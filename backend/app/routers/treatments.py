from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import TreatmentActionsUpdateRequest, TreatmentRead
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/treatments", tags=["treatments"])


@router.get("", response_model=list[TreatmentRead])
def list_treatments(session: Session = Depends(get_session)) -> list[TreatmentRead]:
    service = KnowledgeService(session)
    return [TreatmentRead.model_validate(row) for row in service.list_treatments()]


@router.put("/{treatment_id}/actions", response_model=TreatmentRead)
def update_treatment_actions(
    treatment_id: int,
    payload: TreatmentActionsUpdateRequest,
    session: Session = Depends(get_session),
) -> TreatmentRead:
    service = KnowledgeService(session)
    try:
        updated = service.update_treatment_actions(treatment_id, payload.actions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Лечение не найдено")
    return TreatmentRead.model_validate(updated)
