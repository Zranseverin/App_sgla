document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    document.querySelectorAll("[data-sidebar-open]").forEach((button) => {
        button.addEventListener("click", () => body.classList.add("sidebar-open"));
    });
    document.querySelectorAll("[data-sidebar-close]").forEach((button) => {
        button.addEventListener("click", () => body.classList.remove("sidebar-open"));
    });

    const search = document.querySelector(".global-search input");
    document.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
            event.preventDefault();
            search?.focus();
        }
    });

    document.querySelectorAll("[data-tab]").forEach((tab) => {
        tab.addEventListener("click", () => {
            document.querySelectorAll("[data-tab]").forEach((item) => item.classList.remove("active"));
            tab.classList.add("active");
        });
    });

    const notificationToggle = document.querySelector("[data-notifications-toggle]");
    const notificationPanel = document.querySelector("[data-notifications-panel]");
    const notificationBox = document.querySelector(".notifications");

    const closeNotifications = () => {
        if (!notificationPanel || !notificationToggle) return;
        notificationPanel.hidden = true;
        notificationToggle.setAttribute("aria-expanded", "false");
    };

    notificationToggle?.addEventListener("click", (event) => {
        event.stopPropagation();
        const willOpen = notificationPanel.hidden;
        closeAccount();
        notificationPanel.hidden = !willOpen;
        notificationToggle.setAttribute("aria-expanded", String(willOpen));
    });

    document.addEventListener("click", (event) => {
        if (!notificationBox?.contains(event.target)) closeNotifications();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeNotifications();
    });

    document.querySelector("[data-mark-read]")?.addEventListener("click", () => {
        document.querySelectorAll(".unread-dot").forEach((dot) => dot.remove());
        const count = document.querySelector("[data-notifications-count]");
        if (count) count.hidden = true;
        const subtitle = document.querySelector(".notifications-head span");
        if (subtitle) subtitle.textContent = "Aucune nouvelle";
    });

    const accountToggle = document.querySelector("[data-account-toggle]");
    const accountPanel = document.querySelector("[data-account-panel]");
    const accountMenu = document.querySelector(".account-menu");

    const closeAccount = () => {
        if (!accountPanel || !accountToggle) return;
        accountPanel.hidden = true;
        accountToggle.setAttribute("aria-expanded", "false");
    };

    accountToggle?.addEventListener("click", (event) => {
        event.stopPropagation();
        const willOpen = accountPanel.hidden;
        closeNotifications();
        accountPanel.hidden = !willOpen;
        accountToggle.setAttribute("aria-expanded", String(willOpen));
    });

    document.addEventListener("click", (event) => {
        if (!accountMenu?.contains(event.target)) closeAccount();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeAccount();
    });

    const companyColorInput = document.querySelector(".color-control");
    companyColorInput?.addEventListener("input", (event) => {
        document.body.style.setProperty("--company-color", event.target.value);
    });
});
