from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cras.fichas import contar_situacoes, tela_de_ficha

from .forms import RequerimentoProPaoForm, formset_de_pessoas, formset_de_procedimentos
from .models import RequerimentoProPao


@login_required
def lista(request):
    requerimentos = RequerimentoProPao.objects.select_related('servidor')
    return render(request, 'propao/lista.html', {
        'requerimentos': requerimentos,
        **contar_situacoes(requerimentos),
    })


@login_required
def criar(request):
    return _ficha(request, RequerimentoProPao(), 'Novo Requerimento PRÓ-PÃO', {'data': timezone.localdate()})


@login_required
def editar(request, pk):
    requerimento = get_object_or_404(RequerimentoProPao, pk=pk)
    if not requerimento.pendente:
        messages.error(request, 'Só é possível editar um requerimento pendente.')
        return redirect('propao:lista')
    return _ficha(request, requerimento, 'Editar Requerimento PRÓ-PÃO')


def _ficha(request, requerimento, titulo, inicial=None):
    tabelas = {
        'pessoas': formset_de_pessoas(requerimento),
        'procedimentos': formset_de_procedimentos(requerimento),
    }
    return tela_de_ficha(
        request, requerimento, RequerimentoProPaoForm, tabelas,
        template='propao/form.html', destino='propao:lista', titulo=titulo, inicial=inicial,
        sucesso=('Requerimento registrado.', 'Requerimento atualizado.'),
        ao_criar=lambda novo: setattr(novo, 'servidor', request.user),
    )
