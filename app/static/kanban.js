// ==========================================
// 1. CONFIGURAÇÃO E ESTADO GLOBAL
// ==========================================

// Mapa de Ícones por Setor (Ajuste conforme seus nomes exatos no banco)
const mapaIcones = {
    'DIRETORIA ADMINISTRATIVA': 'fa-briefcase',
    'Tesouraria EAD': 'fa-chart-line',
    'Central de Negociações EAD': 'fa-hand-holding-usd',
    'Processo Seletivo EAD': 'fa-users',
    'Secretaria Acadêmica EAD': 'fa-graduation-cap',
    'SUPORTE TÉCNICO EAD': 'fa-laptop-code',
    'Tecnologia': 'fa-microchip',
    'Atendimento EAD': 'fa-headset',
    'UNINTAFLIX': 'fa-play-circle',
    'Comercial': 'fa-bullhorn',
    'Recursos Humanos': 'fa-user-tie'
};
// --- NOVO: Função para Gerar Avatar (Foto ou Inicial) ---
function gerarAvatarHTML(nome, fotoUrl, tamanho = '') {
    // Classes CSS base
    const cssClass = tamanho === 'small' ? 'kb-avatar-small' : 'kb-avatar';
    const cssSize = tamanho === 'grande' ? 'kb-avatar-grande' : cssClass;

    if (fotoUrl) {
        // Se tiver foto, retorna a tag IMG
        return `<img src="${fotoUrl}" class="${cssSize} rounded-circle border border-white shadow-sm" style="object-fit: cover;" title="${nome}">`;
    } else {
        // Se não tiver, retorna a bolinha com a inicial
        const inicial = nome ? nome[0].toUpperCase() : '?';
        return `<div class="${cssSize} bg-primary text-white d-flex align-items-center justify-content-center rounded-circle border border-white shadow-sm mx-auto" title="${nome}">
                    ${inicial}
                </div>`;
    }
}
const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,
    didOpen: (toast) => {
        toast.addEventListener('mouseenter', Swal.stopTimer)
        toast.addEventListener('mouseleave', Swal.resumeTimer)
    }
});

// Estado da Navegação
let estadoAtual = {
    view: 'setores',
    setor: null,
    colaborador: null,
    colaboradorId: null
};

// Variáveis Globais
let quill; // Editor de texto
let quillEdit;
let draggedItem = null; // Para Drag & Drop
let todosColaboradoresCache = []; // Cache para busca
let selecionadosIds = new Set(); // IDs dos responsáveis selecionados


// ==========================================
// 2. INICIALIZAÇÃO E EVENTOS
// ==========================================
document.addEventListener('DOMContentLoaded', function() {

    // 1. Carrega a primeira tela
    carregarSetores();

    // --- ADICIONE ISTO AQUI (Chama a notificação de novidades) ---
    verificarNovidades();

    // 2. Botão Voltar
    const btnVoltar = document.getElementById('btn-voltar');
    if(btnVoltar) btnVoltar.addEventListener('click', voltar);

    // 3. Configura a busca de colaboradores (Modal)
    const inputBusca = document.getElementById('buscaColaborador');
    if (inputBusca) {
        inputBusca.addEventListener('input', filtrarColaboradores);

        // Fecha o dropdown se clicar fora
        document.addEventListener('click', function(e) {
            const lista = document.getElementById('listaResultados');
            if (lista && e.target.id !== 'buscaColaborador') {
                lista.style.display = 'none';
            }
        });
    }

    // 4. Inicializa o Editor Quill (Apenas se o container existir)
    if(document.getElementById('editor-container')) {
        quill = new Quill('#editor-container', {
            theme: 'snow',
            modules: {
                toolbar: [
                    ['bold', 'italic', 'underline'], // Negrito, Itálico...
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }], // Listas
                    [{ 'header': [1, 2, false] }], // Títulos
                    ['clean'] // Limpar formatação
                ]
            },
            placeholder: 'Descreva os detalhes da tarefa aqui...'
        });
    }

    // --- NOVO BLOCO DO EDITOR DE EDIÇÃO (LOGO ABAIXO, MESMO NÍVEL) ---
    if(document.getElementById('editor-container-edit')) {
        quillEdit = new Quill('#editor-container-edit', {
            theme: 'snow',
            modules: {
                toolbar: [
                    ['bold', 'italic', 'underline'],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    [{ 'header': [1, 2, false] }],
                    ['clean']
                ]
            },
            placeholder: 'Edite os detalhes da tarefa...'
        });
    }
    // Feedback visual do anexo
    const inputAnexo = document.getElementById('inputAnexo');
    if(inputAnexo) {
        inputAnexo.addEventListener('change', function(e) {
            const feedback = document.getElementById('feedbackAnexo');
            if (this.files && this.files[0]) {
                feedback.innerHTML = `<i class="fas fa-check-circle"></i> Arquivo selecionado: ${this.files[0].name}`;
            } else {
                feedback.innerText = '';
            }
        });
    }
});


