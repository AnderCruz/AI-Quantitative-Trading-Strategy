"""Paired statistical comparisons for baseline return forecasts.

Reads existing predictions only; it does not train or refit models.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import norm

INPUT_PATH = Path("reports/baseline_evaluation/baseline_predictions.csv")
OUTPUT_DIR = Path("reports/baseline_evaluation")
OUTPUT_PATH = OUTPUT_DIR / "baseline_paired_statistical_tests_recomputed.csv"
BOOTSTRAP_REPETITIONS = 5_000
BOOTSTRAP_BLOCK_LENGTH = 10
RANDOM_SEED = 20261026
SIGNIFICANCE_LEVEL = 0.05


def validate_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Validate and chronologically sort baseline predictions."""
    required = {"date", "horizon", "model", "prediction", "actual_return"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = predictions.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["horizon"] = pd.to_numeric(data["horizon"], errors="raise").astype(int)
    data["prediction"] = pd.to_numeric(data["prediction"], errors="raise")
    data["actual_return"] = pd.to_numeric(data["actual_return"], errors="raise")

    if data.duplicated(["date", "horizon", "model"]).any():
        raise ValueError("Duplicate date, horizon and model records were found.")
    numeric = data[["prediction", "actual_return"]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError("Predictions and actual returns must be finite.")
    if (data["horizon"] <= 0).any():
        raise ValueError("Forecast horizons must be positive.")
    models = sorted(data["model"].unique())
    if len(models) != 3:
        raise ValueError(f"Expected three baseline models; found {models}")
    return data.sort_values(["horizon", "date", "model"]).reset_index(drop=True)


def holm_adjust(p_values: Iterable[float]) -> np.ndarray:
    """Return Holm step-down adjusted p-values in their original order."""
    values = np.asarray(list(p_values), dtype=float)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("At least one p-value is required.")
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("P-values must be finite and between zero and one.")
    order = np.argsort(values)
    adjusted = np.empty(len(values), dtype=float)
    running_maximum = 0.0
    for rank, index in enumerate(order):
        candidate = (len(values) - rank) * values[index]
        running_maximum = max(running_maximum, candidate)
        adjusted[index] = min(running_maximum, 1.0)
    return adjusted


def newey_west_mean_test(values: Iterable[float], lag: int) -> dict[str, float]:
    """Test zero mean using Bartlett-kernel HAC variance and a normal reference."""
    x = np.asarray(list(values), dtype=float)
    if x.ndim != 1 or len(x) < 3:
        raise ValueError("At least three paired observations are required.")
    if not np.isfinite(x).all():
        raise ValueError("HAC input values must be finite.")
    if lag < 0:
        raise ValueError("HAC lag cannot be negative.")

    n = len(x)
    lag = min(int(lag), n - 1)
    demeaned = x - x.mean()
    long_run_variance = float(np.dot(demeaned, demeaned) / n)

    for k in range(1, lag + 1):
        gamma_k = float(np.dot(demeaned[k:], demeaned[:-k]) / n)
        weight = 1.0 - k / (lag + 1.0)
        long_run_variance += 2.0 * weight * gamma_k

    if long_run_variance < -1e-12:
        raise ArithmeticError(f"Estimated HAC long-run variance is negative: {long_run_variance}")
    long_run_variance = max(long_run_variance, 0.0)
    standard_error = float(np.sqrt(long_run_variance / n))

    # Handle degenerate cases where HAC inference is not defined.
    if standard_error == 0.0:
        z_statistic = float("nan")
        p_value = float("nan")
    else:
        z_statistic = float(x.mean() / standard_error)
        p_value = float(2.0 * norm.sf(abs(z_statistic)))
    
    return {
        "hac_lag": int(lag),
        "hac_long_run_variance": long_run_variance,
        "hac_standard_error": standard_error,
        "hac_z_statistic": z_statistic,
        "hac_p_value": p_value,
    }


def circular_block_bootstrap_ci(
    values: Iterable[float],
    block_size: int,
    repetitions: int,
    rng: np.random.Generator,
) -> tuple[float, float]:
    """Calculate a percentile confidence interval using circular blocks."""
    x = np.asarray(list(values), dtype=float)
    if x.ndim != 1 or len(x) < 3:
        raise ValueError("At least three observations are required for bootstrap.")
    if not np.isfinite(x).all():
        raise ValueError("Bootstrap input values must be finite.")
    if block_size < 1 or repetitions < 1:
        raise ValueError("Block size and repetitions must be positive.")

    n = len(x)
    block_size = min(int(block_size), n)
    blocks_needed = int(np.ceil(n / block_size))
    means = np.empty(repetitions, dtype=float)
    offsets = np.arange(block_size)

    for repetition in range(repetitions):
        sampled = []
        for _ in range(blocks_needed):
            start = int(rng.integers(0, n))
            sampled.extend(x[(start + offsets) % n])
        means[repetition] = np.mean(sampled[:n])

    lower, upper = np.quantile(means, [0.025, 0.975])
    return float(lower), float(upper)


def run_paired_tests(
    predictions: pd.DataFrame,
    bootstrap_repetitions: int = BOOTSTRAP_REPETITIONS,
    bootstrap_block_length: int = BOOTSTRAP_BLOCK_LENGTH,
    random_seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Compare baseline pairs for absolute and squared forecast errors."""
    data = validate_predictions(predictions)
    models = sorted(data["model"].unique())
    rng = np.random.default_rng(random_seed)
    records = []

    for horizon in sorted(data["horizon"].unique()):
        subset = data.loc[data["horizon"] == horizon]
        actual_by_date = subset.pivot(
            index="date", columns="model", values="actual_return"
        ).sort_index()
        prediction_by_date = subset.pivot(
            index="date", columns="model", values="prediction"
        ).sort_index()

        if actual_by_date.isna().any().any():
            raise ValueError(f"Models do not share actual returns for horizon {horizon}.")
        if prediction_by_date.isna().any().any():
            raise ValueError(f"Models do not share prediction dates for horizon {horizon}.")
        if not np.allclose(
            actual_by_date.to_numpy(),
            actual_by_date.iloc[:, [0]].to_numpy(),
            rtol=0,
            atol=1e-12,
        ):
            raise ValueError(f"Actual returns differ across models for horizon {horizon}.")

        actual = actual_by_date.iloc[:, 0]
        losses = {}
        for model in models:
            errors = prediction_by_date[model] - actual
            losses[model] = {"absolute": errors.abs(), "squared": errors.pow(2)}

        for model_a, model_b in combinations(models, 2):
            for loss_name in ("absolute", "squared"):
                differences = (
                    losses[model_a][loss_name] - losses[model_b][loss_name]
                ).to_numpy(dtype=float)
                n = len(differences)
                hac_lag = min(max(int(horizon) - 1, 10), n - 1)
                hac = newey_west_mean_test(differences, hac_lag)
                ci_lower, ci_upper = circular_block_bootstrap_ci(
                    differences, bootstrap_block_length, bootstrap_repetitions, rng
                )
                records.append({
                    "horizon": int(horizon),
                    "loss": loss_name,
                    "model_a": model_a,
                    "model_b": model_b,
                    "sample_size": n,
                    "mean_loss_difference_a_minus_b": float(differences.mean()),
                    **hac,
                    "bootstrap_block_length": min(bootstrap_block_length, n),
                    "bootstrap_repetitions": bootstrap_repetitions,
                    "bootstrap_ci_95_lower": ci_lower,
                    "bootstrap_ci_95_upper": ci_upper,
                })

    results = pd.DataFrame(records)
    results["holm_adjusted_p_value"] = holm_adjust(results["hac_p_value"])
    results["significant_after_holm_5pct"] = (
        results["holm_adjusted_p_value"] < SIGNIFICANCE_LEVEL
    )
    return results


def main() -> None:
    """Run statistical tests on existing predictions and write a new report."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Baseline predictions not found: {INPUT_PATH}")
    predictions = pd.read_csv(INPUT_PATH)
    results = run_paired_tests(predictions)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False)

    print("PAIRED BASELINE STATISTICAL TESTS COMPLETED")
    print(f"Input: {INPUT_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Comparisons: {len(results)}")
    print(f"Bootstrap repetitions: {BOOTSTRAP_REPETITIONS}")
    print(f"Bootstrap block length: {BOOTSTRAP_BLOCK_LENGTH}")
    print("HAC lag: max(horizon - 1, 10), capped at sample_size - 1")
    print("\nResults significant after Holm correction:")
    significant = results.loc[results["significant_after_holm_5pct"]]
    if significant.empty:
        print("No comparisons reached the 5% significance level after correction.")
    else:
        print(significant[[
            "horizon", "loss", "model_a", "model_b",
            "mean_loss_difference_a_minus_b", "hac_p_value",
            "holm_adjusted_p_value", "bootstrap_ci_95_lower",
            "bootstrap_ci_95_upper",
        ]].to_string(index=False))


if __name__ == "__main__":
    main()
