# Arquivo: app.py (Versão Final da Aula 5)

from flask import Flask, render_template, request
from utils.db import Database

app = Flask(__name__)
db = Database()


@app.route('/')
def home():
    # --- Parte 1: Buscando dados para os filtros ---
    tipos_atendimento = db.execute_query("SELECT nome FROM tipos_atendimento ORDER BY nome", fetch='all')
    if tipos_atendimento is None:
        tipos_atendimento = []

    # --- Parte 2: Lendo os filtros enviados pelo usuário na URL ---
    # request.args contém os dados do formulário enviado com GET
    tipo_filtro = request.args.get('tipo_filtro', '')  # Pega o valor ou uma string vazia
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')

    # --- Parte 3: Construindo a consulta SQL dinamicamente ---
    base_query = """
        SELECT a.id, a.data_atendimento, a.status, t.nome AS tipo_atendimento, 
               a.numero_atendimento, a.descricao, c.nome AS colaborador_nome, s.nome_setor 
        FROM atividades a
        JOIN tipos_atendimento t ON a.tipo_atendimento_id = t.id 
        JOIN colaboradores c ON a.colaborador_id = c.id 
        JOIN setores s ON c.setor_id = s.id
    """
    where_clauses = []
    params = []

    if tipo_filtro:
        where_clauses.append("t.nome = %s")
        params.append(tipo_filtro)
    if data_ini:
        where_clauses.append("a.data_atendimento >= %s")
        params.append(data_ini)
    if data_fim:
        where_clauses.append("a.data_atendimento <= %s")
        params.append(data_fim)

    if where_clauses:
        final_query = base_query + " WHERE " + " AND ".join(where_clauses)
    else:
        final_query = base_query

    final_query += " ORDER BY a.data_atendimento DESC, a.id DESC LIMIT 100"

    atividades = db.execute_query(final_query, tuple(params), fetch='all')
    if atividades is None:
        atividades = []

    # --- Parte 4: Enviando os resultados E os filtros usados de volta para a página ---
    filtros_aplicados = {
        'tipo': tipo_filtro,
        'data_ini': data_ini,
        'data_fim': data_fim
    }

    return render_template('index.html',
                           lista_atividades=atividades,
                           tipos_atendimento=tipos_atendimento,
                           filtros_aplicados=filtros_aplicados)


if __name__ == '__main__':
    app.run(debug=True)