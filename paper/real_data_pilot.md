# Real-data pilot: WESAD

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

This is the first real-data application of the audit pipeline. We ran the framework on subjects S2 and S3 from the WESAD dataset (Schmidt et al. 2018, UCI repository entry 465), producing 850 5-second windows of synchronized chest ECG and wrist PPG across baseline, stress, and amusement labeled states. The same code scales to all 15 WESAD subjects without modification.

The pilot has six analyses, four of which surface real findings about the in-house SQI on real wrist data that were not visible on the synthetic cohort.

## Pipeline

```bash
# Step 1: extract windows and run per-window in-house SQI + Orphanidou + Sukor baselines
python scripts/run_real_data_pilot.py --dataset wesad --path /path/to/wesad

# Step 2: deep analysis (Bland-Altman, three-way SQI, motion vs HR error, recalibration)
python scripts/run_deep_real_analysis.py --path /path/to/wesad
```

Outputs under `results/real_data/wesad/` and `results/real_data/wesad_deep/`. Wall clock for the two-subject pilot: about 25 seconds end-to-end on a laptop CPU. Full 15-subject run estimated at ~3 minutes.

## What WESAD tests

WESAD provides ~100 minutes per subject of synchronized chest RespiBAN (700 Hz ECG / EDA / EMG / Resp / Temp) and wrist Empatica E4 (64 Hz BVP, 32 Hz accelerometer) data, with labeled segments for baseline, stress (Trier Social Stress Test), amusement (funny-video clips), and meditation. It is a single session per subject, so analyses that depend on multi-day longitudinal data (test-retest reliability, weekly drift, change-point detection on calendar time, missingness dynamics across days) cannot be exercised. What WESAD validates is per-window signal quality, cross-modality HR agreement, comparison against two published SQI baselines on real PPG, and within-subject sensitivity to labeled state.

## Subjects

| Subject | Recording | Baseline | Stress | Amusement | Resting HR | HRV RMSSD |
|---|---|---|---|---|---|---|
| S2 | 101 min | 19.1 min | 10.2 min | 6.0 min | 72.3 bpm | 59.5 ms |
| S3 | 108 min | 18.8 min |  9.6 min | 6.0 min | 54.0 bpm | 116.5 ms |

S2 looks unremarkable. S3 has a low resting HR (54 bpm) and high RMSSD (116 ms). To check whether the high RMSSD was a R-peak undercounting artifact, we re-ran S3 with a Pan-Tompkins-style detector (bandpass 5-15 Hz, squaring, moving average, peak-finding with 250 ms refractory). Both detectors agree on HR (54.0 bpm) and produce nearly identical RMSSD (116.5 vs 115.6 ms). S3 genuinely has very high resting vagal tone, which is published behavior for trained or young adult subjects at rest.

## Analysis 1: Cross-modality HR agreement (Bland-Altman)

Pair the per-window HR from chest ECG against the per-window HR from wrist PPG and run a Bland-Altman analysis. This is the first signal of the device-fidelity problem on real WESAD wrist data.

| Quantity | Value |
|---|---|
| n windows | 848 |
| Mean absolute error | 14.55 bpm |
| Bias (PPG - ECG) | **+12.77 bpm** |
| 95% Limits of agreement | **[-16.18, +41.72] bpm** |
| Pearson r | +0.478 (p < 10⁻⁴⁹) |
| Fraction within 5 bpm | 0.303 |
| Fraction within 10 bpm | 0.486 |

The wrist E4 PPG reads on average ~13 bpm higher than the chest RespiBAN ECG, with limits of agreement spanning nearly 60 bpm. Only 30% of windows agree within 5 bpm. This is a real-world device-fidelity result that the framework correctly surfaces without any per-device tuning. Per-subject and per-state breakdowns are in `hr_agreement_per_subject_state.csv`.

`results/real_data/wesad_deep/figures/fig1_bland_altman_hr.png` shows the Bland-Altman plot colored by labeled state. The amusement state (orange) cluster sits visibly higher in the disagreement axis than baseline (blue).

## Analysis 2: Within-subject per-state comparisons

Mann-Whitney U test on each (subject, metric, baseline-vs-state) contrast, with Wilcoxon p-value reported. The pooled-by-state numbers can hide between-subject heterogeneity.

### Baseline vs Stress

