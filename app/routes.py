# Arquivo: app/routes.py
from functools import wraps
from flask import session, flash, redirect, url_for, render_template, request
from app import app
from utils.db import Database
import bcrypt
from datetime import date,datetime,timedelta
import math
from app.decorators import admin_required, login_required, gestor_required

db = Database()

@app.route('/')
def index():
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    # Simplesmente renderiza a nova página de boas-vindas
    return render_template('home.html')

@app.route('/historico')
@login_required
def historico():
    # --- LÓGICA DE PAGINAÇÃO ---
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 25
    offset = (page - 1) * PER_PAGE

    # --- Busca de dados para os menus de filtro ---
    tipos_atendimento = db.execute_query("SELECT nome FROM tipos_atendimento ORDER BY nome", fetch='all') or []
    lista_colaboradores = db.execute_query("SELECT id, nome FROM colaboradores ORDER BY nome", fetch='all') or []
    lista_setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []

    # --- Construção da Query Dinâmica ---
    base_query_from = """
        FROM atividades a
        JOIN tipos_atendimento t ON a.tipo_atendimento_id = t.id 
        JOIN colaboradores c ON a.colaborador_id = c.id 
        JOIN setores s ON c.setor_id = s.id
    """
    where_clauses = []
    params = []

    # Aplica filtro de permissão com base no perfil do usuário logado
    user_id = session['colaborador_id']
    user_profile = session['colaborador_perfil']

    if user_profile == 'Colaborador':
        where_clauses.append("a.colaborador_id = %s")
        params.append(user_id)
    elif user_profile == 'Gestor':
        # LÓGICA CORRIGIDA: Encontra os setores do gestor e filtra por eles
        query_setores_gestor = "SELECT id FROM setores WHERE gestor_id = %s"
        setores_do_gestor = db.execute_query(query_setores_gestor, (user_id,), fetch='all')
        if setores_do_gestor:
            ids_setores = [s['id'] for s in setores_do_gestor]
            placeholders = ','.join(['%s'] * len(ids_setores))
            where_clauses.append(f"c.setor_id IN ({placeholders})")
            params.extend(ids_setores)
        else:
            # Se um gestor não gerencia nenhum setor, ele não vê nenhuma atividade
            where_clauses.append("1=0")

    filtros_aplicados = {k: v for k, v in request.args.items() if k != 'page' and v}

    if filtros_aplicados.get('tipo_filtro'):
        where_clauses.append("t.nome = %s")
        params.append(filtros_aplicados['tipo_filtro'])
    if filtros_aplicados.get('data_ini'):
        where_clauses.append("DATE(a.data_atendimento) >= %s")
        params.append(filtros_aplicados['data_ini'])
    if filtros_aplicados.get('data_fim'):
        where_clauses.append("DATE(a.data_atendimento) <= %s")
        params.append(filtros_aplicados['data_fim'])
    if filtros_aplicados.get('colaborador_filtro'):
        where_clauses.append("c.id = %s")  # Filtra pelo ID do colaborador
        params.append(filtros_aplicados['colaborador_filtro'])
    if filtros_aplicados.get('setor_filtro'):
        where_clauses.append("s.id = %s")  # Filtra pelo ID do setor
        params.append(filtros_aplicados['setor_filtro'])
    if filtros_aplicados.get('descricao_filtro'):
        where_clauses.append("a.descricao LIKE %s")
        params.append(f"%{filtros_aplicados['descricao_filtro']}%")

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # Query para CONTAR o total de registros (forma mais segura)
    count_query = "SELECT COUNT(a.id) AS total" + base_query_from + where_sql
    count_result = db.execute_query(count_query, tuple(params), fetch='one')
    total_records = count_result['total'] if count_result else 0
    total_pages = math.ceil(total_records / PER_PAGE) if total_records > 0 else 1

    # Query para BUSCAR os dados da página
    data_query = "SELECT a.id, a.data_atendimento, a.status, t.nome AS tipo_atendimento, a.numero_atendimento, a.descricao, c.nome AS colaborador_nome, s.nome_setor, a.nivel_complexidade" + base_query_from + where_sql + " ORDER BY a.data_atendimento DESC, a.id DESC LIMIT %s OFFSET %s"
    atividades = db.execute_query(data_query, tuple(params + [PER_PAGE, offset]), fetch='all') or []

    return render_template('historico.html',
                           lista_atividades=atividades,
                           tipos_atendimento=tipos_atendimento,
                           lista_colaboradores=lista_colaboradores,
                           lista_setores=lista_setores,
                           filtros_aplicados=filtros_aplicados,
                           current_page=page,
                           total_pages=total_pages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_input = request.form.get('usuario')
        senha_input = request.form.get('senha')

        query = """
            SELECT 
                c.id, 
                c.nome, 
                c.senha, 
                c.status,
                p.nome AS nome_perfil
            FROM colaboradores c
            JOIN perfis p ON c.perfil_id = p.id
            WHERE LOWER(c.usuario) = LOWER(%s) OR LOWER(c.email) = LOWER(%s)
        """
        colaborador = db.execute_query(query, (usuario_input, usuario_input), fetch='one')

        # Verifica se o colaborador existe e se a senha está correta
        if colaborador and bcrypt.checkpw(senha_input.encode('utf-8'), colaborador['senha'].encode('utf-8')):
            if colaborador['status'] == 'Ativo':
                session['colaborador_id'] = colaborador['id']
                session['colaborador_nome'] = colaborador['nome']
                session['colaborador_perfil'] = colaborador['nome_perfil']
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Este usuário está inativo. Por favor, contate o administrador.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('colaborador_id', None)
    session.pop('colaborador_nome', None)
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))


