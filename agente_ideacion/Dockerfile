FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY agente_ideacion/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copiar tools compartidas
COPY shared_tools/ /app/shared_tools/

# Copiar código del agente
COPY agente_ideacion/ /app/

EXPOSE 8000

CMD ["python", "main.py"]
