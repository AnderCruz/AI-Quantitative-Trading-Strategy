"""Audit temporal periods and target maturity for LLOY.L."""

from pathlib import Path

import pandas as pd
import numpy as np

from src.target_generation import create_targets
from src.temporal_split import (
    get_target_maturity_dates,
    get_temporal_periods,
    get_training_eligibility_mask,
)

# Load the configured historical dataset without modifying the source.
data_path = Path("data/raw/yahoo/configured/LLOY.L.csv")
history = pd.read_csv(data_path)

# Parse dates consistently while preserving the original row order.
history["date"] = pd.to_datetime(
    history["date"],
    errors="raise",
).dt.date

# Define the approved forecast horizons.
horizons = (1, 5, 10)

# Generate targets and their corresponding maturity dates.
targeted_history = create_targets(history)
maturity_dates = get_target_maturity_dates(
    history,
    horizons=horizons,
)

# Derive contiguous temporal periods from the available history.
periods = get_temporal_periods(
    history,
    development_years=7,
    validation_years=2,
    final_test_years=1,
)

latest_session = max(history["date"])
print("=" * 72)
print("LLOY.L TEMPORAL AND TARGET MATURITY AUDIT")
print("=" * 72)
print(f"Historical observations: {len(history):,}")
print(f"First session: {min(history['date'])}")
print(f"Latest session: {latest_session}")
print(f"Forecast horizons: {horizons}")
print()

# Report period boundaries and observation counts.
period_counts = {}

for period_name, (period_start, period_end) in periods.items():
    membership = history["date"].between(
        period_start,
        period_end,
        inclusive="both",
    )
    period_counts[period_name] = membership

    print(f"{period_name.upper()}")
    print(f"  Start: {period_start}")
    print(f"  End:   {period_end}")
    print(f"  Observations: {int(membership.sum()):,}")

    # Evaluate maturity at the period end and at the latest available session.
    period_history = history.loc[membership]
    period_maturities = maturity_dates.loc[membership]

    print("  Target maturity:")
    for horizon in horizons:
        column = f"target_maturity_date_{horizon}d"
        maturity = pd.to_datetime(
            period_maturities[column],
            errors="raise",
        ).dt.date

        valid_targets = int(maturity.notna().sum())
        matured_by_period_end = int(
            (maturity.notna() & (maturity <= period_end)).sum()
        )
        matured_by_latest = int(
            (maturity.notna() & (maturity <= latest_session)).sum()
        )
        pending_at_latest = int(
            (maturity.isna() | (maturity > latest_session)).sum()
        )

        print(
            f"    {horizon:2d}-session horizon: "
            f"valid={valid_targets:,}; "
            f"matured_by_period_end={matured_by_period_end:,}; "
            f"matured_by_latest={matured_by_latest:,}; "
            f"pending_at_latest={pending_at_latest:,}"
        )

    print()

# Specifically audit Development training eligibility at its cutoff.
development_start, development_end = periods["development"]

development_membership = history["date"].between(
    development_start,
    development_end,
    inclusive="both",
)

development_history = history.loc[development_membership]
development_maturities = maturity_dates.loc[development_membership]

eligibility = get_training_eligibility_mask(
    history=development_history,
    maturity_dates=development_maturities,
    period_start=development_start,
    period_end=development_end,
    cutoff_date=development_end,
)

print("=" * 72)
print("DEVELOPMENT TRAINING ELIGIBILITY")
print("=" * 72)
print(f"Development cutoff: {development_end}")
print(f"Development observations: {len(development_history):,}")

for horizon in horizons:
    column = f"target_maturity_date_{horizon}d"
    eligible_count = int(eligibility[column].sum())
    excluded_count = len(eligibility) - eligible_count

    print(
        f"{horizon:2d}-session horizon: "
        f"eligible={eligible_count:,}; "
        f"excluded={excluded_count:,}"
    )

# Confirm that no eligible observation violates the period or cutoff.
for horizon in horizons:
    eligible_rows = development_history.loc[
        eligibility[f"target_maturity_date_{horizon}d"]
    ]

    assert eligible_rows["date"].between(
        development_start,
        development_end,
        inclusive="both",
    ).all()

    assert (
        development_maturities.loc[
            eligibility[f"target_maturity_date_{horizon}d"],
            f"target_maturity_date_{horizon}d",
        ]
        .dt.date.le(development_end)
        .all()
    )

