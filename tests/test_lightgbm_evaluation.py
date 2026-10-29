"""Tests for the LightGBM walk-forward evaluation."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.feature_target_pipeline import FEATURE_COLUMNS
from src.lightgbm_evaluation import (
    DEFAULT_PARAMETERS,
    MODEL_NAME,
    evaluate_lightgbm_walk_forward,
)


def make_synthetic_data():
    """Create deterministic chronological data for evaluator tests."""
    rng = np.random.default_rng(42)

    dates = pd.bdate_range("2020-01-01", periods=900)
    index = pd.RangeIndex(len(dates))

    history = pd.DataFrame(
        {
            "date": dates,
            "ticker": "LLOY.L",
        },
        index=index,
    )

    features = pd.DataFrame(
        rng.normal(size=(len(dates), len(FEATURE_COLUMNS))),
        columns=FEATURE_COLUMNS,
        index=index,
    )

    targets = pd.DataFrame(index=index)
    maturity_dates = pd.DataFrame(index=index)

    for horizon in (1, 5, 10):
        targets[f"forward_return_{horizon}d"] = (
            0.001 * features[FEATURE_COLUMNS[0]]
            + rng.normal(0, 0.01, len(dates))
        )

        maturity_dates[f"target_maturity_date_{horizon}d"] = [
            dates[min(i + horizon, len(dates) - 1)]
            if i + horizon < len(dates)
            else pd.NaT
            for i in range(len(dates))
        ]

    return history, features, targets, maturity_dates


@pytest.fixture
def synthetic_data():
    return make_synthetic_data()


def run_evaluation(data, **overrides):
    history, features, targets, maturity_dates = data

    arguments = {
        "history": history,
        "features": features,
        "targets": targets,
        "maturity_dates": maturity_dates,
        "development_start": date(2020, 1, 1),
        "development_end": date(2021, 12, 31),
        "validation_start": date(2022, 1, 3),
        "validation_end": date(2022, 6, 30),
        "horizons": (1, 5, 10),
        "min_training_samples": 100,
    }
    arguments.update(overrides)

    return evaluate_lightgbm_walk_forward(**arguments)


def test_default_parameters_are_reproducible():
    assert DEFAULT_PARAMETERS["n_estimators"] == 100
    assert DEFAULT_PARAMETERS["random_state"] == 42
    assert DEFAULT_PARAMETERS["n_jobs"] == 1


def test_evaluation_returns_predictions_and_metrics(synthetic_data):
    predictions, metrics = run_evaluation(synthetic_data)

    assert not predictions.empty
    assert set(predictions["model"]) == {MODEL_NAME}
    assert set(predictions["horizon"]) == {1, 5, 10}
    assert {"date", "cutoff_date", "prediction", "actual_return",
            "training_sample_size"}.issubset(predictions.columns)
    assert {"horizon", "mae", "rmse"}.issubset(metrics.columns)
    assert predictions["prediction"].map(np.isfinite).all()


def test_predictions_stay_inside_validation_period(synthetic_data):
    predictions, _ = run_evaluation(synthetic_data)

    assert predictions["date"].min() >= date(2022, 1, 3)
    assert predictions["date"].max() <= date(2022, 6, 30)


def test_labels_maturing_after_validation_end_are_excluded(synthetic_data):
    predictions, _ = run_evaluation(synthetic_data)
    maturity_dates = synthetic_data[3]

    for row in predictions.itertuples(index=False):
        maturity = maturity_dates.loc[
            synthetic_data[0].index[
                synthetic_data[0]["date"].dt.date == row.date
            ][0],
            f"target_maturity_date_{row.horizon}d",
        ]
        assert maturity.date() <= date(2022, 6, 30)


def test_insufficient_training_data_is_rejected(synthetic_data):
    with pytest.raises(ValueError, match="Insufficient eligible training"):
        run_evaluation(synthetic_data, min_training_samples=10_000)


def test_duplicate_horizons_are_rejected(synthetic_data):
    with pytest.raises(ValueError, match="must not contain duplicates"):
        run_evaluation(synthetic_data, horizons=(1, 1))


def test_overlapping_development_and_validation_are_rejected(synthetic_data):
    with pytest.raises(ValueError, match="must not overlap"):
        run_evaluation(
            synthetic_data,
            development_end=date(2022, 1, 10),
            validation_start=date(2022, 1, 3),
        )
