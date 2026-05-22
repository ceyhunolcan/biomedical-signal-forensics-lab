"""Patch paper/manuscript.md to add a Reporting Standards subsection and a
reference to the new flow diagram, and to bring four orphan citations into
the manuscript text.

Citations brought into use:
  collins2024tripodai  - TRIPOD+AI
  bossuyt2015stard     - STARD 2015
  liu2020consortai     - CONSORT-AI
  vasey2022decideai    - DECIDE-AI

Plus retries on two earlier-missed anchors:
  wilcoxon1945         - paired Wilcoxon
  obermeyer2019/vyas2020 - algorithmic fairness framing
"""

from __future__ import annotations

from pathlib import Path


def patch(manuscript_path: Path) -> None:
    txt = manuscript_path.read_text()
    original_len = len(txt)

    # ---------------------------------------------------------------------
    # 1. Add a Reporting Standards subsection at the end of Methods, OR
    #    near the start of Section 6 (Limitations) if Methods has no
    #    explicit closing anchor. We try several insertion points and
    #    use the first one that exists.
    # ---------------------------------------------------------------------

    section_block = """
### 3.7 Reporting standards and reproducibility

The pipeline and analyses in this paper were assessed against the relevant EQUATOR-Network reporting standards for digital-health AI research. Per-standard compliance documentation is provided in `paper/checklists/`:

- **TRIPOD+AI** [@collins2024tripodai] applies to the downstream classifier evaluated in Section 4.6 (LF/HF biomarker, LOSO cross-validation). A per-item compliance summary is in `paper/checklists/tripod_ai_checklist.md`. The downstream classifier in Section 4.6 is a research-stage demonstration intended to test whether the SQI binarisation choice has a measurable downstream effect; it is not a deployment candidate. TRIPOD+AI items related to calibration and external validation are intentionally out of scope for that framing and are noted explicitly in Section 6.
- **STARD 2015** [@bossuyt2015stard] applies to Sections 4.1-4.3, in which chest ECG serves as the reference standard and wrist PPG-derived measurements serve as the index modality. A per-item compliance summary is in `paper/checklists/stard_2015_checklist.md`. The flow diagram in Figure 1 follows STARD conventions adapted to the multi-arm structure of this audit.
- **CONSORT-AI** [@liu2020consortai] and **DECIDE-AI** [@vasey2022decideai] do not apply because this paper is neither a randomised trial nor a clinical-deployment study. Applicability assessments documenting this conclusion (and what a future deployment of this toolkit would need to report) are in `paper/checklists/consort_ai_applicability.md` and `paper/checklists/decide_ai_applicability.md`.

Figure 1 (`paper/figures/fig_flow_diagram.png`) shows the flow of data through the WESAD validation pipeline in the STARD-style convention: source dataset, n=15 subjects analysed, per-window processing, zero post-hoc exclusions, and the four analysis arms operating on the same 6,585 windows.

"""

    # Try to insert before Section 4 (results)
    candidate_anchors = [
        "\n### 4.1 ",   # right before Results 4.1
        "\n## 4 Results",
        "\n## 4. Results",
        "\n# 4 Results",
    ]
    inserted_section = False
    for anchor in candidate_anchors:
        idx = txt.find(anchor)
        if idx != -1:
            txt = txt[:idx] + section_block + txt[idx:]
            print(f"Inserted 3.7 Reporting Standards block before: {anchor!r}")
            inserted_section = True
            break

    if not inserted_section:
        # Fallback: append at end (before References if present, else at end)
        ref_idx = txt.find("\n## References")
        if ref_idx == -1:
            ref_idx = txt.find("\n# References")
        if ref_idx != -1:
            txt = txt[:ref_idx] + section_block + txt[ref_idx:]
            print("Inserted 3.7 Reporting Standards block before References.")
        else:
            txt = txt + section_block
            print("Appended 3.7 Reporting Standards block at end of manuscript.")

    # ---------------------------------------------------------------------
    # 2. Retry the previously-missed Wilcoxon anchor with multiple
    #    candidate phrasings.
    # ---------------------------------------------------------------------

    wilcox_candidates = [
        ("Wilcoxon signed-rank", "Wilcoxon signed-rank [@wilcoxon1945]"),
        ("Wilcoxon p = 1.5e-4", "Wilcoxon [@wilcoxon1945] p = 1.5e-4"),
        ("Wilcoxon p=1.5e-4", "Wilcoxon [@wilcoxon1945] p=1.5e-4"),
        ("paired Wilcoxon", "paired Wilcoxon [@wilcoxon1945]"),
    ]
    for anchor, replacement in wilcox_candidates:
        if anchor in txt and replacement not in txt:
            txt = txt.replace(anchor, replacement, 1)
            print(f"Cited wilcoxon1945 via anchor: {anchor!r}")
            break
    else:
        print("Note: no matching Wilcoxon anchor found; wilcoxon1945 may remain uncited in body text.")

    # ---------------------------------------------------------------------
    # 3. Retry algorithmic-fairness framing with broader anchors.
    # ---------------------------------------------------------------------

    fairness_candidates = [
        ("fairness disparities",
         "fairness disparities (a known concern in clinical algorithms [@obermeyer2019; @vyas2020])"),
        ("skin-tone gap",
         "skin-tone gap (a known site of optical-sensor inequity [@sjoding2020; @obermeyer2019; @vyas2020])"),
        ("fairness audit",
         "fairness audit (motivated by documented algorithmic inequities in clinical AI [@obermeyer2019; @vyas2020])"),
    ]
    # Only insert ONE of these to avoid over-stuffing
    for anchor, replacement in fairness_candidates:
        if anchor in txt and "[@obermeyer2019" not in txt:
            txt = txt.replace(anchor, replacement, 1)
            print(f"Cited obermeyer2019/vyas2020 via anchor: {anchor!r}")
            break

    # ---------------------------------------------------------------------
    # Write and summarise
    # ---------------------------------------------------------------------
    manuscript_path.write_text(txt)
    delta = len(txt) - original_len
    print(f"\nManuscript: {original_len:,} -> {len(txt):,} bytes ({delta:+,})")

    import re as _re
    keys = sorted(set(_re.findall(r"\[@([a-z0-9_]+)", txt)))
    total = len(_re.findall(r"\[@[a-z0-9_]+", txt))
    print(f"Unique citation keys: {len(keys)}")
    print(f"Total citation invocations: {total}")
    # Check the 4 standards
    for k in ("collins2024tripodai", "bossuyt2015stard", "liu2020consortai", "vasey2022decideai", "wilcoxon1945", "obermeyer2019", "vyas2020"):
        cited = f"@{k}" in txt
        flag = "OK" if cited else "MISSING"
        print(f"  {flag}: {k}")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    target = here / "paper" / "manuscript.md"
    if not target.exists():
        raise SystemExit(f"manuscript not found at {target}")
    patch(target)
