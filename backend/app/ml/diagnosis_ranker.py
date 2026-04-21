import hashlib
import json
from typing import Any

from app.ml.feature_vectorizer import FeatureVectorizer
from app.ml.synthetic_training import generate_synthetic_cases

try:
    from sklearn.ensemble import RandomForestClassifier
except Exception:  # pragma: no cover - fallback for environments without sklearn
    RandomForestClassifier = None


def knowledge_hash(snapshot: dict[str, Any]) -> str:
    payload = {
        "characteristics": snapshot.get("characteristics", []),
        "diagnoses": [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "criteria": row.get("criteria", []),
            }
            for row in snapshot.get("diagnoses", [])
        ],
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class DiagnosisRanker:
    def __init__(self) -> None:
        self._vectorizer = FeatureVectorizer()
        self._model: Any = None
        self._classes: list[int] = []
        self._snapshot_hash = ""

    def fit(self, knowledge_snapshot: dict[str, Any]) -> None:
        characteristics = knowledge_snapshot.get("characteristics", [])
        diagnoses = knowledge_snapshot.get("diagnoses", [])
        characteristic_map = {int(item["id"]): item for item in characteristics}

        self._vectorizer.fit(characteristics)
        train_rows, train_labels = generate_synthetic_cases(
            diagnoses=diagnoses,
            characteristic_map=characteristic_map,
        )

        self._model = None
        self._classes = sorted(set(int(item) for item in train_labels))
        if train_rows and len(self._classes) > 1 and RandomForestClassifier is not None:
            matrix = self._vectorizer.transform_many(train_rows)
            model = RandomForestClassifier(
                n_estimators=120,
                random_state=42,
                min_samples_leaf=1,
            )
            model.fit(matrix, train_labels)
            self._model = model

        self._snapshot_hash = knowledge_hash(knowledge_snapshot)

    def ensure_fitted(self, knowledge_snapshot: dict[str, Any]) -> None:
        current_hash = knowledge_hash(knowledge_snapshot)
        if self._snapshot_hash != current_hash:
            self.fit(knowledge_snapshot)

    @staticmethod
    def _fallback_score(
        diagnosis: dict[str, Any],
        patient_values: dict[str, Any],
    ) -> float:
        criteria_by_id = {int(item["characteristic_id"]): item for item in diagnosis.get("criteria", [])}
        matched = 0.0
        checked = 0.0
        for key, value in patient_values.items():
            if value is None:
                continue
            characteristic_id = int(key)
            criterion = criteria_by_id.get(characteristic_id)
            if not criterion:
                continue
            checked += 1.0
            if criterion["characteristic_type"] == "range":
                try:
                    v = float(value)
                    v_min = float(criterion["expected_min"])
                    v_max = float(criterion["expected_max"])
                except (TypeError, ValueError):
                    continue
                if v_min <= v <= v_max:
                    matched += 1.0
            else:
                if str(value) == str(criterion["expected_enum_key"]):
                    matched += 1.0

        if checked == 0:
            return 0.0
        return matched / checked

    def rank(
        self,
        patient_values: dict[str, Any],
        candidate_ids: list[int],
        knowledge_snapshot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        self.ensure_fitted(knowledge_snapshot)

        if not candidate_ids:
            return []

        diagnosis_by_id = {
            int(item["id"]): item
            for item in knowledge_snapshot.get("diagnoses", [])
        }
        candidates = [diagnosis_by_id[item] for item in candidate_ids if item in diagnosis_by_id]
        if not candidates:
            return []

        if self._model is not None:
            vector = self._vectorizer.transform(patient_values)
            proba = self._model.predict_proba([vector])[0]
            class_to_proba = {
                int(class_id): float(score)
                for class_id, score in zip(self._model.classes_, proba)
            }
            ranked = [
                {
                    "diagnosis_id": int(item["id"]),
                    "probability": class_to_proba.get(int(item["id"]), 0.0),
                    "model_score": class_to_proba.get(int(item["id"]), 0.0),
                }
                for item in candidates
            ]
        else:
            ranked = []
            for item in candidates:
                score = self._fallback_score(item, patient_values)
                ranked.append(
                    {
                        "diagnosis_id": int(item["id"]),
                        "probability": float(score),
                        "model_score": float(score),
                    }
                )

        ranked.sort(key=lambda row: (row["probability"], row["diagnosis_id"]), reverse=True)
        total = sum(item["probability"] for item in ranked)
        if total > 0:
            for item in ranked:
                item["probability"] = float(item["probability"] / total)

        return ranked
