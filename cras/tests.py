import json
import re
from datetime import date, time, timedelta
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administrativo.models import RegistroAdministrativo
from atendimentos.models import RegistroAtendimento
from triagem.models import Atendimento
from usuarios.models import Usuario

from . import graficos

S = Atendimento.Status


def por_chave(secao):
    return {g['chave']: g for g in secao['graficos']}


def valores(grafico):
    return dict(zip(grafico['categorias'], grafico['series'][0]['valores']))


def resumo(secao):
    return {n['rotulo']: (n['valor'], n['detalhe']) for n in secao['resumo']}


class UtilidadesTests(TestCase):
    def test_chave_pessoa_usa_cpf_e_recupera_zero_a_esquerda(self):
        self.assertEqual(graficos.chave_pessoa('012.345.678-90', 'Ana'), 'cpf:01234567890')
        self.assertEqual(graficos.chave_pessoa('1234567890', 'Ana'), 'cpf:01234567890')

    def test_chave_pessoa_sem_cpf_valido_cai_para_o_nome(self):
        self.assertEqual(graficos.chave_pessoa('', 'José  da Silva'), 'nome:JOSE DA SILVA')
        self.assertEqual(graficos.chave_pessoa('000.000.000-00', 'Ana'), 'nome:ANA')
        self.assertIsNone(graficos.chave_pessoa('', ''))

    def test_periodo_valido_descarta_datas_erradas_nas_pontas(self):
        por_mes = {date(1930, 1, 1): 2, date(2019, 2, 1): 59, date(2020, 1, 1): 2,
                   date(2024, 9, 1): 184, date(2032, 8, 1): 2}
        self.assertEqual(graficos.periodo_valido(por_mes), (date(2019, 2, 1), date(2024, 9, 1)))

    def test_faixa_etaria(self):
        self.assertEqual(graficos.faixa_etaria(17), '0 a 17')
        self.assertEqual(graficos.faixa_etaria(60), '60 a 79')
        self.assertEqual(graficos.faixa_etaria(80), '80+')
        self.assertIsNone(graficos.faixa_etaria(-1))
        self.assertIsNone(graficos.faixa_etaria(graficos.IDADE_MAXIMA + 1))


class SecaoRecenteTests(TestCase):
    def setUp(self):
        self.hoje = timezone.localdate()

    def test_atendimentos_por_dia_separados_por_desfecho(self):
        ontem = self.hoje - timedelta(days=1)
        Atendimento.objects.create(nome='A', data=ontem, status=S.ATENDIDO, hora_entrada=time(9, 10))
        Atendimento.objects.create(nome='B', data=ontem, status=S.ATENDIDO_TRIAGEM, hora_entrada=time(9, 40))
        Atendimento.objects.create(nome='D', data=ontem, status=S.AGUARDANDO, hora_entrada=time(9, 50))
        Atendimento.objects.create(nome='C', data=self.hoje, status=S.AGUARDANDO_60, hora_entrada=time(14, 5))
        Atendimento.objects.create(nome='Antigo', data=self.hoje - timedelta(days=40), status=S.ATENDIDO)

        secao = graficos.secao_recente(self.hoje)
        g = por_chave(secao)
        dias = g['por_dia']
        self.assertEqual(len(dias['categorias']), graficos.DIAS_RECENTES)
        series = {s['nome']: s['valores'] for s in dias['series']}
        self.assertEqual(series['Atendidos'][-2:], [1, 0])
        self.assertEqual(series['Resolvidos na triagem'][-2:], [1, 0])
        # Na fila ontem = foi embora sem atendimento; na fila hoje = ainda aguardando.
        self.assertEqual(series['Sem atendimento'][-2:], [1, 0])
        self.assertEqual(series['Aguardando'][-2:], [0, 1])

        horas = valores(g['horario'])
        self.assertEqual((horas['9h'], horas['14h']), (3, 1))

        self.assertEqual(resumo(secao), {
            'Triagens': ('4', ''), 'Atendidas': ('2', '50%'),
            'Sem atendimento': ('1', '25%'), 'Horário de pico': ('9h', ''),
        })

    def test_serie_aguardando_so_aparece_com_gente_na_fila_hoje(self):
        Atendimento.objects.create(nome='A', data=self.hoje, status=S.ATENDIDO, hora_entrada=time(9, 10))
        dias = por_chave(graficos.secao_recente(self.hoje))['por_dia']
        self.assertNotIn('Aguardando', [s['nome'] for s in dias['series']])

    def test_tipos_em_ranking_com_todos_os_tipos(self):
        for _ in range(2):
            RegistroAtendimento.objects.create(nome='X', tipo_atendimento=RegistroAtendimento.Tipo.PSICOSSOCIAL)
        RegistroAtendimento.objects.create(nome='Y', tipo_atendimento=RegistroAtendimento.Tipo.ORIENTACAO)

        tipos = por_chave(graficos.secao_recente(self.hoje))['tipos']
        self.assertEqual(tipos['categorias'][:2], ['Psicossocial', 'Orientação'])
        self.assertEqual(valores(tipos), {'Psicossocial': 2, 'Orientação': 1, 'Administrativo': 0, 'Outro': 0})

    def test_sem_movimento_marca_os_graficos_como_vazios(self):
        g = por_chave(graficos.secao_recente(self.hoje))
        self.assertTrue(all(item['vazio'] for item in g.values()))


