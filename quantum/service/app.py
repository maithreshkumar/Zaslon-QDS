"""
FastAPI application for the Quantum Engine Microservice.
Exposes REST endpoints for CUDA-Q 3-qubit teleportation execution and state mapping.
"""
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os

from .engine import QuantumTeleportationEngine
from .circuits.state_prep import derive_teleportation_parameters
from .network.simulator import simulate_qds_network

app = FastAPI(
    title="Zaslon-QDS Quantum Engine Microservice",
    description="Dedicated microservice for NVIDIA CUDA-Q 3-qubit quantum teleportation execution and SeQUeNCe network simulation.",
    version="1.0.0"
)

target_backend = os.getenv("CUDA_TARGET", "default")
engine = QuantumTeleportationEngine(target_backend=target_backend)


class NetworkSimulateRequest(BaseModel):
    total_operations: int = Field(4096, ge=1)
    fiber_distance_km: float = Field(25.0, ge=0.1, le=1000.0)
    active_attack: Optional[str] = None


class TeleportBatchRequest(BaseModel):
    sha512_digest: str = Field(..., min_length=128, max_length=128, description="Hexadecimal SHA-512 digest")
    start_index: int = Field(0, ge=0)
    batch_size: int = Field(512, ge=1, le=4096)
    total_count: int = Field(4096, ge=1)


class ParameterGenerationRequest(BaseModel):
    sha512_digest: str = Field(..., min_length=128, max_length=128)
    total_count: int = Field(4096, ge=1)


@app.get("/health", tags=["Health"])
def health_check():
    availability = engine.check_availability()
    return {
        "service": "zaslon-quantum-service",
        "status": "HEALTHY" if availability["cuda_q_available"] else "DEGRADED",
        "quantum_engine": availability
    }


@app.get("/status", tags=["Status"])
def get_status():
    return engine.check_availability()


@app.post("/teleport/parameters", tags=["State Preparation"])
def generate_parameters(req: ParameterGenerationRequest):
    try:
        params = derive_teleportation_parameters(req.sha512_digest, total_count=req.total_count)
        return {
            "success": True,
            "total_count": len(params),
            "parameters": params[:50],  # preview sample
            "full_count": len(params)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameter generation failed: {str(e)}"
        )


@app.post("/teleport/batch", tags=["Quantum Teleportation"])
def execute_batch(req: TeleportBatchRequest):
    try:
        batch_result = engine.execute_batch(
            sha512_digest=req.sha512_digest,
            start_index=req.start_index,
            batch_size=req.batch_size,
            total_count=req.total_count
        )
        return {
            "success": True,
            "data": batch_result
        }
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(re)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch execution error: {str(e)}"
        )


@app.post("/network/simulate", tags=["Quantum Network"])
def simulate_network(req: NetworkSimulateRequest):
    try:
        res = simulate_qds_network(
            total_operations=req.total_operations,
            fiber_distance_km=req.fiber_distance_km,
            active_attack=req.active_attack
        )
        return {
            "success": True,
            "simulation": res
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Network simulation error: {str(e)}"
        )
