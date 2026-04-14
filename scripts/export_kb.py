from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import get_export_path  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.services.knowledge_service import KnowledgeService  # noqa: E402


def main() -> None:
    path = get_export_path()
    with SessionLocal() as session:
        service = KnowledgeService(session)
        service.export_snapshot(path)
    print(f"Exported knowledge snapshot to: {path}")


if __name__ == "__main__":
    main()
