"""
Quantum Microservice Client Interface.
Dispatches quantum circuit execution requests to the CUDA-Q microservice.
"""
import httpx
import logging
from typing import Dict, Any, List, Optional

from ..core.config import settings
from ..core.exceptions import CudaQUnavailableError, QuantumExecutionError

logger = logging.getLogger("zaslon.services.quantum")

_persistent_client: Optional[httpx.Client] = None
_persistent_async_client: Optional[httpx.AsyncClient] = None


def get_quantum_http_client() -> httpx.Client:
    global _persistent_client
    if _persistent_client is None or _persistent_client.is_closed:
        _persistent_client = httpx.Client(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
        )
    return _persistent_client


def get_quantum_async_client() -> httpx.AsyncClient:
    global _persistent_async_client
    if _persistent_async_client is None or _persistent_async_client.is_closed:
        _persistent_async_client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
        )
    return _persistent_async_client


class QuantumService:
    @staticmethod
    def check_health() -> Dict[str, Any]:
        """Checks quantum microservice reachability and CUDA-Q engine status using persistent client."""
        try:
            client = get_quantum_http_client()
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
        Sends a batch teleportation request to the CUDA-Q microservice using persistent keep-alive client.
        """
        url = f"{settings.QUANTUM_SERVICE_URL}/teleport/batch"
        payload = {
            "sha512_digest": sha512_digest,
            "start_index": start_index,
            "batch_size": batch_size,
            "total_count": total_count
        }

        global _persistent_client
        for attempt in range(2):
            try:
                client = get_quantum_http_client()
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
            except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError) as e:
                if _persistent_client and not _persistent_client.is_closed:
                    try:
                        _persistent_client.close()
                    except Exception:
                        pass
                _persistent_client = None
                if attempt == 1:
                    raise QuantumExecutionError(f"Failed to communicate with quantum microservice: {str(e)}")
            except Exception as e:
                raise QuantumExecutionError(f"Failed to communicate with quantum microservice: {str(e)}")

    @staticmethod
    async def execute_teleportation_batch_async(
        sha512_digest: str,
        start_index: int,
        batch_size: int,
        total_count: int = 4096
    ) -> Dict[str, Any]:
        """
        Asynchronously sends a batch teleportation request to the CUDA-Q microservice using persistent AsyncClient.
        """
        url = f"{settings.QUANTUM_SERVICE_URL}/teleport/batch"
        payload = {
            "sha512_digest": sha512_digest,
            "start_index": start_index,
            "batch_size": batch_size,
            "total_count": total_count
        }

        global _persistent_async_client
        for attempt in range(2):
            try:
                client = get_quantum_async_client()
                res = await client.post(url, json=payload)
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
            except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError) as e:
                if _persistent_async_client and not _persistent_async_client.is_closed:
                    try:
                        await _persistent_async_client.aclose()
                    except Exception:
                        pass
                _persistent_async_client = None
                if attempt == 1:
                    raise QuantumExecutionError(f"Failed to communicate with quantum microservice: {str(e)}")
            except Exception as e:
                raise QuantumExecutionError(f"Failed to communicate with quantum microservice: {str(e)}")
