from datetime import date

from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario

from .models import TapDiario


class TapMensalTests(TestCase):
    """A7: salvar um mês volta para o mesmo mês."""

    def setUp(self):
        self.client.force_login(Usuario.objects.create_user('u', password='x'))
        self.campos_fev = {f'tap_{d}': '0' for d in range(1, 29)}

    def test_salvar_mes_passado_volta_para_o_mesmo_mes(self):
        url = reverse('tap:mensal') + '?ano=2026&mes=2'
        resp = self.client.post(url, {'ano': '2026', 'mes': '2', **self.campos_fev, 'tap_3': '7'})
        self.assertRedirects(resp, url)
        self.assertEqual(TapDiario.objects.get(data=date(2026, 2, 3)).tap_diario, 7)
        self.assertEqual(TapDiario.objects.filter(data__year=2026, data__month=2).count(), 28)

    def test_post_sem_querystring_usa_ano_e_mes_dos_campos_ocultos(self):
        resp = self.client.post(reverse('tap:mensal'), {'ano': '2026', 'mes': '2', **self.campos_fev, 'tap_10': '4'})
        self.assertRedirects(resp, reverse('tap:mensal') + '?ano=2026&mes=2')
        self.assertEqual(TapDiario.objects.get(data=date(2026, 2, 10)).tap_diario, 4)
