from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import SolveBySymptomsRequest, SolveBySymptomsResponse, SolveRequest, SolveResponse
from app.solver import solve_by_symptoms, solve_validate_selected

router = APIRouter(prefix="/api/solver", tags=["solver"])


@router.post("/solve", response_model=SolveResponse)
def solve_task(
    payload: SolveRequest,
    session: Session = Depends(get_session),
) -> SolveResponse:
    try:
        result = solve_validate_selected(session, payload.diagnosis_id, payload.patient_values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SolveResponse.model_validate(result)


@router.post("/determine", response_model=SolveBySymptomsResponse)
def determine_task(
    payload: SolveBySymptomsRequest,
    session: Session = Depends(get_session),
) -> SolveBySymptomsResponse:
    try:
        result = solve_by_symptoms(session, payload.patient_values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SolveBySymptomsResponse.model_validate(result)
