#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -c "from importlib.metadata import version; assert version('fp-persistence-audit') in ('0.1.2', '0.1.3'); assert version('fp-persistence-toolkit') == '0.2.1'"
python -m unittest discover -s tests -v
python examples/public_engine_end_to_end.py
printf '\nVALIDATION PASS: inspect demo_output and ensure real-engine tests were not skipped.\n'
