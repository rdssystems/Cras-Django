"""Dados dos gráficos do Painel (desenhados com Apache ECharts em cras/static/cras/js/painel-graficos.js).

Cada gráfico é um dict com o que o template mostra (titulo, subtitulo, largo, vazio)
e o que o JavaScript desenha (tipo, categorias, series, dicas, unidade, eixo).
"""
import re
import unicodedata
from collections import Counter
from datetime import date, timedelta

from django.core.cache import cache
from django.db.models import Count, Max
from django.db.models.functions import TruncMonth

from administrativo.models import RegistroAdministrativo
from atendimentos.models import RegistroAtendimento
from triagem.models import STATUS_FILA, Atendimento

DIAS_RECENTES = 30
# Cinza neutro (estado pendente, não uma categoria): contraste 3:1 com o fundo, separado do âmbar para daltônicos.
COR_AGUARDANDO = '#7c8ba1'
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
DIAS_SEMANA = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']

# Nas pontas da série mensal, meses com menos registros que isso são datas digitadas
# erradas na planilha (há atendimentos "em 1930" e "em 2032").
MINIMO_MES_NA_PONTA = 10
TOP_BAIRROS = 10
IDADE_MAXIMA = 110
FAIXAS_ETARIAS = [
    (0, 17, '0 a 17'), (18, 29, '18 a 29'), (30, 39, '30 a 39'), (40, 49, '40 a 49'),
    (50, 59, '50 a 59'), (60, 79, '60 a 79'), (80, IDADE_MAXIMA, '80+'),
]
VEZES = ['1 vez', '2 vezes', '3 vezes', '4 vezes', '5 ou mais']

ROTULO_TIPO = {
    RegistroAtendimento.Tipo.PSICOSSOCIAL: 'Psicossocial',
    RegistroAtendimento.Tipo.ADMINISTRATIVO: 'Administrativo',
    RegistroAtendimento.Tipo.ORIENTACAO: 'Orientação',
    RegistroAtendimento.Tipo.OUTRO: 'Outro',
}

# Chave normalizada (sem acento) -> rótulo exibido.
ROTULO_MOTIVO = {
    'ATUALIZACAO CADASTRAL - CADUNICO': 'Atualização cadastral (CadÚnico)',
    'CADASTRO NOVO - CADUNICO': 'Cadastro novo (CadÚnico)',
    'DMAE': 'DMAE',
    'CERTIDAO DE NASCIMENTO': 'Certidão de nascimento',
    'ORIENTACAO': 'Orientação',
    'SEGUNDA VIA RG': 'Segunda via do RG',
    'CERTIDAO DE CASAMENTO': 'Certidão de casamento',
    'PSICOSSOCIAL': 'Psicossocial',
    'PSICOSOCIAL': 'Psicossocial',
    'FOLHA RESUMO': 'Folha resumo',
    'CESTA BASICA': 'Cesta básica',
    'CERTIDAO DE OBITO': 'Certidão de óbito',
    'OUTRO': 'Outro',
}

ABREVIACOES_BAIRRO = [
    (re.compile(r'^STA\.? '), 'SANTA '),
    (re.compile(r'^STO\.? '), 'SANTO '),
    (re.compile(r'^JD\.? '), 'JARDIM '),
    (re.compile(r'^RES\.? '), 'RESIDENCIAL '),
]
PALAVRAS_MINUSCULAS = {'De', 'Da', 'Do', 'Das', 'Dos', 'E'}


# ---------------------------------------------------------------- utilidades

def milhar(n):
    return f'{n:,}'.replace(',', '.')


def sem_acento(texto):
    texto = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', texto).strip().upper()


def titulo_ptbr(texto):
    palavras = texto.strip().title().split()
    return ' '.join(
        p.lower() if i and p in PALAVRAS_MINUSCULAS else p
        for i, p in enumerate(palavras)
    )


def rotulo_mes(mes):
    return f'{MESES[mes.month - 1]}/{mes.year}'


