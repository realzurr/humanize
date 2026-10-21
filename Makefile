# =============================================================================
# Comandos auxiliares do Humaniza Acadêmico.
# Uso: make <alvo>   (executar a partir da raiz do repositório)
# =============================================================================

BACKEND := backend
FRONTEND := frontend
PY := $(BACKEND)/.venv/bin/python
UV := cd $(BACKEND) && uv

.DEFAULT_GOAL := help
.PHONY: help install install-backend install-frontend dev-backend dev-frontend \
        check test lint format typecheck coverage clean

help: ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# --- Instalação --------------------------------------------------------------

install: install-backend install-frontend ## Instala todas as dependências

install-backend: ## Cria o venv Python 3.12 e instala as dependências
	$(UV) venv --python 3.12
	$(UV) pip install -e "$(BACKEND)[dev]"

install-frontend: ## Instala as dependências do frontend
	cd $(FRONTEND) && npm install

# --- Desenvolvimento ----------------------------------------------------------

dev-backend: ## Sobe a API com recarga automática
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-frontend: ## Sobe o frontend em modo de desenvolvimento
	cd $(FRONTEND) && npm run dev

# --- Qualidade ---------------------------------------------------------------

check: lint format typecheck test ## Executa todas as verificações

lint: ## Ruff — lint
	cd $(BACKEND) && .venv/bin/ruff check .

format: ## Ruff — verifica formatação
	cd $(BACKEND) && .venv/bin/ruff format --check .

typecheck: ## Mypy — tipagem estrita
	cd $(BACKEND) && .venv/bin/mypy

test: ## Pytest
	cd $(BACKEND) && .venv/bin/python -m pytest

coverage: ## Pytest com relatório de cobertura
	cd $(BACKEND) && .venv/bin/python -m pytest --cov=app --cov-report=term-missing --cov-report=html

# --- Manutenção --------------------------------------------------------------

clean: ## Remove artefatos de build e cache
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache
	rm -rf $(BACKEND)/htmlcov $(BACKEND)/.coverage
	rm -rf $(FRONTEND)/dist $(FRONTEND)/node_modules/.vite
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
