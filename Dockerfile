# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install -e .

EXPOSE 8501

# Run migrations then launch Streamlit.
CMD bash -lc "python -m alembic upgrade head && \
    streamlit run src/planner/ui/app.py \
        --server.port=8501 \
        --server.address=0.0.0.0 \
        --server.headless=true"
