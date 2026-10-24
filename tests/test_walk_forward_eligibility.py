from datetime import date

import pandas as pd

from src.temporal_split import get_training_eligibility_mask


def test_walk_forward_eligibility_updates_at_each_retraining_date():
    # Create four historical observations.
    history = pd.DataFrame(
        {
            "date": [
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
            ]
        }
    )

    # Define independent maturity dates for each forecast horizon.
    maturity_dates = pd.DataFrame(
        {
            "forward_return_1d": [
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
                None,
            ],
            "forward_return_5d": [
                date(2024, 1, 9),
                date(2024, 1, 10),
                date(2024, 1, 11),
                None,
            ],
            "forward_return_10d": [
                date(2024, 1, 16),
                date(2024, 1, 17),
                date(2024, 1, 18),
                None,
            ],
        }
    )

    # Evaluate eligibility at the first retraining date.
    first_cutoff = get_training_eligibility_mask(
        history,
        maturity_dates,
        date(2024, 1, 2),
        date(2024, 1, 5),
        date(2024, 1, 4),
    )

    # Only matured one-session targets are eligible.
    assert first_cutoff["forward_return_1d"].tolist() == [
        True, True, False, False
    ]
    assert not first_cutoff["forward_return_5d"].any()
    assert not first_cutoff["forward_return_10d"].any()

    # Recalculate eligibility at a later retraining date.
    second_cutoff = get_training_eligibility_mask(
        history,
        maturity_dates,
        date(2024, 1, 2),
        date(2024, 1, 5),
        date(2024, 1, 11),
    )

    # More targets have matured, but ten-session targets remain unavailable.
    assert second_cutoff["forward_return_1d"].tolist() == [
        True, True, True, False
    ]
    assert second_cutoff["forward_return_5d"].tolist() == [
        True, True, True, False
    ]
    assert not second_cutoff["forward_return_10d"].any()

def test_eligibility_is_monotonic_as_targets_mature():
    # Create observations and maturity dates for three horizons.
    history = pd.DataFrame(
        {
            "date": [
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 4),
            ]
        }
    )

    maturity_dates = pd.DataFrame(
        {
            "forward_return_1d": [
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
            ],
            "forward_return_5d": [
                date(2024, 1, 9),
                date(2024, 1, 10),
                date(2024, 1, 11),
            ],
            "forward_return_10d": [
                date(2024, 1, 16),
                date(2024, 1, 17),
                date(2024, 1, 18),
            ],
        }
    )

    # Calculate eligibility at two consecutive retraining cutoffs.
    early = get_training_eligibility_mask(
        history, maturity_dates,
        date(2024, 1, 2), date(2024, 1, 4),
        date(2024, 1, 4),
    )
    late = get_training_eligibility_mask(
        history, maturity_dates,
        date(2024, 1, 2), date(2024, 1, 4),
        date(2024, 1, 11),
    )

    # Previously eligible observations must remain eligible.
    for column in maturity_dates.columns:
        assert (early[column] <= late[column]).all()


def test_observations_after_retraining_cutoff_are_excluded():
    # Include one observation after the retraining cutoff.
    history = pd.DataFrame(
        {
            "date": [
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 4),
            ]
        }
    )

    maturity_dates = pd.DataFrame(
        {
            "forward_return_1d": [
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
            ],
            "forward_return_5d": [
                date(2024, 1, 9),
                date(2024, 1, 10),
                date(2024, 1, 11),
            ],
            "forward_return_10d": [
                date(2024, 1, 16),
                date(2024, 1, 17),
                date(2024, 1, 18),
            ],
        }
    )

    # Set the cutoff before the final observation.
    cutoff = date(2024, 1, 3)
    eligibility = get_training_eligibility_mask(
        history, maturity_dates,
        date(2024, 1, 2), date(2024, 1, 4),
        cutoff,
    )

    # No observation dated after the cutoff may be eligible.
    future_observations = history["date"] > cutoff
    assert not eligibility.loc[future_observations].any().any()