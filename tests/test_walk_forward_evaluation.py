"""Unit tests for the generic walk-forward evaluator."""

from datetime import date

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.feature_target_pipeline import FEATURE_COLUMNS
from src.walk_forward_evaluation import evaluate_walk_forward


def make_synthetic_data(periods: int = 260):
    dates = pd.bdate_range("2022-01-03", periods=periods)
    index = pd.RangeIndex(periods)
    rng = np.random.default_rng(42)
    feature_values = rng.normal(size=(periods, len(FEATURE_COLUMNS)))
    features = pd.DataFrame(feature_values, columns=FEATURE_COLUMNS, index=index)
    history = pd.DataFrame(
        {"date": dates, "ticker": "TEST"}, index=index
    )
    targets = pd.DataFrame(index=index)
    maturity_dates = pd.DataFrame(index=index)
    for horizon in (1, 5, 10):
        targets[f"forward_return_{horizon}d"] = (
            0.01 * features[FEATURE_COLUMNS[0]]
            - 0.005 * features[FEATURE_COLUMNS[1]]
            + rng.normal(0, 0.01, periods)
        )
        maturity_dates[f"target_maturity_date_{horizon}d"] = [
            dates[i + horizon] if i + horizon < periods else pd.NaT
            for i in range(periods)
        ]
    return history, features, targets, maturity_dates


def make_model():
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=1.0)),
        ]
    )


def run_evaluation(data, **overrides):
    history, features, targets, maturity_dates = data
    arguments = {
        "history": history,
        "features": features,
        "targets": targets,
        "maturity_dates": maturity_dates,
        "development_start": date(2022, 1, 3),
        "development_end": date(2022, 7, 29),
        "validation_start": date(2022, 8, 1),
        "validation_end": date(2022, 12, 30),
        "model_factory": make_model,
        "model_name": "test_ridge",
        "horizons": (1, 5, 10),
        "min_training_samples": 30,
    }
    arguments.update(overrides)
    return evaluate_walk_forward(**arguments)


def test_returns_predictions_and_metrics_for_requested_horizons():
    predictions, metrics = run_evaluation(make_synthetic_data())
    assert not predictions.empty
    assert set(predictions["model"]) == {"test_ridge"}
    assert set(predictions["horizon"]) == {1, 5, 10}
    assert {
        "date", "cutoff_date", "horizon", "model", "prediction",
        "actual_return", "training_sample_size",
    }.issubset(predictions.columns)
    assert {"horizon", "model", "mae", "rmse", "sample_size"}.issubset(metrics.columns)
    assert np.isfinite(predictions["prediction"]).all()
    assert np.isfinite(predictions["actual_return"]).all()
    assert (predictions["cutoff_date"] <= predictions["date"]).all()
    assert (predictions["training_sample_size"] >= 30).all()


def test_validation_predictions_are_within_period_and_labels_are_mature():
    data = make_synthetic_data()
    predictions, _ = run_evaluation(data)
    maturity_dates = data[3]
    assert predictions["date"].min() >= date(2022, 8, 1)
    assert predictions["date"].max() <= date(2022, 12, 30)
    for row in predictions.itertuples(index=False):
        row_index = data[0].index[data[0]["date"].dt.date == row.date][0]
        maturity = maturity_dates.loc[row_index, f"target_maturity_date_{row.horizon}d"]
        assert pd.Timestamp(maturity).date() <= date(2022, 12, 30)


def test_rejects_duplicate_horizons():
    with pytest.raises(ValueError, match="must not contain duplicates"):
        run_evaluation(make_synthetic_data(), horizons=(1, 1))


def test_rejects_unsupported_horizon():
    with pytest.raises(ValueError, match="non-empty subset"):
        run_evaluation(make_synthetic_data(), horizons=(2,))


def test_rejects_overlapping_periods():
    with pytest.raises(ValueError, match="must not overlap"):
        run_evaluation(
            make_synthetic_data(),
            development_end=date(2022, 8, 5),
            validation_start=date(2022, 8, 1),
        )


def test_rejects_misaligned_feature_index():
    data = list(make_synthetic_data())
    data[1] = data[1].copy()
    data[1].index = data[1].index + 1
    with pytest.raises(ValueError, match="identical indices"):
        run_evaluation(tuple(data))


def test_rejects_insufficient_training_samples():
    with pytest.raises(ValueError, match="Insufficient eligible training observations"):
        run_evaluation(make_synthetic_data(), min_training_samples=10_000)


def test_incomplete_validation_features_are_not_scored():
    data = list(make_synthetic_data())
    history, features, _, _ = data
    features = features.copy()
    target_date = date(2022, 8, 1)
    row_index = history.index[history["date"].dt.date == target_date][0]
    features.loc[row_index, list(FEATURE_COLUMNS)] = np.nan
    data[1] = features
    predictions, _ = run_evaluation(tuple(data), horizons=(1,))
    assert not ((predictions["date"] == target_date) & (predictions["horizon"] == 1)).any()


def test_model_factory_must_be_callable():
    with pytest.raises(TypeError, match="model_factory must be callable"):
        run_evaluation(make_synthetic_data(), model_factory=None)


def test_model_name_must_be_non_empty():
    with pytest.raises(ValueError, match="model_name"):
        run_evaluation(make_synthetic_data(), model_name=" ")
