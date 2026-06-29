FROM docker.io/python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY app ./app

RUN uv sync --frozen --no-dev

EXPOSE 8080

# --no-dev keeps the runtime env in sync with the build (no pyright/ruff re-download on cold start)
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
