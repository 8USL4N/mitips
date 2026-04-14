from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import knowledge, solver

app = FastAPI(title="Expert System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solver.router)
app.include_router(knowledge.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "message": "Expert System API is running"}
