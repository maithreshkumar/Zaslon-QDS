FROM nvcr.io/nvidia/quantum/cuda-quantum:cu12-0.15.1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    PYTHONPATH=/app/shared/backend:/app/Alice/backend:/app/Bob/backend:/app/Attack/backend

USER root
WORKDIR /app

COPY requirements-api.txt requirements-worker.txt /app/
RUN python -m pip install --no-cache-dir --requirement /app/requirements-worker.txt

ENV PYTHONHASHSEED=0 \
    ZASLON_CONTAINER_IMAGE=zaslon-qds-quantum-worker:cuda-quantum-cu12-0.15.1

RUN groupadd --system zaslon && \
    useradd --system --gid zaslon --create-home --shell /usr/sbin/nologin zaslon

COPY --chown=zaslon:zaslon shared/backend /app/shared/backend
COPY --chown=zaslon:zaslon Alice /app/Alice
COPY --chown=zaslon:zaslon Bob /app/Bob
COPY --chown=zaslon:zaslon Attack /app/Attack
COPY --chown=zaslon:zaslon scripts /app/scripts
COPY --chown=zaslon:zaslon compose.yaml requirements-api.txt requirements-worker.txt /app/
COPY --chown=zaslon:zaslon docker /app/docker
COPY --chown=zaslon:zaslon .env.example .env.auth.example /app/

USER zaslon:zaslon

# The NVIDIA base image launches commands through `bash -l`. Clear that
# inherited entrypoint so Compose exec-form commands run as actual executables.
ENTRYPOINT []
CMD ["python", "-m", "zaslon_shared.quantum_worker"]
