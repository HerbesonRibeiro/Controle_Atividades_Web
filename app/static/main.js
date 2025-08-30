document.addEventListener('DOMContentLoaded', function() {

    // --- LÓGICA GERAL E NOTIFICAÇÕES (TOAST) ---
    // Esta parte roda em todas as páginas
    const toasts = document.querySelectorAll('#toast-container .toast');
    toasts.forEach((toast) => {
        setTimeout(() => {
            toast.classList.add('fade-out');
            toast.addEventListener('animationend', () => toast.remove());
        }, 5000); // Desaparece após 5 segundos
    });


    // --- LÓGICA DA SIDEBAR (SANFONA) ---
    // Esta parte também roda em todas as páginas com sidebar
    const menuTitles = document.querySelectorAll('.sidebar-title');
    menuTitles.forEach(title => {
        title.addEventListener('click', function(event) {
            event.preventDefault();
            const submenu = this.nextElementSibling;
            if (submenu && submenu.classList.contains('sidebar-submenu')) {
                submenu.classList.toggle('hidden');
            }
        });
    });


    // --- LÓGICA ESPECÍFICA DA PÁGINA DE HISTÓRICO ---
    // O código abaixo só será executado se os elementos da página de histórico existirem,
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
                if (selectedCount === 0) {
                    counterElement.textContent = 'Nenhum item selecionado';
                } else if (selectedCount === 1) {
                    counterElement.textContent = '1 item selecionado';
                } else {
                    counterElement.textContent = `${selectedCount} itens selecionados`;
                }
            }
            if (editBtn) editBtn.disabled = selectedCount !== 1;
            if (deleteBtn) deleteBtn.disabled = selectedCount === 0;
        }

        // Evento para o checkbox "Selecionar Todos"
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', function() {
                rowCheckboxes.forEach(checkbox => {
                    checkbox.checked = this.checked;
                });
                updateCounterAndButtons();
            });
        }

        // Evento para os checkboxes individuais
        rowCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                if (!this.checked) {
                    selectAllCheckbox.checked = false;
                } else {
                    const allSelected = Array.from(rowCheckboxes).every(cb => cb.checked);
                    selectAllCheckbox.checked = allSelected;
                }
                updateCounterAndButtons();
            });
        });

        // Lógica do botão Editar
        if (editBtn) {
            editBtn.addEventListener('click', function() {
                const selectedCheckbox = document.querySelector('.row-checkbox:checked');
                if (selectedCheckbox) {
                    const activityId = selectedCheckbox.value;
                    // CORREÇÃO IMPORTANTE: A URL da sua rota de edição
                    window.location.href = `/editar_atividade/${activityId}`;
                }
            });
        }

        // Confirmação antes de excluir em massa
        bulkForm.addEventListener('submit', function(event) {
            const selectedCount = document.querySelectorAll('.row-checkbox:checked').length;
            if (selectedCount > 0) {
                const confirmed = confirm(`Tem certeza que deseja excluir os ${selectedCount} itens selecionados?`);
                if (!confirmed) {
                    event.preventDefault(); // Cancela o envio do formulário
                }
            } else {
                event.preventDefault();
            }
        });

        // Lógica do MODAL DE DETALHES (com event delegation mais segura)
        if (tableBody) {
             tableBody.addEventListener('click', function(event) {
                const target = event.target.closest('.btn-details');
                if (target) {
                    const data = target.dataset;
                    modalBody.innerHTML = `
                        <p><strong>ID:</strong> ${data.id}</p>
                        <p><strong>Data:</strong> ${data.data}</p>
                        <p><strong>Tipo:</strong> ${data.tipo}</p>
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