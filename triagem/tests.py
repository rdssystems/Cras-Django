import tempfile
from datetime import date, datetime, time
from importlib import import_module
from io import StringIO
from pathlib import Path
from unittest import mock

import openpyxl
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from atendimentos.models import RegistroAtendimento
from certidoes.models import Certidao
from dsf.models import Dsf
from tap.models import TapDiario
from usuarios.models import Usuario

from .models import Atendimento, listas_de_chamada, pode_atender

S = Atendimento.Status


def criar_usuario(username, cargo=Usuario.Cargo.TECNICO_ADMINISTRATIVO, **extra):
    return Usuario.objects.create_user(username=username, password='x', cargo=cargo, **extra)


def momento(dia, hora):
    return timezone.make_aware(datetime.combine(dia, hora))


class OrdemDaFilaTests(TestCase):
    """A1 e A2: fila em ordem de chegada e espera máxima de verdade."""

    def setUp(self):
        self.hoje = timezone.localdate()
        self.client.force_login(criar_usuario('tec'))

    def test_fila_em_ordem_de_chegada_com_espera_maxima_real(self):
        for nome, hora in (('Primeira', time(8, 0)), ('Segunda', time(8, 20)), ('Terceira', time(8, 45))):
            Atendimento.objects.create(nome=nome, hora_entrada=hora)
        with mock.patch('django.utils.timezone.localtime', return_value=momento(self.hoje, time(9, 0))):
            administrativo = listas_de_chamada(self.hoje)[0]
        self.assertEqual([i.nome for i in administrativo['itens']], ['Primeira', 'Segunda', 'Terceira'])
        self.assertEqual((administrativo['count'], administrativo['espera_max']), (3, 60))

    def test_sao_duas_filas_administrativa_e_psicossocial(self):
        Atendimento.objects.create(nome='Geral')
        Atendimento.objects.create(nome='Idoso', status=S.AGUARDANDO_60)
        Atendimento.objects.create(nome='Psico', status=S.AGUARDANDO_PSICO_80)
        Atendimento.objects.create(nome='Atendida', status=S.ATENDIDO)
        filas = listas_de_chamada(self.hoje)
        self.assertEqual([f['titulo'] for f in filas], ['Atendimento administrativo', 'Atendimento psicossocial'])
        self.assertEqual([[i.nome for i in f['itens']] for f in filas], [['Idoso', 'Geral'], ['Psico']])

        resp = self.client.get(reverse('inicio'))
        self.assertEqual([f['chave'] for f in resp.context['filas']], ['administrativo', 'psicossocial'])
        self.assertContains(resp, 'Atendimento psicossocial')

    def test_painel_mostra_os_proximos_5_da_fila(self):
        for n in range(7):
            Atendimento.objects.create(nome=f'P{n}')
        resp = self.client.get(reverse('inicio'))
        fila = resp.context['filas'][0]
        self.assertEqual(fila['count'], 7)
        self.assertEqual(resp.context['total_aguardando'], 7)
        self.assertEqual([i.numero for i in fila['itens']], [1, 2, 3, 4, 5])


