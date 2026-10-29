"""Prepare horizon-specific model datasets from the integrated feature-target pipeline.

This module reuses existing feature, target, maturity and temporal-eligibility
functions. It does not fit preprocessing, train models or run backtests.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.feature_target_pipeline import (
    FEATURE_COLUMNS,
    build_feature_target_dataset,
)
from src.target_generation import HORIZONS
from src.temporal_split import (
    get_last_available_session,
    get_temporal_periods,
    get_training_eligibility_mask,
)

IDENTIFIER_COLUMNS = ("date", "ticker")


def _feature_complete_mask(frame: pd.DataFrame) -> pd.Series:
    """Return rows whose contracted features are numeric and finite."""
    numeric = frame.loc[:, FEATURE_COLUMNS].apply(
        pd.to_numeric, errors="raise"
    )
    values = numeric.to_numpy(dtype=float)
    return pd.Series(
        np.isfinite(values).all(axis=1),
        index=frame.index,
        name="features_complete",
    )


def _finite_target_mask(series: pd.Series) -> pd.Series:
    """Return a Boolean mask for finite, non-missing numeric targets."""
    numeric = pd.to_numeric(series, errors="raise")
    values = numeric.to_numpy(dtype=float, na_value=np.nan)
    return pd.Series(
        np.isfinite(values),
        index=series.index,
    )


def _date_string(series: pd.Series) -> pd.Series:
    """Represent dates consistently in CSV outputs."""
    parsed = pd.to_datetime(series, errors="raise")
    return parsed.dt.strftime("%Y-%m-%d")


def prepare_model_dataset_frames(
    history: pd.DataFrame,
    reference_date: date | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Build split/horizon feature and label tables without fitting transforms.

    Outputs are returned as a mapping of CSV stem to DataFrame plus a JSON-safe
    summary. Development rows are restricted to targets mature by the
    Development cutoff. Validation and Final Test features are kept separate
    from their label ledgers. Pending labels remain explicitly marked.

    Rows with missing/non-finite features are not imputed. They are excluded
    from feature matrices and recorded in ``feature_exclusions.csv``.
    """
    if not isinstance(history, pd.DataFrame):
        raise TypeError("history must be a pandas DataFrame.")

    required = {"date", "ticker", "Open", "Close"}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError(
            "Missing required input columns: " + ", ".join(sorted(missing))
        )
    if history.empty:
        raise ValueError("Historical data cannot be empty.")
    if history["ticker"].isna().any():
        raise ValueError("Ticker values must not be missing.")

    tickers = history["ticker"].drop_duplicates().tolist()
    if len(tickers) != 1:
        raise ValueError(
            "Model dataset preparation expects one configured asset per input; "
            f"found {len(tickers)} tickers."
        )

    working = history.copy(deep=True)
    parsed_dates = pd.to_datetime(working["date"], errors="raise")
    if parsed_dates.isna().any():
        raise ValueError("Historical data contains missing dates.")
    working["date"] = parsed_dates.dt.date

    if working.duplicated(subset=["ticker", "date"]).any():
        raise ValueError("Duplicate ticker-date observations are not allowed.")

    as_of = get_last_available_session(
        working,
        reference_date=reference_date,
    )
    periods = get_temporal_periods(
        working,
        reference_date=as_of,
        development_years=7,
        validation_years=2,
        final_test_years=1,
    )

    # Reuse the integrated pipeline; no feature/target calculation is duplicated.
    integrated = build_feature_target_dataset(working)
    integrated_dates = pd.to_datetime(integrated["date"], errors="raise").dt.date
    feature_complete = _feature_complete_mask(integrated)

    maturity_columns = [
        f"target_maturity_date_{horizon}d" for horizon in HORIZONS
    ]
    maturity_dates = integrated.loc[:, maturity_columns].copy()

    development_start, development_end = periods["development"]
    development_eligibility = get_training_eligibility_mask(
        history=integrated.loc[:, ["date"]],
        maturity_dates=maturity_dates,
        period_start=development_start,
        period_end=development_end,
        cutoff_date=development_end,
    )

    frames: dict[str, pd.DataFrame] = {}
    exclusions: list[pd.DataFrame] = []
    summary: dict[str, Any] = {
        "asset": tickers[0],
        "as_of_date": as_of.isoformat(),
        "horizons": list(HORIZONS),
        "feature_columns": list(FEATURE_COLUMNS),
        "target_definition": "Close(t+h) / Open(t+1) - 1",
        "missing_value_policy": (
            "No imputation. Feature rows with missing or non-finite contracted "
            "features are excluded from feature matrices and recorded. Labels "
            "with unavailable future outcomes remain pending."
        ),
        "periods": {
            name: {
                "start": bounds[0].isoformat(),
                "end": bounds[1].isoformat(),
            }
            for name, bounds in periods.items()
        },
        "splits": {},
    }

    period_masks: dict[str, pd.Series] = {}
    for split_name, (start, end) in periods.items():
        mask = pd.Series(
            (integrated_dates >= start) & (integrated_dates <= end),
            index=integrated.index,
        )
        period_masks[split_name] = mask
        count = int(mask.sum())
        complete_count = int((mask & feature_complete).sum())
        summary["splits"][split_name] = {
            "observations": count,
            "feature_complete": complete_count,
            "excluded_for_missing_or_non_finite_features": count - complete_count,
        }

        incomplete_mask = mask & ~feature_complete
        if incomplete_mask.any():
            excluded = integrated.loc[
                incomplete_mask, list(IDENTIFIER_COLUMNS)
            ].copy()
            excluded["split"] = split_name
            excluded["missing_feature_columns"] = integrated.loc[
                incomplete_mask, list(FEATURE_COLUMNS)
            ].apply(
                lambda row: ",".join(
                    column
                    for column in FEATURE_COLUMNS
                    if not np.isfinite(float(row[column]))
                ),
                axis=1,
            )
            exclusions.append(excluded)

    # Development: training examples only if target is mature at dev cutoff.
    development_mask = period_masks["development"]
    development_complete = development_mask & feature_complete
    for horizon in HORIZONS:
        target_column = f"forward_return_{horizon}d"
        maturity_column = f"target_maturity_date_{horizon}d"
        eligible = (
            development_eligibility[maturity_column]
            & development_complete
            & _finite_target_mask(integrated[target_column])
        )
        eligible_indices = integrated.index[eligible]

        x = integrated.loc[
            eligible_indices, list(IDENTIFIER_COLUMNS) + list(FEATURE_COLUMNS)
        ].copy()
        y = integrated.loc[
            eligible_indices,
            list(IDENTIFIER_COLUMNS) + [target_column, maturity_column],
        ].copy()
        x["date"] = _date_string(x["date"])
        y["date"] = _date_string(y["date"])
        y[maturity_column] = _date_string(y[maturity_column])

        frames[f"development_h{horizon}_features"] = x.reset_index(drop=True)
        frames[f"development_h{horizon}_labels"] = y.reset_index(drop=True)
        summary["splits"]["development"][f"eligible_training_rows_h{horizon}"] = int(
            len(eligible_indices)
        )

    # Validation and Final Test: keep X separate from the outcome ledger.
    for split_name in ("validation", "final_test"):
        split_mask = period_masks[split_name]
        split_complete = split_mask & feature_complete
        x_all = integrated.loc[
            split_complete,
            list(IDENTIFIER_COLUMNS) + list(FEATURE_COLUMNS),
        ].copy()
        x_all["date"] = _date_string(x_all["date"])
        frames[f"{split_name}_features"] = x_all.reset_index(drop=True)

        for horizon in HORIZONS:
            target_column = f"forward_return_{horizon}d"
            maturity_column = f"target_maturity_date_{horizon}d"
            target_values = pd.to_numeric(
                integrated[target_column], errors="raise"
            )
            maturity = pd.to_datetime(
                integrated[maturity_column], errors="raise"
            )
            matured_by_as_of = (
                maturity.notna()
                & (maturity.dt.date <= as_of)
                & _finite_target_mask(target_values)
            )
            pending = maturity.isna() | (maturity.dt.date > as_of)
            inconsistent = (
                maturity.notna()
                & (maturity.dt.date <= as_of)
                & ~_finite_target_mask(target_values)
            )
            if (split_mask & inconsistent).any():
                raise ValueError(
                    f"{split_name} contains a target with a matured date but "
                    f"no finite target value for horizon {horizon}."
                )

            labels = integrated.loc[
                split_mask,
                list(IDENTIFIER_COLUMNS) + [target_column, maturity_column],
            ].copy()
            labels["date"] = _date_string(labels["date"])
            labels[maturity_column] = _date_string(labels[maturity_column])
            labels["label_status_as_of_date"] = np.where(
                matured_by_as_of.loc[split_mask].to_numpy(),
                "matured",
                "pending",
            )
            frames[f"{split_name}_h{horizon}_labels"] = labels.reset_index(
                drop=True
            )
            summary["splits"][split_name][f"matured_labels_h{horizon}"] = int(
                (split_mask & matured_by_as_of).sum()
            )
            summary["splits"][split_name][f"pending_labels_h{horizon}"] = int(
                (split_mask & pending).sum()
            )

    if exclusions:
        frames["feature_exclusions"] = pd.concat(
            exclusions, ignore_index=True
        )
    else:
        frames["feature_exclusions"] = pd.DataFrame(
            columns=[
                "date",
                "ticker",
                "split",
                "missing_feature_columns",
            ]
        )

    return frames, summary


def write_model_dataset_bundle(
    history: pd.DataFrame,
    output_dir: Path | str,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Prepare and write CSV tables and a JSON summary to ``output_dir``."""
    import json

    output_path = Path(output_dir)
    frames, summary = prepare_model_dataset_frames(
        history=history,
        reference_date=reference_date,
    )
    output_path.mkdir(parents=True, exist_ok=True)

    for name, frame in frames.items():
        frame.to_csv(output_path / f"{name}.csv", index=False)

    (output_path / "dataset_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary
