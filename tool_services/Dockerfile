# Dockerfile paramétrico para los 6 tool services.
# El servicio se selecciona con el build arg TOOL_DIR (p.ej. tool_client).
FROM python:3.11-slim

ARG TOOL_DIR

WORKDIR /app

COPY tool_services/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Kernel común (contratos, eventos, RPC) + dominio (queries SQL/RSS)
COPY common/ /app/common/
COPY shared_tools/ /app/shared_tools/

# Código del servicio concreto
COPY tool_services/${TOOL_DIR}/ /app/

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
