"""Tests for temporal dataset splitting."""

from datetime import date

import pytest

from src.temporal_split import get_temporal_periods


def _synthetic_history():
    """Create a deterministic weekday-only history for period tests."""
    import pandas as pd

    return pd.DataFrame({
        "date": pd.bdate_range(
            start="2010-01-01",
            end="2026-10-23",
        ).strftime("%Y-%m-%d")
    })


def test_temporal_periods_end_at_latest_available_session():
    """The final test ends at the latest eligible historical session."""
    history = _synthetic_history()

    periods = get_temporal_periods(
        history,
        reference_date=date(2026, 10, 24),
    )

    assert periods["final_test"][1] == date(2026, 10, 23)


def test_temporal_periods_are_chronological_and_non_overlapping():
    """Periods must be ordered and separated by adjacent sessions."""
    history = _synthetic_history()

    periods = get_temporal_periods(
        history,
        reference_date=date(2026, 10, 24),
    )

    sessions = set(
        __import__("pandas").to_datetime(history["date"]).dt.date
    )

    development_start, development_end = periods["development"]
    validation_start, validation_end = periods["validation"]
    final_test_start, final_test_end = periods["final_test"]

    assert development_start <= development_end
    assert validation_start <= validation_end
    assert final_test_start <= final_test_end

    assert development_end < validation_start
    assert validation_end < final_test_start

    assert development_start in sessions
    assert development_end in sessions
    assert validation_start in sessions
    assert validation_end in sessions
    assert final_test_start in sessions
    assert final_test_end in sessions

    ordered_sessions = sorted(sessions)

    assert ordered_sessions[ordered_sessions.index(validation_start) - 1] == (
        development_end
    )
    assert ordered_sessions[ordered_sessions.index(final_test_start) - 1] == (
        validation_end
    )


def test_temporal_periods_update_with_latest_available_history():
    """Period boundaries must move when the historical endpoint changes."""
    import pandas as pd

    history = _synthetic_history()

    first_periods = get_temporal_periods(
        history,
        reference_date=date(2026, 10, 24),
    )

    shortened_history = history[
        pd.to_datetime(history["date"]).dt.date <= date(2025, 10, 23)
    ]

    second_periods = get_temporal_periods(
        shortened_history,
        reference_date=date(2026, 10, 24),
    )

    assert first_periods["final_test"][1] == date(2026, 10, 23)
    assert second_periods["final_test"][1] == date(2025, 10, 23)
    assert (
        first_periods["final_test"][0]
        != second_periods["final_test"][0]
    )


def test_future_sessions_are_excluded_from_temporal_periods():
    """Sessions after the reference date must not enter any period."""
    import pandas as pd

    history = _synthetic_history()

    periods = get_temporal_periods(
        history,
        reference_date=date(2026, 10, 20),
    )

    assert periods["final_test"][1] == date(2026, 10, 20)
    assert all(
        end_date <= date(2026, 10, 20)
        for _, end_date in periods.values()
    )


def test_temporal_periods_reject_invalid_year_lengths():
    """Period lengths must be positive integers."""
    history = _synthetic_history()

    with pytest.raises(ValueError):
        get_temporal_periods(history, development_years=0)

    with pytest.raises(ValueError):
        get_temporal_periods(history, validation_years=-1)


def test_temporal_periods_reject_insufficient_history():
    """Reject histories too short to construct all three periods."""
    import pandas as pd

    history = pd.DataFrame({
        "date": pd.bdate_range(
            start="2024-01-01",
            end="2026-10-23",
        ).strftime("%Y-%m-%d")
    })

    with pytest.raises(ValueError):
        get_temporal_periods(
            history,
            reference_date=date(2026, 10, 24),
        )


def test_last_available_session_is_selected():
    """Select the last available date not later than the reference date."""
    import pandas as pd

    from src.temporal_split import get_last_available_session

    history = pd.DataFrame({
        "date": [
            "2026-10-20",
            "2026-10-21",
            "2026-10-22",
            "2026-10-23",
        ]
    })

    result = get_last_available_session(
        history,
        reference_date=date(2026, 10, 24),
    )

    assert result == date(2026, 10, 23)


def test_future_sessions_are_excluded():
    """Ignore historical rows dated after the reference date."""
    import pandas as pd

    from src.temporal_split import get_last_available_session

    history = pd.DataFrame({
        "date": [
            "2026-10-21",
            "2026-10-23",
            "2026-10-26",
        ]
    })

    result = get_last_available_session(
        history,
        reference_date=date(2026, 10, 24),
    )

    assert result == date(2026, 10, 23)


def test_empty_history_is_rejected():
    """Reject an empty historical DataFrame."""
    import pandas as pd

    from src.temporal_split import get_last_available_session

    with pytest.raises(ValueError):
        get_last_available_session(
            pd.DataFrame({"date": []}),
            reference_date=date(2026, 10, 24),
        )


