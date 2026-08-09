# Base pinned by digest (LAV-52/L-4). Digest resolved from the local image cache
# (docker images --digests) — daemon-side pulls to Docker Hub are IPv6-blackholed,
# so this is the verified repo digest of python:3.14-slim-bookworm as cached.
FROM docker.io/python:3.14-slim-bookworm@sha256:4ff4b92a68355dbdb52584ab3391dff8d371a61d4e063468bfd0130e3189c6d9

# uv binary, also pinned by digest (resolved from the local cache of ghcr.io/astral-sh/uv:latest).
COPY --from=ghcr.io/astral-sh/uv@sha256:99ea34acedc870ba4ad11a1f540a1c04267c9f30aadc465a94406f52dfda2c36 /uv /bin/uv

# Non-root runtime user (LAV-48/M-1). Fixed uid/gid 10001 so Kubernetes
# runAsNonRoot/fsGroup defaults in helm/lavs/values.yaml line up with the image.
RUN groupadd --gid 10001 lavs \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin lavs

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY app ./app

# Install deps, then hand the whole tree to the runtime user: the embedded DuckDB
# writes its file (and WAL) under the app package dir (/app/app/test.db by default,
# see app/configurations/root_dir.py), and `uv run` needs the venv writable.
RUN uv sync --frozen --no-dev \
    && chown -R lavs:lavs /app

USER 10001:10001
ENV HOME=/home/lavs

EXPOSE 8080

# Container-level liveness (LAV-52). curl is not in the slim image; python is.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4).status == 200 else 1)"]

# --no-dev keeps the runtime env in sync with the build (no pyright/ruff re-download on cold start)
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
