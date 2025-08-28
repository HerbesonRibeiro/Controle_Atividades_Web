# Arquivo: utils/db.py (VERSÃO FINAL PARA POSTGRESQL/NEON)

import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
import psycopg2.pool
from psycopg2 import extras, OperationalError
import threading

# Configuração do logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s")
logger = logging.getLogger(__name__)

# Carrega as variáveis de ambiente de forma segura
try:
    if getattr(sys, 'frozen', False):
        # Se estiver rodando como um executável (PyInstaller)
        base_path = Path(sys.executable).parent
    else:
        # Se estiver rodando como um script .py
        base_path = Path(__file__).resolve().parent.parent

    dotenv_path = base_path / ".env"
    load_dotenv(dotenv_path)
    logger.info(f"Arquivo .env carregado de: {dotenv_path}")
except Exception as e:
    logger.error(f"Não foi possível carregar o arquivo .env: {e}")
    # Em um app web, não usamos sys.exit(), apenas logamos o erro.
    # O Flask tratará a falha de conexão.


class Database:
    _instance = None
    _pool = None
    _lock = threading.Lock()

    def __new__(cls):
        # Implementação do padrão Singleton para garantir uma única instância
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def _initialize_pool(self):
        """Inicializa o pool de conexões de forma segura (thread-safe)."""
        with self._lock:
            if self._pool is not None and not self._pool.closed:
                return

            logger.info("🔧 Criando pool de conexões com PostgreSQL/Neon...")
            connection_url = os.getenv("DATABASE_URL")
            if not connection_url:
                raise ValueError("Variável de ambiente DATABASE_URL não encontrada no .env")

            pool_size = int(os.getenv("DB_POOL_SIZE", 3))

            try:
                self._pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=pool_size,
                    dsn=connection_url
                )
                logger.info(f"✅ Pool de conexões criado com sucesso! (Tamanho: {pool_size})")
                return
            except OperationalError as e:
                logger.error(f"❌ Erro CRÍTICO ao criar o pool de conexões: {e}")
                raise ConnectionError("Não foi possível criar o pool de conexões com o banco de dados.")

    def get_connection(self):
        """Obtém uma conexão do pool, inicializando-o se necessário."""
        if self._pool is None or self._pool.closed:
            self._initialize_pool()
        return self._pool.getconn()

    def release_connection(self, conn):
        """Devolve uma conexão ao pool."""
        if self._pool:
            self._pool.putconn(conn)

    def execute_query(self, query, params=None, fetch=None):
        """
        Executa uma query de forma segura.
        - fetch='one': Retorna um único resultado (ou None)
        - fetch='all': Retorna uma lista de resultados (ou uma lista vazia)
        - fetch=None (padrão para INSERT/UPDATE): Não retorna nada, apenas executa.
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params or ())

                if fetch == 'one':
                    return cursor.fetchone()
                if fetch == 'all':
                    return cursor.fetchall()

                conn.commit()

                if query.strip().upper().startswith("INSERT") and "RETURNING" in query.upper():
                    return cursor.fetchone()

                return None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Erro ao executar query: {e}\nQuery: {query}\nParams: {params}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def close_all_connections(self):
        """Fecha todas as conexões do pool. Chamar ao encerrar o app."""
        with self._lock:
            if self._pool:
                self._pool.closeall()
                self._pool = None
                logger.info("👋 Todas as conexões do pool foram fechadas.")