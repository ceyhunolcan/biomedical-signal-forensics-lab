# Preprint Outline

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

Working outline of the paper this framework would support. Section lengths are notional and assume an arXiv preprint at roughly 12 pages plus appendix. The intent is to make the structure explicit so future contributors know what each repository module is supposed to feed.

## Title

Biomedical Signal Forensics: A Reliability Framework for Wearable-Derived Digital Biomarkers

## Authors and affiliations

(To be filled.)

## Abstract (~250 words)

See `paper/abstract.md`.

## 1. Introduction (~1.5 pages)

- Why digital biomarkers fail when signal quality is ignored. Concrete examples from the literature where a downstream finding was traced back to a pipeline artifact.
- The gap: most signal-quality work focuses on a single component (waveform SQI, missingness, device bias) in isolation.
- Our contribution: a six-component decomposition operationalized as an auditable trust score, with a reproducible synthetic cohort for testing.
- Out of scope: clinical claims, deployment, validation on a specific device.

## 2. Related work (~1 page)

- Waveform-level signal-quality literature for ECG and PPG (template matching, learned classifiers).
- Missingness-as-signal literature in longitudinal wearable studies.
- Device-bias studies comparing consumer wearables against reference standards.
- ICC and test-retest methodology in digital-biomarker validation.
- Why we report all of these together rather than a single number.

## 3. Framework (~2 pages)

Material from `paper/signal_quality_framework.md`. The six-component decomposition, how each component is computed, how they are weighted, how to interpret category thresholds. Figure 1: framework diagram.

## 4. Synthetic cohort (~1 page)

Material from `paper/data_card.md` and `paper/methods.md`. Generative model, parameter choices, what is included (state-dependent missingness, environmental confounding, device bias, skin-tone-coupled signal degradation) and what is left out (arrhythmia, sleep staging, firmware drift). Figure 2: example daily trace per device family.

## 5. Audit pipeline (~1.5 pages)

The end-to-end flow: generation → preprocessing → artifact detection → reliability metrics → trust score → report. The four scripts and what each produces. Figure 3: sample audit-report excerpt. Figure 4: trust-score radar for two contrasting participants.

## 6. Baseline models (~1.5 pages)

The five bundled models, their feature sets, training procedure, leaderboard. Table 1: model leaderboard. The framing is "these are scaffolding, not the contribution" (see model card).

## 7. Robustness and ablation (~1 page)

- Sensitivity of trust-score components to weight changes.
- Sensitivity of artifact detectors to threshold changes.
- Performance drop when synthetic generator confounders are turned off (does the framework still detect what little signal remains?).
- Stratified trust scores by simulated device family.

## 8. Discussion (~1 page)

- What the framework can and cannot tell you.
- How to interpret a trust-score category in practice.
- When to escalate from screening (this framework) to formal causal analysis (downstream tooling).
- Implications for digital-biomarker reproducibility.

## 9. Limitations (~0.5 page)

Material from `paper/limitations.md`. Synthetic-only validation, hand-tuned thresholds, simple waveform model, no firmware drift, no formal causal inference.

## 10. Ethics (~0.5 page)

Material from `paper/ethics.md`. Non-clinical framing, synthetic-data policy, fairness implications of the skin-tone proxy, recommendations to downstream users.

## 11. Conclusion (~0.5 page)

Recap, future work (real-data validation, change-point detection for firmware drift, learned weighting tied to specific downstream outcomes, automated fairness-stratified audit).

## Appendix A: detector specifications

Material from `docs/artifact_examples.md`.

## Appendix B: trust-score formulas

The mathematical form of each component score and the aggregation.

## Appendix C: reproducibility checklist

- Seeds: documented in `configs/default.yaml`.
- Software versions: pinned in `requirements.txt`.
- Hardware: CPU-only.
- Run time: end-to-end on a 2024 laptop in under 5 minutes.
- All figures: produced by `scripts/generate_report.py`. No hand-editing.

## Appendix D: reviewer response simulation

Material from `paper/reviewer_response_simulation.md`. The pre-emptive responses to objections we expect.

## Figures and tables

Required figures (all produced by the pipeline):

1. Framework diagram.
2. Example daily trace per device family.
3. Sample audit-report excerpt.
4. Trust-score radar comparison.
5. Reliability heatmap.
6. Confounding scatter (heat → HRV).
7. Trust-score distribution histogram.

Required tables:

1. Model leaderboard.
2. Per-component trust-score statistics for the synthetic cohort.
3. Stratified trust scores by device family.
4. Stratified trust scores by skin-tone-proxy quartile.

## Notes for future authors

- Resist the temptation to add real-data results to this paper. The point is the framework. A real-data validation belongs in a companion paper.
- Resist the temptation to add a deep-learning waveform model. The autoencoder is scaffolding; a real waveform model needs a different paper and different data.
- Keep the synthetic generator simple. Every additional knob in the generator is a knob that needs to be defended in review.
