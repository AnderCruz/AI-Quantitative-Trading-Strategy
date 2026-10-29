"""Compare existing validation predictions, including MLP, on common observations."""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


ROOT = Path(__file__).resolve().parents[1]

ASSET_DIR = ROOT / "reports" / "model_evaluation" / "LLOY.L"
EXISTING_PREDICTIONS_PATH = (
    ASSET_DIR
    / "lightgbm_regression"
    / "all_models_aligned_predictions.csv"
)
MLP_PREDICTIONS_PATH = (
    ASSET_DIR
    / "mlp_regression"
    / "mlp_validation_predictions.csv"
)

OUTPUT_DIR = ASSET_DIR / "lightgbm_regression"
ALIGNED_OUTPUT_PATH = (
    OUTPUT_DIR / "all_models_including_mlp_aligned_predictions.csv"
)
METRICS_OUTPUT_PATH = (
    OUTPUT_DIR / "all_models_including_mlp_comparison_metrics.csv"
)

BASE_MODELS = (
    "lightgbm_regression",
    "ridge_regression",
    "zero_return",
    "historical_mean",
    "historical_median",
)
MLP_MODEL = "mlp_regression"
ALL_MODELS = (*BASE_MODELS, MLP_MODEL)
KEYS = ["date", "horizon"]
REQUIRED_COLUMNS = {*KEYS, "model", "prediction", "actual_return"}


def load_predictions(path: Path) -> pd.DataFrame:
    """Load and validate prediction-level records."""
    if not path.exists():
        raise FileNotFoundError(f"Prediction file not found: {path}")

    data = pd.read_csv(path, parse_dates=["date"])
    missing = REQUIRED_COLUMNS.difference(data.columns)

    if missing:
        raise ValueError(
            f"{path.name} is missing columns: {sorted(missing)}"
        )

    data = data.loc[
        :, ["date", "horizon", "model", "prediction", "actual_return"]
    ].copy()

    data["horizon"] = pd.to_numeric(
        data["horizon"], errors="raise"
    ).astype(int)

    for column in ("prediction", "actual_return"):
        data[column] = pd.to_numeric(data[column], errors="raise")

    if data.duplicated([*KEYS, "model"]).any():
        raise ValueError(f"Duplicate date/horizon/model rows in {path.name}.")

    values = data[["prediction", "actual_return"]].to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError(f"Non-finite values found in {path.name}.")

    return data

def calculate_directional_metrics(
    actual: pd.Series,
    predicted: pd.Series,
) -> dict[str, float]:
    """Calculate directional accuracy and directional forecast coverage."""
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)

    if (
        not np.isfinite(actual_values).all()
        or not np.isfinite(predicted_values).all()
    ):
        raise ValueError("Actual returns and predictions must be finite.")

    directional_accuracy = float(
        np.mean(np.sign(predicted_values) == np.sign(actual_values))
    )

    directional_coverage = float(np.mean(predicted_values != 0.0))

    return {
        "directional_accuracy": directional_accuracy,
        "directional_coverage": directional_coverage,
    }

def calculate_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    """Calculate the project's validation metrics."""
    if len(actual) == 0 or len(actual) != len(predicted):
        raise ValueError("Actual and predicted arrays must be non-empty and aligned.")

    if np.ptp(actual) == 0 or np.ptp(predicted) == 0:
        correlation = np.nan
    else:
        correlation = spearmanr(actual, predicted).statistic

    directional_metrics = calculate_directional_metrics(
        actual,
        predicted,
    )

    return {
        "sample_size": int(len(actual)),
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        **directional_metrics,
        "spearman_correlation": (
            float(correlation) if np.isfinite(correlation) else np.nan
        ),
        "r_squared": float(r2_score(actual, predicted)),
    }


