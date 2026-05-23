# Citing this toolkit

If you use this toolkit in academic work, please cite the software.
The repository's [`CITATION.cff`](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/blob/main/CITATION.cff)
file is the canonical source of citation metadata; tools like
GitHub, Zotero, Mendeley, and Citation File Format readers will parse
it automatically.

## BibTeX

```bibtex
@software{olcan2026biomedical,
  author       = {Olcan, Ceyhun},
  title        = {{biomedical-signal-forensics-lab}: An open-source
                  toolkit for auditing wearable physiological signal
                  pipelines},
  year         = {2026},
  version      = {v0.15.0},
  url          = {https://github.com/ceyhunolcan/biomedical-signal-forensics-lab},
  doi          = {10.5281/zenodo.20349806}
}
```

## DOIs

| DOI | Resolves to |
|---|---|
| **10.5281/zenodo.20349806** | Concept DOI (always points to the latest release) |
| Version-specific DOIs | Individual releases (see [Zenodo](https://zenodo.org/account/settings/github/) or the Zenodo deposit page) |

For papers that depend on the exact code state of a single release, use
the version-specific DOI. For papers that should always link to the
latest version, use the concept DOI.

## Plain text

> Olcan, C. (2026). biomedical-signal-forensics-lab: An open-source
> toolkit for auditing wearable physiological signal pipelines
> (v0.15.0) [Computer software]. Zenodo.
> https://doi.org/10.5281/zenodo.20349806

## Citing the manuscript

The methods paper that this toolkit accompanies is in preparation
([see the manuscript draft on GitHub](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/blob/main/paper/manuscript.md)).
Once published, the canonical citation will be updated here and in
`CITATION.cff`. Until then, please cite the software as above.

## Citing the methods we build on

This toolkit reuses and audits methodologies from prior published work.
If you use specific components, please also cite the originating paper:

- **Orphanidou et al. 2015** (signal-quality template matching):
  Orphanidou et al., IEEE J Biomed Health Inform 19(3):832-838.
- **Sukor et al. 2011** (PPG signal-quality decision tree):
  Sukor et al., Physiol Meas 32(4):369-384.
- **Elgendi 2016** (skewness, kurtosis, entropy SQIs):
  Elgendi, Bioengineering 3(4):21.
- **Schmidt et al. 2018** (WESAD dataset):
  Schmidt et al., ICMI 2018.
- Full bibliographic details in
  [`paper/paper.bib`](https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/blob/main/paper/paper.bib).
