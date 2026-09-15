/* =========================================================
   Shared application behavior: sidebar, toasts, icons, search
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    // Render Lucide icons
    if (window.lucide) {
        lucide.createIcons();
    }

    initSidebarToggle();
    initToasts();
    initGlobalSearch();
    initNotifications();
});

function initSidebarToggle() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const hamburger = document.getElementById("hamburgerBtn");

    if (!sidebar || !overlay || !hamburger) return;

    const openSidebar = () => {
        sidebar.classList.add("open");
        overlay.classList.add("show");
    };
    const closeSidebar = () => {
        sidebar.classList.remove("open");
        overlay.classList.remove("show");
    };

    hamburger.addEventListener("click", () => {
        sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
    });
    overlay.addEventListener("click", closeSidebar);
}

function initToasts() {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toasts = container.querySelectorAll(".toast");
    toasts.forEach((toast) => {
        const hideDelay = parseInt(toast.dataset.autohide || "6000", 10);
        const closeBtn = toast.querySelector(".toast-close");

        const remove = () => {
            toast.style.transition = "opacity 0.2s ease, transform 0.2s ease";
            toast.style.opacity = "0";
            toast.style.transform = "translateX(12px)";
            setTimeout(() => toast.remove(), 200);
        };

        if (closeBtn) closeBtn.addEventListener("click", remove);
        setTimeout(remove, hideDelay);
    });
}

function initGlobalSearch() {
    const input = document.getElementById("globalSearch");
    if (!input) return;

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && input.value.trim()) {
            const url = new URL(window.location.origin + "/expenses");
            url.searchParams.set("search", input.value.trim());
            window.location.href = url.toString();
        }
    });
}

function initNotifications() {
    const wrap = document.getElementById("notifWrap");
    const btn = document.getElementById("notifBtn");
    const dropdown = document.getElementById("notifDropdown");
    const dot = document.getElementById("notifDot");
    const list = document.getElementById("notifList");
    if (!wrap || !btn || !dropdown || !list) return;

    const iconToneMap = { danger: "tone-red", warning: "tone-orange", alert: "tone-orange" };

    const render = (notifications) => {
        if (!notifications.length) {
            list.innerHTML = `<div class="notif-empty">You're all caught up. No alerts right now.</div>`;
            return;
        }
        list.innerHTML = notifications.map((n) => `
            <div class="notif-item">
                <div class="notif-icon ${iconToneMap[n.type] || 'tone-orange'}"><i data-lucide="${n.icon}"></i></div>
                <div>
                    <p class="notif-title">${n.title}</p>
                    <p class="notif-message">${n.message}</p>
                </div>
            </div>
        `).join("");
        if (window.lucide) lucide.createIcons();
    };

    const fetchNotifications = () => {
        fetch("/api/notifications")
            .then((res) => res.json())
            .then((data) => {
                const notifications = data.notifications || [];
                dot.hidden = notifications.length === 0;
                render(notifications);
            })
            .catch(() => {
                list.innerHTML = `<div class="notif-empty">Couldn't load notifications.</div>`;
            });
    };

    fetchNotifications();

    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.hidden = !dropdown.hidden;
    });

    document.addEventListener("click", (e) => {
        if (!wrap.contains(e.target)) dropdown.hidden = true;
    });
}

/**
 * Show a toast without a full page reload (used by AJAX-driven actions).
 */
function showToast(message, type = "success") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const iconMap = { success: "check-circle", error: "x-circle", warning: "alert-triangle" };
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i data-lucide="${iconMap[type] || "info"}"></i>
        <span>${message}</span>
        <button class="toast-close" aria-label="Dismiss">&times;</button>
    `;
    container.appendChild(toast);
    if (window.lucide) lucide.createIcons();

    toast.querySelector(".toast-close").addEventListener("click", () => toast.remove());
    setTimeout(() => toast.remove(), 6000);
}

/**
 * Small helper used across pages to format numbers as Indian Rupees on the client side.
 */
function formatINR(value) {
    const num = Number(value) || 0;
    return "\u20b9" + num.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

/**
 * Confirm-before-delete helper attached to delete forms.
 */
function confirmDelete(message) {
    return window.confirm(message || "Are you sure you want to delete this item?");
}
