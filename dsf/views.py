from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import DsfForm
from .models import Dsf


@login_required
def lista(request):
    dsfs = Dsf.objects.select_related('tecnico_responsavel')
    deferidos = dsfs.filter(resultado=Dsf.Resultado.DEFERIDO).count()
    indeferidos = dsfs.filter(resultado=Dsf.Resultado.INDEFERIDO).count()
    return render(request, 'dsf/lista.html', {'dsfs': dsfs, 'deferidos': deferidos, 'indeferidos': indeferidos})


@login_required
def criar(request):
    if request.method == 'POST':
        form = DsfForm(request.POST)
        if form.is_valid():
            dsf = form.save(commit=False)
            dsf.tecnico_responsavel = request.user
            dsf.save()
            messages.success(request, 'DSF registrado.')
            return redirect('dsf:lista')
    else:
        form = DsfForm()
    return render(request, 'dsf/form.html', {'form': form})
