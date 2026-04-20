from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import BodySystemRead, BodySystemUpsertRequest
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/body-systems", tags=["body-systems"])


@router.get("", response_model=list[BodySystemRead])
def list_body_systems(session: Session = Depends(get_session)) -> list[BodySystemRead]:
    service = KnowledgeService(session)
    return [BodySystemRead.model_validate(item) for item in service.list_body_systems()]


@router.post("", response_model=BodySystemRead)
def create_body_system(
    payload: BodySystemUpsertRequest,
    session: Session = Depends(get_session),
) -> BodySystemRead:
    service = KnowledgeService(session)
    try:
        created = service.create_body_system(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BodySystemRead.model_validate(created)


@router.put("/{body_system_id}", response_model=BodySystemRead)
def update_body_system(
    body_system_id: int,
    payload: BodySystemUpsertRequest,
    session: Session = Depends(get_session),
) -> BodySystemRead:
    service = KnowledgeService(session)
    try:
        updated = service.update_body_system(body_system_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not updated:
        raise HTTPException(status_code=404, detail="Система организма не найдена")
    return BodySystemRead.model_validate(updated)


@router.delete("/{body_system_id}")
def delete_body_system(
    body_system_id: int,
    session: Session = Depends(get_session),
) -> dict[str, str | int]:
    service = KnowledgeService(session)
    removed = service.delete_body_system(body_system_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Система организма не найдена")
    return {"status": "ok", "deleted": body_system_id}
