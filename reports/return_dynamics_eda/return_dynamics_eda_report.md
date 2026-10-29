# LLOY.L Return Dynamics Exploratory Data Analysis

## Scope

- Source: `data/raw/yahoo/configured/LLOY.L.csv`
- Development period: 2016-10-24 to 2023-10-20
- Source observations: 2,985
- Development observations: 1,766
- Price convention: raw `Open` and `Close` prices; dividends are not added to returns.
- No model training, strategy backtest, or trading simulation was performed.
- The validation and final test periods were not used in this exploratory analysis.

## Daily Return Summary

- Non-missing daily returns: 1,765
- Mean: 0.00002853
- Standard deviation: 0.01932357
- Median: -0.00053237
- Skewness: 0.1216
- Excess kurtosis: 6.6993

## ADF Stationarity Test

- Test statistic: -10.308364
- p-value: 3.23389e-18
- Interpretation at 5%: Reject unit-root null at 5%

The ADF test evaluates a unit-root null hypothesis. Its result does not establish that returns are forecastable or that a trading strategy is profitable.

## Forward-Return Targets

Targets follow the approved definition `R(t,h) = Close(t+h) / Open(t+1) - 1` for horizons of 1, 5, and 10 trading sessions. Targets whose exit date would cross the end of the development period are excluded.

## Dependence Diagnostics

See `return_dependence_tests.csv` for Ljung–Box tests on returns and squared returns, plus the ARCH-LM diagnostic. Small p-values indicate evidence against the relevant null hypothesis, not proof of a profitable signal.

## Outputs

- `return_distribution_statistics.csv`
- `adf_stationarity_tests.csv`
- `return_dependence_tests.csv`
- `monthly_return_summary.csv`
- `annual_return_summary.csv`
- `development_returns_and_targets.csv`
- `daily_return_time_series.png`
- `daily_return_distribution.png`
- `daily_return_acf.png`
- `squared_return_acf.png`
- `monthly_mean_return.png`
- `monthly_return_volatility.png`

## Limitations

- Raw-price returns do not include dividend cash flows; this is consistent with the current target convention but is not a total-return measure.
- Overlapping forward-return targets are dependent, especially at longer horizons.
- Monthly and annual summaries are descriptive and should not be interpreted as independent statistical evidence.
- This report is exploratory and does not authorise model training or backtesting.
