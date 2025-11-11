"""
Ponto de entrada principal da aplicação (Application Entrypoint).

Este script é responsável por inicializar e configurar o ambiente da aplicação
antes que qualquer componente principal do Flask seja importado.

A lógica central é a seleção dinâmica das variáveis de ambiente
(ex: desenvolvimento vs. teste) antes da inicialização do 'app'.
"""

import os
from dotenv import load_dotenv

# Determina qual arquivo .env carregar com base na variável de sistema FLASK_ENV.
# Isso permite que a aplicação utilize diferentes configurações (ex: um banco de dados
# de teste) sem a necessidade de alterar o código-fonte.
if os.getenv('FLASK_ENV') == 'testing':
    print("🧪 MODO DE TESTE ATIVADO: Carregando configurações de '.env.test'")
    load_dotenv(dotenv_path='.env.test')
else:
    print("💻 MODO DE DESENVOLVIMENTO: Carregando configurações de '.env'")
    load_dotenv()

# Importação tardia (late import) do objeto 'app'.
# Esta importação deve obrigatoriamente ocorrer APÓS o load_dotenv(),
# pois o objeto 'app' (definido em app/__init__.py) depende das
# variáveis de ambiente que acabaram de ser carregadas.
from app import app

# Bloco de execução principal: Inicia o servidor de desenvolvimento do Flask.
# Este código só é executado quando o script é chamado diretamente
# (ex: `python run.py`) e não quando é importado por outro módulo.
if __name__ == '__main__':
    # debug=True ativa o "hot-reload" (reinício automático) em desenvolvimento.
    # Em produção, este script não é usado; um servidor WSGI (como Gunicorn)
    # será usado para carregar o objeto 'app'.
    app.run(debug=True)
