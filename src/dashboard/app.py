"""Streamlit dashboard for the biomedical signal forensics lab.

Pages:
    Overview · Signal Quality · Artifact Detection · Reliability
    Confounding · Missingness · Device Bias · Trust Score · Report · Safety
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.confounding import environmental_confounding, missingness_dynamics
from src.reliability.biomarker_trust_score import DigitalBiomarkerTrustScore
from src.reliability.device_bias import per_column_bias
from src.utils.config import load_yaml
from src.utils.paths import resolve


st.set_page_config(page_title="Signal Forensics Lab", layout="wide")


DISCLAIMER = (
    "Research prototype only. Not medical advice, diagnosis, treatment, "
    "or a medical device."
)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    cfg = load_yaml("configs/default.yaml")
    p = resolve(cfg.paths.synthetic_csv)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


@st.cache_data(show_spinner=False)
def compute_trust_scores(df: pd.DataFrame) -> pd.DataFrame:
    scorer = DigitalBiomarkerTrustScore()
    return scorer.cohort_scores(df)


@st.cache_data(show_spinner=False)
def load_windows() -> tuple[np.ndarray, np.ndarray, int, int] | None:
    cfg = load_yaml("configs/default.yaml")
    p = resolve(cfg.paths.synthetic_windows)
    if not p.exists():
        return None
    arrays = np.load(p)
    return (
        arrays["ecg"], arrays["ppg"],
        int(cfg.cohort.ecg_sample_rate_hz),
        int(cfg.cohort.ppg_sample_rate_hz),
    )


def _safety_banner():
    st.warning(DISCLAIMER)


def page_overview(df: pd.DataFrame, trust: pd.DataFrame) -> None:
    st.title("Biomedical Signal Forensics Lab")
    st.markdown(
        "A research-grade audit layer for wearable physiological signals. "
        "Five forensic dimensions feed a single Digital Biomarker Trust Score."
    )
    _safety_banner()
    if df.empty:
        st.error("No synthetic data found. Run `python scripts/run_pipeline.py` first.")
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Participants", df["participant_id"].nunique())
    c2.metric("Days observed", df["date"].nunique())
    c3.metric("Mean trust score", f"{trust['overall_trust_score'].mean():.1f}")
    c4.metric("Low-trust participants",
              int((trust['overall_trust_score'] < 40).sum()))


def page_signal_quality(df: pd.DataFrame) -> None:
    st.header("Signal quality explorer")
    _safety_banner()
    pid = st.selectbox("Participant", sorted(df["participant_id"].unique()))
    g = df[df["participant_id"] == pid].sort_values("date")
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(g["date"], g["signal_quality_ground_truth"], marker=".", label="quality")
    ax.set_xticks(g["date"].iloc[::7])
    ax.set_xticklabels(g["date"].iloc[::7], rotation=45, ha="right")
    ax.set_ylabel("signal_quality_ground_truth")
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    win = load_windows()
    if win is not None:
        ecg, ppg, ecg_fs, ppg_fs = win
        idx = st.slider("Signal window index", 0, len(ecg) - 1, 0)
        fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 5))
        ax1.plot(np.arange(len(ecg[idx])) / ecg_fs, ecg[idx], linewidth=0.8)
        ax1.set_title("ECG window")
        ax1.set_xlabel("s")
        ax2.plot(np.arange(len(ppg[idx])) / ppg_fs, ppg[idx], linewidth=0.8,
                 color="darkorange")
        ax2.set_title("PPG window")
        ax2.set_xlabel("s")
        fig2.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)


def page_artifacts(df: pd.DataFrame) -> None:
    st.header("Artifact detection")
    _safety_banner()
    high = df[df["artifact_burden_ground_truth"] > 0.5]
    st.write(f"Participant-days flagged as high artifact burden: **{len(high)}** "
             f"({len(high) / len(df) * 100:.1f}%)")
    fig, ax = plt.subplots()
    ax.hist(df["artifact_burden_ground_truth"], bins=30, edgecolor="white")
    ax.set_xlabel("artifact_burden_ground_truth")
    ax.set_ylabel("count")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def page_reliability(df: pd.DataFrame) -> None:
    st.header("Reliability analysis")
    _safety_banner()
    pid = st.selectbox("Participant", sorted(df["participant_id"].unique()),
                       key="rel_pid")
    g = df[df["participant_id"] == pid].sort_values("date")
    fig, ax = plt.subplots()
    ax.plot(g["date"], g["reliability_ground_truth"], marker=".")
    ax.set_ylim(0, 1)
    ax.set_xticks(g["date"].iloc[::7])
    ax.set_xticklabels(g["date"].iloc[::7], rotation=45, ha="right")
    ax.set_ylabel("reliability_ground_truth")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def page_confounding(df: pd.DataFrame) -> None:
    st.header("Environmental confounding")
    _safety_banner()
    corr = environmental_confounding.correlation_table(df)
    st.dataframe(corr)
    if not corr.empty:
        top = corr.iloc[0]
        fig, ax = plt.subplots()
        sample = df.sample(min(2000, len(df)), random_state=0)
        ax.scatter(sample[top["environmental_var"]], sample[top["biomarker"]],
                   s=4, alpha=0.3)
        ax.set_xlabel(top["environmental_var"])
        ax.set_ylabel(top["biomarker"])
        ax.set_title(f"Top pair · r = {top['pearson_r']:+.3f}")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)


def page_missingness(df: pd.DataFrame) -> None:
    st.header("Missingness dynamics")
    _safety_banner()
    summary = missingness_dynamics.per_participant_summary(df)
    state = missingness_dynamics.state_dependent_missingness(df)
    st.subheader("Per-participant summary")
    st.dataframe(summary.head(30))
    st.subheader("State-dependence")
    st.dataframe(state)
    fig, ax = plt.subplots()
    ax.hist(summary["miss_rate"], bins=20, edgecolor="white")
    ax.set_xlabel("missingness rate")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def page_device_bias(df: pd.DataFrame) -> None:
    st.header("Device bias")
    _safety_banner()
    bias = per_column_bias(df, ["resting_hr", "hrv_rmssd", "sleep_efficiency"])
    st.dataframe(bias)
    if not bias.empty:
        pivot = bias.pivot_table(index="device", columns="column",
                                 values="mean_diff", aggfunc="mean")
        fig, ax = plt.subplots()
        pivot.plot(kind="bar", ax=ax)
        ax.set_ylabel("mean diff vs reference")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)


def page_trust(df: pd.DataFrame, trust: pd.DataFrame) -> None:
    st.header("Digital Biomarker Trust Score")
    _safety_banner()
    pid = st.selectbox("Participant", sorted(df["participant_id"].unique()),
                       key="trust_pid")
    row = trust[trust["participant_id"] == pid].iloc[0]
    labels = ["signal_quality_score", "artifact_burden_score",
              "temporal_stability_score", "missingness_risk_score",
              "device_bias_score", "confounding_risk_score"]
    values = [float(row[l]) for l in labels]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_loop = values + [values[0]]
    angles_loop = angles + [angles[0]]
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(projection="polar"))
    ax.plot(angles_loop, values_loop, linewidth=2)
    ax.fill(angles_loop, values_loop, alpha=0.2)
    ax.set_xticks(angles)
    ax.set_xticklabels([l.replace("_", "\n") for l in labels], fontsize=7)
    ax.set_ylim(0, 100)
    st.pyplot(fig)
    plt.close(fig)
    st.metric("Overall trust score", f"{row['overall_trust_score']:.1f}")
    st.write(f"Category: **{row['category']}**")
    st.caption(row["explanation"])

    st.subheader("Cohort distribution")
    fig2, ax = plt.subplots()
    ax.hist(trust["overall_trust_score"], bins=30, edgecolor="white")
    ax.axvline(80, color="green", linestyle="--", label="high")
    ax.axvline(60, color="orange", linestyle="--", label="moderate")
    ax.axvline(40, color="red", linestyle="--", label="low")
    ax.set_xlabel("trust score")
    ax.legend()
    fig2.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)


def page_report() -> None:
    st.header("Report generator")
    _safety_banner()
    if st.button("Generate full markdown report"):
        from src.reports.report_generator import generate_report
        with st.spinner("Building report…"):
            path = generate_report()
        st.success(f"Report written to {path}")
        st.code(Path(path).read_text(encoding="utf-8")[:3000] + "\n\n…")


def page_safety() -> None:
    st.header("Safety notice")
    st.markdown(
        "This is a **non-clinical research prototype**. It is intended to "
        "support methodological audits of wearable-derived digital biomarkers. "
        "It is not a medical device. It does not diagnose, treat, cure, "
        "or prevent any disease. Outputs are signal-quality estimates and "
        "research-methodological recommendations.\n\n"
        "Do not use this tool to make medical decisions. Do not pass its "
        "outputs to participants as health information. If you adapt the "
        "codebase for a study, declare it as a methodological tool in your "
        "protocol and IRB submission and explicitly note that the trust "
        "score is a research signal, not a clinical signal."
    )


PAGES = {
    "Overview": page_overview,
    "Signal Quality Explorer": page_signal_quality,
    "Artifact Detection": page_artifacts,
    "Reliability Analysis": page_reliability,
    "Confounding Analysis": page_confounding,
    "Missingness Dynamics": page_missingness,
    "Device Bias": page_device_bias,
    "Digital Biomarker Trust Score": page_trust,
    "Report Generator": page_report,
    "Safety Notice": page_safety,
}


def main() -> None:
    page = st.sidebar.radio("Page", list(PAGES.keys()))
    df = load_data()
    if df.empty and page not in ("Safety Notice", "Report Generator"):
        st.info("Run `python scripts/run_pipeline.py` to generate synthetic data.")
        return
    trust = compute_trust_scores(df) if not df.empty else pd.DataFrame()
    fn = PAGES[page]
    # dispatch by signature length
    if page in ("Overview", "Digital Biomarker Trust Score"):
        fn(df, trust)
    elif page in ("Safety Notice", "Report Generator"):
        fn()
    else:
        fn(df)


if __name__ == "__main__":
    main()
