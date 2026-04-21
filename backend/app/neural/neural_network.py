from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class TrainResult:
    initial_loss: float
    final_loss: float
    epochs: int


class FeedForwardNeuralNetwork:
    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        output_size: int,
        learning_rate: float = 0.05,
        seed: int = 42,
    ) -> None:
        self.input_size = int(input_size)
        self.hidden_size = int(hidden_size)
        self.output_size = int(output_size)
        self.learning_rate = float(learning_rate)
        self.seed = int(seed)

        rng = np.random.default_rng(self.seed)
        self.W1 = rng.normal(0.0, 0.08, size=(self.input_size, self.hidden_size))
        self.b1 = np.zeros(self.hidden_size, dtype=np.float64)
        self.W2 = rng.normal(0.0, 0.08, size=(self.hidden_size, self.output_size))
        self.b2 = np.zeros(self.output_size, dtype=np.float64)

    @staticmethod
    def _as_matrix(x: np.ndarray | list[list[float]] | list[float]) -> np.ndarray:
        array = np.asarray(x, dtype=np.float64)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        if array.ndim != 2:
            raise ValueError("Input must be a 1D or 2D array-like structure")
        return array

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits, axis=1, keepdims=True)
        exp = np.exp(shifted)
        denom = np.sum(exp, axis=1, keepdims=True)
        return exp / np.clip(denom, 1e-12, None)

    @staticmethod
    def _cross_entropy(probabilities: np.ndarray, y_indices: np.ndarray) -> float:
        eps = 1e-12
        row_ids = np.arange(probabilities.shape[0])
        selected = probabilities[row_ids, y_indices]
        return float(-np.mean(np.log(np.clip(selected, eps, 1.0))))

    def forward(self, x: np.ndarray | list[list[float]] | list[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        matrix = self._as_matrix(x)
        hidden_raw = matrix @ self.W1 + self.b1
        hidden = np.tanh(hidden_raw)
        logits = hidden @ self.W2 + self.b2
        probabilities = self._softmax(logits)
        return hidden, logits, probabilities

    def predict_proba(self, x: np.ndarray | list[list[float]] | list[float]) -> np.ndarray:
        _, _, probabilities = self.forward(x)
        return probabilities

    def train(
        self,
        x_train: np.ndarray | list[list[float]],
        y_train: np.ndarray | list[int],
        epochs: int = 1500,
    ) -> TrainResult:
        x_matrix = self._as_matrix(x_train)
        y_indices = np.asarray(y_train, dtype=np.int64)

        if x_matrix.shape[0] == 0:
            return TrainResult(initial_loss=0.0, final_loss=0.0, epochs=0)
        if x_matrix.shape[1] != self.input_size:
            raise ValueError("x_train shape does not match input_size")
        if y_indices.shape[0] != x_matrix.shape[0]:
            raise ValueError("x_train and y_train must contain the same number of samples")
        if np.any(y_indices < 0) or np.any(y_indices >= self.output_size):
            raise ValueError("y_train contains class ids out of range")

        _, _, initial_probabilities = self.forward(x_matrix)
        initial_loss = self._cross_entropy(initial_probabilities, y_indices)

        for _ in range(int(epochs)):
            hidden, _, probabilities = self.forward(x_matrix)

            d_logits = probabilities.copy()
            row_ids = np.arange(x_matrix.shape[0])
            d_logits[row_ids, y_indices] -= 1.0
            d_logits /= x_matrix.shape[0]

            dW2 = hidden.T @ d_logits
            db2 = np.sum(d_logits, axis=0)

            d_hidden = d_logits @ self.W2.T
            d_hidden_raw = d_hidden * (1.0 - np.square(hidden))

            dW1 = x_matrix.T @ d_hidden_raw
            db1 = np.sum(d_hidden_raw, axis=0)

            self.W1 -= self.learning_rate * dW1
            self.b1 -= self.learning_rate * db1
            self.W2 -= self.learning_rate * dW2
            self.b2 -= self.learning_rate * db2

        _, _, final_probabilities = self.forward(x_matrix)
        final_loss = self._cross_entropy(final_probabilities, y_indices)
        return TrainResult(
            initial_loss=float(initial_loss),
            final_loss=float(final_loss),
            epochs=int(epochs),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_size": self.input_size,
            "hidden_size": self.hidden_size,
            "output_size": self.output_size,
            "learning_rate": self.learning_rate,
            "seed": self.seed,
            "weights": {
                "input_hidden": self.W1.tolist(),
                "hidden_bias": self.b1.tolist(),
                "hidden_output": self.W2.tolist(),
                "output_bias": self.b2.tolist(),
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FeedForwardNeuralNetwork":
        network = cls(
            input_size=int(payload["input_size"]),
            hidden_size=int(payload["hidden_size"]),
            output_size=int(payload["output_size"]),
            learning_rate=float(payload.get("learning_rate", 0.05)),
            seed=int(payload.get("seed", 42)),
        )
        weights = payload.get("weights", {})
        network.W1 = np.asarray(weights["input_hidden"], dtype=np.float64)
        network.b1 = np.asarray(weights["hidden_bias"], dtype=np.float64)
        network.W2 = np.asarray(weights["hidden_output"], dtype=np.float64)
        network.b2 = np.asarray(weights["output_bias"], dtype=np.float64)
        return network
