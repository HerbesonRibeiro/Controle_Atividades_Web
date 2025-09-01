# Arquivo: app/decorators.py
from functools import wraps
from flask import session, flash, redirect, url_for

def login_required(f):
    """
    Decorator que verifica se o usuário está logado.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica se o "crachá" (colaborador_id) está na sessão
        if 'colaborador_id' not in session:
            # Se não estiver, avisa o usuário e o redireciona para a página de login
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        # Se estiver logado, permite que a rota original seja executada
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('colaborador_perfil') != 'Administrador':
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def gestor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('colaborador_perfil') not in ['Gestor', 'Administrador']:
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
