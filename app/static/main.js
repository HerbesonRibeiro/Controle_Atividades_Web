/**
 * Script principal da aplicação.
 * ... (comentários de cabeçalho) ...
 */

// [A] Bloco de Inicialização Principal
document.addEventListener('DOMContentLoaded', function() {

    /* [1] Gerenciamento de Notificações (Toasts) */
    // ... (seu código de toasts, que está correto) ...
    const toasts = document.querySelectorAll('#toast-container .toast');
    toasts.forEach((toast) => {
        setTimeout(() => {
            toast.classList.add('fade-out');
            toast.addEventListener('animationend', () => toast.remove());
        }, 5000);
    });

    /* [2] Controle da Sidebar (Toggle do Menu Hamburger) */
    // ... (seu código da sidebar, que está correto) ...
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    const body = document.body;
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            body.classList.toggle('sidebar-collapsed');
        });
    }

    /* [3] Controle do Menu Acordeão (Accordion da Sidebar) */
    // ... (seu código de submenu, que está correto) ...
    const menuTitles = document.querySelectorAll('.sidebar-title');
    menuTitles.forEach(title => {
        title.addEventListener('click', function(event) {
            event.preventDefault();
            const submenu = this.nextElementSibling;
            if (!submenu || !submenu.classList.contains('sidebar-submenu')) {
                return;
            }
            document.querySelectorAll('.sidebar-submenu').forEach(otherSubmenu => {
                if (otherSubmenu !== submenu) {
                    otherSubmenu.classList.add('hidden');
                }
            });
            submenu.classList.toggle('hidden');
        });
    });

/* [4] Lógica Específica da Página: /historico */
    // Este bloco só é executado na página de histórico.
    // Isso é uma "guarda de página" (page guard) que previne erros
    // de 'null' em outras páginas que não contêm estes elementos.
    const bulkForm = document.getElementById('bulk-action-form');
    if (bulkForm) {

        // --- [4.1] Seleção de Elementos ---
        // Primeiro, encontramos todos os botões e elementos que vamos usar
        const selectAllCheckbox = document.getElementById('select-all-checkbox');
        const rowCheckboxes = document.querySelectorAll('.row-checkbox');
        const counterElement = document.getElementById('selection-counter');
        const editBtn = document.getElementById('edit-selected-btn');
        const deleteBtn = document.getElementById('delete-selected-btn');
        const detailsModal = document.getElementById('details-modal');
        const closeDetailsModalBtn = document.getElementById('close-details-modal-btn');
        const modalBody = document.getElementById('modal-body');
        const tableBody = document.querySelector('.table-uppercase tbody');

        /**
         * [4.2] Função Auxiliar (Helper)
         * Atualiza a UI de ações em massa (contador e botões)
         * com base no número de checkboxes selecionados.
         */
        function updateCounterAndButtons() {
            const selectedCount = document.querySelectorAll('.row-checkbox:checked').length;

            if (counterElement) {
                counterElement.textContent = selectedCount === 1 ? '1 item selecionado' : `${selectedCount} itens selecionados`;
            }
            // Habilita/desabilita botões: Editar só é permitido com 1 item.
            if (editBtn) editBtn.disabled = selectedCount !== 1;
            if (deleteBtn) deleteBtn.disabled = selectedCount === 0;
        }

        // --- [4.3] Listeners de Ação em Massa ---

        // Event listener para o checkbox "Selecionar Todos"
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', function() {
                rowCheckboxes.forEach(checkbox => checkbox.checked = this.checked);
                updateCounterAndButtons();
            });
        }

        // Event listener para os checkboxes individuais das linhas
        rowCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                // Se todos estiverem marcados, marca o "Selecionar Todos"
                const allChecked = Array.from(rowCheckboxes).every(cb => cb.checked);
                if (selectAllCheckbox) selectAllCheckbox.checked = allChecked;
                updateCounterAndButtons();
            });
        });

        // Event listener para o botão "Editar Selecionado"
        if (editBtn) {
            editBtn.addEventListener('click', function() {
                const selectedCheckbox = document.querySelector('.row-checkbox:checked');
                if (selectedCheckbox) {
                    // Redireciona o navegador para a página de edição daquele ID
                    window.location.href = `/editar_atividade/${selectedCheckbox.value}`;
                }
            });
        }

        // Adiciona uma confirmação (popup do navegador) antes de enviar o form de exclusão
        bulkForm.addEventListener('submit', function(event) {
            const selectedCount = document.querySelectorAll('.row-checkbox:checked').length;
            if (selectedCount > 0 && !confirm(`Tem certeza que deseja excluir os ${selectedCount} itens selecionados?`)) {
                event.preventDefault(); // Cancela o envio do formulário
            }
        });

        // --- [4.4] Listeners do Modal de Detalhes ---

        // Gerenciamento do Modal de Detalhes (Leitura)
        if (tableBody) {
             tableBody.addEventListener('click', function(event) {
                // Delegação de evento: escuta cliques na tabela inteira
                const target = event.target.closest('.btn-details');
                if (target) {
                    // Se o clique foi no botão de detalhes, popula e abre o modal
                    const data = target.dataset; // Acessa os atributos data-*

                    if (modalBody) {
                        modalBody.innerHTML = `
                            <p><strong>ID:</strong> ${data.id}</p>
                            <p><strong>Data:</strong> ${data.data}</p>
                            <p><strong>Tipo:</strong> ${data.tipo}</p>
                            <p><strong>Nº Atendimento:</strong> ${data.numero || 'N/A'}</p>
                            <p><strong>Colaborador:</strong> ${data.colaborador}</p>
                            <p><strong>Status:</strong> ${data.status}</p>
                            <hr>
                            <p><strong>Descrição:</strong></p>
                            <p style="white-space: pre-wrap; background-color: #f8f9fa; padding: 10px; border-radius: 5px;">${data.descricao}</p>
                        `;
                    }
                    if (detailsModal) detailsModal.classList.remove('hidden');
                }
            });
        }

        // Eventos para fechar o modal de detalhes
        if (closeDetailsModalBtn && detailsModal) {
            // Usa as funções genéricas que criamos
            closeDetailsModalBtn.addEventListener('click', () => fecharModal('details-modal'));
        }

        // (Não precisamos mais do listener de clique "fora",
        // pois o nosso listener GENÉRICO no Bloco [5] já cuida disso!)

        // --- [4.5] Inicialização ---
        // Inicializa o contador ao carregar a página
        updateCounterAndButtons();
    }


    /* ==========================================================================
       [5] LISTENERS GLOBAIS PARA TODOS OS MODAIS (GENÉRICOS)

       Este código SÓ funciona aqui dentro do DOMContentLoaded,
       pois ele precisa que os modais no HTML já existam.
       ========================================================================== */

    // Adiciona a lógica de "fechar ao clicar fora" para TODOS os modais
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', function(event) {
            // Verifica se o clique foi no próprio overlay (o fundo)
            if (event.target === this) {
                fecharModal(this.id);
            }
        });
    });

    // Adiciona a lógica de "fechar com a tecla Esc" para TODOS os modais
    document.addEventListener('keydown', function(event) {
        if (event.key === "Escape") {
            // Encontra o modal que está aberto atualmente
            const openModal = document.querySelector('.modal-overlay:not(.hidden)');
            if (openModal) {
                fecharModal(openModal.id);
            }
        }
    });

}); // <-- FIM DO 'DOMContentLoaded'


