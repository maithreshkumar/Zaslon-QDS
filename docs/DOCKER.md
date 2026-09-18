# Docker & Deployment Architecture — Zaslon-QDS

Multi-Container Topology, Environment Variables, and Startup Guide for SIH 26141.

---

## 1. Multi-Container Topology

Zaslon-QDS runs via `docker compose up --build` with 4 dedicated containers:

```text
┌─────────────────┐       ┌─────────────────┐
│     frontend    │       │     backend     │
│   (Port: 3000)  │──────▶│   (Port: 8000)  │
│  (Nginx + React)│       │    (FastAPI)    │
└─────────────────┘       └────────┬────────┘
                                   │
                 ┌─────────────────┴─────────────────┐
                 │                                   │
                 ▼                                   ▼
        ┌─────────────────┐                 ┌─────────────────┐
        │ quantum-service │                 │     mysql-db    │
        │   (Port: 8001)  │                 │   (Port: 3306)  │
        │(CUDA-Q / Python)│                 │   (MySQL 8.0)   │
        └─────────────────┘                 └─────────────────┘
```

---

## 2. Ports and Network Bindings

| Service | Internal Port | Host Port | Description |
| :--- | :--- | :--- | :--- |
| **frontend** | 80 | 3000 | React UI served by Nginx |
| **backend** | 8000 | 8000 | FastAPI REST Application |
| **quantum-service** | 8001 | 8001 | CUDA-Q Execution Microservice |
| **mysql-db** | 3306 | 3306 | MySQL 8.0 Relational Persistence |

All containers are linked on the private bridge network `zaslon-net`.

---

## 3. Quickstart Guide

### 1. Configure Environment
```bash
cp .env.example .env
```

### 2. Launch Entire Platform
```bash
docker compose up --build -d
```

### 3. Check Health
```bash
curl http://localhost:8000/api/v1/health
```

### 4. Access UI
Navigate to [http://localhost:3000](http://localhost:3000) in your web browser.
