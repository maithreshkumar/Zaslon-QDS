from fastapi import APIRouter, Depends, HTTPException

from zaslon_shared.auth import require_roles
from zaslon_shared.dispatch import (
    attack as dispatch_attack,
    detector_benchmark as dispatch_detector_benchmark,
    multiverifier_benchmark as dispatch_multiverifier_benchmark,
    network_experiment as dispatch_network_experiment,
)
from zaslon_shared.job_queue import JobFailed, JobTimedOut
from zaslon_shared.schemas import (
    AttackRunRequest,
    DetectorBenchmarkRequest,
    MultiVerifierExperimentRequest,
    NetworkExperimentRequest,
)
from zaslon_shared.runtime import AdmissionRejected
from .base import list_experiments

router = APIRouter(
    prefix="/api/v1/attacks",
    tags=["Attack laboratory"],
    dependencies=[Depends(require_roles("ATTACK"))],
)


@router.post("/runs")
def execute(request: AttackRunRequest):
    try:
        return dispatch_attack(request)
    except JobTimedOut as exc:
        raise HTTPException(202, {"job_id": exc.job_id, "status": "RUNNING"}) from exc
    except JobFailed as exc:
        raise HTTPException(503, {"job_id": exc.job_id, "code": exc.code}) from exc
    except AdmissionRejected as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "2"}) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/runs")
def history():
    return {"items": list_experiments()}


@router.post("/benchmarks/channel")
def channel_benchmark(request: DetectorBenchmarkRequest):
    try:
        return dispatch_detector_benchmark(request.model_dump(mode="json"))
    except JobTimedOut as exc:
        raise HTTPException(202, {"job_id": exc.job_id, "status": "RUNNING"}) from exc
    except JobFailed as exc:
        raise HTTPException(503, {"job_id": exc.job_id, "code": exc.code}) from exc
    except AdmissionRejected as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "2"}) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/benchmarks/multiverifier")
def multiverifier_benchmark(request: MultiVerifierExperimentRequest):
    try:
        return dispatch_multiverifier_benchmark(request.model_dump(mode="json"))
    except JobTimedOut as exc:
        raise HTTPException(202, {"job_id": exc.job_id, "status": "RUNNING"}) from exc
    except JobFailed as exc:
        raise HTTPException(503, {"job_id": exc.job_id, "code": exc.code}) from exc
    except AdmissionRejected as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "2"}) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/network")
def network_experiment(request: NetworkExperimentRequest):
    try:
        return dispatch_network_experiment(request.model_dump(mode="json"))
    except JobTimedOut as exc:
        raise HTTPException(202, {"job_id": exc.job_id, "status": "RUNNING"}) from exc
    except JobFailed as exc:
        raise HTTPException(503, {"job_id": exc.job_id, "code": exc.code}) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
