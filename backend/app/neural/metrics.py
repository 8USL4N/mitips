from __future__ import annotations

import numpy as np


def cross_entropy_loss(probabilities: np.ndarray, y_indices: np.ndarray) -> float:
    eps = 1e-12
    row_ids = np.arange(probabilities.shape[0])
    selected = probabilities[row_ids, y_indices]
    return float(-np.mean(np.log(np.clip(selected, eps, 1.0))))


def accuracy(probabilities: np.ndarray, y_indices: np.ndarray) -> float:
    predicted = np.argmax(probabilities, axis=1)
    return float(np.mean(predicted == y_indices))
