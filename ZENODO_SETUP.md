# Zenodo integration setup (one-time)

This document walks through enabling Zenodo so that every future GitHub
release of this repository automatically mints a permanent DOI. The DOI
is what `npj Digital Medicine`, `Lancet Digital Health`, and most other
high-tier journals require for code citations in published papers.

## Why Zenodo and not just GitHub releases

GitHub release URLs are tied to GitHub the company. If GitHub goes away,
moves the repository, or renames the user, the URL breaks. Zenodo is
operated by CERN, archives a full snapshot of each release, and issues a
DOI that resolves forever through doi.org. Journals require the DOI form
for citing software.

## Steps

### 1. Sign in to Zenodo via GitHub

Visit https://zenodo.org/login and choose "Log in with GitHub". Authorise
the OAuth permissions Zenodo requests (read-only access to your public
repositories and the ability to receive release webhooks).

### 2. Enable the integration for this repository

Visit https://zenodo.org/account/settings/github/. Find
`ceyhunolcan/biomedical-signal-forensics-lab` in the list and flip the
toggle to **ON**. If the repository does not appear, click "Sync now" at
the top of the page; Zenodo polls GitHub roughly every five minutes.

After flipping the toggle, Zenodo registers a webhook on the GitHub
repository. You can verify this at
https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/settings/hooks;
there should be a `https://zenodo.org/...` webhook with a green check
mark.

### 3. Verify .zenodo.json metadata is correct

Open `.zenodo.json` at the repository root. The contents will be parsed
by Zenodo every time you publish a GitHub release. Fields that matter:

- `title`, `description`, `creators`, `keywords`, `license`,
  `upload_type`, `access_right` : these all populate the Zenodo deposit.
- `creators[].orcid` : links the Zenodo deposit to your ORCID profile,
  so the DOI shows up automatically on https://orcid.org/0000-0002-6326-6071.

If the file is missing fields, Zenodo will fall back to scraping the
GitHub repository description, which is much less clean.

### 4. Trigger the first deposit

Zenodo only mints DOIs for releases created AFTER the integration is
toggled on. The integration was enabled at the start of v0.13.0, so the
first DOI will be minted when you publish the v0.13.0 release on GitHub
(via `gh release create v0.13.0 ...`).

Within roughly one minute of the GitHub release, you can visit
https://zenodo.org/account/settings/github/ and click on the repository
name to see the deposit listed. Zenodo provides two DOIs:

- A **concept DOI** (also called "all versions" DOI) that points to the
  latest version of the software in perpetuity. Use this in papers
  where the version-specific URL is not appropriate.
- A **version-specific DOI** that points to v0.13.0 specifically. Use
  this in papers that need to cite the exact code state used.

Both DOIs resolve forever through doi.org.

### 5. Update the README and CITATION.cff with the real DOI

Once the first DOI is minted, update:

- `README.md`: replace the two `PLACEHOLDER` strings in the DOI badge
  and BibTeX block with the actual DOI (typically of the form
  `10.5281/zenodo.<id>`).
- `CITATION.cff`: add a `doi:` field at the top level pointing to the
  concept DOI.

Commit and push the update. The DOI will then propagate to the GitHub
"Cite this repository" sidebar button.

## Optional: also publish to PyPI

If you want `pip install biomedical-signal-forensics-lab` to work, you
also need to publish to PyPI. That is a separate flow covered in
`.github/workflows/publish-pypi.yml` (added in a future release). It
requires creating a PyPI account and registering the project name. PyPI
does not replace Zenodo; the two serve different purposes (PyPI is for
installation, Zenodo is for citation).

## Troubleshooting

- "Repository does not appear in the Zenodo list." Click "Sync now" and
  wait one minute. If still missing, confirm the repository is public.
  Zenodo only sees public GitHub repos by default.
- "The DOI badge in the README shows `PLACEHOLDER`." Replace the
  placeholder string with the actual DOI from Zenodo after the first
  deposit. See step 5.
- "ORCID does not show up on the Zenodo deposit." Confirm the `orcid`
  field in `.zenodo.json` is exactly 19 characters (four groups of
  digits separated by hyphens) and that the ORCID is public on
  orcid.org.
