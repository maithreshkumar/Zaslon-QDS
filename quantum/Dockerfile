FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python packages including cuda-quantum on Linux
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV QUANTUM_HOST=0.0.0.0
ENV QUANTUM_PORT=8001

EXPOSE 8001

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8001"]
