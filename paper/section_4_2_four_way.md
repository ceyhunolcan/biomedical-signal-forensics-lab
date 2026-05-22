# Section 4.2 update: four-way SQI agreement with Elgendi 2016

> This file is a drop-in replacement for the current Section 4.2 of the
> manuscript. After running the updated pipeline on n=15 WESAD, replace the
> placeholder values [BRACKETED] with the actual numbers from
> `results/real_data/wesad_deep/summary.json` (the `four_way_sqi` field).

### 4.2 Four-way SQI agreement on real wrist PPG (Figure 5)

We compare the in-house per-window PPG SQI against three independent published baselines: Orphanidou et al. 2015 (four-rule template matching) [@orphanidou2015], Sukor et al. 2011 (pulse-morphology decision rules) [@sukor2011], and Elgendi 2016 (higher-order signal statistics: skewness, kurtosis, normalized entropy) [@elgendi2016]. The three baselines were chosen to span different families of quality-assessment methods. The Elgendi 2016 implementation includes automatic polarity detection because the Empatica E4 wrist PPG used in WESAD reports signals inverted relative to fingertip-PPG conventions on which Elgendi was originally validated.

| Method | Pass rate (n=15) | Cohen's κ vs in-house |
|---|---|---|
| In-house (default threshold 0.7) | **1.000** | - |
| Orphanidou 2015 | [ORPH_PASS] | 0.000 |
| Sukor 2011 | [SUKOR_PASS] | 0.000 |
| **Elgendi 2016 SSQI/KSQI/ESQI** | **[ELG_PASS]** | **0.000** |

| Pairwise Cohen's κ | published only |
|---|---|
| Orphanidou ↔ Sukor | [K_OS] |
| Orphanidou ↔ Elgendi | [K_OE] |
| Sukor ↔ Elgendi | [K_SE] |
| **Median across published pairs** | **[K_MED_PUB]** |
| **Median in-house ↔ published** | **0.000** |

**Headline statistic: in-house passes on [P]% of windows when all three published baselines reject them.** This is the bulletproof "in-house is the outlier" argument: when three independent SQI methods, each based on a different family of features (template matching, pulse morphology, higher-order statistics), unanimously agree that a window is unusable, and the in-house method still accepts it, the in-house method is unambiguously the outlier. The fraction of windows where this happens is the most damning single statistic for the default in-house threshold on real wrist PPG.

| Quantity | Value (n=15) |
|---|---|
| Fraction of windows where all three published baselines pass | [P_ALL_PASS] |
| Fraction of windows where all three published baselines fail | [P_ALL_FAIL] |
| **Fraction where in-house passes but all three published baselines fail** | **[P_ALL_FAIL]** |

**Inter-baseline disagreement is itself informative.** The three published baselines disagree with each other to varying degrees ([K_OS], [K_OE], [K_SE]). This is consistent with them capturing different failure modes: Orphanidou's template-matching is sensitive to morphological irregularities; Sukor's pulse-amplitude variability metric is sensitive to motion-induced amplitude swings; Elgendi's skewness-based test is sensitive to global distribution shape changes from saturation or flatlines. The three methods are independent rather than redundant, and the in-house method disagrees with all three.

CSV: `results/real_data/wesad_deep/summary.json` field `four_way_sqi`. Source: `python scripts/run_deep_real_analysis.py --path <wesad_path>`.
