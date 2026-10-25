import numpy as np
import pandas as pd

from src.temporal_split import get_training_eligibility_mask


# Define the supported forecasting horizons.
SUPPORTED_HORIZONS = (1, 5, 10)


def get_eligible_training_targets(
    history: pd.DataFrame,
    targets: pd.DataFrame,
    maturity_dates: pd.DataFrame,
    horizon: int,
    period_start,
    period_end,
    cutoff_date,
) -> pd.Series:
    """Return training targets whose outcomes matured by the cutoff date."""

    # Validate the forecasting horizon.
    if (
        not isinstance(horizon, int)
        or isinstance(horizon, bool)
        or horizon not in SUPPORTED_HORIZONS
    ):
        raise ValueError(
            f"horizon must be one of {SUPPORTED_HORIZONS}."
        )

    # Identify the target column for the selected horizon.
    target_column = f"forward_return_{horizon}d"
    maturity_column = f"target_maturity_date_{horizon}d"

    # Validate the required columns.
    if target_column not in targets.columns:
        raise ValueError(f"Missing target column: {target_column}")

    if maturity_column not in maturity_dates.columns:
        raise ValueError(f"Missing maturity column: {maturity_column}")

    # Require identical indices to prevent accidental misalignment.
    if not (
        history.index.equals(targets.index)
        and history.index.equals(maturity_dates.index)
    ):
        raise ValueError(
            "History, targets and maturity dates must have identical "
            "indices in the same order."
        )

    # Reuse the existing temporal eligibility controls.
    eligibility = get_training_eligibility_mask(
        history=history,
        maturity_dates=maturity_dates[[maturity_column]],
        period_start=period_start,
        period_end=period_end,
        cutoff_date=cutoff_date,
    )

    # Select only observations eligible for the chosen horizon.
    eligible_mask = eligibility[maturity_column]
    eligible_targets = targets.loc[eligible_mask, target_column].copy()

    # Reject missing or non-finite outcomes instead of silently dropping them.
    values = pd.to_numeric(eligible_targets, errors="raise").to_numpy(
        dtype=float
    )

    if len(values) == 0:
        raise ValueError(
            f"No eligible training targets for horizon {horizon}."
        )

    if not np.isfinite(values).all():
        raise ValueError(
            "Eligible training targets must be finite and non-missing."
        )

    # Return a numeric series while preserving the original observation index.
    return pd.Series(
        values,
        index=eligible_targets.index,
        name=target_column,
    )


class _ConstantBaseline:
    """Base class for baselines that predict one constant value."""

    def __init__(self) -> None:
        # Mark the model as unfitted until valid training data is supplied.
        self._is_fitted = False
        self.value_ = None

    def fit(self, y: pd.Series):
        """Fit the baseline using eligible historical target values."""

        # Convert the training targets to a numeric one-dimensional array.
        if isinstance(y, pd.DataFrame):
            raise TypeError("y must be a one-dimensional series or array.")

        values = np.asarray(y, dtype=float)

        if values.ndim != 1:
            raise ValueError("y must be one-dimensional.")

        if values.size == 0:
            raise ValueError("Training targets cannot be empty.")

        if not np.isfinite(values).all():
            raise ValueError(
                "Training targets must be finite and non-missing."
            )

        # Calculate the baseline-specific constant.
        self.value_ = float(self._calculate_value(values))
        self._is_fitted = True

        return self

    def _calculate_value(self, values: np.ndarray) -> float:
        """Calculate the constant prediction value."""
        raise NotImplementedError

    def predict(self, n_samples: int) -> np.ndarray:
        """Return constant predictions for the requested number of samples."""

        # Require a fitted model before generating predictions.
        if not self._is_fitted:
            raise RuntimeError("The baseline model must be fitted first.")

        # Validate the requested prediction count.
        if (
            not isinstance(n_samples, int)
            or isinstance(n_samples, bool)
            or n_samples <= 0
        ):
            raise ValueError("n_samples must be a positive integer.")

        # Return one constant prediction per requested observation.
        return np.full(n_samples, self.value_, dtype=float)


class ZeroReturnBaseline(_ConstantBaseline):
    """Predict a zero forward return for every observation."""

    def _calculate_value(self, values: np.ndarray) -> float:
        # Return zero independently of the observed training returns.
        return 0.0


class HistoricalMeanBaseline(_ConstantBaseline):
    """Predict the mean of eligible historical forward returns."""

    def _calculate_value(self, values: np.ndarray) -> float:
        # Estimate the mean exclusively from the supplied training targets.
        return float(np.mean(values))


class HistoricalMedianBaseline(_ConstantBaseline):
    """Predict the median of eligible historical forward returns."""

    def _calculate_value(self, values: np.ndarray) -> float:
        # Estimate the median exclusively from the supplied training targets.
        return float(np.median(values))
