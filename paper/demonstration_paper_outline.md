# Demonstration paper: outline and execution plan

## Working title

"Wearable signal-quality methods disagree at scale: an audit of public benchmark data with implications for digital-health AI"

## One-sentence pitch

Three independent published wearable-PPG signal-quality methods collectively reject 44.6 percent of windows that a typical synthetic-tuned in-house pipeline passes; this paper quantifies how often that disagreement affects the headline conclusions of recent wearable-AI publications.

## Why this paper is high-impact

The WESAD 44.6 percent finding is empirically interesting on its own. The demonstration paper extrapolates from that finding to ask whether published wearable-AI work in top venues holds up under the audit. That framing converts a methods toolkit into an investigative empirical contribution, which is the form that gets cited in top-tier digital-health journals.

## Target venues

Primary: Nature Digital Medicine, Lancet Digital Health, npj Digital Medicine. All three publish empirical methodology pieces with broad clinical implications. Secondary fall-back: PLOS Digital Health, IEEE J-BHI.

## Hypothesis structure

**Primary:** Wearable-AI publications using wrist PPG without explicit multi-baseline signal-quality auditing report effect sizes that are sensitive to the choice of signal-quality threshold; specifically, applying a three-baseline consensus filter materially changes headline findings in at least 25 percent of audited studies.

**Secondary:** The direction of change is non-random; studies reporting positive findings on noisy populations (e.g., stress detection, AFib screening on consumer Fitbit data) attenuate more than studies reporting findings on tightly controlled lab populations.

## Method (high level)

### Paper-selection criteria

1. Published in Nature Digital Medicine, Lancet Digital Health, npj Digital Medicine, or comparable venue, 2020-2025
2. Uses wrist PPG as primary signal modality
3. Reports a downstream classification or regression outcome
4. Has either (a) publicly available data sufficient for replication, or (b) sufficient pipeline detail in the paper or supplement to allow faithful re-implementation on a comparable public dataset
5. Reports a headline finding with a quantifiable effect size

Target list size: 8 to 12 papers.

### Audit protocol (per paper)

1. Replicate the paper's preprocessing pipeline as documented
2. Apply the four-way SQI audit (in-house, Orphanidou, Sukor, Elgendi) at the window level
3. Quantify the rejection-rate disagreement on the same data the paper used (or a publicly available analog)
4. Recompute the paper's headline finding three ways: (i) with the paper's own quality filter, (ii) with each published baseline as the filter, (iii) with the three-baseline consensus filter
5. Report effect-size deltas across the four filter conditions
6. Categorise the headline finding as: stable, weakened (less than 50 percent of original effect), reversed (sign-flipped), or unrecoverable (data insufficient)

### Statistical methods

- Effect-size comparison across filter conditions using bootstrap confidence intervals on the per-paper deltas
- Cross-paper meta-summary: proportion of papers in each categorisation, with binomial confidence intervals
- Sensitivity analysis: varying the three-baseline consensus threshold from majority (at least 2 of 3 baselines agree) to unanimous (all 3 agree)
- Pre-registration on OSF prior to running the audit, to lock in the paper selection and the audit protocol

### What this paper does not claim

It does not claim that any individual published paper is wrong. It claims that the field of wearable-AI lacks a standardised signal-quality reporting practice and that the resulting variance is large enough to materially affect cross-study synthesis.

## Structure (target ~4,000 words)

### 1. Introduction (500-800 words)

- The promise of wearable-derived digital biomarkers (citations to top recent papers)
- The implicit signal-quality assumption underlying nearly all downstream work
- WESAD as reference benchmark: three published baselines collectively reject 44.6 percent of windows that a synthetic-tuned in-house pipeline passes; pairwise Cohen's kappa across the three published baselines is -0.20
- Research question: do published wearable-AI papers' conclusions hold under multi-baseline signal-quality audit?

### 2. Methods (1000-1500 words)

- Paper-selection criteria (see above)
- Audit protocol (see above)
- Statistical methods (see above)
- Pre-registration link (OSF)
- Software availability: biomedical-signal-forensics-lab v1.0+

### 3. Results (1000-1500 words)

