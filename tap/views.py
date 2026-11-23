from calendar import monthrange
from datetime import date

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import TapDiario


@login_required
def mensal(request):
    # O POST traz ano/mes em campos ocultos; o GET, na querystring.
    dados = request.POST if request.method == 'POST' else request.GET
    ano = dados.get('ano') or request.GET.get('ano') or timezone.localdate().year
    mes = dados.get('mes') or request.GET.get('mes') or timezone.localdate().month
    try:
        ano, mes = int(ano), int(mes)
        dias = monthrange(ano, mes)[1]
    except ValueError:
        return redirect('tap:mensal')

    registros = {r.data.day: r.tap_diario for r in TapDiario.objects.filter(data__year=ano, data__month=mes)}

    class TapForm(forms.Form):
        pass

    for dia in range(1, dias + 1):
        TapForm.base_fields[f'tap_{dia}'] = forms.IntegerField(
            required=False, min_value=0, initial=registros.get(dia, 0),
            widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        )

    if request.method == 'POST':
        form = TapForm(request.POST)
        if form.is_valid():
            for dia in range(1, dias + 1):
                valor = form.cleaned_data[f'tap_{dia}'] or 0
                TapDiario.objects.update_or_create(
                    data=date(ano, mes, dia), defaults={'tap_diario': valor}
                )
            messages.success(request, f'TAP de {mes:02d}/{ano} salvo.')
            return redirect(f"{reverse('tap:mensal')}?ano={ano}&mes={mes}")
    else:
        form = TapForm()

    linhas = [{'dia': d, 'campo': f'tap_{d}'} for d in range(1, dias + 1)]
    total = sum(registros.values())
    return render(request, 'tap/mensal.html', {
        'form': form, 'linhas': linhas, 'ano': ano, 'mes': mes, 'dias': dias, 'total': total,
    })