/* ==========================================================================
   [B] Funções Globais (Acessíveis pelo 'onclick' do HTML)

   Estas funções ficam FORA do DOMContentLoaded para
   estarem no escopo global.
   ========================================================================== */

/**
 * Ponto de entrada do Modal para o fluxo do ADMINISTRADOR.
 */
function abrirModalAtividadesHoje() {
    const modal = document.getElementById('modal-hoje-setor');
    if (modal) {
        // Força o display a aparecer, sobrescrevendo o style="none" do HTML
        modal.style.display = 'flex';

        // Remove a classe hidden também, só por garantia
        modal.classList.remove('hidden');

        carregarDadosModalSetores();
    }
}
function fecharModalSetoresHoje() {
    const modal = document.getElementById('modal-hoje-setor');
    if (modal) {
        // Força o modal a sumir
        modal.style.display = 'none';
        // Adiciona a classe hidden para manter padrão
        modal.classList.add('hidden');
    }
}

/**
 * Ponto de entrada do Modal para o fluxo do GESTOR.
 */
/**
 * Ponto de entrada do Modal para o fluxo do GESTOR.
 */
function abrirModalColaboradoresGestor(setorId, setorNome) {
    const modal = document.getElementById('modal-hoje-setor');
    if (modal) {
        // 1. Força o modal a ficar visível (sobrescreve o display: none)
        modal.style.display = 'flex';

        // 2. Remove a classe hidden (para garantir)
        modal.classList.remove('hidden');

        // 3. Carrega os dados usando o ID do setor que veio do Python
        carregarDadosModalColaboradores(setorId, setorNome, false);
    }
}
/**
 * Carrega o Estágio 1 do modal (Lista de Setores).
 */
