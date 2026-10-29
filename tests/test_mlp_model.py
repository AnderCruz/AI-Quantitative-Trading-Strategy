"""Tests for MLP regression model construction."""

import numpy as np
import pytest
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.supervised_models import (
    DEFAULT_MLP_PARAMETERS,
    create_mlp_regression_model,
)


def test_mlp_default_parameters_are_reproducible():
    model = create_mlp_regression_model()

    assert isinstance(model, Pipeline)
    assert isinstance(model.named_steps["scaler"], StandardScaler)

    estimator = model.named_steps["mlp"]
    assert isinstance(estimator, MLPRegressor)

    for parameter, expected in DEFAULT_MLP_PARAMETERS.items():
        assert estimator.get_params()[parameter] == expected


def test_mlp_accepts_custom_parameters():
    model = create_mlp_regression_model(
        hidden_layer_sizes=(32, 16),
        activation="tanh",
        solver="adam",
        alpha=0.01,
        batch_size=16,
        learning_rate_init=0.005,
        max_iter=100,
        random_state=7,
    )

    estimator = model.named_steps["mlp"]

    assert estimator.hidden_layer_sizes == (32, 16)
    assert estimator.activation == "tanh"
    assert estimator.solver == "adam"
    assert estimator.alpha == 0.01
    assert estimator.batch_size == 16
    assert estimator.learning_rate_init == 0.005
    assert estimator.max_iter == 100
    assert estimator.random_state == 7
    assert estimator.early_stopping is False


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("hidden_layer_sizes", ()),
        ("hidden_layer_sizes", (32, 0)),
        ("hidden_layer_sizes", (32, True)),
        ("hidden_layer_sizes", [32, 16]),
        ("alpha", -0.1),
        ("alpha", float("nan")),
        ("alpha", float("inf")),
        ("batch_size", 0),
        ("batch_size", True),
        ("learning_rate_init", 0),
        ("learning_rate_init", -0.001),
        ("learning_rate_init", float("nan")),
        ("max_iter", 0),
        ("max_iter", True),
        ("random_state", -1),
        ("random_state", True),
    ],
)
def test_mlp_rejects_invalid_parameters(parameter, value):
    with pytest.raises(ValueError):
        create_mlp_regression_model(**{parameter: value})


def test_mlp_fits_synthetic_data_and_returns_finite_predictions():
    model = create_mlp_regression_model(
        hidden_layer_sizes=(16, 8),
        max_iter=100,
        random_state=42,
    )

    rng = np.random.default_rng(42)
    features = rng.normal(size=(120, 7))
    target = 0.01 * features[:, 0] - 0.02 * features[:, 1]

    model.fit(features, target)
    predictions = model.predict(features[:10])

    assert predictions.shape == (10,)
    assert np.isfinite(predictions).all()


def test_mlp_pipeline_scales_features_before_regression():
    model = create_mlp_regression_model()

    assert list(model.named_steps) == ["scaler", "mlp"]
