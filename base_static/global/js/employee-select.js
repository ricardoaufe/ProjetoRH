/*
 * Busca por nome nos campos que escolhem funcionário (classe js-employee-select).
 * Usa o Tom Select, carregado por partials/employee_select.html.
 *
 * - Campo simples (Férias, Plano de Carreira): um funcionário por vez.
 * - Campo múltiplo (Treinamentos): vários, e a busca se apaga a cada nome
 *   adicionado, para digitar o próximo sem apagar o anterior.
 *
 * O Tom Select dispara "change" no <select> original, então os listeners
 * que já existiam nas páginas (ex.: AJAX do Plano de Carreira) continuam valendo.
 */
(function () {
    function initEmployeeSelects() {
        document.querySelectorAll("select.js-employee-select").forEach(function (el) {
            if (el.tomselect) return;

            const options = {
                create: false,
                maxOptions: null,
                sortField: { field: "text", direction: "asc" },
                placeholder: el.dataset.placeholder || "Digite o nome do funcionário...",
            };

            if (el.multiple) {
                options.plugins = ["remove_button"];
                options.onItemAdd = function () {
                    this.setTextboxValue("");
                    this.refreshOptions(false);
                };
            } else {
                options.maxItems = 1;
                options.allowEmptyOption = false;
            }

            new TomSelect(el, options);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initEmployeeSelects);
    } else {
        initEmployeeSelects();
    }
})();
