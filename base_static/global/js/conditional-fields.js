/*
 * Campos que só aparecem quando uma opção está marcada.
 *
 *   <div data-show-if-name="venues" data-show-if-value="other"> ... </div>
 *
 * O bloco fica visível só se houver um input name="venues" value="other"
 * marcado (caixinha ou opção). Para uma caixinha simples, o valor é "on".
 * O servidor também apaga o texto de uma opção desmarcada; aqui é só a tela.
 */
(function () {
    function selector(block) {
        return 'input[name="' + block.dataset.showIfName + '"][value="' + block.dataset.showIfValue + '"]';
    }

    function refresh() {
        document.querySelectorAll("[data-show-if-name]").forEach(function (block) {
            var input = document.querySelector(selector(block));
            block.classList.toggle("hidden", !(input && input.checked));
        });
    }

    document.addEventListener("change", function (event) {
        if (event.target.matches("input[type=checkbox], input[type=radio]")) refresh();
    });
    document.addEventListener("DOMContentLoaded", refresh);
})();
