# Reviewer Response Simulation

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

A pre-emptive responses-to-reviewers document. We list the objections we expect a careful reviewer to raise and our response. Each response is what we would say in a revision letter, including the cases where the right answer is "you are correct, we have updated the manuscript."

## R1: "Validation is entirely synthetic. How can we trust any of these numbers?"

You should not trust any of these numbers as estimates of real-device performance. We are explicit about this in the abstract, in the limitations section, in the data card, and in the model card. The contribution of this work is not a benchmark result; it is a reproducible framework for performing an audit. The synthetic cohort exists to give the framework something concrete to operate on and to let any reader reproduce every figure without needing access to a specific dataset.

A natural next step is to validate the framework on a real wearable dataset with known device families and known annotation. We have flagged this as future work.

## R2: "Why not use established signal-quality indices from the literature instead of inventing your own?"

Our PPG and ECG signal-quality estimators are simple. They are not contributions of the paper. The contribution is the six-component trust score and the audit pipeline around it. We chose simple SQI estimators because we did not want the framework to depend on a specific SQI implementation; any reader can replace `src/signals/signal_quality.py` with a more sophisticated estimator and the rest of the pipeline will still run.

In a revision we will (a) add a paragraph in the methods explicitly framing the SQI estimators as illustrative, and (b) provide a documented extension point so that drop-in replacement is one config change.

## R3: "The ICC(2,1) application looks wrong."

The reviewer is correct that we are using ICC(2,1) in a non-standard way. We treat each participant's daily measurements as a multi-rater design where the day index plays the rater role. This is a deliberate abuse of the formula, chosen because the resulting number is useful for ranking participants by within-participant variability and because the alternative (true test-retest with two timepoints per participant) is not available for daily data.

In the revision we will (a) rename the function to make the unconventional use explicit, (b) report the result alongside a standard test-retest split-half correlation, and (c) discuss in the methods why we report both.

## R4: "The 'confounding risk' score is just a maximum correlation. That's not confounding analysis."

The reviewer is correct. The score is a screening signal, not a causal-inference result. We use the word "risk" to indicate that the number is a warning, not a conclusion. The framework's recommendation when this score is low is to run a sensitivity analysis adjusting for the suspected covariate, which is causal-inference machinery the user is responsible for performing downstream.

We will rename the component to "confounding screening score" in the next version to make this less confusing, and we will add a worked example in the supplementary that takes the screening output and runs a proper adjusted analysis.

## R5: "What about firmware drift? Real wearables change their algorithms over time."

You are right and we do not handle this. The framework's temporal-stability component will detect a distribution shift over time but will not attribute it to a firmware event. Modeling firmware drift requires either ground-truth release notes from the manufacturer or a change-point detection step we have not implemented.

We have added this to the limitations section. A future version of the framework could include a change-point detector in the reliability module.

## R6: "The skin-tone bias in the synthetic generator is arbitrary."

It is. The 0.12 × proxy penalty was chosen to be large enough to be detectable by the framework's stratified audit and small enough not to dominate other effects. We do not claim this magnitude corresponds to any real device. The point of including the term is to demonstrate that the audit machinery responds correctly to such an effect when it is present in real data. We have re-worded the data card and methods section to make this clearer.

## R7: "The model performance numbers in the leaderboard are uninteresting."

They should be. The leaderboard is included as scaffolding, to demonstrate that the framework's outputs can be used as model targets and to provide a place for future detectors to be benchmarked. We have re-framed the leaderboard table caption in the revision to emphasize this and to remove any implication that the bundled models should be compared against the wearable-quality literature.

## R8: "Why not learn the trust-score weights from data?"

Because there is no held-out label that we trust to learn against. Any learned weighting would inherit the biases of whatever label we used. The fixed weights are a defensible default, and we expose them in `configs/reliability.yaml` so they can be changed and the change reported.

A separate paper could examine learned weightings tied to specific downstream outcomes (e.g., reproducibility of a HRV-based stress prediction). That is out of scope for this work.

## R9: "The dashboard and API feel like over-engineering for a research prototype."

They might be. They are included because the framework is meant to be exercised end-to-end by people who are not the authors, and because the audit report is more useful as an interactive object than as a static PDF. We are open to moving the API and dashboard to a separate companion repository if the reviewers feel they distract from the methodological contribution.

## R10: "How does this compare to existing signal-quality literature?"

The audit pipeline now runs an Orphanidou et al. (2015) template-matching SQI alongside the in-house per-window PPG SQI and reports agreement metrics (Spearman ρ, point-biserial r, full 2x2 crosstab). On the bundled synthetic cohort, Spearman is 0.78 across 1800 windows. See Section 8 of `paper/results.md`, the audit log line `audit | Orphanidou agreement`, and `results/tables/baseline_comparison_orphanidou.csv`. The framework's six-component decomposition is novel in our reading of the literature; the closest prior work focuses on single-component quality scoring (template-matching SQI on ECG, motion-flag classifiers on PPG). Section 7 of `paper/results.md` adds a second method comparison: the unconventional ICC(2,1) days-as-raters vs proper bootstrap week-pair r, with the two methods producing consistent rankings.
