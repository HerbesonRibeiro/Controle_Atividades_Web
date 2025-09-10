# # Arquivo: run.py
import os
from dotenv import load_dotenv

# Verifica se a variável de ambiente FLASK_ENV está definida como 'testing'
if os.getenv('FLASK_ENV') == 'testing':
    print("🧪 MODO DE TESTE ATIVADO: Carregando configurações de '.env.test'")
    # Carrega as variáveis do arquivo de teste
    load_dotenv(dotenv_path='.env.test')
else:
    print("💻 MODO DE DESENVOLVIMENTO: Carregando configurações de '.env'")
    # Carrega as variáveis do .env padrão
    load_dotenv()

# Importa o app DEPOIS de carregar as variáveis de ambiente
from app import app

if __name__ == '__main__':
    app.run(debug=True)