function carregarDadosModalSetores() {
    const modalBody = document.getElementById('modal-body-setores');
    const modalTitle = document.getElementById('modal-title');
    const backBtn = document.getElementById('modal-back-btn');

    if(modalTitle) modalTitle.innerText = 'Atividades de Hoje por Setor';
    if(backBtn) backBtn.style.display = 'none';
    if(!modalBody) return;

    modalBody.innerHTML = '<tr><td colspan="2">Carregando...</td></tr>';

    // CORREÇÃO 1: A URL deve ser EXATAMENTE igual à rota do Python
    fetch('/api/atividades-hoje-setor')
        .then(response => response.json())
        .then(data => {
            modalBody.innerHTML = '';

            // Verifica se veio erro
            if (data.error) {
                console.error(data.error);
                modalBody.innerHTML = '<tr><td colspan="2">Erro ao carregar dados.</td></tr>';
                return;
            }

            if (data.length === 0) {
                modalBody.innerHTML = '<tr><td colspan="2">Nenhuma atividade registrada hoje.</td></tr>';
                return;
            }

            data.forEach(item => {
                // CORREÇÃO 2: Usar 'item.id' (que vem do SELECT s.id)
                // em vez de 'item.setor_id'.
                const row = `
                    <tr onclick="carregarDadosModalColaboradores(${item.id}, '${item.nome_setor}')" style="cursor: pointer;" title="Ver detalhes de ${item.nome_setor}">
                        <td>${item.nome_setor}</td>
                        <td>${item.total}</td>
                    </tr>
                `;
                modalBody.innerHTML += row;
            });
        })
        .catch(error => {
            console.error('Erro ao buscar dados dos setores:', error);
            modalBody.innerHTML = '<tr><td colspan="2">Ocorreu um erro ao carregar os dados.</td></tr>';
        });
}

/**
 * Carrega o Estágio 2 do modal (Lista de Colaboradores).
 */
function carregarDadosModalColaboradores(setorId, setorNome, showBackButton = true) {
    // ... (seu código, que está correto) ...
    const modalBody = document.getElementById('modal-body-setores');
    const modalTitle = document.getElementById('modal-title');
    const backBtn = document.getElementById('modal-back-btn');

    if(modalTitle) modalTitle.innerText = `Atividades Hoje - ${setorNome}`;
    if(backBtn) backBtn.style.display = showBackButton ? 'block' : 'none';
    if(!modalBody) return;

    modalBody.innerHTML = '<tr><td colspan="2">Carregando...</td></tr>';

    fetch(`/api/atividades-hoje-por-colaborador/${setorId}`)
        .then(response => response.json())
        .then(data => {
            modalBody.innerHTML = '';
            if (data.length === 0) {
                modalBody.innerHTML = '<tr><td colspan="2">Nenhum colaborador ativo neste setor.</td></tr>';
                return;
            }
            data.forEach(item => {
                const row = `
                    <tr>
                        <td>${item.nome}</td>
                        <td>${item.total}</td>
                    </tr>
                `;
                modalBody.innerHTML += row;
            });
        })
        .catch(error => {
            console.error('Erro ao buscar dados dos colaboradores:', error);
            modalBody.innerHTML = '<tr><td colspan="2">Ocorreu um erro ao carregar os dados.</td></tr>';
        });
}

/**
 * Fecha o modal de Atividades Hoje (específico).
 */
function fecharModalSetoresHoje() {
    const modal = document.getElementById('modal-hoje-setor');
    if (modal) {
        modal.classList.add('hidden'); // Usa a classe 'hidden'
    }
}


/* ==========================================================================
   [C] Funções Globais e Reutilizáveis para Modals (Genéricos)
   ========================================================================== */

/**
 * Abre qualquer modal no site pelo seu ID.
 */
function abrirModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * Fecha qualquer modal no site pelo seu ID.
 */
function fecharModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

/* ==========================================================================
   [PDS - Pesquisa de Satisfação]
   ========================================================================== */

function copiarLinkPDS() {
    const inputLink = document.getElementById("pds-link-url");
    const btn = document.getElementById("btn-copiar-pds");
    const corSucesso = getComputedStyle(document.documentElement)
        .getPropertyValue('--success-color') || '#28a745';

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(inputLink.value)
            .then(() => {
                mostrarToast("Link copiado com sucesso!", "success");
                btn.classList.add('copiado');
                btn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    btn.classList.remove('copiado');
                    btn.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            })
            .catch(err => {
                console.error("Erro ao copiar:", err);
                mostrarToast("Erro ao copiar o link.", "error");
            });
    } else {
        inputLink.select();
        document.execCommand("copy");
        mostrarToast("Link copiado (modo compatibilidade)", "success");
    }
}

