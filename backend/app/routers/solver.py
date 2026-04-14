from fastapi import APIRouter, HTTPException

from app.models import SolveRequest, SolveResponse
from app.solver import rank_all, solve_validate_selected

router = APIRouter(prefix="/api/solver", tags=["solver"])


@router.post("/solve", response_model=SolveResponse)
def solve_task(payload: SolveRequest) -> SolveResponse:
    try:
        result = solve_validate_selected(payload.diagnosis, payload.patient_values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SolveResponse.model_validate(result)


@router.post("/rank")
def rank_task(payload: SolveRequest) -> dict[str, list[dict]]:
    ranked = rank_all(payload.patient_values)
    return {"items": ranked[:3]}
