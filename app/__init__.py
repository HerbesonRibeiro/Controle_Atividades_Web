# Arquivo: app/__init__.py
import os

from flask import Flask

app = Flask(__name__)

# Adicione esta linha. A chave pode ser qualquer texto complexo.
# É crucial para a segurança das sessões.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

from app import routes