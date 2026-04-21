import pathlib


def test_no_sklearn_or_random_forest_used() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    app_files = list((root / "app").rglob("*.py"))
    content = "\n".join(path.read_text(encoding="utf-8") for path in app_files)

    assert "RandomForestClassifier" not in content
    assert "sklearn" not in content

    requirements = (root / "requirements.txt").read_text(encoding="utf-8-sig")
    assert "scikit-learn" not in requirements
    assert "sklearn" not in requirements
