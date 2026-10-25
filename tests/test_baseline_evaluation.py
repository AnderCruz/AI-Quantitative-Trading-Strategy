"""Test chronological evaluation of baseline return-forecasting models."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.baseline_evaluation import (
    _calculate_metrics,
    _get_retraining_cutoffs,
    evaluate_baselines_walk_forward,
)
from src.temporal_split import get_target_maturity_dates


# Build a small synthetic single-asset dataset for evaluation tests.
def make_synthetic_data():
    """Return aligned history, targets and maturity dates."""

    # Create business-day observations with deterministic closing prices.
    dates = pd.bdate_range("2024-01-01", periods=100)

    history = pd.DataFrame(
        {
            "date": dates,
            "ticker": "TEST",
            "Open": 100.0 + np.arange(100) * 0.1,
            "Close": 100.0 + np.arange(100) * 0.2,
        }
    )

    # Generate deterministic forward-return targets for each horizon.
    targets = pd.DataFrame(index=history.index)

    for horizon in (1, 5, 10):
        targets[f"forward_return_{horizon}d"] = (
            history["Close"].shift(-horizon)
            / history["Open"].shift(-1)
            - 1
        )

    # Calculate maturity dates using the project's existing logic.
    maturity_dates = get_target_maturity_dates(history)

    return history, targets, maturity_dates


# Test that weekly cutoffs use the final observed session of each week.
def test_retraining_cutoffs_use_last_observed_weekly_session():
    validation_dates = [
        date(2024, 1, 1),
        date(2024, 1, 2),
        date(2024, 1, 4),
        date(2024, 1, 8),
        date(2024, 1, 9),
    ]

    cutoffs = _get_retraining_cutoffs(validation_dates)

    assert cutoffs == [
        date(2024, 1, 4),
        date(2024, 1, 9),
    ]


# Test the metric calculations on a simple example.
def test_calculate_metrics_returns_expected_errors():
    metrics = _calculate_metrics(
        actual=[0.01, 0.02, -0.01],
        predicted=[0.01, 0.01, -0.01],
    )

    assert metrics["sample_size"] == 3
    assert metrics["mae"] == pytest.approx(0.01 / 3)
    assert metrics["rmse"] == pytest.approx(np.sqrt(0.0001 / 3))
    assert metrics["directional_accuracy"] == pytest.approx(1.0)

# Test that undefined correlation metrics are handled correctly.
def test_calculate_metrics_handles_constant_predictions():
    metrics = _calculate_metrics(
        actual=[0.01, 0.02, -0.01],
        predicted=[0.0, 0.0, 0.0],
    )

    # Spearman correlation is undefined for constant predictions.
    assert np.isnan(metrics["spearman_correlation"])

    # R-squared remains defined when actual values vary.
    assert np.isfinite(metrics["r_squared"])
    assert metrics["r_squared"] < 0

# Test that malformed metric inputs are rejected.
def test_calculate_metrics_rejects_misaligned_inputs():
    with pytest.raises(ValueError, match="equal lengths"):
        _calculate_metrics(
            actual=[0.01, 0.02],
            predicted=[0.01],
        )


# Test that the evaluator returns all three models for each horizon.
def test_evaluator_returns_all_baselines_and_horizons():
    history, targets, maturity_dates = make_synthetic_data()

    predictions, metrics = evaluate_baselines_walk_forward(
        history=history,
        targets=targets,
        maturity_dates=maturity_dates,
        development_start=date(2024, 1, 1),
        development_end=date(2024, 2, 23),
        validation_start=date(2024, 2, 26),
        validation_end=date(2024, 5, 17),
    )

    # Confirm the expected model and horizon combinations are represented.
    assert set(predictions["model"]) == {
        "zero_return",
        "historical_mean",
        "historical_median",
    }
    assert set(predictions["horizon"]) == {1, 5, 10}
    assert len(metrics) == 9


# Test that the final test period cannot overlap the validation period.
def test_evaluator_rejects_overlapping_development_and_validation():
    history, targets, maturity_dates = make_synthetic_data()

    with pytest.raises(ValueError, match="must not overlap"):
        evaluate_baselines_walk_forward(
            history=history,
            targets=targets,
            maturity_dates=maturity_dates,
            development_start=date(2024, 1, 1),
            development_end=date(2024, 3, 1),
            validation_start=date(2024, 2, 1),
            validation_end=date(2024, 5, 17),
        )

# Test that predictions never use a future weekly retraining cutoff.
def test_predictions_never_use_a_future_retraining_cutoff():
    history, targets, maturity_dates = make_synthetic_data()

    predictions, _ = evaluate_baselines_walk_forward(
        history=history,
        targets=targets,
        maturity_dates=maturity_dates,
        development_start=date(2024, 1, 1),
        development_end=date(2024, 2, 23),
        validation_start=date(2024, 2, 26),
        validation_end=date(2024, 5, 17),
        horizons=(1,),
    )

    # Select the prediction generated on the first validation session.
    monday_prediction = predictions.loc[
        (predictions["date"] == date(2024, 2, 26))
        & (predictions["model"] == "zero_return")
    ]

    # The model must use the previous Friday's cutoff, not a future date.
    assert len(monday_prediction) == 1
    assert monday_prediction.iloc[0]["cutoff_date"] == date(2024, 2, 23)


# Test that the expanding training window grows over validation.
def test_expanding_window_includes_matured_validation_targets():
    history, targets, maturity_dates = make_synthetic_data()

    predictions, _ = evaluate_baselines_walk_forward(
        history=history,
        targets=targets,
        maturity_dates=maturity_dates,
        development_start=date(2024, 1, 1),
        development_end=date(2024, 2, 23),
        validation_start=date(2024, 2, 26),
        validation_end=date(2024, 5, 17),
        horizons=(1,),
    )

    # Compare training sample sizes at two validation dates.
    early_sample = predictions.loc[
        (predictions["date"] == date(2024, 2, 26))
        & (predictions["model"] == "zero_return"),
        "training_sample_size",
    ].iloc[0]

    later_sample = predictions.loc[
        (predictions["date"] == date(2024, 3, 15))
        & (predictions["model"] == "zero_return"),
        "training_sample_size",
    ].iloc[0]

    # The later training window should include additional matured targets.
    assert later_sample > early_sample