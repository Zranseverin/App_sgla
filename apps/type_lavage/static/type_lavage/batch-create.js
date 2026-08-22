document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("service-lines");
    const addButton = document.getElementById("add-service-line");
    const template = document.getElementById("empty-service-line");
    const total = document.getElementById("id_services-TOTAL_FORMS");
    if (!container || !addButton || !template || !total) return;

    const bindRemove = (line) => {
        line.querySelector("[data-remove-line]")?.addEventListener("click", () => {
            const deleteInput = line.querySelector('input[name$="-DELETE"]');
            const visibleLines = [...container.querySelectorAll(".wash-service-line")].filter((item) => !item.hidden);
            if (visibleLines.length === 1) {
                line.querySelectorAll('input:not([type="checkbox"])').forEach((input) => { input.value = ""; });
                return;
            }
            if (deleteInput) deleteInput.checked = true;
            line.hidden = true;
        });
    };
    container.querySelectorAll(".wash-service-line").forEach(bindRemove);
    addButton.addEventListener("click", () => {
        const index = Number(total.value);
        const wrapper = document.createElement("div");
        wrapper.innerHTML = template.innerHTML.replaceAll("__prefix__", String(index)).trim();
        const line = wrapper.firstElementChild;
        container.appendChild(line);
        total.value = String(index + 1);
        bindRemove(line);
        line.querySelector("input")?.focus();
    });
});
