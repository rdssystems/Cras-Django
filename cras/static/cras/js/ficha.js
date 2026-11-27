// Comportamento das fichas: CPF só com números e tabelas com linhas que entram e saem.
document.querySelectorAll('[data-cpf]').forEach(function (campo) {
    campo.addEventListener('input', function () {
        campo.value = campo.value.replace(/\D/g, '').slice(0, 11);
    });
});

document.querySelectorAll('[data-linhas]').forEach(function (corpo) {
    var prefixo = corpo.dataset.linhas;
    var total = document.getElementById('id_' + prefixo + '-TOTAL_FORMS');

    document.querySelector('[data-adicionar="' + prefixo + '"]').addEventListener('click', function () {
        var modelo = document.querySelector('[data-modelo="' + prefixo + '"]').innerHTML;
        corpo.insertAdjacentHTML('beforeend', modelo.replace(/__prefix__/g, total.value));
        total.value = Number(total.value) + 1;
        corpo.lastElementChild.querySelector('input, textarea, select').focus();
    });

    // A linha removida some da tela e vai marcada para o Django apagar (ou ignorar).
    corpo.addEventListener('click', function (evento) {
        var botao = evento.target.closest('[data-remover-linha]');
        if (!botao) return;
        var linha = botao.closest('tr');
        linha.querySelector('input[name$="-DELETE"]').checked = true;
        linha.classList.add('removido');
    });
});
