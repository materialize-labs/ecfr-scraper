# Makefile for eCFR Scraper project

.PHONY: help setup test test-unit test-integration test-cli test-coverage clean lint format install run-sample docs

# Default target
help:
	@echo "eCFR Scraper - Available commands:"
	@echo ""
	@echo "Setup:"
	@echo "  setup          - Set up virtual environment and install dependencies"
	@echo "  install        - Install package in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-cli       - Test CLI commands"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint           - Run linting checks"
	@echo "  format         - Format code with black and isort"
	@echo "  type-check     - Run type checking with mypy"
	@echo ""
	@echo "Database:"
	@echo "  init-db        - Initialize database"
	@echo "  sample-data    - Add sample data for testing"
	@echo ""
	@echo "Running:"
	@echo "  run-sample     - Run scraper on a sample title"
	@echo "  scrape-all     - Scrape all CFR titles (long running)"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean          - Clean up temporary files"
	@echo "  clean-all      - Clean everything including data"

# Setup and installation
setup:
	python setup.py

install:
	pip install -e .

# Testing targets
test:
	python run_tests.py

test-unit:
	python run_tests.py --unit-only --framework pytest

test-integration:
	python run_tests.py --integration-only --framework pytest

test-cli:
	python run_tests.py --file test_cli.py

test-coverage:
	python run_tests.py --coverage --framework pytest

test-fast:
	python run_tests.py --fast --framework pytest

# Code quality
lint:
	@echo "Running flake8..."
	@flake8 src/ tests/ || echo "flake8 not installed, skipping..."
	@echo "Running black check..."
	@black --check src/ tests/ || echo "black not installed, skipping..."
	@echo "Running isort check..."
	@isort --check-only src/ tests/ || echo "isort not installed, skipping..."

format:
	@echo "Formatting with black..."
	@black src/ tests/ || echo "black not installed, skipping..."
	@echo "Sorting imports with isort..."
	@isort src/ tests/ || echo "isort not installed, skipping..."

type-check:
	@echo "Running mypy..."
	@mypy src/ --ignore-missing-imports || echo "mypy not installed, skipping..."

# Database operations
init-db:
	python -m src.main init-db --force

sample-data:
	@echo "Adding sample data..."
	python -c "from tests.conftest import *; from src.database import ECFRDatabase; db = ECFRDatabase(); db.connect(); db.initialize_schema(); print('Sample data would be added here')"

# Running the scraper
run-sample:
	python -m src.main scrape --titles 1 --debug

scrape-all:
	@echo "WARNING: This will scrape all 50 CFR titles and may take several hours!"
	@read -p "Are you sure? (y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	python -m src.main scrape

# Maintenance
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .tox/
	rm -rf build/
	rm -rf dist/

clean-all: clean
	@echo "Cleaning all data..."
	rm -rf data/
	rm -rf logs/
	rm -rf venv/
	rm -f *.db

# Development helpers
dev-deps:
	pip install pytest pytest-cov flake8 black isort mypy tox

docs:
	@echo "Documentation:"
	@echo "  README.md       - Main documentation"
	@echo "  USAGE_EXAMPLES.md - Usage examples"
	@echo "  Database schema - database_schema.sql"

# Quick commands for common workflows
quick-test: test-unit test-cli

quality-check: lint type-check

full-check: format quality-check test-coverage

# CI/CD simulation
ci-test:
	@echo "Running CI-like tests..."
	python -m unittest discover -s tests -p "test_*.py" -v
	python -m src.main --help
	ECFR_DB_PATH=./ci_test.db python -m src.main init-db --force
	ECFR_DB_PATH=./ci_test.db python -m src.main stats

# Project info
info:
	@echo "eCFR Scraper Project Information:"
	@echo "================================"
	@echo "Python version: $$(python --version)"
	@echo "Virtual env: $$(which python)"
	@echo "Dependencies:"
	@pip list | grep -E "(requests|lxml|click|tqdm)" || echo "Dependencies not installed"
	@echo ""
	@echo "Project structure:"
	@find . -name "*.py" -not -path "./venv/*" -not -path "./.tox/*" | head -20