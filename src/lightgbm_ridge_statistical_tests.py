"""Run paired statistical comparisons of LightGBM, Ridge and baselines."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.baseline_statistical_tests import (
    BOOTSTRAP_BLOCK_LENGTH,
    BOOTSTRAP_REPETITIONS,
    SIGNIFICANCE_LEVEL,
    circular_block_bootstrap_ci,
    holm_adjust,
    newey_west_mean_test,
)


ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = (
    ROOT
    / "reports"
    / "model_evaluation"
    / "LLOY.L"
    / "lightgbm_regression"
    / "all_models_aligned_predictions.csv"
)

OUTPUT_DIR = INPUT_PATH.parent
OUTPUT_PATH = OUTPUT_DIR / "all_models_paired_statistical_tests.csv"

MODELS = (
    "lightgbm_regression",
    "ridge_regression",
    "zero_return",
    "historical_mean",
    "historical_median",
)

LOSSES = ("absolute", "squared")
RANDOM_SEED = 20261029


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    data = pd.read_csv(INPUT_PATH, parse_dates=["date"])

    required = {
        "date",
        "horizon",
        "model",
        "prediction",
        "actual_return",
    }
    missing = required.difference(data.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = data.loc[data["model"].isin(MODELS)].copy()

    if set(data["model"].unique()) != set(MODELS):
        raise ValueError("One or more required models are missing.")

    data["horizon"] = pd.to_numeric(
        data["horizon"], errors="raise"
    ).astype(int)

    for column in ("prediction", "actual_return"):
        data[column] = pd.to_numeric(data[column], errors="raise")

    if data.duplicated(["date", "horizon", "model"]).any():
        raise ValueError("Duplicate date/horizon/model records found.")

    numeric = data[["prediction", "actual_return"]].to_numpy(dtype=float)

    if not np.isfinite(numeric).all():
        raise ValueError("Non-finite prediction or actual-return values found.")

    # Ensure every model has identical dates and realised returns.
    key_counts = data.groupby(["date", "horizon"])["model"].nunique()

    if not (key_counts == len(MODELS)).all():
        raise ValueError("Model observations are not completely aligned.")

    actual_spread = (
        data.groupby(["date", "horizon"])["actual_return"]
        .agg(lambda values: values.max() - values.min())
    )

    if not np.allclose(
        actual_spread.to_numpy(), 0.0, rtol=0, atol=1e-12
    ):
        raise ValueError("Actual returns differ across models.")

    predictions = data.pivot(
        index=["date", "horizon"],
        columns="model",
        values="prediction",
    ).sort_index()

    actual = (
        data.drop_duplicates(["date", "horizon"])
        .set_index(["date", "horizon"])["actual_return"]
        .sort_index()
    )

    # Compare the two learned models against each other and against
    # each baseline. The three baselines are retained as references.
    comparisons = [
        ("lightgbm_regression", "ridge_regression"),
        *[
            (model, baseline)
            for model in ("lightgbm_regression", "ridge_regression")
            for baseline in (
                "zero_return",
                "historical_mean",
                "historical_median",
            )
        ],
    ]

    rng = np.random.default_rng(RANDOM_SEED)
    records = []

    for horizon in sorted(data["horizon"].unique()):
        horizon_index = predictions.index.get_level_values("horizon") == horizon
        horizon_predictions = predictions.loc[horizon_index]
        horizon_actual = actual.loc[horizon_predictions.index].to_numpy()

        for model_a, model_b in comparisons:
            prediction_a = horizon_predictions[model_a].to_numpy(dtype=float)
            prediction_b = horizon_predictions[model_b].to_numpy(dtype=float)

            error_a = prediction_a - horizon_actual
            error_b = prediction_b - horizon_actual

            losses_a = {
                "absolute": np.abs(error_a),
                "squared": np.square(error_a),
            }
            losses_b = {
                "absolute": np.abs(error_b),
                "squared": np.square(error_b),
            }

            for loss_name in LOSSES:
                # Negative differences favour model_a.
                differences = losses_a[loss_name] - losses_b[loss_name]

                hac_lag = min(
                    max(int(horizon) - 1, 10),
                    len(differences) - 1,
                )

                hac = newey_west_mean_test(differences, hac_lag)

                ci_lower, ci_upper = circular_block_bootstrap_ci(
                    differences,
                    min(BOOTSTRAP_BLOCK_LENGTH, len(differences)),
                    BOOTSTRAP_REPETITIONS,
                    rng,
                )

                records.append(
                    {
                        "horizon": int(horizon),
                        "loss": loss_name,
                        "model_a": model_a,
                        "model_b": model_b,
                        "sample_size": len(differences),
                        "mean_loss_difference_a_minus_b": float(
                            differences.mean()
                        ),
                        **hac,
                        "bootstrap_ci_95_lower": ci_lower,
                        "bootstrap_ci_95_upper": ci_upper,
                    }
                )

    results = pd.DataFrame(records)

    # Correct across the full family of planned pairwise tests.
    results["holm_adjusted_p_value"] = holm_adjust(
        results["hac_p_value"]
    )
    results["significant_after_holm_5pct"] = (
        results["holm_adjusted_p_value"] < SIGNIFICANCE_LEVEL
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False)

    print("\nPAIRED STATISTICAL COMPARISONS")
    print("=" * 110)
    print(f"Input: {INPUT_PATH.relative_to(ROOT)}")
    print(f"Output: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Comparisons: {len(results)}")
    print(f"Bootstrap repetitions: {BOOTSTRAP_REPETITIONS}")
    print(f"Bootstrap block length: {BOOTSTRAP_BLOCK_LENGTH}")
    print("Final Test used: False")
    print("Backtesting performed: False")
    print("Negative loss differences favour model_a.")

    display_columns = [
        "horizon",
        "loss",
        "model_a",
        "model_b",
        "sample_size",
        "mean_loss_difference_a_minus_b",
        "hac_p_value",
        "holm_adjusted_p_value",
        "bootstrap_ci_95_lower",
        "bootstrap_ci_95_upper",
        "significant_after_holm_5pct",
    ]

    print("\nRESULTS")
    print(
        results[display_columns].to_string(
            index=False,
            float_format=lambda value: f"{value:.8f}",
        )
    )

    significant = results.loc[
        results["significant_after_holm_5pct"]
    ]

    print("\nSIGNIFICANT COMPARISONS AFTER HOLM CORRECTION")
    if significant.empty:
        print("None at the 5% significance level.")
    else:
        print(
            significant[display_columns].to_string(
                index=False,
                float_format=lambda value: f"{value:.8f}",
            )
        )


if __name__ == "__main__":
    main()
