# Model Dataset Preparation Contract

**Project:** AI Quantitative Trading & Decision Intelligence System  
**Pilot asset:** `LLOY.L`  
**Status:** Implementation prepared; execution against the local historical dataset is pending.

## Purpose

Prepare reproducible, horizon-specific feature matrices and separate label ledgers from the existing integrated feature-target pipeline. This stage does not train models, fit preprocessing, or run backtests.

## Existing components reused

- `src.feature_target_pipeline.build_feature_target_dataset`
- `src.temporal_split.get_temporal_periods`
- `src.temporal_split.get_training_eligibility_mask`
- The existing target horizons and feature/target column definitions

No feature, target, maturity or eligibility calculation is reimplemented in the dataset-preparation module.

## Output layout

The default output directory is `data/processed/modeling/LLOY.L/`.

- `development_h{h}_features.csv`: features and observation identifiers for eligible Development training rows.
- `development_h{h}_labels.csv`: the matching target and maturity date, keyed by `date` and `ticker`.
- `validation_features.csv`: feature matrix for feature-complete Validation observations.
- `validation_h{h}_labels.csv`: separate Validation target ledger, with maturity status as of the latest available session.
- `final_test_features.csv`: feature matrix only; no target columns are included.
- `final_test_h{h}_labels.csv`: separate Final Test label ledger. Pending outcomes remain marked `pending`.
- `feature_exclusions.csv`: rows excluded from feature matrices due to missing or non-finite features, with the affected feature names.
- `dataset_summary.json`: period boundaries, row counts, feature exclusions, and horizon-specific maturity counts.

## Eligibility and missingness

1. The temporal periods retain the approved 7-year Development, 2-year Validation and 1-year Final Test structure, anchored to observed sessions.
2. Development labels are included only if their horizon-specific maturity is no later than the Development cutoff and the target is finite.
3. Features and labels are stored separately and can be aligned by `date` and `ticker`.
4. No missing feature is imputed. Rows with missing or non-finite contracted features are excluded from feature matrices and explicitly listed in `feature_exclusions.csv`.
5. Validation and Final Test label ledgers retain pending labels. A pending label is not a completed evaluation outcome.
6. Final Test features are stored separately from Final Test labels to reduce the risk of accidental target use during model fitting or selection.
7. Preprocessing fit, model training, hyperparameter selection and backtesting are outside this stage.

## Execution

From the repository root:

```bash
python scripts/prepare_model_dataset.py
```

Optional arguments:

```bash
python scripts/prepare_model_dataset.py \
  --input data/raw/yahoo/configured/LLOY.L.csv \
  --output-dir data/processed/modeling/LLOY.L \
  --as-of-date YYYY-MM-DD
```

The script reads the raw CSV and writes derived files under the processed-data directory. It does not alter the raw CSV.

## Acceptance

This preparation stage is complete only after the script runs against the local configured dataset and its output summary has been reviewed. The output counts must not be inferred from prior audits; they must be taken from this specific dataset-preparation run.