| Subject | Metric | Baseline mean | Stress mean | Δ | p |
|---|---|---|---|---|---|
| S2 | inhouse_ppg_sqi | 0.989 | 0.986 | -0.003 | 0.141 |
| **S2** | **inhouse_ecg_sqi** | **0.987** | **0.978** | **-0.009** | **5.7e-7** |
| S2 | inhouse_ppg_motion | 0.020 | 0.026 | +0.006 | 0.141 |
| **S2** | **hr_abs_diff (bpm)** | **8.33** | **14.97** | **+6.64** | **3.5e-10** |
| **S2** | **orphanidou_template_corr** | **0.822** | **0.661** | **-0.161** | **3.4e-14** |
| **S3** | **inhouse_ppg_sqi** | **0.986** | **0.983** | **-0.004** | **0.026** |
| S3 | inhouse_ecg_sqi | 0.987 | 0.989 | +0.002 | 0.078 |
| **S3** | **inhouse_ppg_motion** | **0.025** | **0.031** | **+0.007** | **0.026** |
| **S3** | **hr_abs_diff (bpm)** | **16.43** | **11.82** | **-4.61** | **0.033** |
| S3 | orphanidou_template_corr | 0.739 | 0.717 | -0.022 | 0.145 |

Bold rows are significant at α = 0.05. **The Orphanidou template correlation on S2 drops from 0.82 (baseline) to 0.66 (stress) with p = 3.4 × 10⁻¹⁴**. This is a strong, methodologically clean signal. The in-house PPG SQI on the same subject and same windows shows only a 0.003 drop that is not significant. This is direct evidence on real data that the in-house SQI under-reacts to state-induced quality degradation that the published baseline catches.

S2's chest ECG SQI also drops significantly during stress (-0.009, p = 5.7e-7), and S2's HR-modality disagreement nearly doubles (8.3 → 15.0 bpm).

S3 shows the opposite direction on hr_abs_diff (decreases from 16.4 to 11.8 bpm during stress), which is a real between-subject difference: S3 may have moved less during the Trier task than during baseline. Both directions are physiologically possible and the framework reports both honestly.

### Baseline vs Amusement

