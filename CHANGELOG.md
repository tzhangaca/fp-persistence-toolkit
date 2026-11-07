# Changelog

## 0.2.1

- Corrected interpretation wording: excess persistence measures recurrence (the share of eligible entities with two or more false positives relative to the reference), not overall false-positive concentration or severity. Updated the README, package description and citation abstract.
- Corrected one report message (`context_flag_allocation.interpretation`, shown when context allocations differ): "entity-level concentration" now reads "differences in which entities were flagged".
- Accepts `fp-persistence-audit` `0.1.3` in addition to `0.1.2` (dependency `>=0.1.2,<0.1.4`; explicit runtime allowlist). The two engine versions were verified to produce identical results; other versions are still rejected.
- Added two tests (accepted and rejected engine versions) and a CI matrix over both engine versions.
- No changes to comparison calculations, report fields, the report schema (`0.2.0`) or the public API.

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
