FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY llm_gateway/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copiar el código del gateway
COPY llm_gateway/ /app/

EXPOSE 8003

CMD ["python", "main.py"]
