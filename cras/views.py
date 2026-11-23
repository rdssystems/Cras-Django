from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from triagem.models import Atendimento, listas_de_chamada

from .graficos import secoes_do_painel

ITENS_POR_FILA_NO_PAINEL = 5


@login_required
def inicio(request):
    hoje = timezone.localdate()
    atendidos = Atendimento.objects.filter(data=hoje, status=Atendimento.Status.ATENDIDO).count()
    total_hoje = Atendimento.objects.filter(data=hoje).count()

    filas = listas_de_chamada(hoje)
    total_aguardando = sum(f['count'] for f in filas)
    esperas = [
        item.tempo_espera_min
        for f in filas for item in f['itens']
        if item.tempo_espera_min is not None
    ]
    espera_media = int(sum(esperas) / len(esperas)) if esperas else 0

    # O painel mostra só os próximos a serem chamados em cada fila.
    for f in filas:
        f['itens'] = f['itens'][:ITENS_POR_FILA_NO_PAINEL]

    pct_atendidos = int(atendidos / total_hoje * 100) if total_hoje else 0

    secoes_graficos = secoes_do_painel(hoje)
    campos_do_js = ('tipo', 'categorias', 'series', 'dicas', 'unidade', 'eixo')
    dados_graficos = {
        g['chave']: {campo: g[campo] for campo in campos_do_js}
        for secao in secoes_graficos for g in secao['graficos'] if not g['vazio']
    }

    return render(request, 'inicio.html', {
        'secoes_graficos': secoes_graficos,
        'dados_graficos': dados_graficos,
        'filas': filas,
        'total_aguardando': total_aguardando,
        'atendidos': atendidos,
        'total_hoje': total_hoje,
        'espera_media': espera_media,
        'pct_atendidos': pct_atendidos,
        'hoje': hoje,
    })
