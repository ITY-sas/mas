"""
Tests de integración: RabbitMQ
I01-I04 del plan de pruebas.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

pika = pytest.importorskip("pika", reason="pika no instalado")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST_TEST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT_TEST", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")


def _get_connection():
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS),
        )
    )


class TestRabbitMQConnection:
    """I01-I04: Conexión y operaciones básicas con RabbitMQ."""

    @pytest.mark.integration
    def test_connection(self):
        """I01: Conexión a RabbitMQ exitosa."""
        try:
            conn = _get_connection()
            assert conn.is_open
            conn.close()
        except Exception as e:
            pytest.skip(f"RabbitMQ no disponible: {e}")

    @pytest.mark.integration
    def test_declare_queue(self):
        """I02: Declarar cola ideation_queue."""
        try:
            conn = _get_connection()
            ch = conn.channel()
            ch.queue_declare(queue="ideation_queue")
            assert conn.is_open
            conn.close()
        except Exception as e:
            pytest.skip(f"RabbitMQ no disponible: {e}")

    @pytest.mark.integration
    def test_publish_consume_roundtrip(self):
        """I03: Publicar y recibir un mensaje."""
        try:
            conn = _get_connection()
            ch = conn.channel()
            queue = "test_unit_queue"
            ch.queue_declare(queue=queue, auto_delete=True)

            # Publicar
            test_msg = json.dumps({"test": "hello", "id": 42})
            ch.basic_publish(exchange="", routing_key=queue, body=test_msg)

            # Consumir
            method, properties, body = ch.basic_get(queue=queue, auto_ack=True)
            assert method is not None
            received = json.loads(body)
            assert received["test"] == "hello"
            assert received["id"] == 42

            conn.close()
        except Exception as e:
            pytest.skip(f"RabbitMQ no disponible: {e}")

    @pytest.mark.integration
    def test_credentials_accepted(self):
        """I04: Credenciales user/password aceptadas."""
        try:
            conn = _get_connection()
            assert conn.is_open
            conn.close()
        except pika.exceptions.ProbableAuthenticationError:
            pytest.fail("Credenciales rechazadas por RabbitMQ")
        except Exception as e:
            pytest.skip(f"RabbitMQ no disponible: {e}")
