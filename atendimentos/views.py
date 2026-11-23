from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import RegistroAtendimento


@login_required
def lista(request):
    registros = RegistroAtendimento.objects.select_related('responsavel', 'atendimento_origem')
    data = request.GET.get('data')
    if data:
        from datetime import date
        try:
            registros = registros.filter(data=date.fromisoformat(data))
        except ValueError:
            messages.error(request, 'Data inválida.')
    return render(request, 'atendimentos/lista.html', {'registros': registros})
