# =============================================================================
# Backend — Humaniza Acadêmico
# =============================================================================
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Ferramentas de sistema necessárias:
#  - curl: health check
#  - fonts: renderização de PDF com LibreOffice (opcional)
RUN apt-get update && apt-get install --no-install-recommends -y \
        curl \
        fonts-liberation \
        libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

# Extras opcionais separados por vírgula (ex.: "redis" ou "redis,pdf").
ARG EXTRAS=""

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install ".${EXTRAS:+[$EXTRAS]}"

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
