from fastapi import APIRouter, HTTPException

from app.knowledge import load_kb, save_kb
from app.models import DiagnosisUpsertRequest, TreatmentUpdateRequest

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/")
def get_knowledge_base() -> dict:
    return load_kb()


@router.get("/diagnoses")
def get_diagnoses() -> dict:
    return load_kb()["diagnoses"]


@router.get("/characteristics")
def get_characteristics() -> dict:
    return load_kb()["characteristics"]


@router.get("/treatments")
def get_treatments() -> dict:
    return load_kb()["treatments"]


@router.post("/diagnoses/{name}")
def add_diagnosis(name: str, data: DiagnosisUpsertRequest) -> dict:
    kb = load_kb()
    if name in kb["diagnoses"]:
        raise HTTPException(status_code=409, detail="Диагноз уже существует")

    kb["diagnoses"][name] = data.model_dump()
    save_kb(kb)
    return {"status": "ok", "created": name}


@router.put("/diagnoses/{name}")
def update_diagnosis(name: str, data: DiagnosisUpsertRequest) -> dict:
    kb = load_kb()
    if name not in kb["diagnoses"]:
        raise HTTPException(status_code=404, detail="Диагноз не найден")

    kb["diagnoses"][name] = data.model_dump()
    save_kb(kb)
    return {"status": "ok", "updated": name}


@router.delete("/diagnoses/{name}")
def delete_diagnosis(name: str) -> dict:
    kb = load_kb()
    if name not in kb["diagnoses"]:
        raise HTTPException(status_code=404, detail="Диагноз не найден")

    del kb["diagnoses"][name]
    save_kb(kb)
    return {"status": "ok", "deleted": name}


@router.put("/treatments/{name}")
def update_treatment(name: str, payload: TreatmentUpdateRequest) -> dict:
    kb = load_kb()
    kb["treatments"][name] = payload.actions
    save_kb(kb)
    return {"status": "ok", "updated": name}