class OrdemDeChamadaTests(TestCase):
    """Tela Filas: duas listas em linhas, 80+ -> demais prioritários -> geral, empate por chegada."""

    def setUp(self):
        self.hoje = timezone.localdate()
        chegadas = [
            ('Ana', S.AGUARDANDO),
            ('Bia', S.AGUARDANDO_60),
            ('Caio', S.AGUARDANDO_80),
            ('Duda', S.AGUARDANDO_PCD),
            ('Edu', S.REUNIAO),
            ('Fabio', S.AGUARDANDO_PSICO),
            ('Gil', S.AGUARDANDO_PSICO_80),
            ('Hugo', S.LIBRAS),
            ('Iris', S.AGUARDANDO_PSICO_GESTANTE),
            ('Juca', S.ATENDIDO),  # já atendido: não aparece
        ]
        for nome, status in chegadas:
            Atendimento.objects.create(nome=nome, status=status)

    def nomes(self, listas):
        return {l['chave']: [i.nome for i in l['itens']] for l in listas}

    def test_ordem_de_chamada_separada_por_equipe(self):
        self.assertEqual(self.nomes(listas_de_chamada(self.hoje)), {
            'administrativo': ['Caio', 'Bia', 'Duda', 'Hugo', 'Ana', 'Edu'],
            'psicossocial': ['Gil', 'Iris', 'Fabio'],
        })

    def test_etiquetas(self):
        por_nome = {i.nome: i for l in listas_de_chamada(self.hoje) for i in l['itens']}
        self.assertEqual(por_nome['Caio'].etiqueta, '80+')
        self.assertEqual(por_nome['Iris'].etiqueta, 'Gestante / colo')
        self.assertIsNone(por_nome['Ana'].etiqueta)
        self.assertIsNone(por_nome['Fabio'].etiqueta)
        self.assertEqual(por_nome['Edu'].etiqueta, 'Reunião')
        self.assertFalse(por_nome['Edu'].prioritario)
        self.assertTrue(por_nome['Hugo'].prioritario)

    def test_tela_para_tecnico_bloqueia_so_o_psicossocial(self):
        self.client.force_login(criar_usuario('tec'))
        resp = self.client.get(reverse('triagem:filas'))
        listas = {l['chave']: l for l in resp.context['listas']}
        self.assertEqual([i.nome for i in listas['administrativo']['itens']][:2], ['Caio', 'Bia'])
        self.assertFalse(listas['administrativo']['sem_permissao'])
        self.assertTrue(listas['psicossocial']['sem_permissao'])
        caio = Atendimento.objects.get(nome='Caio')
        gil = Atendimento.objects.get(nome='Gil')
        self.assertContains(resp, f'id="modal-atender-{caio.pk}"')
        self.assertNotContains(resp, f'id="modal-atender-{gil.pk}"')

    def test_tela_para_psicologo_libera_as_duas_listas(self):
        self.client.force_login(criar_usuario('psi', cargo=Usuario.Cargo.PSICOLOGO))
        resp = self.client.get(reverse('triagem:filas'))
        self.assertFalse(any(l['sem_permissao'] for l in resp.context['listas']))

    def test_lista_vazia(self):
        Atendimento.objects.filter(status__in=[S.AGUARDANDO_PSICO, S.AGUARDANDO_PSICO_80,
                                                S.AGUARDANDO_PSICO_GESTANTE]).delete()
        self.client.force_login(criar_usuario('tec'))
        resp = self.client.get(reverse('triagem:filas'))
        self.assertContains(resp, 'Ninguém aguardando.')