def test_missing_date_column_is_rejected():
    """Reject historical data without a date column."""
    import pandas as pd

    from src.temporal_split import get_last_available_session

    with pytest.raises(ValueError):
        get_last_available_session(
            pd.DataFrame({"Close": [10.0]}),
            reference_date=date(2026, 10, 24),
        )


def test_no_eligible_session_is_rejected():
    """Reject history containing only dates after the reference date."""
    import pandas as pd

    from src.temporal_split import get_last_available_session

    with pytest.raises(ValueError):
        get_last_available_session(
            pd.DataFrame({"date": ["2026-10-26", "2026-10-27"]}),
            reference_date=date(2026, 10, 24),
        )


# Tests for target maturity dates.
def test_target_maturity_dates_for_approved_horizons():
    # Import the target maturity function.
    import pandas as pd
    from src.temporal_split import get_target_maturity_dates

    # Create twelve consecutive business-session observations.
    dates = pd.bdate_range("2026-01-05", periods=12)
    history = pd.DataFrame({
        "date": dates,
        "ticker": "LLOY.L",
    })

    # Calculate the maturity dates.
    result = get_target_maturity_dates(history)

    # Check the expected maturity dates for the first observation.
    assert result.loc[0, "target_maturity_date_1d"] == dates[1]
    assert result.loc[0, "target_maturity_date_5d"] == dates[5]
    assert result.loc[0, "target_maturity_date_10d"] == dates[10]


def test_target_maturity_dates_keep_separate_tickers():
    # Import the target maturity function.
    import pandas as pd
    from src.temporal_split import get_target_maturity_dates

    # Create two independent asset histories.
    history = pd.DataFrame({
        "date": [
            "2026-01-05", "2026-01-06", "2026-01-07",
            "2026-01-05", "2026-01-06", "2026-01-07",
        ],
        "ticker": [
            "LLOY.L", "LLOY.L", "LLOY.L",
            "AAPL", "AAPL", "AAPL",
        ],
    })

    # Calculate maturity dates for a one-session horizon.
    result = get_target_maturity_dates(history, horizons=(1,))

    # Confirm that each ticker uses its own chronological observations.
    assert result.loc[0, "target_maturity_date_1d"] == pd.Timestamp("2026-01-06")
    assert result.loc[3, "target_maturity_date_1d"] == pd.Timestamp("2026-01-06")
    assert result.loc[2, "target_maturity_date_1d"] is pd.NaT or pd.isna(
        result.loc[2, "target_maturity_date_1d"]
    )
    assert result.loc[5, "target_maturity_date_1d"] is pd.NaT or pd.isna(
        result.loc[5, "target_maturity_date_1d"]
    )


def test_target_maturity_dates_preserve_original_order_and_index():
    # Import the target maturity function.
    import pandas as pd
    from src.temporal_split import get_target_maturity_dates

    # Create deliberately unsorted observations with a non-sequential index.
    history = pd.DataFrame({
        "date": ["2026-01-07", "2026-01-05", "2026-01-06"],
        "ticker": ["LLOY.L", "LLOY.L", "LLOY.L"],
    }, index=[20, 10, 30])

    # Calculate maturity dates without changing the input order.
    result = get_target_maturity_dates(history, horizons=(1,))

    # Check the original index and expected dates.
    assert result.index.tolist() == [20, 10, 30]
    assert result.loc[10, "target_maturity_date_1d"] == pd.Timestamp("2026-01-06")
    assert result.loc[30, "target_maturity_date_1d"] == pd.Timestamp("2026-01-07")
    assert pd.isna(result.loc[20, "target_maturity_date_1d"])


def test_target_maturity_dates_reject_duplicate_ticker_dates():
    # Import the required libraries and function.
    import pandas as pd
    import pytest
    from src.temporal_split import get_target_maturity_dates

    # Create duplicate observations for the same ticker and date.
    history = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-05"],
        "ticker": ["LLOY.L", "LLOY.L"],
    })

    # Duplicate ticker-date pairs must be rejected.
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        get_target_maturity_dates(history, horizons=(1,))


def test_target_maturity_dates_reject_invalid_horizons():
    # Import the required libraries and function.
    import pandas as pd
    import pytest
    from src.temporal_split import get_target_maturity_dates

    # Create a valid minimal history.
    history = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06"],
        "ticker": ["LLOY.L", "LLOY.L"],
    })

    # Reject zero, negative, duplicate, and non-integer horizons.
    for invalid_horizons in [(0,), (-1,), (1, 1), (1.5,), (True,)]:
        with pytest.raises((TypeError, ValueError)):
            get_target_maturity_dates(history, horizons=invalid_horizons)


