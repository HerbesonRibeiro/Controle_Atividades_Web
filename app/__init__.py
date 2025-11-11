"""
Construtor do pacote da aplicação Flask.

Este arquivo é executado automaticamente quando o pacote 'app' é importado.
Ele é responsável por:
1. Criar a instância principal da aplicação Flask.
2. Carregar configurações essenciais (como a SECRET_KEY).
3. Importar outros módulos do pacote (como as rotas).
"""

import os
from flask import Flask

# [1] Criação da Instância da Aplicação
# '__name__' é passado para que o Flask saiba onde procurar recursos
# como templates e arquivos estáticos (pastas 'templates' e 'static').
app = Flask(__name__)

# [2] Carregamento de Configurações
# A SECRET_KEY é fundamental para a segurança. Ela é usada pelo Flask
# para "assinar" digitalmente os cookies de sessão, protegendo-os contra
# adulteração por parte do usuário.
# O valor é lido das variáveis de ambiente (via .env) para evitar
# expor segredos diretamente no código-fonte.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# [3] Importação Tardia (Circular Import Handling)
# O módulo 'routes' é importado no final do arquivo, e não no topo.
# Isso é intencional e necessário para evitar uma "importação circular".
# O 'routes.py' precisa importar o objeto 'app' (definido acima) para
# poder criar os decorators (ex: @app.route('/')), portanto, 'app'
# deve ser totalmente criado antes que 'routes' seja importado.
from app import routes