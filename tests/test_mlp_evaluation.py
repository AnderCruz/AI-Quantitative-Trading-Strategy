"""Tests for MLP walk-forward evaluation."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.mlp_evaluation import MODEL_NAME, evaluate_mlp_walk_forward


FEATURE_COLUMNS = [
    "close_return_1d",
    "close_return_5d",
    "close_return_10d",
    "close_return_20d",
    "close_volatility_5d",
    "close_volatility_10d",
    "close_volatility_20d",
]


def make_evaluation_data(n_samples=700):
    """Create deterministic synthetic data for temporal evaluation."""
    dates = pd.bdate_range("2020-01-01", periods=n_samples)
    rng = np.random.default_rng(42)

    features = pd.DataFrame(
        rng.normal(size=(n_samples, len(FEATURE_COLUMNS))),
        index=dates,
        columns=FEATURE_COLUMNS,
    )

    history = pd.DataFrame(
        {
            "date": dates,
            "ticker": "TEST",
            "open": 100.0 + np.arange(n_samples) * 0.01,
            "close": 100.0 + np.arange(n_samples) * 0.01,
        },
        index=dates,
    )

    targets = pd.DataFrame(index=dates)
    maturity_dates = pd.DataFrame(index=dates)

    for horizon in (1, 5, 10):
        targets[f"forward_return_{horizon}d"] = (
            0.01 * features["close_return_1d"]
            - 0.02 * features["close_return_5d"]
            + rng.normal(0, 0.001, size=n_samples)
        )
        maturity_dates[f"target_maturity_date_{horizon}d"] = (
            dates + pd.offsets.BDay(horizon)
        )

    return history, features, targets, maturity_dates, dates


def evaluation_kwargs(data, horizon=1):
    history, features, targets, maturity_dates, dates = data
    return {
        "history": history,
        "features": features,
        "targets": targets,
        "maturity_dates": maturity_dates,
        "development_start": dates[0].date(),
        "development_end": dates[519].date(),
        "validation_start": dates[520].date(),
        "validation_end": dates[649].date(),
        "horizons": (horizon,),
        "min_training_samples": 500,
    }


def test_mlp_evaluation_returns_expected_predictions_and_metrics():
    predictions, metrics = evaluate_mlp_walk_forward(
        **evaluation_kwargs(make_evaluation_data())
    )

    assert not predictions.empty
    assert not metrics.empty

    assert {
        "date",
        "cutoff_date",
        "horizon",
        "model",
        "prediction",
        "actual_return",
        "training_sample_size",
    }.issubset(predictions.columns)

    assert {"horizon", "model"}.issubset(metrics.columns)
    assert predictions["model"].eq(MODEL_NAME).all()
    assert predictions["horizon"].eq(1).all()
    assert np.isfinite(predictions["prediction"]).all()
    assert np.isfinite(predictions["actual_return"]).all()
    assert (predictions["training_sample_size"] >= 500).all()


def test_mlp_evaluation_respects_validation_end_and_target_maturity():
    data = make_evaluation_data()
    kwargs = evaluation_kwargs(data)
    validation_end = kwargs["validation_end"]

    predictions, _ = evaluate_mlp_walk_forward(**kwargs)

    assert (
        pd.to_datetime(predictions["date"]).dt.date <= validation_end
    ).all()

    maturity_dates = data[3]
    for _, prediction in predictions.iterrows():
        row_date = pd.Timestamp(prediction["date"])
        maturity = maturity_dates.loc[
            row_date, "target_maturity_date_1d"
        ]
        assert pd.Timestamp(maturity).date() <= validation_end


@pytest.mark.parametrize("horizon", [0, 2, 15])
def test_mlp_evaluation_rejects_unsupported_horizons(horizon):
    kwargs = evaluation_kwargs(make_evaluation_data(), horizon=horizon)

    with pytest.raises(ValueError):
        evaluate_mlp_walk_forward(**kwargs)


def test_mlp_evaluation_rejects_overlapping_development_and_validation():
    kwargs = evaluation_kwargs(make_evaluation_data())
    kwargs["development_end"] = kwargs["validation_start"]

    with pytest.raises(ValueError):
        evaluate_mlp_walk_forward(**kwargs)
