import psycopg2
from psycopg2.extras import RealDictCursor

class Memoria:
    def __init__(self):
        self.connection = psycopg2.connect(
            dbname="ideation_db",
            user="postgres",
            password="password",
            host="postgres"
        )

    def save_idea(self, client_id, content):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute("INSERT INTO ideas_generadas (client_id, content) VALUES (%s, %s)", (client_id, content))
        self.connection.commit()
        cursor.close()
