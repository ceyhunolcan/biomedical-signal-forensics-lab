# PyPI publishing setup (one-time)

This document walks through publishing `biomedical-signal-forensics-lab`
to PyPI so `pip install biomedical-signal-forensics-lab` works for
anyone, anywhere. The setup uses
[trusted publishers](https://docs.pypi.org/trusted-publishers/) (OIDC),
which means **no API tokens are stored in the repository**; the GitHub
Actions workflow authenticates to PyPI by virtue of being run from
this repository.

## One-time setup steps

### 1. Create a PyPI account

Visit https://pypi.org/account/register/ and create an account if you
do not already have one. The email you use should be one you check;
PyPI will send a verification email and uses the same address for
security notifications.

While you are there, also create a
[TestPyPI](https://test.pypi.org/account/register/) account. TestPyPI
is a sandbox where you can dry-run uploads before publishing to the
real PyPI.

### 2. Add a "pending publisher" for this repository

Go to https://pypi.org/manage/account/publishing/ and click
**Add a new pending publisher**. Fill in:

| Field | Value |
|---|---|
| PyPI Project Name | `biomedical-signal-forensics-lab` |
| Owner | `ceyhunolcan` |
| Repository name | `biomedical-signal-forensics-lab` |
| Workflow name | `publish-pypi.yml` |
| Environment name | `pypi` |

This tells PyPI to expect an OIDC token from the named GitHub Actions
workflow in the named repository, running in the named environment.

Repeat the same steps on https://test.pypi.org/manage/account/publishing/
with the same project name and `testpypi` as the environment.

### 3. Add matching environments on the GitHub repository

Go to
https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/settings/environments
and create two environments:

- `pypi` (for the real publish)
- `testpypi` (for the TestPyPI dry-run)

For each environment, optionally add a deployment protection rule so
that only specific tags (e.g. `v*`) can deploy to it. This is
defence-in-depth; the OIDC binding already ties the environment to
this repo.

### 4. Verify pyproject.toml has the required fields

Run the audit script:

```bash
python audit_pyproject.py
```

It will report any missing fields that PyPI requires (description,
readme, license, etc.). Fix anything it flags before proceeding.

### 5. Dry-run on TestPyPI

After the v0.15.0 release lands on GitHub, manually trigger the
publish workflow with target `testpypi`:

```bash
gh workflow run publish-pypi.yml -f target=testpypi
```

Watch the run at
https://github.com/ceyhunolcan/biomedical-signal-forensics-lab/actions/workflows/publish-pypi.yml.

If it succeeds, you should be able to install from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ biomedical-signal-forensics-lab
```

### 6. First real publish

Create the next release on GitHub (e.g. `v0.15.1` or `v0.16.0`). The
publish-pypi.yml workflow fires automatically on release publication
and pushes to the real PyPI. You can also trigger it manually:

```bash
gh workflow run publish-pypi.yml -f target=pypi
```

Within a minute, the package appears at
https://pypi.org/project/biomedical-signal-forensics-lab/ and is
installable with `pip install biomedical-signal-forensics-lab`.

## Per-release flow after the first publish

Once the trusted publisher is configured, every future release on
GitHub fires the workflow automatically:

1. Bump the version (`python3 update_version.py X.Y.Z`).
2. Commit, tag, push.
3. Create the GitHub release (`gh release create vX.Y.Z ...`).
4. Within ~3 minutes the new version is on PyPI.

## Troubleshooting

- "OIDC token rejected" - confirm the environment name in
  `publish-pypi.yml` matches what you registered on PyPI, exactly,
  case-sensitive.
- "Project name conflict" - someone else already has the name on
  PyPI. Pick a different distribution name in `pyproject.toml`
  (e.g. `biomedical-signal-forensics-lab-toolkit`) while keeping the
  import name (`biomedical_signal_forensics_lab`) the same.
- "Metadata validation failed" - run `twine check dist/*` locally on
  a built distribution to see the specific error.
- "Token has insufficient scope" - the trusted-publisher OIDC token
  is single-purpose; do not try to add additional scopes. The
  `id-token: write` permission on the publish job is all that is
  required.
