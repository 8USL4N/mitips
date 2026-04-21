from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import TreatmentActionsUpdateRequest, TreatmentRead, TreatmentUpsertRequest
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/treatments", tags=["treatments"])


@router.get("", response_model=list[TreatmentRead])
def list_treatments(session: Session = Depends(get_session)) -> list[TreatmentRead]:
    service = KnowledgeService(session)
    return [TreatmentRead.model_validate(row) for row in service.list_treatments()]


@router.get("/{treatment_id}", response_model=TreatmentRead)
def get_treatment(treatment_id: int, session: Session = Depends(get_session)) -> TreatmentRead:
    service = KnowledgeService(session)
    treatment = service.get_treatment_detail(treatment_id)
    if not treatment:
        raise HTTPException(status_code=404, detail="Лечение не найдено")
    return TreatmentRead.model_validate(treatment)


@router.post("", response_model=TreatmentRead)
def create_treatment(
    payload: TreatmentUpsertRequest,
    session: Session = Depends(get_session),
) -> TreatmentRead:
    service = KnowledgeService(session)
    try:
        created = service.create_treatment(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TreatmentRead.model_validate(created)


@router.put("/{treatment_id}", response_model=TreatmentRead)
def update_treatment(
    treatment_id: int,
    payload: TreatmentUpsertRequest,
    session: Session = Depends(get_session),
) -> TreatmentRead:
    service = KnowledgeService(session)
    try:
        updated = service.update_treatment(treatment_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Лечение не найдено")
    return TreatmentRead.model_validate(updated)


@router.delete("/{treatment_id}")
def delete_treatment(treatment_id: int, session: Session = Depends(get_session)) -> dict[str, str | int]:
    service = KnowledgeService(session)
    try:
        removed = service.delete_treatment(treatment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Лечение не найдено")
    return {"status": "ok", "deleted": treatment_id}


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
