"""
Módulo de Decorators de Permissão.

Este arquivo centraliza a lógica de autenticação e autorização da aplicação,
seguindo o princípio DRY (Don't Repeat Yourself).

Decorators são usados para "embrulhar" as rotas (endpoints) no 'routes.py'
e verificar as credenciais do usuário na 'session' antes de executar
a lógica principal da rota.
"""

from functools import wraps
from flask import session, flash, redirect, url_for


def login_required(f):
    """
    Decorator de Autenticação.

    Verifica se um 'colaborador_id' existe na sessão, provando que
    o usuário está autenticado. Caso contrário, redireciona para a
    página de login.
    """

    @wraps(f)  # Preserva os metadados da função original (ex: __name__)
    def decorated_function(*args, **kwargs):
        # A presença de 'colaborador_id' na sessão é a
        # principal validação de que o usuário está logado.
        if 'colaborador_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))

        # Usuário está logado, permite a execução da rota.
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """
    Decorator de Autorização (Nível Administrador).

    Verifica se o usuário logado possui *estritamente* o perfil 'Administrador'.
    Redireciona para a 'index' (home) se a permissão for negada.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # A verificação é estrita: apenas 'Administrador' pode passar.
        if session.get('colaborador_perfil') != 'Administrador':
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            # Redireciona para 'index' pois o usuário ESTÁ logado,
            # ele apenas não tem autorização.
            return redirect(url_for('index'))

        # Usuário é Admin, permite a execução.
        return f(*args, **kwargs)

    return decorated_function


def gestor_required(f):
    """
    Decorator de Autorização (Nível Gestor ou Superior).

    Verifica se o usuário logado possui perfil 'Gestor' OU 'Administrador'.
    Isso estabelece uma hierarquia de permissões onde um Administrador
    pode acessar todas as áreas de um Gestor.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Lógica de hierarquia: Admins podem fazer tudo que Gestores podem.
        allowed_profiles = ['Gestor', 'Administrador']

        if session.get('colaborador_perfil') not in allowed_profiles:
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('index'))

        # Usuário é Gestor ou Admin, permite a execução.
        return f(*args, **kwargs)

    return decorated_function