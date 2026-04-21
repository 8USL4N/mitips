import numpy as np

from app.neural.neural_network import FeedForwardNeuralNetwork


def test_neural_network_predict_proba_sums_to_one() -> None:
    network = FeedForwardNeuralNetwork(
        input_size=4,
        hidden_size=3,
        output_size=2,
        seed=42,
    )

    probabilities = network.predict_proba([0.0, 1.0, 0.0, 1.0])[0]

    assert len(probabilities) == 2
    assert abs(float(np.sum(probabilities)) - 1.0) < 1e-6


def test_neural_network_train_reduces_loss() -> None:
    x_train = np.asarray(
        [
            [0.0, 0.0],
            [0.0, 1.0],
            [1.0, 0.0],
            [1.0, 1.0],
        ],
        dtype=np.float64,
    )
    y_train = np.asarray([0, 1, 1, 0], dtype=np.int64)

    network = FeedForwardNeuralNetwork(
        input_size=2,
        hidden_size=4,
        output_size=2,
        learning_rate=0.1,
        seed=42,
    )
    result = network.train(x_train, y_train, epochs=400)

    assert result.final_loss < result.initial_loss


def test_neural_network_to_dict_from_dict_restores_weights() -> None:
    network = FeedForwardNeuralNetwork(
        input_size=3,
        hidden_size=5,
        output_size=2,
        seed=7,
    )

    payload = network.to_dict()
    restored = FeedForwardNeuralNetwork.from_dict(payload)

    assert np.allclose(network.W1, restored.W1)
    assert np.allclose(network.b1, restored.b1)
    assert np.allclose(network.W2, restored.W2)
    assert np.allclose(network.b2, restored.b2)
