"""Compare Ridge and existing baselines on identical validation observations."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.baseline_evaluation import _calculate_metrics


ROOT = Path(__file__).resolve().parents[1]

BASELINE_PATH = (
    ROOT / "reports" / "baseline_evaluation" / "baseline_predictions.csv"
)

RIDGE_PATH = (
    ROOT
    / "reports"
    / "model_evaluation"
    / "LLOY.L"
    / "ridge_regression"
    / "ridge_validation_predictions.csv"
)

OUTPUT_DIR = (
    ROOT
    / "reports"
    / "model_evaluation"
    / "LLOY.L"
    / "ridge_regression"
)

BASELINE_MODELS = (
    "zero_return",
    "historical_mean",
    "historical_median",
)

KEYS = ["date", "horizon"]


def main() -> None:
    baseline = pd.read_csv(BASELINE_PATH, parse_dates=["date"])
    ridge = pd.read_csv(RIDGE_PATH, parse_dates=["date"])

    required = {
        "date",
        "horizon",
        "model",
        "prediction",
        "actual_return",
    }

    for name, frame in (("baseline", baseline), ("ridge", ridge)):
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(
                f"{name} predictions are missing columns: "
                + ", ".join(sorted(missing))
            )

    if ridge.duplicated(KEYS).any():
        raise ValueError("Ridge predictions contain duplicate date-horizon keys.")

    baseline = baseline.loc[
        baseline["model"].isin(BASELINE_MODELS)
    ].copy()

    if baseline.duplicated(KEYS + ["model"]).any():
        raise ValueError(
            "Baseline predictions contain duplicate date-horizon-model keys."
        )

    # Use exactly the date-horizon observations scored by Ridge.
    common_keys = ridge[KEYS].drop_duplicates()

    aligned = common_keys.merge(
        ridge[KEYS + ["prediction", "actual_return"]].rename(
            columns={
                "prediction": "ridge_prediction",
                "actual_return": "ridge_actual_return",
            }
        ),
        on=KEYS,
        how="left",
        validate="one_to_one",
    )

    aligned_records = []

    for model_name in BASELINE_MODELS:
        model_rows = baseline.loc[
            baseline["model"] == model_name,
            KEYS + ["prediction", "actual_return"],
        ].rename(
            columns={
                "prediction": "baseline_prediction",
                "actual_return": "baseline_actual_return",
            }
        )

        joined = aligned.merge(
            model_rows,
            on=KEYS,
            how="left",
            validate="one_to_one",
        )

        if joined["baseline_prediction"].isna().any():
            raise ValueError(
                f"Missing {model_name} predictions on Ridge evaluation dates."
            )

        if joined["baseline_actual_return"].isna().any():
            raise ValueError(
                f"Missing actual returns for {model_name}."
            )

        if not np.allclose(
            joined["ridge_actual_return"],
            joined["baseline_actual_return"],
            rtol=1e-9,
            atol=1e-12,
        ):
            raise ValueError(
                f"Actual returns differ between Ridge and {model_name}."
            )

        joined["baseline_model"] = model_name
        aligned_records.append(joined)

    aligned_predictions = pd.concat(
        aligned_records,
        ignore_index=True,
    )

    metric_records = []

    for horizon in sorted(ridge["horizon"].unique()):
        ridge_rows = ridge.loc[ridge["horizon"] == horizon]

        metrics = _calculate_metrics(
            actual=ridge_rows["actual_return"],
            predicted=ridge_rows["prediction"],
        )

        metric_records.append(
            {
                "horizon": int(horizon),
                "model": "ridge_regression",
                **metrics,
            }
        )

        for model_name in BASELINE_MODELS:
            rows = aligned_predictions.loc[
                (aligned_predictions["horizon"] == horizon)
                & (aligned_predictions["baseline_model"] == model_name)
            ]

            metrics = _calculate_metrics(
                actual=rows["ridge_actual_return"],
                predicted=rows["baseline_prediction"],
            )

            metric_records.append(
                {
                    "horizon": int(horizon),
                    "model": model_name,
                    **metrics,
                }
            )

    metrics_frame = pd.DataFrame(metric_records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    aligned_predictions.to_csv(
        OUTPUT_DIR / "ridge_baseline_aligned_predictions.csv",
        index=False,
    )

    metrics_frame.to_csv(
        OUTPUT_DIR / "ridge_baseline_comparison_metrics.csv",
        index=False,
    )

    print("COMPARISON: IDENTICAL RIDGE VALIDATION OBSERVATIONS")
    print("=" * 72)
    print(metrics_frame.to_string(index=False))
    print("\nOBSERVATION COUNTS")
    print(
        metrics_frame[["horizon", "model", "sample_size"]]
        .to_string(index=False)
    )
    print("\nOUTPUT FILES")
    print(OUTPUT_DIR / "ridge_baseline_comparison_metrics.csv")
    print(OUTPUT_DIR / "ridge_baseline_aligned_predictions.csv")


if __name__ == "__main__":
    main()
