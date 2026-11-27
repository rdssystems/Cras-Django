from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CIDADE_PADRAO, CertidaoForm
from .models import Certidao


@login_required
def lista(request):
    certidoes = Certidao.objects.select_related('servidor')
    pendentes = certidoes.filter(data_entrega__isnull=True).count()
    return render(request, 'certidoes/lista.html', {'certidoes': certidoes, 'pendentes': pendentes})


@login_required
def criar(request):
    if request.method == 'POST':
        form = CertidaoForm(request.POST)
        if form.is_valid():
            certidao = form.save(commit=False)
            certidao.servidor = request.user
            certidao.ficha_preenchida = True
            certidao.save()
            messages.success(request, 'Certidão registrada.')
            return redirect('certidoes:lista')
    else:
        form = CertidaoForm(initial={'data_solicitacao': timezone.localdate(), 'cidade': CIDADE_PADRAO})
    return render(request, 'certidoes/form.html', {'form': form, 'titulo': 'Nova Certidão'})


@login_required
def editar(request, pk):
    certidao = get_object_or_404(Certidao, pk=pk)
    if request.method == 'POST':
        form = CertidaoForm(request.POST, instance=certidao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Certidão atualizada.')
            return redirect('certidoes:lista')
    else:
        form = CertidaoForm(instance=certidao)
    return render(request, 'certidoes/form.html', {
        'form': form, 'titulo': 'Editar Certidão',
        'acompanhamento': True,  # recebimento e entrega só existem depois da solicitação
    })