// ==========================================
// 3. NAVEGAÇÃO ENTRE TELAS
// ==========================================
function navegarPara(viewId) {
    // Esconde todas as views
    ['view-setores', 'view-colaboradores', 'view-kanban'].forEach(id => {
        const el = document.getElementById(id);
        if(el) el.style.display = 'none';
    });

    // Mostra a view alvo
    const viewAlvo = document.getElementById(viewId);
    if(viewAlvo) viewAlvo.style.display = 'block';

    // Ajusta Breadcrumbs e Botões
    const btnVoltar = document.getElementById('btn-voltar');
    const btnMaster = document.getElementById('btn-master'); // Botão Visão Geral
    const bread = document.getElementById('kb-breadcrumbs');

    if (viewId === 'view-setores') {
        if(btnVoltar) btnVoltar.style.display = 'none';
        if(btnMaster) btnMaster.style.display = 'inline-block';
        if(bread) bread.innerText = 'Selecione um Setor';
        estadoAtual.view = 'setores';
    }
    else if (viewId === 'view-colaboradores') {
        if(btnVoltar) btnVoltar.style.display = 'inline-block';
        if(btnMaster) btnMaster.style.display = 'inline-block';
        if(bread) bread.innerText = `Setor: ${estadoAtual.setor}`;
        estadoAtual.view = 'colaboradores';
    }
    else if (viewId === 'view-kanban') {
        if(btnVoltar) btnVoltar.style.display = 'inline-block';
        if(btnMaster) btnMaster.style.display = 'none';
        if(bread) bread.innerText = `Tarefas de ${estadoAtual.colaborador}`;
        estadoAtual.view = 'kanban';
    }
}

function voltar() {
    // Se estiver vendo colaboradores, volta pra setores
    if (estadoAtual.view === 'colaboradores') {
        navegarPara('view-setores');
    }
    // Se estiver no kanban INDIVIDUAL, volta para colaboradores
    else if (estadoAtual.view === 'kanban' && estadoAtual.colaboradorId) {
        navegarPara('view-colaboradores');
    }
    // NOVO: Se estiver no Master, volta para setores (Home)
    else if (estadoAtual.view === 'kanban' && !estadoAtual.colaboradorId) {
         navegarPara('view-setores');
    }
}


// ==========================================
// 4. LÓGICA DE SETORES (Corrigida e Segura)
// ==========================================
function carregarSetores() {
    console.log("Iniciando busca de setores...");

    fetch('/api/kanban/setores')
        .then(r => {
            if (!r.ok) throw new Error("Erro na requisição: " + r.status);
            return r.json();
        })
        .then(data => {
            console.log("Dados recebidos dos setores:", data);

            const container = document.getElementById('grid-setores');
            if(!container) return;
            container.innerHTML = '';

            // Verificação de segurança: garante que data é um Array
            if (!Array.isArray(data)) {
                console.error("Erro: API não retornou uma lista", data);
                container.innerHTML = '<div class="col-12 text-danger">Erro ao carregar dados. Verifique o console.</div>';
                return;
            }

            if (data.length === 0) {
                container.innerHTML = '<div class="col-12 text-center text-muted py-5"><p>Nenhum setor encontrado.</p></div>';
                return;
            }

            data.forEach(setor => {
                // O Python agora retorna 'nome' (alias de nome_setor)
                const nomeSetor = setor.nome || setor.nome_setor;
                const qtd = setor.qtd_colaboradores;
                const iconeClass = mapaIcones[nomeSetor.trim()] || 'fa-building';

                container.innerHTML += `
                    <div class="col-12 col-md-4 col-lg-3">
                        <div class="kb-nav-card" onclick="selecionarSetor('${nomeSetor}')">
                            <div class="mb-2"><i class="fas ${iconeClass} fa-2x text-primary opacity-75"></i></div>
                            <h6 class="fw-bold text-dark mb-2 text-truncate" title="${nomeSetor}">${nomeSetor}</h6>
                            <div class="kb-badge small"><i class="fas fa-users me-1"></i> ${qtd} Colab.</div>
                        </div>
                    </div>`;
            });
        })
        .catch(err => {
            console.error("Erro CRÍTICO ao buscar setores:", err);
            const container = document.getElementById('grid-setores');
            if(container) container.innerHTML = '<div class="text-danger p-3">Erro de conexão com o servidor.</div>';
        });
}

window.selecionarSetor = function(nomeSetor) {
    estadoAtual.setor = nomeSetor;
    const container = document.getElementById('grid-colaboradores');

    navegarPara('view-colaboradores');
    container.innerHTML = '<div class="col-12 text-center py-5"><div class="spinner-border text-primary"></div></div>';

    // Codifica a URL para evitar erros com espaços ou caracteres especiais
    fetch(`/api/kanban/colaboradores/${encodeURIComponent(nomeSetor)}`)
        .then(r => r.json())
        .then(data => {
            container.innerHTML = '';

            if(!Array.isArray(data) || data.length === 0) {
                container.innerHTML = '<div class="col-12 text-center text-muted">Nenhum colaborador ativo neste setor.</div>';
                return;
            }

            data.forEach(c => {
                // CORREÇÃO: Usando a função geradora e a variável 'c.foto' (URL correta do Python)
                // O 'grande' define o estilo CSS da tela de seleção
                const avatarHtml = gerarAvatarHTML(c.nome, c.foto, 'grande');

                container.innerHTML += `
                    <div class="col-6 col-md-4 col-lg-3">
                        <div class="kb-nav-card" onclick="carregarKanban(${c.id}, '${c.nome}')">
                            <div class="mb-3 d-flex justify-content-center">
                                ${avatarHtml}
                            </div>
                            <h6 class="fw-bold text-dark mb-1 text-truncate">${c.nome}</h6>
                            <small class="text-muted">Ver Quadro</small>
                        </div>
                    </div>`;
            });
        })
        .catch(err => {
            console.error(err);
            container.innerHTML = '<div class="text-danger">Erro ao carregar colaboradores.</div>';
        });
}


