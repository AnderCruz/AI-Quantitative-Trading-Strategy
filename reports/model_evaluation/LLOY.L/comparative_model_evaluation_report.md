# Comparative Model Evaluation Report

## 1. Executive Summary

Six forecasting approaches have been evaluated for Lloyds Banking Group (`LLOY.L`), listed on the London Stock Exchange:

* Zero Return
* Historical Mean
* Historical Median
* Ridge Regression
* LightGBM Regression
* Multi-Layer Perceptron (MLP)

The comparison covers forecast horizons of 1, 5 and 10 trading sessions.

All six models were compared on identical date-horizon observations. The evaluation used 1,505 common observations, producing 9,030 aligned model-prediction records.

The Final Test period was excluded, and no trading backtest was performed.

The results do not establish that any model is profitable. They provide evidence about forecasting performance under the current walk-forward evaluation design.

## 2. Evaluation Framework

| Parameter                | Configuration                     |
| ------------------------ | --------------------------------- |
| Instrument               | Lloyds Banking Group              |
| Ticker                   | `LLOY.L`                          |
| Exchange                 | London Stock Exchange             |
| Market-data source       | Yahoo Finance                     |
| Development period       | 24 October 2016 – 20 October 2023 |
| Validation period        | 23 October 2023 – 22 October 2025 |
| Final Test period        | 23 October 2025 – 23 October 2026 |
| Forecast horizons        | 1, 5 and 10 trading sessions      |
| Evaluation method        | Expanding-window walk-forward     |
| Minimum training samples | 500                               |
| Final Test used          | No                                |
| Backtesting performed    | No                                |

The forecast targets represent forward returns, with target maturity constraints used to prevent future information from entering the training process.

## 3. Comparative Results

### 3.1 One-session horizon

| Model               |      MAE |     RMSE | Directional Accuracy |      R² |
| ------------------- | -------: | -------: | -------------------: | ------: |
| Zero Return         | 0.009757 | 0.013655 |       Not meaningful | -0.0060 |
| Historical Mean     | 0.009759 | 0.013659 |               49.80% | -0.0066 |
| Historical Median   | 0.009793 | 0.013693 |               46.25% | -0.0116 |
| Ridge Regression    | 0.009777 | 0.013688 |               50.00% | -0.0109 |
| LightGBM Regression | 0.009854 | 0.013752 |               52.96% | -0.0204 |
| MLP Regression      | 0.016136 | 0.021704 |               53.36% | -1.5417 |

Zero Return achieved the lowest MAE and RMSE. The MLP produced the highest reported directional accuracy among the learned models, but its forecast errors were substantially larger.

No learned model demonstrated a compelling overall advantage at this horizon.

### 3.2 Five-session horizon

| Model               |      MAE |     RMSE | Directional Accuracy |      R² |
| ------------------- | -------: | -------: | -------------------: | ------: |
| Zero Return         | 0.026485 | 0.035934 |       Not meaningful | -0.0432 |
| Historical Mean     | 0.026355 | 0.035839 |               58.37% | -0.0377 |
| Historical Median   | 0.026620 | 0.036050 |               37.25% | -0.0499 |
| Ridge Regression    | 0.026023 | 0.035465 |               59.36% | -0.0161 |
| LightGBM Regression | 0.026133 | 0.035502 |               54.58% | -0.0183 |
| MLP Regression      | 0.031753 | 0.042175 |               48.41% | -0.4370 |

Ridge achieved the lowest MAE and RMSE. It also reported the highest directional accuracy among the six approaches.

LightGBM remained competitive in forecast error, but it did not outperform Ridge on these metrics.

The MLP performed worse than the other models in MAE, RMSE and R².

### 3.3 Ten-session horizon

| Model               |      MAE |     RMSE | Directional Accuracy |      R² |
| ------------------- | -------: | -------: | -------------------: | ------: |
| Zero Return         | 0.039843 | 0.052158 |       Not meaningful | -0.0939 |
| Historical Mean     | 0.039502 | 0.051818 |               62.37% | -0.0797 |
| Historical Median   | 0.040012 | 0.052286 |               47.08% | -0.0992 |
| Ridge Regression    | 0.039124 | 0.051289 |               56.14% | -0.0577 |
| LightGBM Regression | 0.039940 | 0.052301 |               48.89% | -0.0999 |
| MLP Regression      | 0.044880 | 0.058873 |               50.30% | -0.3937 |

Ridge achieved the lowest MAE and RMSE. Historical Mean reported the highest directional accuracy.

These results illustrate why forecast magnitude and directional performance must be assessed separately.

## 4. Main Findings

### Ridge Regression

Ridge is the strongest current learned-model candidate based on MAE and RMSE at the five- and ten-session horizons.

Its performance provides an important benchmark for assessing whether more complex sequence models add value.

### LightGBM Regression

LightGBM remains a useful nonlinear benchmark. However, its current forecast errors do not establish an advantage over Ridge.

### MLP Regression

The MLP did not demonstrate an improvement over the simpler approaches.

Its negative R² values, particularly at the one-session horizon, indicate weak performance relative to a mean-based reference under the current evaluation.

The model should not be prioritised for further experiments without a specific, testable hypothesis for improvement.

### Baseline Models

The baseline models remain essential.

Zero Return is particularly competitive on one-session MAE and RMSE. Historical Mean performs comparatively well on directional accuracy at the ten-session horizon.

Neither result alone demonstrates a tradable advantage.

## 5. Interpretation and Limitations

Directional accuracy for a prediction of exactly zero is not meaningful as a measure of correctly forecasting an upward or downward move.

Consequently, Zero Return must be assessed using error metrics and treated as a non-directional reference. Directional accuracy should be interpreted alongside directional coverage.

All reported R² values are negative. Under the current evaluation, this indicates that the forecasts do not outperform the relevant mean-based reference under the R² metric.

Forecast accuracy does not establish trading profitability. No conclusions about returns after transaction costs, turnover, risk exposure or execution constraints can be drawn from this evaluation.

The results also do not establish statistical superiority for any model unless supported by an appropriate statistical comparison.

## 6. Model Status

| Model               | Current Assessment                                               | Decision                                       |
| ------------------- | ---------------------------------------------------------------- | ---------------------------------------------- |
| Zero Return         | Strong short-horizon error baseline                              | Retain                                         |
| Historical Mean     | Useful benchmark, particularly at 10 sessions                    | Retain                                         |
| Historical Median   | Useful robust benchmark                                          | Retain                                         |
| Ridge Regression    | Strongest current learned model by MAE/RMSE at 5 and 10 sessions | Retain as primary reference                    |
| LightGBM Regression | Useful nonlinear comparison                                      | Retain                                         |
| MLP Regression      | No demonstrated improvement                                      | Keep results; do not prioritise further tuning |

These are provisional research decisions, not production deployment decisions.

## 7. Next Step

Proceed to an LSTM model as the next experimental candidate.

The LSTM should use the same instrument, forecast targets, horizons, development period, validation period and temporal safeguards.

Its evaluation should be compared against the existing models on identical date-horizon observations.

The Final Test period must remain excluded, and no backtesting should be performed as part of this stage.
