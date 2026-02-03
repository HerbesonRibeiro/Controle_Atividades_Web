/* ARQUIVO: static/notificacoes.js */

document.addEventListener('DOMContentLoaded', function() {

    // --- 1. LÓGICA DA BOLINHA (CONTAGEM) ---
    function atualizarContador() {
        if (document.hidden) return;

        fetch('/api/notificacoes/contar')
            .then(res => res.json())
            .then(data => {
                const badge = document.getElementById('badge-notificacao');
                const btn = document.getElementById('btn-notificacoes');

                if (!badge || !btn) return;

                if (data.total > 0) {
                    badge.innerText = data.total > 99 ? '99+' : data.total;
                    badge.style.display = 'flex';

                    if (data.criticas > 0) {
                        badge.classList.add('badge-urgent');
                        badge.classList.remove('badge-normal');
                        btn.classList.add('bell-urgent');
                    } else {
                        badge.classList.add('badge-normal');
                        badge.classList.remove('badge-urgent');
                        btn.classList.remove('bell-urgent');
                    }
                } else {
                    badge.style.display = 'none';
                    btn.classList.remove('bell-urgent');
                }
            })
            .catch(err => console.warn("Erro conexao notificacao")); // Silencioso
    }

    // --- 2. LÓGICA DA LISTA (EVENTO DO BOOTSTRAP) ---
    const btnSino = document.getElementById('btn-notificacoes');
    const listaSino = document.getElementById('lista-notificacoes');

    if (btnSino && listaSino) {
        // AQUI ESTÁ O SEGREDO: Ouvimos o evento do Bootstrap, não o click manual.
        // Isso impede que o menu trave ou abra duas vezes.
        btnSino.addEventListener('show.bs.dropdown', function () {

            // 1. Reseta para "Buscando..." sempre que abrir
            listaSino.innerHTML = '<li class="p-3 text-center text-muted"><i class="fas fa-spinner fa-spin"></i> Buscando...</li>';

            // 2. Busca os dados
            fetch('/api/notificacoes/listar')
                .then(res => res.json())
                .then(tarefas => {
                    listaSino.innerHTML = ''; // Limpa o carregando

                    if (!tarefas || tarefas.length === 0) {
                        listaSino.innerHTML = '<li class="p-3 text-center text-muted">Tudo em dia! 🎉</li>';
                        return;
                    }

                    listaSino.innerHTML += '<li><h6 class="dropdown-header">Pendências</h6></li>';

                    tarefas.forEach(t => {
                        // Proteção contra dados nulos
                        let titulo = t.titulo || 'Sem título';
                        let dataStr = t.data_prazo || '';
                        let prioridade = (t.prioridade || '').toLowerCase();

                        // Lógica Visual
                        let hoje = new Date().toISOString().split('T')[0];
                        let isCritico = (prioridade === 'alta' || (dataStr && dataStr < hoje));
                        let icone = isCritico ? '🔥' : '🔹';
                        let corTexto = isCritico ? 'text-danger fw-bold' : 'text-dark';

                        // Formata Data
                        let dataFmt = 'S/ Prazo';
                        if (dataStr) {
                            try { dataFmt = dataStr.split('-').reverse().slice(0, 2).join('/'); } catch(e){}
                        }

                        // HTML Blindado contra quebra de layout
                        listaSino.innerHTML += `
                            <li>
                                <a class="dropdown-item d-flex gap-2 align-items-center py-2" href="/kanban?t_id=${t.id}">
                                    <div style="overflow:hidden; width:100%">
                                        <div class="${corTexto} text-truncate-notify" title="${titulo}">
                                            ${titulo}
                                        </div>
                                        <small class="text-muted" style="font-size:0.75rem">${dataFmt}</small>
                                    </div>
                                </a>
                            </li>
                        `;
                    });

                    listaSino.innerHTML += '<li><hr class="dropdown-divider"></li>';
                    listaSino.innerHTML += '<li><a class="dropdown-item text-center small text-primary" href="/kanban">Ir para o Kanban</a></li>';
                })
                .catch(err => {
                    console.error(err);
                    listaSino.innerHTML = '<li class="p-3 text-center text-danger">Erro ao carregar lista.</li>';
                });
        });
    }

    // Inicialização
    atualizarContador();
    setInterval(atualizarContador, 120000); // 2 minutos
});