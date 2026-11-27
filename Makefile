# Offline, deterministic, one command. `make verify` is the promise the README
# makes to a reviewer: lint, tests, then re-measure every published number and
# fail if the prose has drifted. No network at any target.

PYTHON ?= python
PKG := cpr

.PHONY: help install lint test cov experiments report receipts evidence verify clean

help:
	@echo "Targets:"
	@echo "  install     editable install with dev extras"
	@echo "  lint        ruff check + the em-dash guard"
	@echo "  test        pytest with coverage, writes coverage.json and coverage.xml"
	@echo "  experiments re-run all experiments into docs/experiments/"
	@echo "  report      build the HTML report from the fixture"
	@echo "  receipts    collect metrics then check every published number"
	@echo "  evidence    render diagram SVG, screenshots, demo replay (needs playwright)"
	@echo "  verify      lint + test + receipts (the reviewer command)"

install:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	ruff check .
	$(PYTHON) tools/check_no_emdash.py

test:
	$(PYTHON) -m pytest -q \
		--cov=$(PKG) --cov-branch \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-report=json:coverage.json \
		--junitxml=reports/junit.xml

experiments:
	$(PYTHON) experiments/exp01_shared_float.py
	$(PYTHON) experiments/exp02_rerouting.py
	$(PYTHON) experiments/exp03_blast_radius.py
	$(PYTHON) experiments/exp04_joint_boundary.py
	$(PYTHON) experiments/exp05_robustness.py

report:
	$(PYTHON) -m cpr.cli analyze fixtures/program.json --html docs/report/program.html

# collect_metrics runs the suite and the experiments itself; check_numbers
# guards the prose. Split in CI (see ci-and-rendering-traps), joined here.
receipts:
	$(PYTHON) tools/collect_metrics.py
	$(PYTHON) tools/check_numbers.py

evidence:
	$(PYTHON) tools/render_diagrams.py
	$(PYTHON) tools/capture_screenshots.py
	$(PYTHON) tools/record_demo.py

verify: lint test receipts
	@echo "verify: OK"

clean:
	rm -rf reports htmlcov .pytest_cache .ruff_cache coverage.xml coverage.json .coverage docs/report
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
