# Baseline Model Evaluation Summary

## 1. Purpose and Scope

This report documents the validation results for the baseline forecasting models in the AI Quantitative Trading & Decision Intelligence System.
It summarises existing evaluation outputs and does not retrain models, change the evaluation, or assess trading-strategy profitability.

## 2. Evaluation Design

- **Pilot asset:** Lloyds Banking Group (LLOY.L), London Stock Exchange.
- **Forecast horizons:** 1, 5 and 10 trading sessions.
- **Validation period:** 23 October 2023 to 22 October 2025.
- **Primary metrics:** Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).
- **Complementary metrics:** Directional Accuracy, Spearman correlation and R-squared.
- **Baseline models:** Zero Return, Historical Mean and Historical Median.

The final test period remains isolated from model selection. The reported results concern validation data only.

## 3. Validation Performance

| Horizon | Model | Observations | MAE | RMSE | Directional Accuracy | Spearman Correlation | R-squared |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | zero_return | 507 | 0.009775 | 0.013668 | 0.469428 | Undefined | -0.006446 |
| 1 | historical_mean | 507 | 0.009777 | 0.013672 | 0.499014 | -0.094001 | -0.006982 |
| 1 | historical_median | 507 | 0.009812 | 0.013706 | 0.469428 | -0.090335 | -0.012020 |
| 5 | historical_mean | 507 | 0.026529 | 0.035942 | 0.587771 | -0.112736 | -0.041122 |
| 5 | zero_return | 507 | 0.026672 | 0.036054 | 0.382643 | Undefined | -0.047619 |
| 5 | historical_median | 507 | 0.026800 | 0.036161 | 0.441815 | -0.104527 | -0.053846 |
| 10 | historical_mean | 507 | 0.039749 | 0.051877 | 0.631164 | -0.134977 | -0.087566 |
| 10 | zero_return | 507 | 0.040146 | 0.052276 | 0.343195 | Undefined | -0.104330 |
| 10 | historical_median | 507 | 0.040274 | 0.052362 | 0.485207 | -0.110397 | -0.107960 |

MAE and RMSE are expressed in decimal return units. A value of 0.01 corresponds to a return magnitude of 1%.

## 4. Statistical Comparison

Paired comparisons were conducted on common observations. The recorded analysis includes absolute and squared loss, HAC/Newey–West inference, and Holm adjustment across 18 comparisons. The significance threshold is 0.05.

**Comparisons significant after Holm adjustment:** 2 of 18.

| Horizon | Loss | Model A | Model B | Mean Loss Difference (A − B) | HAC p-value | Holm-adjusted p-value |
|---:|---|---|---|---:|---:|---:|
| 5 | absolute | historical_mean | historical_median | -0.00027079 | 0.000796 | 0.014329 |
| 10 | absolute | historical_mean | historical_median | -0.00052581 | 0.001593 | 0.027088 |

The two significant comparisons favour the Historical Mean over the Historical Median in absolute loss at the 5- and 10-session horizons. Comparisons against Zero Return did not pass the Holm-adjusted threshold.

## 5. Bootstrap Robustness

The existing bootstrap robustness file contains 54 records. It evaluates block lengths of 5, 10 and 20 sessions.

Bootstrap confidence intervals provide complementary sensitivity evidence. They do not replace the pre-specified HAC tests or the Holm correction, and a confidence interval excluding zero should not independently be treated as confirmatory significance.

## 6. Limitations

1. Negative R-squared values indicate that these forecasts perform worse under this metric than predicting the observed validation-sample mean.
2. A constant zero-return prediction has undefined Spearman correlation because it has no variation.
3. Historical relationships may change across market regimes.
4. The target uses raw Open and Close prices; returns may reflect ex-dividend price drops and do not explicitly add dividend cash flows.
5. Forecasting metrics do not include transaction costs, spread, slippage, taxes or market impact.
6. Forecast accuracy does not establish trading profitability.
7. The conclusions are limited to the validation period and the documented statistical procedure.

## 7. Conclusions

The Historical Mean has the lowest MAE among the three baselines at the 5- and 10-session horizons. Its absolute-loss advantage over the Historical Median is statistically significant after Holm adjustment at both horizons.

No comparison against Zero Return passed the Holm-adjusted significance threshold. All recorded R-squared values are negative, so the baseline results do not yet demonstrate strong predictive value under that metric.

These findings establish reference points for subsequent research; they do not demonstrate positive net trading profitability.

## 8. Recommended Next Steps

1. Review this report and the baseline evaluation notebook.
2. Preserve the final test period as an untouched evaluation set.
3. Document approval before starting the next modelling phase.
4. When authorised, compare more complex models against these baselines using the same chronological controls and clearly defined evaluation criteria.

**Project control:** this report does not authorise progression to further modelling, backtesting or paper trading.
