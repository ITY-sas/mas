FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY agente_ideacion/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Kernel común: eventos + runner + Tool Discovery.
# NO se copia shared_tools: el agente no ejecuta código de negocio.
COPY common/ /app/common/

# Copiar código del agente
COPY agente_ideacion/ /app/agente_ideacion/

EXPOSE 8000

CMD ["python", "-m", "agente_ideacion"]
