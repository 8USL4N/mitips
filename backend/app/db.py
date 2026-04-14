from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_database_url


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


SessionLocal = sessionmaker(autocommit=False, autoflush=False, future=True)
engine = create_engine(get_database_url(), future=True, pool_pre_ping=True, connect_args=_connect_args(get_database_url()))
SessionLocal.configure(bind=engine)


def reconfigure_engine(database_url: str) -> None:
    global engine
    engine.dispose()
    engine = create_engine(database_url, future=True, pool_pre_ping=True, connect_args=_connect_args(database_url))
    SessionLocal.configure(bind=engine)


def get_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
