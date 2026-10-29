"""Tests for Random Forest walk-forward return evaluation."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.feature_target_pipeline import FEATURE_COLUMNS
from src.random_forest_evaluation import (
    MODEL_NAME,
    SUPPORTED_HORIZONS,
    evaluate_random_forest_walk_forward,
)


def make_synthetic_data(periods=900):
    """Create deterministic chronological data for evaluator tests."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-01", periods=periods)
    index = pd.RangeIndex(len(dates))

    history = pd.DataFrame(
        {"date": dates, "ticker": "LLOY.L"},
        index=index,
    )

    features = pd.DataFrame(
        rng.normal(size=(len(dates), len(FEATURE_COLUMNS))),
        columns=FEATURE_COLUMNS,
        index=index,
    )

    targets = pd.DataFrame(index=index)
    maturity_dates = pd.DataFrame(index=index)

    for horizon in SUPPORTED_HORIZONS:
        targets[f"forward_return_{horizon}d"] = (
            0.001 * features[FEATURE_COLUMNS[0]]
            + rng.normal(0, 0.01, len(dates))
        )

        maturity_dates[f"target_maturity_date_{horizon}d"] = [
            dates[i + horizon]
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
        "horizons": SUPPORTED_HORIZONS,
        "min_training_samples": 100,
    }
    arguments.update(overrides)

    return evaluate_random_forest_walk_forward(**arguments)


def test_model_name_and_supported_horizons():
    assert MODEL_NAME == "random_forest_regression"
    assert SUPPORTED_HORIZONS == (1, 5, 10)


def test_evaluation_returns_finite_predictions_and_metrics(synthetic_data):
    predictions, metrics = run_evaluation(synthetic_data)

    assert not predictions.empty
    assert set(predictions["model"]) == {MODEL_NAME}
    assert set(predictions["horizon"]) == {1, 5, 10}
    assert {
        "date",
        "cutoff_date",
        "horizon",
        "model",
        "prediction",
        "actual_return",
        "training_sample_size",
    }.issubset(predictions.columns)
    assert {"horizon", "model", "mae", "rmse"}.issubset(metrics.columns)
    assert np.isfinite(predictions["prediction"]).all()
    assert np.isfinite(predictions["actual_return"]).all()
    assert (predictions["cutoff_date"] <= predictions["date"]).all()
    assert (predictions["training_sample_size"] >= 100).all()
    assert (metrics["sample_size"] > 0).all()


def test_predictions_stay_inside_validation_period(synthetic_data):
    predictions, _ = run_evaluation(synthetic_data)

    assert predictions["date"].min() >= date(2022, 1, 3)
    assert predictions["date"].max() <= date(2022, 6, 30)


def test_labels_maturing_after_validation_end_are_excluded(synthetic_data):
    predictions, _ = run_evaluation(synthetic_data)
    history, _, _, maturity_dates = synthetic_data

    for row in predictions.itertuples(index=False):
        row_index = history.index[
            history["date"].dt.date == row.date
        ][0]
        maturity = maturity_dates.loc[
            row_index,
            f"target_maturity_date_{row.horizon}d",
        ]
        assert pd.notna(maturity)
        assert maturity.date() <= date(2022, 6, 30)


def test_insufficient_training_data_is_rejected(synthetic_data):
    with pytest.raises(
        ValueError,
        match="Insufficient eligible training observations",
    ):
        run_evaluation(synthetic_data, min_training_samples=10_000)


def test_duplicate_horizons_are_rejected(synthetic_data):
    with pytest.raises(ValueError, match="must not contain duplicates"):
        run_evaluation(synthetic_data, horizons=(1, 1))


def test_unsupported_horizon_is_rejected(synthetic_data):
    with pytest.raises(ValueError, match="horizons must be a non-empty subset"):
        run_evaluation(synthetic_data, horizons=(2,))


def test_overlapping_development_and_validation_are_rejected(synthetic_data):
    with pytest.raises(ValueError, match="must not overlap"):
        run_evaluation(
            synthetic_data,
            development_end=date(2022, 1, 10),
            validation_start=date(2022, 1, 3),
        )


