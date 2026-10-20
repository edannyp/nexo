# API de Nexo. Contexto de construcción: apps/api
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1

WORKDIR /app
# Dependencias primero: la capa se reutiliza mientras no cambie uv.lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --system --no-create-home nexo
USER nexo
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/salud')"

# Con NEXO_MIGRAR_AL_ARRANCAR=true aplica las migraciones pendientes antes de arrancar (ADR 0016).
CMD ["sh", "-c", "if [ \"$NEXO_MIGRAR_AL_ARRANCAR\" = true ]; then alembic upgrade head; fi && exec uvicorn nexo_api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'"]
