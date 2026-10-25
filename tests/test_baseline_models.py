"""Test leakage controls and behaviour of baseline forecasting models."""

import numpy as np
import pandas as pd
import pytest

from src.baseline_models import (
    HistoricalMeanBaseline,
    HistoricalMedianBaseline,
    ZeroReturnBaseline,
    get_eligible_training_targets,
)


# Test that the zero-return baseline always predicts zero.
def test_zero_return_baseline_predicts_zero():
    model = ZeroReturnBaseline().fit(
        pd.Series([0.01, -0.02, 0.03])
    )

    predictions = model.predict(3)

    np.testing.assert_array_equal(predictions, np.zeros(3))


# Test that the historical mean uses the supplied training targets.
def test_historical_mean_baseline():
    model = HistoricalMeanBaseline().fit(
        pd.Series([0.01, 0.02, 0.03])
    )

    assert model.value_ == pytest.approx(0.02)
    np.testing.assert_allclose(model.predict(2), [0.02, 0.02])


# Test that the historical median is calculated correctly.
def test_historical_median_baseline():
    model = HistoricalMedianBaseline().fit(
        pd.Series([0.01, 0.02, 0.50])
    )

    assert model.value_ == pytest.approx(0.02)


# Test that predictions cannot be generated before fitting.
def test_baseline_rejects_prediction_before_fit():
    model = ZeroReturnBaseline()

    with pytest.raises(RuntimeError):
        model.predict(1)


# Test that fitting rejects empty or non-finite targets.
@pytest.mark.parametrize(
    "values",
    [
        [],
        [0.01, np.nan],
        [0.01, np.inf],
        [0.01, -np.inf],
    ],
)
def test_baseline_rejects_invalid_training_targets(values):
    model = HistoricalMeanBaseline()

    with pytest.raises(ValueError):
        model.fit(pd.Series(values, dtype=float))


# Test that fitting rejects a DataFrame instead of a one-dimensional input.
def test_baseline_rejects_dataframe_input():
    model = HistoricalMeanBaseline()
    targets = pd.DataFrame({"return": [0.01, 0.02]})

    with pytest.raises(TypeError):
        model.fit(targets)


# Test that invalid prediction counts are rejected.
@pytest.mark.parametrize("n_samples", [0, -1, 1.5, True])
def test_baseline_rejects_invalid_prediction_count(n_samples):
    model = ZeroReturnBaseline().fit(pd.Series([0.01, 0.02]))

    with pytest.raises(ValueError):
        model.predict(n_samples)


# Test that unsupported forecasting horizons are rejected.
@pytest.mark.parametrize("horizon", [0, 2, 20, True])
def test_unsupported_horizon_is_rejected(horizon):
    with pytest.raises(ValueError):
        get_eligible_training_targets(
            history=pd.DataFrame(),
            targets=pd.DataFrame(),
            maturity_dates=pd.DataFrame(),
            horizon=horizon,
            period_start="2020-01-01",
            period_end="2020-12-31",
            cutoff_date="2020-12-31",
        )


# Test that targets and maturity dates must have matching indices.
def test_target_index_mismatch_is_rejected():
    dates = pd.to_datetime(["2020-01-02", "2020-01-03"])

    history = pd.DataFrame(
        {"Date": dates},
        index=[0, 1],
    )
    targets = pd.DataFrame(
        {"forward_return_1d": [0.01, 0.02]},
        index=[1, 0],
    )
    maturity_dates = pd.DataFrame(
        {
            "target_maturity_date_1d": pd.to_datetime(
                ["2020-01-03", "2020-01-06"]
            )
        },
        index=[0, 1],
    )

    with pytest.raises(ValueError, match="identical indices"):
        get_eligible_training_targets(
            history=history,
            targets=targets,
            maturity_dates=maturity_dates,
            horizon=1,
            period_start=pd.Timestamp("2020-01-01").date(),
            period_end=pd.Timestamp("2020-12-31").date(),
            cutoff_date=pd.Timestamp("2020-12-31").date(),
        )