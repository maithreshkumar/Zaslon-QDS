from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_compose_has_pinned_local_only_four_service_runtime():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert {
        "frontend",
        "api",
        "quantum-worker",
        "mysql",
        "migrate",
        "secrets-init",
    } <= services.keys()
    assert services["mysql"]["image"] == "mysql:9.7.2"
    assert "ports" not in services["mysql"]
    assert "mysql_data:/var/lib/mysql" in services["mysql"]["volumes"]
    assert "local_secrets:/run/secrets/zaslon:ro" in services["mysql"]["volumes"]
    assert services["quantum-worker"]["gpus"] == "all"
    assert "ports" not in services["quantum-worker"]
    assert services["api"]["ports"] == ["127.0.0.1:8000:8000"]
    assert all(port.startswith("127.0.0.1:") for port in services["frontend"]["ports"])
    assert compose["networks"]["backend"]["internal"] is True
    assert set(services["api"]["networks"]) == {"backend", "edge"}
    assert set(services["frontend"]["networks"]) == {"backend", "edge"}
    assert compose["volumes"]["local_secrets"]["name"] == "zaslon_local_secrets"
    assert (
        services["mysql"]["environment"]["MYSQL_ROOT_PASSWORD_FILE"]
        == "/run/secrets/zaslon/db_root_password"
    )
    for service in services.values():
        assert service.get("privileged") is not True
        assert not any("docker.sock" in volume for volume in service.get("volumes", []))


def test_worker_uses_pinned_official_cudaq_image_and_api_has_no_cudaq_dependency():
    worker = (ROOT / "docker" / "quantum-worker.Dockerfile").read_text(encoding="utf-8")
    api_requirements = (ROOT / "requirements-api.txt").read_text(encoding="utf-8")
    worker_requirements = (ROOT / "requirements-worker.txt").read_text(encoding="utf-8")
    assert worker.startswith("FROM nvcr.io/nvidia/quantum/cuda-quantum:cu12-0.15.1")
    assert "ENTRYPOINT []" in worker
    assert "cudaq" not in api_requirements.lower()
    assert "numpy==2.2.6" in api_requirements
    assert "sequence==0.7.6" in worker_requirements
    assert "qiskit-aer==0.17.2" in worker_requirements


def test_frontend_proxy_keeps_role_credentials_out_of_built_javascript():
    dockerfile = (ROOT / "docker" / "frontend.Dockerfile").read_text(encoding="utf-8")
    nginx = (ROOT / "docker" / "nginx.conf.template").read_text(encoding="utf-8")
    assert "ENV VITE_API_URL=/api/v1" in dockerfile
    assert "VITE_ZASLON_API_KEY" not in dockerfile
    assert "X-ZASLON-API-Key" in nginx
    assert "location ^~ /api/ { return 403; }" in nginx
