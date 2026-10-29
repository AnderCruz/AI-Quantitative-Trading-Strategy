"""Explore LLOY.L return dynamics using the development period only.

This script does not train models or evaluate trading strategies. It reads the
existing canonical raw-price dataset and writes reproducible EDA outputs.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.stattools import adfuller


# Resolve project paths independently of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "yahoo" / "configured" / "LLOY.L.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "return_dynamics_eda"

# Use the approved development period for exploratory model-selection analysis.
DEVELOPMENT_START = pd.Timestamp("2016-10-24", tz="UTC")
DEVELOPMENT_END = pd.Timestamp("2023-10-20", tz="UTC")
HORIZONS = (1, 5, 10)
TEST_LAGS = (5, 10, 20)


# Configure clear, reproducible console logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def load_and_validate_data(path: Path) -> pd.DataFrame:
    """Load the canonical dataset and validate essential fields."""

    if not path.exists():
        raise FileNotFoundError(f"Historical dataset not found: {path}")

    data = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "Open", "Close", "ticker"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    # Normalise dates to UTC so split boundaries are compared consistently.
    dates = pd.to_datetime(data["date"], utc=True)
    data = data.assign(date=dates).sort_values("date").reset_index(drop=True)

    if data["date"].duplicated().any():
        duplicates = int(data["date"].duplicated().sum())
        raise ValueError(f"Dataset contains {duplicates} duplicate dates.")
    if data["ticker"].nunique() != 1 or data["ticker"].iloc[0] != "LLOY.L":
        raise ValueError("The canonical dataset must contain LLOY.L only.")
    if data[["Open", "Close"]].isna().any().any():
        raise ValueError("Open or Close contains missing values.")
    if (data[["Open", "Close"]] <= 0).any().any():
        raise ValueError("Open or Close contains non-positive prices.")

    return data


def build_development_series(data: pd.DataFrame) -> pd.DataFrame:
    """Create returns and forward targets without crossing the development boundary."""

    # Restrict the source observations to the development window first.
    development = data.loc[
        data["date"].between(DEVELOPMENT_START, DEVELOPMENT_END, inclusive="both")
    ].copy()
    development = development.sort_values("date").reset_index(drop=True)

    if development.empty:
        raise ValueError("No observations fall within the configured development period.")

    # Daily close-to-close returns are used for return-dynamics diagnostics.
    development["close_return_1d"] = development["Close"].pct_change()

    # Build targets from raw Open/Close prices, matching the project target definition.
    # Targets are only computed where both entry and exit dates remain in development.
    for horizon in HORIZONS:
        entry_open = development["Open"].shift(-1)
        exit_close = development["Close"].shift(-horizon)
        exit_date = development["date"].shift(-horizon)

        target = exit_close.div(entry_open).sub(1)
        target.loc[exit_date.isna() | (exit_date > DEVELOPMENT_END)] = np.nan
        development[f"forward_return_{horizon}d"] = target

    return development


def distribution_summary(series: pd.Series, name: str) -> dict[str, object]:
    """Calculate descriptive statistics for a numeric series."""

    values = series.dropna().astype(float)
    if values.empty:
        return {"series": name, "n": 0}

    return {
        "series": name,
        "n": int(values.size),
        "mean": float(values.mean()),
        "std": float(values.std(ddof=1)),
        "median": float(values.median()),
        "min": float(values.min()),
        "p01": float(values.quantile(0.01)),
        "p05": float(values.quantile(0.05)),
        "p25": float(values.quantile(0.25)),
        "p75": float(values.quantile(0.75)),
        "p95": float(values.quantile(0.95)),
        "p99": float(values.quantile(0.99)),
        "max": float(values.max()),
        "skewness": float(skew(values, bias=False)) if values.size > 2 else np.nan,
        "excess_kurtosis": float(kurtosis(values, fisher=True, bias=False))
        if values.size > 3 else np.nan,
    }


def run_stationarity_test(series: pd.Series, name: str) -> dict[str, object]:
    """Run the Augmented Dickey-Fuller test on a non-missing series."""

    values = series.dropna().astype(float)
    result: dict[str, object] = {
        "series": name,
        "n": int(values.size),
        "adf_statistic": np.nan,
        "p_value": np.nan,
        "used_lags": np.nan,
        "n_observations": np.nan,
        "critical_value_1pct": np.nan,
        "critical_value_5pct": np.nan,
        "critical_value_10pct": np.nan,
        "interpretation_5pct": "Not tested",
    }
    if values.size < 30 or values.nunique() < 2:
        result["interpretation_5pct"] = "Insufficient data or constant series"
        return result

    test = adfuller(values, regression="c", autolag="AIC")
    result.update({
        "adf_statistic": float(test[0]),
        "p_value": float(test[1]),
        "used_lags": int(test[2]),
        "n_observations": int(test[3]),
        "critical_value_1pct": float(test[4]["1%"]),
        "critical_value_5pct": float(test[4]["5%"]),
        "critical_value_10pct": float(test[4]["10%"]),
        "interpretation_5pct": (
            "Reject unit-root null at 5%" if test[1] < 0.05
            else "Do not reject unit-root null at 5%"
        ),
    })
    return result


def run_dependence_tests(series: pd.Series, name: str) -> list[dict[str, object]]:
    """Run Ljung-Box and ARCH-LM diagnostics on returns or squared returns."""

    values = series.dropna().astype(float)
    rows: list[dict[str, object]] = []
    if values.size < max(TEST_LAGS) + 10:
        return rows

    # Ljung-Box tests whether autocorrelations up to each lag are jointly zero.
    for lag in TEST_LAGS:
        lb = acorr_ljungbox(values, lags=[lag], return_df=True)
        rows.append({
            "series": name,
            "test": "Ljung-Box",
            "lags": lag,
            "statistic": float(lb["lb_stat"].iloc[0]),
            "p_value": float(lb["lb_pvalue"].iloc[0]),
        })

    # ARCH-LM tests for conditional heteroskedasticity in the return series.
    arch_stat, arch_pvalue, _, _ = het_arch(values, nlags=10)
    rows.append({
        "series": name,
        "test": "ARCH-LM",
        "lags": 10,
        "statistic": float(arch_stat),
        "p_value": float(arch_pvalue),
    })
    return rows


def save_plots(data: pd.DataFrame, output_dir: Path) -> list[str]:
    """Save return distribution, time-series, and autocorrelation plots."""

    plot_files: list[str] = []
    returns = data["close_return_1d"].dropna()

    # Plot the daily return time series.
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(data["date"], data["close_return_1d"], linewidth=0.7)
    ax.axhline(0, linewidth=0.8)
    ax.set_title("LLOY.L Daily Close-to-Close Returns — Development Period")
    ax.set_xlabel("Date")
    ax.set_ylabel("Simple return")
    fig.tight_layout()
    filename = "daily_return_time_series.png"
    fig.savefig(output_dir / filename, dpi=150)
    plt.close(fig)
    plot_files.append(filename)

    # Plot the return distribution with a robust central view.
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(returns, bins=80)
    ax.set_title("LLOY.L Daily Return Distribution — Development Period")
    ax.set_xlabel("Simple return")
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    filename = "daily_return_distribution.png"
    fig.savefig(output_dir / filename, dpi=150)
    plt.close(fig)
    plot_files.append(filename)

    # Plot ACF for daily returns and squared returns.
    for values, label, filename in [
        (returns, "Daily Returns", "daily_return_acf.png"),
        (returns.pow(2), "Squared Daily Returns", "squared_return_acf.png"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 5))
        plot_acf(values, lags=40, zero=False, ax=ax, missing="drop")
        ax.set_title(f"ACF of {label} — Development Period")
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)
        plot_files.append(filename)

    # Plot monthly mean and standard deviation as descriptive stability checks.
    monthly = data.set_index("date")["close_return_1d"].resample("MS").agg(
        ["mean", "std"]
    )
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(monthly.index, monthly["mean"], linewidth=1.0)
    ax.axhline(0, linewidth=0.8)
    ax.set_title("Monthly Mean of Daily Returns — Development Period")
    ax.set_xlabel("Month")
    ax.set_ylabel("Mean daily return")
    fig.tight_layout()
    filename = "monthly_mean_return.png"
    fig.savefig(output_dir / filename, dpi=150)
    plt.close(fig)
    plot_files.append(filename)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(monthly.index, monthly["std"], linewidth=1.0)
    ax.set_title("Monthly Standard Deviation of Daily Returns — Development Period")
    ax.set_xlabel("Month")
    ax.set_ylabel("Daily return standard deviation")
    fig.tight_layout()
    filename = "monthly_return_volatility.png"
    fig.savefig(output_dir / filename, dpi=150)
    plt.close(fig)
    plot_files.append(filename)

    return plot_files


def main() -> int:
    """Run return-dynamics EDA and write machine-readable and narrative outputs."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Loading canonical historical data: %s", INPUT_PATH)
    raw = load_and_validate_data(INPUT_PATH)
    data = build_development_series(raw)

    return_series = data["close_return_1d"]
    target_columns = [f"forward_return_{horizon}d" for horizon in HORIZONS]

    # Summarise daily returns and each forward-return target.
    distribution_rows = [
        distribution_summary(return_series, "close_return_1d")
    ]
    distribution_rows.extend(
        distribution_summary(data[column], column) for column in target_columns
    )
    distributions = pd.DataFrame(distribution_rows)
    distributions.to_csv(OUTPUT_DIR / "return_distribution_statistics.csv", index=False)

    # Test stationarity for daily returns and the forward-return targets.
    stationarity_rows = [
        run_stationarity_test(return_series, "close_return_1d")
    ]
    stationarity_rows.extend(
        run_stationarity_test(data[column], column) for column in target_columns
    )
    stationarity = pd.DataFrame(stationarity_rows)
    stationarity.to_csv(OUTPUT_DIR / "adf_stationarity_tests.csv", index=False)

    # Run dependence diagnostics on daily returns and squared returns.
    dependence_rows = run_dependence_tests(return_series, "close_return_1d")
    dependence_rows.extend(
        run_dependence_tests(return_series.pow(2), "squared_close_return_1d")
    )
    dependence = pd.DataFrame(dependence_rows)
    dependence.to_csv(OUTPUT_DIR / "return_dependence_tests.csv", index=False)

    # Create monthly and annual summaries for temporal stability inspection.
    dated = data.set_index("date")
    monthly = dated["close_return_1d"].resample("MS").agg(
        observations="count", mean="mean", std="std", median="median"
    )
    monthly.index.name = "period"
    monthly.to_csv(OUTPUT_DIR / "monthly_return_summary.csv")

    annual = dated["close_return_1d"].resample("YS").agg(
        observations="count", mean="mean", std="std", median="median"
    )
    annual.index.name = "period"
    annual.to_csv(OUTPUT_DIR / "annual_return_summary.csv")

    # Save a compact dataset containing the return series and target columns.
    export_columns = ["date", "ticker", "Open", "Close", "close_return_1d", *target_columns]
    data[export_columns].to_csv(OUTPUT_DIR / "development_returns_and_targets.csv", index=False)

    plot_files = save_plots(data, OUTPUT_DIR)

    # Write a report that describes the analysis without claiming profitability.
    daily_stats = distributions.loc[
        distributions["series"].eq("close_return_1d")
    ].iloc[0]
    adf_daily = stationarity.loc[
        stationarity["series"].eq("close_return_1d")
    ].iloc[0]
    report_lines = [
        "# LLOY.L Return Dynamics Exploratory Data Analysis",
        "",
        "## Scope",
        "",
        f"- Source: `{INPUT_PATH.relative_to(PROJECT_ROOT)}`",
        f"- Development period: {DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
        f"- Source observations: {len(raw):,}",
        f"- Development observations: {len(data):,}",
        "- Price convention: raw `Open` and `Close` prices; dividends are not added to returns.",
        "- No model training, strategy backtest, or trading simulation was performed.",
        "- The validation and final test periods were not used in this exploratory analysis.",
        "",
        "## Daily Return Summary",
        "",
        f"- Non-missing daily returns: {int(daily_stats['n']):,}",
        f"- Mean: {daily_stats['mean']:.8f}",
        f"- Standard deviation: {daily_stats['std']:.8f}",
        f"- Median: {daily_stats['median']:.8f}",
        f"- Skewness: {daily_stats['skewness']:.4f}",
        f"- Excess kurtosis: {daily_stats['excess_kurtosis']:.4f}",
        "",
        "## ADF Stationarity Test",
        "",
        f"- Test statistic: {adf_daily['adf_statistic']:.6f}",
        f"- p-value: {adf_daily['p_value']:.6g}",
        f"- Interpretation at 5%: {adf_daily['interpretation_5pct']}",
        "",
        "The ADF test evaluates a unit-root null hypothesis. Its result does not establish "
        "that returns are forecastable or that a trading strategy is profitable.",
        "",
        "## Forward-Return Targets",
        "",
        "Targets follow the approved definition `R(t,h) = Close(t+h) / Open(t+1) - 1` "
        "for horizons of 1, 5, and 10 trading sessions. Targets whose exit date would "
        "cross the end of the development period are excluded.",
        "",
        "## Dependence Diagnostics",
        "",
        "See `return_dependence_tests.csv` for Ljung–Box tests on returns and squared "
        "returns, plus the ARCH-LM diagnostic. Small p-values indicate evidence against "
        "the relevant null hypothesis, not proof of a profitable signal.",
        "",
        "## Outputs",
        "",
    ]
    report_lines.extend(f"- `{filename}`" for filename in [
        "return_distribution_statistics.csv",
        "adf_stationarity_tests.csv",
        "return_dependence_tests.csv",
        "monthly_return_summary.csv",
        "annual_return_summary.csv",
        "development_returns_and_targets.csv",
        *plot_files,
    ])
    report_lines.extend([
        "",
        "## Limitations",
        "",
        "- Raw-price returns do not include dividend cash flows; this is consistent with "
        "the current target convention but is not a total-return measure.",
        "- Overlapping forward-return targets are dependent, especially at longer horizons.",
        "- Monthly and annual summaries are descriptive and should not be interpreted as "
        "independent statistical evidence.",
        "- This report is exploratory and does not authorise model training or backtesting.",
        "",
    ])
    (OUTPUT_DIR / "return_dynamics_eda_report.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )

    logger.info("EDA completed successfully.")
    logger.info("Output directory: %s", OUTPUT_DIR)
    logger.info("Generated %s CSV files and %s plots.", 6, len(plot_files))
    logger.info("Report: %s", OUTPUT_DIR / "return_dynamics_eda_report.md")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logger.exception("Return-dynamics EDA failed: %s", exc)
        raise
