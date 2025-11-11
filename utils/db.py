# # Arquivo: utils/db.py
# import os
# import mysql.connector
# from mysql.connector import pooling
# import logging
#
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
#
# class Database:
#     _pool = None
#
#     def __init__(self):
#         if Database._pool is None:
#             self._initialize_pool()
#
#     def _initialize_pool(self):
#         try:
#             logging.info("🔧 Criando pool de conexões com MySQL...")
#             connection_url = os.environ.get('DATABASE_URL')
#             if not connection_url:
#                 raise ValueError("A variável de ambiente DATABASE_URL não foi definida.")
#
#             parts = connection_url.replace('mysql://', '').split('@')
#             user_pass, host_port_db = parts[0], parts[1]
#             user, password = user_pass.split(':')
#             host_port, database = host_port_db.split('/')
#             host, port = host_port.split(':')
#
#             db_config = {
#                 'pool_name': "mypool", 'pool_size': 10, 'host': host,
#                 'port': port, 'user': user, 'password': password, 'database': database
#             }
#
#             Database._pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)
#             logging.info("✅ Pool de conexões com MySQL criado com sucesso.")
#         except Exception as e:
#             logging.error(f"❌ Erro CRÍTICO ao criar o pool de conexões: {e}")
#             Database._pool = None
#
#     def get_connection(self):
#         if self._pool is None:
#             raise ConnectionError("Pool de conexões não inicializado.")
#         return self._pool.get_connection()
#
#     def execute_query(self, query, params=None, fetch=None):
#         conn = None; cursor = None
#         try:
#             conn = self.get_connection()
#             cursor = conn.cursor(dictionary=True, buffered=True)
#             cursor.execute(query, params or ())
#             if fetch == 'one': return cursor.fetchone()
#             elif fetch == 'all': return cursor.fetchall()
#             else: conn.commit(); return cursor.rowcount
#         except Exception as e:
#             logging.error(f"❌ Erro ao executar query: {e}")
#             if conn: conn.rollback()
#             return None
#         finally:
#             if cursor: cursor.close()
#             if conn: conn.close()
#
# db = Database()

"""
Módulo de Abstração de Banco de Dados (DAL).

Este módulo centraliza toda a lógica de conexão e execução de queries
com o banco de dados MySQL. Ele utiliza um pool de conexões (connection pooling)
para performance e o padrão singleton para garantir uma única instância do pool.
"""

import os
import mysql.connector
from mysql.connector import pooling
import logging

# Configura o logging para este módulo.
# Em produção, um arquivo de configuração centralizado (ex: logging.ini) seria ideal.
# O formato inclui o 'threadName' para depurar concorrência no pool.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')


class Database:
    """
    Classe singleton que gerencia o pool de conexões com o MySQL.
    """
    _pool = None  # Variável de classe para armazenar a instância do pool (Singleton)

    def __init__(self):
        """
        Inicializa a classe. O pool só é criado na primeira vez que a
        classe é instanciada, graças à verificação `_pool is None`.
        """
        if Database._pool is None:
            self._initialize_pool()

    def _initialize_pool(self):
        """
        Configura e cria o pool de conexões do MySQL a partir da
        variável de ambiente 'DATABASE_URL'.
        """
        try:
            logging.info("🔧 Inicializando pool de conexões com MySQL...")
            connection_url = os.environ.get('DATABASE_URL')
            if not connection_url:
                logging.critical("A variável de ambiente DATABASE_URL não foi definida.")
                raise ValueError("A variável de ambiente DATABASE_URL não foi definida.")

            # Parse da URL de conexão (ex: mysql://user:pass@host:port/db)
            parts = connection_url.replace('mysql://', '').split('@')
            user_pass, host_port_db = parts[0], parts[1]
            user, password = user_pass.split(':')
            host_port, database = host_port_db.split('/')
            host, port = host_port.split(':')

            db_config = {
                'pool_name': "flask_pool",  # Nome do pool
                'pool_size': 10,  # Número de conexões mantidas prontas
                'host': host,
                'port': port,
                'user': user,
                'password': password,
                'database': database
            }

            Database._pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)
            logging.info("✅ Pool de conexões MySQL inicializado com sucesso.")
        except Exception as e:
            # Um erro aqui é crítico, pois a aplicação não pode funcionar sem o banco.
            logging.critical(f"❌ Erro CRÍTICO ao inicializar o pool de conexões: {e}")
            Database._pool = None

    def get_connection(self):
        """
        Solicita uma conexão ativa do pool.
        Se o pool não estiver inicializado, levanta um erro.
        """
        if self._pool is None:
            logging.error("Tentativa de obter conexão de um pool não inicializado.")
            # Se o pool falhou na inicialização, tentamos recriá-lo uma vez.
            self._initialize_pool()
            if self._pool is None:
                raise ConnectionError("Pool de conexões não está disponível e não pôde ser recriado.")

        return self._pool.get_connection()

    def execute_query(self, query, params=None, fetch=None):
        """
        Método unificado para executar todas as consultas ao banco de dados.
        Gerencia o ciclo de vida da conexão (obter do pool, usar, devolver ao pool).

        :param query: A string da consulta SQL (com placeholders %s).
        :param params: Uma tupla de parâmetros para a consulta (previne SQL Injection).
        :param fetch: 'one' (para SELECT 1), 'all' (para SELECT *), None (para INSERT/UPDATE/DELETE).
        :return: Resultado da consulta (dicionário, lista de dicionários) ou contagem de linhas (para commits).
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()

            # dictionary=True: Retorna resultados como dicionários (ex: row['nome'])
            # buffered=True: Necessário para evitar erros "Unread result found"
            cursor = conn.cursor(dictionary=True, buffered=True)

            # Log de depuração (Nível DEBUG, não aparecerá por padrão, mas útil se necessário)
            logging.debug(f"Executando query: {query[:150]}... Params: {params}")

            cursor.execute(query, params or ())

            if fetch == 'one':
                return cursor.fetchone()
            elif fetch == 'all':
                return cursor.fetchall()
            else:
                # Se não for 'fetch', é uma operação de escrita (INSERT, UPDATE, DELETE)
                conn.commit()
                return cursor.rowcount  # Retorna o número de linhas afetadas

        except Exception as e:
            # Em caso de erro, desfaz a transação e loga o erro COM a query.
            # Adicionar a query ao log é a melhoria de debug que você pediu.
            logging.error(f"❌ Erro ao executar query: {query[:150]}... Erro: {e}")
            if conn:
                conn.rollback()  # Desfaz quaisquer alterações pendentes
            return None  # Retorna None para indicar falha

        finally:
            # Este bloco é CRUCIAL.
            if cursor:
                cursor.close()
            if conn:
                # conn.close() em um pool NÃO fecha a conexão.
                # Ele "libera" a conexão de volta ao pool para ser reutilizada.
                conn.close()


# Cria a instância singleton que será importada por outros módulos (ex: routes.py).
# Isso garante que o pool de conexões é compartilhado por toda a aplicação.
db = Database()