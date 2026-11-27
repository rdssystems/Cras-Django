"""Dados dos gráficos do Painel (desenhados com Apache ECharts em cras/static/cras/js/painel-graficos.js).

Cada gráfico é um dict com o que o template mostra (titulo, subtitulo, largo, vazio)
e o que o JavaScript desenha (tipo, categorias, series, dicas, unidade, eixo).
"""
from collections import Counter
from datetime import timedelta

from django.db.models import Count

from atendimentos.models import RegistroAtendimento
from triagem.models import STATUS_FILA, Atendimento

DIAS_RECENTES = 30
# Cinza neutro (estado pendente, não uma categoria): contraste 3:1 com o fundo, separado do âmbar para daltônicos.
COR_AGUARDANDO = '#7c8ba1'
DIAS_SEMANA = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']

ROTULO_TIPO = {
    RegistroAtendimento.Tipo.PSICOSSOCIAL: 'Psicossocial',
    RegistroAtendimento.Tipo.ADMINISTRATIVO: 'Administrativo',
    RegistroAtendimento.Tipo.ORIENTACAO: 'Orientação',
    RegistroAtendimento.Tipo.OUTRO: 'Outro',
}

# ---------------------------------------------------------------- utilidades

def milhar(n):
    return f'{n:,}'.replace(',', '.')


def grafico(chave, titulo, tipo, categorias, series, *, subtitulo='', largo=False,
            dicas=None, unidade=('registro', 'registros'), eixo=''):
    total = sum(sum(s['valores']) for s in series)
    return {
        'chave': chave, 'titulo': titulo, 'subtitulo': subtitulo, 'largo': largo,
        'vazio': total == 0, 'tipo': tipo, 'categorias': categorias, 'series': series,
        'dicas': dicas, 'unidade': list(unidade), 'eixo': eixo,
    }


def serie(nome, valores, cor=None):
    """cor só para estados neutros (ex.: aguardando); séries comuns usam a paleta do JS, na ordem."""
    return {'nome': nome, 'valores': valores, 'cor': cor}


def numero(rotulo, valor, detalhe=''):
    """Um número da faixa de resumo que abre cada seção."""
    return {'rotulo': rotulo, 'valor': valor, 'detalhe': detalhe}


def porcentagem(parte, total):
    return f'{round(100 * parte / total)}%' if total else ''


def ranking(contagem):
    """[(rótulo, n)] do maior para o menor; empate em ordem alfabética."""
    return sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))


# ---------------------------------------------------------------- últimos 30 dias (sistema)

def desfecho(status, eh_hoje=False):
    if status == Atendimento.Status.ATENDIDO:
        return 'atendido'
    if status == Atendimento.Status.ATENDIDO_TRIAGEM:
        return 'triagem'
    # Quem ainda está na fila hoje pode ser atendido; só de ontem para trás vira "sem atendimento".
    if eh_hoje and status in STATUS_FILA:
        return 'aguardando'
    return 'sem_atendimento'


def secao_recente(hoje):
    inicio = hoje - timedelta(days=DIAS_RECENTES - 1)
    dias = [inicio + timedelta(days=i) for i in range(DIAS_RECENTES)]

    por_dia = {dia: Counter() for dia in dias}
    chegadas = Counter()
    triagens = Atendimento.objects.filter(data__range=(inicio, hoje))
    for dia, status, hora in triagens.values_list('data', 'status', 'hora_entrada'):
        por_dia[dia][desfecho(status, dia == hoje)] += 1
        if hora:
            chegadas[hora.hour] += 1
    total_triagens = sum(sum(c.values()) for c in por_dia.values())

    desfechos = [
        ('atendido', 'Atendidos', None),
        ('triagem', 'Resolvidos na triagem', None),
        ('sem_atendimento', 'Sem atendimento', None),
    ]
    if por_dia[hoje]['aguardando']:
        desfechos.append(('aguardando', 'Aguardando', COR_AGUARDANDO))
    grafico_dias = grafico(
        'por_dia', 'Atendimentos por dia', 'colunas_empilhadas',
        [dia.strftime('%d/%m') for dia in dias],
        [serie(nome, [por_dia[dia][chave] for dia in dias], cor) for chave, nome, cor in desfechos],
        largo=True, eixo='Dia',
        dicas=[f'{DIAS_SEMANA[dia.weekday()]}, {dia:%d/%m}' for dia in dias],
        unidade=('triagem', 'triagens'),
    )

    horas = list(range(min([7, *chegadas]), max([17, *chegadas]) + 1))
    grafico_horas = grafico(
        'horario', 'Chegadas por horário', 'colunas',
        [f'{h}h' for h in horas], [serie('Chegadas', [chegadas[h] for h in horas])],
        eixo='Horário',
        dicas=[f'{h}h às {h}h59' for h in horas], unidade=('chegada', 'chegadas'),
    )

    tipos = Counter({rotulo: 0 for rotulo in ROTULO_TIPO.values()})
    registros = (
        RegistroAtendimento.objects.filter(data__range=(inicio, hoje))
        .values_list('tipo_atendimento').annotate(n=Count('id'))
    )
    for tipo, n in registros:
        tipos[ROTULO_TIPO.get(tipo, 'Outro')] += n
    tipos_ordenados = ranking(tipos)
    grafico_tipos = grafico(
        'tipos', 'Tipo de atendimento', 'barras',
        [rotulo for rotulo, _ in tipos_ordenados],
        [serie('Atendimentos', [n for _, n in tipos_ordenados])],
        subtitulo=f'{milhar(sum(tipos.values()))} registros', eixo='Tipo',
        unidade=('atendimento', 'atendimentos'),
    )

    total = Counter()
    for contagem in por_dia.values():
        total.update(contagem)
    atendidas = total['atendido'] + total['triagem']
    hora_pico = max(chegadas, key=lambda h: (chegadas[h], -h)) if chegadas else None

    return {
        'titulo': f'Últimos {DIAS_RECENTES} dias',
        'icone': 'monitoring',
        'sub': f'{inicio:%d/%m} a {hoje:%d/%m/%Y}',
        'resumo': [
            numero('Triagens', milhar(total_triagens)),
            numero('Atendidas', milhar(atendidas), porcentagem(atendidas, total_triagens)),
            numero('Sem atendimento', milhar(total['sem_atendimento']),
                   porcentagem(total['sem_atendimento'], total_triagens)),
            numero('Horário de pico', f'{hora_pico}h' if hora_pico is not None else '—'),
        ],
        'graficos': [grafico_dias, grafico_tipos, grafico_horas],
    }


def secoes_do_painel(hoje):
    return [secao_recente(hoje)]