print()
print("AUDIT ASSERTIONS PASSED.")
print("No model training or backtesting was performed.")

# Audit walk-forward eligibility at every available validation session.
development_start, development_end = periods["development"]
validation_start, validation_end = periods["validation"]

# Include Development and Validation observations available by each cutoff.
training_history = history.loc[
    history["date"].between(
        development_start,
        validation_end,
        inclusive="both",
    )
].copy()

training_maturities = maturity_dates.loc[training_history.index]

# Use every observed Validation session as a retraining cutoff.
validation_sessions = sorted(
    training_history.loc[
        training_history["date"].between(
            validation_start,
            validation_end,
            inclusive="both",
        ),
        "date",
    ].unique()
)

assert validation_sessions, "No Validation sessions were found."

print()
print("=" * 72)
print("EXHAUSTIVE WALK-FORWARD ELIGIBILITY AUDIT")
print("=" * 72)
print(f"Validation sessions checked: {len(validation_sessions):,}")
print(f"First cutoff: {validation_sessions[0]}")
print(f"Last cutoff:  {validation_sessions[-1]}")

# Track eligible observations separately for each forecast horizon.
previous_masks = {}
total_checks = 0

for cutoff in validation_sessions:
    mask = get_training_eligibility_mask(
        history=training_history,
        maturity_dates=training_maturities,
        period_start=development_start,
        period_end=validation_end,
        cutoff_date=cutoff,
    )

    # Verify each horizon independently at this retraining cutoff.
    for horizon in horizons:
        column = f"target_maturity_date_{horizon}d"
        eligible = mask[column]
        eligible_indices = mask.index[eligible]
        eligible_count = int(eligible.sum())

        # No observation dated after the cutoff may enter training.
        assert (
            training_history.loc[eligible_indices, "date"] <= cutoff
        ).all(), (
            f"Future observation included: cutoff={cutoff}, "
            f"horizon={horizon}"
        )

        # Every eligible target must have matured by the cutoff.
        matured_dates = pd.to_datetime(
            training_maturities.loc[eligible_indices, column],
            errors="raise",
        ).dt.date

        assert matured_dates.notna().all(), (
            f"Missing target maturity: cutoff={cutoff}, "
            f"horizon={horizon}"
        )
        assert matured_dates.le(cutoff).all(), (
            f"Immature target included: cutoff={cutoff}, "
            f"horizon={horizon}"
        )

        # Eligibility must not decrease as the cutoff advances.
        if horizon in previous_masks:
            previous = previous_masks[horizon]
            newly_eligible_indices = previous.index[previous]

            assert newly_eligible_indices.isin(
                eligible_indices
            ).all(), (
                f"Previously eligible observations were lost: "
                f"cutoff={cutoff}, horizon={horizon}"
            )

        previous_masks[horizon] = eligible
        total_checks += 1

    # Print progress periodically without flooding the terminal.
    if (
        total_checks == len(horizons)
        or validation_sessions.index(cutoff) % 50 == 0
        or cutoff == validation_sessions[-1]
    ):
        print(
            f"Checked cutoff {cutoff}: "
            + ", ".join(
                f"{horizon}-session={int(mask[f'target_maturity_date_{horizon}d'].sum()):,}"
                for horizon in horizons
            )
        )

print()
print(f"Successful horizon checks: {total_checks:,}")
print("EXHAUSTIVE WALK-FORWARD AUDIT PASSED.")
print("No model training or backtesting was performed.")
# ---------------------------------------------------------------------------
# Integrated feature, target and maturity audit.
# ---------------------------------------------------------------------------

from src.feature_engineering import create_historical_return_features

print()
print("=" * 72)
print("INTEGRATED FEATURE AND TARGET AUDIT")
print("=" * 72)

# Preserve the historical input before generating additional columns.
original_history = history.copy(deep=True)

# Generate historical features without modifying the source data.
featured_history = create_historical_return_features(history)