function mostrarToast(mensagem, tipo = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${tipo}`;
    toast.textContent = mensagem;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add("show"), 100);
    setTimeout(() => toast.classList.remove("show"), 2500);
    setTimeout(() => toast.remove(), 3000);
}

/* ==========================================================================
   [MODAL DE PESQUISA DE SATISFAÇÃO]
   Atualizado para exibir Sim/Não/Parcialmente e Nota de 1 a 5
   ========================================================================== */

function abrirModalPDS(q1, q2, event) {
    if (event) event.stopPropagation();

    const modal = document.getElementById('modal-pds');
    const body = document.getElementById('modal-pds-body');

    if (!modal || !body) {
        console.error("Modal PDS não encontrado no HTML");
        return;
    }

    // 1. Definição da Cor e Ícone para a Q1 (Texto)
    let badgeClass = 'status-secondary'; // Padrão cinza
    let icon = 'fa-question-circle';
    let textoQ1 = q1 || 'Não informado';

    if (q1 === 'Sim') {
        badgeClass = 'status-success'; // Verde
        icon = 'fa-check-circle';
    } else if (q1 === 'Não') {
        badgeClass = 'status-danger'; // Vermelho
        icon = 'fa-times-circle';
    } else if (q1 === 'Parcialmente') {
        badgeClass = 'status-warning'; // Amarelo
        icon = 'fa-adjust';
    }

    // 2. Geração das Estrelas para a Q2 (Nota 1 a 5)
    let estrelasHTML = '';
    const nota = parseInt(q2) || 0;

    for (let i = 1; i <= 5; i++) {
        if (i <= nota) {
            estrelasHTML += '<i class="fas fa-star" style="color: #ffc107; margin-right: 2px;"></i>'; // Estrela cheia (amarela)
        } else {
            estrelasHTML += '<i class="far fa-star" style="color: #ccc; margin-right: 2px;"></i>'; // Estrela vazia (cinza)
        }
    }

    // 3. Monta o HTML do Modal
    body.innerHTML = `
        <div style="text-align: left; padding: 10px;">

            <div style="margin-bottom: 25px;">
                <p style="margin: 0 0 8px; font-weight: 600; color: #555;">1. Sua demanda foi atendida?</p>
                <span class="status-badge ${badgeClass}" style="font-size: 1rem; padding: 6px 15px;">
                    <i class="fas ${icon}"></i> ${textoQ1}
                </span>
            </div>

            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">

            <div>
                <p style="margin: 0 0 8px; font-weight: 600; color: #555;">2. Nota para o atendimento:</p>
                <div style="font-size: 1.5rem;">
                    ${estrelasHTML}
                    <span style="font-size: 1rem; color: #777; margin-left: 10px; font-weight: 600;">
                        (${nota}/5)
                    </span>
                </div>
            </div>

        </div>
    `;

    // 4. Abre o modal
    modal.classList.remove('hidden');
    modal.style.display = 'flex'; // Garante que o flex do CSS funcione
    document.body.style.overflow = 'hidden'; // Trava a rolagem do fundo
}

function fecharModalPDS() {
    const modal = document.getElementById('modal-pds');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
}
/* ==========================================================================
   [GESTÃO DE CLIENTES E GRUPOS - MODAL DE EDIÇÃO]
   ========================================================================== */

function abrirModalEditarGrupo(id, nome) {
    const modal = document.getElementById('modal-editar');
    if (!modal) return;

    modal.classList.remove('hidden');
    document.getElementById('modal-titulo').innerText = 'Editar Grupo';
    document.getElementById('edit-acao').value = 'editar_grupo';
    document.getElementById('edit-id').value = id;
    document.getElementById('edit-nome').value = nome;

    // Oculta o campo "Grupo Vinculado", pois não é usado em grupos
    document.getElementById('edit-grupo-wrapper').style.display = 'none';
}

function abrirModalEditarTipo(id, nome, grupoId) {
    const modal = document.getElementById('modal-editar');
    if (!modal) return;

    modal.classList.remove('hidden');
    document.getElementById('modal-titulo').innerText = 'Editar Tipo de Cliente';
    document.getElementById('edit-acao').value = 'editar_tipo';
    document.getElementById('edit-id').value = id;
    document.getElementById('edit-nome').value = nome;

    // Exibe o campo de grupo e seleciona o grupo atual
    const grupoWrapper = document.getElementById('edit-grupo-wrapper');
    grupoWrapper.style.display = 'block';
    document.getElementById('edit-grupo-id').value = grupoId;
}

function fecharModalEditar() {
    const modal = document.getElementById('modal-editar');
    if (modal) modal.classList.add('hidden');
}
/* ==========================================================================
   [GESTÃO DE ORIGENS - MODAL DE EDIÇÃO]
   ========================================================================== */

function abrirModalEditar(id, nome) {
    const modal = document.getElementById('modal-editar');
    const inputId = document.getElementById('edit-origem-id');
    const inputNome = document.getElementById('edit-nome-origem');

    if (!modal || !inputId || !inputNome) return;

    inputId.value = id;
    inputNome.value = nome;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function fecharModalEditar() {
    const modal = document.getElementById('modal-editar');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
}