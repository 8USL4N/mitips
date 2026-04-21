from dataclasses import dataclass
from typing import Any


@dataclass
class VectorSchema:
    feature_names: list[str]
    index_by_name: dict[str, int]


class FeatureVectorizer:
    def __init__(self) -> None:
        self.schema = VectorSchema(feature_names=[], index_by_name={})
        self._characteristics: dict[int, dict[str, Any]] = {}

    def fit(self, characteristics: list[dict[str, Any]]) -> None:
        self._characteristics = {int(item["id"]): item for item in characteristics}

        feature_names: list[str] = []
        for item in sorted(characteristics, key=lambda row: int(row["id"])):
            characteristic_id = int(item["id"])
            if item["type"] == "range":
                feature_names.append(f"characteristic_{characteristic_id}_value_normalized")
                feature_names.append(f"characteristic_{characteristic_id}_is_missing")
            else:
                allowed = item["allowed"] if isinstance(item["allowed"], dict) else {}
                for key in sorted(allowed.keys()):
                    feature_names.append(f"characteristic_{characteristic_id}_option_{key}")
                feature_names.append(f"characteristic_{characteristic_id}_is_missing")

        self.schema = VectorSchema(
            feature_names=feature_names,
            index_by_name={name: index for index, name in enumerate(feature_names)},
        )

    def transform(self, patient_values: dict[str, Any]) -> list[float]:
        vector = [0.0] * len(self.schema.feature_names)
        for characteristic_id, item in self._characteristics.items():
            key = str(characteristic_id)
            value = patient_values.get(key)

            if item["type"] == "range":
                missing_name = f"characteristic_{characteristic_id}_is_missing"
                missing_index = self.schema.index_by_name[missing_name]
                if value is None:
                    vector[missing_index] = 1.0
                    continue

                raw_min = float(item["allowed"][0])
                raw_max = float(item["allowed"][1])
                value_float = float(value)
                if raw_max == raw_min:
                    normalized = 0.0
                else:
                    normalized = (value_float - raw_min) / (raw_max - raw_min)
                value_name = f"characteristic_{characteristic_id}_value_normalized"
                vector[self.schema.index_by_name[value_name]] = normalized
                vector[missing_index] = 0.0
                continue

            missing_name = f"characteristic_{characteristic_id}_is_missing"
            missing_index = self.schema.index_by_name[missing_name]
            if value is None:
                vector[missing_index] = 1.0
                continue

            selected = str(value)
            allowed = item["allowed"] if isinstance(item["allowed"], dict) else {}
            for option_key in sorted(allowed.keys()):
                name = f"characteristic_{characteristic_id}_option_{option_key}"
                index = self.schema.index_by_name[name]
                vector[index] = 1.0 if selected == option_key else 0.0
            vector[missing_index] = 0.0

        return vector

    def transform_many(self, rows: list[dict[str, Any]]) -> list[list[float]]:
        return [self.transform(item) for item in rows]
