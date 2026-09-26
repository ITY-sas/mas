FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY orchestrator/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Kernel común: eventos, contrato de tools, TaskStore (SIN shared_tools:
# el orquestador no ejecuta código de negocio — es stateless)
COPY common/ /app/common/

# Copiar código del orquestador
COPY orchestrator/ /app/

EXPOSE 8002

CMD ["python", "main.py"]
