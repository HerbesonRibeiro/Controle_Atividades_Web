/**
 * pds.js — Funções visuais e utilitárias do CRM / Modal / Copiar Link / Toasts
 * Autor: Herbeson Ribeiro
 * Data: 2025
 */

// Espera o DOM carregar antes de iniciar
document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
       [1] SISTEMA DE TOASTS (mensagens flutuantes)
       ===================================================== */
    const toasts = document.querySelectorAll("#toast-container .toast");
    toasts.forEach((toast) => {
        setTimeout(() => {
            toast.classList.add("fade-out");
            toast.addEventListener("animationend", () => toast.remove());
        }, 4000);
    });

    /* =====================================================
       [2] BOTÕES "COPIAR LINK"
       ===================================================== */
    document.querySelectorAll(".btn-copy").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            const link = e.currentTarget.dataset.link;
            if (!link) return;

            try {
                await navigator.clipboard.writeText(link);
                mostrarToast("Link copiado com sucesso!", "success");
            } catch (err) {
                console.error("Erro ao copiar:", err);
                mostrarToast("Erro ao copiar link.", "error");
            }
        });
    });

    /* =====================================================
       [3] MODAIS GLOBAIS
       ===================================================== */
    document.querySelectorAll(".modal-overlay").forEach((modal) => {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) fecharModal(modal.id);
        });
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            const aberto = document.querySelector(".modal-overlay:not(.hidden)");
            if (aberto) fecharModal(aberto.id);
        }
    });
});

/* =====================================================
   [FUNÇÕES GLOBAIS]
   ===================================================== */

/** Abre um modal pelo ID */
function abrirModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove("hidden");
}

/** Fecha um modal pelo ID */
function fecharModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add("hidden");
}

/** Exibe uma mensagem flutuante (toast) personalizada */
function mostrarToast(mensagem, tipo = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${tipo}`;
    toast.innerHTML = `
        <div class="toast-message">${mensagem}</div>
        <button class="toast-close-btn">&times;</button>
    `;

    container.appendChild(toast);

    toast.querySelector(".toast-close-btn").addEventListener("click", () => {
        toast.classList.add("fade-out");
        toast.addEventListener("animationend", () => toast.remove());
    });

    setTimeout(() => {
        toast.classList.add("fade-out");
        toast.addEventListener("animationend", () => toast.remove());
    }, 4000);
}
