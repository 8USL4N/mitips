from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import (
    CharacteristicCreateRequest,
    CharacteristicRead,
    CharacteristicUpdateRequest,
    CharacteristicUsageRead,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/characteristics", tags=["characteristics"])


@router.get("", response_model=list[CharacteristicRead])
def list_characteristics(session: Session = Depends(get_session)) -> list[CharacteristicRead]:
    service = KnowledgeService(session)
    return [CharacteristicRead.model_validate(row) for row in service.list_characteristics()]


@router.get("/{characteristic_id}", response_model=CharacteristicRead)
def get_characteristic(characteristic_id: int, session: Session = Depends(get_session)) -> CharacteristicRead:
    service = KnowledgeService(session)
    item = service.get_characteristic_detail(characteristic_id)
    if not item:
        raise HTTPException(status_code=404, detail="Характеристика не найдена")
    return CharacteristicRead.model_validate(item)


@router.get("/{characteristic_id}/usage", response_model=CharacteristicUsageRead)
def get_characteristic_usage(
    characteristic_id: int,
    session: Session = Depends(get_session),
) -> CharacteristicUsageRead:
    service = KnowledgeService(session)
    try:
        usage = service.get_characteristic_usage(characteristic_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CharacteristicUsageRead.model_validate(usage)


@router.post("", response_model=CharacteristicRead)
def create_characteristic(
    payload: CharacteristicCreateRequest,
    session: Session = Depends(get_session),
) -> CharacteristicRead:
    service = KnowledgeService(session)
    try:
        created = service.create_characteristic(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CharacteristicRead.model_validate(created)


@router.put("/{characteristic_id}", response_model=CharacteristicRead)
def update_characteristic(
    characteristic_id: int,
    payload: CharacteristicUpdateRequest,
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> CharacteristicRead:
    service = KnowledgeService(session)
    try:
        updated = service.update_characteristic(characteristic_id, payload.model_dump(), force=force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Характеристика не найдена")
    return CharacteristicRead.model_validate(updated)


@router.delete("/{characteristic_id}")
def delete_characteristic(
    characteristic_id: int,
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> dict[str, str | int]:
    service = KnowledgeService(session)
    try:
        deleted = service.delete_characteristic(characteristic_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Характеристика не найдена")
    return {"status": "ok", "deleted": characteristic_id}
