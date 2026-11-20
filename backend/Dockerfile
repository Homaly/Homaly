# Desenvolvimento: FastAPI com uvicorn --reload.
# O codigo entra por bind mount (ver docker-compose.yml); a imagem so traz as dependencias.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_LINK_MODE=copy

# ffmpeg: as imagens e o detetor de movimento da camara (US13, backend/src/backend/camara.py).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Dependencias primeiro, para a cache sobreviver a mudancas no codigo.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

# Modulo e objeto FastAPI a arrancar; muda-se no docker-compose.yml se o codigo for outro.
ENV APP_MODULE=backend.main:app
EXPOSE 8000
# RECARREGAR=0 (no .env) arranca sem --reload: na demo, gravar um ficheiro nao reinicia o backend.
CMD ["sh", "-c", "if [ \"${RECARREGAR:-1}\" = 1 ]; then R=--reload; fi; exec uv run uvicorn \"$APP_MODULE\" --host 0.0.0.0 --port 8000 $R --app-dir src"]
