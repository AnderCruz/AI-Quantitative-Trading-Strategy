"""Compare LightGBM, Ridge and baselines on identical validation observations."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.baseline_evaluation import _calculate_metrics


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "reports" / "model_evaluation" / "LLOY.L"

INPUT_FILES = {
    "lightgbm_regression": (
        ASSET_DIR
        / "lightgbm_regression"
        / "lightgbm_validation_predictions.csv"
    ),
    "ridge_regression": (
        ASSET_DIR
        / "ridge_regression"
        / "ridge_validation_predictions.csv"
    ),
    "baselines": (
        ROOT
        / "reports"
        / "baseline_evaluation"
        / "baseline_predictions.csv"
    ),
}

BASELINE_MODELS = (
    "zero_return",
    "historical_mean",
    "historical_median",
)

MODEL_ORDER = (
    "lightgbm_regression",
    "ridge_regression",
    *BASELINE_MODELS,
)

KEYS = ["date", "horizon"]
OUTPUT_DIR = ASSET_DIR / "lightgbm_regression"


def load_predictions(name: str, path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{name} prediction file not found: {path}"
        )

    frame = pd.read_csv(path, parse_dates=["date"])

    required = {
        "date",
        "horizon",
        "model",
        "prediction",
        "actual_return",
    }
    missing = required.difference(frame.columns)

    if missing:
        raise ValueError(
            f"{name} file is missing columns: {sorted(missing)}"
        )

    expected_models = (
        set(BASELINE_MODELS) if name == "baselines" else {name}
    )

    unexpected = set(frame["model"].dropna().unique()) - expected_models

    if unexpected:
        raise ValueError(
            f"Unexpected models in {name}: {sorted(unexpected)}"
        )

    frame = frame.loc[
        frame["model"].isin(expected_models)
    ].copy()

    frame["horizon"] = pd.to_numeric(
        frame["horizon"], errors="raise"
    ).astype(int)

    for column in ("prediction", "actual_return"):
        frame[column] = pd.to_numeric(
            frame[column], errors="raise"
        )

    if frame.duplicated(KEYS + ["model"]).any():
        raise ValueError(
            f"{name} contains duplicate date-horizon-model observations."
        )

    values = frame[
        ["prediction", "actual_return"]
    ].to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError(
            f"{name} contains non-finite numeric values."
        )

    return frame[
        KEYS + ["model", "prediction", "actual_return"]
    ]


def main() -> None:
    frames = {
        name: load_predictions(name, path)
        for name, path in INPUT_FILES.items()
    }

    # Build the intersection using unique date-horizon keys.
    key_sets = [
        frame[KEYS].drop_duplicates()
        for frame in frames.values()
    ]

    common_keys = key_sets[0]

    for keys in key_sets[1:]:
        common_keys = common_keys.merge(
            keys,
            on=KEYS,
            how="inner",
            validate="one_to_one",
        )

    if common_keys.empty:
        raise ValueError(
            "No common validation observations across models."
        )

    aligned_parts = []

    for name, frame in frames.items():
        # Baseline data contains multiple models per date and horizon.
        # Align each baseline separately to preserve unique merge keys.
        model_names = (
            BASELINE_MODELS if name == "baselines" else (name,)
        )

        for model_name in model_names:
            model_frame = frame.loc[
                frame["model"] == model_name
            ].copy()

            part = common_keys.merge(
                model_frame,
                on=KEYS,
                how="left",
                validate="one_to_one",
            )

            if part["prediction"].isna().any():
                raise ValueError(
                    f"Missing predictions for {model_name} after alignment."
                )

            part["model"] = model_name
            aligned_parts.append(part)

    aligned = pd.concat(
        aligned_parts,
        ignore_index=True,
    )

    observed_models = set(aligned["model"].unique())
    expected_models = set(MODEL_ORDER)

    if observed_models != expected_models:
        raise ValueError(
            f"Expected models {sorted(expected_models)}, "
            f"found {sorted(observed_models)}."
        )

    # Verify identical realised returns for every date and horizon.
    actual_spread = (
        aligned.groupby(KEYS)["actual_return"]
        .agg(lambda values: values.max() - values.min())
    )

    if not np.allclose(
        actual_spread.to_numpy(),
        0.0,
        rtol=0,
        atol=1e-12,
    ):
        raise ValueError(
            "Actual returns differ across models on aligned observations."
        )

    metric_records = []

    for horizon in sorted(aligned["horizon"].unique()):
        horizon_data = aligned.loc[
            aligned["horizon"] == horizon
        ]

        for model_name in MODEL_ORDER:
            rows = horizon_data.loc[
                horizon_data["model"] == model_name
            ].sort_values("date")

            metrics = _calculate_metrics(
                actual=rows["actual_return"],
                predicted=rows["prediction"],
            )

            metric_records.append(
                {
                    "horizon": int(horizon),
                    "model": model_name,
                    **metrics,
                }
            )

    metrics_frame = pd.DataFrame(metric_records)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    aligned_path = (
        OUTPUT_DIR / "all_models_aligned_predictions.csv"
    )
    metrics_path = (
        OUTPUT_DIR / "all_models_comparison_metrics.csv"
    )

    aligned.sort_values(
        ["horizon", "date", "model"]
    ).to_csv(
        aligned_path,
        index=False,
    )

    metrics_frame.to_csv(
        metrics_path,
        index=False,
    )

    print("\nALL-MODEL VALIDATION COMPARISON")
    print("=" * 100)
    print(
        f"Common date-horizon observations: {len(common_keys)}"
    )
    print(
        f"Aligned model prediction rows: {len(aligned)}"
    )
    print("Final Test used: False")
    print("Backtesting performed: False")

    print("\nMetrics on identical observations:")
    print(
        metrics_frame.to_string(
            index=False,
            float_format=lambda value: f"{value:.6f}",
        )
    )

    print("\nSample sizes:")
    print(
        metrics_frame[
            ["horizon", "model", "sample_size"]
        ].to_string(index=False)
    )

    print("\nOutput files:")
    print(aligned_path)
    print(metrics_path)


if __name__ == "__main__":
    main()
