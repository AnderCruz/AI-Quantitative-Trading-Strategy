"""Walk-forward evaluation for supervised Random Forest return forecasts."""

from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd

from src.supervised_models import create_random_forest_regression_model
from src.walk_forward_evaluation import (
    SUPPORTED_HORIZONS,
    _as_date,
    _validate_inputs,
    _weekly_cutoffs,
    evaluate_walk_forward,
)

MODEL_NAME = "random_forest_regression"


def evaluate_random_forest_walk_forward(
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
    """Evaluate Random Forest using weekly expanding-window forecasts.

    Model fitting, temporal eligibility, target maturity, prediction
    generation and metric calculation are delegated to the generic
    walk-forward evaluator.

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
        model_factory=create_random_forest_regression_model,
        model_name=MODEL_NAME,
        horizons=horizons,
        min_training_samples=min_training_samples,
    )