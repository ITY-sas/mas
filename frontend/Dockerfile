FROM python:3.10-slim

WORKDIR /app

COPY frontend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY frontend/ /app/frontend/

ENV PORT=3000
EXPOSE 3000

CMD ["python", "-m", "uvicorn", "frontend.server:app", "--host", "0.0.0.0", "--port", "3000"]
