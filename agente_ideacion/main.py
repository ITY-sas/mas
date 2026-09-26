import asyncio
import pika
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel
import logging
import time

app = FastAPI()

class Brief(BaseModel):
    client_id: int
    content: str

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    return {"metrics": "data"}

def autocorrect(func):
    def wrapper(*args, **kwargs):
        attempts = 0
        while attempts < 5:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error: {e}")
                time.sleep(1)
                attempts += 1
        logging.error("Max attempts reached. Documenting the issue.")
        with open("INFORME_BLOQUEOS.md", "a") as f:
            f.write(f"Error: {e}\n")
    return wrapper

@autocorrect
async def consume_messages():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='ideation_queue')

    def callback(ch, method, properties, body):
        brief = Brief.parse_raw(body)
        print(f"Received brief: {brief.content}")
        # Aquí iría la lógica de procesamiento del brief
        # ...

    channel.basic_consume(queue='ideation_queue', on_message_callback=callback, auto_ack=True)
    print('Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == "__main__":
    asyncio.run(consume_messages())
