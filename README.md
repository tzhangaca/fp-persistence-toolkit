# False-Positive Persistence Toolkit

A Python companion to [fp-persistence-audit](https://github.com/tzhangaca/fp-persistence-audit), designed to compare repeated false-positive patterns across two fitted fraud-screening model instances.

Fraud-screening models can produce similar transaction-level metrics while differing in how many returning accounts receive repeated false-positive flags. This toolkit compares entity-level recurrence on a shared set of legitimate transactions. It calls the published `fp-persistence-audit` engine (v0.1.2 or v0.1.3, which produce identical results) for each audit and presents the results side by side. It does not train a fraud model or replace the underlying audit engine.

The toolkit is distributed as open source through GitHub. The current package version is `0.2.1`; see GitHub Releases for tagged snapshots. It is not currently available through PyPI.

## Installation

Use Python 3.10–3.13. In the repository directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

The package installs the published audit engine as a dependency.

To install the tagged release without cloning (requires `git`):

```bash
python -m pip install "fp-persistence-toolkit @ git+https://github.com/tzhangaca/fp-persistence-toolkit.git@v0.2.1"
```

## Quick start

Run the tests and the included example:

```bash
python -m unittest discover -s tests -v
python examples/public_engine_end_to_end.py
```

The example creates twelve artificial legitimate transactions and evaluates two different sets of false-positive flags. Both have four false positives, but those flags recur on different numbers of entities. It writes `demo_output/comparison_report.json` and `demo_output/comparison_report.md`. The JSON report records execution timestamps (and source hashes that include them), so its file hash changes between otherwise identical runs; the Markdown report and the scientific fields are stable.

For a live comparison, supply one event table with two flag columns and preassigned context strata:

```python
from fp_persistence import ExposureSpec, PermutationSpec
from persistence_toolkit import audit_and_compare_shared_frame

result = audit_and_compare_shared_frame(
    events,
    left_flag_col="flags_A",
    right_flag_col="flags_B",
    entity_col="entity_id",
    event_id_col="event_id",
    legitimate_col="legitimate",
    final_stratum_col="final_stratum",
    exposure=ExposureSpec(3, 3),
    permutation=PermutationSpec(500, 2026091601),
    audit_window="documented audit window",
)
```

`events` must be a pandas DataFrame containing the listed columns. The `legitimate` indicator, entity IDs, and resolved context strata must be supplied by the analyst. This package does not infer ground truth or generate the context hierarchy used in the research paper.

To compare saved example JSON files or summarize seed-level results:

```bash
python -m persistence_toolkit compare examples/toy_model_A.json examples/toy_model_B.json --out demo_unverified
python -m persistence_toolkit seeds examples/toy_seeds.json --out demo_seeds
```

## Interpreting a comparison

The live workflow checks that the models are evaluated on the same event, entity, label, and context records, with matching exposure rules and the same total false-positive budget. Reports describe three possible comparability outcomes:

- `COMPARABLE`: the live, same-frame checks passed for a descriptive comparison.
- `INCOMPATIBLE`: one or more required comparison conditions conflict.
- `INDETERMINATE`: the source identity cannot be established, as with independently supplied JSON files that only contain self-reported metadata.

The report also records whether the two models allocate the same number of false positives to each resolved context (`MATCH` or `DIFFERENT`). If context-specific counts differ, reference expectations may differ as well; the excess-persistence gap should not be attributed solely to changes in which entities were flagged.

Excess persistence compares the share of eligible entities with two or more false positives against the reference expectation. It is not a monotonic measure of overall false-positive concentration or severity. A model with lower excess persistence can still place more false positives on fewer entities, because counts above two are not summarized. Do not read a lower or negative excess as "less concentrated" or "less burdensome" without also comparing the per-entity false-positive count distribution, computed separately.

These checks make the reports easier to interpret, but do not authenticate transaction histories or prove that supplied labels are correct. The output is descriptive, not a statistical test of model superiority, an equivalence test, or a recommendation to deploy one model over another. PR-AUC and ROC-AUC are not calculated from the legitimate-only audit input; any external values must be sourced and checked separately.

False-positive flags are model outputs. They are not, by themselves, evidence of extra verification, declined payments, lost sales, or consumer harm. Reports may include metadata provided by the caller, so review JSON files for sensitive information before sharing them. SHA256 hashes support input consistency checks but are not a privacy safeguard or a digital signature.

## Development and release status

Version `0.2.1` corrects interpretation wording (one report message and the documentation) and accepts audit engine `0.1.3` in addition to `0.1.2`; comparison calculations, report fields and the report schema are unchanged (see [CHANGELOG.md](CHANGELOG.md)). GitHub Actions runs the 40 unit and integration tests on Python 3.10–3.13 against both supported engine versions. Check the latest Actions run for the test outcome before using a newly tagged version. See [RELEASE_STATUS.md](RELEASE_STATUS.md) for release details.

## Citation

For software citation metadata, see [CITATION.cff](CITATION.cff). All versions are archived on Zenodo under the concept DOI [https://doi.org/10.5281/zenodo.23907914](https://doi.org/10.5281/zenodo.23907914); version `0.2.0` is [https://doi.org/10.5281/zenodo.23907916](https://doi.org/10.5281/zenodo.23907916).

## License

Apache License 2.0. See [LICENSE](LICENSE).
