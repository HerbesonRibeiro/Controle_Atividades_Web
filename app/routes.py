"""
Arquivo: app/routes.py
Descrição: Módulo principal de roteamento e lógica de negócios (views) da aplicação Flask.
"""

from functools import wraps
from flask import session, flash, redirect, url_for, render_template, request, jsonify
from app import app  # Importa a instância 'app' criada no __init__.py
from utils.db import Database  # Importa a instância 'db' do nosso módulo DAL
import bcrypt
from datetime import date, datetime, timedelta
import uuid
import math
from app.decorators import admin_required, login_required, gestor_required  # Nossos decorators de permissão

# Instancia o banco de dados. Graças ao padrão Singleton no db.py,
# esta é a mesma instância 'db' usada em toda a aplicação.
db = Database()


# =============================================================================
# Bloco 1: Rotas de Autenticação e Perfil do Usuário
# =============================================================================

@app.route('/')
def index():
    """
    Rota principal (home page) da aplicação.

    Verifica se o usuário está logado. Se não, redireciona para o login.
    Se sim, renderiza a página 'home.html'.
    """
    if 'colaborador_id' not in session:
        return redirect(url_for('login'))

    # Esta é a página de "boas-vindas" pós-login.
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Processa a autenticação do usuário (login).

    GET: Renderiza o formulário de login.
    POST: Valida as credenciais do usuário.
    """
    if request.method == 'POST':
        usuario_input = request.form.get('usuario')
        senha_input = request.form.get('senha')

        # [1] Busca o usuário no banco de dados.
        # A query já inclui os dados que serão necessários para popular a sessão
        # (perfil_id, setor_id), otimizando a consulta.
        query = """
            SELECT 
                c.id, 
                c.nome, 
                c.senha, 
                c.status,
                c.setor_id,
                p.nome AS nome_perfil
            FROM colaboradores c
            JOIN perfis p ON c.perfil_id = p.id
            WHERE LOWER(c.usuario) = LOWER(%s) OR LOWER(c.email) = LOWER(%s)
        """
        colaborador = db.execute_query(query, (usuario_input, usuario_input), fetch='one')

        # [2] Validação de Credenciais e Status
        # Verifica se o usuário existe E se a senha hashada confere com a senha digitada.
        if colaborador and bcrypt.checkpw(senha_input.encode('utf-8'), colaborador['senha'].encode('utf-8')):

            # Verificação de segurança adicional: usuário está ativo no sistema?
            if colaborador['status'] == 'Ativo':

                # [3] Sucesso: Popula a sessão do Flask
                # A 'session' é um cookie seguro assinado pela SECRET_KEY.
                # Estes dados persistirão entre as requisições do usuário.
                session['colaborador_id'] = colaborador['id']
                session['colaborador_nome'] = colaborador['nome']
                session['colaborador_perfil'] = colaborador['nome_perfil']
                session['colaborador_setor_id'] = colaborador['setor_id']

                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('index'))  # Redireciona para a home page
            else:
                flash('Este usuário está inativo. Por favor, contate o administrador.', 'danger')
                return redirect(url_for('login'))
        else:
            # Resposta genérica para não informar ao atacante se foi
            # o usuário ou a senha que falhou (segurança).
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('login'))

    # Se for um request GET, apenas mostra a página de login.
    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Realiza o logout do usuário limpando todos os dados da sessão.
    """
    session.pop('colaborador_id', None)
    session.pop('colaborador_nome', None)
    session.pop('colaborador_perfil', None)
    session.pop('colaborador_setor_id', None)
    # session.clear() também funcionaria

    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))


@app.route('/perfil')
@login_required  # Protege a rota: Apenas usuários logados podem ver.
def perfil():
    """
    Exibe a página de perfil do usuário logado, buscando seus dados
    detalhados no banco de dados.
    """
    colaborador_id = session['colaborador_id']

    # Query mais completa para exibir informações de perfil,
    # incluindo o nome do setor e do gestor direto.
    query = """
            SELECT 
                c.id, 
                c.nome, 
                c.email, 
                c.usuario, 
                p.nome AS nome_perfil,
                c.status, 
                s.nome_setor,
                gestor.nome AS nome_gestor
            FROM 
                colaboradores AS c
            JOIN 
                setores AS s ON c.setor_id = s.id
            JOIN 
                perfis AS p ON c.perfil_id = p.id
            LEFT JOIN -- LEFT JOIN é usado caso um setor não tenha um gestor definido.
                colaboradores AS gestor ON s.gestor_id = gestor.id
            WHERE 
                c.id = %s
        """
    colaborador = db.execute_query(query, (colaborador_id,), fetch='one')

    if not colaborador:
        # Se o usuário não for encontrado (ex: deletado enquanto logado),
        # força o logout por segurança.
        return redirect(url_for('logout'))

    return render_template('perfil.html', colaborador=colaborador)


@app.route('/alterar-senha', methods=['GET', 'POST'])
@login_required  # Protege a rota
def alterar_senha():
    """
    Processa a lógica de alteração de senha do próprio usuário.
    GET: Mostra o formulário.
    POST: Valida a senha atual e atualiza para a nova.
    """
    colaborador_id = session['colaborador_id']

    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')

        # [1] Validação de entrada (input validation)
        if not all([senha_atual, nova_senha, confirmar_senha]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return redirect(url_for('alterar_senha'))

        if nova_senha != confirmar_senha:
            flash('A nova senha e a confirmação não coincidem.', 'danger')
            return redirect(url_for('alterar_senha'))

        if len(nova_senha) < 6:
            flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
            return redirect(url_for('alterar_senha'))

        # [2] Validação da senha atual
        query = "SELECT senha FROM colaboradores WHERE id = %s"
        colaborador = db.execute_query(query, (colaborador_id,), fetch='one')

        # Compara a senha digitada com a hash armazenada no banco
        if colaborador and bcrypt.checkpw(senha_atual.encode('utf-8'), colaborador['senha'].encode('utf-8')):

            # [3] Gera a nova hash e atualiza o banco
            nova_senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            update_query = "UPDATE colaboradores SET senha = %s WHERE id = %s"
            db.execute_query(update_query, (nova_senha_hash, colaborador_id))

            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('perfil'))
        else:
            flash('Senha atual incorreta.', 'danger')
            return redirect(url_for('alterar_senha'))

    # Se for um request GET, apenas mostra o formulário.
    return render_template('alterar_senha.html')


# =============================================================================
# Bloco 2: Rotas de CRUD (Create, Read, Update, Delete) de Atividades
# =============================================================================

@app.route('/registrar', methods=['GET', 'POST'])
@login_required  # Garante que apenas usuários logados possam registrar
def registrar_atividade():
    """
    Rota principal para o registro de novas atividades.

    GET: Exibe o formulário de registro e estatísticas pessoais do usuário.
    POST: Valida e insere os dados da nova atividade no banco.
    """
    colaborador_id = session['colaborador_id']

    # [1] Lógica de Inserção (POST)
    if request.method == 'POST':
        # Coleta de dados do formulário
        data_atendimento = request.form.get('data_atendimento')
        tipo_atendimento_id = request.form.get('tipo_atendimento')
        nivel = request.form.get('nivel')
        numero_atendimento = request.form.get('numero_atendimento')
        status = request.form.get('status')
        descricao = request.form.get('descricao')

        # Validação de campos obrigatórios no lado do servidor
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
            db.execute_query(query, params)  # 'fetch=None' é o padrão para INSERT/commit
            flash('Atividade registrada com sucesso!', 'success')
            return redirect(url_for('registrar_atividade'))
        except Exception as e:
            # Captura erros de banco (ex: violação de constraint)
            flash(f'Erro ao registrar atividade: {e}', 'danger')
            return redirect(url_for('registrar_atividade'))

    # [2] Lógica de Exibição (GET)
    # Busca dados para popular o formulário e os cards de estatísticas

    # Popula o <select> de tipos de atendimento
    query_tipos = "SELECT id, nome FROM tipos_atendimento ORDER BY nome"
    tipos_atendimento = db.execute_query(query_tipos, fetch='all') or []

    # Busca informações do colaborador logado para exibição
    query_colaborador = "SELECT c.nome, s.nome_setor, p.nome AS perfil FROM colaboradores c JOIN setores s ON c.setor_id = s.id JOIN perfis p ON c.perfil_id = p.id WHERE c.id = %s"
    colaborador_info = db.execute_query(query_colaborador, (colaborador_id,), fetch='one')

    # Busca estatísticas pessoais para os cards de performance
    stats_hoje = db.execute_query(
        "SELECT COUNT(*) AS total FROM atividades WHERE colaborador_id = %s AND DATE(data_atendimento) = CURDATE()",
        (colaborador_id,), fetch='one')['total']
    stats_mes = db.execute_query(
        "SELECT COUNT(*) AS total FROM atividades WHERE colaborador_id = %s AND MONTH(data_atendimento) = MONTH(CURDATE()) AND YEAR(data_atendimento) = YEAR(CURDATE())",
        (colaborador_id,), fetch='one')['total']
    stats_semana = db.execute_query(
        "SELECT COUNT(*) AS total FROM atividades WHERE colaborador_id = %s AND YEARWEEK(data_atendimento, 1) = YEARWEEK(CURDATE(), 1)",
        (colaborador_id,), fetch='one')['total']
    stats = {'hoje': stats_hoje, 'semana': stats_semana, 'mes': stats_mes}

    data_atual = date.today().isoformat()

    return render_template('registro_atividades.html',
                           tipos_atendimento=tipos_atendimento,
                           colaborador=colaborador_info,
                           stats=stats,
                           data_atual=data_atual)


@app.route('/editar_atividade/<int:id>', methods=['GET', 'POST'])
@login_required  # Usuário deve estar logado
def editar_atividade(id):
    """
    Processa a edição de uma atividade existente.
    Utiliza um sistema de permissão granular baseado na tabela 'perfil_permissoes'.

    GET: Exibe o formulário de edição pré-preenchido.
    POST: Valida e atualiza a atividade no banco.
    """
    user_id = session['colaborador_id']

    # [1] Verificação de Permissão Granular
    # Esta é uma verificação de autorização mais complexa que um simples decorator.
    # Ela consulta se o perfil do usuário tem a permissão específica 'editar_atividade'.
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

    # [2] Lógica de Atualização (POST)
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
            db.execute_query(query, params, fetch=None)  # Commit
            flash('Atividade atualizada com sucesso!', 'success')
            return redirect(url_for('historico'))
        except Exception as e:
            flash(f'Erro ao atualizar atividade: {e}', 'danger')

    # [3] Lógica de Exibição (GET)
    # Busca a atividade específica para pré-preencher o formulário
    query_atividade = "SELECT * FROM atividades WHERE id = %s"
    atividade = db.execute_query(query_atividade, (id,), fetch='one')

    if not atividade:
        flash('Atividade não encontrada.', 'danger')
        return redirect(url_for('historico'))

    tipos_atendimento = db.execute_query("SELECT id, nome FROM tipos_atendimento ORDER BY nome", fetch='all')

    return render_template('editar_atividade.html', atividade=atividade, tipos_atendimento=tipos_atendimento)


@app.route('/excluir/<int:id>', methods=['GET', 'POST'])
@login_required  # Usuário deve estar logado
def excluir_atividade(id):
    """
    Processa a exclusão de uma atividade individual.
    GET: Exibe uma página de confirmação (boa prática de UX).
    POST: Executa a exclusão.
    """
    user_id = session['colaborador_id']

    # [1] Verificação de Permissão Granular (similar à edição)
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

    # [2] Lógica de Exclusão (POST)
    if request.method == 'POST':
        try:
            db.execute_query("DELETE FROM atividades WHERE id = %s", (id,), fetch=None)  # Commit
            flash('Atividade excluída com sucesso!', 'success')
            return redirect(url_for('historico'))
        except Exception as e:
            flash(f'Erro ao excluir atividade: {e}', 'danger')
            return redirect(url_for('historico'))

    # [3] Lógica de Confirmação (GET)
    # Busca dados mínimos da atividade apenas para exibição na tela de confirmação.
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

    return render_template('excluir_atividade.html', atividade=atividade)


