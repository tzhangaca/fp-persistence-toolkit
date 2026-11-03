# Changelog

## 0.2.0

- Added `CITATION.cff` and consistent software citation metadata.
- Aligned the distribution, test scripts and documentation on version `0.2.0`.
- Updated GitHub Actions runner versions.
- No changes to the audit estimand or comparison calculations since `0.2.0rc3`.

## 0.2.0rc3 — source preview

- Renamed the repository, distribution and Python import to `fp-persistence-toolkit` and `persistence_toolkit`.
- Fixed a Markdown layout issue in the comparison report and added a regression test.
- Left the published `fp-persistence-audit` engine and its statistical definitions unchanged.

## 0.2.0rc2 — release candidate

- Added a check for differences in how false-positive counts are distributed across context strata.
- Strengthened population and input consistency checks.
- Added integration tests using the published audit engine and GitHub Actions jobs for Python 3.10–3.13.

## 0.2.0rc1 — development candidate

- Added a direct two-model audit workflow using a common event table.
- Changed comparisons of independently supplied JSON reports to `INDETERMINATE` when provenance cannot be independently established.
- Added source fingerprints and checks against public audit results.

The `0.2.0rc3` candidate was published as a GitHub pre-release before the preparation of `0.2.0`.
