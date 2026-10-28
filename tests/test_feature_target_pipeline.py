"""Integration tests for the feature/target pipeline contract."""

import pandas as pd
import pytest

from src.feature_target_pipeline import (
    FEATURE_COLUMNS,
    GENERATED_COLUMNS,
    MATURITY_COLUMNS,
    TARGET_COLUMNS,
    build_feature_target_dataset,
)


def _make_history(n_sessions: int = 30) -> pd.DataFrame:
    """Create two interleaved synthetic ticker histories."""
    rows = []
    dates = pd.bdate_range("2024-01-02", periods=n_sessions)

    for position, date in enumerate(dates):
        for ticker, offset in (("AAA", 0.0), ("BBB", 250.0)):
            open_price = 100.0 + offset + position
            close_price = 100.0 + offset + (0.5 * position)

            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "Open": open_price,
                    "High": max(open_price, close_price) + 1.0,
                    "Low": min(open_price, close_price) - 1.0,
                    "Close": close_price,
                    "Volume": 1_000 + position,
                }
            )

    frame = pd.DataFrame(rows)

    # Deliberately create duplicate index labels to test positional alignment.
    frame.index = [position // 2 for position in range(len(frame))]

    return frame


def test_pipeline_emits_all_columns_and_preserves_input():
    source = _make_history()
    original = source.copy(deep=True)

    result = build_feature_target_dataset(source)

    assert len(result) == len(source)
    assert result.index.equals(source.index)
    assert list(result.columns[:len(source.columns)]) == list(source.columns)

    assert set(GENERATED_COLUMNS).issubset(result.columns)
    assert len(FEATURE_COLUMNS) == 7
    assert len(TARGET_COLUMNS) == 6
    assert len(MATURITY_COLUMNS) == 3

    # The input DataFrame must remain unchanged.
    pd.testing.assert_frame_equal(source, original)


def test_pipeline_aligns_targets_and_maturity_dates():
    source = _make_history()
    result = build_feature_target_dataset(source)

    ticker = "AAA"
    ticker_rows = (
        source.loc[source["ticker"] == ticker]
        .sort_values("date")
        .reset_index(drop=True)
    )

    decision_position = 4
    decision_row = ticker_rows.iloc[decision_position]

    for horizon in (1, 5, 10):
        entry_row = ticker_rows.iloc[decision_position + 1]
        exit_row = ticker_rows.iloc[decision_position + horizon]

        expected_return = (
            exit_row["Close"] / entry_row["Open"] - 1.0
        )

        mask = (
            (result["ticker"] == ticker)
            & (result["date"] == decision_row["date"])
        )
        result_row = result.loc[mask].iloc[0]

        assert result_row[f"forward_return_{horizon}d"] == pytest.approx(
            expected_return
        )

        assert pd.Timestamp(
            result_row[f"target_maturity_date_{horizon}d"]
        ) == pd.Timestamp(exit_row["date"])

        expected_class = int(expected_return > 0)

        assert result_row[f"positive_return_{horizon}d"] == expected_class


def test_pipeline_does_not_cross_ticker_boundaries():
    source = _make_history()
    result = build_feature_target_dataset(source)

    ticker_rows = (
        source.loc[source["ticker"] == "BBB"]
        .sort_values("date")
        .reset_index(drop=True)
    )

    decision_position = 3
    horizon = 5

    expected_return = (
        ticker_rows.iloc[decision_position + horizon]["Close"]
        / ticker_rows.iloc[decision_position + 1]["Open"]
        - 1.0
    )

    decision_date = ticker_rows.iloc[decision_position]["date"]

    actual = result.loc[
        (result["ticker"] == "BBB")
        & (result["date"] == decision_date),
        "forward_return_5d",
    ].iloc[0]

    assert actual == pytest.approx(expected_return)


def test_targets_and_maturity_are_missing_without_future_sessions():
    source = _make_history(n_sessions=12)
    result = build_feature_target_dataset(source)

    for ticker in source["ticker"].unique():
        ticker_rows = (
            result.loc[result["ticker"] == ticker]
            .sort_values("date")
        )

        for horizon in (1, 5, 10):
            final_rows = ticker_rows.tail(horizon)

            assert final_rows[
                f"forward_return_{horizon}d"
            ].isna().all()

            assert final_rows[
                f"positive_return_{horizon}d"
            ].isna().all()

            assert final_rows[
                f"target_maturity_date_{horizon}d"
            ].isna().all()


def test_pipeline_rejects_existing_output_columns():
    source = _make_history()
    source["close_return_1d"] = 0.0

    with pytest.raises(
        ValueError,
        match="already contains pipeline output columns",
    ):
        build_feature_target_dataset(source)


def test_pipeline_rejects_missing_required_input_columns():
    source = _make_history().drop(columns=["Open"])

    with pytest.raises(
        ValueError,
        match="Missing required input columns",
    ):
        build_feature_target_dataset(source)