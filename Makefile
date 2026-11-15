# Gate 1 (HARNESS.md section 6b). CI runs `make check`; locally on Windows run only the first three
# commands by hand (ruff, mypy, pytest). Any high-severity finding fails.
.PHONY: check

check:
	ruff check .
	mypy --strict pipeline/
	pytest -q --tb=short --cov=pipeline --cov-report=term
	pytest -q --tb=short .harness/tests
	bandit -q -r pipeline --severity-level high
	semgrep scan --config p/python --severity ERROR --error --metrics off --quiet pipeline tests
	gitleaks git --redact --no-banner .
	pip-audit
	actionlint
