document.addEventListener("DOMContentLoaded", () => {
    initializeSidebar();
    initializeMessages();
    initializeUserMenu();
});


/**
 * Controla la apertura y cierre del sidebar
 * en dispositivos móviles.
 */
function initializeSidebar() {
    const sidebar = document.getElementById("app-sidebar");
    const sidebarToggle = document.getElementById("sidebar-toggle");

    if (!sidebar || !sidebarToggle) {
        return;
    }

    sidebarToggle.addEventListener("click", () => {
        const isOpen = sidebar.classList.toggle("is-open");

        sidebarToggle.setAttribute(
            "aria-expanded",
            String(isOpen)
        );

        sidebarToggle.setAttribute(
            "aria-label",
            isOpen
                ? "Cerrar menú de navegación"
                : "Abrir menú de navegación"
        );
    });

    const sidebarLinks = sidebar.querySelectorAll(
        ".sidebar__menu-link"
    );

    sidebarLinks.forEach((link) => {
        link.addEventListener("click", () => {
            if (window.innerWidth > 768) {
                return;
            }

            sidebar.classList.remove("is-open");

            sidebarToggle.setAttribute(
                "aria-expanded",
                "false"
            );

            sidebarToggle.setAttribute(
                "aria-label",
                "Abrir menú de navegación"
            );
        });
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth <= 768) {
            return;
        }

        sidebar.classList.remove("is-open");

        sidebarToggle.setAttribute(
            "aria-expanded",
            "false"
        );

        sidebarToggle.setAttribute(
            "aria-label",
            "Abrir menú de navegación"
        );
    });
}


/**
 * Permite cerrar manualmente los mensajes
 * generados por Django.
 */
function initializeMessages() {
    const closeButtons = document.querySelectorAll(
        ".message__close"
    );

    closeButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const message = button.closest(".message");

            if (!message) {
                return;
            }

            message.remove();
        });
    });
}


/**
 * Controla el menú desplegable del usuario.
 */
function initializeUserMenu() {
    const toggle = document.getElementById("user-menu-toggle");
    const dropdown = document.getElementById("user-menu-dropdown");

    if (!toggle || !dropdown) {
        return;
    }

    const closeMenu = () => {
        dropdown.hidden = true;

        toggle.setAttribute(
            "aria-expanded",
            "false"
        );

        toggle.setAttribute(
            "aria-label",
            "Abrir menú de usuario"
        );
    };

    const openMenu = () => {
        dropdown.hidden = false;

        toggle.setAttribute(
            "aria-expanded",
            "true"
        );

        toggle.setAttribute(
            "aria-label",
            "Cerrar menú de usuario"
        );
    };

    toggle.addEventListener("click", (event) => {
        event.stopPropagation();

        const isOpen =
            toggle.getAttribute("aria-expanded") === "true";

        if (isOpen) {
            closeMenu();
            return;
        }

        openMenu();
    });

    dropdown.addEventListener("click", (event) => {
        event.stopPropagation();
    });

    document.addEventListener("click", () => {
        closeMenu();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        closeMenu();
        toggle.focus();
    });
}