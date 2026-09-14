FROM python:3.12.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    PYTHONPATH=/app/shared/backend:/app/Alice/backend:/app/Bob/backend:/app/Attack/backend

WORKDIR /app

COPY requirements-api.txt /app/requirements-api.txt
RUN python -m pip install --no-cache-dir --requirement /app/requirements-api.txt

ENV PYTHONHASHSEED=0 \
    ZASLON_CONTAINER_IMAGE=zaslon-qds-api:python-3.12.10-slim-bookworm

RUN groupadd --gid 10001 zaslon && \
    useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin zaslon

COPY --chown=10001:10001 shared/backend /app/shared/backend
COPY --chown=10001:10001 Alice /app/Alice
COPY --chown=10001:10001 Bob /app/Bob
COPY --chown=10001:10001 Attack /app/Attack
COPY --chown=10001:10001 scripts /app/scripts
COPY --chown=10001:10001 compose.yaml /app/compose.yaml
COPY --chown=10001:10001 docker /app/docker
COPY --chown=10001:10001 requirements-worker.txt /app/requirements-worker.txt
COPY --chown=10001:10001 .env.example .env.auth.example /app/

USER 10001:10001

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "shared/backend", "--host", "0.0.0.0", "--port", "8000"]
