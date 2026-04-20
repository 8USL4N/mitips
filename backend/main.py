from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_seed_path
from app.orm import Base
from app.routers import body_systems, characteristics, diagnoses, solver, treatments
from app.services.knowledge_service import KnowledgeService

app = FastAPI(title="Expert System API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnoses.router)
app.include_router(characteristics.router)
app.include_router(treatments.router)
app.include_router(body_systems.router)
app.include_router(solver.router)


@app.on_event("startup")
def startup() -> None:
    # Backup safety for tests/local runs if migrations were not applied yet.
    Base.metadata.create_all(bind=db.engine)
    with db.SessionLocal() as session:
        service = KnowledgeService(session)
        service.seed_from_json_if_empty(get_seed_path())


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "message": "Expert System API is running"}