// ==========================================
// 5. LÓGICA DO KANBAN (QUADRO)
// ==========================================
window.carregarKanban = function(colabId, colabNome) {
    // 1. Configura estado e variáveis
    estadoAtual.colaboradorId = colabId; // Importante para o "Nova Tarefa" saber quem é o dono
    estadoAtual.colaborador = colabNome;

    if(colabNome) document.getElementById('titulo-kanban-colaborador').innerText = `Quadro de ${colabNome}`;

    // 2. Limpa as colunas antes de carregar
    const colFazer = document.getElementById('col-fazer');
    const colAndamento = document.getElementById('col-andamento');
    const colConcluido = document.getElementById('col-concluido');

    colFazer.innerHTML = '<div class="spinner-border spinner-border-sm text-muted"></div>';
    colAndamento.innerHTML = '';
    colConcluido.innerHTML = '';

    // 3. A CORREÇÃO PRINCIPAL ESTÁ AQUI:
    // Precisamos mandar o navegador mostrar a tela do Kanban
    navegarPara('view-kanban');

    // 4. Chama a API
    fetch(`/api/kanban/tarefas/${colabId}`)
        .then(response => response.json())
        .then(tarefas => {

            // Limpa o loading
            colFazer.innerHTML = '';
            colAndamento.innerHTML = '';
            colConcluido.innerHTML = '';

            if (!tarefas || tarefas.length === 0) {
                // Opcional: Mostrar aviso de "Nenhuma tarefa"
                return;
            }

            // 5. Loop para desenhar os cards
            tarefas.forEach(t => {
                const cardElemento = criarCardTarefa(t);

                // Verifica o status e joga na coluna certa
                // O trim() ajuda a evitar erros se vier com espaço do banco
                const status = t.status ? t.status.trim() : '';

                if (status === 'a_fazer') {
                    colFazer.appendChild(cardElemento);
                }
                else if (status === 'em_andamento') {
                    colAndamento.appendChild(cardElemento);
                }
                else if (status === 'concluido') {
                    colConcluido.appendChild(cardElemento);
                }
                else {
                    // Isso ajuda a descobrir se tem tarefa com status errado no banco
                    console.warn("Tarefa com status desconhecido ignorada:", t.titulo, t.status);
                }
            });
        })
        .catch(erro => {
            console.error("Erro ao carregar:", erro);
            colFazer.innerHTML = '<p class="text-danger">Erro ao carregar tarefas.</p>';
        });
};

