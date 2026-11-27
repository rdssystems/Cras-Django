import json
import re
from datetime import time, timedelta

from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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


class PainelGraficosTests(TestCase):
    def setUp(self):
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

    def test_historico_administrativo_nao_existe_mais(self):
        self.client.force_login(Usuario.objects.create_superuser(username='chefe', password='x'))
        resp = self.client.get(reverse('inicio'))
        self.assertEqual([s['titulo'] for s in resp.context['secoes_graficos']], ['Últimos 30 dias'])
        self.assertNotContains(resp, 'Histórico')
        self.assertContains(resp, reverse('usuarios:lista'))  # o menu do administrador continua
        self.assertEqual(self.client.get('/administrativo/').status_code, 404)
        self.assertNotIn('administrativo_registroadministrativo', connection.introspection.table_names())