def meses_entre(inicio, fim):
    atual = inicio
    while atual <= fim:
        yield atual
        atual = date(atual.year + atual.month // 12, atual.month % 12 + 1, 1)


def idade_em(nascimento, dia):
    return dia.year - nascimento.year - ((dia.month, dia.day) < (nascimento.month, nascimento.day))


def faixa_etaria(idade):
    for minimo, maximo, rotulo in FAIXAS_ETARIAS:
        if minimo <= idade <= maximo:
            return rotulo
    return None


def chave_pessoa(cpf, nome):
    """CPF (só dígitos) identifica a pessoa; sem CPF válido, cai para o nome."""
    digitos = re.sub(r'\D', '', cpf or '')
    if 9 <= len(digitos) <= 11:
        digitos = digitos.zfill(11)  # a planilha perdeu o zero à esquerda de alguns CPFs
    if digitos and len(set(digitos)) > 1:
        return 'cpf:' + digitos
    nome = sem_acento(nome)
    return 'nome:' + nome if nome else None


def expandir_abreviacoes(texto):
    for padrao, troca in ABREVIACOES_BAIRRO:
        texto = padrao.sub(troca, texto)
    return texto


def chave_bairro(bairro):
    return expandir_abreviacoes(sem_acento(bairro))


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


# ---------------------------------------------------------------- histórico administrativo (planilha)

def periodo_valido(por_mes):
    """Primeiro e último mês com volume real, descartando datas digitadas erradas nas pontas."""
    meses = sorted(mes for mes, n in por_mes.items() if n >= MINIMO_MES_NA_PONTA)
    return (meses[0], meses[-1]) if meses else (None, None)


def secao_historico():
    registros = RegistroAdministrativo.objects.all()

    por_mes = dict(
        registros.exclude(data_atendimento=None)
        .annotate(mes=TruncMonth('data_atendimento'))
        .values_list('mes').annotate(n=Count('id'))
    )
    inicio, fim = periodo_valido(por_mes)
    meses = list(meses_entre(inicio, fim)) if inicio else []
    valores_mes = [por_mes.get(mes, 0) for mes in meses]
    pico = max(range(len(meses)), key=lambda i: valores_mes[i]) if meses else None
    grafico_meses = grafico(
        'por_mes', 'Atendimentos por mês', 'area',
        [rotulo_mes(mes) for mes in meses], [serie('Atendimentos', valores_mes)],
        subtitulo=f'Pico de {milhar(valores_mes[pico])} em {rotulo_mes(meses[pico])}' if pico is not None else '',
        largo=True, eixo='Mês',
        unidade=('atendimento', 'atendimentos'),
    )

    motivos = Counter()
    sem_motivo = 0
    for motivo, n in registros.values_list('motivo').annotate(n=Count('id')):
        chave = sem_acento(motivo)
        if not chave:
            sem_motivo += n
            continue
        motivos[ROTULO_MOTIVO.get(chave) or motivo.strip().capitalize()] += n
    motivos_ordenados = ranking(motivos)
    grafico_motivos = grafico(
        'motivos', 'Motivos dos atendimentos', 'barras',
        [rotulo for rotulo, _ in motivos_ordenados],
        [serie('Atendimentos', [n for _, n in motivos_ordenados])],
        subtitulo=f'{milhar(sem_motivo)} sem motivo informado' if sem_motivo else '',
        eixo='Motivo', unidade=('atendimento', 'atendimentos'),
    )

    # Uma linha por atendimento; as pessoas são agrupadas por CPF (ou nome, sem CPF).
    visitas = Counter()
    idade_da_pessoa = {}   # chave -> (data do atendimento, faixa) do atendimento mais recente
    bairro_da_pessoa = {}  # chave -> (data do atendimento, chave do bairro)
    grafias_bairro = {}    # chave do bairro -> Counter das grafias originais
    campos = ('cpf', 'nome', 'data_nasc', 'bairro', 'data_atendimento')
    for cpf, nome, nascimento, bairro, dia in registros.values_list(*campos):
        pessoa = chave_pessoa(cpf, nome)
        if not pessoa:
            continue
        visitas[pessoa] += 1
        dia_valido = dia if dia and inicio and inicio <= dia.replace(day=1) <= fim else None

        if nascimento and dia_valido:
            faixa = faixa_etaria(idade_em(nascimento, dia_valido))
            if faixa and dia_valido >= idade_da_pessoa.get(pessoa, (date.min,))[0]:
                idade_da_pessoa[pessoa] = (dia_valido, faixa)

        chave = chave_bairro(bairro)
        if chave:
            grafias_bairro.setdefault(chave, Counter())[bairro.strip()] += 1
            ordem = dia_valido or date.min
            if ordem >= bairro_da_pessoa.get(pessoa, (date.min,))[0]:
                bairro_da_pessoa[pessoa] = (ordem, chave)

    total_pessoas = len(visitas)

    faixas = Counter(faixa for _, faixa in idade_da_pessoa.values())
    rotulos_faixa = [rotulo for _, _, rotulo in FAIXAS_ETARIAS]
    sem_idade = total_pessoas - len(idade_da_pessoa)
    grafico_idade = grafico(
        'idade', 'Pessoas atendidas por faixa etária', 'colunas',
        rotulos_faixa, [serie('Pessoas', [faixas[r] for r in rotulos_faixa])],
        subtitulo=f'{milhar(sem_idade)} sem data de nascimento válida' if sem_idade else '',
        eixo='Faixa etária', dicas=[f'{r} anos' for r in rotulos_faixa],
        unidade=('pessoa', 'pessoas'),
    )

    def nome_bairro(chave):
        # Prefere a grafia com acento ("São Jorge" e não "Sao Jorge"); depois a mais usada.
        grafias = grafias_bairro[chave]
        escolhida = max(grafias, key=lambda g: (not g.isascii(), grafias[g]))
        return titulo_ptbr(expandir_abreviacoes(re.sub(r'\s+', ' ', escolhida).upper()))

    bairros = Counter(chave for _, chave in bairro_da_pessoa.values())
    top_bairros = ranking(bairros)[:TOP_BAIRROS]
    sem_bairro = total_pessoas - len(bairro_da_pessoa)
    grafico_bairros = grafico(
        'bairros', f'Os {TOP_BAIRROS} bairros com mais pessoas atendidas', 'barras',
        [nome_bairro(chave) for chave, _ in top_bairros],
        [serie('Pessoas', [n for _, n in top_bairros])],
        subtitulo=f'{milhar(sem_bairro)} pessoas sem bairro informado' if sem_bairro else '',
        eixo='Bairro', unidade=('pessoa', 'pessoas'),
    )

    vezes = Counter(min(n, len(VEZES)) for n in visitas.values())
    grafico_vezes = grafico(
        'retorno', 'Quantas vezes cada pessoa foi atendida', 'colunas',
        VEZES, [serie('Pessoas', [vezes[i] for i in range(1, len(VEZES) + 1)])],
        eixo='Atendimentos', unidade=('pessoa', 'pessoas'),
    )

    voltaram = total_pessoas - vezes[1]
    return {
        'titulo': 'Histórico administrativo',
        'icone': 'history',
        'sub': f'{rotulo_mes(inicio)} a {rotulo_mes(fim)}' if inicio else '',
        'resumo': [
            numero('Atendimentos', milhar(sum(valores_mes))),
            numero('Pessoas atendidas', milhar(total_pessoas)),
            numero('Média por mês', milhar(round(sum(valores_mes) / len(meses))) if meses else '—'),
            numero('Voltaram mais de uma vez', milhar(voltaram), porcentagem(voltaram, total_pessoas)),
        ],
        'graficos': [grafico_meses, grafico_motivos, grafico_bairros, grafico_idade, grafico_vezes],
    }


CACHE_HISTORICO_SEGUNDOS = 600


def secao_historico_em_cache():
    """O histórico é só leitura e leva ~150 ms para agregar; a chave muda se entrar ou sair registro."""
    resumo = RegistroAdministrativo.objects.aggregate(n=Count('id'), ultimo=Max('id'))
    chave = f'painel-historico:{resumo["n"]}:{resumo["ultimo"]}'
    return cache.get_or_set(chave, secao_historico, CACHE_HISTORICO_SEGUNDOS)


def secoes_do_painel(hoje):
    return [secao_recente(hoje), secao_historico_em_cache()]
