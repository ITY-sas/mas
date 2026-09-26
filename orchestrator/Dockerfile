FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY orchestrator/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copiar tools compartidas
COPY shared_tools/ /app/shared_tools/

# Copiar código del orquestador
COPY orchestrator/ /app/

EXPOSE 8002

CMD ["python", "main.py"]
