"""Define reproducible temporal periods for model development and evaluation."""

from datetime import date, datetime, timedelta

def get_temporal_periods(
    history,
    reference_date: date | None = None,
    development_years: int = 7,
    validation_years: int = 2,
    final_test_years: int = 1,
) -> dict[str, tuple[date, date]]:
    """Return contiguous temporal periods anchored to available sessions.

    The final test ends on the latest historical session not later than
    the reference date. Period start dates are derived from calendar-year
    offsets and aligned to the first available session on or after each
    calculated boundary.

    The returned periods are inclusive and contain no overlapping dates.
    """

    import pandas as pd

    # Validate the reference date.
    if reference_date is None:
        reference_date = get_last_available_session(history)

    if not isinstance(reference_date, date) or isinstance(
        reference_date, datetime
    ):
        raise TypeError("reference_date must be a datetime.date instance.")

    # Validate the requested period lengths.
    year_lengths = (
        development_years,
        validation_years,
        final_test_years,
    )

    if any(
        not isinstance(years, int) or isinstance(years, bool) or years <= 0
        for years in year_lengths
    ):
        raise ValueError("All period lengths must be positive integers.")

    # Resolve the latest session available by the reference date.
    last_session = get_last_available_session(
        history,
        reference_date=reference_date,
    )

    # Parse and sort the available historical session dates.
    parsed_dates = pd.to_datetime(history["date"], errors="raise")

    if parsed_dates.isna().any():
        raise ValueError("Historical data contains missing dates.")

    sessions = sorted({
        session_date
        for session_date in parsed_dates.dt.date
        if session_date <= last_session
    })

    # Reject duplicate session dates because this function expects
    # a single chronological series for one selected asset.
    if len(sessions) != len([
        session_date
        for session_date in parsed_dates.dt.date
        if session_date <= last_session
    ]):
        raise ValueError(
            "Historical data contains duplicate session dates. "
            "Select one asset before calculating temporal periods."
        )

    # Select the first available session on or after a calendar boundary.
    def first_session_on_or_after(boundary: date) -> date:
        for session_date in sessions:
            if session_date >= boundary:
                return session_date

        raise ValueError(
            f"No historical session is available on or after {boundary}."
        )

    # Calculate the final test start using a calendar-year offset.
    final_test_boundary = (
        pd.Timestamp(last_session) - pd.DateOffset(years=final_test_years)
    ).date()
    final_test_start = first_session_on_or_after(final_test_boundary)

    # Calculate the validation start relative to the final test start.
    validation_boundary = (
        pd.Timestamp(final_test_start) - pd.DateOffset(years=validation_years)
    ).date()
    validation_start = first_session_on_or_after(validation_boundary)

    # Calculate the development start relative to the validation start.
    development_boundary = (
        pd.Timestamp(validation_start) - pd.DateOffset(years=development_years)
    ).date()
    development_start = first_session_on_or_after(development_boundary)

    # Locate adjacent sessions to ensure the periods are contiguous.
    validation_start_index = sessions.index(validation_start)
    final_test_start_index = sessions.index(final_test_start)

    if validation_start_index == 0 or final_test_start_index == 0:
        raise ValueError(
            "Insufficient historical sessions to construct contiguous periods."
        )

    development_end = sessions[validation_start_index - 1]
    validation_end = sessions[final_test_start_index - 1]

    # Ensure all three periods contain at least one session.
    if development_start > development_end:
        raise ValueError(
            "Insufficient history for the requested development period."
        )

    if validation_start > validation_end:
        raise ValueError(
            "Insufficient history for the requested validation period."
        )

    if final_test_start > last_session:
        raise ValueError(
            "Insufficient history for the requested final test period."
        )

    # Return inclusive boundaries aligned to the available sessions.
    return {
        "development": (development_start, development_end),
        "validation": (validation_start, validation_end),
        "final_test": (final_test_start, last_session),
    }

