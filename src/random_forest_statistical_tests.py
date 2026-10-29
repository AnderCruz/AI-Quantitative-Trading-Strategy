"""Compare existing Random Forest forecasts against established models."""

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

from src.baseline_statistical_tests import (
    SIGNIFICANCE_LEVEL,
    circular_block_bootstrap_ci,
    holm_adjust,
    newey_west_mean_test,
)

ROOT = Path(__file__).resolve().parents[1]

REFERENCE_PATH = (
    ROOT
    / "reports"
    / "model_evaluation"
    / "LLOY.L"
    / "lightgbm_regression"
    / "all_models_aligned_predictions.csv"
)

RF_PATH = (
    ROOT
    / "reports"
    / "model_evaluation"
    / "LLOY.L"
    / "random_forest_regression"
    / "random_forest_validation_predictions.csv"
)

RAW_PATH = (
    ROOT
    / "data"
    / "raw"
    / "yahoo"
    / "configured"
    / "LLOY.L.csv"
)

OUTPUT_DIR = (
    ROOT
    / "reports"
    / "model_evaluation"
    / "LLOY.L"
    / "random_forest_regression"
)

OUTPUT_PATH = OUTPUT_DIR / "random_forest_paired_statistical_tests.csv"
ALIGNED_PATH = OUTPUT_DIR / "random_forest_all_models_aligned_predictions.csv"

RF_MODEL = "random_forest_regression"
REFERENCE_MODELS = (
    "ridge_regression",
    "lightgbm_regression",
    "zero_return",
    "historical_mean",
    "historical_median",
)

HORIZONS = (1, 5, 10)
GLOBAL_SEED = 20261028
BOOTSTRAP_REPETITIONS = 5000


def stable_rng(horizon, model_b, metric):
    """Create a reproducible RNG for each comparison."""
    identifier = f"{RF_MODEL}|{horizon}|{model_b}|{metric}"
    digest = sha256(identifier.encode("utf-8")).digest()
    offset = int.from_bytes(digest[:4], "big")
    return np.random.default_rng((GLOBAL_SEED + offset) % (2**32))


