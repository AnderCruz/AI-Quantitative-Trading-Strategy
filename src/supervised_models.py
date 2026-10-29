"""Supervised regression models for return forecasting."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DEFAULT_RIDGE_ALPHA = 1.0


def create_ridge_regression_model(alpha: float = DEFAULT_RIDGE_ALPHA) -> Pipeline:
    """Create a scaler + Ridge pipeline fitted only on each training window."""
    if not np.isfinite(alpha) or alpha < 0:
        raise ValueError("Ridge alpha must be a finite, non-negative number.")
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )
DEFAULT_RANDOM_FOREST_PARAMETERS = {
    "n_estimators": 100,
    "max_depth": 5,
    "min_samples_leaf": 5,
    "random_state": 42,
    "n_jobs": 1,
}


def create_random_forest_regression_model(
    *,
    n_estimators: int = DEFAULT_RANDOM_FOREST_PARAMETERS["n_estimators"],
    max_depth: int | None = DEFAULT_RANDOM_FOREST_PARAMETERS["max_depth"],
    min_samples_leaf: int = DEFAULT_RANDOM_FOREST_PARAMETERS["min_samples_leaf"],
    random_state: int = DEFAULT_RANDOM_FOREST_PARAMETERS["random_state"],
    n_jobs: int = DEFAULT_RANDOM_FOREST_PARAMETERS["n_jobs"],
):
    """Create a reproducible Random Forest regressor."""

    from sklearn.ensemble import RandomForestRegressor

    if isinstance(n_estimators, bool) or not isinstance(n_estimators, int) or n_estimators < 1:
        raise ValueError("n_estimators must be a positive integer.")

    if max_depth is not None and (
        isinstance(max_depth, bool)
        or not isinstance(max_depth, int)
        or max_depth < 1
    ):
        raise ValueError("max_depth must be None or a positive integer.")

    if (
        isinstance(min_samples_leaf, bool)
        or not isinstance(min_samples_leaf, int)
        or min_samples_leaf < 1
    ):
        raise ValueError("min_samples_leaf must be a positive integer.")

    if isinstance(random_state, bool) or not isinstance(random_state, int) or random_state < 0:
        raise ValueError("random_state must be a non-negative integer.")

    if isinstance(n_jobs, bool) or not isinstance(n_jobs, int) or n_jobs == 0:
        raise ValueError("n_jobs must be a non-zero integer.")

    return RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
        n_jobs=n_jobs,
    )


from sklearn.neural_network import MLPRegressor

DEFAULT_MLP_PARAMETERS = {
    "hidden_layer_sizes": (64, 32),
    "activation": "relu",
    "solver": "adam",
    "alpha": 0.001,
    "batch_size": 32,
    "learning_rate_init": 0.001,
    "max_iter": 500,
    "early_stopping": False,
    "random_state": 42,
}

def create_mlp_regression_model(
    *,
    hidden_layer_sizes: tuple[int, ...] = DEFAULT_MLP_PARAMETERS[
        "hidden_layer_sizes"
    ],
    activation: str = DEFAULT_MLP_PARAMETERS["activation"],
    solver: str = DEFAULT_MLP_PARAMETERS["solver"],
    alpha: float = DEFAULT_MLP_PARAMETERS["alpha"],
    batch_size: int = DEFAULT_MLP_PARAMETERS["batch_size"],
    learning_rate_init: float = DEFAULT_MLP_PARAMETERS[
        "learning_rate_init"
    ],
    max_iter: int = DEFAULT_MLP_PARAMETERS["max_iter"],
    random_state: int = DEFAULT_MLP_PARAMETERS["random_state"],
) -> Pipeline:
    """Create a reproducible MLP regression pipeline with feature scaling."""

    if (
        not isinstance(hidden_layer_sizes, tuple)
        or not hidden_layer_sizes
        or any(
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 1
            for size in hidden_layer_sizes
        )
    ):
        raise ValueError(
            "hidden_layer_sizes must be a non-empty tuple of positive integers."
        )

    if not np.isfinite(alpha) or alpha < 0:
        raise ValueError("MLP alpha must be finite and non-negative.")

    if (
        isinstance(batch_size, bool)
        or not isinstance(batch_size, int)
        or batch_size < 1
    ):
        raise ValueError("batch_size must be a positive integer.")

    if not np.isfinite(learning_rate_init) or learning_rate_init <= 0:
        raise ValueError("learning_rate_init must be finite and positive.")

    if (
        isinstance(max_iter, bool)
        or not isinstance(max_iter, int)
        or max_iter < 1
    ):
        raise ValueError("max_iter must be a positive integer.")

    if (
        isinstance(random_state, bool)
        or not isinstance(random_state, int)
        or random_state < 0
    ):
        raise ValueError("random_state must be a non-negative integer.")

    model = MLPRegressor(
        hidden_layer_sizes=hidden_layer_sizes,
        activation=activation,
        solver=solver,
        alpha=float(alpha),
        batch_size=batch_size,
        learning_rate_init=float(learning_rate_init),
        max_iter=max_iter,
        early_stopping=False,
        random_state=random_state,
    )

    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("mlp", model),
        ]
    )
