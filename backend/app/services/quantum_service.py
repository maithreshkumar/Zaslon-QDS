"""
Quantum Microservice Client Interface.
Dispatches quantum circuit execution requests to the CUDA-Q microservice.
"""
import httpx
import logging
from typing import Dict, Any, List

from ..core.config import settings
from ..core.exceptions import CudaQUnavailableError, QuantumExecutionError

logger = logging.getLogger("zaslon.services.quantum")


class QuantumService:
    @staticmethod
    def check_health() -> Dict[str, Any]:
        """Checks quantum microservice reachability and CUDA-Q engine status."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{settings.QUANTUM_SERVICE_URL}/health")
                if res.status_code == 200:
                    return res.json()
                return {"status": "UNHEALTHY", "code": res.status_code}
        except Exception as e:
            logger.warning(f"Failed to connect to quantum microservice: {str(e)}")
            return {"status": "UNREACHABLE", "error": str(e)}

    @staticmethod
    def execute_teleportation_batch(
        sha512_digest: str,
        start_index: int,
        batch_size: int,
        total_count: int = 4096
    ) -> Dict[str, Any]:
        """
        Sends a batch teleportation request to the CUDA-Q microservice.
        """
        url = f"{settings.QUANTUM_SERVICE_URL}/teleport/batch"
        payload = {
            "sha512_digest": sha512_digest,
            "start_index": start_index,
            "batch_size": batch_size,
            "total_count": total_count
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json()["data"]
                elif res.status_code == 503:
                    detail = res.json().get("detail", "CUDA-Q unavailable")
                    raise CudaQUnavailableError(detail)
                else:
                    detail = res.json().get("detail", "Unknown quantum error")
                    raise QuantumExecutionError(f"Quantum execution failed: {detail}")
        except (CudaQUnavailableError, QuantumExecutionError):
            raise
        except Exception as e:
            raise QuantumExecutionError(f"Failed to communicate with quantum microservice: {str(e)}")