function criarCardTarefa(t) {
    const div = document.createElement('div');

    // 1. Adicionamos 'cursor-pointer' para indicar que é clicável
    div.className = `kb-task-card priority-${t.prioridade}`;
    div.style.cursor = 'pointer';

    div.setAttribute('draggable', 'true');
    div.setAttribute('data-id', t.id);

    div.addEventListener('dragstart', dragStart);
    div.addEventListener('dragend', dragEnd);

    // 2. O Evento de Clique no Card Inteiro
    div.onclick = function(e) {
        // Evita abrir o modal se o clique foi em botões específicos (ex: excluir, se houver no futuro)
        // Mas como só temos visualização, pode chamar direto:
        editarTarefa(t.id);
    };

    // Ícones (Anexo e Equipe)
    const iconAnexo = t.tem_anexo
        ? `<span class="me-2 text-muted" title="Possui anexo"><i class="fas fa-paperclip"></i></span>`
        : '';

    const iconEquipe = t.is_compartilhada
        ? `<span class="me-2 text-info" title="Compartilhada com equipe"><i class="fas fa-users"></i></span>`
        : '';

    const classData = t.atrasada ? 'text-danger fw-bold' : 'text-muted';
    const iconData = t.atrasada ? 'fas fa-exclamation-circle' : 'far fa-calendar-alt';

    // 3. Removemos o 'onclick' do lápis para não disparar duas vezes
    // (O lápis fica apenas visual agora, já que o card todo clica)
    div.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-2">
            <span class="badge-priority">${t.prioridade}</span>
            ${t.atrasada ? '<i class="fas fa-fire text-danger" title="Atrasada!"></i>' : ''}
        </div>

        <span class="task-title mb-2 d-block">${t.titulo}</span>

        <div class="task-footer d-flex justify-content-between align-items-center mt-2">
            <div class="${classData}" style="font-size: 0.85rem;">
                <i class="${iconData}"></i> ${t.prazo_fmt}
            </div>

            <div class="d-flex align-items-center">
                ${iconAnexo}
                ${iconEquipe}
                <i class="fas fa-pencil-alt text-muted hover-blue ms-1" title="Editar"></i>
            </div>
        </div>`;

    return div;
}

// ==========================================
// FUNÇÃO DE ABRIR O MODAL E CARREGAR TUDO
// ==========================================
window.editarTarefa = function(id) {
    const modalEl = document.getElementById('modalEditarTarefa');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    // Sincroniza Tipos
    const selectOrigem = document.getElementById('inputTipoAtendimento');
    const selectDestino = document.getElementById('editTipoAtendimento');
    if(selectOrigem && selectDestino) {
        selectDestino.innerHTML = selectOrigem.innerHTML;
    }

    // Limpezas
    document.getElementById('editIdTarefa').value = id;
    document.getElementById('editTitulo').value = 'Carregando...';
    document.getElementById('listaComentarios').innerHTML = '<div class="text-center text-muted mt-3"><i class="fas fa-spinner fa-spin"></i></div>';
    document.getElementById('listaVinculos').innerHTML = '';
    document.getElementById('areaVinculos').style.display = 'none';

    if(quillEdit) quillEdit.setText('Carregando...');

    // Busca dados
    fetch(`/api/kanban/tarefa/${id}`)
        .then(r => r.json())
        .then(t => {
            if(t.erro) { alert(t.erro); return; }

            // --- AQUI: REMOVI O STATUS ---
            document.getElementById('editTitulo').value = t.titulo;
            document.getElementById('editPrioridade').value = t.prioridade;
            // O Status não é mais preenchido pois o campo sumiu
            document.getElementById('editPrazo').value = t.data_prazo || '';

            if(t.tipo_atendimento_id) {
                 document.getElementById('editTipoAtendimento').value = t.tipo_atendimento_id;
            } else if (t.tipo) {
                 document.getElementById('editTipoAtendimento').value = t.tipo;
            }

            if(quillEdit) quillEdit.root.innerHTML = t.descricao || '';

            // Anexo
            const divAnexo = document.getElementById('areaAnexoExistente');
            const linkAnexo = document.getElementById('linkAnexoAtual');
            const nomeAnexo = document.getElementById('nomeAnexoAtual');

            if (t.caminho_anexo) {
                divAnexo.style.setProperty('display', 'block', 'important');
                if(nomeAnexo) nomeAnexo.innerText = t.nome_anexo || 'Arquivo Anexado';
                if(linkAnexo) {
                    let caminhoLimpo = t.caminho_anexo.replace(/\\/g, '/');
                    if (!caminhoLimpo.startsWith('/')) caminhoLimpo = '/' + caminhoLimpo;
                    linkAnexo.href = caminhoLimpo;
                }
            } else {
                divAnexo.style.setProperty('display', 'none', 'important');
            }

            // Vínculos (Equipe)
            const areaVin = document.getElementById('areaVinculos');
            const listaVin = document.getElementById('listaVinculos');
            const semVin = document.getElementById('semVinculos');

            if (t.vinculos && t.vinculos.length > 0) {
                areaVin.style.display = 'block';
                if(semVin) semVin.style.display = 'none';
                listaVin.innerHTML = '';
                t.vinculos.forEach(v => {
                    let badgeClass = 'bg-secondary';
                    let statusLabel = v.status;
                    if(v.status === 'concluido') { badgeClass = 'bg-success'; statusLabel = 'Concluído'; }
                    if(v.status === 'em_andamento') { badgeClass = 'bg-warning text-dark'; statusLabel = 'Andamento'; }
                    if(v.status === 'a_fazer') { badgeClass = 'bg-danger'; statusLabel = 'A Fazer'; }

                    listaVin.innerHTML += `
                        <li class="d-flex justify-content-between align-items-center mb-2 p-2 bg-white rounded border">
                            <span class="text-dark small fw-bold"><i class="fas fa-user-circle me-1 text-secondary"></i> ${v.responsavel}</span>
                            <span class="badge ${badgeClass}" style="font-size: 0.7rem;">${statusLabel}</span>
                        </li>`;
                });
            } else {
                areaVin.style.display = 'none';
                if(semVin) semVin.style.display = 'block';
            }

            renderizarComentarios(t.comentarios);
        })
        .catch(err => console.error("Erro ao carregar detalhes:", err));
}

// Função Auxiliar para renderizar a lista
function renderizarComentarios(lista) {
    const container = document.getElementById('listaComentarios');
    container.innerHTML = '';

    if (!lista || lista.length === 0) {
        container.innerHTML = '<p class="text-muted text-center small mt-3">Nenhum comentário ainda.</p>';
        return;
    }

    lista.forEach(c => {
        container.innerHTML += `
            <div class="mb-2 p-2 bg-white border rounded shadow-sm">
                <div class="d-flex justify-content-between mb-1">
                    <strong class="text-primary small">${c.autor}</strong>
                    <small class="text-muted" style="font-size: 0.7rem;">${c.data_fmt}</small>
                </div>
                <p class="mb-0 text-dark small" style="white-space: pre-wrap;">${c.comentario}</p>
            </div>`;
    });

    // Rola para o final (último comentário)
    container.scrollTop = container.scrollHeight;
}


// ==========================================
// FUNÇÃO DE ENVIAR COMENTÁRIO
// ==========================================
window.enviarComentario = function() {
    const idTarefa = document.getElementById('editIdTarefa').value;
    const input = document.getElementById('inputNovoComentario');
    const texto = input.value.trim();

    if (!texto) return; // Não envia vazio

    // Mostra feedback visual rápido
    input.disabled = true;

    fetch('/api/kanban/comentario', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ tarefa_id: idTarefa, texto: texto })
    })
    .then(r => r.json())
    .then(res => {
        input.disabled = false;
        if(res.sucesso) {
            input.value = ''; // Limpa campo

            // Recarrega apenas os dados para atualizar a lista
            // (Poderia otimizar e só adicionar na tela, mas assim garante sincronia)
            fetch(`/api/kanban/tarefa/${idTarefa}`)
                .then(r => r.json())
                .then(t => {
                   renderizarComentarios(t.comentarios);
                });
        } else {
            alert('Erro ao comentar: ' + res.erro);
        }
    })
    .catch(err => {
        console.error(err);
        input.disabled = false;
        alert('Erro de conexão.');
    });
}


// ==========================================
// 6. DRAG AND DROP
// ==========================================
function dragStart(e) {
    draggedItem = this;
    // Pequeno delay para efeito visual
    setTimeout(() => this.style.opacity = '0.4', 0);
}

function dragEnd(e) {
    this.style.opacity = '1';
    draggedItem = null;
}

window.allowDrop = function(e) { e.preventDefault(); }

window.drop = function(e) {
    e.preventDefault();
    if (!draggedItem) return;

    let target = e.target;
    // Sobe na hierarquia até achar a lista correta
    while (!target.classList.contains('kb-task-list')) {
        target = target.parentElement;
        if (!target) return;
    }

    target.appendChild(draggedItem);
    draggedItem.style.opacity = '1';

    const taskId = draggedItem.getAttribute('data-id');
    const novoStatus = target.getAttribute('data-status');

    // Envia atualização para o servidor
    fetch('/api/kanban/mover', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: taskId, status: novoStatus})
    }).then(r => {
        if(r.ok) console.log("Movido com sucesso");
        else alert("Erro ao salvar movimento.");
    });
}


// ==========================================
// 7. NOVA TAREFA - BUSCA E TAGS
// ==========================================
window.abrirModalNovaTarefa = function() {
    // 1. Resetar Form e Editor
    document.getElementById('formNovaTarefa').reset();
    if(quill) quill.setText('');

    // 2. Resetar Tags e Busca
    document.getElementById('areaTags').innerHTML = '';
    const listaResultados = document.getElementById('listaResultados');
    if(listaResultados) listaResultados.style.display = 'none';

    // LIMPEZA DA LISTA DE IDS
    selecionadosIds.clear();

    // ============================================================
    // CORREÇÃO AQUI: AUTO-SELECIONAR O DONO DO QUADRO ATUAL
    // ============================================================
    if (estadoAtual.colaboradorId && estadoAtual.colaborador) {
        // Cria um objeto temporário com os dados que temos
        const colabAtual = {
            id: estadoAtual.colaboradorId,
            nome: estadoAtual.colaborador
        };
        // Chama a função que cria a tag visual e adiciona no Set de IDs
        adicionarTag(colabAtual);
    }

    // 3. Abrir Modal
    const modalEl = document.getElementById('modalNovaTarefa');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    // 4. Carregar Tipos de Atendimento (Só se ainda não carregou)
    const sel = document.getElementById('inputTipoAtendimento');
    if(sel.options.length <= 1) {
        fetch('/api/kanban/tipos_atendimento')
            .then(r => r.json())
            .then(tipos => {
                sel.innerHTML = '<option value="">Selecione...</option>';
                tipos.forEach(t => sel.innerHTML += `<option value="${t.id}">${t.nome}</option>`);
            });
    }

    // 5. Carregar Cache de Colaboradores (para a busca funcionar)
    if (todosColaboradoresCache.length === 0) {
        fetch('/api/kanban/todos_colaboradores')
            .then(r => r.json())
            .then(data => {
                todosColaboradoresCache = data;
            })
            .catch(err => console.error("Erro ao carregar colaboradores:", err));
    }
}

// Filtro da Busca
function filtrarColaboradores(e) {
    const termo = e.target.value.toLowerCase();
    const listaEl = document.getElementById('listaResultados');

    if (termo.length < 2) {
        listaEl.style.display = 'none';
        return;
    }

    const filtrados = todosColaboradoresCache.filter(c =>
        c.nome.toLowerCase().includes(termo) && !selecionadosIds.has(c.id)
    );

    listaEl.innerHTML = '';

    if (filtrados.length > 0) {
        listaEl.style.display = 'block';
        filtrados.forEach(c => {
            const item = document.createElement('button');
            item.className = 'list-group-item list-group-item-action text-start';
            // Exibe Nome e Setor
            item.innerHTML = `
                <i class="fas fa-user-circle me-2 text-primary"></i>
                <strong>${c.nome}</strong>
                <small class="text-muted ms-2"> - ${c.setor || 'Geral'}</small>`;

            item.onclick = (evt) => {
                evt.preventDefault();
                adicionarTag(c);
                document.getElementById('buscaColaborador').value = '';
                listaEl.style.display = 'none';
                document.getElementById('buscaColaborador').focus();
            };
            listaEl.appendChild(item);
        });
    } else {
        listaEl.innerHTML = '<div class="list-group-item text-muted">Ninguém encontrado</div>';
        listaEl.style.display = 'block';
    }
}

function adicionarTag(c) {
    // Garante que o ID seja tratado como inteiro (caso venha string do HTML)
    const id = parseInt(c.id);

    // Se já tiver na lista, não faz nada
    if (selecionadosIds.has(id)) return;

    // Adiciona ao Set
    selecionadosIds.add(id);

    // Cria o elemento visual (Badge)
    const area = document.getElementById('areaTags');
    const tag = document.createElement('div');
    tag.className = 'badge bg-primary p-2 d-flex align-items-center me-1 mb-1';

    // Adiciona o nome e o ícone de fechar
    tag.innerHTML = `
        <span class="me-2">${c.nome}</span>
        <i class="fas fa-times" style="cursor:pointer;" onclick="removerTag(${id}, this)"></i>`;

    area.appendChild(tag);
}

window.removerTag = function(id, el) {
    const idInt = parseInt(id);
    selecionadosIds.delete(idInt);
    el.parentElement.remove();
}


// ==========================================
// 8. SALVAR TAREFA (FORMDATA + ANEXO)
// ==========================================
window.salvarNovaTarefa = function() {
    const titulo = document.getElementById('inputTitulo').value;
    const prazo = document.getElementById('inputPrazo').value;
    const prioridade = document.getElementById('inputPrioridade').value;
    const tipo = document.getElementById('inputTipoAtendimento').value;

    // PEGAR O CONTEÚDO HTML DO QUILL
    const descricaoHtml = quill ? quill.root.innerHTML : '';

    if (!titulo || !prazo || !tipo) {
        alert("Preencha Título, Prazo e Tipo.");
        return;
    }

    const arrayIds = Array.from(selecionadosIds);
    if(arrayIds.length === 0) {
        alert("Selecione pelo menos um responsável na busca.");
        return;
    }

    // Usa FormData para suportar Arquivos
    const form = new FormData();
    form.append('titulo', titulo);
    form.append('descricao', descricaoHtml);
    form.append('prioridade', prioridade);
    form.append('prazo', prazo);
    form.append('tipo_atendimento_id', tipo);
    // Envia array de IDs como string JSON
    form.append('responsaveis_ids', JSON.stringify(arrayIds));

    // Anexo (se houver)
    const fileInput = document.getElementById('inputAnexo');
    if (fileInput && fileInput.files[0]) {
        form.append('arquivo_anexo', fileInput.files[0]);
    }

    // Botão loading
    const btn = document.querySelector('#modalNovaTarefa .modal-footer .btn-primary');
    const txtOriginal = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    btn.disabled = true;

    fetch('/api/kanban/nova_tarefa', {
        method: 'POST',
        body: form
    })
    .then(r => r.json())
    .then(data => {
        if(data.sucesso) {
            alert("Tarefa criada com sucesso!");

            // Fecha Modal
            const modalEl = document.getElementById('modalNovaTarefa');
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();

            // Atualiza a tela
            if(estadoAtual.colaboradorId) {
                // Se estiver vendo um quadro, recarrega ele
                carregarKanban(estadoAtual.colaboradorId, estadoAtual.colaborador);
            } else {
                // Se estiver na home, recarrega os setores (contagem muda)
                carregarSetores();
            }
        } else {
            alert("Erro: " + data.erro);
        }
    })
    .catch(err => {
        console.error(err);
        alert("Erro de comunicação com o servidor.");
    })
    .finally(() => {
        btn.innerHTML = txtOriginal;
        btn.disabled = false;
    });
}
// ==========================================
// 9. SALVAR EDIÇÃO DA TAREFA
// ==========================================
window.salvarEdicaoTarefa = function() {
    const id = document.getElementById('editIdTarefa').value;
    const titulo = document.getElementById('editTitulo').value;
    const prioridade = document.getElementById('editPrioridade').value;
    const prazo = document.getElementById('editPrazo').value;
    const tipo = document.getElementById('editTipoAtendimento').value;
    const descricao = quillEdit ? quillEdit.root.innerHTML : '';

    if (!titulo) {
        if(typeof Toast !== 'undefined') Toast.fire({ icon: 'warning', title: 'O título é obrigatório!' });
        else alert('Título obrigatório');
        return;
    }

    const payload = {
        id: id, titulo: titulo, prioridade: prioridade,
        prazo: prazo, tipo_atendimento_id: tipo, descricao: descricao
    };

    const btnSalvar = document.querySelector('#modalEditarTarefa .btn-success');
    const textoOriginal = btnSalvar ? btnSalvar.innerHTML : 'Salvar';
    if(btnSalvar) {
        btnSalvar.disabled = true;
        btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    }

    fetch('/api/kanban/editar_tarefa', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if(data.sucesso) {
            // Fecha Modal
            const modalEl = document.getElementById('modalEditarTarefa');
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();

            // Alerta
            if(typeof Toast !== 'undefined') Toast.fire({ icon: 'success', title: 'Tarefa atualizada!' });

            // --- CORREÇÃO DO REFRESH ---
            // Verifica se recarrega o Individual ou o Master
            if (estadoAtual.colaboradorId) {
                carregarKanban(estadoAtual.colaboradorId, estadoAtual.colaborador);
            } else {
                carregarVisaoMaster(); // Recarrega a visão geral se estiver nela
            }

        } else {
            Swal.fire('Erro!', data.erro, 'error');
        }
    })
    .catch(err => {
        console.error(err);
        Swal.fire('Erro!', 'Falha na conexão.', 'error');
    })
    .finally(() => {
        if(btnSalvar) {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = textoOriginal;
        }
    });
}

// ==========================================
// 10. EXCLUIR TAREFA
// ==========================================
window.confirmarExclusao = function() {
    const id = document.getElementById('editIdTarefa').value;

    Swal.fire({
        title: 'Tem certeza?',
        text: "A tarefa será apagada permanentemente.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sim, excluir!',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {

            fetch('/api/kanban/excluir', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id: id })
            })
            .then(r => r.json())
            .then(data => {
                if(data.sucesso) {
                    const modalEl = document.getElementById('modalEditarTarefa');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    modal.hide();

                    Swal.fire('Excluído!', 'Tarefa removida.', 'success');

                    // --- CORREÇÃO DO REFRESH ---
                    if (estadoAtual.colaboradorId) {
                        carregarKanban(estadoAtual.colaboradorId, estadoAtual.colaborador);
                    } else {
                        carregarVisaoMaster();
                    }
                } else {
                    Swal.fire('Erro', data.erro, 'error');
                }
            })
            .catch(err => Swal.fire('Erro', 'Erro de conexão.', 'error'));
        }
    })
}

// ==========================================
// 11. VISÃO MASTER (GERAL)
// ==========================================
window.carregarVisaoMaster = function() {
    // 1. Limpa ID de colaborador para indicar modo Global
    estadoAtual.colaboradorId = null;
    estadoAtual.colaborador = null;

    navegarPara('view-kanban');

    document.getElementById('titulo-kanban-colaborador').innerHTML = '<i class="fas fa-globe-americas me-2 text-primary"></i>Visão Geral da Empresa';
    document.getElementById('kb-breadcrumbs').innerText = 'Monitoramento Global';

    const colFazer = document.getElementById('col-fazer');
    const colAndamento = document.getElementById('col-andamento');
    const colConcluido = document.getElementById('col-concluido');

    colFazer.innerHTML = '<div class="spinner-border spinner-border-sm text-muted"></div>';
    colAndamento.innerHTML = '';
    colConcluido.innerHTML = '';

    fetch('/api/kanban/master')
        .then(r => r.json())
        .then(tarefas => {
            colFazer.innerHTML = '';

            if (!tarefas || tarefas.length === 0) {
                colFazer.innerHTML = '<p class="text-muted ms-2">Nenhuma tarefa encontrada.</p>';
                return;
            }

            tarefas.forEach(t => {
                const cardElemento = criarCardMaster(t);
                // Validação de status seguro
                const st = t.status ? t.status.trim() : 'a_fazer';

                if (st === 'a_fazer') colFazer.appendChild(cardElemento);
                else if (st === 'em_andamento') colAndamento.appendChild(cardElemento);
                else if (st === 'concluido') colConcluido.appendChild(cardElemento);
            });
        })
        .catch(err => console.error("Erro Master:", err));
}

function criarCardMaster(t) {
    const div = document.createElement('div');
    div.className = `kb-task-card priority-${t.prioridade}`;
    div.style.cursor = 'pointer';

    div.onclick = function() { editarTarefa(t.id); };

    // --- CORREÇÃO: Usando a função helper da Parte 1 ---
    let htmlAvatares = '<div class="kb-avatar-group">';
    if (t.equipe && t.equipe.length > 0) {
        t.equipe.forEach(membro => {
            // Usa a função global para manter o design consistente
            // Passamos 'small' para ficar pequeno dentro do card
            htmlAvatares += gerarAvatarHTML(membro.nome, membro.foto, 'small');
        });
    }
    htmlAvatares += '</div>';

    const classData = t.atrasada ? 'text-danger fw-bold' : 'text-muted';
    const iconData = t.atrasada ? 'fas fa-exclamation-circle' : 'far fa-calendar-alt';

    div.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-2">
            <span class="badge-priority">${t.prioridade}</span>
             ${t.atrasada ? '<i class="fas fa-fire text-danger" title="Atrasada!"></i>' : ''}
        </div>

        <span class="task-title mb-3 d-block">${t.titulo}</span>

        <div class="d-flex justify-content-between align-items-end mt-2">
            <div class="${classData}" style="font-size: 0.8rem;">
                <i class="${iconData}"></i> ${t.prazo_fmt}
            </div>
            ${htmlAvatares}
        </div>`;

    return div;
}

