"""Unit tests for the LSTM regression model."""

import numpy as np
import pytest
import torch

from src.lstm_model import (
    DEFAULT_LSTM_PARAMETERS,
    LSTMRegressor,
    build_lstm_sequences,
    create_lstm_regression_model,
)


def test_default_model_parameters():
    model = create_lstm_regression_model()

    assert isinstance(model, LSTMRegressor)
    assert model.input_size == 7
    assert model.hidden_size == 32
    assert model.num_layers == 1
    assert model.dropout == 0.0
    assert DEFAULT_LSTM_PARAMETERS["sequence_length"] == 20


def test_model_returns_one_prediction_per_sequence():
    model = create_lstm_regression_model()

    inputs = torch.randn(8, 20, 7)
    predictions = model(inputs)

    assert predictions.shape == (8,)
    assert torch.isfinite(predictions).all()


def test_model_supports_custom_architecture():
    model = create_lstm_regression_model(
        input_size=7,
        hidden_size=16,
        num_layers=2,
        dropout=0.2,
        random_state=123,
    )

    inputs = torch.randn(4, 20, 7)
    predictions = model(inputs)

    assert model.hidden_size == 16
    assert model.num_layers == 2
    assert predictions.shape == (4,)
    assert torch.isfinite(predictions).all()


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("input_size", 0),
        ("hidden_size", 0),
        ("num_layers", 0),
        ("input_size", -1),
        ("hidden_size", -5),
        ("num_layers", -1),
    ],
)
def test_model_rejects_invalid_dimensions(parameter, value):
    with pytest.raises(ValueError):
        create_lstm_regression_model(**{parameter: value})


@pytest.mark.parametrize("dropout", [-0.1, 1.0, float("nan"), float("inf")])
def test_model_rejects_invalid_dropout(dropout):
    with pytest.raises(ValueError):
        create_lstm_regression_model(dropout=dropout)


def test_model_rejects_negative_random_state():
    with pytest.raises(ValueError):
        create_lstm_regression_model(random_state=-1)


def test_model_rejects_wrong_number_of_input_features():
    model = create_lstm_regression_model(input_size=7)
    inputs = torch.randn(4, 20, 6)

    with pytest.raises(ValueError, match="Expected 7 input features"):
        model(inputs)


def test_model_rejects_two_dimensional_input():
    model = create_lstm_regression_model()

    with pytest.raises(ValueError, match="three-dimensional"):
        model(torch.randn(20, 7))


def test_model_supports_a_training_step():
    model = create_lstm_regression_model()
    optimiser = torch.optim.Adam(model.parameters(), lr=0.001)

    inputs = torch.randn(8, 20, 7)
    targets = torch.randn(8)

    optimiser.zero_grad()
    predictions = model(inputs)
    loss = torch.nn.functional.mse_loss(predictions, targets)
    loss.backward()
    optimiser.step()

    assert torch.isfinite(loss)
    assert all(
        parameter.grad is None
        or torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    )


def test_same_random_state_produces_same_initial_weights():
    first = create_lstm_regression_model(random_state=42)
    second = create_lstm_regression_model(random_state=42)

    for first_parameter, second_parameter in zip(
        first.parameters(),
        second.parameters(),
    ):
        assert torch.equal(first_parameter, second_parameter)


def test_sequence_builder_preserves_chronological_order():
    features = np.arange(30, dtype=np.float32).reshape(10, 3)
    targets = np.arange(10, dtype=np.float32)

    sequences, aligned_targets = build_lstm_sequences(
        features,
        targets,
        sequence_length=4,
    )

    assert sequences.shape == (7, 4, 3)
    assert aligned_targets.shape == (7,)

    np.testing.assert_array_equal(sequences[0], features[:4])
    np.testing.assert_array_equal(sequences[-1], features[-4:])
    np.testing.assert_array_equal(aligned_targets, targets[3:])


def test_sequence_builder_rejects_insufficient_observations():
    features = np.ones((5, 7), dtype=np.float32)
    targets = np.ones(5, dtype=np.float32)

    with pytest.raises(ValueError, match="Not enough observations"):
        build_lstm_sequences(features, targets, sequence_length=6)


def test_sequence_builder_rejects_mismatched_lengths():
    features = np.ones((10, 7), dtype=np.float32)
    targets = np.ones(9, dtype=np.float32)

    with pytest.raises(ValueError, match="same number of rows"):
        build_lstm_sequences(features, targets)


def test_sequence_builder_rejects_non_finite_features():
    features = np.ones((10, 7), dtype=np.float32)
    targets = np.ones(10, dtype=np.float32)
    features[3, 2] = np.nan

    with pytest.raises(ValueError, match="finite values"):
        build_lstm_sequences(features, targets)


def test_sequence_builder_rejects_non_finite_targets():
    features = np.ones((10, 7), dtype=np.float32)
    targets = np.ones(10, dtype=np.float32)
    targets[3] = np.inf

    with pytest.raises(ValueError, match="finite values"):
        build_lstm_sequences(features, targets)


def test_sequence_builder_rejects_invalid_sequence_length():
    features = np.ones((10, 7), dtype=np.float32)
    targets = np.ones(10, dtype=np.float32)

    with pytest.raises(ValueError, match="positive integer"):
        build_lstm_sequences(features, targets, sequence_length=0)