@app.route('/registrar', methods=['GET', 'POST'])
def registrar_atividade():
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    colaborador_id = session['colaborador_id']

    if request.method == 'POST':
        data_atendimento = request.form.get('data_atendimento')
        tipo_atendimento_id = request.form.get('tipo_atendimento')
        nivel = request.form.get('nivel')
        numero_atendimento = request.form.get('numero_atendimento')
        status = request.form.get('status')
        descricao = request.form.get('descricao')

        if not tipo_atendimento_id or not status:
            flash('Tipo de atendimento e Status são obrigatórios.', 'danger')
            return redirect(url_for('registrar_atividade'))

        query = """
            INSERT INTO atividades 
            (colaborador_id, tipo_atendimento_id, numero_atendimento, descricao, status, data_atendimento, nivel_complexidade)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (colaborador_id, int(tipo_atendimento_id), numero_atendimento, descricao, status, data_atendimento,
                  nivel)

        try:
            db.execute_query(query, params)
            flash('Atividade registrada com sucesso!', 'success')
            return redirect(url_for('registrar_atividade'))
        except Exception as e:
            flash(f'Erro ao registrar atividade: {e}', 'danger')
            return redirect(url_for('registrar_atividade'))

    query_tipos = "SELECT id, nome FROM tipos_atendimento ORDER BY nome"
    tipos_atendimento = db.execute_query(query_tipos, fetch='all') or []

    query_colaborador = "SELECT c.nome, s.nome_setor, p.nome AS perfil FROM colaboradores c JOIN setores s ON c.setor_id = s.id JOIN perfis p ON c.perfil_id = p.id WHERE c.id = %s"
    colaborador_info = db.execute_query(query_colaborador, (colaborador_id,), fetch='one')

    query_stats_hoje = "SELECT COUNT(*) AS total FROM atividades WHERE colaborador_id = %s AND DATE(data_atendimento) = CURDATE()"
    stats_hoje = db.execute_query(query_stats_hoje, (colaborador_id,), fetch='one')['total']

    query_stats_mes = "SELECT COUNT(*) AS total FROM atividades WHERE colaborador_id = %s AND MONTH(data_atendimento) = MONTH(CURDATE()) AND YEAR(data_atendimento) = YEAR(CURDATE())"
    stats_mes = db.execute_query(query_stats_mes, (colaborador_id,), fetch='one')['total']

    query_stats_semana = "SELECT COUNT(*) AS total FROM atividades WHERE colaborador_id = %s AND YEARWEEK(data_atendimento, 1) = YEARWEEK(CURDATE(), 1)"
    stats_semana = db.execute_query(query_stats_semana, (colaborador_id,), fetch='one')['total']

    stats = {'hoje': stats_hoje, 'semana': stats_semana, 'mes': stats_mes}

    data_atual = date.today().isoformat()

    return render_template('registro_atividades.html',
                           tipos_atendimento=tipos_atendimento,
                           colaborador=colaborador_info,
                           stats=stats,
                           data_atual=data_atual)


@app.route('/editar_atividade/<int:id>', methods=['GET', 'POST'])
def editar_atividade(id):
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    user_id = session['colaborador_id']
    query_permissao = """
        SELECT 1 FROM perfil_permissoes pp
        JOIN colaboradores c ON c.perfil_id = pp.perfil_id
        JOIN permissoes p ON p.id = pp.permissao_id
        WHERE c.id = %s AND p.nome = 'editar_atividade'
    """
    permissao = db.execute_query(query_permissao, (user_id,), fetch='one')

    if not permissao:
        flash('Você não tem permissão para editar atividades.', 'danger')
        return redirect(url_for('historico'))

    if request.method == 'POST':
        data_atendimento = request.form.get('data_atendimento')
        tipo_atendimento = request.form.get('tipo_atendimento')
        nivel_complexidade = request.form.get('nivel_complexidade')
        status = request.form.get('status')
        numero_atendimento = request.form.get('numero_atendimento')
        descricao = request.form.get('descricao')

        try:
            query = """
                UPDATE atividades
                SET data_atendimento = %s, tipo_atendimento_id = %s, nivel_complexidade = %s,
                    status = %s, numero_atendimento = %s, descricao = %s
                WHERE id = %s
            """
            params = (data_atendimento, tipo_atendimento, nivel_complexidade, status, numero_atendimento, descricao, id)
            db.execute_query(query, params, fetch=None)
            flash('Atividade atualizada com sucesso!', 'success')
            return redirect(url_for('historico'))
        except Exception as e:
            flash(f'Erro ao atualizar atividade: {e}', 'danger')

    query_atividade = "SELECT * FROM atividades WHERE id = %s"
    atividade = db.execute_query(query_atividade, (id,), fetch='one')

    if not atividade:
        flash('Atividade não encontrada.', 'danger')
        return redirect(url_for('historico'))

    tipos_atendimento = db.execute_query("SELECT id, nome FROM tipos_atendimento ORDER BY nome", fetch='all')

    return render_template('editar_atividade.html', atividade=atividade, tipos_atendimento=tipos_atendimento)


@app.route('/excluir/<int:id>', methods=['GET', 'POST'])
def excluir_atividade(id):
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    user_id = session['colaborador_id']
    query_permissao = """
        SELECT 1 FROM perfil_permissoes pp
        JOIN colaboradores c ON c.perfil_id = pp.perfil_id
        JOIN permissoes p ON p.id = pp.permissao_id
        WHERE c.id = %s AND p.nome = 'excluir_atividade'
    """
    permissao = db.execute_query(query_permissao, (user_id,), fetch='one')

    if not permissao:
        flash('Você não tem permissão para excluir atividades.', 'danger')
        return redirect(url_for('historico'))

    query_atividade = """
        SELECT a.id, a.data_atendimento, a.descricao, t.nome AS tipo_atendimento
        FROM atividades a
        JOIN tipos_atendimento t ON a.tipo_atendimento_id = t.id
        WHERE a.id = %s
    """
    atividade = db.execute_query(query_atividade, (id,), fetch='one')

    if not atividade:
        flash('Atividade não encontrada.', 'danger')
        return redirect(url_for('historico'))

    if request.method == 'POST':
        try:
            db.execute_query("DELETE FROM atividades WHERE id = %s", (id,), fetch=None)
            flash('Atividade excluída com sucesso!', 'success')
            return redirect(url_for('historico'))
        except Exception as e:
            flash(f'Erro ao excluir atividade: {e}', 'danger')
            return redirect(url_for('historico'))

    return render_template('excluir_atividade.html', atividade=atividade)


@app.route('/excluir-massa', methods=['POST'])
def excluir_massa():
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    user_id = session['colaborador_id']
    query_permissao = """
        SELECT 1 FROM perfil_permissoes pp
        JOIN colaboradores c ON c.perfil_id = pp.perfil_id
        JOIN permissoes p ON p.id = pp.permissao_id
        WHERE c.id = %s AND p.nome = 'excluir_atividade'
    """
    permissao = db.execute_query(query_permissao, (user_id,), fetch='one')

    if not permissao:
        flash('Você não tem permissão para excluir atividades.', 'danger')
        return redirect(url_for('historico'))

    ids_para_excluir = request.form.getlist('selecao_ids')

    if not ids_para_excluir:
        flash('Nenhum item selecionado para exclusão.', 'warning')
        return redirect(url_for('historico'))

    try:
        placeholders = ','.join(['%s'] * len(ids_para_excluir))
        query = f"DELETE FROM atividades WHERE id IN ({placeholders})"
        db.execute_query(query, tuple(ids_para_excluir), fetch=None)

        flash(f'{len(ids_para_excluir)} atividade(s) foram excluídas com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir atividades: {e}', 'danger')

    return redirect(url_for('historico'))


@app.route('/perfil')
def perfil():
    if 'colaborador_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('login'))

    colaborador_id = session['colaborador_id']

    query = """
            SELECT 
                c.id, 
                c.nome, 
                c.email, 
                c.usuario, 
                p.nome AS nome_perfil,
                c.status, 
                s.nome_setor,
                gestor.nome AS nome_gestor  -- Esta é a nova coluna que estamos buscando
            FROM 
                colaboradores AS c
            JOIN 
                setores AS s ON c.setor_id = s.id
            JOIN 
                perfis AS p ON c.perfil_id = p.id
            LEFT JOIN -- Usamos LEFT JOIN aqui para o caso de um setor não ter gestor
                colaboradores AS gestor ON s.gestor_id = gestor.id
            WHERE 
                c.id = %s
        """

    colaborador = db.execute_query(query, (colaborador_id,), fetch='one')

    if not colaborador:
        return redirect(url_for('logout'))

    return render_template('perfil.html', colaborador=colaborador)


@app.route('/alterar-senha', methods=['GET', 'POST'])
def alterar_senha():
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    colaborador_id = session['colaborador_id']

    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')

        if not all([senha_atual, nova_senha, confirmar_senha]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return redirect(url_for('alterar_senha'))

        if nova_senha != confirmar_senha:
            flash('A nova senha e a confirmação não coincidem.', 'danger')
            return redirect(url_for('alterar_senha'))

        if len(nova_senha) < 6:
            flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
            return redirect(url_for('alterar_senha'))

        query = "SELECT senha FROM colaboradores WHERE id = %s"
        colaborador = db.execute_query(query, (colaborador_id,), fetch='one')

        if colaborador and bcrypt.checkpw(senha_atual.encode('utf-8'), colaborador['senha'].encode('utf-8')):
            nova_senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            update_query = "UPDATE colaboradores SET senha = %s WHERE id = %s"
            db.execute_query(update_query, (nova_senha_hash, colaborador_id))

            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('perfil'))
        else:
            flash('Senha atual incorreta.', 'danger')
            return redirect(url_for('alterar_senha'))

    return render_template('alterar_senha.html')


@app.route('/gestao/usuarios')
@admin_required
def gestao_usuarios():
    setor_filtro = request.args.get('setor_filtro', '')
    perfil_filtro = request.args.get('perfil_filtro', '')

    query = """
        SELECT 
            c.id, c.nome, c.usuario, c.status, c.cargo,
            p.nome as perfil, s.nome_setor as setor,
            s.id as setor_id, p.id as perfil_id
        FROM colaboradores c
        JOIN perfis p ON c.perfil_id = p.id
        JOIN setores s ON c.setor_id = s.id
    """

    params = []
    where_clauses = []

    if setor_filtro:
        where_clauses.append("s.id = %s")
        params.append(setor_filtro)

    if perfil_filtro:
        where_clauses.append("p.id = %s")
        params.append(perfil_filtro)

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY c.nome"

    usuarios = db.execute_query(query, tuple(params) if params else None, fetch='all') or []

    perfis = db.execute_query("SELECT id, nome FROM perfis ORDER BY nome", fetch='all') or []
    setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []

    cargos = db.execute_query("SHOW COLUMNS FROM colaboradores LIKE 'cargo'", fetch='one')
    if cargos:
        cargo_type = cargos['Type']
        import re
        cargo_options = re.findall(r"'(.*?)'", cargo_type)
        cargos = [{'cargo': cargo} for cargo in cargo_options]
    else:
        cargos = []

    return render_template('gestao_usuarios.html',
                           usuarios=usuarios,
                           perfis=perfis,
                           setores=setores,
                           cargos=cargos,
                           filtros_aplicados={
                               'setor': setor_filtro,
                               'perfil': perfil_filtro
                           })


@app.route('/gestao/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    if request.method == 'POST':
        nome = request.form.get('nome')
        usuario = request.form.get('usuario')
        email = request.form.get('email')
        setor_id = request.form.get('setor')
        perfil_id = request.form.get('perfil')
        cargo = request.form.get('cargo')
        status = request.form.get('status')
        nova_senha = request.form.get('nova_senha')

        try:
            if nova_senha:
                senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                query = """
                    UPDATE colaboradores 
                    SET nome = %s, usuario = %s, email = %s, 
                        setor_id = %s, perfil_id = %s, cargo = %s, status = %s, senha = %s
                    WHERE id = %s
                """
                params = (nome, usuario, email, setor_id, perfil_id, cargo, status, senha_hash, id)
            else:
                query = """
                    UPDATE colaboradores 
                    SET nome = %s, usuario = %s, email = %s, 
                        setor_id = %s, perfil_id = %s, cargo = %s, status = %s
                    WHERE id = %s
                """
                params = (nome, usuario, email, setor_id, perfil_id, cargo, status, id)

            db.execute_query(query, params)

            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('gestao_usuarios'))

        except Exception as e:
            flash(f'Erro ao atualizar usuário: {e}', 'danger')
            return redirect(url_for('editar_usuario', id=id))

    query = """
        SELECT 
            c.id, c.nome, c.usuario, c.email, c.status, c.cargo,
            p.nome as perfil, s.nome_setor as setor,
            s.id as setor_id, p.id as perfil_id
        FROM colaboradores c
        JOIN perfis p ON c.perfil_id = p.id
        JOIN setores s ON c.setor_id = s.id
        WHERE c.id = %s
    """

    usuario = db.execute_query(query, (id,), fetch='one')

    if not usuario:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('gestao_usuarios'))

    perfis = db.execute_query("SELECT id, nome FROM perfis ORDER BY nome", fetch='all') or []
    setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []

    cargos_query = db.execute_query("SHOW COLUMNS FROM colaboradores LIKE 'cargo'", fetch='one')
    if cargos_query:
        cargo_type = cargos_query['Type']
        import re
        cargo_options = re.findall(r"'(.*?)'", cargo_type)
        cargos = [{'cargo': cargo} for cargo in cargo_options]
    else:
        cargos = []

    return render_template('editar_usuario.html',
                           usuario=usuario,
                           perfis=perfis,
                           setores=setores,
                           cargos=cargos)


@app.route('/gestao/usuarios/novo', methods=['POST'])
@admin_required
def novo_usuario():
    nome = request.form.get('nome')
    usuario = request.form.get('usuario')
    email = request.form.get('email')
    setor_id = request.form.get('setor')
    perfil_id = request.form.get('perfil')
    cargo = request.form.get('cargo')
    status = request.form.get('status')
    senha = request.form.get('senha')

    try:
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        query = """
            INSERT INTO colaboradores 
            (nome, usuario, email, setor_id, perfil_id, cargo, status, senha)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (nome, usuario, email, setor_id, perfil_id, cargo, status, senha_hash)
        db.execute_query(query, params)

        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('gestao_usuarios'))

    except Exception as e:
        flash(f'Erro ao criar usuário: {e}', 'danger')
        return redirect(url_for('gestao_usuarios'))


