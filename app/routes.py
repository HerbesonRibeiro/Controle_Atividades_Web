# Arquivo: app/routes.py (Reorganizado)

# Arquivo: app/routes.py
from functools import wraps
from flask import session, flash, redirect, url_for, render_template, request
from app import app
from utils.db import Database
import bcrypt
from datetime import date
import math


db = Database()

# --- COLE O DECORATOR AQUI NO TOPO ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica se o usuário está logado E se o perfil é 'Administrator'
        if session.get('colaborador_perfil') != 'Administrador':
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('index')) # Redireciona para a home se não for admin
        return f(*args, **kwargs)
    return decorated_function
# --- FIM DO DECORATOR ---
@app.route('/')
def index():
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    # Simplesmente renderiza a nova página de boas-vindas
    return render_template('home.html')

# ROTA DO HISTÓRICO AGORA EM (/historico)
# Em app/routes.py
import math  # Garanta que math está importado no topo do seu arquivo


@app.route('/historico')
def historico():
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    # --- LÓGICA DE PAGINAÇÃO ---
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 25
    offset = (page - 1) * PER_PAGE

    # --- Busca de dados para os filtros ---
    tipos_atendimento = db.execute_query("SELECT nome FROM tipos_atendimento ORDER BY nome", fetch='all') or []
    lista_colaboradores = db.execute_query("SELECT id, nome FROM colaboradores ORDER BY nome", fetch='all') or []
    lista_setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []

    # --- Lógica de Permissões e Filtros ---
    user_id = session['colaborador_id']
    query_perfil = "SELECT p.nome AS perfil_nome FROM colaboradores c JOIN perfis p ON c.perfil_id = p.id WHERE c.id = %s"
    user_profile = db.execute_query(query_perfil, (user_id,), fetch='one')['perfil_nome']

    base_query_from = """
        FROM atividades a
        JOIN tipos_atendimento t ON a.tipo_atendimento_id = t.id 
        JOIN colaboradores c ON a.colaborador_id = c.id 
        JOIN setores s ON c.setor_id = s.id
    """
    where_clauses = []
    params = []

    if user_profile == 'Colaborador':
        where_clauses.append("a.colaborador_id = %s")
        params.append(user_id)
    elif user_profile == 'Gestor':
        where_clauses.append("s.gestor_id = %s")
        params.append(user_id)

    # --- CONSTRUÇÃO DOS FILTROS ---
    # Pega todos os filtros da URL que não estão vazios
    filtros_aplicados = {k: v for k, v in request.args.items() if k != 'page' and v}

    # Filtro por Tipo de Atendimento (já existia)
    if 'tipo_filtro' in filtros_aplicados:
        where_clauses.append("t.nome = %s")
        params.append(filtros_aplicados['tipo_filtro'])

    # --- FILTROS ADICIONADOS ---
    # Filtro por Data de Início
    if 'data_ini' in filtros_aplicados:
        where_clauses.append("a.data_atendimento >= %s")
        params.append(filtros_aplicados['data_ini'])

    # Filtro por Data de Fim
    if 'data_fim' in filtros_aplicados:
        # Adicionamos ' 23:59:59' para incluir o dia inteiro
        where_clauses.append("a.data_atendimento <= %s")
        params.append(f"{filtros_aplicados['data_fim']} 23:59:59")

    # Filtro por Colaborador
    if 'colaborador_filtro' in filtros_aplicados:
        where_clauses.append("a.colaborador_id = %s")
        params.append(filtros_aplicados['colaborador_filtro'])

    # Filtro por Setor
    if 'setor_filtro' in filtros_aplicados:
        where_clauses.append("c.setor_id = %s")
        params.append(filtros_aplicados['setor_filtro'])

    # Filtro por Descrição
    if 'descricao_filtro' in filtros_aplicados:
        where_clauses.append("a.descricao ILIKE %s")
        params.append(f"%{filtros_aplicados['descricao_filtro']}%")

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)

    # --- Query para CONTAR o total de registros ---
    count_query = "SELECT COUNT(a.id)" + base_query_from + where_sql
    total_records = db.execute_query(count_query, tuple(params), fetch='one')['count']
    total_pages = math.ceil(total_records / PER_PAGE)

    # --- Query para BUSCAR os dados da página atual ---
    data_query = "SELECT a.id, a.data_atendimento, a.status, t.nome AS tipo_atendimento, a.numero_atendimento, a.descricao, c.nome AS colaborador_nome, s.nome_setor, a.nivel_complexidade"
    data_query += base_query_from + where_sql
    data_query += " ORDER BY a.data_atendimento DESC, a.id DESC LIMIT %s OFFSET %s"

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
                p.nome AS nome_perfil  -- Buscando o NOME do perfil
            FROM colaboradores c
            JOIN perfis p ON c.perfil_id = p.id -- Fazendo a junção com a tabela de perfis
            WHERE LOWER(c.usuario) = LOWER(%s) OR LOWER(c.email) = LOWER(%s)
        """
        colaborador = db.execute_query(query, (usuario_input, usuario_input), fetch='one')

        # Verifica se o colaborador existe e se a senha está correta
        if colaborador and bcrypt.checkpw(senha_input.encode('utf-8'), colaborador['senha'].encode('utf-8')):

            # --- MUDANÇA 2: Verificamos se o status do colaborador é 'Ativo' ---
            if colaborador['status'] == 'Ativo':
                session['colaborador_id'] = colaborador['id']
                session['colaborador_nome'] = colaborador['nome']
                session['colaborador_perfil'] = colaborador['nome_perfil']  # <-- ADICIONADO
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('index'))
            else:
                # Se o status for 'Inativo', mostra uma mensagem de erro específica
                flash('Este usuário está inativo. Por favor, contate o administrador.', 'danger')
                return redirect(url_for('login'))
        else:
            # Se o usuário não foi encontrado ou a senha está errada
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')
@app.route('/logout')
def logout():
    session.pop('colaborador_id', None)
    session.pop('colaborador_nome', None)
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))


# Em app/routes.py, substitua a função inteira

@app.route('/registrar', methods=['GET', 'POST'])
def registrar_atividade():
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    colaborador_id = session['colaborador_id']

    if request.method == 'POST':
        # --- Lendo TODOS os campos do formulário ---
        data_atendimento = request.form.get('data_atendimento')
        tipo_atendimento_id = request.form.get('tipo_atendimento')
        nivel = request.form.get('nivel')
        numero_atendimento = request.form.get('numero_atendimento')
        status = request.form.get('status')
        descricao = request.form.get('descricao')

        # --- Nova Validação ---
        if not tipo_atendimento_id or not status:
            flash('Tipo de atendimento e Status são obrigatórios.', 'danger')
            return redirect(url_for('registrar_atividade'))

        # --- Query de INSERT ---
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

    # --- Lógica GET atualizada para passar a data e hora ---
    query_tipos = "SELECT id, nome FROM tipos_atendimento ORDER BY nome"
    tipos_atendimento = db.execute_query(query_tipos, fetch='all') or []

    query_colaborador = "SELECT c.nome, s.nome_setor, p.nome AS perfil FROM colaboradores c JOIN setores s ON c.setor_id = s.id JOIN perfis p ON c.perfil_id = p.id WHERE c.id = %s"
    colaborador_info = db.execute_query(query_colaborador, (colaborador_id,), fetch='one')
    query_stats_hoje = "SELECT COUNT(*) AS total FROM atividades WHERE colaborador_id = %s AND DATE(data_atendimento) = CURRENT_DATE"
    stats_hoje = db.execute_query(query_stats_hoje, (colaborador_id,), fetch='one')['total']
    query_stats_mes = "SELECT COUNT(*) AS total FROM atividades WHERE colaborador_id = %s AND DATE_TRUNC('month', data_atendimento) = DATE_TRUNC('month', CURRENT_DATE)"
    stats_mes = db.execute_query(query_stats_mes, (colaborador_id,), fetch='one')['total']
    query_stats_semana = "SELECT COUNT(*) AS total FROM atividades WHERE colaborador_id = %s AND DATE_TRUNC('week', data_atendimento) = DATE_TRUNC('week', CURRENT_DATE)"
    stats_semana = db.execute_query(query_stats_semana, (colaborador_id,), fetch='one')['total']
    stats = {'hoje': stats_hoje, 'semana': stats_semana, 'mes': stats_mes}

    # Gera a data e hora
    data_atual = date.today().isoformat()

    return render_template('registro_atividades.html',
                           tipos_atendimento=tipos_atendimento,
                           colaborador=colaborador_info,
                           stats=stats,
                           data_atual=data_atual)  # <--- Passa a data para o template


# Adicione ao final de app/routes.py

# Em app/routes.py

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_atividade(id):
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    # --- Lógica de Permissão ---
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

    # Se o método for POST, o usuário está salvando as alterações
    if request.method == 'POST':
        # Pega os dados do formulário
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

    # Se o método for GET, o usuário está abrindo a página para editar
    # Buscamos os dados atuais da atividade no banco
    query_atividade = "SELECT * FROM atividades WHERE id = %s"
    atividade = db.execute_query(query_atividade, (id,), fetch='one')

    if not atividade:
        flash('Atividade não encontrada.', 'danger')
        return redirect(url_for('historico'))

    # Buscamos a lista de tipos de atendimento para preencher o <select>
    tipos_atendimento = db.execute_query("SELECT id, nome FROM tipos_atendimento ORDER BY nome", fetch='all')

    return render_template('editar_atividade.html', atividade=atividade, tipos_atendimento=tipos_atendimento)

@app.route('/excluir/<int:id>', methods=['GET', 'POST'])
def excluir_atividade(id):
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    # --- Lógica de Permissão ---
    # Primeiro, verificamos se o usuário tem a permissão para excluir
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

    # Buscamos a atividade que será excluída para mostrar na tela de confirmação
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

    # Se o método for POST, o usuário clicou em "Sim, Excluir"
    if request.method == 'POST':
        try:
            db.execute_query("DELETE FROM atividades WHERE id = %s", (id,), fetch=None)
            flash('Atividade excluída com sucesso!', 'success')
            return redirect(url_for('historico'))
        except Exception as e:
            flash(f'Erro ao excluir atividade: {e}', 'danger')
            return redirect(url_for('historico'))

    # Se o método for GET, mostramos a página de confirmação
    return render_template('excluir_atividade.html', atividade=atividade)


# Adicione ao final de app/routes.py

@app.route('/excluir-massa', methods=['POST'])
def excluir_massa():
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    # --- Lógica de Permissão ---
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

    # Pega a lista de IDs do formulário
    ids_para_excluir = request.form.getlist('selecao_ids')

    if not ids_para_excluir:
        flash('Nenhum item selecionado para exclusão.', 'warning')
        return redirect(url_for('historico'))

    try:
        # Converte todos os IDs para inteiros para segurança
        ids_tuple = tuple(map(int, ids_para_excluir))

        # A cláusula IN permite deletar múltiplos IDs de uma vez
        query = "DELETE FROM atividades WHERE id IN %s"
        db.execute_query(query, (ids_tuple,), fetch=None)

        flash(f'{len(ids_tuple)} atividade(s) foram excluídas com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir atividades: {e}', 'danger')

    return redirect(url_for('historico'))


# Em app/routes.py

@app.route('/perfil')
def perfil():
    # Garante que apenas usuários logados possam acessar
    if 'colaborador_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'danger')
        return redirect(url_for('login'))

    colaborador_id = session['colaborador_id']

    # Consulta SQL para buscar todos os dados do colaborador, incluindo o nome do setor
    query = """
        SELECT 
            c.id, 
            c.nome, 
            c.email, 
            c.usuario, 
            p.nome AS nome_perfil,
            c.status, 
            s.nome_setor AS nome_setor  -- MUDANÇA BEM AQUI
        FROM colaboradores c
        JOIN setores s ON c.setor_id = s.id
        JOIN perfis p ON c.perfil_id = p.id
        WHERE c.id = %s
    """

    colaborador = db.execute_query(query, (colaborador_id,), fetch='one')

    if not colaborador:
        # Se por algum motivo o colaborador não for encontrado, desloga por segurança
        return redirect(url_for('logout'))

    return render_template('perfil.html', colaborador=colaborador)


# Em app/routes.py - adicione estas rotas

@app.route('/alterar-senha', methods=['GET', 'POST'])
def alterar_senha():
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    colaborador_id = session['colaborador_id']

    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')

        # Validações
        if not all([senha_atual, nova_senha, confirmar_senha]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return redirect(url_for('alterar_senha'))

        if nova_senha != confirmar_senha:
            flash('A nova senha e a confirmação não coincidem.', 'danger')
            return redirect(url_for('alterar_senha'))

        if len(nova_senha) < 6:
            flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
            return redirect(url_for('alterar_senha'))

        # Verificar senha atual
        query = "SELECT senha FROM colaboradores WHERE id = %s"
        colaborador = db.execute_query(query, (colaborador_id,), fetch='one')

        if colaborador and bcrypt.checkpw(senha_atual.encode('utf-8'), colaborador['senha'].encode('utf-8')):
            # Senha atual correta, prosseguir com a alteração
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
    # Buscar parâmetros de filtro da URL
    setor_filtro = request.args.get('setor_filtro', '')
    perfil_filtro = request.args.get('perfil_filtro', '')

    # Query base - AGORA INCLUINDO CARGO
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

    # Aplicar filtros
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

    # Buscar perfis, setores E cargos para filtros e formulários
    perfis = db.execute_query("SELECT id, nome FROM perfis ORDER BY nome", fetch='all') or []
    setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []

    # Buscar opções de cargo do ENUM
    cargos = db.execute_query("SELECT unnest(enum_range(NULL::cargo_enum)) as cargo", fetch='all') or []

    return render_template('gestao_usuarios.html',
                           usuarios=usuarios,
                           perfis=perfis,
                           setores=setores,
                           cargos=cargos,  # <-- NOVO
                           filtros_aplicados={
                               'setor': setor_filtro,
                               'perfil': perfil_filtro
                           })


@app.route('/gestao/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    if request.method == 'POST':
        # Processar o formulário de edição - AGORA INCLUINDO CARGO
        nome = request.form.get('nome')
        usuario = request.form.get('usuario')
        email = request.form.get('email')
        setor_id = request.form.get('setor')
        perfil_id = request.form.get('perfil')
        cargo = request.form.get('cargo')  # <-- NOVO
        status = request.form.get('status')
        nova_senha = request.form.get('nova_senha')

        try:
            if nova_senha:
                # Se foi fornecida uma nova senha, atualizar com hash
                senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                query = """
                    UPDATE colaboradores 
                    SET nome = %s, usuario = %s, email = %s, 
                        setor_id = %s, perfil_id = %s, cargo = %s, status = %s, senha = %s
                    WHERE id = %s
                """
                params = (nome, usuario, email, setor_id, perfil_id, cargo, status, senha_hash, id)
            else:
                # Se não foi fornecida nova senha, manter a atual
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

    # Buscar dados do usuário para edição (GET) - AGORA INCLUINDO CARGO
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
    cargos = db.execute_query("SELECT unnest(enum_range(NULL::cargo_enum)) as cargo", fetch='all') or []

    return render_template('editar_usuario.html',
                           usuario=usuario,
                           perfis=perfis,
                           setores=setores,
                           cargos=cargos)  # <-- NOVO


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
        # Hash da senha
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

# Rota para listar e criar os tipos de atividade
@app.route('/gestao/tipos-atividades', methods=['GET', 'POST'])
@admin_required
def gestao_tipos_atividades():
    if request.method == 'POST':
        # A lógica de criar um novo tipo continua a mesma
        nome_atividade = request.form.get('nome_atividade')
        if nome_atividade:
            try:
                query = "INSERT INTO tipos_atendimento (nome) VALUES (%s)"
                db.execute_query(query, (nome_atividade,))
                flash('Tipo de atividade criado com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao criar tipo de atividade: {e}', 'danger')
        return redirect(url_for('gestao_tipos_atividades'))

    # --- LÓGICA GET ATUALIZADA COM FILTRO ---

    # 1. Pega o termo de busca da URL (ex: /.../?q=Abertura)
    filtro_nome = request.args.get('q', '')

    # 2. Constrói a query SQL dinamicamente
    query = "SELECT id, nome FROM tipos_atendimento"
    params = []

    if filtro_nome:
        # Usa ILIKE para busca case-insensitive (não diferencia maiúsculas/minúsculas)
        query += " WHERE nome ILIKE %s"
        # Adiciona os '%' para buscar qualquer correspondência (início, meio ou fim)
        params.append(f"%{filtro_nome}%")

    query += " ORDER BY nome"

    # 3. Executa a query com os parâmetros, se houver
    tipos = db.execute_query(query, tuple(params) if params else None, fetch='all') or []

    # 4. Envia os tipos filtrados E o termo da busca de volta para o template
    return render_template('gestao_tipos_atividades.html',
                           tipos=tipos,
                           filtro_nome=filtro_nome)
# Rota para editar um tipo de atividade
# Em app/routes.py

@app.route('/gestao/tipos-atividades/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_tipo_atividade(id):
    if request.method == 'POST':
        # Lógica para ATUALIZAR o tipo
        nome_atividade = request.form.get('nome_atividade')
        if nome_atividade:
            try:
                query = "UPDATE tipos_atendimento SET nome = %s WHERE id = %s"
                db.execute_query(query, (nome_atividade, id))
                flash('Tipo de atividade atualizado com sucesso!', 'success')
                return redirect(url_for('gestao_tipos_atividades'))
            except Exception as e:
                flash(f'Erro ao atualizar tipo de atividade: {e}', 'danger')

        # --- CORREÇÃO 2: Redireciona de volta para a PÁGINA DE EDIÇÃO em caso de erro ---
        return redirect(url_for('editar_tipo_atividade', id=id))

    # Lógica para MOSTRAR o formulário de edição (GET)
    query = "SELECT id, nome FROM tipos_atendimento WHERE id = %s"
    tipo = db.execute_query(query, (id,), fetch='one')
    if not tipo:
        flash('Tipo de atividade não encontrado.', 'danger')
        return redirect(url_for('gestao_tipos_atividades'))

    # --- CORREÇÃO 1: Renderiza o TEMPLATE DE EDIÇÃO correto ---
    # Lembre-se de que o nome do arquivo deve ser exatamente este.
    # Se você usou "gestao_editar_atividades.html", coloque esse nome aqui.
    return render_template('editar_tipo_atividade.html', tipo=tipo)


# Em app/routes.py

# Rota para listar e criar setores
@app.route('/gestao/setores', methods=['GET', 'POST'])
@admin_required
def gestao_setores():
    if request.method == 'POST':
        # Lógica para CRIAR um novo setor
        nome_setor = request.form.get('nome_setor')
        gestor_id = request.form.get('gestor_id')

        # Converte para None se "Nenhum" for selecionado (string vazia)
        gestor_id = int(gestor_id) if gestor_id else None

        if nome_setor:
            try:
                query = "INSERT INTO setores (nome_setor, gestor_id) VALUES (%s, %s)"
                db.execute_query(query, (nome_setor, gestor_id))
                flash('Setor criado com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao criar setor: {e}', 'danger')
        return redirect(url_for('gestao_setores'))

    # Lógica para LISTAR os setores (GET)
    # Usamos LEFT JOIN para que setores sem gestor também apareçam
    query_setores = """
        SELECT s.id, s.nome_setor, c.nome AS nome_gestor
        FROM setores s
        LEFT JOIN colaboradores c ON s.gestor_id = c.id
        ORDER BY s.nome_setor
    """
    setores = db.execute_query(query_setores, fetch='all') or []

    # Busca todos os colaboradores para popular o dropdown de gestores
    query_colaboradores = "SELECT id, nome FROM colaboradores ORDER BY nome"
    colaboradores = db.execute_query(query_colaboradores, fetch='all') or []

    return render_template('gestao_setores.html', setores=setores, colaboradores=colaboradores)


# Rota para editar um setor
@app.route('/gestao/setores/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_setor(id):
    if request.method == 'POST':
        # Lógica para ATUALIZAR o setor
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

    # Lógica para MOSTRAR o formulário de edição (GET)
    query_setor = "SELECT id, nome_setor, gestor_id FROM setores WHERE id = %s"
    setor = db.execute_query(query_setor, (id,), fetch='one')
    if not setor:
        flash('Setor não encontrado.', 'danger')
        return redirect(url_for('gestao_setores'))

    query_colaboradores = "SELECT id, nome FROM colaboradores ORDER BY nome"
    colaboradores = db.execute_query(query_colaboradores, fetch='all') or []

    return render_template('editar_setor.html', setor=setor, colaboradores=colaboradores)