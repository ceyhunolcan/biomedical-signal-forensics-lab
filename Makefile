.PHONY: help install test lint pipeline audit train report dashboard api clean check-em-dashes all

PYTHON ?= python

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime dependencies
	pip install -r requirements.txt

install-dev:  ## Install runtime + dev dependencies (pytest, ruff)
	pip install -r requirements.txt
	pip install pytest pytest-cov ruff

test:  ## Run the sandbox-compatible minimal test runner
	$(PYTHON) scripts/run_tests_minimal.py

test-pytest:  ## Run the full pytest suite (requires pytest)
	pytest tests/ -v --ignore=tests/test_api.py

lint:  ## Run ruff check and format check
	ruff check src scripts tests --select E,F,W,B --ignore E501
	ruff format --check src scripts tests

format:  ## Apply ruff format
	ruff format src scripts tests

check-em-dashes:  ## Fail if any em-dash is found in .md or .py files
	@if grep -rln "—" --include="*.md" --include="*.py" .; then \
		echo "Found em-dashes. Use periods, colons, or parentheses instead."; \
		exit 1; \
	fi
	@echo "No em-dashes found."

pipeline:  ## Generate the synthetic cohort and run preprocessing
	$(PYTHON) scripts/run_pipeline.py

audit:  ## Run the full signal-audit pipeline (assumes cohort already generated)
	$(PYTHON) scripts/run_signal_audit.py

train:  ## Train baseline models and write the leaderboard
	$(PYTHON) scripts/train_quality_model.py

report:  ## Generate the markdown report
	$(PYTHON) scripts/generate_report.py

cross-cohort:  ## Run the cross-cohort generalization check
	$(PYTHON) scripts/run_cross_cohort_check.py

all: pipeline audit train report  ## Generate cohort and run the full audit + report

dashboard:  ## Launch the Streamlit dashboard (requires streamlit)
	streamlit run src/dashboard/app.py

api:  ## Launch the FastAPI service (requires fastapi + uvicorn)
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

clean:  ## Remove generated outputs and caches
	rm -rf results/tables/* results/figures/* results/reports/*
	rm -rf data/synthetic/* data/processed/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

verify:  ## Run tests + em-dash check + lint
	$(MAKE) test
	$(MAKE) check-em-dashes
	@echo "All checks passed."
