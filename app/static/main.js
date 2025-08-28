document.addEventListener('DOMContentLoaded', function() {
    // --- Lógica da Sidebar (Sanfona) ---
    // 1. Seleciona TODOS os títulos de menu que têm a classe .sidebar-title
    const menuTitles = document.querySelectorAll('.sidebar-title');

    // 2. Adiciona um evento de clique para CADA um dos títulos encontrados
    menuTitles.forEach(title => {
        title.addEventListener('click', function(event) {
            event.preventDefault(); // Impede o link de pular para o topo da página

            // 3. Encontra o submenu que é o próximo "irmão" do título que foi clicado
            const submenu = this.nextElementSibling;

            // 4. Verifica se esse "irmão" é realmente um submenu e, se for, alterna a classe 'hidden'
            if (submenu && submenu.classList.contains('sidebar-submenu')) {
                submenu.classList.toggle('hidden');
            }
        });
    });

    // --- LÓGICA DAS AÇÕES EM MASSA E MODAL (PÁGINA DE HISTÓRICO) ---
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const rowCheckboxes = document.querySelectorAll('.row-checkbox');
    const counterElement = document.getElementById('selection-counter');
    const editBtn = document.getElementById('edit-selected-btn');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const bulkForm = document.getElementById('bulk-action-form');

    // Função para atualizar contador e estado dos botões
    function updateCounterAndButtons() {
        const selectedCount = document.querySelectorAll('.row-checkbox:checked').length;

        // Atualiza o texto do contador
        if (selectedCount === 0) {
            counterElement.textContent = 'Nenhum item selecionado';
        } else if (selectedCount === 1) {
            counterElement.textContent = '1 item selecionado';
        } else {
            counterElement.textContent = `${selectedCount} itens selecionados`;
        }

        // Habilita/desabilita botão de Editar (só para 1 item)
        editBtn.disabled = selectedCount !== 1;

        // Habilita/desabilita botão de Excluir (para 1 ou mais itens)
        deleteBtn.disabled = selectedCount === 0;
    }

    // Evento para o checkbox "Selecionar Todos"
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            rowCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateCounterAndButtons();
        });
    }

    // Evento para os checkboxes individuais
    rowCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            // Se um checkbox for desmarcado, o "Selecionar Todos" também é
            if (!checkbox.checked) {
                selectAllCheckbox.checked = false;
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
                window.location.href = `/editar/${activityId}`; // Redireciona para a página de edição
            }
        });
    }

    // Lógica do botão Excluir em Massa
    if (bulkForm) {
        bulkForm.addEventListener('submit', function(event) {
            event.preventDefault(); // Impede o envio imediato
            const selectedCount = document.querySelectorAll('.row-checkbox:checked').length;
            if (selectedCount > 0) {
                if (confirm(`Você tem certeza que deseja excluir os ${selectedCount} itens selecionados?`)) {
                    bulkForm.submit(); // Envia o formulário se o usuário confirmar
                }
            }
        });
    }

    // --- Lógica do MODAL DE DETALHES ---
    const detailsModal = document.getElementById('details-modal');
    const closeDetailsModalBtn = document.getElementById('close-details-modal-btn');
    const modalBody = document.getElementById('modal-body');

    document.querySelector('table tbody').addEventListener('click', function(event) {
        const target = event.target.closest('.btn-details');
        if (target) {
            const data = target.dataset;
            modalBody.innerHTML = `
                <p><strong>Data:</strong> ${data.data}</p>
                <p><strong>Tipo:</strong> ${data.tipo}</p>
                <p><strong>Colaborador:</strong> ${data.colaborador}</p>
                <p><strong>Status:</strong> ${data.status}</p>
                <hr>
                <p><strong>Descrição:</strong></p>
                <p>${data.descricao.replace(/\n/g, '<br>')}</p>
            `;
            detailsModal.classList.remove('hidden');
        }
    });

    if (closeDetailsModalBtn) {
        closeDetailsModalBtn.addEventListener('click', () => detailsModal.classList.add('hidden'));
        detailsModal.addEventListener('click', (event) => {
            if (event.target === detailsModal) {
                detailsModal.classList.add('hidden');
            }
        });
    }

    // Inicia a página com o contador zerado
    updateCounterAndButtons();
});

// --- Lógica para Notificações Toast ---
document.addEventListener('DOMContentLoaded', function() {
    const toasts = document.querySelectorAll('#toast-container .toast');

    toasts.forEach((toast, index) => {
        // Define um tempo para a notificação desaparecer
        setTimeout(() => {
            toast.classList.add('fade-out');

            // Remove o elemento do HTML depois que a animação de saída terminar
            toast.addEventListener('animationend', () => {
                toast.remove();
            });

        }, 5000); // 5000 milissegundos = 5 segundos
    });
});