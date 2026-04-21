from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from app.config import get_model_data_path
from app.neural.feature_vectorizer import FeatureVectorizer
from app.neural.metrics import accuracy, cross_entropy_loss
from app.neural.model_store import load_model, save_model
from app.neural.neural_network import FeedForwardNeuralNetwork
from app.neural.synthetic_training import generate_synthetic_cases


def _canonical_characteristics(characteristics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in characteristics:
        characteristic_id = int(item["id"])
        characteristic_type = str(item["type"])
        allowed: list[float] | dict[str, str]
        normal: list[float] | str
        if characteristic_type == "range":
            allowed = [float(item["allowed"][0]), float(item["allowed"][1])]
            normal = [float(item["normal"][0]), float(item["normal"][1])]
        else:
            raw_allowed = item["allowed"] if isinstance(item["allowed"], dict) else {}
            allowed = {str(key): str(raw_allowed[key]) for key in sorted(raw_allowed.keys())}
            normal = str(item["normal"])

        rows.append(
            {
                "id": characteristic_id,
                "name": str(item.get("name", "")),
                "type": characteristic_type,
                "unit": str(item.get("unit", "") or ""),
                "allowed": allowed,
                "normal": normal,
            }
        )

    rows.sort(key=lambda row: row["id"])
    return rows


def _canonical_diagnoses(diagnoses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    for diagnosis in diagnoses:
        criteria_rows = []
        for criterion in diagnosis.get("criteria", []):
            criteria_rows.append(
                {
                    "characteristic_id": int(criterion["characteristic_id"]),
                    "characteristic_type": str(criterion["characteristic_type"]),
                    "expected_enum_key": (
                        None
                        if criterion.get("expected_enum_key") is None
                        else str(criterion.get("expected_enum_key"))
                    ),
                    "expected_min": (
                        None
                        if criterion.get("expected_min") is None
                        else float(criterion.get("expected_min"))
                    ),
                    "expected_max": (
                        None
                        if criterion.get("expected_max") is None
                        else float(criterion.get("expected_max"))
                    ),
                }
            )
        criteria_rows.sort(key=lambda row: row["characteristic_id"])

        canonical.append(
            {
                "id": int(diagnosis["id"]),
                "name": str(diagnosis.get("name", "")),
                "criteria": criteria_rows,
            }
        )

    canonical.sort(key=lambda row: row["id"])
    return canonical


def canonical_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    characteristics = _canonical_characteristics(snapshot.get("characteristics", []))
    diagnoses = _canonical_diagnoses(snapshot.get("diagnoses", []))
    return {
        "characteristics": characteristics,
        "diagnoses": diagnoses,
    }


def knowledge_hash(snapshot: dict[str, Any]) -> str:
    payload = canonical_snapshot(snapshot)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class NeuralDiagnosisRanker:
    def __init__(
        self,
        *,
        hidden_size: int = 16,
        learning_rate: float = 0.05,
        epochs: int = 1500,
        samples_per_diagnosis: int = 200,
        missing_prob: float = 0.2,
        normal_fill_prob: float = 0.35,
        noise_prob: float = 0.05,
        seed: int = 42,
    ) -> None:
        self.hidden_size = int(hidden_size)
        self.learning_rate = float(learning_rate)
        self.epochs = int(epochs)
        self.samples_per_diagnosis = int(samples_per_diagnosis)
        self.missing_prob = float(missing_prob)
        self.normal_fill_prob = float(normal_fill_prob)
        self.noise_prob = float(noise_prob)
        self.seed = int(seed)

        self._network: FeedForwardNeuralNetwork | None = None
        self._vectorizer: FeatureVectorizer | None = None
        self._diagnosis_ids: list[int] = []
        self._diagnosis_name_by_id: dict[int, str] = {}
        self._knowledge_hash = ""

    @staticmethod
    def _diagnosis_ids_and_names(diagnoses: list[dict[str, Any]]) -> tuple[list[int], dict[int, str]]:
        ids = sorted(int(item["id"]) for item in diagnoses)
        names = {int(item["id"]): str(item.get("name", "")) for item in diagnoses}
        return ids, names

    @staticmethod
    def _model_payload_compatible(
        payload: dict[str, Any],
        *,
        expected_hash: str,
        expected_features: list[str],
        expected_diagnosis_ids: list[int],
    ) -> bool:
        if payload.get("model_type") != "feed_forward_neural_network":
            return False
        if payload.get("knowledge_hash") != expected_hash:
            return False

        stored_features = list(payload.get("input_features", []))
        if stored_features != expected_features:
            return False

        stored_diagnosis_ids = [int(item) for item in payload.get("diagnosis_ids", [])]
        if stored_diagnosis_ids != expected_diagnosis_ids:
            return False

        weights = payload.get("weights", {})
        required_keys = {"input_hidden", "hidden_bias", "hidden_output", "output_bias"}
        if not isinstance(weights, dict) or not required_keys.issubset(weights.keys()):
            return False
        return True

    def _load_from_payload(
        self,
        payload: dict[str, Any],
        vectorizer: FeatureVectorizer,
        diagnosis_ids: list[int],
        diagnosis_name_by_id: dict[int, str],
    ) -> None:
        architecture = payload.get("architecture", {})
        network_payload = {
            "input_size": int(architecture["input_size"]),
            "hidden_size": int(architecture["hidden_size"]),
            "output_size": int(architecture["output_size"]),
            "learning_rate": float(payload.get("training", {}).get("learning_rate", self.learning_rate)),
            "seed": int(payload.get("training", {}).get("seed", self.seed)),
            "weights": payload["weights"],
        }
        network = FeedForwardNeuralNetwork.from_dict(network_payload)

        self._network = network
        self._vectorizer = vectorizer
        self._diagnosis_ids = list(diagnosis_ids)
        self._diagnosis_name_by_id = dict(diagnosis_name_by_id)
        self._knowledge_hash = str(payload["knowledge_hash"])

    def _train_and_store(
        self,
        snapshot: dict[str, Any],
        *,
        vectorizer: FeatureVectorizer,
        diagnosis_ids: list[int],
        diagnosis_name_by_id: dict[int, str],
        current_hash: str,
    ) -> None:
        characteristics = snapshot["characteristics"]
        diagnoses = snapshot["diagnoses"]
        characteristic_map = {int(item["id"]): item for item in characteristics}

        rows, labels = generate_synthetic_cases(
            diagnoses=diagnoses,
            characteristic_map=characteristic_map,
            samples_per_diagnosis=self.samples_per_diagnosis,
            missing_prob=self.missing_prob,
            normal_fill_prob=self.normal_fill_prob,
            noise_prob=self.noise_prob,
            seed=self.seed,
        )
        if not rows or not diagnosis_ids:
            self._network = None
            self._vectorizer = vectorizer
            self._diagnosis_ids = list(diagnosis_ids)
            self._diagnosis_name_by_id = dict(diagnosis_name_by_id)
            self._knowledge_hash = current_hash
            return

        label_to_index = {diagnosis_id: idx for idx, diagnosis_id in enumerate(diagnosis_ids)}
        x_train = np.asarray(vectorizer.transform_many(rows), dtype=np.float64)
        y_train = np.asarray([label_to_index[int(label)] for label in labels], dtype=np.int64)

        network = FeedForwardNeuralNetwork(
            input_size=x_train.shape[1],
            hidden_size=self.hidden_size,
            output_size=len(diagnosis_ids),
            learning_rate=self.learning_rate,
            seed=self.seed,
        )
        train_result = network.train(x_train, y_train, epochs=self.epochs)
        train_probabilities = network.predict_proba(x_train)
        train_accuracy = accuracy(train_probabilities, y_train)
        final_loss = cross_entropy_loss(train_probabilities, y_train)

        network_dict = network.to_dict()
        model_payload = {
            "model_type": "feed_forward_neural_network",
            "architecture": {
                "input_size": int(network_dict["input_size"]),
                "hidden_size": int(network_dict["hidden_size"]),
                "output_size": int(network_dict["output_size"]),
                "hidden_activation": "tanh",
                "output_activation": "softmax",
            },
            "knowledge_hash": current_hash,
            "input_features": vectorizer.get_feature_names(),
            "diagnosis_ids": diagnosis_ids,
            "diagnosis_names": [diagnosis_name_by_id[item] for item in diagnosis_ids],
            "training": {
                "samples_per_diagnosis": self.samples_per_diagnosis,
                "epochs": train_result.epochs,
                "learning_rate": self.learning_rate,
                "seed": self.seed,
                "train_accuracy": float(train_accuracy),
                "initial_loss": float(train_result.initial_loss),
                "final_loss": float(final_loss),
            },
            "weights": network_dict["weights"],
        }
        save_model(get_model_data_path(), model_payload)

        self._network = network
        self._vectorizer = vectorizer
        self._diagnosis_ids = list(diagnosis_ids)
        self._diagnosis_name_by_id = dict(diagnosis_name_by_id)
        self._knowledge_hash = current_hash

    def ensure_fitted(self, knowledge_snapshot: dict[str, Any]) -> None:
        snapshot = canonical_snapshot(knowledge_snapshot)
        current_hash = knowledge_hash(snapshot)
        diagnoses = snapshot["diagnoses"]
        diagnosis_ids, diagnosis_name_by_id = self._diagnosis_ids_and_names(diagnoses)

        vectorizer = FeatureVectorizer()
        vectorizer.fit(snapshot["characteristics"])
        current_feature_names = vectorizer.get_feature_names()

        if (
            self._network is not None
            and self._knowledge_hash == current_hash
            and self._diagnosis_ids == diagnosis_ids
            and self._vectorizer is not None
            and self._vectorizer.get_feature_names() == current_feature_names
        ):
            return

        model_payload = load_model(get_model_data_path())
        if model_payload and self._model_payload_compatible(
            model_payload,
            expected_hash=current_hash,
            expected_features=current_feature_names,
            expected_diagnosis_ids=diagnosis_ids,
        ):
            self._load_from_payload(model_payload, vectorizer, diagnosis_ids, diagnosis_name_by_id)
            return

        self._train_and_store(
            snapshot,
            vectorizer=vectorizer,
            diagnosis_ids=diagnosis_ids,
            diagnosis_name_by_id=diagnosis_name_by_id,
            current_hash=current_hash,
        )

    def rank(
        self,
        patient_values: dict[str, Any],
        candidate_ids: list[int],
        knowledge_snapshot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        self.ensure_fitted(knowledge_snapshot)

        if not candidate_ids:
            return []
        if self._network is None or self._vectorizer is None or not self._diagnosis_ids:
            return []

        vector = np.asarray([self._vectorizer.transform(patient_values)], dtype=np.float64)
        probabilities = self._network.predict_proba(vector)[0]
        probability_by_diagnosis_id = {
            diagnosis_id: float(probabilities[index])
            for index, diagnosis_id in enumerate(self._diagnosis_ids)
        }

        ranked = [
            {
                "diagnosis_id": int(diagnosis_id),
                "probability": float(probability_by_diagnosis_id.get(int(diagnosis_id), 0.0)),
                "model_score": float(probability_by_diagnosis_id.get(int(diagnosis_id), 0.0)),
            }
            for diagnosis_id in candidate_ids
        ]

        total = sum(item["probability"] for item in ranked)
        if total <= 0:
            return []

        for item in ranked:
            item["probability"] = float(item["probability"] / total)
            item["model_score"] = item["probability"]

        ranked.sort(key=lambda row: (row["probability"], row["diagnosis_id"]), reverse=True)
        return ranked