def load_and_align_predictions():
    """Combine existing reference predictions with Random Forest outputs."""
    for path in (REFERENCE_PATH, RF_PATH, RAW_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Required input not found: {path}")

    reference = pd.read_csv(REFERENCE_PATH)
    random_forest = pd.read_csv(RF_PATH)

    required = {
        "date", "horizon", "model", "prediction", "actual_return"
    }

    for name, frame in (
        ("Reference predictions", reference),
        ("Random Forest predictions", random_forest),
    ):
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{name} missing columns: {sorted(missing)}")

    reference = reference.loc[
        reference["model"].isin(REFERENCE_MODELS)
    ].copy()

    if set(reference["model"].unique()) != set(REFERENCE_MODELS):
        raise ValueError("One or more reference models are missing.")

    if random_forest["model"].nunique() != 1:
        raise ValueError("Random Forest file contains unexpected model names.")

    if set(random_forest["model"].unique()) != {RF_MODEL}:
        raise ValueError("Random Forest model name does not match expectation.")

    data = pd.concat(
        [
            reference,
            random_forest.loc[:, list(required)],
        ],
        ignore_index=True,
    )

    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["horizon"] = pd.to_numeric(
        data["horizon"], errors="raise"
    ).astype(int)

    for column in ("prediction", "actual_return"):
        data[column] = pd.to_numeric(data[column], errors="raise")

    data = data.loc[data["horizon"].isin(HORIZONS)].copy()

    if data.duplicated(["date", "horizon", "model"]).any():
        raise ValueError("Duplicate date/horizon/model observations found.")

    values = data[["prediction", "actual_return"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite predictions or actual returns found.")

    counts = data.groupby(["date", "horizon"])["model"].nunique()
    expected_models = len(REFERENCE_MODELS) + 1

    if not (counts == expected_models).all():
        raise ValueError(
            "Models do not have identical date/horizon coverage. "
            "Resolve missing observations before statistical inference."
        )

    actual_spread = (
        data.groupby(["date", "horizon"])["actual_return"]
        .agg(lambda values: values.max() - values.min())
    )

    if not np.allclose(
        actual_spread.to_numpy(), 0.0, rtol=0, atol=1e-12
    ):
        raise ValueError("Actual returns differ between model records.")

    data = data.sort_values(["horizon", "date", "model"]).reset_index(
        drop=True
    )

    # Verify temporal continuity using the actual trading-session calendar.
    raw = pd.read_csv(RAW_PATH, usecols=["date"])
    sessions = pd.to_datetime(raw["date"], errors="raise").drop_duplicates()
    sessions = sessions.sort_values().reset_index(drop=True)
    session_index = {value: i for i, value in enumerate(sessions)}

    data_dates = pd.DatetimeIndex(data["date"].drop_duplicates())
    unknown_dates = [d for d in data_dates if d not in session_index]

    if unknown_dates:
        raise ValueError(
            f"Forecast dates absent from the trading-session calendar: "
            f"{unknown_dates[:5]}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data.to_csv(ALIGNED_PATH, index=False)

    return data, session_index


def run_comparisons(data, session_index):
    records = []

    for horizon in HORIZONS:
        subset = data.loc[data["horizon"] == horizon].copy()

        pivot = subset.pivot(
            index="date", columns="model", values="prediction"
        ).sort_index()

        actual = (
            subset.drop_duplicates("date")
            .set_index("date")["actual_return"]
            .reindex(pivot.index)
            .to_numpy(dtype=float)
        )

        # Refuse to bootstrap across missing trading sessions.
        positions = np.array(
            [session_index[d] for d in pivot.index], dtype=int
        )

        if len(positions) > 1 and not np.all(np.diff(positions) == 1):
            raise ValueError(
                f"Horizon {horizon}: gaps exist in paired trading sessions. "
                "Segmented bootstrap is required; no inference was produced."
            )

        prediction_a = pivot[RF_MODEL].to_numpy(dtype=float)
        error_a = prediction_a - actual

        for model_b in REFERENCE_MODELS:
            prediction_b = pivot[model_b].to_numpy(dtype=float)
            error_b = prediction_b - actual

            metric_differences = {
                "absolute_error": np.abs(error_a) - np.abs(error_b),
                "squared_error": np.square(error_a) - np.square(error_b),
                "directional_correctness": (
                    (np.sign(prediction_a) == np.sign(actual)).astype(float)
                    - (np.sign(prediction_b) == np.sign(actual)).astype(float)
                ),
            }

            for metric, differences in metric_differences.items():
                # Predeclared protocol: HAC lag = horizon - 1.
                hac_lag = horizon - 1
                hac = newey_west_mean_test(differences, hac_lag)

                rng = stable_rng(horizon, model_b, metric)

                # Protocol: primary block length equals forecast horizon.
                ci_lower, ci_upper = circular_block_bootstrap_ci(
                    differences,
                    block_size=horizon,
                    repetitions=BOOTSTRAP_REPETITIONS,
                    rng=rng,
                )

                records.append(
                    {
                        "horizon": horizon,
                        "metric": metric,
                        "model_a": RF_MODEL,
                        "model_b": model_b,
                        "difference_direction": "Random Forest minus reference",
                        "sample_size": len(differences),
                        "mean_difference": float(np.mean(differences)),
                        "hac_lag": hac_lag,
                        **hac,
                        "bootstrap_block_length": horizon,
                        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
                        "bootstrap_seed": GLOBAL_SEED,
                        "bootstrap_ci_95_lower": ci_lower,
                        "bootstrap_ci_95_upper": ci_upper,
                    }
                )

    results = pd.DataFrame(records)

    # Correct the full predeclared family of 45 comparisons.
    results["holm_adjusted_p_value"] = holm_adjust(
        results["hac_p_value"]
    )

    results["significant_after_holm_5pct"] = (
        results["holm_adjusted_p_value"] < SIGNIFICANCE_LEVEL
    )

    return results


def main():
    print("Loading existing predictions; no model training will be performed.")
    data, session_index = load_and_align_predictions()

    print(f"Aligned prediction records: {len(data)}")
    print("Final Test data used: False")
    print("Backtesting performed: False")

    results = run_comparisons(data, session_index)
    results.to_csv(OUTPUT_PATH, index=False)

    print("\nRANDOM FOREST PAIRED STATISTICAL COMPARISONS")
    print("=" * 100)
    print(f"Output: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Comparisons: {len(results)}")
    print(f"Bootstrap repetitions per comparison: {BOOTSTRAP_REPETITIONS}")
    print(f"Global bootstrap seed: {GLOBAL_SEED}")
    print("HAC lags: 0, 4, 9")
    print("Bootstrap block lengths: 1, 5, 10")
    print("Negative error differences favour Random Forest.")
    print("Positive directional-correctness differences favour Random Forest.")

    display_columns = [
        "horizon",
        "metric",
        "model_b",
        "sample_size",
        "mean_difference",
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

    print("\nCOMPARISONS SIGNIFICANT AFTER HOLM CORRECTION")
    if significant.empty:
        print("None at the 5% significance level.")
    else:
        print(
            significant[display_columns].to_string(
                index=False,
                float_format=lambda value: f"{value:.8f}",
            )
        )

    print("\nAligned predictions:")
    print(ALIGNED_PATH)
    print("Statistical results:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
