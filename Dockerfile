FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN useradd --create-home --uid 1000 user \
    && pip install --no-cache-dir uv==0.11.29

WORKDIR /app

COPY --chown=user:user pyproject.toml uv.lock README.md ./

USER user

RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=user:user main.py ./
COPY --chown=user:user persian_morphology ./persian_morphology
COPY --chown=user:user static ./static
COPY --chown=user:user fst/artifacts ./fst/artifacts

RUN uv sync --frozen --no-dev \
    && test -s fst/artifacts/analyzer.hfstol \
    && test -s fst/artifacts/generator.hfstol

ENV HOME=/home/user \
    PATH="/app/.venv/bin:${PATH}"

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=2).read()"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
