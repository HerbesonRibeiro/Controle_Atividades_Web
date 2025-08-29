# Arquivo: utils/db.py
import os
import mysql.connector
from mysql.connector import pooling
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')

class Database:
    _pool = None

    def __init__(self):
        if Database._pool is None:
            self._initialize_pool()

    def _initialize_pool(self):
        try:
            logging.info("🔧 Criando pool de conexões com MySQL...")
            connection_url = os.environ.get('DATABASE_URL')
            if not connection_url:
                raise ValueError("A variável de ambiente DATABASE_URL não foi definida.")

            parts = connection_url.replace('mysql://', '').split('@')
            user_pass, host_port_db = parts[0], parts[1]
            user, password = user_pass.split(':')
            host_port, database = host_port_db.split('/')
            host, port = host_port.split(':')

            db_config = {
                'pool_name': "mypool", 'pool_size': 10, 'host': host,
                'port': port, 'user': user, 'password': password, 'database': database
            }

            Database._pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)
            logging.info("✅ Pool de conexões com MySQL criado com sucesso.")
        except Exception as e:
            logging.error(f"❌ Erro CRÍTICO ao criar o pool de conexões: {e}")
            Database._pool = None

    def get_connection(self):
        if self._pool is None:
            raise ConnectionError("Pool de conexões não inicializado.")
        return self._pool.get_connection()

    def execute_query(self, query, params=None, fetch=None):
        conn = None; cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(query, params or ())
            if fetch == 'one': return cursor.fetchone()
            elif fetch == 'all': return cursor.fetchall()
            else: conn.commit(); return cursor.rowcount
        except Exception as e:
            logging.error(f"❌ Erro ao executar query: {e}")
            if conn: conn.rollback()
            return None
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

db = Database()