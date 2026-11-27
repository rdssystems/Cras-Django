from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cras.fichas import contar_situacoes, tela_de_ficha

from .forms import DsfForm, formset_de_membros
from .models import Dsf, pode_preencher_dsf


def somente_quem_preenche(view):
    @wraps(view)
    @login_required
    def protegida(request, *args, **kwargs):
        if not pode_preencher_dsf(request.user):
            messages.error(request, 'A ficha do DSF é feita por Assistente Social ou Psicólogo(a).')
            return redirect('dsf:lista')
        return view(request, *args, **kwargs)
    return protegida


@login_required
def lista(request):
    dsfs = Dsf.objects.select_related('tecnico_responsavel')
    return render(request, 'dsf/lista.html', {
        'dsfs': dsfs,
        'pode_preencher': pode_preencher_dsf(request.user),
        **contar_situacoes(dsfs),
        'pendentes': dsfs.filter(ficha_preenchida=True, resultado='').count(),
    })


@somente_quem_preenche
def criar(request):
    inicial = {'data': timezone.localdate(), 'beneficio_solicitado': Dsf.Beneficio.CESTA_BASICA}
    return _ficha(request, Dsf(), 'Novo DSF', inicial)


@somente_quem_preenche
def editar(request, pk):
    dsf = get_object_or_404(Dsf, pk=pk)
    if not dsf.pendente:
        messages.error(request, 'Só é possível editar um DSF pendente.')
        return redirect('dsf:lista')
    return _ficha(request, dsf, 'Editar DSF')


def _ficha(request, dsf, titulo, inicial=None):
    def ao_criar(novo):
        novo.tecnico_responsavel = request.user
        novo.ficha_preenchida = True

    return tela_de_ficha(
        request, dsf, DsfForm, {'membros': formset_de_membros(dsf)},
        template='dsf/form.html', destino='dsf:lista', titulo=titulo, inicial=inicial,
        sucesso=('DSF registrado.', 'DSF atualizado.'), ao_criar=ao_criar,
    )
