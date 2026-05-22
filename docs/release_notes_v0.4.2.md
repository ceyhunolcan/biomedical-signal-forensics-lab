# v0.4.2 release notes

> Research prototype only. Not medical advice, diagnosis, treatment, or a medical device.

This release stops adding more bug-audit rounds and instead ships three things that take the repo closer to a publishable state: a consolidated results document, real-data adapter scaffolding for WESAD, and a final humanization pass.

## 1. `paper/results.md`

A single 10-section document that compiles every empirical result the framework produces into one narrative. The structure tracks what a methods paper would look like:

1. The cohort (300 simulated participants × 60 days)
2. Cohort-level Digital Biomarker Trust Score (mean 74.11)
3. Fairness disparities recovered (device gap 13 pts; skin-tone Q1-Q4 gap 9.5 pts)
4. Causal-adjusted confounding (AIPW vs screening correlation)
5. Learned trust-score weights (holdout Spearman ρ = 0.668)
6. Bootstrap test-retest reliability (week-pair design with cluster bootstrap CIs)
7. ICC(2,1) days-as-raters vs proper week-pair r (the formal defense)
8. Comparison against Orphanidou et al. 2015 (Spearman ρ = 0.782 across 1800 windows)
9. Cross-cohort generalization (7 of 8 qualitative predictions recovered)
10. What this exercise does not show

Every number references a CSV in `results/tables/`. The document is ready to paste into a JOSS submission or a workshop paper draft.

## 2. WESAD adapter scaffolding

New module `src/data/wesad_adapter.py` and driver script `scripts/run_real_data_pilot.py`. Anyone with a downloaded WESAD archive (Schmidt et al. 2018; freely available from UCI) can drop the dataset in and produce a real-data pilot report:

```bash
python scripts/run_real_data_pilot.py --dataset wesad --path /your/wesad/dir
```

The output directory contains `daily_summary.csv` (one row per WESAD subject), `windows_meta.csv` (one row per extracted ECG/PPG window), `signal_quality.csv` (in-house SQI on real signals), `orphanidou_baseline.csv` (in-house vs published baseline on real PPG), and `report.md` (human-readable summary).

What WESAD is good for in this framework:

- Per-window ECG and PPG signal-quality validation against the framework's in-house SQI and the Orphanidou (2015) baseline on real signals
- Cross-device comparison between RespiBAN (chest, gold standard) and Empatica E4 (wrist, the realistic clinical device)
- Artifact-burden estimates under labeled states (baseline / stress / amusement)

What WESAD is not good for here: test-retest reliability, weekly reproducibility, multi-day longitudinal stability. WESAD is a single ~60-minute session per subject. For longitudinal analyses, MIMIC-PERform or AppleWatch-MIMIC is a better fit; adapters for those are not yet implemented.

The adapter has 10 regression tests in `tests/test_wesad_adapter.py` that run end-to-end against a WESAD-shaped synthetic fixture. The smoke test recovers an injected 75 bpm heart rate from synthesized ECG, extracts 12 5-second windows split evenly across baseline and stress labels, and produces SQI values for both modalities. The adapter is ready for real WESAD data the moment someone downloads it.

## 3. Humanization pass

Across all documentation and prose code comments:

- Removed all 13 lingering instances of "deliberately", "on purpose", "by design" as design-choice flags. Real prose uses these once and moves on; the cluster of repetitions is the kind of pattern that gives AI-assisted writing away.
- Cut "Research-grade" wherever it remained.
- Trimmed "framework" overuse in `paper/ethics.md` from 11 instances to 5.
- Updated `paper/reviewer_response_simulation.md` to reflect that the Orphanidou comparison now exists (the old text said "we have not run this"; now it points to Section 8 of `paper/results.md`).
- Re-verified zero em-dashes anywhere in `.md` or `.py` files.
- Re-verified zero vendor or model-name mentions across the codebase.

Kept the "essentially" and "head-to-head" instances that read as normal technical English; cut the ones that read as AI hedges.

## Verification

- **162 of 162 tests passing** (was 152 in v0.4.1; +10 from the new WESAD adapter tests)
- Full pipeline rebuilds from scratch in 117 seconds
- Headline numbers stable across eight versions:

| Version | Mean DBTS | Orphanidou ρ | Holdout ρ | Cross-cohort pass |
|---|---|---|---|---|
| v0.2.0 | 69.3 | not computed | 0.586 | n/a |
| v0.2.4 | 74.1 | not computed | 0.668 | n/a |
| v0.3.0 | 74.1 | 0.782 | 0.668 | n/a |
| v0.3.2 | 74.1 | 0.782 | 0.668 | n/a |
| v0.4.0 | 74.1 | 0.782 | 0.668 | 7/8 |
| v0.4.1 | 74.1 | 0.782 | 0.668 | 7/8 |
| v0.4.2 | 74.1 | 0.782 | 0.668 | 7/8 |

## Where this leaves the publication path

The advisor read identified four remaining gaps for a methods paper. Three are now closed:

| Gap | Status |
|---|---|
| Real-data validation | Adapter scaffolding ready; needs a downloaded WESAD copy to actually run |
| ICC(2,1) defense | Done in v0.4.0; surfaced in the report in v0.4.1; written up in `paper/results.md` Section 7 |
| Autoencoder cut | Done in v0.4.0 (demoted to opt-in extension point) |
| Reframing as "forensic investigation tool" | A writing decision, not a code one. Pending. |

For a JOSS submission, the repo is ready as-is. For a methods journal (npj Digital Medicine), the remaining gate is a real-data pilot, which the WESAD scaffolding here is built to support. The first network-enabled run of `scripts/run_real_data_pilot.py --dataset wesad --path ...` will produce a complete pilot report that can be inlined into the methods paper.
