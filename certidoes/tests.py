from datetime import date

from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario

from .models import Certidao


class EditarCertidaoTests(TestCase):
    def test_datas_gravadas_aparecem_na_edicao(self):
        """Antes elas vinham em dd/mm/aaaa, o campo abria vazio e salvar apagava recebimento e entrega."""
        self.client.force_login(Usuario.objects.create_user('adm', password='x'))
        certidao = Certidao.objects.create(
            data_solicitacao=date(2026, 11, 5), quem_solicitou='Bia Exemplo', de_quem='Ana Exemplo',
            data_recebimento=date(2026, 11, 12), data_entrega=date(2026, 11, 20),
        )
        resp = self.client.get(reverse('certidoes:editar', args=[certidao.pk]))
        for dia in ('2026-11-05', '2026-11-12', '2026-11-20'):
            self.assertContains(resp, f'value="{dia}"')