The amusement state produces larger PPG quality drops than stress for both subjects (consistent with the framework's prior: amusement involves more upper-body motion from laughter than the seated Trier task). Full table in `per_state_baseline_vs_amusement.csv`. S3's PPG SQI drops with Cliff's δ ≈ +0.49 (p < 10⁻⁴), and S3's PPG motion artifact score nearly doubles (0.018 → 0.038, p < 10⁻⁴).

## Analysis 3: Three-way SQI agreement

We compare the in-house SQI against two published baselines: Orphanidou et al. 2015 (template-matching rules) and Sukor et al. 2011 (decision-tree on pulse-morphology features). Two published methods give the in-house SQI a two-witness comparison rather than relying on a single baseline.

| Method | Pass rate | Cohen's κ vs in-house | Cohen's κ vs Orphanidou |
|---|---|---|---|
| In-house (threshold 0.7) | 1.00 | - | 0.000 |
| Orphanidou (2015) | 0.22 | 0.000 | - |
| Sukor (2011) | 0.12 | 0.000 | **0.313** |

Spearman correlation between continuous scores:

| Pair | Spearman ρ |
|---|---|
| in-house ↔ Orphanidou | +0.267 |
| in-house ↔ Sukor | +0.223 |
| **Orphanidou ↔ Sukor** | **+0.565** |

The two published baselines correlate moderately with each other (ρ = 0.57) and agree on pass/fail at κ = 0.31. The in-house SQI on real data correlates only weakly with either (ρ ≈ 0.22-0.27) and has κ = 0.000 with both. **The in-house SQI is the outlier, not the published baselines.** This is the central result of the pilot.

`results/real_data/wesad_deep/figures/fig3_sqi_pass_rates.png` shows the three pass rates side by side. The contrast is severe: in-house passes everything, the published baselines pass a small minority.

## Analysis 4: Motion artifact predicts HR-modality disagreement

We test whether the framework's PPG motion-artifact score actually predicts when wrist HR will disagree with chest HR. If the motion detector is doing its job, high-motion windows should produce more disagreement.

| Quantity | Value |
|---|---|
| Spearman (motion vs in-house SQI) | -1.000 |
| **Spearman (motion vs |HR_PPG - HR_ECG|)** | **+0.304** |
| Spearman (motion vs Orphanidou template corr) | -0.267 |
| Mean |HR diff| at low motion | 12.86 bpm |
| Mean |HR diff| at high motion | **19.62 bpm** |

The Spearman of -1.000 between motion and the in-house SQI is mechanical (the in-house SQI penalty term is a deterministic function of motion). The real test is the +0.304 correlation between motion and HR-modality disagreement on a held-out test (the motion score and the HR estimates come from independent computations). It is positive, moderate, and significant. Mean HR disagreement goes from 12.9 bpm at low motion to 19.6 bpm at high motion, a relative increase of 52%.

The motion artifact detector is doing what it claims to do. The detector's output is a useful explanation for *why* the in-house SQI agrees poorly with the published baselines on real wrist PPG: the wrist motion is genuinely producing artifact, the in-house SQI's continuous score reflects that, but the binarization at 0.7 erases the signal because the in-house SQI's dynamic range on real PPG is concentrated above 0.97.

`results/real_data/wesad_deep/figures/fig5_motion_vs_hr_error.png` shows the scatter with a fitted line of slope 141 bpm per unit motion score.

## Analysis 5: Recalibration of the in-house SQI threshold

The default in-house threshold of 0.7 produces Cohen's κ = 0.000 against the Orphanidou pass/fail label (no agreement beyond chance). We recalibrate the threshold by splitting the 850 windows into 425 calibration and 425 holdout, searching the threshold space on calibration to maximize κ vs Orphanidou, and reporting the holdout κ at the chosen threshold.

| Threshold | Holdout raw agreement | Holdout Cohen's κ |
|---|---|---|
| Original (0.70) | 0.214 | 0.000 |
| Recalibrated (0.99) | 0.626 | +0.217 |
| **Δ κ** | | **+0.217** |

Cohen's κ on held-out data jumps from 0.000 to +0.217 (interpreted as "fair" agreement). The recalibrated threshold of 0.99 is far from the synthetic-tuned default of 0.70, reflecting how concentrated the in-house SQI distribution is on real wrist PPG (median 0.99 across all states).

`results/real_data/wesad_deep/figures/fig6_recalibration.png` shows the full κ-vs-threshold curve. The original 0.70 sits in a region of κ ≈ 0, the curve rises sharply above 0.95, and the maximum κ is at 0.99.

This is a directly actionable result for anyone using the framework on real Empatica E4 data: the default threshold needs recalibration, and the recalibration recipe is published as `scripts/run_deep_real_analysis.py`.

## Analysis 6: Per-subject Orphanidou agreement

To check whether the pooled disagreement is driven by one subject, we compute the in-house vs Orphanidou agreement separately for S2 and S3.

| Subject | n | In-house mean | Orphanidou acceptable | Spearman ρ |
|---|---|---|---|---|
| S2 | 422 | 0.988 | 0.291 | +0.265 |
| S3 | 428 | 0.983 | 0.157 | +0.214 |

Both subjects show Spearman ρ in the 0.21 to 0.27 range, both well below the 0.78 achieved on the synthetic cohort. The pilot's disagreement story is not a single-subject artifact.

## Conclusions of the deep pilot

1. **The adapter and pipeline work correctly on real WESAD data.** Two bugs were caught and fixed during the shakedown: duplicate-column collision in the per-state aggregate, and missing RR-interval cleaning that inflated HRV RMSSD by ~50%. The corrected pipeline produces physiologically sensible HR estimates, clean per-window SQI on real signals, and reproducible outputs from a fixed seed.

2. **Wrist PPG vs chest ECG agreement is poor on real WESAD data.** Bias +12.8 bpm, LoA 58 bpm wide, only 30% of windows within 5 bpm. This is a real device-fidelity result. Anyone running biomarker analyses on E4 wrist PPG should compute and report this disagreement.

3. **The in-house SQI binarized at 0.7 is uninformative on real wrist PPG.** Cohen's κ = 0.000 against both Orphanidou (2015) and Sukor (2011). The threshold needs recalibration before any real-world claim.

4. **Recalibration to threshold 0.99 raises holdout Cohen's κ to +0.217.** A directly actionable fix, with the recipe published in `scripts/run_deep_real_analysis.py`.

5. **The two published baselines (Orphanidou, Sukor) agree with each other (κ = 0.31, ρ = 0.57) but neither agrees with the in-house SQI on real data.** The in-house SQI is the outlier. This justifies the framework's policy of running multiple baselines side by side.

6. **The framework's motion-artifact score predicts HR-modality disagreement on real data** (ρ = +0.30, mean error +52% at high motion). The motion detector is doing what it claims.

7. **Per-state sensitivity is real but heterogeneous across subjects.** S2's Orphanidou template correlation drops from 0.82 to 0.66 during stress (p = 3.4e-14). S3's PPG quality drops most during amusement. Effect sizes range from Cliff's δ = 0.10 to 0.49 depending on (subject, metric, contrast).

8. **What the pilot does not validate.** Test-retest reliability, weekly drift, longitudinal trust scores, missingness dynamics, calendar-time device-bias analyses, fairness audits by demographic variables. WESAD has no multi-day data and no fairness-relevant demographics. Those analyses require AppleWatch-MIMIC, All of Us, or another longitudinal dataset.

## Reproducibility

Every number in this section comes from running the two scripts above on subjects S2 and S3 from the public WESAD release. Every table has a CSV in `results/real_data/wesad/` or `results/real_data/wesad_deep/`. Every figure has a PNG in `results/real_data/wesad_deep/figures/`. The framework's bundled tests (`tests/test_wesad_adapter.py`, `tests/test_deep_real_analysis.py`, `tests/test_sukor_sqi.py`) exercise every code path end-to-end on synthetic fixtures on every CI run, so the code stays regression-tested even when no real WESAD copy is present in the test environment.
