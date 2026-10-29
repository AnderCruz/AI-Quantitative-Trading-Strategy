"""Paired statistical tests comparing Ridge against existing baselines."""

from pathlib import Path
import sys

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
    ROOT / "reports" / "model_evaluation" / "LLOY.L"
    / "ridge_regression" / "ridge_baseline_aligned_predictions.csv"
)

OUTPUT_DIR = (
    ROOT / "reports" / "model_evaluation" / "LLOY.L"
    / "ridge_regression"
)

OUTPUT_PATH = OUTPUT_DIR / "ridge_paired_statistical_tests.csv"

BASELINES = ("zero_return", "historical_mean", "historical_median")
LOSSES = ("absolute", "squared")
RANDOM_SEED = 20261029


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    data = pd.read_csv(INPUT_PATH, parse_dates=["date"])

    required = {
        "date",
        "horizon",
        "ridge_prediction",
        "ridge_actual_return",
        "baseline_prediction",
        "baseline_actual_return",
        "baseline_model",
    }

    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    numeric_columns = [
        "horizon",
        "ridge_prediction",
        "ridge_actual_return",
        "baseline_prediction",
        "baseline_actual_return",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="raise")

    if data.duplicated(["date", "horizon", "baseline_model"]).any():
        raise ValueError("Duplicate date/horizon/baseline records found.")

    if not set(data["baseline_model"].unique()).issubset(set(BASELINES)):
        raise ValueError("Unexpected baseline model found.")

    numeric = data[
        [
            "ridge_prediction",
            "ridge_actual_return",
            "baseline_prediction",
            "baseline_actual_return",
        ]
    ].to_numpy(dtype=float)

    if not np.isfinite(numeric).all():
        raise ValueError("Non-finite prediction or actual-return values found.")

    if not np.allclose(
        data["ridge_actual_return"].to_numpy(),
        data["baseline_actual_return"].to_numpy(),
        rtol=0,
        atol=1e-12,
    ):
        raise ValueError("Ridge and baseline actual returns do not match.")

    rng = np.random.default_rng(RANDOM_SEED)
    records = []

    for horizon in sorted(data["horizon"].unique()):
        horizon_data = data.loc[data["horizon"] == horizon]

        for baseline in BASELINES:
            pair = horizon_data.loc[
                horizon_data["baseline_model"] == baseline
            ].sort_values("date")

            if pair.empty:
                raise ValueError(
                    f"No aligned observations for horizon={horizon}, "
                    f"baseline={baseline}"
                )

            actual = pair["ridge_actual_return"].to_numpy(dtype=float)
            ridge_prediction = pair["ridge_prediction"].to_numpy(dtype=float)
            baseline_prediction = pair["baseline_prediction"].to_numpy(dtype=float)

            ridge_error = ridge_prediction - actual
            baseline_error = baseline_prediction - actual

            ridge_losses = {
                "absolute": np.abs(ridge_error),
                "squared": np.square(ridge_error),
            }

            baseline_losses = {
                "absolute": np.abs(baseline_error),
                "squared": np.square(baseline_error),
            }

            for loss_name in LOSSES:
                # Negative values favour Ridge; positive values favour baseline.
                differences = (
                    ridge_losses[loss_name] - baseline_losses[loss_name]
                )

                hac_lag = min(max(int(horizon) - 1, 10), len(differences) - 1)
                hac = newey_west_mean_test(differences, hac_lag)

                ci_lower, ci_upper = circular_block_bootstrap_ci(
                    differences,
                    BOOTSTRAP_BLOCK_LENGTH,
                    BOOTSTRAP_REPETITIONS,
                    rng,
                )

                records.append(
                    {
                        "horizon": int(horizon),
                        "loss": loss_name,
                        "model_a": "ridge_regression",
                        "model_b": baseline,
                        "sample_size": len(differences),
                        "mean_loss_difference_ridge_minus_baseline": float(
                            differences.mean()
                        ),
                        **hac,
                        "bootstrap_block_length": min(
                            BOOTSTRAP_BLOCK_LENGTH, len(differences)
                        ),
                        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
                        "bootstrap_ci_95_lower": ci_lower,
                        "bootstrap_ci_95_upper": ci_upper,
                    }
                )

    results = pd.DataFrame(records)

    results["holm_adjusted_p_value"] = holm_adjust(results["hac_p_value"])
    results["significant_after_holm_5pct"] = (
        results["holm_adjusted_p_value"] < SIGNIFICANCE_LEVEL
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False)

    print("\nRIDGE PAIRED STATISTICAL TESTS")
    print("=" * 100)
    print(f"Input: {INPUT_PATH.relative_to(ROOT)}")
    print(f"Output: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Observations used: {len(data)} aligned model-pair records")
    print(f"Comparisons: {len(results)}")
    print(f"Bootstrap repetitions: {BOOTSTRAP_REPETITIONS}")
    print(f"Bootstrap block length: {BOOTSTRAP_BLOCK_LENGTH}")
    print("HAC lag: max(horizon - 1, 10), capped at sample_size - 1")
    print("Mean loss difference: Ridge minus baseline")
    print("Negative differences favour Ridge.")
    print("Final Test: not used.")
    print("Backtesting: not performed.")

    columns = [
        "horizon",
        "loss",
        "model_b",
        "sample_size",
        "mean_loss_difference_ridge_minus_baseline",
        "hac_p_value",
        "holm_adjusted_p_value",
        "bootstrap_ci_95_lower",
        "bootstrap_ci_95_upper",
        "significant_after_holm_5pct",
    ]

    print("\nRESULTS")
    print(results[columns].to_string(index=False, float_format=lambda x: f"{x:.8f}"))

    significant = results.loc[results["significant_after_holm_5pct"]]

    print("\nSIGNIFICANT RESULTS AFTER HOLM CORRECTION")
    if significant.empty:
        print("None at the 5% significance level.")
    else:
        print(
            significant[columns].to_string(
                index=False, float_format=lambda x: f"{x:.8f}"
            )
        )

    print("\nDecision aid:")
    print("- Negative mean differences favour Ridge.")
    print("- Positive mean differences favour the baseline.")
    print("- Check adjusted p-values and bootstrap intervals together.")
    print("- Statistical significance alone does not establish trading profitability.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
