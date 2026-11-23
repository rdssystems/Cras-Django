from django.test import TestCase
from django.urls import reverse

from .models import Usuario

SENHA = 'Cras-2026-segura'


class GestaoDeContasTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser('chefe', password='x')
        self.client.force_login(self.admin)

    def criar(self, **dados):
        padrao = {'first_name': 'Rita', 'last_name': 'Lopes', 'username': 'rita', 'email': '',
                  'cargo': 'ASSISTENTE_SOCIAL', 'password1': SENHA, 'password2': SENHA}
        return self.client.post(reverse('usuarios:criar'), {**padrao, **dados}, follow=True)

    def test_administrador_cria_conta_que_consegue_entrar(self):
        resp = self.criar()
        self.assertContains(resp, 'Conta de Rita Lopes criada.')
        rita = Usuario.objects.get(username='rita')
        self.assertEqual(rita.cargo, Usuario.Cargo.ASSISTENTE_SOCIAL)
        self.assertFalse(rita.is_superuser)
        self.client.logout()
        self.assertTrue(self.client.login(username='rita', password=SENHA))

    def test_so_tres_cargos_e_cargo_obrigatorio(self):
        self.assertEqual([c for c, _ in Usuario.Cargo.choices],
                         ['ASSISTENTE_SOCIAL', 'PSICOLOGO', 'TECNICO_ADMINISTRATIVO'])
        self.assertEqual(Usuario.Cargo.TECNICO_ADMINISTRATIVO.label, 'Administrativo')
        self.assertContains(self.criar(cargo=''), 'Escolha o cargo.')
        self.criar(cargo='COORDENADOR')
        self.assertFalse(Usuario.objects.filter(username='rita').exists())

    def test_senhas_diferentes_ou_fracas_sao_recusadas(self):
        self.criar(password2='outra-coisa-123')
        self.criar(password1='123', password2='123')
        self.assertFalse(Usuario.objects.filter(username='rita').exists())

    def test_quem_nao_e_administrador_nao_acessa(self):
        tec = Usuario.objects.create_user('tec', password='x', cargo='TECNICO_ADMINISTRATIVO')
        self.client.force_login(tec)
        for url in (reverse('usuarios:lista'), reverse('usuarios:criar'),
                    reverse('usuarios:editar', args=[self.admin.pk])):
            self.assertRedirects(self.client.get(url), reverse('inicio'))
        self.assertNotContains(self.client.get(reverse('inicio')), 'manage_accounts')

    def test_editar_e_desativar_conta(self):
        tec = Usuario.objects.create_user('tec', password='x', cargo='TECNICO_ADMINISTRATIVO', first_name='Téo')
        self.client.post(reverse('usuarios:editar', args=[tec.pk]), {
            'first_name': 'Téo', 'last_name': 'Silva', 'username': 'tec', 'email': '',
            'cargo': 'PSICOLOGO', 'is_active': 'on',
        })
        tec.refresh_from_db()
        self.assertEqual((tec.last_name, tec.cargo), ('Silva', 'PSICOLOGO'))

        self.client.post(reverse('usuarios:alternar_ativo', args=[tec.pk]))
        tec.refresh_from_db()
        self.assertFalse(tec.is_active)

    def test_administrador_nao_se_tranca_para_fora(self):
        resp = self.client.post(reverse('usuarios:editar', args=[self.admin.pk]), {
            'first_name': 'Chefe', 'username': 'chefe', 'cargo': '',
        })
        self.assertContains(resp, 'Você não pode tirar o seu próprio acesso de administrador.')
        self.assertContains(resp, 'Você não pode desativar a sua própria conta.')
        self.client.post(reverse('usuarios:alternar_ativo', args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_superuser and self.admin.is_active)

    def test_definir_nova_senha(self):
        tec = Usuario.objects.create_user('tec', password='antiga', cargo='TECNICO_ADMINISTRATIVO')
        self.client.post(reverse('usuarios:senha', args=[tec.pk]),
                         {'new_password1': SENHA, 'new_password2': SENHA})
        tec.refresh_from_db()
        self.assertTrue(tec.check_password(SENHA))
