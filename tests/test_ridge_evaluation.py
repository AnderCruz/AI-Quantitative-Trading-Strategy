"""Tests for Ridge model construction and walk-forward evaluation."""

from datetime import date

import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.feature_target_pipeline import FEATURE_COLUMNS
from src.ridge_evaluation import evaluate_ridge_walk_forward
from src.supervised_models import create_ridge_regression_model
from src.temporal_split import get_target_maturity_dates


def make_data(periods: int = 220):
    dates = pd.bdate_range("2022-01-03", periods=periods)
    t = np.arange(periods, dtype=float)
    close = 100 + 0.025 * t + 0.8 * np.sin(t / 7) + 0.2 * np.cos(t / 3)
    open_price = close * (1 + 0.001 * np.sin(t / 5))
    history = pd.DataFrame({"date": dates.date, "ticker": "TEST", "Open": open_price, "Close": close})
    maturity = get_target_maturity_dates(history)
    close_series = pd.Series(close)
    daily_returns = close_series.pct_change()
    features = pd.DataFrame(index=history.index)
    features["close_return_1d"] = close_series.pct_change(1)
    features["close_return_5d"] = close_series.pct_change(5)
    features["close_return_10d"] = close_series.pct_change(10)
    features["close_return_20d"] = close_series.pct_change(20)
    features["close_volatility_5d"] = daily_returns.rolling(5).std()
    features["close_volatility_10d"] = daily_returns.rolling(10).std()
    features["close_volatility_20d"] = daily_returns.rolling(20).std()
    features = features.loc[:, FEATURE_COLUMNS]
    targets = pd.DataFrame(index=history.index)
    for horizon in (1, 5, 10):
        targets[f"forward_return_{horizon}d"] = history["Close"].shift(-horizon) / history["Open"].shift(-1) - 1
    return history, features, targets, maturity


def evaluate(history, features, targets, maturity, *, horizons=(1, 5, 10), minimum=30):
    return evaluate_ridge_walk_forward(
        history=history, features=features, targets=targets, maturity_dates=maturity,
        development_start=date(2022, 1, 3), development_end=date(2022, 7, 1),
        validation_start=date(2022, 7, 4), validation_end=date(2022, 11, 4),
        horizons=horizons, min_training_samples=minimum,
    )


def test_ridge_model_contains_scaler_and_ridge_in_pipeline():
    model = create_ridge_regression_model(alpha=1.0)
    assert isinstance(model, Pipeline)
    assert isinstance(model.named_steps["scaler"], StandardScaler)
    assert model.named_steps["ridge"].alpha == 1.0


@pytest.mark.parametrize("alpha", [-1, np.nan, np.inf])
def test_ridge_model_rejects_invalid_alpha(alpha):
    with pytest.raises(ValueError, match="alpha"):
        create_ridge_regression_model(alpha=alpha)


def test_evaluator_rejects_misaligned_feature_index():
    history, features, targets, maturity = make_data()
    features.index = features.index + 1
    with pytest.raises(ValueError, match="identical indices"):
        evaluate(history, features, targets, maturity, horizons=(1,))


def test_evaluator_enforces_500_sample_default_minimum():
    history, features, targets, maturity = make_data(periods=100)
    with pytest.raises(ValueError, match="Insufficient eligible training observations"):
        evaluate_ridge_walk_forward(
            history=history, features=features, targets=targets, maturity_dates=maturity,
            development_start=date(2022, 1, 3), development_end=date(2022, 3, 31),
            validation_start=date(2022, 4, 1), validation_end=date(2022, 5, 20),
            horizons=(1,),
        )


def test_walk_forward_ridge_returns_finite_predictions_and_metrics():
    history, features, targets, maturity = make_data()
    predictions, metrics = evaluate(history, features, targets, maturity)
    assert not predictions.empty
    assert set(predictions["model"]) == {"ridge_regression"}
    assert set(predictions["horizon"]) == {1, 5, 10}
    assert (predictions["cutoff_date"] <= predictions["date"]).all()
    assert (predictions["training_sample_size"] >= 30).all()
    assert np.isfinite(predictions["prediction"]).all()
    assert np.isfinite(predictions["actual_return"]).all()
    assert set(metrics["horizon"]) == {1, 5, 10}
    assert (metrics["sample_size"] > 0).all()


def test_incomplete_validation_features_are_not_scored():
    history, features, targets, maturity = make_data()
    validation_date = date(2022, 7, 4)
    row = history.index[history["date"] == validation_date][0]
    features.loc[row, list(FEATURE_COLUMNS)] = np.nan
    predictions, _ = evaluate(history, features, targets, maturity, horizons=(1,))
    assert not ((predictions["date"] == validation_date) & (predictions["horizon"] == 1)).any()