def get_last_available_session(
    history,
    reference_date: date | None = None,
) -> date:
    """Return the latest available historical session up to a reference date.

    The input DataFrame must contain a column named 'date'.
    Dates later than the reference date are excluded.

    Args:
        history: DataFrame containing historical session dates.
        reference_date: Latest permitted calendar date.

    Returns:
        The latest eligible session date as a datetime.date object.

    Raises:
        ValueError: If the date column is missing, dates are invalid,
            or no eligible session is available.
        TypeError: If the reference date is not a datetime.date instance.
    """
    import pandas as pd

    # Validate the historical data structure.
    if not isinstance(history, pd.DataFrame):
        raise TypeError("history must be a pandas DataFrame.")

    if "date" not in history.columns:
        raise ValueError("Historical data must contain a 'date' column.")

    if history.empty:
        raise ValueError("Historical data cannot be empty.")

    # Parse historical dates before selecting the default reference.
    try:
        parsed_dates = pd.to_datetime(
            history["date"],
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Historical data contains invalid dates.") from exc

    if parsed_dates.isna().any():
        raise ValueError("Historical data contains missing dates.")

    # Use the latest historical calendar date when no reference is supplied.
    if reference_date is None:
        reference_date = max(parsed_dates.dt.date)

    # Reject datetime values and other types where a plain date is required.
    if not isinstance(reference_date, date) or isinstance(
        reference_date, datetime
    ):
        raise TypeError("reference_date must be a datetime.date instance.")

    # Compare calendar dates, excluding any time component.
    calendar_dates = parsed_dates.dt.date

    # Exclude sessions later than the reference date.
    eligible_dates = calendar_dates[calendar_dates <= reference_date]

    if eligible_dates.empty:
        raise ValueError(
            "No historical session is available on or before the reference date."
        )

    # Return the latest eligible calendar date.
    return max(eligible_dates)


def get_target_maturity_dates(
    history,
    horizons: tuple[int, ...] = (1, 5, 10),
):
    """Return the observed maturity date for each forward-return horizon.

    The maturity date is the session whose closing price completes the
    target calculation. Dates are derived from the observed historical
    sessions independently for each ticker.

    The input row order and index are preserved. Targets without sufficient
    future observations receive a missing maturity date.

    Args:
        history: DataFrame containing 'date' and 'ticker' columns.
        horizons: Positive forward-session horizons.

    Returns:
        A DataFrame containing one maturity-date column per horizon.

    Raises:
        TypeError: If history is not a pandas DataFrame.
        ValueError: If required columns, valid dates, or unique
            ticker-date observations are missing.
    """
    import pandas as pd

    # Validate the input type and required columns.
    if not isinstance(history, pd.DataFrame):
        raise TypeError("history must be a pandas DataFrame.")

    required_columns = {"date", "ticker"}
    missing_columns = required_columns.difference(history.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing}")

    # Validate the requested horizons.
    if not horizons or any(
        not isinstance(horizon, int)
        or isinstance(horizon, bool)
        or horizon <= 0
        for horizon in horizons
    ):
        raise ValueError("horizons must contain positive integers.")

    if len(set(horizons)) != len(horizons):
        raise ValueError("horizons must not contain duplicates.")

    # Validate identifiers and parse dates without modifying the input.
    if history["ticker"].isna().any():
        raise ValueError("Ticker values must not be missing.")

    if history["date"].isna().any():
        raise ValueError("Date values must not be missing.")

    try:
        parsed_dates = pd.to_datetime(history["date"], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("Historical data contains invalid dates.") from exc

    if parsed_dates.isna().any():
        raise ValueError("Historical data contains missing dates.")

    # Use positional identifiers to support duplicate DataFrame indices.
    working = pd.DataFrame(
        {
            "_position": range(len(history)),
            "ticker": history["ticker"].to_numpy(),
            "date": parsed_dates.to_numpy(),
        }
    )

    # Reject duplicate observations for the same ticker and date.
    if working.duplicated(subset=["ticker", "date"]).any():
        raise ValueError(
            "Duplicate ticker-date observations are not allowed."
        )

    # Sort chronologically to identify each target's exit session.
    working = working.sort_values(
        ["ticker", "date"],
        kind="stable",
    )

    grouped_dates = working.groupby("ticker", sort=False)["date"]
    maturity_columns = {}

    # Map each observation to the closing session for each horizon.
    for horizon in horizons:
        maturity = grouped_dates.shift(-horizon)

        column = f"target_maturity_date_{horizon}d"
        maturity_columns[column] = pd.Series(
            maturity.to_numpy(),
            index=working["_position"].to_numpy(),
        )

    # Restore the original positional order and index.
    result = pd.DataFrame(
        {
            column: values.reindex(range(len(history))).to_numpy()
            for column, values in maturity_columns.items()
        },
        index=history.index,
    )

    # Return maturity dates without changing the historical input.
    return result


def get_matured_target_mask(
    maturity_dates,
    cutoff_date: date,
):
    """Identify targets whose outcomes were known by a training cutoff.

    Each maturity-date column is evaluated independently. A target is
    eligible when its maturity date is on or before the cutoff date.
    Missing maturity dates are not eligible.

    Args:
        maturity_dates: DataFrame containing target maturity-date columns.
        cutoff_date: Latest date on which an outcome may have matured.

    Returns:
        A Boolean DataFrame with the same index and one column per input
        maturity-date column.

    Raises:
        TypeError: If the input is not a DataFrame or cutoff_date is invalid.
        ValueError: If the input has no maturity-date columns or contains
            invalid non-missing dates.
    """
    import pandas as pd

    # Validate the input type.
    if not isinstance(maturity_dates, pd.DataFrame):
        raise TypeError("maturity_dates must be a pandas DataFrame.")

    # Require a plain calendar date as the training cutoff.
    if not isinstance(cutoff_date, date) or isinstance(cutoff_date, datetime):
        raise TypeError("cutoff_date must be a datetime.date instance.")

    # Require at least one maturity-date column.
    if maturity_dates.empty or len(maturity_dates.columns) == 0:
        raise ValueError("maturity_dates must contain maturity-date columns.")

    # Validate and evaluate each maturity-date column independently.
    eligible_columns = {}

    for column in maturity_dates.columns:
        try:
            parsed_dates = pd.to_datetime(
                maturity_dates[column],
                errors="raise",
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid maturity dates in column '{column}'."
            ) from exc

        # Missing maturity dates remain ineligible.
        eligible_columns[column] = (
            parsed_dates.notna()
            & (parsed_dates.dt.date <= cutoff_date)
        )

    # Preserve the input index and column names.
    return pd.DataFrame(eligible_columns, index=maturity_dates.index)


def get_training_eligibility_mask(
    history,
    maturity_dates,
    period_start: date,
    period_end: date,
    cutoff_date: date,
):
    """Identify observations eligible for model training without leakage.

    An observation is eligible for a target horizon only when:
    - Its observation date falls within the specified training period.
    - Its observation date is not later than the training cutoff.
    - Its target outcome has matured by the training cutoff.

    Eligibility is evaluated independently for each target horizon.

    Args:
        history: DataFrame containing the historical observation dates.
        maturity_dates: DataFrame containing target maturity-date columns.
        period_start: First permitted observation date, inclusive.
        period_end: Last permitted observation date, inclusive.
        cutoff_date: Latest date available when training takes place.

    Returns:
        A Boolean DataFrame with the same index and columns as
        maturity_dates.

    Raises:
        TypeError: If inputs or dates have invalid types.
        ValueError: If required columns, dates or index alignment are invalid.
    """
    import pandas as pd

    # Validate the historical data.
    if not isinstance(history, pd.DataFrame):
        raise TypeError("history must be a pandas DataFrame.")

    if "date" not in history.columns:
        raise ValueError("history must contain a 'date' column.")

    if not isinstance(maturity_dates, pd.DataFrame):
        raise TypeError("maturity_dates must be a pandas DataFrame.")

    # Require matching indices to prevent observations and targets
    # from becoming misaligned.
    if not history.index.equals(maturity_dates.index):
        raise ValueError(
            "history and maturity_dates must have identical indices "
            "in the same order."
        )

    # Validate the period boundaries and training cutoff.
    for name, value in (
        ("period_start", period_start),
        ("period_end", period_end),
        ("cutoff_date", cutoff_date),
    ):
        if not isinstance(value, date) or isinstance(value, datetime):
            raise TypeError(f"{name} must be a datetime.date instance.")

    if period_start > period_end:
        raise ValueError("period_start must not be after period_end.")

    # Parse observation dates and reject missing or invalid values.
    try:
        observation_dates = pd.to_datetime(
            history["date"],
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("history contains invalid observation dates.") from exc

    if observation_dates.isna().any():
        raise ValueError("history contains missing observation dates.")

    # Restrict observations to the permitted period and available history.
    observation_days = observation_dates.dt.date

    period_mask = (
        (observation_days >= period_start)
        & (observation_days <= period_end)
        & (observation_days <= cutoff_date)
    )

    # Reuse the existing horizon-specific maturity logic.
    matured_mask = get_matured_target_mask(
        maturity_dates,
        cutoff_date=cutoff_date,
    )

    # Both period membership and target maturity must be satisfied.
    eligible = matured_mask.mul(period_mask, axis=0)

    # Preserve the original row index and target column names.
    return eligible.astype(bool)
