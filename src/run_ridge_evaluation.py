"""Run Ridge walk-forward evaluation using the approved validation period."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from src.feature_target_pipeline import (
    FEATURE_COLUMNS,
    MATURITY_COLUMNS,
    build_feature_target_dataset,
)
from src.ridge_evaluation import evaluate_ridge_walk_forward
from src.supervised_models import DEFAULT_RIDGE_ALPHA


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TICKER = "LLOY.L"

RAW_DATA_PATH = (
    PROJECT_ROOT / "data" / "raw" / "yahoo" / "configured" / f"{TICKER}.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "model_evaluation"
    / TICKER
    / "ridge_regression"
)

DEVELOPMENT_START = date(2016, 10, 24)
DEVELOPMENT_END = date(2023, 10, 20)

VALIDATION_START = date(2023, 10, 23)
VALIDATION_END = date(2025, 10, 22)

HORIZONS = (1, 5, 10)
MIN_TRAINING_SAMPLES = 500


def main() -> None:
    """Load approved historical data, evaluate Ridge and save the results."""

    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Historical data file not found: {RAW_DATA_PATH}"
        )

    raw_history = pd.read_csv(RAW_DATA_PATH)

    required_columns = {"date", "ticker", "Open", "Close"}
    missing_columns = required_columns.difference(raw_history.columns)

    if missing_columns:
        raise ValueError(
            "Historical data is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    raw_history["date"] = pd.to_datetime(
        raw_history["date"],
        errors="raise",
    )

    if raw_history["ticker"].nunique() != 1:
        raise ValueError(
            "The historical file must contain exactly one ticker."
        )

    if raw_history["ticker"].iloc[0] != TICKER:
        raise ValueError(
            f"Expected ticker {TICKER}, "
            f"received {raw_history['ticker'].iloc[0]}."
        )

    raw_history = (
        raw_history.loc[
            raw_history["date"].dt.date <= VALIDATION_END
        ]
        .sort_values("date")
        .reset_index(drop=True)
    )

    if raw_history.empty:
        raise ValueError(
            "No historical observations are available through validation end."
        )

    if raw_history["date"].dt.date.max() != VALIDATION_END:
        raise ValueError(
            "The available history does not end on the approved "
            f"validation date {VALIDATION_END}."
        )

    # Reuse the project's existing feature, target and maturity pipeline.
    integrated = build_feature_target_dataset(raw_history)

    history = integrated.loc[:, ["date", "ticker"]].copy()

    features = integrated.loc[:, list(FEATURE_COLUMNS)].copy()

    target_columns = [
        f"forward_return_{horizon}d"
        for horizon in HORIZONS
    ]
    targets = integrated.loc[:, target_columns].copy()

    maturity_dates = integrated.loc[:, list(MATURITY_COLUMNS)].copy()

    # Preserve the same row index across every input DataFrame.
    assert history.index.equals(features.index)
    assert history.index.equals(targets.index)
    assert history.index.equals(maturity_dates.index)

    # Ensure the Final Test period cannot enter this evaluation.
    assert history["date"].dt.date.max() == VALIDATION_END

    print("=" * 72)
    print("RIDGE REGRESSION WALK-FORWARD EVALUATION")
    print("=" * 72)
    print(f"Ticker: {TICKER}")
    print(f"Development: {DEVELOPMENT_START} to {DEVELOPMENT_END}")
    print(f"Validation:  {VALIDATION_START} to {VALIDATION_END}")
    print(f"Horizons: {HORIZONS}")
    print(f"Ridge alpha: {DEFAULT_RIDGE_ALPHA}")
    print(f"Minimum training samples: {MIN_TRAINING_SAMPLES}")
    print(f"Historical observations loaded: {len(history)}")
    print(f"Last permitted session: {history['date'].max().date()}")
    print("Final Test data: excluded")
    print("Backtesting: not performed")
    print("=" * 72)

    predictions, metrics = evaluate_ridge_walk_forward(
        history=history,
        features=features,
        targets=targets,
        maturity_dates=maturity_dates,
        development_start=DEVELOPMENT_START,
        development_end=DEVELOPMENT_END,
        validation_start=VALIDATION_START,
        validation_end=VALIDATION_END,
        horizons=HORIZONS,
        alpha=DEFAULT_RIDGE_ALPHA,
        min_training_samples=MIN_TRAINING_SAMPLES,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    predictions_path = OUTPUT_DIR / "ridge_validation_predictions.csv"
    metrics_path = OUTPUT_DIR / "ridge_validation_metrics.csv"
    metadata_path = OUTPUT_DIR / "ridge_validation_run.json"

    predictions.to_csv(predictions_path, index=False)
    metrics.to_csv(metrics_path, index=False)

    run_metadata = {
        "ticker": TICKER,
        "model": "ridge_regression",
        "alpha": DEFAULT_RIDGE_ALPHA,
        "horizons": list(HORIZONS),
        "development_start": DEVELOPMENT_START.isoformat(),
        "development_end": DEVELOPMENT_END.isoformat(),
        "validation_start": VALIDATION_START.isoformat(),
        "validation_end": VALIDATION_END.isoformat(),
        "last_loaded_session": history["date"].max().date().isoformat(),
        "historical_observations": len(history),
        "minimum_training_samples": MIN_TRAINING_SAMPLES,
        "prediction_count": len(predictions),
        "final_test_used": False,
        "backtesting_performed": False,
        "predictions_file": predictions_path.name,
        "metrics_file": metrics_path.name,
    }

    metadata_path.write_text(
        json.dumps(run_metadata, indent=2),
        encoding="utf-8",
    )

    print("\nVALIDATION METRICS")
    print(metrics.to_string(index=False))

    print("\nPREDICTION COUNTS BY HORIZON")
    print(
        predictions.groupby("horizon")
        .size()
        .rename("prediction_count")
        .to_string()
    )

    print("\nTRAINING SAMPLE SIZE RANGE BY HORIZON")
    print(
        predictions.groupby("horizon")["training_sample_size"]
        .agg(["min", "max"])
        .to_string()
    )

    print("\nOUTPUT FILES")
    print(predictions_path)
    print(metrics_path)
    print(metadata_path)


if __name__ == "__main__":
    main()
