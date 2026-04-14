import json
import threading
from pathlib import Path
from typing import Any

from app.config import get_kb_path
from app.models import KnowledgeBaseSchema

KB_PATH = get_kb_path()
_WRITE_LOCK = threading.RLock()


def _ensure_kb_exists() -> None:
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not KB_PATH.exists():
        empty = {
            "body_systems": {},
            "characteristics": {},
            "diagnoses": {},
            "treatments": {},
        }
        KB_PATH.write_text(json.dumps(empty, ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_integrity(kb: dict[str, Any]) -> None:
    parsed = KnowledgeBaseSchema.model_validate(kb)

    for diagnosis_name, diagnosis in parsed.diagnoses.items():
        if diagnosis.treatment not in parsed.treatments:
            raise ValueError(
                f"Diagnosis '{diagnosis_name}' references missing treatment '{diagnosis.treatment}'"
            )
        for characteristic_name in diagnosis.characteristics.keys():
            if characteristic_name not in parsed.characteristics:
                raise ValueError(
                    f"Diagnosis '{diagnosis_name}' references missing characteristic "
                    f"'{characteristic_name}'"
                )


def load_kb() -> dict[str, Any]:
    _ensure_kb_exists()
    raw = KB_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)
    _validate_integrity(data)
    return data


def save_kb(data: dict[str, Any]) -> None:
    _validate_integrity(data)
    _ensure_kb_exists()

    tmp_path = Path(f"{KB_PATH}.tmp")
    backup_path = Path(f"{KB_PATH}.bak")

    with _WRITE_LOCK:
        payload = json.dumps(data, ensure_ascii=False, indent=2)

        if KB_PATH.exists():
            backup_path.write_text(KB_PATH.read_text(encoding="utf-8"), encoding="utf-8")

        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(KB_PATH)