// ==========================================
// 13. DEEP LINK (ABRIR TAREFA PELA URL)
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const tarefaId = urlParams.get('t_id');

    if (tarefaId) {
        setTimeout(() => {
            console.log("Abrindo via Link:", tarefaId);
            editarTarefa(tarefaId);
            // Limpa URL para não reabrir ao dar F5
            window.history.replaceState({}, document.title, window.location.pathname);
        }, 600);
    }
});

// ==========================================
// 14. HISTÓRICO DE TAREFAS
// ==========================================
window.abrirModalHistorico = function() {
    const colabId = estadoAtual.colaboradorId;

    if (!colabId) {
        Swal.fire('Aviso', 'Selecione um colaborador para ver o histórico individual.', 'info');
        return;
    }

    const modalEl = document.getElementById('modalHistoricoTarefas');
    const modal = new bootstrap.Modal(modalEl);
    const lista = document.getElementById('listaHistorico');

    lista.innerHTML = '<div class="text-center p-4"><div class="spinner-border text-success"></div></div>';
    modal.show();

    fetch(`/api/kanban/historico_concluidas/${colabId}`)
        .then(r => r.json())
        .then(dados => {
            lista.innerHTML = '';

            if (dados.length === 0) {
                lista.innerHTML = '<div class="text-center p-4 text-muted">Nenhuma tarefa concluída no histórico.</div>';
                return;
            }

            dados.forEach(t => {
                let badgeCor = 'bg-secondary';
                if(t.prioridade === 'alta') badgeCor = 'bg-danger';
                if(t.prioridade === 'media') badgeCor = 'bg-warning text-dark';
                if(t.prioridade === 'baixa') badgeCor = 'bg-success';

                lista.innerHTML += `
                    <button class="list-group-item list-group-item-action" onclick="editarTarefa(${t.id}); bootstrap.Modal.getInstance(document.getElementById('modalHistoricoTarefas')).hide();">
                        <div class="d-flex w-100 justify-content-between align-items-center">
                            <h6 class="mb-1 text-truncate" style="max-width: 70%;">${t.titulo}</h6>
                            <small class="text-muted">${t.data_fmt}</small>
                        </div>
                        <div class="mt-1">
                            <span class="badge ${badgeCor} rounded-pill" style="font-size: 0.65rem;">${t.prioridade}</span>
                            <small class="text-muted ms-2" style="font-size: 0.75rem;"><i class="fas fa-check-double text-success"></i> Concluído</small>
                        </div>
                    </button>
                `;
            });
        })
        .catch(err => {
            console.error(err);
            lista.innerHTML = '<div class="text-danger p-3 text-center">Erro ao carregar histórico.</div>';
        });
}

