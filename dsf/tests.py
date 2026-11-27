from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario

from .forms import ReaisField
from .models import Dsf, MembroFamiliar

CPF_DE_TESTE = '52998224725'  # exemplo com dígitos verificadores válidos


def usuario(nome='tec', cargo='ASSISTENTE_SOCIAL', **extra):
    return Usuario.objects.create_user(nome, password='x', cargo=cargo, **extra)


def dados(membros=(), iniciais=0, **campos):
    """POST da ficha: campos do DSF mais as linhas da composição familiar."""
    post = {'data': '2026-11-26', 'beneficio_solicitado': 'CESTA BÁSICA', 'nome': 'Ana Exemplo'}
    post.update(campos)
    post.update({
        'membros-TOTAL_FORMS': str(len(membros)), 'membros-INITIAL_FORMS': str(iniciais),
        'membros-MIN_NUM_FORMS': '0', 'membros-MAX_NUM_FORMS': '1000',
    })
    for indice, membro in enumerate(membros):
        post.update({f'membros-{indice}-{chave}': valor for chave, valor in membro.items()})
    return post


class NovoDsfTests(TestCase):
    def setUp(self):
        self.tecnico = usuario()
        self.client.force_login(self.tecnico)

    def enviar(self, **kwargs):
        return self.client.post(reverse('dsf:criar'), dados(**kwargs))

    def test_formulario_traz_as_secoes_da_ficha_e_quatro_linhas_de_familia(self):
        resp = self.client.get(reverse('dsf:criar'))
        for secao in ('1. Solicitação', 'I. Identificação', 'II. Composição familiar', 'III. Condição socioeconômica',
                      '2. Abordagem domiciliar', 'IV. Condição de habitabilidade', 'VI. Condições de saúde',
                      'VII. Benefícios sociais'):
            self.assertContains(resp, secao)
        self.assertContains(resp, 'name="membros-TOTAL_FORMS" value="4"')
        self.assertNotContains(resp, 'name="resultado"')  # o parecer é a etapa de deferimento

    def test_beneficio_e_uma_das_tres_opcoes(self):
        html = self.client.get(reverse('dsf:criar')).content.decode()
        for opcao in ('Cesta Básica', 'Fralda', 'Absorvente'):
            self.assertIn(f'>{opcao}</option>', html)
        self.enviar(beneficio_solicitado='FRALDA')
        self.assertEqual(Dsf.objects.get().get_beneficio_solicitado_display(), 'Fralda')

    def test_beneficio_fora_da_lista_e_recusado(self):
        resp = self.enviar(beneficio_solicitado='BOLSA QUALQUER')
        self.assertFalse(Dsf.objects.exists())
        self.assertContains(resp, 'erro-campo')

    def test_ficha_completa_fica_pendente_com_a_familia(self):
        resp = self.enviar(
            cpf=CPF_DE_TESTE, data_nascimento='1990-05-10', estado_civil='CASADO', morou_outros_lugares='SIM',
            pensao_alimenticia='350,50', renda_familiar='R$ 1.412,00', moradia='ALUGADA', moradia_valor='600',
            tem_deficiencia='SIM', deficiencia_fisica='on', deficiencia_visual='on', gestante='NAO',
            dmae='SIM', dmae_detalhe='isento', abordagem1_data='2026-11-27', abordagem1_tecnico='Maria',
            resultado='DEFERIDO',  # ignorado: não se defere pela ficha
            membros=[{'nome': 'Ana Exemplo', 'parentesco': 'Titular', 'idade': '36', 'renda': '1.412,00'},
                     {'nome': 'Bia Exemplo', 'parentesco': 'Filha', 'idade': '8'},
                     {'nome': '', 'parentesco': ''}],  # linha em branco não grava
        )
        self.assertRedirects(resp, reverse('dsf:lista'))
        dsf = Dsf.objects.get()
        self.assertEqual(dsf.resultado, '')
        self.assertTrue(dsf.pendente)
        self.assertEqual(dsf.tecnico_responsavel, self.tecnico)
        self.assertEqual(dsf.pensao_alimenticia, Decimal('350.50'))
        self.assertEqual(dsf.renda_familiar, Decimal('1412.00'))
        self.assertTrue(dsf.deficiencia_fisica and dsf.deficiencia_visual)
        self.assertFalse(dsf.deficiencia_mental)
        self.assertEqual(list(dsf.membros.values_list('nome', flat=True)), ['Ana Exemplo', 'Bia Exemplo'])

        lista = self.client.get(reverse('dsf:lista'))
        self.assertContains(lista, 'PENDENTE')
        self.assertContains(lista, reverse('dsf:editar', args=[dsf.pk]))
        self.assertEqual(lista.context['pendentes'], 1)

    def test_nome_e_data_sao_obrigatorios(self):
        resp = self.enviar(nome='', data='')
        self.assertFalse(Dsf.objects.exists())
        self.assertEqual({'nome', 'data'}, set(resp.context['form'].errors))

    def test_cpf_invalido_e_recusado(self):
        resp = self.enviar(cpf='12345678900')
        self.assertFalse(Dsf.objects.exists())
        self.assertIn('cpf', resp.context['form'].errors)

    def test_pessoa_sem_nome_nao_deixa_salvar_nada(self):
        resp = self.enviar(membros=[{'nome': '', 'parentesco': 'Filho'}])
        self.assertFalse(Dsf.objects.exists())
        self.assertContains(resp, 'O DSF não foi salvo')

    def test_valor_em_reais_aceita_os_formatos_digitados(self):
        campo = ReaisField(max_digits=10, decimal_places=2)
        for digitado, esperado in (('1.412,50', '1412.50'), ('1412,5', '1412.5'), ('R$ 600', '600'),
                                   ('1.412', '1412'), ('600.00', '600.00')):
            self.assertEqual(campo.clean(digitado), Decimal(esperado), digitado)


