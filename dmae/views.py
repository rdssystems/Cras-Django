from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cras.fichas import contar_situacoes, tela_de_ficha

from .forms import IsencaoDmaeForm, formset_de_evolucao, formset_de_membros
from .models import IsencaoDmae


@login_required
def lista(request):
    requerimentos = IsencaoDmae.objects.select_related('servidor')
    return render(request, 'dmae/lista.html', {
        'requerimentos': requerimentos,
        **contar_situacoes(requerimentos),
    })


@login_required
def criar(request):
    return _ficha(request, IsencaoDmae(), 'Novo Requerimento DMAE', {'data': timezone.localdate()})


@login_required
def editar(request, pk):
    requerimento = get_object_or_404(IsencaoDmae, pk=pk)
    if not requerimento.pendente:
        messages.error(request, 'Só é possível editar um requerimento pendente.')
        return redirect('dmae:lista')
    return _ficha(request, requerimento, 'Editar Requerimento DMAE')


def _ficha(request, requerimento, titulo, inicial=None):
    tabelas = {'membros': formset_de_membros(requerimento), 'evolucoes': formset_de_evolucao(requerimento)}
    return tela_de_ficha(
        request, requerimento, IsencaoDmaeForm, tabelas,
        template='dmae/form.html', destino='dmae:lista', titulo=titulo, inicial=inicial,
        sucesso=('Requerimento registrado.', 'Requerimento atualizado.'),
        ao_criar=lambda novo: setattr(novo, 'servidor', request.user),
    )