def main() -> None:
    existing = load_predictions(EXISTING_PREDICTIONS_PATH)
    mlp = load_predictions(MLP_PREDICTIONS_PATH)

    existing = existing.loc[existing["model"].isin(BASE_MODELS)].copy()
    mlp = mlp.loc[mlp["model"] == MLP_MODEL].copy()

    if set(existing["model"].unique()) != set(BASE_MODELS):
        raise ValueError("One or more existing models are missing.")

    if mlp.empty:
        raise ValueError("No mlp_regression predictions were found.")

    # Combine old predictions and MLP predictions without retraining.
    combined = pd.concat([existing, mlp], ignore_index=True)

    if set(combined["model"].unique()) != set(ALL_MODELS):
        raise ValueError("The combined data does not contain all six models.")

    # Keep only date/horizon keys for which every model has a prediction.
    model_counts = combined.groupby(KEYS)["model"].nunique()
    common_keys = model_counts[model_counts == len(ALL_MODELS)].index

    aligned = combined.set_index(KEYS).loc[
        combined.set_index(KEYS).index.isin(common_keys)
    ].reset_index()

    if aligned.empty:
        raise ValueError("No common date/horizon observations across all models.")

    # Verify each model has the same realised return for every common key.
    actual_spread = aligned.groupby(KEYS)["actual_return"].agg(
        lambda values: values.max() - values.min()
    )

    if not np.allclose(
        actual_spread.to_numpy(dtype=float), 0.0, rtol=0, atol=1e-12
    ):
        raise ValueError("Actual returns differ across models.")

    # Enforce complete alignment after filtering to common keys.
    counts = aligned.groupby(KEYS)["model"].nunique()

    if not (counts == len(ALL_MODELS)).all():
        raise ValueError("The final prediction set is not fully aligned.")

    metric_records = []

    for horizon in sorted(aligned["horizon"].unique()):
        horizon_data = aligned.loc[aligned["horizon"] == horizon]
        actual = (
            horizon_data.drop_duplicates(KEYS)
            .set_index(KEYS)["actual_return"]
            .sort_index()
        )

        for model in ALL_MODELS:
            model_data = (
                horizon_data.loc[horizon_data["model"] == model]
                .set_index(KEYS)
                .sort_index()
            )

            model_actual = model_data["actual_return"]

            if not actual.index.equals(model_data.index):
                raise ValueError(
                    f"Observation indices differ for {model}, horizon {horizon}."
                )

            if not np.allclose(
                actual.to_numpy(dtype=float),
                model_actual.to_numpy(dtype=float),
                rtol=0,
                atol=1e-12,
            ):
                raise ValueError(
                    f"Actual returns differ for {model}, horizon {horizon}."
                )

            metric_records.append(
                {
                    "horizon": int(horizon),
                    "model": model,
                    **calculate_metrics(
                        actual.to_numpy(dtype=float),
                        model_data["prediction"].to_numpy(dtype=float),
                    ),
                }
            )

    metrics = pd.DataFrame(metric_records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    aligned.sort_values([*KEYS, "model"]).to_csv(
        ALIGNED_OUTPUT_PATH, index=False
    )
    metrics.to_csv(METRICS_OUTPUT_PATH, index=False)

    print("\nALL-MODEL VALIDATION COMPARISON INCLUDING MLP")
    print("=" * 100)
    print(f"Models: {', '.join(ALL_MODELS)}")
    print(f"Common date-horizon observations: {len(common_keys)}")
    print(f"Aligned model prediction rows: {len(aligned)}")
    print("Final Test used: False")
    print("Backtesting performed: False")
    print("\nMETRICS ON IDENTICAL OBSERVATIONS")
    print(metrics.to_string(index=False))
    print("\nOBSERVATION COUNTS BY HORIZON")
    print(
        metrics[["horizon", "model", "sample_size"]].to_string(index=False)
    )
    print("\nOUTPUT FILES")
    print(ALIGNED_OUTPUT_PATH)
    print(METRICS_OUTPUT_PATH)


if __name__ == "__main__":
    main()