- Audit outcomes summary table (one row per audited paper): n_windows, rejection_rate_in_house, rejection_rate_orphanidou, rejection_rate_sukor, rejection_rate_elgendi, rejection_rate_consensus, headline_finding_original, headline_finding_audited, delta_effect_size, categorisation
- Cross-paper synthesis figure: forest plot of effect-size deltas with 95 percent bootstrap CIs
- Categorisation summary: percent stable / weakened / reversed / unrecoverable
- Sensitivity analysis: variation across consensus-threshold choices

### 4. Discussion (800-1200 words)

- Implications for wearable-AI research practice
- Specific recommendations for journal reporting standards (multi-baseline SQI as supplementary material; quality-threshold sensitivity analyses as standard practice)
- Limitations: full original data is not available for all audited papers, so replication faithfulness varies; the three published baselines themselves may not be the right ground truth in all contexts; the audit is not a substitute for prospective clinical validation
- Future direction: a public benchmark page maintained alongside the toolkit, tracking signal-quality method disagreement across an expanding paper list

### 5. Conclusion (200 words)

We recommend that wearable-AI publications using PPG report a multi-baseline signal-quality audit as standard supplementary material. Variance in current published findings under such audit is large enough to warrant routine sensitivity reporting.

## Initial paper-list candidates (to refine during selection)

Brainstorm pool, not committed targets:

- Apple Heart Study (Turakhia et al., 2019, NEJM): large-scale Apple Watch PPG for AFib detection
- Fitbit Heart Study (Lubitz et al., 2022): similar scope on Fitbit
- COVID-19 detection from wearables (Mishra et al., 2020 Nature Biomedical Engineering; Quer et al., 2021 Nature Medicine)
- Stress detection from wrist PPG (recent WESAD-derived papers)
- Sleep-stage classification from consumer wearables
- Continuous blood-pressure estimation from PPG
- Recent npj Digital Medicine wearable-AI papers (2024-2025)

Selection should aim for a mix of clinical-stakes high (AFib, BP) and behavioural-outcome (stress, sleep) papers to test the secondary hypothesis.

## Execution timeline

| Stage | Duration | Deliverable |
|---|---|---|
| 1. Paper list selection and screening | 1 week | shortlist of 8-12 papers |
| 2. OSF pre-registration | 2-3 days | pre-registered audit protocol |
| 3. Pipeline replication per paper | 2-4 weeks | reproducible audit harness for each paper |
| 4. Run audit and statistical analysis | 1 week | results tables and figures |
| 5. First draft | 2 weeks | full manuscript |
| 6. Internal review (mentor, clinical co-author if recruited) | 1 week | revised manuscript |
| 7. Submission | 1 day | submitted to target journal |

Total: roughly 8-10 weeks from start of execution to submission. Critical path is pipeline replication, which can shortcut significantly if (a) the audited papers have well-documented pipelines, (b) the audited papers release per-window data.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Audited papers do not release per-window data | Use the documented pipeline on a public analog dataset (WESAD, AppleWatch-MIMIC). Be explicit in methods that the audit is on a representative analog, not on the original paper's data. |
| Audit reveals no signal (all findings stable) | This is also publishable: "wearable AI is more robust to signal-quality variation than expected." Frame the paper around the empirical finding rather than the controversy. |
| Audited authors object pre-publication | Pre-publication transparency: share the audit results with each paper's senior author before submission. Some may collaborate; some may push back; both are useful for the discussion section. |
| Reviewers reject as "criticism without remedy" | The remedy is the open-source toolkit and the recommendation for routine multi-baseline reporting. Lead the discussion with the constructive frame, not the critical one. |
| Clinical co-author recruitment fails | The paper can stand on the methodology alone, but a clinical co-author adds substantial credibility. Reach out to Geisel digital-health faculty early. |

## Dependencies on this repository

- biomedical-signal-forensics-lab v1.0+ with the four-way SQI audit
- AppleWatch-MIMIC adapter or other multi-cohort validation dataset (item 7 in the broader work plan)
- Published JOSS paper for software citation
- Published medRxiv pre-print or accepted npj DM manuscript for the methodology paper that this work builds on

## How to start

Tomorrow's task: assemble the candidate paper list. Spend 90 minutes searching Nature Digital Medicine, Lancet Digital Health, and npj Digital Medicine archives for wearable-PPG papers from 2022-2025. Record title, DOI, headline finding, and data-availability status in a CSV at `paper/demonstration_paper_candidates.csv`. Do not start the audit work until the list is complete and the OSF pre-registration is filed.