# Define the seven approved historical features.
feature_columns = [
    "close_return_1d",
    "close_return_5d",
    "close_return_10d",
    "close_return_20d",
    "close_volatility_5d",
    "close_volatility_10d",
    "close_volatility_20d",
]

# Confirm that all approved features have been generated.
assert all(
    column in featured_history.columns
    for column in feature_columns
), "One or more approved features are missing."

# Confirm that feature engineering preserves observation alignment.
assert featured_history.index.equals(history.index), (
    "Feature engineering changed the original index."
)
assert featured_history["date"].reset_index(drop=True).equals(
    pd.to_datetime(history["date"]).reset_index(drop=True)
), "Feature dates are not aligned with the original observations."
assert featured_history["ticker"].reset_index(drop=True).equals(
    history["ticker"].reset_index(drop=True)
), "Feature tickers are not aligned with the original observations."

# Confirm that feature engineering does not modify the input data.
pd.testing.assert_frame_equal(history, original_history)

# Check feature values and report initial missing observations.
for column in feature_columns:
    values = featured_history[column]

    assert not np.isinf(values.dropna()).any(), (
        f"Infinite values detected in feature {column}."
    )

    print(
        f"{column}: "
        f"valid={int(values.notna().sum()):,}; "
        f"missing={int(values.isna().sum()):,}"
    )

# Generate targets and their maturity dates on the same historical rows.
integrated_targets = create_targets(history)
integrated_maturities = get_target_maturity_dates(
    history,
    horizons=horizons,
)

# Confirm that all target and maturity columns exist and remain aligned.
for horizon in horizons:
    return_column = f"forward_return_{horizon}d"
    classification_column = f"positive_return_{horizon}d"
    maturity_column = f"target_maturity_date_{horizon}d"

    assert return_column in integrated_targets.columns
    assert classification_column in integrated_targets.columns
    assert maturity_column in integrated_maturities.columns

    assert integrated_targets.index.equals(history.index)
    assert integrated_maturities.index.equals(history.index)

    # A target is available if and only if its exit session is known.
    target_valid = integrated_targets[return_column].notna()
    maturity_valid = integrated_maturities[maturity_column].notna()

    assert target_valid.equals(maturity_valid), (
        f"Target and maturity availability differ for horizon {horizon}."
    )

    # Compare each maturity date with the actual historical session t+h.
    chronological = history.sort_values(
        ["ticker", "date"],
        kind="stable",
    )

    expected_maturity = (
        chronological.groupby("ticker", sort=False)["date"]
        .shift(-horizon)
        .reindex(history.index)
    )

    actual_maturity = pd.to_datetime(
        integrated_maturities[maturity_column],
        errors="raise",
    ).dt.date

    expected_maturity = pd.to_datetime(
        expected_maturity,
        errors="raise",
    ).dt.date

    assert actual_maturity.reset_index(drop=True).equals(
        expected_maturity.reset_index(drop=True)
    ), f"Incorrect maturity dates for horizon {horizon}."

    # Confirm that classification targets agree with the return definition.
    valid_returns = integrated_targets.loc[target_valid, return_column]
    expected_classification = (valid_returns > 0).astype(int)

    actual_classification = integrated_targets.loc[
        target_valid,
        classification_column,
    ].astype(int)

    assert actual_classification.equals(expected_classification), (
        f"Classification targets are inconsistent for horizon {horizon}."
    )

    print(
        f"{horizon}-session horizon: "
        f"valid_targets={int(target_valid.sum()):,}; "
        f"missing_targets={int((~target_valid).sum()):,}; "
        "maturity dates verified."
    )

# Explicitly confirm that walk-forward training history excludes Final Test.
final_test_start, final_test_end = periods["final_test"]

assert not training_history["date"].between(
    final_test_start,
    final_test_end,
    inclusive="both",
).any(), "Final Test observations entered the walk-forward training history."

# Confirm that feature and target generation did not modify the source.
pd.testing.assert_frame_equal(history, original_history)

print()
print("INTEGRATED FEATURE AND TARGET AUDIT PASSED.")
print("Final Test remains excluded from walk-forward training history.")
print("No model training or backtesting was performed.")
