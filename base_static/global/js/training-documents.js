/*
 * Documentos escaneados do treinamento (dashboard/pages/training/form.html).
 *
 * O <input type="file"> do navegador troca a seleção a cada vez que é aberto:
 * escolher um arquivo, depois outro, deixaria só o último. Aqui os arquivos
 * escolhidos vão se acumulando (DataTransfer) e aparecem numa lista, com um
 * botão para retirar cada um. Todos são enviados juntos ao salvar.
 */
(function () {
    function formatSize(bytes) {
        if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1).replace(".", ",") + " MB";
        return Math.max(1, Math.round(bytes / 1024)) + " KB";
    }

    function sameFile(a, b) {
        return a.name === b.name && a.size === b.size && a.lastModified === b.lastModified;
    }

    function initPendingDocuments() {
        var input = document.getElementById("id_documents");
        var list = document.getElementById("pending-documents");
        if (!input || !list || typeof DataTransfer === "undefined") return;

        var picked = new DataTransfer();

        function render() {
            list.replaceChildren();
            Array.from(picked.files).forEach(function (file, index) {
                var item = document.createElement("li");
                item.className = "training-docs__pending-item";

                var name = document.createElement("span");
                name.className = "training-docs__pending-name";
                name.textContent = file.name + " (" + formatSize(file.size) + ")";

                var remove = document.createElement("button");
                remove.type = "button";
                remove.className = "training-docs__pending-remove";
                remove.title = "Retirar este arquivo";
                remove.innerHTML = '<i class="fa fa-times"></i> Retirar';
                remove.addEventListener("click", function () {
                    picked.items.remove(index);
                    input.files = picked.files;
                    render();
                });

                item.append(name, remove);
                list.append(item);
            });
            list.hidden = picked.files.length === 0;
        }

        input.addEventListener("change", function () {
            Array.from(input.files).forEach(function (file) {
                var duplicate = Array.from(picked.files).some(function (f) { return sameFile(f, file); });
                if (!duplicate) picked.items.add(file);
            });
            // Também cobre o "Cancelar" da janela, que esvaziaria o campo.
            input.files = picked.files;
            render();
        });
    }

    document.addEventListener("DOMContentLoaded", initPendingDocuments);
})();
