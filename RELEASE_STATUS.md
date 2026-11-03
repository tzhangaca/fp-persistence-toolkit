# Release status

`fp-persistence-toolkit` 0.2.0rc3 is a source preview. It has not been tagged, uploaded to PyPI, or assigned a software DOI.

The previous `rc2` code passed 37 tests without skips and completed an end-to-end comparison using the published `fp-persistence-audit==0.1.2` engine on macOS with Python 3.13. Since then, the package was renamed and one report-layout regression test was added. The current source needs a fresh CI run with 38 tests and the example workflow on each of Python 3.10–3.13 before tagging.

The included example uses constructed transactions, not real-world payment decisions. The toolkit does not reproduce the paper's complete FDH training, context-construction or RQ2 inference pipeline.
