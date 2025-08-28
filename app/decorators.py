from functools import wraps
from flask import session, flash, redirect, url_for

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('colaborador_perfil') != 'Administrador':
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Você pode adicionar outros decorators aqui no futuro
def gestor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('colaborador_perfil') not in ['Gestor', 'Administrador']:
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function