class AtenderTests(TestCase):
    """A3: ninguém é atendido duas vezes."""

    def setUp(self):
        self.tec = criar_usuario('tec')
        self.psi = criar_usuario('psi', cargo=Usuario.Cargo.PSICOLOGO)
        self.pessoa = Atendimento.objects.create(nome='Maria')
        self.url = reverse('triagem:atender', args=[self.pessoa.pk])
        self.dados = {'tipo_atendimento': 'ORIENTAÇÃO', 'motivo': 'DMAE', 'observacoes': 'ok'}

    def test_atender_marca_atendido_e_cria_um_registro(self):
        self.client.force_login(self.tec)
        self.client.post(self.url, self.dados)
        self.pessoa.refresh_from_db()
        self.assertEqual(self.pessoa.status, S.ATENDIDO)
        self.assertEqual(self.pessoa.servidor1, self.tec)
        self.assertIsNotNone(self.pessoa.hora_atendimento)
        registro = RegistroAtendimento.objects.get()
        self.assertEqual(registro.atendimento_origem, self.pessoa)
        self.assertEqual(registro.responsavel, self.tec)
        self.assertEqual(registro.tipo_atendimento, 'ORIENTAÇÃO')
        self.assertEqual(registro.hora_atendimento, self.pessoa.hora_atendimento)

    def test_segundo_post_nao_duplica_nem_troca_o_servidor(self):
        self.client.force_login(self.tec)
        self.client.post(self.url, self.dados)
        self.client.force_login(self.psi)
        resp = self.client.post(self.url, self.dados, follow=True)
        self.assertEqual(RegistroAtendimento.objects.count(), 1)
        self.pessoa.refresh_from_db()
        self.assertEqual(self.pessoa.servidor1, self.tec)
        self.assertContains(resp, 'já foi atendido(a) por tec')

    def test_corrida_entre_dois_servidores_gera_um_registro_so(self):
        # O 2º servidor leu a pessoa ainda AGUARDANDO, mas o 1º gravou antes dele.
        obsoleto = Atendimento.objects.get(pk=self.pessoa.pk)
        Atendimento.objects.filter(pk=self.pessoa.pk).update(status=S.ATENDIDO, servidor1=self.psi)
        self.client.force_login(self.tec)
        with mock.patch('triagem.views.get_object_or_404', return_value=obsoleto):
            resp = self.client.post(self.url, self.dados, follow=True)
        self.assertFalse(RegistroAtendimento.objects.exists())
        self.pessoa.refresh_from_db()
        self.assertEqual(self.pessoa.servidor1, self.psi)
        self.assertContains(resp, 'acabou de ser atendido(a) por outro servidor')

    def test_tecnico_nao_atende_fila_psicossocial(self):
        psico = Atendimento.objects.create(nome='João', status=S.AGUARDANDO_PSICO)
        self.client.force_login(self.tec)
        self.client.post(reverse('triagem:atender', args=[psico.pk]), self.dados)
        psico.refresh_from_db()
        self.assertEqual(psico.status, S.AGUARDANDO_PSICO)
        self.assertFalse(RegistroAtendimento.objects.exists())

    def test_tipo_de_atendimento_invalido_vira_administrativo(self):
        self.client.force_login(self.tec)
        self.client.post(self.url, {**self.dados, 'tipo_atendimento': 'QUALQUER COISA'})
        self.assertEqual(RegistroAtendimento.objects.get().tipo_atendimento, 'ATENDIMENTO ADMINISTRATIVO')

    def test_pode_atender_recusa_quem_nao_esta_em_fila(self):
        root = criar_usuario('root', cargo=None, is_superuser=True)
        self.assertFalse(pode_atender(root, S.ATENDIDO))
        self.assertFalse(pode_atender(self.psi, S.ATENDIDO_TRIAGEM))
        self.assertTrue(pode_atender(root, S.AGUARDANDO_PSICO))
        self.assertTrue(pode_atender(self.tec, S.AGUARDANDO_60))


