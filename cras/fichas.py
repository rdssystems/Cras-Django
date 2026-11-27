"""Fluxo comum das fichas (DSF, Isenção DMAE e PRÓ-PÃO): formulário e tabelas de linhas salvos juntos."""
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from .escolhas import Resultado


def contar_situacoes(registros):
    """Totais dos cartões da lista. O DSF recalcula os pendentes, por causa dos registros da planilha."""
    return {
        'pendentes': registros.filter(resultado='').count(),
        'deferidos': registros.filter(resultado=Resultado.DEFERIDO).count(),
        'indeferidos': registros.filter(resultado=Resultado.INDEFERIDO).count(),
    }


def tela_de_ficha(request, registro, form_class, tabelas, *, template, destino, titulo,
                  sucesso, ao_criar, inicial=None):
    """Mostra e salva uma ficha.

    `tabelas` é {prefixo: classe do formset}; `sucesso` é (mensagem ao criar, mensagem ao editar);
    `ao_criar(registro)` preenche o que só vale na criação, como quem fez a ficha.
    """
    novo = registro.pk is None
    dados = request.POST if request.method == 'POST' else None
    form = form_class(dados, instance=registro, initial=inicial)
    linhas = {prefixo: Formset(dados, instance=registro, prefix=prefixo) for prefixo, Formset in tabelas.items()}
    # Valida tudo (lista, e não gerador), para a tela mostrar todos os erros de uma vez.
    if dados is not None and all([form.is_valid(), *[tabela.is_valid() for tabela in linhas.values()]]):
        with transaction.atomic():
            registro = form.save(commit=False)
            if novo:
                ao_criar(registro)
            registro.save()
            for tabela in linhas.values():
                tabela.save()
        messages.success(request, sucesso[0] if novo else sucesso[1])
        return redirect(destino)
    return render(request, template, {'form': form, 'titulo': titulo, 'registro': registro, **linhas})
