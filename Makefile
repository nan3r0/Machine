# Gate 1 (HARNESS.md section 6b). CI runs `make check`; locally on Windows run only the first three
# commands by hand (ruff, mypy, pytest). Any high-severity finding fails.
# The two pip-audit ignores are setuptools 81.0.0 advisories (fixed in 83.0.0 and 84.1.0). torch
# caps setuptools below 82, so the pin cannot move; drop the ignores when torch lifts the cap.
# PYSEC-2025-194 is torch 2.11.0 (fixed in 2.13.0). It cannot move yet: stable-ts imports
# torchaudio at module level, and the newest torchaudio is 2.11.1, which needs torch 2.11. Drop the
# ignore when a torchaudio for torch 2.13+ ships and both pins move.
# pip-audit resolves from PyPI, where the +cpu local versions do not exist, so it audits a copy
# of requirements-heavy.txt without the suffix (same release, same advisories).
# `audit` is its own target so the weekly audit workflow runs the same command and ignores.
.PHONY: check audit

check:
	python tests/docs_check.py
	ruff check .
	mypy --strict pipeline/
	pytest -q --tb=short --cov=pipeline --cov-report=term
	pytest -q --tb=short .harness/tests
	bandit -q -r pipeline --severity-level high
	semgrep scan --config p/python --severity ERROR --error --metrics off --quiet pipeline tests
	gitleaks git --redact --no-banner .
	$(MAKE) audit
	actionlint

audit:
	audit=$$(mktemp) && sed 's/+cpu//' requirements-heavy.txt > $$audit && pip-audit -r requirements.txt -r $$audit --ignore-vuln PYSEC-2026-3447 --ignore-vuln PYSEC-2025-194 --ignore-vuln GHSA-xmj3-9gf7-h52w