@mock.patch.object(graficos, 'MINIMO_MES_NA_PONTA', 1)
class SecaoHistoricoTests(TestCase):
    def criar(self, **campos):
        padrao = {'nome': 'Fulano', 'data_atendimento': date(2023, 3, 10)}
        return RegistroAdministrativo.objects.create(**{**padrao, **campos})

    def test_meses_preenchem_lacunas_com_zero(self):
        self.criar(data_atendimento=date(2023, 1, 5))
        self.criar(data_atendimento=date(2023, 3, 9))
        meses = por_chave(graficos.secao_historico())['por_mes']
        self.assertEqual(valores(meses), {'jan/2023': 1, 'fev/2023': 0, 'mar/2023': 1})

    def test_motivos_agrupam_grafias_e_contam_os_sem_motivo(self):
        self.criar(motivo='PSICOSOCIAL')
        self.criar(motivo='PSICOSSOCIAL')
        self.criar(motivo='ATUALIZAÇÃO CADASTRAL - CADÚNICO')
        self.criar(motivo='')
        motivos = por_chave(graficos.secao_historico())['motivos']
        self.assertEqual(valores(motivos), {'Psicossocial': 2, 'Atualização cadastral (CadÚnico)': 1})
        self.assertEqual(motivos['subtitulo'], '1 sem motivo informado')

    def test_pessoas_contadas_uma_vez_por_cpf(self):
        for dia in (date(2023, 1, 5), date(2023, 2, 5), date(2023, 3, 5)):
            self.criar(nome='Ana', cpf='111.222.333-44', data_nasc=date(1990, 6, 1), bairro='SAO JORGE',
                       data_atendimento=dia)
        self.criar(nome='Bia', cpf='555.666.777-88', data_nasc=date(1940, 1, 1), bairro='SÃO JORGE')
        self.criar(nome='Caio', cpf='', data_nasc=date(9999, 12, 31), bairro='STA LUZIA')

        secao = graficos.secao_historico()
        g = por_chave(secao)
        self.assertEqual(valores(g['retorno'])['1 vez'], 2)
        self.assertEqual(valores(g['retorno'])['3 vezes'], 1)
        self.assertEqual(resumo(secao)['Pessoas atendidas'], ('3', ''))
        self.assertEqual(resumo(secao)['Voltaram mais de uma vez'], ('1', '33%'))
        self.assertEqual(g['por_mes']['subtitulo'], 'Pico de 3 em mar/2023')

        idades = valores(g['idade'])
        self.assertEqual((idades['30 a 39'], idades['80+']), (1, 1))
        self.assertEqual(g['idade']['subtitulo'], '1 sem data de nascimento válida')

        self.assertEqual(valores(g['bairros']), {'São Jorge': 2, 'Santa Luzia': 1})


class PainelGraficosTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client.force_login(Usuario.objects.create_user(username='tec', password='x'))

    def test_painel_entrega_os_dados_dos_graficos_e_o_echarts(self):
        Atendimento.objects.create(nome='Ana', status=S.ATENDIDO)
        resp = self.client.get(reverse('inicio'))
        # ?v=<data de modificação>: depois de editar CSS/JS o navegador não usa a versão velha do cache.
        self.assertRegex(resp.content.decode(), r'cras/css/tema\.css\?v=\d+')
        self.assertRegex(resp.content.decode(), r'cras/js/painel-graficos\.js\?v=\d+')
        self.assertContains(resp, 'data-grafico="por_dia"')
        self.assertContains(resp, 'Horário de pico')
        bloco = re.search(r'<script id="dados-graficos" type="application/json">(.*?)</script>',
                          resp.content.decode(), re.S)
        dados = json.loads(bloco.group(1))
        self.assertIn('por_dia', dados)
        self.assertNotIn('titulo', dados['por_dia'])  # o JS recebe só o que desenha

    def test_grafico_sem_dados_mostra_aviso_em_vez_do_canvas(self):
        resp = self.client.get(reverse('inicio'))
        self.assertContains(resp, 'Sem registros no período.')
        self.assertNotContains(resp, 'data-grafico="por_dia"')
        self.assertEqual(resp.context['dados_graficos'], {})