class EditarDsfTests(TestCase):
    def setUp(self):
        self.autor = usuario('autor')
        self.client.force_login(usuario('visita'))
        self.dsf = Dsf.objects.create(
            nome='Ana Exemplo', data='2026-11-26', beneficio_solicitado='CESTA BÁSICA', ficha_preenchida=True,
            renda_familiar=Decimal('1412.00'), tecnico_responsavel=self.autor,
        )
        self.bia = MembroFamiliar.objects.create(dsf=self.dsf, nome='Bia Exemplo')
        self.url = reverse('dsf:editar', args=[self.dsf.pk])

    def test_abre_com_os_dados_gravados(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, 'value="2026-11-26"')
        self.assertContains(resp, 'value="1412,00"')
        self.assertContains(resp, 'value="Bia Exemplo"')

    def test_completa_a_visita_e_remove_pessoa_sem_trocar_o_autor(self):
        resp = self.client.post(self.url, dados(
            iniciais=1, tipo_construcao='ALVENARIA',
            membros=[{'id': str(self.bia.pk), 'dsf': str(self.dsf.pk), 'nome': 'Bia Exemplo', 'DELETE': 'on'},
                     {'nome': 'Caio Exemplo'}],
        ))
        self.assertRedirects(resp, reverse('dsf:lista'))
        self.dsf.refresh_from_db()
        self.assertEqual(self.dsf.tipo_construcao, 'ALVENARIA')
        self.assertEqual(self.dsf.tecnico_responsavel, self.autor)
        self.assertTrue(self.dsf.pendente)
        self.assertEqual(list(self.dsf.membros.values_list('nome', flat=True)), ['Caio Exemplo'])

    def test_deferido_nao_pode_ser_editado(self):
        Dsf.objects.filter(pk=self.dsf.pk).update(resultado=Dsf.Resultado.DEFERIDO)
        self.client.post(self.url, dados(nome='Outro Nome'))
        self.dsf.refresh_from_db()
        self.assertEqual(self.dsf.nome, 'Ana Exemplo')
        self.assertNotContains(self.client.get(reverse('dsf:lista')), self.url)

    def test_registro_da_planilha_sem_resultado_nao_vira_pendente(self):
        Dsf.objects.filter(pk=self.dsf.pk).update(ficha_preenchida=False)
        lista = self.client.get(reverse('dsf:lista'))
        self.assertEqual(lista.context['pendentes'], 0)
        self.assertNotContains(lista, 'PENDENTE<')
        self.assertNotContains(lista, self.url)
        self.assertRedirects(self.client.get(self.url), reverse('dsf:lista'))


class QuemPreencheODsfTests(TestCase):
    def setUp(self):
        self.dsf = Dsf.objects.create(
            nome='Ana Exemplo', data='2026-11-26', beneficio_solicitado='CESTA BÁSICA', ficha_preenchida=True,
        )
        self.editar = reverse('dsf:editar', args=[self.dsf.pk])

    def test_assistente_social_psicologo_e_administrador_preenchem(self):
        contas = (usuario('as'), usuario('psi', 'PSICOLOGO'), usuario('root', None, is_superuser=True))
        for conta in contas:
            self.client.force_login(conta)
            lista = self.client.get(reverse('dsf:lista'))
            self.assertContains(lista, reverse('dsf:criar'))
            self.assertContains(lista, self.editar)
            self.assertEqual(self.client.get(reverse('dsf:criar')).status_code, 200)
            self.assertEqual(self.client.get(self.editar).status_code, 200)

    def test_administrativo_ve_a_lista_mas_nao_abre_nem_grava_a_ficha(self):
        self.client.force_login(usuario('adm', 'TECNICO_ADMINISTRATIVO'))
        lista = self.client.get(reverse('dsf:lista'))
        self.assertContains(lista, 'Ana Exemplo')
        self.assertNotContains(lista, reverse('dsf:criar'))
        self.assertNotContains(lista, self.editar)
        for url in (reverse('dsf:criar'), self.editar):
            self.assertRedirects(self.client.get(url), reverse('dsf:lista'))
            self.client.post(url, dados(nome='Outro Nome'))
        self.assertEqual(list(Dsf.objects.values_list('nome', flat=True)), ['Ana Exemplo'])


class MenuDeGestaoTests(TestCase):
    PAGINAS = ('dsf:lista', 'certidoes:lista', 'dmae:lista', 'propao:lista')

    def setUp(self):
        self.usuario = usuario()

    def test_menu_traz_as_quatro_opcoes_e_marca_so_a_atual(self):
        self.client.force_login(self.usuario)
        for atual in self.PAGINAS:
            html = self.client.get(reverse(atual)).content.decode()
            self.assertNotIn('abas-painel', html)
            for pagina in self.PAGINAS:
                marcado = 'ativo' if pagina == atual else ''
                self.assertIn(f'class="sidebar-link {marcado}" href="{reverse(pagina)}"', html)

    def test_ficha_do_dsf_mantem_o_menu_dsf_marcado(self):
        self.client.force_login(self.usuario)
        resp = self.client.get(reverse('dsf:criar'))
        self.assertContains(resp, f'class="sidebar-link ativo" href="{reverse("dsf:lista")}"')

    def test_paginas_exigem_login(self):
        for nome in (*self.PAGINAS, 'dsf:criar'):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 302)

    def test_pagina_dsf_tem_botao_novo_e_menu_chama_dsf(self):
        self.client.force_login(self.usuario)
        resp = self.client.get(reverse('dsf:lista'))
        self.assertContains(resp, reverse('dsf:criar'))
        self.assertNotContains(resp, 'DSF Concluído')
