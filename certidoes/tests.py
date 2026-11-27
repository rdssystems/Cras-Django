from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Usuario

from .models import Certidao

CPF_DE_TESTE = '52998224725'  # exemplo com dígitos verificadores válidos


def dados(**campos):
    post = {
        'data_solicitacao': '2026-11-05', 'cidade': 'UBERLÂNDIA - MG', 'certidao_nascimento': 'on',
        'de_quem': 'Ana Exemplo', 'quem_solicitou': 'Bia Exemplo',
    }
    post.update(campos)
    return {chave: valor for chave, valor in post.items() if valor is not None}


class NovaCertidaoTests(TestCase):
    def setUp(self):
        self.servidor = Usuario.objects.create_user('adm', password='x', cargo='TECNICO_ADMINISTRATIVO')
        self.client.force_login(self.servidor)

    def test_formulario_traz_a_ficha_com_data_de_hoje_e_sem_acompanhamento(self):
        resp = self.client.get(reverse('certidoes:criar'))
        for trecho in ('de Nascimento', 'de Casamento', 'de Óbito', 'Com averbação', 'Filiação', 'CadÚnico',
                       'Nome do responsável', 'UBERLÂNDIA - MG', f'value="{timezone.localdate():%Y-%m-%d}"'):
            self.assertContains(resp, trecho)
        self.assertNotContains(resp, 'name="data_entrega"')

    def test_ficha_completa_e_listada(self):
        resp = self.client.post(reverse('certidoes:criar'), dados(
            certidao_casamento='on', com_averbacao='on', filiacao='Carla Exemplo', data_nascimento='1990-05-10',
            cpf=CPF_DE_TESTE, cad_unico='SIM', nis='12345678901', parentesco='Irmã',
        ))
        self.assertRedirects(resp, reverse('certidoes:lista'))
        certidao = Certidao.objects.get()
        self.assertEqual(certidao.servidor, self.servidor)
        self.assertTrue(certidao.ficha_preenchida)
        self.assertEqual(certidao.tipos, 'Nascimento, Casamento, Com averbação')
        self.assertEqual(certidao.cad_unico, 'SIM')
        self.assertContains(self.client.get(reverse('certidoes:lista')), 'Nascimento, Casamento, Com averbação')

    def test_exige_o_tipo_da_certidao(self):
        resp = self.client.post(reverse('certidoes:criar'), dados(certidao_nascimento=None))
        self.assertFalse(Certidao.objects.exists())
        self.assertContains(resp, 'Marque a certidão solicitada.')

    def test_exige_nomes_e_recusa_cpf_invalido(self):
        resp = self.client.post(reverse('certidoes:criar'), dados(de_quem='', quem_solicitou='', cpf='12345678900'))
        self.assertFalse(Certidao.objects.exists())
        self.assertEqual({'de_quem', 'quem_solicitou', 'cpf'}, set(resp.context['form'].errors))

    def test_exige_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('certidoes:criar')).status_code, 302)


class EditarCertidaoTests(TestCase):
    def setUp(self):
        self.client.force_login(Usuario.objects.create_user('adm', password='x'))
        self.antiga = Certidao.objects.create(  # como as importadas da planilha
            data_solicitacao=date(2026, 11, 5), quem_solicitou='Bia Exemplo', de_quem='Ana Exemplo',
            data_recebimento=date(2026, 11, 12), data_entrega=date(2026, 11, 20),
        )
        self.url = reverse('certidoes:editar', args=[self.antiga.pk])

    def test_datas_gravadas_aparecem_na_edicao(self):
        """Antes elas vinham em dd/mm/aaaa, o campo abria vazio e salvar apagava recebimento e entrega."""
        resp = self.client.get(self.url)
        for data in ('2026-11-05', '2026-11-12', '2026-11-20'):
            self.assertContains(resp, f'value="{data}"')
        self.assertContains(resp, 'name="data_entrega"')

    def test_registro_antigo_salva_o_acompanhamento_sem_tipo(self):
        resp = self.client.post(self.url, dados(
            certidao_nascimento=None, data_recebimento='2026-11-12', data_entrega='2026-11-21',
            entregue_para='Ana Exemplo',
        ))
        self.assertRedirects(resp, reverse('certidoes:lista'))
        self.antiga.refresh_from_db()
        self.assertEqual(self.antiga.data_entrega, date(2026, 11, 21))
        self.assertFalse(self.antiga.ficha_preenchida)

    def test_ficha_feita_no_sistema_continua_exigindo_o_tipo(self):
        Certidao.objects.filter(pk=self.antiga.pk).update(ficha_preenchida=True, certidao_nascimento=True)
        resp = self.client.post(self.url, dados(certidao_nascimento=None))
        self.assertContains(resp, 'Marque a certidão solicitada.')
