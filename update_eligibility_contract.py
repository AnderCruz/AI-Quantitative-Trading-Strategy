from pathlib import Path

path = Path("docs/data/integrated_feature_target_pipeline_contract.md")
text = path.read_text(encoding="utf-8")

replacements = [
    (
        "**Status:** Proposed contract — pending implementation verification",
        "**Status:** Integrated feature-target pipeline implemented; focused integration tests and the recorded temporal eligibility audit have passed. Full modelling-pipeline leakage verification remains pending.",
    ),
    (
        """This condition is necessary but may not be sufficient for inclusion in a particular training or evaluation window.

The complete eligibility decision must also respect the approved chronological split, the prediction and training cutoffs, and any purging rules required to prevent overlapping target intervals from contaminating evaluation.

The final test period must not be used for model fitting, feature selection, preprocessing decisions or hyperparameter selection.""",
        """For the approved sequential walk-forward protocol, an observation is eligible for a particular horizon only when all of the following are true:

1. Its observation date is within the permitted training period.
2. Its observation date is no later than the training cutoff `C`.
3. Its target maturity date for that horizon is present and no later than `C`.

Formally:

$$
\\text{Eligible}(t,h,C) =
(t \\in P) \\land (t \\leq C) \\land (M(t,h) \\leq C)
$$

where `P` is the permitted observation period and `M(t,h)` is the observed maturity date for horizon `h`. Missing maturity dates are ineligible. Eligibility is evaluated independently for each horizon.

Do not add an arbitrary purging interval to this sequential walk-forward design. The maturity rule prevents training targets whose outcomes extend beyond the training cutoff from being used. Reassess purging or embargo only if a different evaluation design, such as temporal cross-validation folds, is introduced.

Overlapping forward targets can still be statistically dependent. That dependence must be considered in evaluation and statistical inference; it is distinct from using outcomes that were not yet available at the training cutoff.

The final test period must not be used for model fitting, feature selection, preprocessing decisions or hyperparameter selection.""",
    ),
    (
        "10. Training eligibility respects target maturity and the approved temporal validation design.\n11. Existing unit tests continue to pass, and any remaining integration gaps are covered by targeted tests.",
        "10. Training eligibility respects the permitted observation period, the training cutoff and horizon-specific target maturity; missing maturity dates are ineligible.\n11. The recorded unit tests and temporal eligibility audit provide evidence for the implemented components. Full integration with a model-training and preprocessing workflow remains to be verified before modelling.",
    ),
    (
        """## 11. Implementation Status

The feature-generation, target-generation and target-maturity components already exist in the project.

Their individual implementations and associated tests must be reused rather than duplicated.

The integrated pipeline is not declared complete solely because its component functions exist. Integration compliance must be established through focused verification against the acceptance criteria above.

**Current status:** Contract proposed; integrated implementation verification pending.""",
        """## 11. Implementation Status

The following components have been implemented:

- Historical feature generation for the seven contracted features.
- Forward-return and positive-return target generation for horizons of 1, 5 and 10 sessions.
- Horizon-specific target maturity dates based on observed future sessions.
- The integrated feature-target pipeline, which composes the existing functions and preserves input row order and index.
- Horizon-specific training eligibility based on the permitted period, observation date, training cutoff and target maturity.

Focused tests for the integrated feature-target pipeline and temporal eligibility were previously reported as passing. The recorded temporal audit also checked eligibility at the observed Validation cutoffs and verified target maturity and exclusion of observations dated after each cutoff. These are recorded results, not a claim that the tests were rerun during this documentation update.

The following remain outside the verification completed by these components:

- Integration of eligibility into an actual model-training loop.
- Fit-time isolation for imputation, scaling, feature selection and other learned preprocessing.
- End-to-end verification of every feature against the exact information available at the prediction timestamp.
- Final evaluation workflow and forecast-scoring controls.

These remaining items must be addressed before model training is authorised. They do not invalidate the implemented feature-target integration or require repeating its already recorded tests solely to update this contract.

**Current status:** Integrated feature-target pipeline implemented; focused integration tests and the recorded temporal eligibility audit passed. Modelling-workflow integration and end-to-end leakage controls remain pending.""",
    ),
]

for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"Stopped without changing the file: expected one occurrence, found {count}."
        )
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print(f"Updated documentation only: {path}")
print("No tests or audits were run.")