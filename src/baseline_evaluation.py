"""Evaluate return-forecasting baselines using chronological validation."""

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.baseline_models import (
    HistoricalMeanBaseline,
    HistoricalMedianBaseline,
    ZeroReturnBaseline,
    get_eligible_training_targets,
)


# Define the supported forecasting horizons and baseline models.
SUPPORTED_HORIZONS = (1, 5, 10)

BASELINE_MODELS = {
    "zero_return": ZeroReturnBaseline,
    "historical_mean": HistoricalMeanBaseline,
    "historical_median": HistoricalMedianBaseline,
}

def _validate_date(value, name):
    """Validate a calendar date used by the evaluation process."""

    # Require a date without a time component.
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime.date instance.")


def _get_week_end(date_value):
    """Return the Sunday associated with a calendar date."""

    # Use Monday as the first weekday and Sunday as the last.
    return date_value + timedelta(days=6 - date_value.weekday())


def _get_retraining_cutoffs(validation_dates):
    """Create weekly retraining cutoffs from observed validation sessions."""

    # Normalise and sort the available validation dates.
    unique_dates = sorted(set(validation_dates))

    if not unique_dates:
        raise ValueError("Validation dates cannot be empty.")

    # Select the final observed session of each calendar week.
    weekly_dates = {}

    for session_date in unique_dates:
        week_end = _get_week_end(session_date)
        weekly_dates[week_end] = session_date

    return sorted(weekly_dates.values())


def _calculate_metrics(actual, predicted):
    """Calculate forecasting metrics for aligned actual and predicted returns."""

    # Convert inputs into numeric arrays and validate their alignment.
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    if actual.ndim != 1 or predicted.ndim != 1:
        raise ValueError("Actual and predicted returns must be one-dimensional.")

    if actual.size != predicted.size:
        raise ValueError("Actual and predicted returns must have equal lengths.")

    if actual.size == 0:
        raise ValueError("At least one prediction is required for evaluation.")

    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Actual and predicted returns must be finite.")

    # Calculate errors and directional agreement.
    mae = float(mean_absolute_error(actual, predicted))
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))

    # A zero predicted return is treated as a non-positive direction.
    actual_direction = actual > 0
    predicted_direction = predicted > 0

    directional_accuracy = float(
        np.mean(actual_direction == predicted_direction)
    )

    # Correlation and R-squared require additional handling for constant data.
    if actual.size < 2 or np.ptp(actual) == 0 or np.ptp(predicted) == 0:
        spearman_correlation = np.nan
    else:
        spearman_correlation = float(
            spearmanr(actual, predicted).statistic
        )

    if actual.size < 2 or np.ptp(actual) == 0:
        r_squared = np.nan
    else:
        r_squared = float(r2_score(actual, predicted))

    return {
        "sample_size": int(actual.size),
        "mae": mae,
        "rmse": rmse,
        "directional_accuracy": directional_accuracy,
        "spearman_correlation": spearman_correlation,
        "r_squared": r_squared,
    }


