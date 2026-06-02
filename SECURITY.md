# Security Policy

## Supported versions

Security fixes are applied to the most recent release on PyPI. Older versions
are not maintained. The current release line is shown on the project's
[PyPI page](https://pypi.org/project/biomedical-signal-forensics-lab/).

| Version  | Supported |
| -------- | --------- |
| latest   | yes       |
| < latest | no        |

## Reporting a vulnerability

Please do not open a public issue for a security problem. Instead, use the
private vulnerability reporting on this repository (Security tab, then "Report
a vulnerability"), or email the maintainer at ceyhun.olcan.27@dartmouth.edu
with a description and steps to reproduce.

You can expect an initial response within a reasonable time. Confirmed issues
will be addressed in a patched release, and the report will be credited unless
you prefer to remain anonymous.

## Scope

This toolkit analyzes pre-recorded physiological signal files and public
datasets. It runs no network services and handles no credentials. The most
likely class of issue is unsafe handling of untrusted input files, so reports
in that area are especially welcome.
