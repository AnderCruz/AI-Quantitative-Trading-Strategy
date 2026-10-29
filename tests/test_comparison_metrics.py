"""Tests for directional metrics used in model comparisons."""

import numpy as np
import pandas as pd
import pytest

from src.compare_all_models_including_mlp import (
    calculate_directional_metrics,
)


def test_perfect_directional_predictions():
    actual = pd.Series([0.02, -0.03, 0.01, -0.01])
    predicted = pd.Series([0.01, -0.02, 0.03, -0.04])

    metrics = calculate_directional_metrics(actual, predicted)

    assert metrics["directional_accuracy"] == 1.0
    assert metrics["directional_coverage"] == 1.0


def test_zero_predictions_have_zero_directional_coverage():
    actual = pd.Series([0.02, -0.03, 0.01, -0.01])
    predicted = pd.Series([0.0, 0.0, 0.0, 0.0])

    metrics = calculate_directional_metrics(actual, predicted)

    assert metrics["directional_accuracy"] == 0.0
    assert metrics["directional_coverage"] == 0.0


def test_mixed_predictions_use_exact_sign_matching():
    actual = pd.Series([0.02, -0.03, 0.01, -0.01])
    predicted = pd.Series([0.01, 0.02, 0.0, -0.04])

    metrics = calculate_directional_metrics(actual, predicted)

    assert metrics["directional_accuracy"] == pytest.approx(0.5)
    assert metrics["directional_coverage"] == pytest.approx(0.75)


def test_zero_actual_return_is_neutral():
    actual = pd.Series([0.0, 0.02, -0.02])
    predicted = pd.Series([0.0, 0.01, -0.01])

    metrics = calculate_directional_metrics(actual, predicted)

    assert metrics["directional_accuracy"] == pytest.approx(1.0)
    assert metrics["directional_coverage"] == pytest.approx(2 / 3)


@pytest.mark.parametrize(
    ("actual", "predicted"),
    [
        ([0.01, np.nan], [0.02, 0.03]),
        ([0.01, 0.02], [0.03, np.inf]),
    ],
)
def test_non_finite_values_are_rejected(actual, predicted):
    with pytest.raises(ValueError, match="must be finite"):
        calculate_directional_metrics(
            pd.Series(actual),
            pd.Series(predicted),
        )