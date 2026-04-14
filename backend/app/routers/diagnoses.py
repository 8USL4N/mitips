from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import DiagnosisDetailRead, DiagnosisSummaryRead, DiagnosisUpsertRequest
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/diagnoses", tags=["diagnoses"])


@router.get("", response_model=list[DiagnosisSummaryRead])
def list_diagnoses(session: Session = Depends(get_session)) -> list[DiagnosisSummaryRead]:
    service = KnowledgeService(session)
    return [DiagnosisSummaryRead.model_validate(row) for row in service.list_diagnoses()]


@router.get("/{diagnosis_id}", response_model=DiagnosisDetailRead)
def get_diagnosis(diagnosis_id: int, session: Session = Depends(get_session)) -> DiagnosisDetailRead:
    service = KnowledgeService(session)
    diagnosis = service.get_diagnosis_detail(diagnosis_id)
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Диагноз не найден")
    return DiagnosisDetailRead.model_validate(diagnosis)


@router.post("", response_model=DiagnosisDetailRead)
def create_diagnosis(
    payload: DiagnosisUpsertRequest,
    session: Session = Depends(get_session),
) -> DiagnosisDetailRead:
    service = KnowledgeService(session)
    try:
        created = service.create_diagnosis(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DiagnosisDetailRead.model_validate(created)


@router.put("/{diagnosis_id}", response_model=DiagnosisDetailRead)
def update_diagnosis(
    diagnosis_id: int,
    payload: DiagnosisUpsertRequest,
    session: Session = Depends(get_session),
) -> DiagnosisDetailRead:
    service = KnowledgeService(session)
    try:
        updated = service.update_diagnosis(diagnosis_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not updated:
        raise HTTPException(status_code=404, detail="Диагноз не найден")

    return DiagnosisDetailRead.model_validate(updated)


@router.delete("/{diagnosis_id}")
def delete_diagnosis(diagnosis_id: int, session: Session = Depends(get_session)) -> dict[str, str | int]:
    service = KnowledgeService(session)
    removed = service.delete_diagnosis(diagnosis_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Диагноз не найден")
    return {"status": "ok", "deleted": diagnosis_id}
