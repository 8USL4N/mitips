"""Application configuration helpers."""

from pathlib import Path
import os


DEFAULT_SEED_PATH = Path("/app/data/knowledge_base.json")
DEFAULT_EXPORT_PATH = Path("/app/data/knowledge_base.export.json")
DEFAULT_DATABASE_URL = "sqlite:///./expert.db"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_seed_path() -> Path:
    raw = os.getenv("KB_SEED_PATH")
    if raw:
        return Path(raw)
    return DEFAULT_SEED_PATH


def get_export_path() -> Path:
    raw = os.getenv("KB_EXPORT_PATH")
    if raw:
        return Path(raw)
    return DEFAULT_EXPORT_PATH
