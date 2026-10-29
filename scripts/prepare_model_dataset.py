"""Prepare LLOY.L model datasets from the configured historical CSV.

This script writes feature matrices and separate label ledgers. It does not
fit preprocessing, train models, run backtests or modify raw data.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.config import load_asset_config
from src.model_dataset import write_model_dataset_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare split- and horizon-specific model datasets."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data/raw/yahoo/configured/LLOY.L.csv",
        help="Configured raw historical CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/processed/modeling/LLOY.L",
        help="Directory for prepared model dataset CSVs and summary JSON.",
    )
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=None,
        help="Optional ISO date (YYYY-MM-DD) to anchor the temporal periods.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_asset_config()
    configured_ticker = config["asset"]["ticker"]

    if not args.input.is_file():
        raise FileNotFoundError(
            f"Historical input file was not found: {args.input}"
        )

    history = pd.read_csv(args.input)
    if "ticker" not in history.columns:
        history["ticker"] = configured_ticker

    observed_tickers = set(history["ticker"].dropna().astype(str).unique())
    if observed_tickers != {configured_ticker}:
        raise ValueError(
            "Input ticker does not match configured asset. "
            f"Expected {configured_ticker!r}, found {sorted(observed_tickers)!r}."
        )

    summary = write_model_dataset_bundle(
        history=history,
        output_dir=args.output_dir,
        reference_date=args.as_of_date,
    )

    print("MODEL DATASET PREPARATION COMPLETE")
    print(f"Asset: {summary['asset']}")
    print(f"As-of date: {summary['as_of_date']}")
    print(f"Output directory: {args.output_dir}")
    for split_name, split_summary in summary["splits"].items():
        print(
            f"{split_name}: observations={split_summary['observations']}, "
            f"feature_complete={split_summary['feature_complete']}, "
            "excluded_for_missing_or_non_finite_features="
            f"{split_summary['excluded_for_missing_or_non_finite_features']}"
        )
        for key, value in split_summary.items():
            if key.startswith(("eligible_training_rows_", "matured_labels_", "pending_labels_")):
                print(f"  {key}: {value}")
    print("No preprocessing was fitted; no model was trained; no backtest was run.")


if __name__ == "__main__":
    main()
