"""Tests for supervised regression model construction."""

import numpy as np
import pytest
from sklearn.ensemble import RandomForestRegressor

from src.supervised_models import (
    DEFAULT_RANDOM_FOREST_PARAMETERS,
    create_random_forest_regression_model,
)


def test_random_forest_default_parameters_are_reproducible():
    model = create_random_forest_regression_model()

    assert isinstance(model, RandomForestRegressor)
    assert model.get_params()["n_estimators"] == 100
    assert model.get_params()["max_depth"] == 5
    assert model.get_params()["min_samples_leaf"] == 5
    assert model.get_params()["random_state"] == 42
    assert model.get_params()["n_jobs"] == 1


def test_random_forest_accepts_custom_parameters():
    model = create_random_forest_regression_model(
        n_estimators=25,
        max_depth=3,
        min_samples_leaf=2,
        random_state=7,
        n_jobs=1,
    )

    assert model.n_estimators == 25
    assert model.max_depth == 3
    assert model.min_samples_leaf == 2
    assert model.random_state == 7


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("n_estimators", 0),
        ("n_estimators", True),
        ("max_depth", 0),
        ("max_depth", False),
        ("min_samples_leaf", 0),
        ("min_samples_leaf", True),
        ("random_state", -1),
        ("random_state", True),
        ("n_jobs", 0),
        ("n_jobs", True),
    ],
)
def test_random_forest_rejects_invalid_parameters(parameter, value):
    with pytest.raises(ValueError):
        create_random_forest_regression_model(**{parameter: value})


def test_random_forest_fits_synthetic_data_and_returns_finite_predictions():
    model = create_random_forest_regression_model(n_estimators=10)

    rng = np.random.default_rng(42)
    features = rng.normal(size=(100, 7))
    target = 0.01 * features[:, 0] - 0.02 * features[:, 1]

    model.fit(features, target)
    predictions = model.predict(features[:5])

    assert predictions.shape == (5,)
    assert np.isfinite(predictions).all()


def test_default_parameters_match_model_factory_defaults():
    model = create_random_forest_regression_model()

    assert model.get_params()["n_estimators"] == DEFAULT_RANDOM_FOREST_PARAMETERS["n_estimators"]
    assert model.get_params()["max_depth"] == DEFAULT_RANDOM_FOREST_PARAMETERS["max_depth"]
    assert model.get_params()["min_samples_leaf"] == DEFAULT_RANDOM_FOREST_PARAMETERS["min_samples_leaf"]