@app.route('/gestao/tipos-atividades', methods=['GET', 'POST'])
@admin_required
def gestao_tipos_atividades():
    if request.method == 'POST':
        nome_atividade = request.form.get('nome_atividade')
        if nome_atividade:
            try:
                query = "INSERT INTO tipos_atendimento (nome) VALUES (%s)"
                db.execute_query(query, (nome_atividade,))
                flash('Tipo de atividade criado com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao criar tipo de atividade: {e}', 'danger')
        return redirect(url_for('gestao_tipos_atividades'))

    filtro_nome = request.args.get('q', '')

    query = "SELECT id, nome FROM tipos_atendimento"
    params = []

    if filtro_nome:
        query += " WHERE nome LIKE %s"
        params.append(f"%{filtro_nome}%")

    query += " ORDER BY nome"

    tipos = db.execute_query(query, tuple(params) if params else None, fetch='all') or []

    return render_template('gestao_tipos_atividades.html',
                           tipos=tipos,
                           filtro_nome=filtro_nome)


@app.route('/gestao/tipos-atividades/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_tipo_atividade(id):
    if request.method == 'POST':
        nome_atividade = request.form.get('nome_atividade')
        if nome_atividade:
            try:
                query = "UPDATE tipos_atendimento SET nome = %s WHERE id = %s"
                db.execute_query(query, (nome_atividade, id))
                flash('Tipo de atividade atualizado com sucesso!', 'success')
                return redirect(url_for('gestao_tipos_atividades'))
            except Exception as e:
                flash(f'Erro ao atualizar tipo de atividade: {e}', 'danger')

        return redirect(url_for('editar_tipo_atividade', id=id))

    query = "SELECT id, nome FROM tipos_atendimento WHERE id = %s"
    tipo = db.execute_query(query, (id,), fetch='one')
    if not tipo:
        flash('Tipo de atividade não encontrado.', 'danger')
        return redirect(url_for('gestao_tipos_atividades'))

    return render_template('editar_tipo_atividade.html', tipo=tipo)


@app.route('/gestao/setores', methods=['GET', 'POST'])
@admin_required
def gestao_setores():
    if request.method == 'POST':
        nome_setor = request.form.get('nome_setor')
        gestor_id = request.form.get('gestor_id')

        gestor_id = int(gestor_id) if gestor_id else None

        if nome_setor:
            try:
                query = "INSERT INTO setores (nome_setor, gestor_id) VALUES (%s, %s)"
                db.execute_query(query, (nome_setor, gestor_id))
                flash('Setor criado com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao criar setor: {e}', 'danger')
        return redirect(url_for('gestao_setores'))

    query_setores = """
        SELECT s.id, s.nome_setor, c.nome AS nome_gestor
        FROM setores s
        LEFT JOIN colaboradores c ON s.gestor_id = c.id
        ORDER BY s.nome_setor
    """
    setores = db.execute_query(query_setores, fetch='all') or []

    query_colaboradores = "SELECT id, nome FROM colaboradores ORDER BY nome"
    colaboradores = db.execute_query(query_colaboradores, fetch='all') or []

    return render_template('gestao_setores.html', setores=setores, colaboradores=colaboradores)


@app.route('/gestao/setores/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_setor(id):
    if request.method == 'POST':
        nome_setor = request.form.get('nome_setor')
        gestor_id = request.form.get('gestor_id')
        gestor_id = int(gestor_id) if gestor_id else None

        if nome_setor:
            try:
                query = "UPDATE setores SET nome_setor = %s, gestor_id = %s WHERE id = %s"
                db.execute_query(query, (nome_setor, gestor_id, id))
                flash('Setor atualizado com sucesso!', 'success')
                return redirect(url_for('gestao_setores'))
            except Exception as e:
                flash(f'Erro ao atualizar setor: {e}', 'danger')
        return redirect(url_for('editar_setor', id=id))

    query_setor = "SELECT id, nome_setor, gestor_id FROM setores WHERE id = %s"
    setor = db.execute_query(query_setor, (id,), fetch='one')
    if not setor:
        flash('Setor não encontrado.', 'danger')
        return redirect(url_for('gestao_setores'))

    query_colaboradores = "SELECT id, nome FROM colaboradores ORDER BY nome"
    colaboradores = db.execute_query(query_colaboradores, fetch='all') or []

    return render_template('editar_setor.html', setor=setor, colaboradores=colaboradores)

#início da bloco DASHBOARD
# Dicionário de cache, mantenha-o no topo do arquivo, fora de qualquer função
dashboard_cache = {
    'Administrador': {'data': None, 'last_updated': None},
    'Gestor': {}  # Cache por gestor
}
CACHE_DURATION_MINUTES = 10

@app.route('/dashboard')
@login_required
def dashboard():
    perfil = session.get('colaborador_perfil')
    user_id = session.get('colaborador_id')

    # --- 1. CLÁUSULA DE GUARDA (Segurança) ---
    if perfil == 'Colaborador':
        flash('Você não tem permissão para acessar o dashboard.', 'warning')
        return redirect(url_for('index'))

    # --- 2. VERIFICAÇÃO DE CACHE (Performance) ---
    now = datetime.now()
    cache_key = str(user_id) if perfil == 'Gestor' else perfil
    cache_data_source = dashboard_cache['Gestor'] if perfil == 'Gestor' else dashboard_cache
    cache_entry = cache_data_source.get(cache_key)
    if cache_entry and cache_entry.get('data') and (
            now < cache_entry.get('last_updated') + timedelta(minutes=CACHE_DURATION_MINUTES)):
        print(f"INFO: Servindo dashboard para {perfil} {user_id} via CACHE.")
        return render_template('dashboard.html', **cache_entry['data'])

    # --- 3. LÓGICA PRINCIPAL (Busca de dados no banco) ---
    print(f"INFO: Gerando dashboard para {perfil} {user_id} a partir do BANCO DE DADOS.")
    kpis = {}
    dados_extras = {}
    labels_grafico = []
    datasets_grafico = []

    # Pega o ano e mês atuais uma única vez
    hoje = datetime.now()
    ano_atual = hoje.year
    mes_atual = hoje.month
    params_mes = (ano_atual, mes_atual)

    # --- LÓGICA SE ADMINISTRADOR ---
    if perfil == 'Administrador':
        # KPIs
        kpis['total_atividades'] = db.execute_query("SELECT COUNT(id) AS total FROM atividades", fetch='one')['total']
        kpis['atividades_hoje'] = \
        db.execute_query("SELECT COUNT(id) AS total FROM atividades WHERE DATE(data_atendimento) = CURDATE()",
                         fetch='one')['total']
        kpis['total_colaboradores'] = \
        db.execute_query("SELECT COUNT(id) AS total FROM colaboradores WHERE status = 'Ativo'", fetch='one')['total']

        # Cards Extras (POR MÊS)
        query_setor_top_mes = "SELECT s.nome_setor, COUNT(a.id) AS total_atividades FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id JOIN setores s ON c.setor_id = s.id WHERE YEAR(a.data_atendimento) = %s AND MONTH(a.data_atendimento) = %s GROUP BY s.nome_setor ORDER BY total_atividades DESC LIMIT 1;"
        dados_extras['setor_mais_ativo'] = db.execute_query(query_setor_top_mes, params_mes, fetch='one')

        query_colab_top_mes = "SELECT c.nome, COUNT(a.id) AS total_atividades FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id WHERE YEAR(a.data_atendimento) = %s AND MONTH(a.data_atendimento) = %s GROUP BY c.id, c.nome ORDER BY total_atividades DESC LIMIT 1;"
        dados_extras['colaborador_mais_ativo'] = db.execute_query(query_colab_top_mes, params_mes, fetch='one')

        # Listas
        query_colab_setor = "SELECT s.id, s.nome_setor, COUNT(c.id) AS total_colaboradores FROM colaboradores c JOIN setores s ON c.setor_id = s.id WHERE c.status = 'Ativo' GROUP BY s.id, s.nome_setor ORDER BY total_colaboradores DESC;"
        dados_extras['colaboradores_por_setor'] = db.execute_query(query_colab_setor, fetch='all')

        query_top_atividades_mes = "SELECT ta.nome, COUNT(a.id) AS total FROM atividades a JOIN tipos_atendimento ta ON a.tipo_atendimento_id = ta.id WHERE YEAR(a.data_atendimento) = %s AND MONTH(a.data_atendimento) = %s GROUP BY ta.id, ta.nome ORDER BY total DESC LIMIT 3;"
        dados_extras['top_atividades'] = db.execute_query(query_top_atividades_mes, params_mes, fetch='all')

        # Dados para o Gráfico (Empilhado por Setor)
        query_grafico = "SELECT DATE(a.data_atendimento) as dia, s.nome_setor, COUNT(a.id) as total FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id JOIN setores s ON c.setor_id = s.id WHERE a.data_atendimento >= CURDATE() - INTERVAL 6 DAY GROUP BY dia, s.nome_setor ORDER BY dia ASC, s.nome_setor ASC;"
        dados_brutos_grafico = db.execute_query(query_grafico, fetch='all')

        if dados_brutos_grafico:
            labels_grafico = sorted(list(set([d['dia'].strftime('%d/%m') for d in dados_brutos_grafico])))
            setores = sorted(list(set([d['nome_setor'] for d in dados_brutos_grafico])))
            dados_por_setor = {setor: [0] * len(labels_grafico) for setor in setores}
            for dado in dados_brutos_grafico:
                label_index = labels_grafico.index(dado['dia'].strftime('%d/%m'))
                dados_por_setor[dado['nome_setor']][label_index] = dado['total']

            cores = ['rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 206, 86, 0.7)',
                     'rgba(75, 192, 192, 0.7)', 'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)']
            for i, setor in enumerate(setores):
                datasets_grafico.append(
                    {'label': setor, 'data': dados_por_setor[setor], 'backgroundColor': cores[i % len(cores)]})

    # --- LÓGICA DO GESTOR ---
    elif perfil == 'Gestor':
        query_setor = "SELECT id FROM setores WHERE gestor_id = %s"
        setor_gestor = db.execute_query(query_setor, (user_id,), fetch='one')
        if setor_gestor:
            setor_id = setor_gestor['id']
            params = [setor_id]

            # KPIs
            kpis['total_atividades_setor'] = db.execute_query(
                "SELECT COUNT(a.id) AS total FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id WHERE c.setor_id = %s",
                tuple(params), fetch='one')['total']
            kpis['atividades_hoje_setor'] = db.execute_query(
                "SELECT COUNT(a.id) AS total FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id WHERE c.setor_id = %s AND DATE(a.data_atendimento) = CURDATE()",
                tuple(params), fetch='one')['total']
            kpis['total_colaboradores_setor'] = \
                db.execute_query(
                    "SELECT COUNT(id) AS total FROM colaboradores WHERE setor_id = %s AND status = 'Ativo'",
                    tuple(params), fetch='one')['total']
            dados_extras['colaborador_top_setor'] = db.execute_query(
                "SELECT c.nome, COUNT(a.id) AS total_atividades FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id WHERE c.setor_id = %s GROUP BY c.id, c.nome ORDER BY total_atividades DESC LIMIT 1",
                tuple(params), fetch='one')

            # Cards e Listas (POR MÊS)
            params_gestor_mes = (setor_id, ano_atual, mes_atual)

            dados_extras['colaborador_top_setor'] = db.execute_query(
                "SELECT c.nome, COUNT(a.id) AS total_atividades FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id WHERE c.setor_id = %s AND YEAR(a.data_atendimento) = %s AND MONTH(a.data_atendimento) = %s GROUP BY c.id, c.nome ORDER BY total_atividades DESC LIMIT 1",
                params_gestor_mes, fetch='one')

            dados_extras['top_atividades_setor'] = db.execute_query(
                "SELECT ta.nome, COUNT(a.id) AS total FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id JOIN tipos_atendimento ta ON a.tipo_atendimento_id = ta.id WHERE c.setor_id = %s AND YEAR(a.data_atendimento) = %s AND MONTH(a.data_atendimento) = %s GROUP BY ta.id, ta.nome ORDER BY total DESC LIMIT 3",
                params_gestor_mes, fetch='all')

            # Top Colaboradores do Setor (Geral, como já estava)
            dados_extras['top_colaboradores_setor'] = db.execute_query(
                "SELECT c.nome, COUNT(a.id) AS total_atividades FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id WHERE c.setor_id = %s GROUP BY c.id, c.nome ORDER BY total_atividades DESC LIMIT 3",
                (setor_id,), fetch='all')

            # Gráfico do Gestor (Empilhado por Colaborador)
            query_grafico = "SELECT DATE(a.data_atendimento) as dia, c.nome as colaborador, COUNT(a.id) as total FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id WHERE c.setor_id = %s AND a.data_atendimento >= CURDATE() - INTERVAL 6 DAY GROUP BY dia, colaborador ORDER BY dia ASC, colaborador ASC;"
            dados_brutos_grafico = db.execute_query(query_grafico, tuple(params), fetch='all')
            if dados_brutos_grafico:
                labels_grafico = sorted(list(set([d['dia'].strftime('%d/%m') for d in dados_brutos_grafico])))
                colaboradores = sorted(list(set([d['colaborador'] for d in dados_brutos_grafico])))
                dados_por_colaborador = {colab: [0] * len(labels_grafico) for colab in colaboradores}
                for dado in dados_brutos_grafico:
                    label_index = labels_grafico.index(dado['dia'].strftime('%d/%m'))
                    dados_por_colaborador[dado['colaborador']][label_index] = dado['total']
                cores = ['rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 206, 86, 0.7)',
                         'rgba(75, 192, 192, 0.7)', 'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)']
                for i, colaborador in enumerate(colaboradores):
                    datasets_grafico.append({'label': colaborador, 'data': dados_por_colaborador[colaborador],
                                             'backgroundColor': cores[i % len(cores)]})

    # --- 4. CONSULTAS COMUNS E DE REFINAMENTO (NOVA SEÇÃO) ---
    hoje = datetime.now()
    ano_atual = hoje.year
    mes_atual = hoje.month

    # Consulta base para top 5 colaboradores
    query_base_top_colab_mes = """
        SELECT c.nome, COUNT(a.id) AS total_atividades 
        FROM atividades a 
        JOIN colaboradores c ON a.colaborador_id = c.id 
        WHERE YEAR(a.data_atendimento) = %s AND MONTH(a.data_atendimento) = %s
    """
    params_top_colab_mes = [ano_atual, mes_atual]
    if perfil == 'Gestor' and 'setor_id' in locals():
        query_base_top_colab_mes += " AND c.setor_id = %s"
        params_top_colab_mes.append(setor_id)
    #QUERY DO TOP 5 COLABORADORES
    query_base_top_colab_mes += " GROUP BY c.id, c.nome ORDER BY total_atividades DESC LIMIT 5;"
    dados_extras['top_colaboradores_mes'] = db.execute_query(query_base_top_colab_mes, tuple(params_top_colab_mes),fetch='all')


    # Bônus: Formatar o nome do mês para exibir na tela
    hoje = datetime.now()
    meses_em_portugues = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    # Pega o nome do mês da lista (hoje.month-1 porque a lista começa em 0)
    nome_mes_pt = meses_em_portugues[hoje.month - 1]

    # Cria a string final e a armazena no dicionário
    dados_extras['mes_referencia'] = f"{nome_mes_pt} de {hoje.year}"

    # --- 5. MONTAGEM E CACHE DOS DADOS ---
    template_data = {
        'kpis': kpis,
        'dados_extras': dados_extras,
        'labels_grafico': labels_grafico,
        'datasets_grafico': datasets_grafico
    }

    cache_entry_to_update = dashboard_cache['Gestor'].get(cache_key) if perfil == 'Gestor' else dashboard_cache.get(
        perfil)
    if cache_entry_to_update is not None:
        cache_entry_to_update['data'] = template_data
        cache_entry_to_update['last_updated'] = now
    else:  # Primeiro acesso do gestor
        if perfil == 'Gestor':
            dashboard_cache['Gestor'][cache_key] = {'data': template_data, 'last_updated': now}
        else:
            dashboard_cache[perfil] = {'data': template_data, 'last_updated': now}

    # --- 6. SAÍDA ÚNICA E UNIFICADA ---
    return render_template('dashboard.html', **template_data)