@app.route('/excluir-massa', methods=['POST'])
@login_required  # Usuário deve estar logado
def excluir_massa():
    """
    Processa a exclusão de múltiplas atividades de uma só vez (bulk delete).
    Esta rota só aceita POST por segurança.
    """
    user_id = session['colaborador_id']

    # [1] Verificação de Permissão (reutiliza a mesma permissão de exclusão)
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

    # [2] Coleta a lista de IDs do formulário
    # request.form.getlist() é usado para coletar múltiplos valores
    # de checkboxes com o mesmo 'name' (name="selecao_ids").
    ids_para_excluir = request.form.getlist('selecao_ids')

    if not ids_para_excluir:
        flash('Nenhum item selecionado para exclusão.', 'warning')
        return redirect(url_for('historico'))

    try:
        # [3] Construção segura da query de exclusão em massa
        # Cria uma string de placeholders (%s, %s, %s) com base no
        # número de IDs recebidos, para prevenir SQL Injection.
        placeholders = ','.join(['%s'] * len(ids_para_excluir))
        query = f"DELETE FROM atividades WHERE id IN ({placeholders})"

        # Converte a lista de strings de ID para uma tupla de inteiros
        db.execute_query(query, tuple(ids_para_excluir), fetch=None)  # Commit

        flash(f'{len(ids_para_excluir)} atividade(s) foram excluídas com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir atividades: {e}', 'danger')

    return redirect(url_for('historico'))


# =============================================================================
# Bloco 3: Rota de Relatório/Histórico com Filtro Dinâmico
# =============================================================================

@app.route('/historico')
@login_required  # Protegido, apenas usuários logados podem acessar
def historico():
    """
    Renderiza a página de histórico de atividades com filtros dinâmicos,
    paginação e filtragem de dados baseada em permissão de perfil.
    """

    # [1] Lógica de Paginação
    # Define a página atual (padrão 1) e o número de itens por página.
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 25  # Constante para definir o tamanho da página
    offset = (page - 1) * PER_PAGE

    # [2] Busca de Dados para Menus <select>
    # Carrega os dados que preenchem os formulários de filtro no HTML.
    tipos_atendimento = db.execute_query("SELECT nome FROM tipos_atendimento ORDER BY nome", fetch='all') or []
    lista_colaboradores = db.execute_query("SELECT id, nome FROM colaboradores ORDER BY nome", fetch='all') or []
    lista_setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []

    # [3] Construção de Query Dinâmica e Segura

    # A parte 'FROM ... JOIN ...' da query é fixa.
    base_query_from = """
        FROM atividades a
        JOIN tipos_atendimento t ON a.tipo_atendimento_id = t.id 
        JOIN colaboradores c ON a.colaborador_id = c.id 
        JOIN setores s ON c.setor_id = s.id
    """
    # 'where_clauses' armazena os trechos de SQL (ex: "t.nome = %s")
    where_clauses = []
    # 'params' armazena os valores correspondentes (prevenção de SQL Injection)
    params = []

    # [3.1] Filtro de Permissão (Data Scoping)
    # Aplica o primeiro e mais importante filtro: o escopo de dados do usuário.
    user_id = session['colaborador_id']
    user_profile = session['colaborador_perfil']

    if user_profile == 'Colaborador':
        # Colaborador só pode ver suas próprias atividades.
        where_clauses.append("a.colaborador_id = %s")
        params.append(user_id)

    elif user_profile == 'Gestor':
        # Gestor só pode ver atividades de colaboradores dos setores que ele gerencia.
        query_setores_gestor = "SELECT id FROM setores WHERE gestor_id = %s"
        setores_do_gestor = db.execute_query(query_setores_gestor, (user_id,), fetch='all')

        if setores_do_gestor:
            ids_setores = [s['id'] for s in setores_do_gestor]
            # Cria placeholders dinâmicos (%s, %s, ...) para a cláusula IN
            placeholders = ','.join(['%s'] * len(ids_setores))
            where_clauses.append(f"c.setor_id IN ({placeholders})")
            params.extend(ids_setores)
        else:
            # Caso de borda: Gestor sem setor não vê nada (segurança).
            where_clauses.append("1=0")  # Condição SQL falsy

    # Se for 'Administrador', nenhum filtro de permissão é aplicado (ele vê tudo).

    # [3.2] Filtros do Usuário (Query String)

    # Coleta todos os filtros da URL (ex: ?tipo_filtro=Atendimento)
    filtros_aplicados = {k: v for k, v in request.args.items() if k != 'page' and v}
    filtro_data_especial = request.args.get('filtro_data')

    # Adiciona dinamicamente as cláusulas WHERE com base nos filtros aplicados
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
        where_clauses.append("c.id = %s")
        params.append(filtros_aplicados['colaborador_filtro'])
    if filtros_aplicados.get('setor_filtro'):
        where_clauses.append("s.id = %s")
        params.append(filtros_aplicados['setor_filtro'])
    if filtros_aplicados.get('descricao_filtro'):
        where_clauses.append("a.descricao LIKE %s")
        params.append(f"%{filtros_aplicados['descricao_filtro']}%")

    # Filtro especial vindo do clique no card do Dashboard
    if filtro_data_especial == 'hoje':
        where_clauses.append("DATE(a.data_atendimento) = CURDATE()")
        # Atualiza o 'filtros_aplicados' para preencher os campos de data no HTML
        today_str = date.today().isoformat()
        filtros_aplicados['data_ini'] = today_str
        filtros_aplicados['data_fim'] = today_str

    # Constrói a string final do WHERE
    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # [4] Execução em Duas Etapas (Paginação)

    # Query 1: Conta o TOTAL de registros que correspondem aos filtros
    # (sem LIMIT/OFFSET) para calcular o número de páginas.
    count_query = "SELECT COUNT(a.id) AS total" + base_query_from + where_sql
    count_result = db.execute_query(count_query, tuple(params), fetch='one')
    total_records = count_result['total'] if count_result else 0
    total_pages = math.ceil(total_records / PER_PAGE) if total_records > 0 else 1

    # Query 2: Busca a PÁGINA ATUAL de dados, aplicando LIMIT e OFFSET.
    data_query = "SELECT a.id, a.data_atendimento, a.status, t.nome AS tipo_atendimento, a.numero_atendimento, a.descricao, c.nome AS colaborador_nome, s.nome_setor, a.nivel_complexidade" + base_query_from + where_sql + " ORDER BY a.data_atendimento DESC, a.id DESC LIMIT %s OFFSET %s"

    # Adiciona os parâmetros de paginação ao final da lista de parâmetros de filtro
    params_paginados = tuple(params + [PER_PAGE, offset])
    atividades = db.execute_query(data_query, params_paginados, fetch='all') or []

    # [5] Renderização
    # Envia os dados e os filtros de volta para o template.
    return render_template('historico.html',
                           lista_atividades=atividades,
                           tipos_atendimento=tipos_atendimento,
                           lista_colaboradores=lista_colaboradores,
                           lista_setores=lista_setores,
                           filtros_aplicados=filtros_aplicados,
                           current_page=page,
                           total_pages=total_pages)


# =============================================================================
# Bloco 4: Rotas de Gestão (Exclusivo para Administradores)
# =============================================================================

@app.route('/gestao/usuarios')
@admin_required  # Protege a rota, apenas Admins podem acessar
def gestao_usuarios():
    """
    Exibe a página de gerenciamento de usuários.
    Permite filtrar a lista de usuários por setor e perfil.
    """
    setor_filtro = request.args.get('setor_filtro', '')
    perfil_filtro = request.args.get('perfil_filtro', '')

    # [1] Construção da Query Dinâmica
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

    # [2] Busca de dados para os menus <select> de filtro e formulários
    perfis = db.execute_query("SELECT id, nome FROM perfis ORDER BY nome", fetch='all') or []
    setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []

    # Lógica para buscar as opções do campo ENUM 'cargo' diretamente do BD
    cargos_query = db.execute_query("SHOW COLUMNS FROM colaboradores LIKE 'cargo'", fetch='one')
    if cargos_query:
        import re
        cargo_type = cargos_query['Type']  # Ex: "enum('Op1','Op2')"
        cargo_options = re.findall(r"'(.*?)'", cargo_type)
        cargos = [{'cargo': cargo} for cargo in cargo_options]
    else:
        cargos = []

    return render_template('gestao_usuarios.html',
                           usuarios=usuarios,
                           perfis=perfis,
                           setores=setores,
                           cargos=cargos,
                           filtros_aplicados={'setor': setor_filtro, 'perfil': perfil_filtro})


