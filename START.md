# Start ZASLON-QDS

Docker Compose is the primary supported runtime. Docker Desktop may use WSL2
internally on Windows 11, but you do not activate a WSL virtual environment,
install CUDA-Q in Ubuntu, or start Uvicorn/Vite manually.

## What Docker starts

| Compose service | Container | Purpose | Host access |
| --- | --- | --- | --- |
| `mysql` | `zaslon-mysql` | MySQL 9.7.2 system of record | Not published |
| `migrate` | `zaslon-migrate` | Applies versioned schema migrations and exits | Internal only |
| `api` | `zaslon-api` | FastAPI, authorization, job submission, result retrieval | `127.0.0.1:8000` |
| `quantum-worker` | `zaslon-quantum-worker` | CUDA-Q, SeQUeNCe, attacks, and quantum statistics | Internal only |
| `frontend` | `zaslon-frontend` | Alice, Attack, and Bob interfaces | `127.0.0.1:5173-5175` |

The API and worker exchange encrypted job payloads through MySQL. Qiskit Aer is
installed in the worker for validation only; it is not a runtime fallback.
The internal `backend` network contains MySQL and the worker. A separate `edge`
network gives only the API and frontend a host-reachable path; MySQL and worker
ports remain unpublished.

## 1. Install the prerequisites once

Install:

- Docker Desktop for Windows with its WSL2 backend enabled.
- A current NVIDIA Windows driver that supports WSL2 GPU compute.
- Git only if the project is being cloned rather than copied.

Start Docker Desktop and wait until it reports that the engine is running. From
PowerShell in this project folder, verify Docker:

```powershell
docker version
docker compose version
```

If PowerShell says `docker` is not recognized, Docker Desktop is either not
installed, not running, or the terminal was opened before installation. Start
Docker Desktop and open a new PowerShell window.

## 2. Verify Docker can see the NVIDIA GPU

Run this before debugging CUDA-Q:

```powershell
docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

The command must show the NVIDIA GPU from inside the container. Merely importing
CUDA-Q is not proof that GPU execution works.

## 3. Local secrets

No manual secret setup is required for a new local Docker installation. A one-shot
`secrets-init` container generates separate random database passwords, three role
keys, a Fernet queue key, and an artifact-attestation key on first startup. It stores them in the private named
volume `zaslon_local_secrets`, never in an image or browser bundle. Existing values
are preserved on later starts.

The application connects as `zaslon_app`, never as MySQL `root`.

To supply your own values instead, copy the templates before the first startup:

```powershell
Copy-Item .env.example .env
Copy-Item .env.auth.example .env.auth
```

Replace the database placeholders in `.env`, keeping the application and root
passwords different. Replace all five placeholders in `.env.auth`. Generate each
role key with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Run that command three times and assign a different value to Alice, Bob, and
Attack. Generate the queue encryption key with:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If host Python does not have `cryptography`, generate the Fernet key without
installing anything on Windows:

```powershell
docker run --rm python:3.12.10-slim-bookworm sh -c "pip install --quiet cryptography==50.0.1 && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
```

Never paste real keys into `compose.yaml`, a Dockerfile, source code, screenshots,
or Git. User-supplied values are copied into the private volume only when each
corresponding volume file does not already exist.

## 4. Validate and start the complete application

The first build downloads the CUDA-Q image and scientific Python packages, so it
can take considerably longer than later starts.

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Startup is health-driven:

```text
MySQL healthy
  -> migration job completes
  -> API and quantum worker start
  -> CUDA-Q known-state and Bell diagnostic execute
  -> frontend starts after the API is healthy