// ==========================================
// 15. SISTEMA DE NOTIFICAÇÃO (NOVIDADES)
// ==========================================
function verificarNovidades() {
    // IMPORTANTE: Mude este nome (v1.0, v1.1) sempre que quiser mostrar uma nova notícia
    // Se você não mudar isso, o popup não aparece para quem já viu.
    const versaoAtual = 'novidades_kanban_v1.0';

    if (!localStorage.getItem(versaoAtual)) {

        Swal.fire({
            title: '<strong>🚀 O Controle de Atividades Evoluiu!</strong>',
            icon: 'info',
            // --- EDITE O TEXTO AQUI EMBAIXO ---
            html: `
                <div class="text-start fs-6">
                    <p class="mb-3">O seu sistema agora conta com Gerenciador de tarefas <strong>simples e poderoso</strong>. Confira o que mudou:</p>

                    <ul class="list-unstyled">
                        <li class="mb-3">
                            <i class="fas fa-camera-retro text-primary me-2 fa-lg"></i>
                            <strong>Fotos de Perfil:</strong>
                            <div class="text-muted small ms-4">Agora o sistema exibe a sua foto real! Ficou muito mais fácil identificar quem é o responsável por cada tarefa nos cards.</div>
                        </li>

                        <li class="mb-3">
                            <i class="fas fa-globe-americas text-info me-2 fa-lg"></i>
                            <strong>Visão Master:</strong>
                            <div class="text-muted small ms-4">Uma nova tela de monitoramento global para acompanhar o fluxo de toda a empresa em um só lugar.</div>
                        </li>

                        <li class="mb-3">
                            <i class="fas fa-history text-success me-2 fa-lg"></i>
                            <strong>Histórico de Tarefas:</strong>
                            <div class="text-muted small ms-4">Precisa consultar algo antigo? Acesse suas tarefas concluídas e reabra se necessário.</div>
                        </li>

                        <li class="mb-2">
                            <i class="fas fa-link text-warning me-2 fa-lg"></i>
                            <strong>Acesso Rápido (Deep Links):</strong>
                            <div class="text-muted small ms-4">Ao clicar no link de uma notificação, a tarefa abre automaticamente na sua tela.</div>
                        </li>
                    </ul>
                    <p class="text-center fw-bold text-primary mt-3">Bom trabalho!</p>
                </div>
            `,
            // ----------------------------------
            showCloseButton: true,
            focusConfirm: false,
            confirmButtonText: '<i class="fas fa-thumbs-up"></i> Entendi!',
            confirmButtonColor: '#0d6efd'
        }).then((result) => {
            // Marca no navegador que o usuário já viu
            localStorage.setItem(versaoAtual, 'true');
        });
    }
}
// ==========================================
// 15. AUTO-DIRECIONAMENTO (NOTIFICAÇÃO -> MEU QUADRO)
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    const params = new URLSearchParams(window.location.search);

    // Verifica se veio da notificação com o sinal 'meus=1'
    if (params.get('meus') === '1') {
        console.log("Modo Notificação: Carregando meu quadro...");

        const myId = document.getElementById('usuario_logado_id')?.value;
        const myName = document.getElementById('usuario_logado_nome')?.value || 'Meu Quadro';

        if (myId) {
            // Chama a função que carrega o quadro
            carregarKanban(myId, myName);

            // Se tiver ID de tarefa, abre o modal com correção de bug
            const tId = params.get('t_id');
            if (tId) {
                setTimeout(() => {
                    if (typeof editarTarefa === 'function') {
                        // 1. Abre o modal
                        editarTarefa(tId);

                        // --- CORREÇÃO DO BUG DA TELA TRAVADA ---
                        // Adiciona um evento para limpar o fundo cinza quando ESSE modal fechar
                        const modalEl = document.getElementById('modalEditarTarefa');
                        if (modalEl) {
                            modalEl.addEventListener('hidden.bs.modal', function () {
                                // Remove forçadamente qualquer backdrop que tenha sobrado
                                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                                // Remove a classe que trava o scroll do corpo
                                document.body.classList.remove('modal-open');
                                document.body.style.overflow = '';
                                document.body.style.paddingRight = '';
                            }, { once: true }); // { once: true } garante que roda só nesta vez automática
                        }
                    }
                    // Limpa a URL
                    window.history.replaceState({}, '', '/kanban');
                }, 800);
            }
        } else {
            console.warn("ATENÇÃO: ID do usuário logado não encontrado.");
        }
    }
});
// ==========================================
// 16. BOTÃO "MINHAS TAREFAS" (MANUAL)
// ==========================================
function irParaMeuQuadro() {
    const myId = document.getElementById('usuario_logado_id')?.value;
    const myName = document.getElementById('usuario_logado_nome')?.value || 'Meu Quadro';

    if (myId) {
        // Usa a sua função nativa para carregar e trocar a tela
        carregarKanban(myId, myName);
    } else {
        Swal.fire('Erro', 'Não foi possível identificar seu usuário.', 'error');
    }
}