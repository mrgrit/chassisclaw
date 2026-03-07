FROM python:3.12-slim

# 필수 운영 툴(워크플로우 기본 커맨드용)
# - uptime: procps
# - ss: iproute2
# - coreutils: 기본 유틸
# - ca-certificates/curl: 내부/외부 호출, TLS
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps iproute2 coreutils ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 55123
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "55123"]
