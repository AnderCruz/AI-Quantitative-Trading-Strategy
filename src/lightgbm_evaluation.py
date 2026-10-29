"""Walk-forward evaluation for LightGBM return forecasts."""

from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd
from lightgbm import LGBMRegressor

from src.ridge_evaluation import (
    _as_date,
    _validate_inputs,
    _weekly_cutoffs,
)
from src.walk_forward_evaluation import (
    SUPPORTED_HORIZONS,
    evaluate_walk_forward,
)

MODEL_NAME = "lightgbm_regression"

DEFAULT_PARAMETERS = {
    "n_estimators": 100,
    "learning_rate": 0.05,
    "num_leaves": 15,
    "max_depth": 5,
    "verbosity": -1,
    "random_state": 42,
    "n_jobs": 1,
}


def create_lightgbm_regression_model() -> LGBMRegressor:
    """Create a reproducible LightGBM regressor."""
    return LGBMRegressor(**DEFAULT_PARAMETERS)


def evaluate_lightgbm_walk_forward(
    *,
    history: pd.DataFrame,
    features: pd.DataFrame,
    targets: pd.DataFrame,
    maturity_dates: pd.DataFrame,
    development_start: date,
    development_end: date,
    validation_start: date,
    validation_end: date,
    horizons: Iterable[int] = SUPPORTED_HORIZONS,
    min_training_samples: int = 500,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate LightGBM using weekly expanding-window forecasts.

    The generic evaluator handles temporal eligibility, target maturity,
    model fitting, prediction generation and metric calculation.

    Only matured training labels are eligible at each retraining cutoff.
    Validation outcomes must mature by validation_end to be scored.
    Final Test observations must remain excluded from this evaluation.
    """

    return evaluate_walk_forward(
        history=history,
        features=features,
        targets=targets,
        maturity_dates=maturity_dates,
        development_start=development_start,
        development_end=development_end,
        validation_start=validation_start,
        validation_end=validation_end,
        model_factory=create_lightgbm_regression_model,
        model_name=MODEL_NAME,
        horizons=horizons,
        min_training_samples=min_training_samples,
    )