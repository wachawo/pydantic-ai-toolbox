.DEFAULT_GOAL := help

.PHONY: help install sync format lint typecheck mypy pyright test test-cov docs docs-serve build clean

help:
	@echo "make install      install runtime deps + all extras"
	@echo "make sync         resolve and install with uv (dev + lint + docs)"
	@echo "make format       run black + ruff --fix"
	@echo "make lint         run ruff + black --check"
	@echo "make typecheck    run mypy + pyright"
	@echo "make mypy         run mypy only"
	@echo "make pyright      run pyright only"
	@echo "make test         run pytest (with coverage gate)"
	@echo "make test-cov     run pytest with coverage and missing-line report"
	@echo "make docs         build MkDocs site"
	@echo "make docs-serve   serve MkDocs site locally"
	@echo "make build        build wheel + sdist"
	@echo "make clean        remove build artefacts and caches"

install:
	pip install -e ".[all]"

sync:
	uv sync --all-extras --all-groups

format:
	black pydantic_ai_toolkits tests examples
	ruff check --fix pydantic_ai_toolkits tests examples

lint:
	ruff check pydantic_ai_toolkits tests examples
	black --check pydantic_ai_toolkits tests examples

typecheck: mypy

mypy:
	mypy pydantic_ai_toolkits

pyright:
	pyright pydantic_ai_toolkits tests

test:
	pytest

test-cov:
	pytest --cov=pydantic_ai_toolkits --cov-report=term-missing --cov-report=html

docs:
	mkdocs build --strict

docs-serve:
	mkdocs serve

build:
	python -m build

clean:
	rm -rf build dist site .ruff_cache .pytest_cache .mypy_cache .pyright .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
