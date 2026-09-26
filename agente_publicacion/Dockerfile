FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY agente_publicacion/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copiar tools compartidas
COPY shared_tools/ /app/shared_tools/

# Copiar código del agente
COPY agente_publicacion/ /app/

EXPOSE 8001

CMD ["python", "main.py"]