class NumeracaoTests(TestCase):
    """A5: número da senha sequencial e único por dia."""

    def setUp(self):
        self.dia = date(2026, 1, 5)

    def test_numero_sequencial_por_dia(self):
        a = Atendimento.objects.create(nome='A', data=self.dia)
        b = Atendimento.objects.create(nome='B', data=self.dia)
        c = Atendimento.objects.create(nome='C', data=date(2026, 1, 6))
        self.assertEqual((a.numero, b.numero, c.numero), (1, 2, 1))

    def test_banco_recusa_numero_repetido_no_mesmo_dia(self):
        Atendimento.objects.create(nome='A', data=self.dia, numero=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Atendimento.objects.create(nome='B', data=self.dia, numero=1)

    def test_colisao_de_numero_tenta_o_proximo(self):
        Atendimento.objects.create(nome='A', data=self.dia)
        novo = Atendimento(nome='B', data=self.dia)
        # Simula a corrida: o cálculo devolve um número que outra triagem acabou de usar.
        with mock.patch.object(Atendimento, '_proximo_numero', side_effect=[1, 2]):
            novo.save()
        self.assertEqual(novo.numero, 2)
        self.assertEqual(Atendimento.objects.filter(data=self.dia).count(), 2)


class HoraEntradaTests(TestCase):
    """A4: hora de entrada informada não é mais sobrescrita."""

    def test_hora_informada_e_preservada(self):
        a = Atendimento.objects.create(nome='A', hora_entrada=time(7, 45))
        a.refresh_from_db()
        self.assertEqual(a.hora_entrada, time(7, 45))

    def test_sem_hora_informada_usa_a_hora_atual(self):
        agora = momento(timezone.localdate(), time(10, 30))
        with mock.patch('django.utils.timezone.localtime', return_value=agora):
            a = Atendimento.objects.create(nome='A')
        self.assertEqual(a.hora_entrada, time(10, 30))


class ImportarPlanilhaTests(TestCase):
    """A4/A6 na importação + trava contra reimportação."""

    def setUp(self):
        pasta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(pasta.cleanup)
        self.caminho = str(Path(pasta.name) / 'planilha.xlsx')
        self._montar_planilha(self.caminho)

    @staticmethod
    def _montar_planilha(caminho):
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        adm = wb.create_sheet('1S2024 ATENDIMENTO ADMINISTRATI')
        adm.append(['NOME', 'DATA NASC.', 'CPF', 'BAIRRO', 'TELEFONE', 'DATA ATENDIMENTO', 'MOTIVO'])
        adm.append(['ANA', datetime(1970, 1, 1), '111', 'CENTRO', '9999', datetime(2024, 3, 1), 'DMAE'])

        ctl = wb.create_sheet('CONTROLE DE ATENDIMENTOS DIÁRIO')
        ctl.append(['CONTROLE DE ATENDIMENTOS DIÁRIO'])
        ctl.append(['NÚMERO', 'DATA', 'NOME', 'CPF', 'HORA ENTRADA', 'HORA ATENDIMENTO', 'STATUS DO ATENDIMENTO'])
        ctl.append([1, datetime(2025, 3, 10), 'BRUNO', '222', time(8, 15), time(9, 0), 'ATENDIDO'])
        ctl.append([2, None, 'SEM DATA', '333', time(8, 30), None, None])
        ctl.append([3, datetime(2025, 3, 10), None, None, None, None, None])

        reg = wb.create_sheet('REGISTRO DE ATENDIMENTOS')
        reg.append(['DATA', 'NOME', 'CPF', 'HORA ENTRADA', 'HORA ATENDIMENTO', 'TIPO'])
        reg.append([datetime(2025, 3, 10), 'BRUNO', '222', time(8, 15), time(9, 0), 'ORIENTAÇÃO',
                    'DMAE', None, None, None, 'PATRICIA', ''])
        reg.append([datetime(2025, 3, 10), None, None, None, None, 'ATENDIMENTO PSICOSSOCIAL',
                    'ORIENTÇÕES BPC', None, None, None, 'PATRICIA', ''])

        tap = wb.create_sheet('2026 TAP MENSAL')
        tap.append([datetime(2026, 1, 1)])
        tap.append(['DIA', 'TAP DIÁRIO'])
        tap.append([1, 12])

        wb.save(caminho)

    def importar(self, **opcoes):
        call_command('importar_planilha', arquivo=self.caminho, stdout=StringIO(), **opcoes)

    def test_importa_sem_jogar_ninguem_na_fila_de_hoje_e_preserva_horas(self):
        self.importar()
        self.assertFalse(Atendimento.objects.filter(data=timezone.localdate()).exists())
        bruno = Atendimento.objects.get()
        self.assertEqual(bruno.nome, 'BRUNO')
        self.assertEqual(bruno.data, date(2025, 3, 10))
        self.assertEqual(bruno.hora_entrada, time(8, 15))
        self.assertEqual(bruno.hora_atendimento, time(9, 0))

        registro = RegistroAtendimento.objects.get()  # a linha sem nome foi ignorada
        self.assertEqual(registro.nome, 'BRUNO')
        self.assertEqual(registro.hora_entrada, time(8, 15))

        self.assertEqual(TapDiario.objects.get(data=date(2026, 1, 1)).tap_diario, 12)

    def test_aba_do_historico_administrativo_nao_e_importada(self):
        saida = StringIO()
        call_command('importar_planilha', arquivo=self.caminho, stdout=saida)
        self.assertNotIn('1S2024', saida.getvalue())
        for modelo in (Atendimento, RegistroAtendimento):
            self.assertFalse(modelo.objects.filter(nome='ANA').exists())  # só existe naquela aba

    def test_reimportar_sem_forcar_e_bloqueado(self):
        self.importar()
        with self.assertRaisesMessage(CommandError, 'pode DUPLICAR'):
            self.importar()
        self.assertEqual(Atendimento.objects.count(), 1)

        self.importar(forcar=True)
        self.assertEqual(Atendimento.objects.count(), 2)

    def test_banco_em_uso_nao_recebe_a_planilha_sem_forcar(self):
        Certidao.objects.create(data_solicitacao=date(2026, 11, 5), quem_solicitou='Bia', de_quem='Ana')
        with self.assertRaisesMessage(CommandError, 'já tem 1 registros'):
            self.importar()
        self.assertFalse(Atendimento.objects.exists())

    def _planilha_completa(self):
        """Planilha como a atual do CRAS Morumbi: motivos em várias colunas, Certidões e DSF."""
        wb = openpyxl.load_workbook(self.caminho)
        reg = wb['REGISTRO DE ATENDIMENTOS']
        reg.append([datetime(2026, 11, 20), 'CARLA', '444', time(10, 0), None, 'ATENDIMENTO ADMINISTRATIVO',
                    'ATUALIZAÇÃO DE CADASTRO', 'CARTEIRINHA DO IDOSO', None, None, 'NICOLLI', ''])

        cert = wb.create_sheet('CERTIDÕES')
        cert.append(['DATA SOLICITAÇÃO', 'QUEM SOLICITOU', 'DE QUEM', 'TELEFONE', 'SERVIDOR', 'CIDADE',
                     'DATA RECEBIMENTO', 'NOME DO CONTATO', 'CONTATO EM:', 'DATA ENTREGA', 'ENTREGUE PARA:'])
        cert.append([None] * 11)  # a planilha real tem a linha 2 em branco
        cert.append([datetime(2026, 1, 5), 'DORA', 'DO MESMO', 34999990000.0, 'GUSTAVO', 'UBERLANDIA-MG',
                     '12/02/2026', datetime(2026, 2, 13), 'TELEFONE', 'ENTREGUE PARA A MÃE EM 20/02/2026', None])
        cert.append(['05/01//2026', 'EDU', 'FILHO', None, 'NICOLLI', 'ARAGUARI', None, None, None, None, None])
        cert.append(['SEM DATA', 'FABI', 'DELA', None, None, None, None, None, None, None, None])

        dsf = wb.create_sheet('DSF CONCLUÍDO')
        dsf.append(['DSF CONCLUÍDO'])
        dsf.append(['NOME', 'BENEFÍCIO SOLICITADO', 'DATA', 'DEFERIDO/ INDEFERIDO', 'TÉCNICO RESPONSÁVEL'])
        dsf.append(['GABI', 'CESTA BÁSICA - DSF', datetime(2026, 11, 3), 'DEFERIDO', 'PATRICIA'])
        dsf.append(['HELO', 'CESTA BÁSICA - DSF', datetime(2026, 11, 4), None, 'ALESSANDRA'])
        wb.save(self.caminho)

    def test_motivos_das_varias_colunas_viram_lista(self):
        self._planilha_completa()
        self.importar()
        carla = RegistroAtendimento.objects.get(nome='CARLA')
        self.assertEqual(carla.motivos, ['ATUALIZAÇÃO DE CADASTRO', 'CARTEIRINHA DO IDOSO'])
        self.assertEqual(carla.responsavel_nome, 'NICOLLI')

    def test_certidoes_sem_perder_o_texto_das_colunas_de_data(self):
        self._planilha_completa()
        self.importar()
        self.assertEqual(Certidao.objects.count(), 2)  # a linha sem data de solicitação foi ignorada

        dora = Certidao.objects.get(quem_solicitou='DORA')
        self.assertEqual(dora.data_solicitacao, date(2026, 1, 5))
        self.assertEqual(dora.data_recebimento, date(2026, 2, 12))  # texto que é só uma data
        self.assertEqual(dora.data_entrega, date(2026, 2, 20))      # data achada dentro do texto
        self.assertIn('ENTREGUE PARA A MÃE EM 20/02/2026', dora.observacoes)
        self.assertNotIn('Data do recebimento', dora.observacoes)  # era só a data: nada a guardar
        self.assertEqual(dora.nome_contato, '13/02/2026')           # data digitada na coluna de nome
        self.assertEqual((dora.telefone, dora.servidor_nome), ('34999990000', 'GUSTAVO'))

        edu = Certidao.objects.get(quem_solicitou='EDU')
        self.assertEqual(edu.data_solicitacao, date(2026, 1, 5))   # "05/01//2026"
        self.assertIsNone(edu.data_entrega)                         # continua pendente

    def test_dsf_com_beneficio_padronizado_e_sem_inventar_resultado(self):
        self._planilha_completa()
        self.importar()
        gabi, helo = Dsf.objects.order_by('data')
        self.assertEqual((gabi.beneficio_solicitado, gabi.resultado, gabi.tecnico_nome),
                         (Dsf.Beneficio.CESTA_BASICA, 'DEFERIDO', 'PATRICIA'))
        self.assertEqual(helo.resultado, '')

    def test_falha_no_meio_nao_deixa_importacao_pela_metade(self):
        self._planilha_completa()
        with mock.patch.object(Dsf.objects, 'create', side_effect=RuntimeError('falhou')):
            with self.assertRaises(RuntimeError):
                self.importar()
        self.assertEqual(Atendimento.objects.count(), 0)
        self.assertEqual(Certidao.objects.count(), 0)


class DemoTriagensTests(TestCase):
    def demo(self, *args):
        call_command('demo_triagens', *args, stdout=StringIO())

    def test_cria_a_demonstracao_e_remove_sem_tocar_nos_dados_reais(self):
        servidor = criar_usuario('real')
        real = Atendimento.objects.create(nome='Pessoa real', servidor_triagem=servidor)
        RegistroAtendimento.objects.create(nome='Pessoa real', responsavel=servidor, atendimento_origem=real)

        self.demo()
        hoje = timezone.localdate()
        demo = Atendimento.objects.filter(servidor_triagem__username__startswith='demo_')
        self.assertGreater(demo.filter(data__lt=hoje).count(), 500)
        self.assertTrue(any(f["count"] for f in listas_de_chamada(hoje)), "hoje deveria ter gente na fila")
        # Os números de senha de hoje continuam depois da triagem real.
        self.assertFalse(demo.filter(data=hoje, numero=real.numero).exists())
        # Todo atendido tem o seu registro de atendimento ligado à triagem.
        atendidos = demo.filter(status=S.ATENDIDO)
        self.assertEqual(
            RegistroAtendimento.objects.filter(atendimento_origem__in=atendidos).count(), atendidos.count()
        )
        self.assertFalse(Usuario.objects.get(username='demo_helena').has_usable_password())

        self.demo()  # rodar de novo substitui, não duplica
        self.assertEqual(Usuario.objects.filter(username__startswith='demo_').count(), 7)

        self.demo('--remover')
        self.assertEqual(list(Atendimento.objects.all()), [real])
        self.assertEqual(RegistroAtendimento.objects.get().atendimento_origem, real)
        self.assertEqual(list(Usuario.objects.values_list('username', flat=True)), ['real'])


class TriagemFilaEPrioridadeTests(TestCase):
    """A triagem pergunta a fila e a prioridade; o status guardado é a combinação das duas."""

    def setUp(self):
        self.client.force_login(criar_usuario('tec'))
        self.url = reverse('triagem:registrar')

    def registrar(self, **dados):
        return self.client.post(self.url, {'nome': 'Ana', 'cpf': '', **dados}, follow=True)

    def test_fila_e_prioridade_viram_o_status_da_planilha(self):
        casos = [
            ('ADMINISTRATIVO', '', S.AGUARDANDO),
            ('PSICOSSOCIAL', '', S.AGUARDANDO_PSICO),
            ('ADMINISTRATIVO', '80+', S.AGUARDANDO_80),
            ('PSICOSSOCIAL', '60+', S.AGUARDANDO_PSICO_60),
            ('PSICOSSOCIAL', 'GESTANTE', S.AGUARDANDO_PSICO_GESTANTE),
            ('ADMINISTRATIVO', 'LIBRAS', S.LIBRAS),
            ('PSICOSSOCIAL', 'LIBRAS', S.LIBRAS_PSICO),
        ]
        for fila, prioridade, esperado in casos:
            with self.subTest(fila=fila, prioridade=prioridade):
                self.registrar(tipo_fila=fila, prioridade=prioridade)
                self.assertEqual(Atendimento.objects.latest('id').status, esperado)

    def test_mensagem_informa_a_senha_e_a_fila(self):
        resp = self.registrar(tipo_fila='PSICOSSOCIAL', prioridade='PCD')
        self.assertContains(resp, 'Senha Nº 1: Ana entrou na fila de atendimento psicossocial (PcD).')

    def test_rotulo_da_caixa_de_orientacao_na_triagem(self):
        self.client.force_login(Usuario.objects.create_user('recepcao', password='x'))
        resp = self.client.get(reverse('triagem:registrar'))
        self.assertContains(resp, 'Orientações Realizadas na triagem (não entra na fila)')
        self.assertNotContains(resp, 'Resolvido na própria triagem')

    def test_resolvido_na_triagem_nao_entra_em_fila(self):
        self.registrar(tipo_fila='ADMINISTRATIVO', prioridade='60+', resolvido_na_triagem='on')
        self.assertEqual(Atendimento.objects.get().status, S.ATENDIDO_TRIAGEM)

    def test_fila_e_obrigatoria_e_prioridade_invalida_e_recusada(self):
        self.registrar(prioridade='60+')
        self.registrar(tipo_fila='ADMINISTRATIVO', prioridade='VIP')
        self.assertFalse(Atendimento.objects.exists())


class MotivosDoAtendimentoTests(TestCase):
    def setUp(self):
        self.client.force_login(criar_usuario('tec'))
        self.pessoa = Atendimento.objects.create(nome='Maria')

    def test_atender_aceita_varios_motivos_na_ordem_da_lista(self):
        self.client.post(reverse('triagem:atender', args=[self.pessoa.pk]), {
            'tipo_atendimento': 'ATENDIMENTO ADMINISTRATIVO',
            'motivo': ['SOLICITAÇÃO DE CESTA BÁSICA', 'INVENTADO', 'ATUALIZAÇÃO CADASTRAL - CADÚNICO'],
        })
        registro = RegistroAtendimento.objects.get()
        self.assertEqual(registro.motivo, 'ATUALIZAÇÃO CADASTRAL - CADÚNICO; SOLICITAÇÃO DE CESTA BÁSICA')
        self.assertEqual(registro.motivos, ['ATUALIZAÇÃO CADASTRAL - CADÚNICO', 'SOLICITAÇÃO DE CESTA BÁSICA'])

    def test_lista_tem_os_motivos_novos_e_cesta_basica_renomeada(self):
        novos = ['ORIENTAÇÃO BPC', 'CARTEIRINHA DO IDOSO', 'ORIENTAÇÕES PASSE LIVRE',
                 'SOLICITAÇÃO DE CADASTRO EM DOMICÍLIO', 'PRÓ-PÃO', 'SOLICITAÇÃO DE CESTA BÁSICA']
        for motivo in novos:
            self.assertIn(motivo, RegistroAtendimento.MOTIVOS)
        self.assertNotIn('CESTA BÁSICA', RegistroAtendimento.MOTIVOS)
        self.assertEqual(RegistroAtendimento.MOTIVOS[-1], 'OUTRO')
        html = self.client.get(reverse('triagem:filas')).content.decode()
        self.assertIn('name="motivo" value="ORIENTAÇÕES PASSE LIVRE"', html)

    def test_migracao_renomeia_so_o_item_exato(self):
        migracao = import_module('atendimentos.migrations.0005_renomeia_motivo_cesta_basica')
        trocar = migracao.trocar_item
        self.assertEqual(trocar('DMAE; CESTA BÁSICA', migracao.ANTIGO, migracao.NOVO),
                         'DMAE; SOLICITAÇÃO DE CESTA BÁSICA')
        self.assertEqual(trocar('SOLICITAÇÃO DE CESTA BÁSICA', migracao.ANTIGO, migracao.NOVO),
                         'SOLICITAÇÃO DE CESTA BÁSICA')  # já estava com o nome novo: não duplica
        self.assertEqual(trocar('DMAE', migracao.ANTIGO, migracao.NOVO), 'DMAE')

    def test_modal_marca_o_tipo_conforme_a_fila(self):
        Atendimento.objects.create(nome='Psi', status=S.AGUARDANDO_PSICO)
        self.client.force_login(criar_usuario('psi', cargo=Usuario.Cargo.PSICOLOGO))
        html = self.client.get(reverse('triagem:filas')).content.decode()
        self.assertEqual(html.count('value="ATENDIMENTO ADMINISTRATIVO" selected'), 1)
        self.assertEqual(html.count('value="ATENDIMENTO PSICOSSOCIAL" selected'), 1)
        self.assertEqual(html.count('name="motivo" value="DMAE"'), 2)