```

No arbitrary sleep delay and no manual MySQL table creation are required.

## 5. Open the interfaces

- Alice: <http://127.0.0.1:5173/>
- Attack Lab: <http://127.0.0.1:5174/>
- Bob: <http://127.0.0.1:5175/>
- API health: <http://127.0.0.1:8000/api/v1/health>
- API documentation: <http://127.0.0.1:8000/docs>

The frontend proxy injects only the credential for its role and blocks other role
route families. Role credentials are never compiled into browser JavaScript.

## 6. Check health and logs

```powershell
docker compose ps
docker compose logs --tail 100 api
docker compose logs --tail 100 quantum-worker
docker compose logs --tail 100 mysql
```

Follow logs only when actively diagnosing something:

```powershell
docker compose logs -f quantum-worker
```

Press `Ctrl+C` to stop following logs; this does not stop the container.

The API health response distinguishes process, CUDA-Q, GPU, selected target, and
fallback status. Expected GPU execution reports `execution_target: "nvidia"`,
`gpu: "AVAILABLE"`, and `fallback_used: false`. Do not infer GPU use from the
image name.

## 7. Run validation and tests

Complete isolated backend/scientific/security suite (uses the already-built
worker image so CUDA-Q, Qiskit Aer, and SeQUeNCe are all available, while its
temporary SQLite database stays outside the application MySQL data):

```powershell
docker run --rm --gpus all --entrypoint pytest zaslon-qds-quantum-worker Attack/backend/tests shared/backend/tests -q -o cache_dir=/tmp/pytest-cache
```

CUDA-Q verification and Qiskit Aer cross-validation:

```powershell
docker compose exec quantum-worker python scripts/verify_cudaq.py
```

Focused quantum and network tests:

```powershell
docker compose exec quantum-worker pytest shared/backend/tests/test_teleportation_regression.py shared/backend/tests/test_sequence_network.py -q -o cache_dir=/tmp/pytest-cache
```

Live end-to-end acceptance test:

```powershell
docker compose exec api python scripts/docker_acceptance.py
```

The acceptance test creates one real MySQL session, generates and downloads a
basis-aware `.qds.json` artifact in memory, consumes it with Bob's one-time
verification, runs baseline/intercept/phase/correction/forgery/impersonation/replay
checks, validates Bob/Charlie SeQUeNCe networking, checks decryption, and verifies
cross-role proxy blocking.

Qiskit Aer is invoked only by validation paths and tests. It never silently
replaces CUDA-Q when CUDA-Q fails.

## 8. Normal stop, restart, and data persistence

Stop safely:

```powershell
docker compose down
```

Start again without rebuilding unchanged images:

```powershell
docker compose up -d
```

MySQL records remain in `zaslon_mysql_data`, and generated local credentials remain
in `zaslon_local_secrets`, across `down`, host restarts, and container replacement.

Do not run the following unless you intentionally want to permanently erase the
Docker development database:

```powershell
docker compose down -v
```

The application never runs that destructive command automatically.

## 9. Rebuild after source or dependency changes

```powershell
docker compose build
docker compose up -d
```

To rebuild only one component:

```powershell
docker compose build quantum-worker
docker compose up -d quantum-worker
```

## 10. CUDA-Q CPU fallback policy

The normal Compose configuration requests the NVIDIA CUDA-Q target and passes the
GPU into the worker. If the container can start but the NVIDIA target cannot be
initialized, CPU fallback occurs only when this explicit policy is set in `.env`:

```text
ZASLON_ALLOW_CUDAQ_CPU_FALLBACK=true
```

Fallback uses CUDA-Q `qpp-cpu` and is reported with:

```json
{
  "engine": "CUDA-Q",
  "target": "qpp-cpu",
  "gpu": false,
  "fallback_used": true,
  "fallback_reason": "CUDA_Q_GPU_TARGET_UNAVAILABLE"
}
```

It does not fall back to Qiskit Aer. A machine with no usable Docker GPU device
may require a Docker-only CPU Compose override; do not remove GPU configuration
from the primary research deployment merely to hide a GPU setup failure.

## 11. Common failures

### A service remains unhealthy

```powershell
docker compose ps
docker compose logs --tail 200 <service-name>
```

Use `mysql`, `migrate`, `api`, `quantum-worker`, or `frontend` as the service name.

### CUDA-Q reports unavailable

First repeat the GPU pre-flight test. Then inspect:

```powershell
docker compose logs --tail 200 quantum-worker
docker compose run --rm quantum-worker python scripts/verify_cudaq.py
```

The worker fails closed with `QUANTUM_BACKEND_UNAVAILABLE`; it does not fabricate
quantum results.

### MySQL authentication fails

Inspect `docker compose logs secrets-init` and `docker compose logs mysql`.
User-supplied MySQL initialization values apply only when both the corresponding
secret file and database data directory are new. Preserve existing data and
correct the account rather than casually deleting volumes.

### A role receives HTTP 401 or 403

Confirm `.env.auth` contains three different role keys and then recreate the API
and frontend containers:

```powershell
docker compose up -d --force-recreate api frontend
```

### A quantum request remains queued

```powershell
docker compose ps quantum-worker
docker compose logs --tail 200 quantum-worker
```

The queue is persisted in MySQL and recovers stale claimed jobs after a worker
restart. Do not submit replacement jobs repeatedly while diagnosing the worker.

## 12. Manual WSL status

The previous `.venv-wsl` setup may remain on this development computer for
low-level debugging, but it is not the primary supported runtime and is not
required to start ZASLON-QDS. Do not run the Docker stack and the old manual stack
on the same ports at the same time.

The supported complete startup command is:

```powershell
docker compose up -d --build
```
