import pika
import time

def publish_brief():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='ideation_queue')

    brief = {
        "client_id": 1,
        "content": "Generate an idea for a new product"
    }

    channel.basic_publish(exchange='',
                          routing_key='ideation_queue',
                          body=str(brief))

    print(" [x] Sent brief")
    connection.close()

if __name__ == "__main__":
    publish_brief()
    time.sleep(10)  # Esperar a que se procese el brief
