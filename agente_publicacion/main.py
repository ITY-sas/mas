import asyncio
import pika
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Idea(BaseModel):
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
    channel.queue_declare(queue='publication_queue')

    def callback(ch, method, properties, body):
        idea = Idea.parse_raw(body)
        print(f"Received idea: {idea.content}")
        # Aquí iría la lógica de procesamiento de la idea
        # ...

    channel.basic_consume(queue='publication_queue', on_message_callback=callback, auto_ack=True)
    print('Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == "__main__":
    asyncio.run(consume_messages())