@app.route('/gestao/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    """
    Processa a edição de um usuário.
    GET: Exibe o formulário de edição pré-preenchido.
    POST: Atualiza os dados do usuário.
    """

    # [1] Lógica de Atualização (POST)
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
            # Lógica condicional de senha:
            # A senha só é atualizada se o campo 'nova_senha' for preenchido.
            if nova_senha:
                senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                query = """
                    UPDATE colaboradores 
                    SET nome = %s, usuario = %s, email = %s, setor_id = %s, 
                        perfil_id = %s, cargo = %s, status = %s, senha = %s
                    WHERE id = %s
                """
                params = (nome, usuario, email, setor_id, perfil_id, cargo, status, senha_hash, id)
            else:
                # Se 'nova_senha' estiver vazio, a senha atual é mantida.
                query = """
                    UPDATE colaboradores 
                    SET nome = %s, usuario = %s, email = %s, setor_id = %s, 
                        perfil_id = %s, cargo = %s, status = %s
                    WHERE id = %s
                """
                params = (nome, usuario, email, setor_id, perfil_id, cargo, status, id)

            db.execute_query(query, params)
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('gestao_usuarios'))
        except Exception as e:
            flash(f'Erro ao atualizar usuário: {e}', 'danger')
            return redirect(url_for('editar_usuario', id=id))

    # [2] Lógica de Exibição (GET)
    # Busca os dados do usuário para preencher o formulário
    query_usuario = """
        SELECT c.id, c.nome, c.usuario, c.email, c.status, c.cargo,
               p.nome as perfil, s.nome_setor as setor,
               s.id as setor_id, p.id as perfil_id
        FROM colaboradores c
        JOIN perfis p ON c.perfil_id = p.id
        JOIN setores s ON c.setor_id = s.id
        WHERE c.id = %s
    """
    usuario = db.execute_query(query_usuario, (id,), fetch='one')

    if not usuario:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('gestao_usuarios'))

    # Busca dados para os menus <select>
    perfis = db.execute_query("SELECT id, nome FROM perfis ORDER BY nome", fetch='all') or []
    setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []
    cargos_query = db.execute_query("SHOW COLUMNS FROM colaboradores LIKE 'cargo'", fetch='one')
    if cargos_query:
        import re
        cargo_type = cargos_query['Type']
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
    """
    Processa a criação de um novo usuário.
    Esta rota só aceita POST e é chamada pelo formulário na pág. 'gestao_usuarios'.
    """
    nome = request.form.get('nome')
    usuario = request.form.get('usuario')
    email = request.form.get('email')
    setor_id = request.form.get('setor')
    perfil_id = request.form.get('perfil')
    cargo = request.form.get('cargo')
    status = request.form.get('status')
    senha = request.form.get('senha')

    try:
        # A senha é sempre obrigatória na criação e deve ser hasheada.
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        query = """
            INSERT INTO colaboradores 
            (nome, usuario, email, setor_id, perfil_id, cargo, status, senha)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (nome, usuario, email, setor_id, perfil_id, cargo, status, senha_hash)
        db.execute_query(query, params)

        flash('Usuário criado com sucesso!', 'success')
    except Exception as e:
        # Captura erros comuns (ex: 'usuario' ou 'email' duplicado)
        flash(f'Erro ao criar usuário: {e}', 'danger')

    return redirect(url_for('gestao_usuarios'))


@app.route('/gestao/tipos-atividades', methods=['GET', 'POST'])
@admin_required
def gestao_tipos_atividades():
    """
    Gerencia os Tipos de Atendimento (lista e cria novos).
    GET: Exibe a lista (com filtro).
    POST: Cria um novo tipo.
    """

    # [1] Lógica de Criação (POST)
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

    # [2] Lógica de Listagem (GET)
    filtro_nome = request.args.get('q', '')  # 'q' é um nome comum para "query" (busca)

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
    """
    Processa a edição de um Tipo de Atendimento.
    GET: Exibe o formulário de edição.
    POST: Atualiza o nome.
    """

    # [1] Lógica de Atualização (POST)
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

    # [2] Lógica de Exibição (GET)
    query = "SELECT id, nome FROM tipos_atendimento WHERE id = %s"
    tipo = db.execute_query(query, (id,), fetch='one')
    if not tipo:
        flash('Tipo de atividade não encontrado.', 'danger')
        return redirect(url_for('gestao_tipos_atividades'))

    return render_template('editar_tipo_atividade.html', tipo=tipo)


@app.route('/gestao/setores', methods=['GET', 'POST'])
@admin_required
def gestao_setores():
    """
    Gerencia os Setores (lista e cria novos).
    GET: Exibe a lista de setores e seus gestores.
    POST: Cria um novo setor.
    """

    # [1] Lógica de Criação (POST)
    if request.method == 'POST':
        nome_setor = request.form.get('nome_setor')
        gestor_id = request.form.get('gestor_id')

        # Converte para int ou None (para permitir 'Nenhum' gestor)
        gestor_id = int(gestor_id) if gestor_id else None

        if nome_setor:
            try:
                query = "INSERT INTO setores (nome_setor, gestor_id) VALUES (%s, %s)"
                db.execute_query(query, (nome_setor, gestor_id))
                flash('Setor criado com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao criar setor: {e}', 'danger')
        return redirect(url_for('gestao_setores'))

    # [2] Lógica de Listagem (GET)
    # Lista os setores e faz LEFT JOIN para buscar o nome do gestor (se houver)
    query_setores = """
        SELECT s.id, s.nome_setor, c.nome AS nome_gestor
        FROM setores s
        LEFT JOIN colaboradores c ON s.gestor_id = c.id
        ORDER BY s.nome_setor
    """
    setores = db.execute_query(query_setores, fetch='all') or []

    # Busca todos os colaboradores para o <select> de 'Gestor'
    query_colaboradores = "SELECT id, nome FROM colaboradores ORDER BY nome"
    colaboradores = db.execute_query(query_colaboradores, fetch='all') or []

    return render_template('gestao_setores.html', setores=setores, colaboradores=colaboradores)


@app.route('/gestao/setores/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_setor(id):
    """
    Processa a edição de um Setor.
    GET: Exibe o formulário de edição.
    POST: Atualiza o nome e o gestor associado.
    """

    # [1] Lógica de Atualização (POST)
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

    # [2] Lógica de Exibição (GET)
    query_setor = "SELECT id, nome_setor, gestor_id FROM setores WHERE id = %s"
    setor = db.execute_query(query_setor, (id,), fetch='one')
    if not setor:
        flash('Setor não encontrado.', 'danger')
        return redirect(url_for('gestao_setores'))

    query_colaboradores = "SELECT id, nome FROM colaboradores ORDER BY nome"
    colaboradores = db.execute_query(query_colaboradores, fetch='all') or []

    return render_template('editar_setor.html', setor=setor, colaboradores=colaboradores)


# =============================================================================
# Bloco 5: Dashboard, APIs e Lógica Global de Aplicação
# =============================================================================

# [1] Configuração do Cache do Dashboard
# -----------------------------------------------------------------------------
# Define um cache in-memory para o dashboard, reduzindo a carga no banco de dados
# em requisições repetidas.
dashboard_cache = {
    'Administrador': {'data': None, 'last_updated': None},
    'Gestor': {}  # O cache do Gestor é por ID (ex: 'Gestor': {'12': {...}, '15': {...}})
}
CACHE_DURATION_MINUTES = 60  # Define o tempo de vida do cache (em minutos)


def get_dados_extras_setor(db, setor_id):
    """
    Função auxiliar (helper) para buscar dados de BI específicos de um setor.
    Isso mantém a rota principal do dashboard mais limpa (Princípio DRY).

    :param db: A instância do banco de dados.
    :param setor_id: O ID do setor a ser consultado.
    :return: Um dicionário com os dados ('colaborador_top_setor', 'top_atividades_setor').
    """
    dados = {}
    hoje = datetime.now()
    ano_atual = hoje.year
    mes_atual = hoje.month
    params_gestor_mes = (setor_id, ano_atual, mes_atual)

    # Query: Colaborador com mais atividades no setor este mês
    query_destaque = """
        SELECT c.nome, COUNT(a.id) AS total_atividades
        FROM atividades a JOIN colaboradores c ON a.colaborador_id = c.id
        WHERE c.setor_id = %s AND YEAR(a.data_atendimento) = %s AND MONTH(a.data_atendimento) = %s
        GROUP BY c.id, c.nome ORDER BY total_atividades DESC LIMIT 1;
    """
    dados['colaborador_top_setor'] = db.execute_query(query_destaque, params_gestor_mes, fetch='one')

    # Query: Top 3 tipos de atividade mais comuns no setor este mês
    query_top_atividades = """
        SELECT ta.nome, COUNT(a.id) AS total
        FROM atividades a
        JOIN colaboradores c ON a.colaborador_id = c.id
        JOIN tipos_atendimento ta ON a.tipo_atendimento_id = ta.id
        WHERE c.setor_id = %s AND YEAR(a.data_atendimento) = %s AND MONTH(a.data_atendimento) = %s
        GROUP BY ta.id, ta.nome ORDER BY total DESC LIMIT 3;
    """
    dados['top_atividades_setor'] = db.execute_query(query_top_atividades, params_gestor_mes, fetch='all')

    return dados


# [2] Rota Principal do Dashboard
# -----------------------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    """
    Rota de BI (Business Intelligence) da aplicação.
    Agora suporta Filtros de Data Dinâmicos.
    """

    # --- [0] Captura e Tratamento de Datas (FILTROS) ---
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    hoje = date.today()

    # Se o usuário não escolheu datas, define o padrão (Dia 1 do mês até hoje)
    if data_inicio_str and data_fim_str:
        data_inicio = data_inicio_str
        data_fim = data_fim_str
    else:
        data_7_dias_atras = hoje - timedelta(days=7)
        data_inicio = data_7_dias_atras.strftime('%Y-%m-%d')
        data_fim = hoje.strftime('%Y-%m-%d')

    # Objeto para devolver ao HTML (preenche os inputs)
    filtros = {'data_inicio': data_inicio, 'data_fim': data_fim}

    # --- [Etapa 1: Lógica de Personificação] ---
    perfil_original = session.get('colaborador_perfil')
    user_id_original = session.get('colaborador_id')
    view_as_user_id = request.args.get('view_as_user_id')
    is_impersonating = False

    if perfil_original == 'Administrador' and view_as_user_id:
        query_gestor_alvo = "SELECT c.id, p.nome as perfil_nome FROM colaboradores c JOIN perfis p ON c.perfil_id = p.id WHERE c.id = %s"
        gestor_alvo = db.execute_query(query_gestor_alvo, (view_as_user_id,), fetch='one')
        if gestor_alvo and gestor_alvo['perfil_nome'] == 'Gestor':
            perfil = 'Gestor'
            user_id = gestor_alvo['id']
            is_impersonating = True
        else:
            perfil = perfil_original
            user_id = user_id_original
    else:
        perfil = perfil_original
        user_id = user_id_original

    # --- [Etapa 2: Cláusula de Guarda] ---
    if perfil_original == 'Colaborador':
        flash('Você não tem permissão para acessar o dashboard.', 'warning')
        return redirect(url_for('index'))

    # --- [Etapa 3: Verificação de Cache Inteligente] ---
    now = datetime.now()

    # ATENÇÃO: A chave do cache agora inclui as DATAS.
    # Isso impede que um filtro antigo apareça quando você muda a data.
    base_key = str(user_id) if perfil == 'Gestor' else perfil
    cache_key = f"{base_key}_{data_inicio}_{data_fim}"

    cache_data_source = dashboard_cache['Gestor'] if perfil == 'Gestor' else dashboard_cache
    cache_entry = cache_data_source.get(cache_key)

    if not is_impersonating and cache_entry and cache_entry.get('data') and \
            (now < cache_entry.get('last_updated') + timedelta(minutes=CACHE_DURATION_MINUTES)):
        print(f"INFO: Servindo dashboard via CACHE ({cache_key}).")
        template_data = cache_entry['data']

    else:
        # --- [Etapa 4: Coleta de Dados (Banco de Dados)] ---
        print(f"INFO: Gerando dashboard via BANCO para {cache_key}.")
        kpis = {}
        dados_extras = {}
        labels_grafico = []
        datasets_grafico = []

        # --- LÓGICA FORK: ADMINISTRADOR ---
        if perfil == 'Administrador':
            # KPIs Globais (Respeitando o filtro de data para o Total)
            kpis['total_atividades'] = db.execute_query(
                "SELECT COUNT(id) AS total FROM atividades WHERE DATE(data_atendimento) BETWEEN %s AND %s",
                (data_inicio, data_fim), fetch='one')['total']

            # Atividades "Hoje" continua sendo HOJE (independente do filtro, pois é um KPI de tempo real)
            kpis['atividades_hoje'] = db.execute_query(
                "SELECT COUNT(id) AS total FROM atividades WHERE DATE(data_atendimento) = CURDATE()",
                fetch='one')['total']

            kpis['total_colaboradores'] = db.execute_query(
                "SELECT COUNT(id) AS total FROM colaboradores WHERE status = 'Ativo'",
                fetch='one')['total']

            # Ranking Setor (Com Filtro de Data)
            query_setor_top = """
                SELECT s.nome_setor, COUNT(a.id) AS total_atividades 
                FROM atividades a 
                JOIN colaboradores c ON a.colaborador_id = c.id 
                JOIN setores s ON c.setor_id = s.id 
                WHERE DATE(a.data_atendimento) BETWEEN %s AND %s 
                GROUP BY s.nome_setor 
                ORDER BY total_atividades DESC LIMIT 1;
            """
            dados_extras['setor_mais_ativo'] = db.execute_query(query_setor_top, (data_inicio, data_fim), fetch='one')

            # Listas Globais
            query_colab_setor = "SELECT s.id, s.nome_setor, COUNT(c.id) AS total_colaboradores FROM colaboradores c JOIN setores s ON c.setor_id = s.id WHERE c.status = 'Ativo' GROUP BY s.id, s.nome_setor ORDER BY total_colaboradores DESC;"
            dados_extras['colaboradores_por_setor'] = db.execute_query(query_colab_setor, fetch='all')

            query_top_atividades = """
                SELECT ta.nome, COUNT(a.id) AS total 
                FROM atividades a 
                JOIN tipos_atendimento ta ON a.tipo_atendimento_id = ta.id 
                WHERE DATE(a.data_atendimento) BETWEEN %s AND %s 
                GROUP BY ta.id, ta.nome 
                ORDER BY total DESC LIMIT 3;
            """
            dados_extras['top_atividades'] = db.execute_query(query_top_atividades, (data_inicio, data_fim),
                                                              fetch='all')

            # GRÁFICO ADMIN (Dinâmico)
            query_grafico = """
                SELECT DATE(a.data_atendimento) as dia, s.nome_setor, COUNT(a.id) as total 
                FROM atividades a 
                JOIN colaboradores c ON a.colaborador_id = c.id 
                JOIN setores s ON c.setor_id = s.id 
                WHERE DATE(a.data_atendimento) BETWEEN %s AND %s 
                GROUP BY dia, s.nome_setor 
                ORDER BY dia ASC, s.nome_setor ASC;
            """
            dados_brutos_grafico = db.execute_query(query_grafico, (data_inicio, data_fim), fetch='all')

            # Processamento do Gráfico Admin
            if dados_brutos_grafico:
                # Gera eixo X baseado no intervalo selecionado
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                delta_days = (dt_fim - dt_inicio).days

                # Labels garantem que todos os dias apareçam, mesmo sem dados
                labels_grafico = [(dt_inicio + timedelta(days=i)).strftime('%d/%m') for i in range(delta_days + 1)]

                setores = sorted(list(set([d['nome_setor'] for d in dados_brutos_grafico])))
                dados_por_setor = {setor: [0] * len(labels_grafico) for setor in setores}

                for dado in dados_brutos_grafico:
                    dia_str = dado['dia'].strftime('%d/%m')
                    if dia_str in labels_grafico:
                        idx = labels_grafico.index(dia_str)
                        dados_por_setor[dado['nome_setor']][idx] = dado['total']

                cores = ['rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 206, 86, 0.7)',
                         'rgba(75, 192, 192, 0.7)', 'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)']

                for i, setor in enumerate(setores):
                    datasets_grafico.append({
                        'label': setor,
                        'data': dados_por_setor[setor],
                        'backgroundColor': cores[i % len(cores)]
                    })

        # --- LÓGICA FORK: GESTOR ---
        elif perfil == 'Gestor':
            query_setor = "SELECT id, nome_setor FROM setores WHERE gestor_id = %s"
            setor_gestor = db.execute_query(query_setor, (user_id,), fetch='one')

            if setor_gestor:
                setor_id = setor_gestor['id']
                dados_extras['setor_id_gestor'] = setor_id
                dados_extras['setor_nome_gestor'] = setor_gestor['nome_setor']

                # KPIs do Setor (Com Filtro de Data)
                kpis['total_atividades_setor'] = db.execute_query(
                    """SELECT COUNT(a.id) as total FROM atividades a 
                       JOIN colaboradores c ON a.colaborador_id = c.id 
                       WHERE c.setor_id = %s AND DATE(a.data_atendimento) BETWEEN %s AND %s""",
                    (setor_id, data_inicio, data_fim), fetch='one')['total']

                # Atividades "Hoje" mantém tempo real
                kpis['atividades_hoje_setor'] = db.execute_query(
                    """SELECT COUNT(a.id) as total FROM atividades a 
                       JOIN colaboradores c ON a.colaborador_id = c.id 
                       WHERE c.setor_id = %s AND DATE(a.data_atendimento) = CURDATE()""",
                    (setor_id,), fetch='one')['total']

                kpis['total_colaboradores_setor'] = db.execute_query(
                    "SELECT COUNT(id) as total FROM colaboradores WHERE setor_id = %s AND status='Ativo'",
                    (setor_id,), fetch='one')['total']

                # OBS: A função get_dados_extras_setor() é externa.
                # Se ela usar queries fixas de mês, ela pode não obedecer o filtro.
                if 'get_dados_extras_setor' in globals():
                    dados_extras.update(get_dados_extras_setor(db, setor_id))

                # GRÁFICO GESTOR (Dinâmico)
                query_grafico = """
                    SELECT DATE(a.data_atendimento) as dia, c.nome as colaborador, COUNT(a.id) as total 
                    FROM atividades a 
                    JOIN colaboradores c ON a.colaborador_id = c.id 
                    WHERE c.setor_id = %s AND DATE(a.data_atendimento) BETWEEN %s AND %s 
                    GROUP BY dia, colaborador 
                    ORDER BY dia ASC, colaborador ASC;
                """
                dados_brutos_grafico = db.execute_query(query_grafico, (setor_id, data_inicio, data_fim), fetch='all')

                # Processamento do Gráfico Gestor
                if dados_brutos_grafico:
                    dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                    dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                    delta_days = (dt_fim - dt_inicio).days

                    labels_grafico = [(dt_inicio + timedelta(days=i)).strftime('%d/%m') for i in range(delta_days + 1)]

                    colaboradores = sorted(list(set([d['colaborador'] for d in dados_brutos_grafico])))
                    dados_por_colab = {colab: [0] * len(labels_grafico) for colab in colaboradores}

                    for dado in dados_brutos_grafico:
                        dia_str = dado['dia'].strftime('%d/%m')
                        if dia_str in labels_grafico:
                            idx = labels_grafico.index(dia_str)
                            dados_por_colab[dado['colaborador']][idx] = dado['total']

                    cores = ['rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 206, 86, 0.7)',
                             'rgba(75, 192, 192, 0.7)', 'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)']

                    for i, colaborador in enumerate(colaboradores):
                        datasets_grafico.append({
                            'label': colaborador,
                            'data': dados_por_colab[colaborador],
                            'backgroundColor': cores[i % len(cores)]
                        })
            else:
                kpis.update({'total_atividades_setor': 0, 'atividades_hoje_setor': 0, 'total_colaboradores_setor': 0})
                dados_extras['setor_nome_gestor'] = "Nenhum Setor"

        # --- [Etapa 5: Consultas de Refinamento (Comum)] ---

        # Top 5 Colaboradores (Agora obedece o filtro de data)
        query_base_top_colab = """
            SELECT c.id, c.nome, COUNT(a.id) AS total_atividades 
            FROM atividades a 
            JOIN colaboradores c ON a.colaborador_id = c.id 
            WHERE DATE(a.data_atendimento) BETWEEN %s AND %s
        """
        params_top_colab = [data_inicio, data_fim]

        if perfil == 'Gestor' and 'setor_id' in locals() and setor_id:
            query_base_top_colab += " AND c.setor_id = %s"
            params_top_colab.append(setor_id)

        query_base_top_colab += " GROUP BY c.id, c.nome ORDER BY total_atividades DESC LIMIT 5;"
        dados_extras['top_colaboradores_mes'] = db.execute_query(query_base_top_colab, tuple(params_top_colab),
                                                                 fetch='all')

        # Texto do período para exibição
        try:
            dt_inicio_fmt = datetime.strptime(data_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
            dt_fim_fmt = datetime.strptime(data_fim, '%Y-%m-%d').strftime('%d/%m/%Y')
            dados_extras['mes_referencia'] = f"De {dt_inicio_fmt} até {dt_fim_fmt}"
        except:
            dados_extras['mes_referencia'] = "Período Selecionado"

        # --- [Etapa 6: Salvar no Cache] ---
        template_data = {
            'kpis': kpis,
            'dados_extras': dados_extras,
            'labels_grafico': labels_grafico,
            'datasets_grafico': datasets_grafico,
            'filtros': filtros  # Importante para o HTML não esquecer a data
        }

        if not is_impersonating:
            if perfil == 'Gestor':
                dashboard_cache['Gestor'][cache_key] = {'data': template_data, 'last_updated': now}
            else:
                dashboard_cache[perfil] = {'data': template_data, 'last_updated': now}

    # --- [Etapa 7: Preparação Final e Saída] ---
    gestores_disponiveis = []
    if perfil_original == 'Administrador':
        query_gestores = "SELECT c.id, c.nome, s.nome_setor as setor FROM colaboradores c JOIN perfis p ON c.perfil_id = p.id LEFT JOIN setores s ON c.setor_id = s.id WHERE p.nome = 'Gestor' AND c.status = 'Ativo' ORDER BY c.nome;"
        gestores_disponiveis = db.execute_query(query_gestores, fetch='all')

    template_data['gestores_disponiveis'] = gestores_disponiveis
    template_data['is_impersonating'] = is_impersonating

    # Garante que 'filtros' esteja no template_data mesmo vindo do cache
    if 'filtros' not in template_data:
        template_data['filtros'] = filtros

    return render_template('dashboard.html', **template_data)


# [3] API Endpoints (para o Modal Interativo do Dashboard)
# -----------------------------------------------------------------------------
@app.route('/api/atividades-hoje-por-setor')
@admin_required  # Apenas Admins podem ver dados de TODOS os setores
def api_atividades_hoje_por_setor():
    """
    Endpoint de API (JSON) que retorna a contagem de atividades de hoje,
    agrupada por setor. Usado pelo modal do dashboard do Admin (Estágio 1).
    """
    query = """
        SELECT s.id as setor_id, s.nome_setor, COUNT(a.id) as total
        FROM atividades a
        JOIN colaboradores c ON a.colaborador_id = c.id
        JOIN setores s ON c.setor_id = s.id
        WHERE DATE(a.data_atendimento) = CURDATE()
        GROUP BY s.id, s.nome_setor
        ORDER BY total DESC;
    """
    dados = db.execute_query(query, fetch='all') or []
    return jsonify(dados)


@app.route('/api/atividades-hoje-por-colaborador/<int:setor_id>')
@gestor_required  # Gestores (ou Admins) podem ver dados de colaboradores
def api_atividades_hoje_por_colaborador(setor_id):
    """
    Endpoint de API (JSON) que retorna a contagem de atividades de hoje
    para CADA colaborador de um setor específico.
    Usado pelo modal do dashboard (Estágio 2).

    Esta query é complexa pois usa um LEFT JOIN para incluir
    colaboradores com 0 atividades, o que é crucial para a visão do gestor.
    """
    query = """
        SELECT c.id, c.nome, COUNT(a.id) as total
        FROM colaboradores c
        LEFT JOIN atividades a ON c.id = a.colaborador_id 
                               AND DATE(a.data_atendimento) = CURDATE()
        WHERE c.setor_id = %s AND c.status = 'Ativo'
        GROUP BY c.id, c.nome
        ORDER BY total DESC, c.nome ASC;
    """
    dados = db.execute_query(query, (setor_id,), fetch='all') or []
    return jsonify(dados)


# [4] Processador de Contexto Global (para Gamificação/Medalhas)
# -----------------------------------------------------------------------------
@app.context_processor
def inject_user_medals():
    """
    Processador de Contexto do Flask.

    Esta função é executada AUTOMATICAMENTE antes de renderizar QUALQUER template.
    Seu objetivo é injetar dados globais (as medalhas) que o 'base.html'
    (e, portanto, todas as páginas) precisa para exibir o ranking do colaborador.
    """
    medals_data = {'medalha_setor': None, 'medalha_geral': None}

    # A lógica só é executada se o usuário logado for um 'Colaborador'
    if 'colaborador_id' in session and session['colaborador_perfil'] == 'Colaborador':
        user_id = session.get('colaborador_id')
        user_setor_id = session.get('colaborador_setor_id')

        if not user_setor_id:
            return medals_data  # Retorna vazio se o colab não tiver setor

        try:
            # Query 1: Ranking do Colaborador DENTRO DO SEU SETOR (Mês Atual)
            # RANK() é uma window function do SQL, eficiente para rankings.
            query_rank_setor = """
                SELECT user_rank FROM (
                    SELECT c.id, RANK() OVER (ORDER BY COUNT(a.id) DESC) as user_rank
                    FROM colaboradores c
                    LEFT JOIN atividades a ON c.id = a.colaborador_id 
                                           AND MONTH(a.data_atendimento) = MONTH(CURDATE()) 
                                           AND YEAR(a.data_atendimento) = YEAR(CURDATE())
                    WHERE c.setor_id = %s AND c.status = 'Ativo'
                    GROUP BY c.id
                ) as ranked_users
                WHERE id = %s;
            """
            rank_setor_result = db.execute_query(query_rank_setor, (user_setor_id, user_id), fetch='one')
            if rank_setor_result:
                medals_data['medalha_setor'] = rank_setor_result['user_rank']

            # Query 2: Ranking GERAL do Colaborador (Mês Atual)
            query_rank_geral = """
                SELECT user_rank FROM (
                    SELECT c.id, RANK() OVER (ORDER BY COUNT(a.id) DESC) as user_rank
                    FROM colaboradores c
                    LEFT JOIN atividades a ON c.id = a.colaborador_id 
                                           AND MONTH(a.data_atendimento) = MONTH(CURDATE()) 
                                           AND YEAR(a.data_atendimento) = YEAR(CURDATE())
                    WHERE c.status = 'Ativo'
                    GROUP BY c.id
                ) as ranked_users
                WHERE id = %s;
            """
            rank_geral_result = db.execute_query(query_rank_geral, (user_id,), fetch='one')
            if rank_geral_result:
                medals_data['medalha_geral'] = rank_geral_result['user_rank']

        except Exception as e:
            print(f"ERRO AO CALCULAR MEDALHAS: {e}")

    # O dicionário retornado é mesclado ao contexto do template globalmente.
    return medals_data


@app.route('/api/atividades-hoje-setor')
@login_required
def api_atividades_hoje_setor():
    """
    API que retorna os dados para o modal.
    - Administrador/Coordenador: Vê todos os setores.
    - Gestor: Vê APENAS o seu próprio setor.
    """
    try:
        # 1. Pegamos os dados de quem está logado
        usuario_id = session.get('colaborador_id')
        perfil_usuario = session.get('colaborador_perfil')

        # 2. Montamos a Query Base (O início é igual para todos)
        base_query = """
            SELECT 
                s.id, 
                s.nome_setor, 
                COUNT(a.id) as total
            FROM atividades a
            JOIN colaboradores c ON a.colaborador_id = c.id
            JOIN setores s ON c.setor_id = s.id
            WHERE DATE(a.data_atendimento) = CURDATE()
        """

        params = []

        # 3. Aplicamos o Filtro de Segurança baseado no Perfil
        if perfil_usuario == 'Gestor':
            # Se for Gestor, adicionamos uma trava:
            # "Onde o setor ID seja igual ao setor deste usuário"
            # Usamos uma subquery simples para pegar o setor do usuário logado
            base_query += " AND s.id = (SELECT setor_id FROM colaboradores WHERE id = %s) "
            params.append(usuario_id)

        elif perfil_usuario in ['Administrador', 'Coordenador']:
            # Se for Admin ou Coordenador, não fazemos nada extra.
            # Eles podem ver tudo.
            pass

        else:
            # Se for um perfil desconhecido (ex: Colaborador comum tentando acessar via URL)
            # Retorna vazio por segurança
            return jsonify([])

        # 4. Finalizamos a Query (Agrupamento e Ordem)
        base_query += """
            GROUP BY s.id, s.nome_setor
            ORDER BY total DESC
        """

        # 5. Executamos
        # Note que passamos 'params' (que pode ter o ID do gestor ou estar vazio)
        dados = db.execute_query(base_query, tuple(params), fetch='all')

        return jsonify(dados)

    except Exception as e:
        print(f"❌ Erro na API de Segurança: {e}")
        return jsonify({'error': 'Erro interno ao buscar dados'}), 500


# =============================================================================
# Bloco 7: O NOVO SISTEMA DE CRM (Atendimentos)
# (Este bloco é ADICIONADO ao sistema, não substitui nada por enquanto)
# =============================================================================
@app.route('/crm/iniciar', methods=['GET', 'POST'])
@login_required
def crm_iniciar_atendimento():
    """
    Rota principal para "Iniciar Triagem" (O novo "Registrar Atividade").
    [CORREÇÃO v5] - Corrige o bug de precisão de microsse segundos.
    """
    colaborador_id = session['colaborador_id']
    colaborador_setor_id = session['colaborador_setor_id']

    # [1] Lógica de Inserção (POST)
    if request.method == 'POST':
        try:
            # Dados da Triagem
            cliente_grupo_id = request.form.get('cliente_grupo')
            cliente_tipo_id = request.form.get('cliente_tipo')
            identificador = request.form.get('identificador_principal')
            cliente_nome = request.form.get('cliente_nome')
            cliente_email = request.form.get('cliente_email')
            cliente_telefone = request.form.get('cliente_telefone')

            origem_id = request.form.get('origem')
            tipo_atendimento_id = request.form.get('tipo_atendimento')
            titulo = request.form.get('titulo')
            descricao = request.form.get('descricao')

            nivel = request.form.get('nivel_complexidade', 'baixo')
            num_externo = request.form.get('numero_atendimento_externo')
            observacao = request.form.get('observacao')

            # Validação
            if not all([cliente_tipo_id, origem_id, tipo_atendimento_id, titulo, descricao, cliente_nome]):
                flash(
                    'Campos principais (Tipo Cliente, Nome, Origem, Tipo Atendimento, Título, Descrição) são obrigatórios.',
                    'danger')
                return redirect(url_for('crm_iniciar_atendimento'))

            # --- Início da Transação ---

            # Passo 1: Encontrar ou Criar o Cliente
            cliente_id = None
            if identificador:
                query_cliente = "SELECT id FROM clientes WHERE identificador_principal = %s"
                cliente_existente = db.execute_query(query_cliente, (identificador,), fetch='one')
                if cliente_existente:
                    cliente_id = cliente_existente['id']

            if not cliente_id:
                identificador_final = identificador
                if not identificador:
                    query_last_id = "SELECT MAX(id) AS max_id FROM clientes"
                    last_id = db.execute_query(query_last_id, fetch='one')['max_id'] or 0
                    identificador_final = f"INT-{last_id + 1:04d}"

                query_novo_cliente = """
                    INSERT INTO clientes (tipo_id, nome, email, telefone, identificador_principal)
                    VALUES (%s, %s, %s, %s, %s)
                """
                params_cliente = (cliente_tipo_id, cliente_nome, cliente_email, cliente_telefone, identificador_final)

                db.execute_query(query_novo_cliente, params_cliente, fetch=None)

                # Busca o ID que acabamos de criar
                cliente_id = db.execute_query(
                    "SELECT id FROM clientes WHERE identificador_principal = %s",
                    (identificador_final,),
                    fetch='one'
                )['id']

            # Passo 2: Criar o Atendimento (A "Capa")
            query_atendimento = """
                INSERT INTO atendimentos
                (titulo, status_fila, criador_id, responsavel_id, setor_responsavel_id, 
                 cliente_id, origem_id, tipo_atendimento_id, 
                 numero_atendimento_externo, observacao, nivel_complexidade, criado_em)
                VALUES (%s, 'Triagem', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # [A CORREÇÃO (v5) ESTÁ AQUI]
            # Remove os microsse segundos para garantir que o MySQL e o Python
            # vejam o mesmo carimbo de data/hora.
            timestamp_criacao = datetime.now().replace(microsecond=0)

            params_atendimento = (
                titulo, colaborador_id, colaborador_id, colaborador_setor_id,
                cliente_id, origem_id, tipo_atendimento_id,
                num_externo, observacao, nivel, timestamp_criacao
            )

            db.execute_query(query_atendimento, params_atendimento, fetch=None)

            # Busca o ID do atendimento que acabamos de criar,
            # usando a chave única (criador + timestamp)
            query_find_atendimento = """
                SELECT id FROM atendimentos 
                WHERE criador_id = %s AND criado_em = %s AND titulo = %s
                ORDER BY id DESC LIMIT 1
            """
            atendimento_criado = db.execute_query(
                query_find_atendimento,
                (colaborador_id, timestamp_criacao, titulo),
                fetch='one'
            )

            if not atendimento_criado:
                # Se ainda falhar, tentamos o LAST_INSERT_ID() como fallback
                # (embora seja propenso a falhas de pool)
                atendimento_id_fallback = db.execute_query("SELECT LAST_INSERT_ID() AS id", fetch='one')['id']
                if not (isinstance(atendimento_id_fallback, int) and atendimento_id_fallback > 0):
                    raise Exception("Falha ao criar o atendimento (ID não encontrado após o INSERT).")
                atendimento_id = atendimento_id_fallback
            else:
                atendimento_id = atendimento_criado['id']

            # Passo 3: Criar o Primeiro Histórico (A "Descrição")
            query_historico = """
                INSERT INTO atendimento_historico
                (atendimento_id, colaborador_id, tipo_acao, descricao)
                VALUES (%s, %s, 'Criacao', %s)
            """
            params_historico = (atendimento_id, colaborador_id, descricao)
            db.execute_query(query_historico, params_historico, fetch=None)

            # --- Fim da Transação ---

            flash('Atendimento iniciado e em triagem com sucesso!', 'success')
            return redirect(url_for('crm_fila_atendimento'))

        except Exception as e:
            # (Seu db.py precisa de um db.rollback() aqui em caso de erro)
            flash(f'Erro ao iniciar atendimento: {e}', 'danger')
            return redirect(url_for('crm_iniciar_atendimento'))

    # [2] Lógica de Exibição (GET)
    query_grupos = "SELECT id, nome FROM cliente_grupos ORDER BY nome"
    cliente_grupos = db.execute_query(query_grupos, fetch='all') or []
    query_origens = "SELECT id, nome FROM origens ORDER BY nome"
    origens = db.execute_query(query_origens, fetch='all') or []
    query_tipos = "SELECT id, nome FROM tipos_atendimento ORDER BY nome"
    tipos_atendimento = db.execute_query(query_tipos, fetch='all') or []

    return render_template('crm_iniciar_atendimento.html',
                           cliente_grupos=cliente_grupos,
                           origens=origens,
                           tipos_atendimento=tipos_atendimento)


# --- Rotas "Helper" (AJAX) para o formulário de Triagem ---

@app.route('/api/cliente-tipos/<int:grupo_id>')
@login_required
def crm_get_cliente_tipos_por_grupo(grupo_id):
    """
    Rota de API (AJAX) que o formulário de triagem usará.
    Quando o usuário selecionar "Cliente Externo", esta rota é chamada
    para popular o segundo dropdown com "Estudante" e "Polo".
    """
    query = "SELECT id, nome FROM cliente_tipos WHERE grupo_id = %s ORDER BY nome"
    tipos = db.execute_query(query, (grupo_id,), fetch='all') or []
    return jsonify(tipos)


@app.route('/api/cliente-buscar/<string:identificador>')
@login_required
def crm_buscar_cliente_por_identificador(identificador):
    """
    Rota de API (AJAX) que o formulário de triagem usará.
    Quando o usuário digitar um RA ou N° de Polo, esta rota busca
    se o cliente já existe para auto-preencher o nome/email/telefone.
    """
    query = """
        SELECT id, nome, email, telefone, tipo_id 
        FROM clientes 
        WHERE identificador_principal = %s
    """
    cliente = db.execute_query(query, (identificador,), fetch='one')
    if cliente:
        return jsonify(cliente)
    else:
        return jsonify(None), 404 # Retorna "Não encontrado"



@app.route('/crm/fila')
@login_required
def crm_fila_atendimento():
    """
    Renderiza a nova "Fila de Atendimento" (o novo "Histórico").
    [VERSÃO COMPLETA COM FILTROS AVANÇADOS]
    """

    # [1] Lógica de Paginação (Reaproveitada)
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 25
    offset = (page - 1) * PER_PAGE

    # [2] Busca de Dados para Menus <select> de FILTRO
    tipos_atendimento = db.execute_query("SELECT id, nome FROM tipos_atendimento ORDER BY nome", fetch='all') or []
    lista_colaboradores = db.execute_query("SELECT id, nome FROM colaboradores ORDER BY nome", fetch='all') or []
    lista_setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []

    # [3] Construção de Query Dinâmica e Segura
    base_query_from = """
            FROM atendimentos a
            LEFT JOIN tipos_atendimento t ON a.tipo_atendimento_id = t.id 
            LEFT JOIN colaboradores c_resp ON a.responsavel_id = c_resp.id 
            LEFT JOIN setores s ON a.setor_responsavel_id = s.id
            LEFT JOIN clientes cl ON a.cliente_id = cl.id
        """
    where_clauses = []
    params = []

    # [3.1] Filtro de Permissão (Data Scoping)
    user_id = session['colaborador_id']
    user_profile = session['colaborador_perfil']
    user_setor_id = session['colaborador_setor_id']

    if user_profile == 'Colaborador':
        where_clauses.append("a.setor_responsavel_id = %s")
        params.append(user_setor_id)

    elif user_profile == 'Gestor':
        query_setores_gestor = "SELECT id FROM setores WHERE gestor_id = %s"
        setores_do_gestor_raw = db.execute_query(query_setores_gestor, (user_id,), fetch='all')
        setores_visiveis = {s['id'] for s in setores_do_gestor_raw}
        setores_visiveis.add(user_setor_id)
        ids_setores = list(setores_visiveis)

        if ids_setores:
            placeholders = ','.join(['%s'] * len(ids_setores))
            where_clauses.append(f"a.setor_responsavel_id IN ({placeholders})")
            params.extend(ids_setores)
        else:
            where_clauses.append("1=0")

    # [3.2] Filtro de Status (O mais importante)
    filtros_aplicados = {k: v for k, v in request.args.items() if k != 'page' and v}
    filtro_status_req = filtros_aplicados.get('filtro_status')
    filtro_status_aplicado = []

    if filtro_status_req == 'finalizados':
        filtro_status_aplicado = ['Resolvido', 'Fechado', 'Cancelado']
    elif filtro_status_req == 'todos':
        pass
    else:
        filtro_status_aplicado = ['Triagem', 'Em fila', 'Em atendimento', 'Aguardando']

    if filtro_status_aplicado:
        placeholders = ','.join(['%s'] * len(filtro_status_aplicado))
        where_clauses.append(f"a.status_fila IN ({placeholders})")
        params.extend(filtro_status_aplicado)

    # [3.3] FILTROS AVANÇADOS
    if filtros_aplicados.get('filtro_titulo'):
        where_clauses.append("a.titulo LIKE %s")
        params.append(f"%{filtros_aplicados.get('filtro_titulo')}%")
    if filtros_aplicados.get('tipo_filtro'):
        where_clauses.append("a.tipo_atendimento_id = %s")
        params.append(filtros_aplicados.get('tipo_filtro'))
    if filtros_aplicados.get('data_ini'):
        where_clauses.append("DATE(a.criado_em) >= %s")
        params.append(filtros_aplicados.get('data_ini'))
    if filtros_aplicados.get('data_fim'):
        where_clauses.append("DATE(a.criado_em) <= %s")
        params.append(filtros_aplicados.get('data_fim'))
    if filtros_aplicados.get('colaborador_filtro'):
        where_clauses.append("a.responsavel_id = %s")
        params.append(filtros_aplicados.get('colaborador_filtro'))
    if filtros_aplicados.get('setor_filtro'):
        where_clauses.append("a.setor_responsavel_id = %s")
        params.append(filtros_aplicados.get('setor_filtro'))
    if filtros_aplicados.get('cliente_nome_filtro'):
        where_clauses.append("cl.nome LIKE %s")
        params.append(f"%{filtros_aplicados.get('cliente_nome_filtro')}%")
    if filtros_aplicados.get('cliente_id_filtro'):
        where_clauses.append("cl.identificador_principal LIKE %s")
        params.append(f"%{filtros_aplicados.get('cliente_id_filtro')}%")

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # [4] Execução
    count_query = "SELECT COUNT(a.id) AS total" + base_query_from + where_sql
    count_result = db.execute_query(count_query, tuple(params), fetch='one')
    total_records = count_result['total'] if count_result else 0
    total_pages = math.ceil(total_records / PER_PAGE) if total_records > 0 else 1
    data_query = """
        SELECT 
            a.id, a.titulo, a.status_fila, 
            a.criado_em,  -- <<< [ADICIONADO]
            a.ultima_atualizacao,
            t.nome AS tipo_atendimento, 
            c_resp.nome AS responsavel_nome, 
            s.nome_setor,
            cl.nome AS cliente_nome
    """ + base_query_from + where_sql + " ORDER BY a.ultima_atualizacao DESC LIMIT %s OFFSET %s"

    params_paginados = tuple(params + [PER_PAGE, offset])
    atendimentos = db.execute_query(data_query, params_paginados, fetch='all') or []

    # [5] Renderização
    return render_template('crm_fila_atendimento.html',
                           lista_atendimentos=atendimentos,
                           tipos_atendimento=tipos_atendimento,
                           lista_colaboradores=lista_colaboradores,
                           lista_setores=lista_setores,
                           filtros_aplicados=filtros_aplicados,
                           current_page=page,
                           total_pages=total_pages)


@app.route('/crm/atendimento/<int:atendimento_id>', methods=['GET', 'POST'])
@login_required
def crm_detalhe_atendimento(atendimento_id):
    """
    Exibe a tela de "Detalhe do Atendimento" (o "hub" de trabalho).
    GET: Mostra os detalhes e o histórico (linha do tempo).
    POST: Processa as ações (comentar, encaminhar, mudar status).
    """
    colaborador_id = session['colaborador_id']
    user_profile = session['colaborador_perfil']
    user_setor_id = session['colaborador_setor_id']

    # Pega o nome do colaborador logado para os logs
    colaborador_nome = session.get('colaborador_nome', 'Usuário')

    # =========================================================================
    # [1] LÓGICA DE AÇÕES (POST)
    # =========================================================================
    if request.method == 'POST':
        try:
            acao = request.form.get('acao')
            if not acao:
                raise Exception("Ação não especificada.")

            # --- AÇÃO 1: Comentário e/ou Status Interno ---
            if acao == 'comentario':
                descricao = request.form.get('descricao')
                novo_status_interno = request.form.get('novo_status_interno')

                query_atual = "SELECT status_interno FROM atendimentos WHERE id = %s"
                atendimento_atual = db.execute_query(query_atual, (atendimento_id,), fetch='one')
                status_interno_antigo = atendimento_atual['status_interno']

                descricao_existe = bool(descricao)
                status_mudou = novo_status_interno != status_interno_antigo

                if not descricao_existe and not status_mudou:
                    flash('Nenhuma alteração detectada.', 'warning')
                    return redirect(url_for('crm_detalhe_atendimento', atendimento_id=atendimento_id))

                # Atualiza Status Interno
                query_update_atendimento = """
                    UPDATE atendimentos SET status_interno = %s, ultima_atualizacao = %s WHERE id = %s
                """
                db.execute_query(query_update_atendimento, (novo_status_interno, datetime.now(), atendimento_id),
                                 fetch=None)

                # Log Comentário
                if descricao_existe:
                    query_historico = """
                        INSERT INTO atendimento_historico (atendimento_id, colaborador_id, tipo_acao, descricao)
                        VALUES (%s, %s, 'Comentario', %s)
                    """
                    db.execute_query(query_historico, (atendimento_id, colaborador_id, descricao), fetch=None)

                # Log Mudança Status
                if status_mudou:
                    log_status = f"[Status Interno alterado de '{status_interno_antigo}' para '{novo_status_interno}' por {colaborador_nome}.]"
                    query_historico_status = """
                        INSERT INTO atendimento_historico (atendimento_id, colaborador_id, tipo_acao, descricao)
                        VALUES (%s, %s, 'Comentario', %s)
                    """
                    db.execute_query(query_historico_status, (atendimento_id, colaborador_id, log_status), fetch=None)

                flash('Atendimento atualizado com sucesso!', 'success')

            # --- AÇÃO 2: Comentar e Resolver (com PDS) ---
            elif acao == 'resolver':
                descricao = request.form.get('descricao')
                gerar_pds_val = request.form.get('gerar_pds')
                status_interno_final = 'Encerrado'

                pds_gerar_flag = 1 if gerar_pds_val == '1' else 0
                pds_status_val = 'Pendente' if pds_gerar_flag == 1 else 'Nao Aplicavel'

                if descricao:
                    query_hist_desc = "INSERT INTO atendimento_historico (atendimento_id, colaborador_id, tipo_acao, descricao) VALUES (%s, %s, 'Comentario', %s)"
                    db.execute_query(query_hist_desc, (atendimento_id, colaborador_id, descricao), fetch=None)

                pds_log_msg = 'Sim' if pds_gerar_flag == 1 else 'Nao'
                hist_msg_res = f"[ATENDIMENTO RESOLVIDO] {colaborador_nome} resolveu o ticket. Gerar PDS: {pds_log_msg}."
                query_hist_res = "INSERT INTO atendimento_historico (atendimento_id, colaborador_id, tipo_acao, descricao) VALUES (%s, %s, 'Comentario', %s)"
                db.execute_query(query_hist_res, (atendimento_id, colaborador_id, hist_msg_res), fetch=None)

                query_resolver = """
                    UPDATE atendimentos
                    SET status_fila = 'Resolvido', status_interno = %s, pds_gerar = %s, pds_status = %s, ultima_atualizacao = %s
                    WHERE id = %s
                """
                db.execute_query(query_resolver,
                                 (status_interno_final, pds_gerar_flag, pds_status_val, datetime.now(), atendimento_id),
                                 fetch=None)

                if pds_gerar_flag == 1:
                    novo_token = str(uuid.uuid4())
                    query_criar_pds = "INSERT INTO pesquisas_satisfacao (atendimento_id, token, status, criado_em) VALUES (%s, %s, 'Pendente', %s)"
                    db.execute_query(query_criar_pds, (atendimento_id, novo_token, datetime.now()), fetch=None)

                flash('Atendimento resolvido com sucesso!', 'success')

            # --- AÇÃO 3: Mudar Status (Macro) ---
            elif acao == 'mudar_status':
                novo_status = request.form.get('novo_status')
                if not novo_status: raise Exception("Novo status não foi selecionado.")

                query_status_atual = "SELECT status_fila FROM atendimentos WHERE id = %s"
                atendimento_atual = db.execute_query(query_status_atual, (atendimento_id,), fetch='one')
                status_antigo = atendimento_atual['status_fila']

                if status_antigo == novo_status:
                    flash('O atendimento já está com este status.', 'warning')
                    return redirect(url_for('crm_detalhe_atendimento', atendimento_id=atendimento_id))

                if novo_status in ['Resolvido', 'Fechado', 'Cancelado']:
                    novo_token = str(uuid.uuid4())
                    query_update_status = """
                        UPDATE atendimentos
                        SET status_fila = %s, status_interno = 'Encerrado', pds_status = 'Pendente', pds_gerar = 1, ultima_atualizacao = %s
                        WHERE id = %s
                    """
                    db.execute_query(query_update_status, (novo_status, datetime.now(), atendimento_id), fetch=None)

                    query_criar_pds = "INSERT INTO pesquisas_satisfacao (atendimento_id, token, status, criado_em) VALUES (%s, %s, 'Pendente', %s)"
                    db.execute_query(query_criar_pds, (atendimento_id, novo_token, datetime.now()), fetch=None)
                else:
                    query_update_status = "UPDATE atendimentos SET status_fila = %s, ultima_atualizacao = %s WHERE id = %s"
                    db.execute_query(query_update_status, (novo_status, datetime.now(), atendimento_id), fetch=None)

                descricao_log = f"[MUDANÇA DE STATUS] Status alterado de '{status_antigo}' para '{novo_status}' por {colaborador_nome}."
                query_historico_status = "INSERT INTO atendimento_historico (atendimento_id, colaborador_id, tipo_acao, descricao) VALUES (%s, %s, 'Comentario', %s)"
                db.execute_query(query_historico_status, (atendimento_id, colaborador_id, descricao_log), fetch=None)

                flash(f'Status atualizado para "{novo_status}" com sucesso!', 'success')

            # --- AÇÃO 4: Encaminhar ---
            elif acao == 'encaminhar':
                novo_setor_id = request.form.get('encaminhar_setor')
                if not novo_setor_id: raise Exception("Nenhum setor de destino selecionado.")

                query_setor_novo = "SELECT nome_setor FROM setores WHERE id = %s"
                setor_novo_obj = db.execute_query(query_setor_novo, (novo_setor_id,), fetch='one')
                novo_setor_nome = setor_novo_obj['nome_setor'] if setor_novo_obj else "Setor Desconhecido"

                query_setor_antigo = "SELECT s.nome_setor FROM atendimentos a JOIN setores s ON a.setor_responsavel_id = s.id WHERE a.id = %s"
                setor_antigo_obj = db.execute_query(query_setor_antigo, (atendimento_id,), fetch='one')
                setor_antigo_nome = setor_antigo_obj['nome_setor'] if setor_antigo_obj else "Setor Anterior"

                query_update_encaminhar = """
                    UPDATE atendimentos
                    SET status_fila = 'Em fila', sector_responsavel_id = %s, responsavel_id = criador_id, ultima_atualizacao = %s
                    WHERE id = %s
                """
                # OBS: Ajustei sector_responsavel_id para setor_responsavel_id caso seja erro de digitação
                query_update_encaminhar = query_update_encaminhar.replace("sector_responsavel_id",
                                                                          "setor_responsavel_id")

                db.execute_query(query_update_encaminhar, (novo_setor_id, datetime.now(), atendimento_id), fetch=None)

                descricao_log = f"[ENCAMINHADO] {colaborador_nome} encaminhou o atendimento do setor '{setor_antigo_nome}' para '{novo_setor_nome}'."
                query_historico_encaminhar = "INSERT INTO atendimento_historico (atendimento_id, colaborador_id, tipo_acao, descricao) VALUES (%s, %s, 'Comentario', %s)"
                db.execute_query(query_historico_encaminhar, (atendimento_id, colaborador_id, descricao_log),
                                 fetch=None)

                flash(f'Atendimento encaminhado para "{novo_setor_nome}"!', 'success')
                return redirect(url_for('crm_fila_atendimento'))

            # --- AÇÃO 5: Mudar Responsável ---
            elif acao == 'mudar_responsavel':
                novo_responsavel_id = request.form.get('novo_responsavel')
                if not novo_responsavel_id: raise Exception("Nenhum novo responsável selecionado.")

                query_resp_antigo = "SELECT c.nome FROM atendimentos a JOIN colaboradores c ON a.responsavel_id = c.id WHERE a.id = %s"
                resp_antigo_obj = db.execute_query(query_resp_antigo, (atendimento_id,), fetch='one')
                resp_antigo_nome = resp_antigo_obj['nome'] if resp_antigo_obj else "Ninguém"

                query_resp_novo = "SELECT nome FROM colaboradores WHERE id = %s"
                resp_novo_obj = db.execute_query(query_resp_novo, (novo_responsavel_id,), fetch='one')
                resp_novo_nome = resp_novo_obj['nome'] if resp_novo_obj else "Desconhecido"

                query_update_responsavel = "UPDATE atendimentos SET responsavel_id = %s, ultima_atualizacao = %s WHERE id = %s"
                db.execute_query(query_update_responsavel, (novo_responsavel_id, datetime.now(), atendimento_id),
                                 fetch=None)

                descricao_log = f"[RE-ATRIBUÍDO] {colaborador_nome} mudou o responsável de '{resp_antigo_nome}' para '{resp_novo_nome}'."
                query_historico_reatribuir = "INSERT INTO atendimento_historico (atendimento_id, colaborador_id, tipo_acao, descricao) VALUES (%s, %s, 'Comentario', %s)"
                db.execute_query(query_historico_reatribuir, (atendimento_id, colaborador_id, descricao_log),
                                 fetch=None)

                flash(f'Atendimento reatribuído para {resp_novo_nome} com sucesso!', 'success')

            # --- AÇÃO 6: Assumir ---
            elif acao == 'assumir':
                query_update_assumir = "UPDATE atendimentos SET status_fila = 'Em atendimento', responsavel_id = %s, ultima_atualizacao = %s WHERE id = %s"
                db.execute_query(query_update_assumir, (colaborador_id, datetime.now(), atendimento_id), fetch=None)

                descricao_log = f"[ASSUMIU] {colaborador_nome} assumiu este atendimento."
                query_historico_assumir = "INSERT INTO atendimento_historico (atendimento_id, colaborador_id, tipo_acao, descricao) VALUES (%s, %s, 'Comentario', %s)"
                db.execute_query(query_historico_assumir, (atendimento_id, colaborador_id, descricao_log), fetch=None)

                flash('Você assumiu este atendimento!', 'success')

        except Exception as e:
            flash(f'Erro ao processar a ação: {e}', 'danger')

        return redirect(url_for('crm_detalhe_atendimento', atendimento_id=atendimento_id))

    # =========================================================================
    # [2] LÓGICA DE EXIBIÇÃO (GET)
    # =========================================================================

    query_atendimento = """
        SELECT 
            a.*,
            cl.nome AS cliente_nome, cl.email AS cliente_email, cl.telefone AS cliente_telefone,
            cl.identificador_principal AS cliente_identificador,
            ct.nome AS cliente_tipo_nome, cg.nome AS cliente_grupo_nome,
            c_criador.nome AS criador_nome, c_resp.nome AS responsavel_nome,
            s_resp.nome_setor AS setor_responsavel_nome,
            t_atend.nome AS tipo_atendimento_nome, o.nome AS origem_nome
        FROM atendimentos a
        LEFT JOIN clientes cl ON a.cliente_id = cl.id
        LEFT JOIN cliente_tipos ct ON cl.tipo_id = ct.id
        LEFT JOIN cliente_grupos cg ON ct.grupo_id = cg.id
        LEFT JOIN colaboradores c_criador ON a.criador_id = c_criador.id
        LEFT JOIN colaboradores c_resp ON a.responsavel_id = c_resp.id
        LEFT JOIN setores s_resp ON a.setor_responsavel_id = s_resp.id
        LEFT JOIN tipos_atendimento t_atend ON a.tipo_atendimento_id = t_atend.id
        LEFT JOIN origens o ON a.origem_id = o.id
        WHERE a.id = %s
    """
    atendimento = db.execute_query(query_atendimento, (atendimento_id,), fetch='one')

    if not atendimento:
        flash('Atendimento não encontrado.', 'danger')
        return redirect(url_for('crm_fila_atendimento'))

    # Permissões
    pode_ver = False
    if user_profile == 'Administrador':
        pode_ver = True
    elif user_profile == 'Gestor':
        query_setores_gestor = "SELECT id FROM setores WHERE gestor_id = %s"
        setores_do_gestor_raw = db.execute_query(query_setores_gestor, (colaborador_id,), fetch='all')
        setores_visiveis = {s['id'] for s in setores_do_gestor_raw}
        setores_visiveis.add(user_setor_id)
        if atendimento['setor_responsavel_id'] in setores_visiveis: pode_ver = True
    elif user_profile == 'Colaborador':
        if atendimento['setor_responsavel_id'] == user_setor_id: pode_ver = True

    if not pode_ver:
        flash('Você não tem permissão para ver este atendimento.', 'danger')
        return redirect(url_for('crm_fila_atendimento'))

    # Histórico
    query_historico = """
        SELECT h.*, c.nome AS colaborador_nome
        FROM atendimento_historico h
        JOIN colaboradores c ON h.colaborador_id = c.id
        WHERE h.atendimento_id = %s
        ORDER BY h.timestamp ASC
    """
    historico = db.execute_query(query_historico, (atendimento_id,), fetch='all') or []

    # Listas para formulários
    lista_setores = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []
    lista_colaboradores_setor = db.execute_query(
        "SELECT id, nome FROM colaboradores WHERE setor_id = %s AND status = 'Ativo' ORDER BY nome",
        (atendimento['setor_responsavel_id'],), fetch='all'
    ) or []

    pds_info = None
    if atendimento['pds_gerar'] == 1:
        query_pds = """
            SELECT token, status, q1_demanda_atendida, q2_nota_atendimento 
            FROM pesquisas_satisfacao 
            WHERE atendimento_id = %s 
            LIMIT 1
        """
        pds_info = db.execute_query(query_pds, (atendimento_id,), fetch='one')

    return render_template('crm_detalhe_atendimento.html',
                           atendimento=atendimento,
                           historico=historico,
                           lista_setores=lista_setores,
                           lista_colaboradores_setor=lista_colaboradores_setor,
                           pds_info=pds_info)
# =============================================================================
# [NOVA ROTA] Gestão de Grupos e Tipos de Cliente
# =============================================================================
@app.route('/admin/gestao_clientes', methods=['GET', 'POST'])
@admin_required
def admin_gestao_clientes():
    """
    [Admin] Permite gerir os Grupos de Cliente e os Tipos de Cliente.
    GET: Mostra os formulários e as listas.
    POST: Processa criação, edição e exclusão.
    """

    if request.method == 'POST':
        try:
            acao = request.form.get('acao')

            # --- Criar Grupo ---
            if acao == 'criar_grupo':
                nome_grupo = request.form.get('nome_grupo')
                if not nome_grupo:
                    raise Exception("O nome do grupo não pode estar vazio.")
                query = "INSERT INTO cliente_grupos (nome) VALUES (%s)"
                db.execute_query(query, (nome_grupo,), fetch=None)
                flash(f"Grupo '{nome_grupo}' criado com sucesso!", 'success')

            # --- Criar Tipo ---
            elif acao == 'criar_tipo':
                nome_tipo = request.form.get('nome_tipo')
                grupo_id = request.form.get('grupo_id')
                if not nome_tipo or not grupo_id:
                    raise Exception("Campos obrigatórios não preenchidos.")
                query = "INSERT INTO cliente_tipos (nome, grupo_id) VALUES (%s, %s)"
                db.execute_query(query, (nome_tipo, grupo_id), fetch=None)
                flash(f"Tipo '{nome_tipo}' criado com sucesso!", 'success')

            # --- Excluir Grupo ---
            elif acao == 'excluir_grupo':
                grupo_id = request.form.get('grupo_id')
                if not grupo_id:
                    raise Exception("ID do grupo não informado.")
                query = "DELETE FROM cliente_grupos WHERE id = %s"
                db.execute_query(query, (grupo_id,), fetch=None)
                flash("Grupo excluído com sucesso!", 'success')

            # --- Excluir Tipo ---
            elif acao == 'excluir_tipo':
                tipo_id = request.form.get('tipo_id')
                if not tipo_id:
                    raise Exception("ID do tipo não informado.")
                query = "DELETE FROM cliente_tipos WHERE id = %s"
                db.execute_query(query, (tipo_id,), fetch=None)
                flash("Tipo excluído com sucesso!", 'success')

        except Exception as e:
            flash(f'Erro ao processar a ação: {e}', 'danger')

        return redirect(url_for('admin_gestao_clientes'))

    # --- GET ---
    query_grupos = "SELECT * FROM cliente_grupos ORDER BY nome"
    grupos = db.execute_query(query_grupos, fetch='all') or []

    query_tipos = """
        SELECT ct.*, cg.nome AS grupo_nome
        FROM cliente_tipos ct
        JOIN cliente_grupos cg ON ct.grupo_id = cg.id
        ORDER BY cg.nome, ct.nome
    """
    tipos = db.execute_query(query_tipos, fetch='all') or []

    return render_template('admin_gestao_clientes.html',
                           grupos=grupos,
                           tipos=tipos)


# =============================================================================
# [NOVA ROTA] Gestão de Origens de Contato
# =============================================================================
@app.route('/admin/gestao_origens', methods=['GET', 'POST'])
@admin_required
def admin_gestao_origens():
    """
    [Admin] Permite gerir as Origens de Contato (Telefone, E-mail, etc.)
    """

    if request.method == 'POST':
        try:
            acao = request.form.get('acao')

            # --- Criar ---
            if acao == 'criar':
                nome_origem = request.form.get('nome_origem')
                if not nome_origem:
                    raise Exception("O nome da origem não pode estar vazio.")
                query = "INSERT INTO origens (nome) VALUES (%s)"
                db.execute_query(query, (nome_origem,), fetch=None)
                flash(f"Origem '{nome_origem}' criada com sucesso!", 'success')

            # --- Editar ---
            elif acao == 'editar':
                origem_id = request.form.get('origem_id')
                nome_origem = request.form.get('nome_origem')
                if not nome_origem or not origem_id:
                    raise Exception("Dados insuficientes para editar.")
                query = "UPDATE origens SET nome = %s WHERE id = %s"
                db.execute_query(query, (nome_origem, origem_id), fetch=None)
                flash(f"Origem atualizada para '{nome_origem}'!", 'success')

            # --- Excluir ---
            elif acao == 'excluir':
                origem_id = request.form.get('origem_id')
                if not origem_id:
                    raise Exception("ID da origem não informado.")
                query = "DELETE FROM origens WHERE id = %s"
                db.execute_query(query, (origem_id,), fetch=None)
                flash("Origem excluída com sucesso!", 'success')

        except Exception as e:
            flash(f'Erro ao processar a ação: {e}', 'danger')

        return redirect(url_for('admin_gestao_origens'))

    # --- GET ---
    query_origens = "SELECT * FROM origens ORDER BY nome"
    origens = db.execute_query(query_origens, fetch='all') or []

    return render_template('admin_gestao_origens.html',
                           origens=origens)



# =============================================================================
# [FASE 4] Rota de Histórico do Cliente (Busca)
# =============================================================================
@app.route('/crm/historico_cliente', methods=['GET'])
@login_required
def crm_historico_cliente():
    """
    Exibe a página de "Histórico do Cliente".
    Implementa lógica profissional de desambiguação:
    1. Se achar 1 cliente -> Abre direto.
    2. Se achar vários -> Mostra lista para escolha.
    3. Se busca for ID exato -> Abre direto.
    """

    # --- 1. Captura Parâmetros ---
    termo_busca = request.args.get('termo_busca', '').strip()
    filtro_setor_id = request.args.get('filtro_setor_id', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    # Variáveis de Retorno
    cliente_encontrado = None
    lista_clientes_ambiguos = []
    atendimentos_do_cliente = []

    # Lista de setores para o dropdown do filtro
    lista_setores_todos = db.execute_query("SELECT id, nome_setor FROM setores ORDER BY nome_setor", fetch='all') or []

    if termo_busca:
        try:
            # --- 2. Estratégia de Busca Inteligente ---

            candidatos = []

            # A) Se o termo for numérico, tenta achar pelo ID exato primeiro (prioridade máxima)
            # Isso serve para quando o usuário clica em "Selecionar" na lista de homônimos
            if termo_busca.isdigit():
                query_id = "SELECT id, nome, identificador_principal, email, telefone FROM clientes WHERE id = %s"
                candidato_id = db.execute_query(query_id, (termo_busca,), fetch='one')
                if candidato_id:
                    candidatos = [candidato_id]  # Transforma em lista para usar a logica abaixo

            # B) Se não achou por ID (ou não é número), busca por Nome ou Documento (Busca Ampla)
            if not candidatos:
                query_busca = """
                    SELECT id, nome, identificador_principal, email, telefone 
                    FROM clientes 
                    WHERE identificador_principal = %s OR nome LIKE %s
                    LIMIT 20 
                """
                # LIMIT 20 previne travar o banco se alguém buscar "a"
                termo_like = f"%{termo_busca}%"
                candidatos = db.execute_query(query_busca, (termo_busca, termo_like), fetch='all') or []

            # --- 3. Tomada de Decisão (O "Cérebro" da Rota) ---

            if len(candidatos) == 1:
                # CENÁRIO PERFEITO: Só existe um cliente com esse dado.
                cliente_encontrado = candidatos[0]

            elif len(candidatos) > 1:
                # CENÁRIO DE AMBIGUIDADE: Existem homônimos.
                # Não carregamos histórico ainda. Enviamos a lista para o HTML.
                lista_clientes_ambiguos = candidatos
                flash(
                    f'Encontramos {len(candidatos)} clientes com termos parecidos. Por favor, selecione o correto abaixo.',
                    'warning')

            else:
                # CENÁRIO VAZIO
                flash(f'Nenhum cliente encontrado para "{termo_busca}".', 'info')

            # --- 4. Se temos UM cliente definido, carregamos o histórico ---
            if cliente_encontrado:
                query_atendimentos = """
                    SELECT 
                        id, titulo, status_fila, status_interno, criado_em, ultima_atualizacao,
                        pds_gerar, pds_status,
                        ROUND(TIME_TO_SEC(TIMEDIFF(ultima_atualizacao, criado_em)) / 3600, 1) AS duracao_horas
                    FROM atendimentos
                    WHERE cliente_id = %s
                """
                params = [cliente_encontrado['id']]

                # Filtros Opcionais
                if filtro_setor_id:
                    query_atendimentos += " AND setor_responsavel_id = %s"
                    params.append(filtro_setor_id)

                if data_inicio:
                    query_atendimentos += " AND criado_em >= %s"
                    params.append(data_inicio)

                if data_fim:
                    query_atendimentos += " AND criado_em <= %s"
                    params.append(f"{data_fim} 23:59:59")

                query_atendimentos += " ORDER BY criado_em DESC"

                atendimentos_do_cliente = db.execute_query(query_atendimentos, tuple(params), fetch='all') or []

                if not atendimentos_do_cliente:
                    flash('Cliente localizado, mas não há histórico de atendimentos com os filtros atuais.', 'info')

        except Exception as e:
            print(f"Erro no CRM: {e}")  # Log no terminal para você ver
            flash(f'Erro ao processar busca: {str(e)}', 'danger')

    # --- 5. Renderização ---
    return render_template('crm_historico_cliente.html',
                           termo_busca=termo_busca,
                           filtro_setor_id=filtro_setor_id,
                           data_inicio=data_inicio,
                           data_fim=data_fim,
                           lista_setores_todos=lista_setores_todos,
                           # Passamos as variáveis cruciais:
                           cliente=cliente_encontrado,
                           atendimentos=atendimentos_do_cliente,
                           lista_clientes_ambiguos=lista_clientes_ambiguos)


# =============================================================================
# [PASSO 3] Rota da Pesquisa de Satisfação (PDS)
# =============================================================================

# Esta rota é PÚBLICA (sem @login_required)
# A segurança é feita pelo token UUID
@app.route('/pds/responder/<token>', methods=['GET', 'POST'])
def pds_responder(token):
    """
    Exibe e processa a pesquisa de satisfação.
    Usa o nome da tabela 'pesquisas_satisfacao'.
    """

    # 1. Buscar a PDS pelo token na sua tabela
    query_pds = """
        SELECT id, atendimento_id, status 
        FROM pesquisas_satisfacao 
        WHERE token = %s
    """
    pds = db.execute_query(query_pds, (token,), fetch='one')

    # 2. Se o token não existe ou a pesquisa já foi respondida
    if not pds or pds['status'] == 'Respondida':
        flash('Esta pesquisa é inválida ou já foi respondida.', 'danger')
        return redirect(url_for('pds_obrigado'))

    # 3. Buscar o título do atendimento (para mostrar ao cliente)
    atendimento = db.execute_query(
        "SELECT id, titulo FROM atendimentos WHERE id = %s",
        (pds['atendimento_id'],),
        fetch='one'
    )

    # --- LÓGICA POST (Quando o cliente envia o formulário) ---
    if request.method == 'POST':
        try:
            # A. Pegar os dados da PDS e do Atendimento
            pds_id = pds['id']
            atendimento_id = pds['atendimento_id']

            # B. Pegar as 3 respostas do formulário
            q1 = request.form.get('q1')  # Agora virá 'Sim', 'Não' ou 'Parcialmente'
            q2 = request.form.get('q2')

            if not q1 or not q2:
                flash('Por favor, responda todas as perguntas.', 'warning')
                return render_template('pds_responder.html', atendimento=atendimento, token=token)

            # C. Salvar (UPDATE) na sua tabela 'pesquisas_satisfacao'
            query_update_pds = """
                UPDATE pesquisas_satisfacao
                SET 
                    q1_demanda_atendida = %s,
                    q2_nota_atendimento = %s,
                    status = 'Respondida',
                    data_resposta = %s
                WHERE id = %s
            """
            db.execute_query(query_update_pds, (q1, q2, datetime.now(), pds_id), fetch=None)

            # D. Atualizar o 'atendimentos' para "Respondida" (para os filtros)
            query_update_atendimento = "UPDATE atendimentos SET pds_status = 'Respondida' WHERE id = %s"
            db.execute_query(query_update_atendimento, (atendimento_id,), fetch=None)

            flash('Sua resposta foi enviada com sucesso. Obrigado!', 'success')
            return redirect(url_for('pds_obrigado'))

        except Exception as e:
            flash(f'Erro ao salvar sua resposta: {e}', 'danger')
            # Não redireciona, fica na página para tentar de novo

    # --- LÓGICA GET (Mostrar a página da pesquisa) ---
    return render_template('pds_responder.html',
                           atendimento=atendimento,
                           token=token)


@app.route('/pds/obrigado')
def pds_obrigado():
    """
    Página de "Obrigado" após a pesquisa.
    """
    return render_template('pds_obrigado.html')


@app.route('/crm/clientes')
@login_required
def crm_lista_clientes():
    """
    Carteira de Clientes com Filtros Avançados (Cascata).
    """
    # 1. Captura Parâmetros
    busca = request.args.get('busca', '').strip()
    filtro_grupo = request.args.get('filtro_grupo', '')
    filtro_tipo = request.args.get('filtro_tipo', '')

    pagina = request.args.get('page', 1, type=int)
    itens_por_pagina = 20
    offset = (pagina - 1) * itens_por_pagina

    # 2. Carregar listas para os Dropdowns
    lista_grupos = db.execute_query("SELECT id, nome FROM cliente_grupos ORDER BY nome", fetch='all') or []

    # Se já tiver um grupo selecionado (após filtrar), carregamos os tipos dele para o dropdown não vir vazio
    lista_tipos_preenchidos = []
    if filtro_grupo:
        lista_tipos_preenchidos = db.execute_query(
            "SELECT id, nome FROM cliente_tipos WHERE grupo_id = %s ORDER BY nome", (filtro_grupo,), fetch='all') or []

    # 3. Montagem da Query de Clientes
    # Precisamos do JOIN com cliente_tipos para filtrar pelo Grupo
    base_query = """
        FROM clientes c
        LEFT JOIN cliente_tipos ct ON c.tipo_id = ct.id
        LEFT JOIN cliente_grupos cg ON ct.grupo_id = cg.id
    """

    condicoes = []
    params = []

    # Filtro de Texto (Busca)
    if busca:
        condicoes.append("(c.nome LIKE %s OR c.identificador_principal LIKE %s OR c.email LIKE %s)")
        termo = f"%{busca}%"
        params.extend([termo, termo, termo])

    # Filtro de Grupo (Indireto via JOIN)
    if filtro_grupo:
        condicoes.append("ct.grupo_id = %s")
        params.append(filtro_grupo)

    # Filtro de Tipo (Direto na tabela clientes ou tipos)
    if filtro_tipo:
        condicoes.append("c.tipo_id = %s")
        params.append(filtro_tipo)

    # Monta o WHERE se houver condições
    clausula_where = ""
    if condicoes:
        clausula_where = "WHERE " + " AND ".join(condicoes)

    # Query 1: Contagem Total (para paginação)
    query_count = f"SELECT COUNT(c.id) as total {base_query} {clausula_where}"
    total_registros = db.execute_query(query_count, tuple(params), fetch='one')['total']
    total_paginas = math.ceil(total_registros / itens_por_pagina)

    # Query 2: Buscar Dados (Incluindo nomes do tipo e grupo para exibir na tabela se quiser)
    query_dados = f"""
        SELECT 
            c.id, c.nome, c.identificador_principal, c.email, c.telefone,
            ct.nome as nome_tipo, cg.nome as nome_grupo
        {base_query}
        {clausula_where}
        ORDER BY c.nome ASC
        LIMIT %s OFFSET %s
    """
    params.append(itens_por_pagina)
    params.append(offset)

    clientes = db.execute_query(query_dados, tuple(params), fetch='all') or []

    return render_template('crm_lista_clientes.html',
                           clientes=clientes,
                           busca=busca,
                           filtro_grupo=filtro_grupo,
                           filtro_tipo=filtro_tipo,
                           lista_grupos=lista_grupos,
                           lista_tipos_preenchidos=lista_tipos_preenchidos,
                           pagina_atual=pagina,
                           total_paginas=total_paginas,
                           total_registros=total_registros)

@app.route('/api/tipos_por_grupo/<int:grupo_id>')
@login_required
def api_tipos_por_grupo(grupo_id):
    """
    Retorna JSON com os tipos de cliente pertencentes a um grupo.
    Usado pelo Javascript do filtro em cascata.
    """
    query = "SELECT id, nome FROM cliente_tipos WHERE grupo_id = %s ORDER BY nome"
    tipos = db.execute_query(query, (grupo_id,), fetch='all') or []
    return jsonify(tipos)