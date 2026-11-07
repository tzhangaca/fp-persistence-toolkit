# Release status

Version `0.2.1` follows `0.2.0`. It corrects interpretation wording and widens the audit-engine dependency to the two verified engine versions, `fp-persistence-audit` `0.1.2` and `0.1.3`, which produce identical schema-1.0 results. Comparison calculations, report fields and the report schema (`0.2.0`) are unchanged. GitHub Actions checks the package against both engine versions on Python 3.10–3.13. See the latest Actions run for test results.

The example uses artificial transactions. The toolkit reports descriptive model-instance comparisons, not a statistical test of superiority, real-world payment declines, or consumer harm. It does not reproduce the paper's complete FDH training, context-building or RQ2 inference pipeline.

GitHub Releases contains the tagged source archives. The package is not distributed through PyPI. All versions are archived on Zenodo under the concept DOI https://doi.org/10.5281/zenodo.23907914; version `0.2.0` is https://doi.org/10.5281/zenodo.23907916.