def evaluate_baselines_walk_forward(
    history: pd.DataFrame,
    targets: pd.DataFrame,
    maturity_dates: pd.DataFrame,
    development_start: date,
    development_end: date,
    validation_start: date,
    validation_end: date,
    horizons: tuple[int, ...] = SUPPORTED_HORIZONS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate baseline models on validation observations chronologically.

    Models are updated after the final observed session of each calendar
    week. The training window expands from the development period into
    validation, including only targets that have matured by each retraining
    cutoff.

    Each prediction uses the latest retraining cutoff available on or before
    its observation date. Final-test observations are never used by this
    function.

    Returns:
        A tuple containing:
        - A prediction-level DataFrame.
        - A model-and-horizon metrics DataFrame.
    """

    # Validate the date boundaries.
    for name, value in (
        ("development_start", development_start),
        ("development_end", development_end),
        ("validation_start", validation_start),
        ("validation_end", validation_end),
    ):
        _validate_date(value, name)

    if development_start > development_end:
        raise ValueError("development_start must not exceed development_end.")

    if validation_start > validation_end:
        raise ValueError("validation_start must not exceed validation_end.")

    if development_end >= validation_start:
        raise ValueError("Development and validation periods must not overlap.")

    # Validate the supported horizons.
    if (
        not horizons
        or any(
            not isinstance(horizon, int)
            or isinstance(horizon, bool)
            or horizon not in SUPPORTED_HORIZONS
            for horizon in horizons
        )
        or len(set(horizons)) != len(horizons)
    ):
        raise ValueError(
            f"horizons must contain unique values from {SUPPORTED_HORIZONS}."
        )

    # Require the date and ticker identifiers needed for chronological work.
    if not isinstance(history, pd.DataFrame):
        raise TypeError("history must be a pandas DataFrame.")

    if "date" not in history.columns or "ticker" not in history.columns:
        raise ValueError("history must contain 'date' and 'ticker' columns.")

    if not history.index.equals(targets.index):
        raise ValueError("History and targets must have identical indices.")

    if not history.index.equals(maturity_dates.index):
        raise ValueError(
            "History and maturity dates must have identical indices."
        )

    if history["ticker"].nunique(dropna=False) != 1:
        raise ValueError(
            "This evaluator currently requires history for exactly one asset."
        )

    # Parse dates and construct a positional working table.
    parsed_dates = pd.to_datetime(history["date"], errors="raise")

    if parsed_dates.isna().any():
        raise ValueError("History contains missing observation dates.")

    working = pd.DataFrame(
        {
            "position": np.arange(len(history)),
            "date": parsed_dates.dt.date.to_numpy(),
        },
        index=history.index,
    )

    # Reject duplicate dates because this evaluator is for one asset.
    if working["date"].duplicated().any():
        raise ValueError("History contains duplicate observation dates.")

    # Restrict the prediction schedule to observed validation sessions.
    validation_rows = working.loc[
        working["date"].between(validation_start, validation_end)
    ].copy()

    if validation_rows.empty:
        raise ValueError("No historical observations exist in validation.")

    # Extract the observed validation session dates in chronological order.
    validation_dates = validation_rows["date"].tolist()

    # Build the weekly retraining schedule using observed sessions
    # from the development and validation periods only.
    schedule_rows = working.loc[
        working["date"].between(development_start, validation_end)
    ]

    schedule_dates = schedule_rows["date"].tolist()

    # Identify the final observed session of each calendar week.
    retraining_cutoffs = _get_retraining_cutoffs(schedule_dates)

    # Assign the latest available retraining cutoff to each validation
    # session, never using a cutoff from a future session.
    cutoff_by_date = {}

    for session_date in validation_dates:
        available_cutoffs = [
            cutoff
            for cutoff in retraining_cutoffs
            if cutoff <= session_date
        ]

        if not available_cutoffs:
            raise ValueError(
                f"No valid retraining cutoff exists for {session_date}."
            )

        cutoff_by_date[session_date] = available_cutoffs[-1]

    # Cache training targets at each weekly cutoff and horizon.
    training_cache = {}
    prediction_records = []

    for horizon in horizons:
        target_column = f"forward_return_{horizon}d"

        if target_column not in targets.columns:
            raise ValueError(f"Missing target column: {target_column}")

        maturity_column = f"target_maturity_date_{horizon}d"

        if maturity_column not in maturity_dates.columns:
            raise ValueError(f"Missing maturity column: {maturity_column}")

        for session_date in validation_dates:
            cutoff_date = cutoff_by_date[session_date]
            cache_key = (horizon, cutoff_date)

            # Fit or refresh models only when the weekly cutoff changes.
            if cache_key not in training_cache:
                eligible_targets = get_eligible_training_targets(
                    history=history,
                    targets=targets,
                    maturity_dates=maturity_dates,
                    horizon=horizon,
                    period_start=development_start,
                    period_end=cutoff_date,
                    cutoff_date=cutoff_date,
                )

                fitted_models = {}

                for model_name, model_class in BASELINE_MODELS.items():
                    fitted_models[model_name] = model_class().fit(
                        eligible_targets
                    )

                training_cache[cache_key] = (
                    eligible_targets,
                    fitted_models,
                )

            eligible_targets, fitted_models = training_cache[cache_key]

            # Retrieve the actual return when it is available in the dataset.
            row_index = validation_rows.index[
                validation_rows["date"] == session_date
            ][0]

            actual_return = targets.loc[row_index, target_column]

            # Skip outcomes that have not yet matured in the supplied history.
            if pd.isna(actual_return):
                continue

            actual_return = float(actual_return)

            if not np.isfinite(actual_return):
                raise ValueError("Observed validation targets must be finite.")

            # Generate a prediction from each baseline.
            for model_name, model in fitted_models.items():
                prediction = float(model.predict(1)[0])

                prediction_records.append(
                    {
                        "date": session_date,
                        "cutoff_date": cutoff_date,
                        "horizon": horizon,
                        "model": model_name,
                        "prediction": prediction,
                        "actual_return": actual_return,
                        "training_sample_size": len(eligible_targets),
                    }
                )

    # Require at least one evaluable prediction.
    predictions = pd.DataFrame(prediction_records)

    if predictions.empty:
        raise ValueError(
            "No matured validation targets are available for evaluation."
        )

    # Calculate metrics separately for each model and horizon.
    metric_records = []

    for (horizon, model_name), group in predictions.groupby(
        ["horizon", "model"],
        sort=True,
    ):
        metrics = _calculate_metrics(
            actual=group["actual_return"],
            predicted=group["prediction"],
        )

        metric_records.append(
            {
                "horizon": horizon,
                "model": model_name,
                **metrics,
            }
        )

    metrics_table = pd.DataFrame(metric_records)

    return predictions, metrics_table