"""Generic weekly expanding-window evaluation for supervised return forecasts."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from src.baseline_evaluation import _calculate_metrics
from src.feature_target_pipeline import FEATURE_COLUMNS
from src.temporal_split import get_training_eligibility_mask

SUPPORTED_HORIZONS = (1, 5, 10)


def _as_date(value: Any) -> date:
    """Normalise pandas, NumPy and Python date values to ``datetime.date``."""
    if pd.isna(value):
        raise ValueError("Dates must not contain missing values.")
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _weekly_cutoffs(observed_dates: Iterable[date]) -> list[date]:
    """Return the last observed session in each ISO calendar week."""
    by_week: dict[tuple[int, int], date] = {}
    for session_date in sorted({_as_date(value) for value in observed_dates}):
        iso = session_date.isocalendar()
        by_week[(iso.year, iso.week)] = session_date
    return sorted(by_week.values())


def _validate_inputs(
    history: pd.DataFrame,
    features: pd.DataFrame,
    targets: pd.DataFrame,
    maturity_dates: pd.DataFrame,
) -> None:
    frames = (history, features, targets, maturity_dates)
    if not all(isinstance(frame, pd.DataFrame) for frame in frames):
        raise TypeError("history, features, targets and maturity_dates must be DataFrames.")

    missing_history = {"date", "ticker"}.difference(history.columns)
    if missing_history:
        raise ValueError(
            "history is missing required columns: " + ", ".join(sorted(missing_history))
        )
    missing_features = set(FEATURE_COLUMNS).difference(features.columns)
    if missing_features:
        raise ValueError(
            "features is missing required columns: " + ", ".join(sorted(missing_features))
        )
    if not history.index.equals(features.index):
        raise ValueError("history and features must have identical indices.")
    if not history.index.equals(targets.index):
        raise ValueError("history and targets must have identical indices.")
    if not history.index.equals(maturity_dates.index):
        raise ValueError("history and maturity_dates must have identical indices.")
    if history.empty:
        raise ValueError("Input data must not be empty.")
    if history["date"].duplicated().any():
        raise ValueError("history dates must be unique.")
    if history["ticker"].nunique(dropna=False) != 1:
        raise ValueError("Walk-forward evaluation requires a single ticker.")


def evaluate_walk_forward(
    *,
    history: pd.DataFrame,
    features: pd.DataFrame,
    targets: pd.DataFrame,
    maturity_dates: pd.DataFrame,
    development_start: date,
    development_end: date,
    validation_start: date,
    validation_end: date,
    model_factory: Callable[[], Any],
    model_name: str,
    horizons: Iterable[int] = SUPPORTED_HORIZONS,
    min_training_samples: int = 500,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate a supervised regressor with weekly expanding-window forecasts.

    The factory must return a fresh, unfitted estimator each time it is called.
    Only training labels that have matured by the retraining cutoff are eligible.
    Validation outcomes are scored only when their maturity date is no later than
    ``validation_end``. Final Test observations must not be supplied to this call.
    """
    _validate_inputs(history, features, targets, maturity_dates)

    development_start, development_end = map(
        _as_date, (development_start, development_end)
    )
    validation_start, validation_end = map(
        _as_date, (validation_start, validation_end)
    )

    if development_start > development_end:
        raise ValueError("development_start must not be after development_end.")
    if validation_start > validation_end:
        raise ValueError("validation_start must not be after validation_end.")
    if development_end >= validation_start:
        raise ValueError("Development and validation periods must not overlap.")
    if (
        isinstance(min_training_samples, bool)
        or not isinstance(min_training_samples, int)
        or min_training_samples < 1
    ):
        raise ValueError("min_training_samples must be a positive integer.")
    if not callable(model_factory):
        raise TypeError("model_factory must be callable.")
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be a non-empty string.")

    horizons = tuple(horizons)
    if not horizons or any(
        isinstance(horizon, bool)
        or not isinstance(horizon, (int, np.integer))
        or horizon not in SUPPORTED_HORIZONS
        for horizon in horizons
    ):
        raise ValueError(f"horizons must be a non-empty subset of {SUPPORTED_HORIZONS}.")
    if len(set(horizons)) != len(horizons):
        raise ValueError("horizons must not contain duplicates.")

    date_values = history["date"].map(_as_date)
    if not date_values.is_monotonic_increasing:
        raise ValueError("history must be sorted in ascending date order.")

    feature_values = features.loc[:, FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    feature_array = feature_values.to_numpy(dtype=float)
    finite_features = pd.Series(
        np.isfinite(feature_array).all(axis=1), index=features.index
    )

    in_scope = date_values.map(lambda value: development_start <= value <= validation_end)
    cutoffs = _weekly_cutoffs(date_values.loc[in_scope].tolist())
    validation_dates = sorted(
        {value for value in date_values if validation_start <= value <= validation_end}
    )
    if not validation_dates:
        raise ValueError("No observations are available in the validation period.")

    schedule: dict[date, date] = {}
    for session_date in validation_dates:
        prior_cutoffs = [cutoff for cutoff in cutoffs if cutoff <= session_date]
        if not prior_cutoffs:
            raise ValueError(f"No retraining cutoff is available for {session_date}.")
        schedule[session_date] = prior_cutoffs[-1]

    prediction_records: list[dict[str, Any]] = []
    fitted_cache: dict[tuple[int, date], tuple[Any, int]] = {}

    for horizon in horizons:
        target_column = f"forward_return_{horizon}d"
        maturity_column = f"target_maturity_date_{horizon}d"
        if target_column not in targets.columns:
            raise ValueError(f"targets is missing {target_column!r}.")
        if maturity_column not in maturity_dates.columns:
            raise ValueError(f"maturity_dates is missing {maturity_column!r}.")

        y_all = pd.to_numeric(targets[target_column], errors="coerce")
        finite_targets = pd.Series(
            np.isfinite(y_all.to_numpy(dtype=float)), index=targets.index
        )

        for session_date in validation_dates:
            cutoff_date = schedule[session_date]
            cache_key = (int(horizon), cutoff_date)

            if cache_key not in fitted_cache:
                eligibility = get_training_eligibility_mask(
                    history,
                    maturity_dates,
                    development_start,
                    cutoff_date,
                    cutoff_date,
                )[maturity_column].astype(bool)
                eligible = eligibility & finite_features & y_all.notna() & finite_targets
                train_index = history.index[eligible]
                training_size = len(train_index)
                if training_size < min_training_samples:
                    raise ValueError(
                        "Insufficient eligible training observations for "
                        f"horizon {horizon}d at cutoff {cutoff_date}: {training_size}; "
                        f"minimum required is {min_training_samples}."
                    )

                model = model_factory()
                if not callable(getattr(model, "fit", None)) or not callable(
                    getattr(model, "predict", None)
                ):
                    raise TypeError("model_factory must return an estimator with fit and predict methods.")
                model.fit(
                    feature_values.loc[train_index],
                    y_all.loc[train_index].to_numpy(dtype=float),
                )
                fitted_cache[cache_key] = (model, training_size)

            model, training_size = fitted_cache[cache_key]
            row_indices = history.index[date_values == session_date]
            if len(row_indices) != 1:
                raise ValueError(f"Expected exactly one row for {session_date}.")
            row_index = row_indices[0]
            if not bool(finite_features.loc[row_index]):
                continue

            actual = y_all.loc[row_index]
            maturity = maturity_dates.loc[row_index, maturity_column]
            if pd.isna(actual) or not np.isfinite(float(actual)) or pd.isna(maturity):
                continue
            if _as_date(maturity) > validation_end:
                continue

            prediction = float(
                model.predict(feature_values.loc[[row_index]])[0]
            )
            if not np.isfinite(prediction):
                raise ValueError(
                    f"Model {model_name!r} returned a non-finite prediction "
                    f"for {session_date}, horizon {horizon}d."
                )
            prediction_records.append(
                {
                    "date": session_date,
                    "cutoff_date": cutoff_date,
                    "horizon": int(horizon),
                    "model": model_name,
                    "prediction": prediction,
                    "actual_return": float(actual),
                    "training_sample_size": training_size,
                }
            )

    predictions = pd.DataFrame(prediction_records)
    if predictions.empty:
        raise ValueError("No matured validation targets are available for evaluation.")

    metric_records = []
    for horizon, group in predictions.groupby("horizon", sort=True):
        metrics = _calculate_metrics(
            actual=group["actual_return"], predicted=group["prediction"]
        )
        metric_records.append(
            {"horizon": int(horizon), "model": model_name, **metrics}
        )

    return predictions, pd.DataFrame(metric_records)
