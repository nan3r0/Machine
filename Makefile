# Gate 1 (HARNESS.md section 6b). CI runs `make check`; locally on Windows run only the first three
# commands by hand (ruff, mypy, pytest). Any high-severity finding fails.
# The two pip-audit ignores are setuptools 81.0.0 advisories (fixed in 83.0.0 and 84.1.0). torch
# caps setuptools below 82, so the pin cannot move; drop the ignores when torch lifts the cap.
.PHONY: check

check:
	ruff check .
	mypy --strict pipeline/
	pytest -q --tb=short --cov=pipeline --cov-report=term
	pytest -q --tb=short .harness/tests
	bandit -q -r pipeline --severity-level high
	semgrep scan --config p/python --severity ERROR --error --metrics off --quiet pipeline tests
	gitleaks git --redact --no-banner .
	pip-audit -r requirements.txt -r requirements-heavy.txt --ignore-vuln PYSEC-2026-3447 --ignore-vuln GHSA-xmj3-9gf7-h52w
	actionlint
