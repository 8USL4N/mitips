from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "export_kb.py"), run_name="__main__")