def test_misaligned_feature_index_is_rejected(synthetic_data):
    history, features, targets, maturity_dates = synthetic_data
    features = features.copy()
    features.index = features.index + 1

    with pytest.raises(ValueError, match="identical indices"):
        run_evaluation((history, features, targets, maturity_dates))


def test_incomplete_validation_features_are_not_scored(synthetic_data):
    history, features, targets, maturity_dates = synthetic_data
    features = features.copy()

    validation_date = date(2022, 1, 3)
    row_index = history.index[
        history["date"].dt.date == validation_date
    ][0]
    features.loc[row_index, list(FEATURE_COLUMNS)] = np.nan

    predictions, _ = run_evaluation(
        (history, features, targets, maturity_dates),
        horizons=(1,),
    )

    assert not (
        (predictions["date"] == validation_date)
        & (predictions["horizon"] == 1)
    ).any()


def test_training_labels_must_be_mature_at_cutoff(synthetic_data):
    """The eligibility contract must exclude labels that mature after cutoff."""
    from src.temporal_split import get_training_eligibility_mask

    history, _, _, maturity_dates = synthetic_data
    cutoff = date(2021, 12, 31)

    eligibility = get_training_eligibility_mask(
        history,
        maturity_dates,
        date(2020, 1, 1),
        cutoff,
        cutoff,
    )

    for column in maturity_dates.columns:
        eligible_dates = maturity_dates.loc[
            eligibility[column], column
        ].dropna()

        assert all(
            pd.Timestamp(value).date() <= cutoff
            for value in eligible_dates
        )


def test_validation_predictions_exclude_post_validation_maturities(
    synthetic_data,
):
    """Scored validation targets must mature no later than validation_end."""
    predictions, _ = run_evaluation(synthetic_data)
    history, _, _, maturity_dates = synthetic_data
    validation_end = date(2022, 6, 30)

    for row in predictions.itertuples(index=False):
        matching_rows = history.index[
            history["date"].dt.date == row.date
        ]
        assert len(matching_rows) == 1

        maturity = maturity_dates.loc[
            matching_rows[0],
            f"target_maturity_date_{row.horizon}d",
        ]

        assert pd.notna(maturity)
        assert pd.Timestamp(maturity).date() <= validation_end

    assert predictions["date"].max() <= validation_end


def test_future_target_perturbations_do_not_change_prior_cutoff_predictions(
    synthetic_data,
):
    """Changing targets immature at a cutoff must not change its predictions."""
    history, features, targets, maturity_dates = synthetic_data
    original_data = (
        history.copy(),
        features.copy(),
        targets.copy(),
        maturity_dates.copy(),
    )

    cutoff = date(2021, 12, 31)

    original_predictions, _ = run_evaluation(original_data)

    perturbed_targets = targets.copy()

    for horizon in SUPPORTED_HORIZONS:
        target_column = f"forward_return_{horizon}d"
        maturity_column = f"target_maturity_date_{horizon}d"

        maturity = pd.to_datetime(maturity_dates[maturity_column])
        future_mask = maturity.dt.date > cutoff

        perturbed_targets.loc[future_mask, target_column] = (
            perturbed_targets.loc[future_mask, target_column] + 10.0
        )

    perturbed_data = (
        history.copy(),
        features.copy(),
        perturbed_targets,
        maturity_dates.copy(),
    )

    perturbed_predictions, _ = run_evaluation(perturbed_data)

    original_at_cutoff = (
        original_predictions.loc[
            original_predictions["cutoff_date"] == cutoff,
            ["date", "horizon", "prediction"],
        ]
        .sort_values(["date", "horizon"])
        .reset_index(drop=True)
    )

    perturbed_at_cutoff = (
        perturbed_predictions.loc[
            perturbed_predictions["cutoff_date"] == cutoff,
            ["date", "horizon", "prediction"],
        ]
        .sort_values(["date", "horizon"])
        .reset_index(drop=True)
    )

    assert not original_at_cutoff.empty
    pd.testing.assert_frame_equal(
        original_at_cutoff[["date", "horizon"]],
        perturbed_at_cutoff[["date", "horizon"]],
    )
    np.testing.assert_allclose(
        original_at_cutoff["prediction"].to_numpy(),
        perturbed_at_cutoff["prediction"].to_numpy(),
        rtol=0,
        atol=1e-12,
    )
