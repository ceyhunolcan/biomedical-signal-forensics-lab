# mkdocs.yml update for v0.17.2

The new `docs/index.md`, `docs/methods.md`, `docs/comparison.md`, and the
existing `docs/results.md` (from v0.17.1) need to be wired into the
mkdocs-material navigation. Open `mkdocs.yml` and replace the existing `nav:`
block with the snippet below; everything else in `mkdocs.yml` (theme,
plugins, markdown extensions) stays unchanged.

```yaml
nav:
  - Home: index.md
  - Getting started: getting_started.md
  - Methods: methods.md
  - Results: results.md
  - Comparison vs other tools: comparison.md
  - Reproducing the paper: reproducing_paper.md
  - Reporting standards: reporting_standards.md
  - API reference: api/index.md
  - Citing: citing.md
  - Changelog: changelog.md
```

The order above places the four new pages (Methods, Results, Comparison) in
the upper navigation where new visitors are most likely to look, while
keeping the operational pages (Getting started, Reproducing the paper) and
the reference pages (API, Citing, Changelog) accessible.

If `mkdocs.yml` references any of the new pages elsewhere (e.g. in plugin
configuration), no change is needed; the navigation block is the only place
that lists pages explicitly.

After committing, the deployed site at
https://ceyhunolcan.github.io/biomedical-signal-forensics-lab/ will pick up
the new nav structure on the next docs.yml workflow run.
