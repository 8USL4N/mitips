"""Application configuration helpers."""

from pathlib import Path
import os


DEFAULT_KB_PATH = Path("/app/data/knowledge_base.json")


def get_kb_path() -> Path:
    raw = os.getenv("KB_PATH")
    if raw:
        return Path(raw)
    return DEFAULT_KB_PATH
