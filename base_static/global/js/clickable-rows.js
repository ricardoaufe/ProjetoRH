/*
 * Linhas de tabela clicáveis: <tr class="clickable-row" data-href="...">.
 *
 * Clicar em qualquer parte da linha abre o data-href. Links, botões e campos
 * dentro da linha continuam funcionando sozinhos (ex.: clipe dos anexos,
 * ícones de Excel). Ctrl/Cmd + clique ou o botão do meio abrem em nova aba,
 * como num link comum. Selecionar texto da linha não navega.
 */
(function () {
    var INTERACTIVE = "a, button, input, select, textarea, label, form";

    function targetRow(event) {
        if (event.target.closest(INTERACTIVE)) return null;
        return event.target.closest("tr.clickable-row[data-href]");
    }

    document.addEventListener("click", function (event) {
        var row = targetRow(event);
        if (!row || String(window.getSelection())) return;
        if (event.ctrlKey || event.metaKey) {
            window.open(row.dataset.href, "_blank");
        } else {
            window.location.href = row.dataset.href;
        }
    });

    document.addEventListener("auxclick", function (event) {
        if (event.button !== 1) return;
        var row = targetRow(event);
        if (!row) return;
        event.preventDefault();
        window.open(row.dataset.href, "_blank");
    });
})();
