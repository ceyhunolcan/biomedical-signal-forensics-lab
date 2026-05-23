# Documentation site setup (one-time)

This document walks through publishing the documentation site to
GitHub Pages so it lives at
https://ceyhunolcan.github.io/biomedical-signal-forensics-lab/.

The setup uses `mkdocs gh-deploy`, which pushes the built site to a
`gh-pages` branch. GitHub Pages then serves that branch as the
website.

## One-time setup

### 1. Confirm mkdocs builds locally

Before pushing, verify the docs build on your machine:

```bash
pip install -r docs/requirements.txt
pip install -e .         # so mkdocstrings can introspect the API
mkdocs serve
```

Open http://localhost:8000 and click through the pages. You should
see:

- Home (landing page with key results)
- Getting started
- Reproducing the paper
- Reporting standards (with TRIPOD+AI and STARD checklists pulled in)
- API reference (auto-generated from docstrings)
- Citing
- Changelog (pulled from `CHANGELOG.md`)

Stop the local server with Ctrl-C when done.

### 2. Push the docs and let CI deploy

Commit `mkdocs.yml`, `docs/`, and `.github/workflows/docs.yml` to
`main`. The `Deploy documentation` workflow will fire automatically
and:

- Build the site with `mkdocs build`.
- Push the built HTML to a `gh-pages` branch (created automatically
  if it does not exist).

Watch the run at
https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/actions/workflows/docs.yml.

### 3. Enable GitHub Pages serving from `gh-pages`

Go to
https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/settings/pages.

Under **Build and deployment**:

- Source: **Deploy from a branch**
- Branch: **gh-pages** / **(root)**

Click **Save**. Within ~30 seconds, your site is live at
https://ceyhunolcan.github.io/biomedical-signal-forensics-lab/.

### 4. (Optional) Add the docs link to the README

Add this badge near the top of `README.md`:

```markdown
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://ceyhunolcan.github.io/biomedical-signal-forensics-lab/)
```

## Per-release flow

Once Pages is enabled, every push to `main` or every release tag
triggers the workflow, rebuilds the site, and pushes to `gh-pages`.
Within ~1 minute the live site reflects the latest content.

## Troubleshooting

- "404 Not Found at <username>.github.io/<repo>/" - GitHub Pages can
  take up to 10 minutes on first enable. Wait, then refresh.
- "mkdocstrings says cannot import src.signals" - confirm the docs
  workflow runs `pip install -e .` before `mkdocs gh-deploy`. The
  shipped `.github/workflows/docs.yml` does this.
- "include-markdown plugin error" - the path in `docs/changelog.md` and
  `docs/reporting-standards.md` is `../CHANGELOG.md`,
  `../paper/checklists/*.md`. These are relative to the file that
  contains the include directive. If the CI environment runs mkdocs
  from a different working directory, set
  `plugins.include-markdown.opening_tag` and `closing_tag` explicitly
  or move the included files under `docs/`.
- "Page renders raw `{% include-markdown %}`" - the `include-markdown`
  plugin is not loaded. Confirm `plugins:` in `mkdocs.yml` includes
  `include-markdown` and the plugin is in `docs/requirements.txt`.

## Adding new pages

1. Drop a new `.md` file under `docs/`.
2. Add it to the `nav:` block in `mkdocs.yml` at the position you
   want it to appear.
3. Push. The workflow rebuilds and redeploys.
