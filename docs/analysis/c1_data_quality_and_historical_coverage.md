# C1 — Final Data Quality Decision

## Documented OHLC Anomalies — Accepted with Limitations

Three historical observations in the configured `LLOY.L` dataset violate the expected OHLC price relationships.

| Date       |    Open |    High |     Low |   Close | Inconsistency    |
| ---------- | ------: | ------: | ------: | ------: | ---------------- |
| 2015-03-31 | 79.3900 | 79.6500 | 78.3000 | 78.2800 | Close below Low  |
| 2020-06-15 | 30.4450 | 32.9400 | 30.8900 | 31.5300 | Open below Low   |
| 2024-05-01 | 52.1000 | 52.1400 | 51.9800 | 52.2000 | Close above High |

**Decision**

The project will retain these observations without modifying or deleting the original market data. The anomalies are considered a documented limitation for the current research scope, and no further investigation into their individual causes will be undertaken at this stage.

A dependency analysis identified a limited number of potentially affected feature observations and forward-return targets. This establishes the scope of potential exposure, but does not demonstrate that every dependent feature or target is numerically incorrect.

**Controls**

* Preserve the original OHLC values.
* Retain the three dates in the project's data-quality documentation.
* Do not automatically classify the anomalies as corporate-action effects.
* Do not silently correct, remove, or replace the observations.
* Reconsider the decision if future evidence indicates a material effect on model evaluation or simulated execution.

**Scope and limitation**

This decision is a documented acceptance of a known data limitation for continued research. It is not a declaration that the historical price series is error-free, nor does it independently establish that the dataset has passed all data-quality or corporate-action checks.

**Status:** Three OHLC anomalies documented; original observations retained; further investigation deferred.
