from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario

from .models import Dsf


class NovoDsfTests(TestCase):
    def setUp(self):
        self.client.force_login(Usuario.objects.create_user('tec', password='x', cargo='TECNICO_ADMINISTRATIVO'))

    def enviar(self, beneficio):
        return self.client.post(reverse('dsf:criar'), {
            'nome': 'Ana', 'beneficio_solicitado': beneficio, 'data': '2026-11-23', 'resultado': 'DEFERIDO',
        })

    def test_beneficio_e_uma_das_tres_opcoes(self):
        html = self.client.get(reverse('dsf:criar')).content.decode()
        for opcao in ('Cesta Básica', 'Fralda', 'Absorvente'):
            self.assertIn(f'>{opcao}</option>', html)
        self.enviar('FRALDA')
        self.assertEqual(Dsf.objects.get().get_beneficio_solicitado_display(), 'Fralda')

    def test_beneficio_fora_da_lista_e_recusado(self):
        resp = self.enviar('BOLSA QUALQUER')
        self.assertFalse(Dsf.objects.exists())
        self.assertContains(resp, 'erro-campo')
