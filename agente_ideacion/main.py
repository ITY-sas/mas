import asyncio
import pika
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel

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
