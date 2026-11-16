# Desenvolvimento: FastAPI com uvicorn --reload.
# O codigo entra por bind mount (ver docker-compose.yml); a imagem so traz as dependencias.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_LINK_MODE=copy

# Dependencias primeiro, para a cache sobreviver a mudancas no codigo.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

# Modulo e objeto FastAPI a arrancar; muda-se no docker-compose.yml se o codigo for outro.
ENV APP_MODULE=backend.main:app
EXPOSE 8000
CMD ["sh", "-c", "uv run uvicorn \"$APP_MODULE\" --host 0.0.0.0 --port 8000 --reload --app-dir src"]