def test_matured_target_mask_respects_cutoff_and_missing_dates():
    """Only targets matured by the cutoff are eligible for training."""
    import pandas as pd
    from datetime import date
    from src.temporal_split import get_matured_target_mask

    # Include dates before, on and after the cutoff, plus missing outcomes.
    maturity_dates = pd.DataFrame({
        "target_maturity_date_1d": pd.to_datetime([
            "2023-12-29", "2023-12-31", "2024-01-02", None,
        ]),
        "target_maturity_date_5d": pd.to_datetime([
            "2024-01-02", "2023-12-29", None, "2024-01-05",
        ]),
    })

    # Evaluate eligibility at the development cutoff.
    result = get_matured_target_mask(
        maturity_dates,
        cutoff_date=date(2023, 12, 31),
    )

    # Verify that each horizon is evaluated independently.
    assert result["target_maturity_date_1d"].tolist() == [
        True, True, False, False,
    ]
    assert result["target_maturity_date_5d"].tolist() == [
        False, True, False, False,
    ]

    # Preserve the original index and column names.
    assert result.index.equals(maturity_dates.index)
    assert result.columns.equals(maturity_dates.columns)


def test_matured_target_mask_rejects_invalid_cutoff():
    """The cutoff must be a datetime.date, not a string or datetime."""
    from datetime import date, datetime
    import pandas as pd
    import pytest
    from src.temporal_split import get_matured_target_mask

    # Create a minimal maturity-date DataFrame.
    maturity_dates = pd.DataFrame({
        "target_maturity_date_1d": pd.to_datetime(["2023-12-29"]),
    })

    # Reject invalid cutoff types.
    for cutoff in ["2023-12-31", datetime(2023, 12, 31)]:
        with pytest.raises(TypeError):
            get_matured_target_mask(maturity_dates, cutoff_date=cutoff)

    # Confirm that a plain date is accepted.
    result = get_matured_target_mask(
        maturity_dates,
        cutoff_date=date(2023, 12, 31),
    )
    assert result.iloc[0, 0]


def test_training_eligibility_requires_period_membership_and_maturity():
    """Require period membership, an available observation and target maturity."""
    import pandas as pd
    from datetime import date
    from src.temporal_split import get_training_eligibility_mask

    # Create observations before, within and after the permitted period.
    history = pd.DataFrame({
        "date": [
            "2023-12-29",
            "2024-01-02",
            "2024-01-03",
            "2024-01-04",
            "2024-01-05",
        ],
        "ticker": ["LLOY.L"] * 5,
    })

    # Give each forecast horizon a separate maturity date.
    maturity_dates = pd.DataFrame({
        "target_maturity_date_1d": pd.to_datetime([
            "2023-12-29",
            "2024-01-02",
            "2024-01-04",
            "2024-01-05",
            "2024-01-05",
        ]),
        "target_maturity_date_5d": pd.to_datetime([
            "2024-01-02",
            "2024-01-04",
            "2024-01-05",
            None,
            "2024-01-05",
        ]),
    })

    # Evaluate eligibility at the specified training cutoff.
    result = get_training_eligibility_mask(
        history=history,
        maturity_dates=maturity_dates,
        period_start=date(2024, 1, 2),
        period_end=date(2024, 1, 5),
        cutoff_date=date(2024, 1, 4),
    )

    # Exclude observations outside the period and after the cutoff.
    assert result.iloc[0].tolist() == [False, False]
    assert result.iloc[4].tolist() == [False, False]

    # Both horizons have matured for the 2 January observation.
    assert result.iloc[1].tolist() == [True, True]

    # Only the one-session target has matured for 3 January.
    assert result.iloc[2].tolist() == [True, False]

    # Neither target for 4 January has matured by the cutoff.
    assert result.iloc[3].tolist() == [False, False]

    # Preserve the original index and target columns.
    assert result.index.equals(maturity_dates.index)
    assert result.columns.equals(maturity_dates.columns)


def test_training_eligibility_rejects_misaligned_indices():
    """Reject history and target data with mismatched indices."""
    import pandas as pd
    import pytest
    from datetime import date
    from src.temporal_split import get_training_eligibility_mask

    # Create inputs whose indices do not match.
    history = pd.DataFrame({"date": ["2024-01-02"]}, index=[0])
    maturity_dates = pd.DataFrame(
        {"target_maturity_date_1d": pd.to_datetime(["2024-01-02"])},
        index=[1],
    )

    # Prevent silent alignment errors.
    with pytest.raises(ValueError, match="identical indices"):
        get_training_eligibility_mask(
            history,
            maturity_dates,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 5),
            cutoff_date=date(2024, 1, 5),
        )


def test_training_eligibility_rejects_invalid_period_boundaries():
    """Reject a training period whose start is after its end."""
    import pandas as pd
    import pytest
    from datetime import date
    from src.temporal_split import get_training_eligibility_mask

    # Create minimal valid inputs.
    history = pd.DataFrame({"date": ["2024-01-02"]})
    maturity_dates = pd.DataFrame({
        "target_maturity_date_1d": pd.to_datetime(["2024-01-02"]),
    })

    # Reject reversed period boundaries.
    with pytest.raises(ValueError, match="period_start"):
        get_training_eligibility_mask(
            history,
            maturity_dates,
            period_start=date(2024, 1, 5),
            period_end=date(2024, 1, 1),
            cutoff_date=date(2024, 1, 5),
        )
