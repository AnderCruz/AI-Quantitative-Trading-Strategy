"""LSTM regression model and time-series sequence preparation."""

from __future__ import annotations

from numbers import Integral, Real

import numpy as np
import torch
from torch import nn


DEFAULT_LSTM_PARAMETERS = {
    "input_size": 7,
    "hidden_size": 32,
    "num_layers": 1,
    "dropout": 0.0,
    "sequence_length": 20,
    "random_state": 42,
}


def _validate_positive_integer(name: str, value: int) -> None:
    """Validate that a parameter is a positive integer."""
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be a positive integer.")

    if value <= 0:
        raise ValueError(f"{name} must be a positive integer.")


def _validate_dropout(dropout: float) -> None:
    """Validate the dropout probability."""
    if isinstance(dropout, bool) or not isinstance(dropout, Real):
        raise ValueError("dropout must be a number between 0 and 1.")

    if not np.isfinite(dropout) or not 0.0 <= dropout < 1.0:
        raise ValueError("dropout must be a finite number in [0, 1).")


class LSTMRegressor(nn.Module):
    """LSTM network for single-target regression."""

    def __init__(
        self,
        input_size: int = 7,
        hidden_size: int = 32,
        num_layers: int = 1,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()

        _validate_positive_integer("input_size", input_size)
        _validate_positive_integer("hidden_size", hidden_size)
        _validate_positive_integer("num_layers", num_layers)
        _validate_dropout(dropout)

        self.input_size = int(input_size)
        self.hidden_size = int(hidden_size)
        self.num_layers = int(num_layers)
        self.dropout = float(dropout)

        # PyTorch applies recurrent-layer dropout only when num_layers > 1.
        recurrent_dropout = self.dropout if self.num_layers > 1 else 0.0

        self.lstm = nn.LSTM(
            input_size=self.input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            batch_first=True,
            dropout=recurrent_dropout,
        )

        self.output_layer = nn.Linear(self.hidden_size, 1)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        """Return one prediction for each input sequence."""
        if inputs.ndim != 3:
            raise ValueError(
                "inputs must be three-dimensional, with shape "
                "(batch_size, sequence_length, input_size)."
            )

        if inputs.shape[-1] != self.input_size:
            raise ValueError(
                f"Expected {self.input_size} input features, "
                f"received {inputs.shape[-1]}."
            )

        if inputs.shape[1] == 0:
            raise ValueError("Input sequences cannot be empty.")

        sequence_output, _ = self.lstm(inputs)

        # Use the final timestep to predict the target return.
        final_output = sequence_output[:, -1, :]

        return self.output_layer(final_output).squeeze(-1)


def create_lstm_regression_model(
    input_size: int = DEFAULT_LSTM_PARAMETERS["input_size"],
    hidden_size: int = DEFAULT_LSTM_PARAMETERS["hidden_size"],
    num_layers: int = DEFAULT_LSTM_PARAMETERS["num_layers"],
    dropout: float = DEFAULT_LSTM_PARAMETERS["dropout"],
    random_state: int = DEFAULT_LSTM_PARAMETERS["random_state"],
) -> LSTMRegressor:
    """Create a reproducibly initialised LSTM regression model."""
    _validate_positive_integer("input_size", input_size)
    _validate_positive_integer("hidden_size", hidden_size)
    _validate_positive_integer("num_layers", num_layers)
    _validate_dropout(dropout)

    if (
        isinstance(random_state, bool)
        or not isinstance(random_state, Integral)
        or random_state < 0
    ):
        raise ValueError("random_state must be a non-negative integer.")

    # Avoid changing the caller's global PyTorch random-number state.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(int(random_state))

        return LSTMRegressor(
            input_size=int(input_size),
            hidden_size=int(hidden_size),
            num_layers=int(num_layers),
            dropout=float(dropout),
        )


def build_lstm_sequences(
    features: np.ndarray,
    targets: np.ndarray,
    sequence_length: int = DEFAULT_LSTM_PARAMETERS["sequence_length"],
) -> tuple[np.ndarray, np.ndarray]:
    """Build chronological sliding windows and their corresponding targets.

    Each target is aligned with the final observation in its input window.
    Temporal splitting and target-maturity checks must be performed by the
    evaluation pipeline before this function is called.
    """
    _validate_positive_integer("sequence_length", sequence_length)

    feature_values = np.asarray(features, dtype=np.float32)
    target_values = np.asarray(targets, dtype=np.float32)

    if feature_values.ndim != 2:
        raise ValueError("features must be a two-dimensional array.")

    if target_values.ndim != 1:
        raise ValueError("targets must be a one-dimensional array.")

    if feature_values.shape[0] != target_values.shape[0]:
        raise ValueError(
            "features and targets must contain the same number of rows."
        )

    if feature_values.shape[1] == 0:
        raise ValueError("features must contain at least one feature.")

    if not np.isfinite(feature_values).all():
        raise ValueError("features must contain only finite values.")

    if not np.isfinite(target_values).all():
        raise ValueError("targets must contain only finite values.")

    if feature_values.shape[0] < sequence_length:
        raise ValueError(
            "Not enough observations to construct the requested sequences."
        )

    sequences = np.stack(
        [
            feature_values[
                end_index - sequence_length + 1 : end_index + 1
            ]
            for end_index in range(
                sequence_length - 1,
                len(feature_values),
            )
        ]
    )

    aligned_targets = target_values[sequence_length - 1 :]

    return sequences, aligned_targets