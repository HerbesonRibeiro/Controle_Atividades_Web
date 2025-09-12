document.addEventListener('DOMContentLoaded', function() {

    // --- 1. LÓGICA DAS NOTIFICAÇÕES (TOAST) ---
    const toasts = document.querySelectorAll('#toast-container .toast');
    toasts.forEach((toast) => {
        // Define um tempo para a notificação desaparecer
        setTimeout(() => {
            toast.classList.add('fade-out');
            // Remove o elemento da página após a animação de saída
            toast.addEventListener('animationend', () => toast.remove());
        }, 5000); // 5 segundos
    });

    // --- 2. LÓGICA DA SIDEBAR (BOTÃO HAMBURGER) ---
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    const body = document.body;
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            body.classList.toggle('sidebar-collapsed');
        });
    }

    // --- 3. LÓGICA DOS SUBMENUS (ABRIR/FECHAR AO CLICAR) ---
    const menuTitles = document.querySelectorAll('.sidebar-title');
    menuTitles.forEach(title => {
        title.addEventListener('click', function(event) {
            event.preventDefault(); // Impede que a página pule para o topo

            const submenu = this.nextElementSibling;

            // Segurança: verifica se o submenu realmente existe
            if (!submenu || !submenu.classList.contains('sidebar-submenu')) {
                return;
            }

            // Fecha todos os OUTROS submenus que estiverem abertos
            document.querySelectorAll('.sidebar-submenu').forEach(otherSubmenu => {
                if (otherSubmenu !== submenu) {
                    otherSubmenu.classList.add('hidden');
                }
            });

            // Abre ou fecha o submenu clicado
            submenu.classList.toggle('hidden');
        });
    });

    // --- 4. LÓGICA ESPECÍFICA DA PÁGINA DE HISTÓRICO ---
    // O código abaixo só será executado se encontrar o formulário do histórico,
    // evitando erros em outras páginas.
    const bulkForm = document.getElementById('bulk-action-form');
    if (bulkForm) {
        const selectAllCheckbox = document.getElementById('select-all-checkbox');
        const rowCheckboxes = document.querySelectorAll('.row-checkbox');
        const counterElement = document.getElementById('selection-counter');
        const editBtn = document.getElementById('edit-selected-btn');
        const deleteBtn = document.getElementById('delete-selected-btn');
        const detailsModal = document.getElementById('details-modal');
        const closeDetailsModalBtn = document.getElementById('close-details-modal-btn');
        const modalBody = document.getElementById('modal-body');
        const tableBody = document.querySelector('.table-uppercase tbody');

        // Função para atualizar contador e estado dos botões
        function updateCounterAndButtons() {
            const selectedCount = document.querySelectorAll('.row-checkbox:checked').length;

            if (counterElement) {
                counterElement.textContent = selectedCount === 1 ? '1 item selecionado' : `${selectedCount} itens selecionados`;
            }
            if (editBtn) editBtn.disabled = selectedCount !== 1;
            if (deleteBtn) deleteBtn.disabled = selectedCount === 0;
        }

        // Evento para o checkbox "Selecionar Todos"
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', function() {
                rowCheckboxes.forEach(checkbox => checkbox.checked = this.checked);
                updateCounterAndButtons();
            });
        }

        // Evento para os checkboxes individuais
        rowCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                selectAllCheckbox.checked = Array.from(rowCheckboxes).every(cb => cb.checked);
                updateCounterAndButtons();
            });
        });

        // Lógica do botão Editar
        if (editBtn) {
            editBtn.addEventListener('click', function() {
                const selectedCheckbox = document.querySelector('.row-checkbox:checked');
                if (selectedCheckbox) {
                    window.location.href = `/editar_atividade/${selectedCheckbox.value}`;
                }
            });
        }

        // Confirmação antes de excluir em massa
        bulkForm.addEventListener('submit', function(event) {
            const selectedCount = document.querySelectorAll('.row-checkbox:checked').length;
            if (selectedCount > 0 && !confirm(`Tem certeza que deseja excluir os ${selectedCount} itens selecionados?`)) {
                event.preventDefault();
            }
        });

        // Lógica do MODAL DE DETALHES
        if (tableBody) {
             tableBody.addEventListener('click', function(event) {
                const target = event.target.closest('.btn-details');
                if (target) {
                    const data = target.dataset;
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
                    detailsModal.classList.remove('hidden');
                }
            });
        }

        if (closeDetailsModalBtn && detailsModal) {
            closeDetailsModalBtn.addEventListener('click', () => detailsModal.classList.add('hidden'));
            detailsModal.addEventListener('click', (event) => {
                if (event.target === detailsModal) {
                    detailsModal.classList.add('hidden');
                }
            });
        }

        // Inicia a página com o contador e botões atualizados
        updateCounterAndButtons();
    }
});