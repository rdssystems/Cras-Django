from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Usuario

from .models import EvolucaoDmae, IsencaoDmae

CPF_DE_TESTE = '52998224725'  # exemplo com dígitos verificadores válidos


def linhas(prefixo, itens, iniciais=0):
    post = {
        f'{prefixo}-TOTAL_FORMS': str(len(itens)), f'{prefixo}-INITIAL_FORMS': str(iniciais),
        f'{prefixo}-MIN_NUM_FORMS': '0', f'{prefixo}-MAX_NUM_FORMS': '1000',
    }
    for i, item in enumerate(itens):
        post.update({f'{prefixo}-{i}-{campo}': valor for campo, valor in item.items()})
    return post


def dados(membros=(), evolucoes=(), evolucoes_iniciais=0, **campos):
    post = {'data': '2026-11-26', 'solicitacao': 'PRIMEIRA', 'nome': 'Ana Exemplo'}
    post.update(campos)
    post.update(linhas('membros', membros))
    post.update(linhas('evolucoes', evolucoes, evolucoes_iniciais))
    return post


class NovoRequerimentoTests(TestCase):
    def setUp(self):
        self.servidor = Usuario.objects.create_user('adm', password='x', cargo='TECNICO_ADMINISTRATIVO')
        self.client.force_login(self.servidor)

    def test_formulario_traz_a_ficha_com_data_de_hoje(self):
        resp = self.client.get(reverse('dmae:criar'))
        for trecho in ('1ª vez', 'Renovação', 'Código do imóvel', 'Composição familiar', 'Invasão',
                       'Possui mais de um imóvel?', 'Consumo de água', 'data-adicionar="evolucoes"',
                       'Parecer social', f'value="{timezone.localdate():%Y-%m-%d}"'):
            self.assertContains(resp, trecho)
        self.assertNotContains(resp, 'name="resultado"')
        self.assertEqual(resp.context['membros'].total_form_count(), 2)
        self.assertEqual(resp.context['evolucoes'].total_form_count(), 1)

    def test_ficha_completa_nasce_pendente_e_e_listada(self):
        resp = self.client.post(reverse('dmae:criar'), dados(
            codigo_imovel='123456', cpf=CPF_DE_TESTE, cad_unico='SIM', nis='12345678901',
            tipo_imovel='CASA', situacao_imovel='ALUGADA', mais_de_um_imovel='NAO', renda_familiar='1.412,50',
            consumo1_mes='8/2026', consumo1_m3='10', consumo2_mes='09/2026', consumo2_m3='11',
            consumo3_mes='10/2026', consumo3_m3='11', parecer_social='Texto de exemplo',
            membros=[{'nome': 'Bia Exemplo', 'parentesco': 'Filha', 'idade': '8', 'renda': '600'}, {}],
            evolucoes=[{'data': '2026-11-26', 'procedimento': 'Visita'},
                       {'data': '2026-11-27', 'procedimento': 'Retorno'}],
        ))
        self.assertRedirects(resp, reverse('dmae:lista'))
        requerimento = IsencaoDmae.objects.get()
        self.assertEqual(requerimento.servidor, self.servidor)
        self.assertTrue(requerimento.pendente)
        self.assertEqual(requerimento.renda_familiar, Decimal('1412.50'))
        self.assertEqual(requerimento.consumo1_mes, '08/2026')
        self.assertEqual(requerimento.consumo_medio, Decimal('10.7'))
        self.assertEqual([m.nome for m in requerimento.membros.all()], ['Bia Exemplo'])
        self.assertEqual([e.procedimento for e in requerimento.evolucoes.all()], ['Visita', 'Retorno'])
        lista = self.client.get(reverse('dmae:lista'))
        for trecho in ('Ana Exemplo', '123456', '10,7 m³', 'PENDENTE'):
            self.assertContains(lista, trecho)

    def test_consumo_medio_considera_so_os_meses_preenchidos(self):
        self.assertIsNone(IsencaoDmae().consumo_medio)
        self.assertEqual(IsencaoDmae(consumo1_m3=0, consumo2_m3=9).consumo_medio, Decimal('4.5'))

    def test_exige_data_solicitacao_e_nome(self):
        resp = self.client.post(reverse('dmae:criar'), dados(data='', solicitacao='', nome=''))
        self.assertFalse(IsencaoDmae.objects.exists())
        self.assertEqual({'data', 'solicitacao', 'nome'}, set(resp.context['form'].errors))

    def test_recusa_cpf_mes_e_linha_incompleta(self):
        resp = self.client.post(reverse('dmae:criar'), dados(
            cpf='12345678900', consumo1_mes='13/2026', evolucoes=[{'data': '2026-11-26'}],
        ))
        self.assertFalse(IsencaoDmae.objects.exists())
        self.assertEqual({'cpf', 'consumo1_mes'}, set(resp.context['form'].errors))
        self.assertIn('procedimento', resp.context['evolucoes'].errors[0])
        self.assertContains(resp, 'Use mês e ano, como 03/2026.')

    def test_endereco_antigo_leva_a_pagina_nova(self):
        resp = self.client.get('/dsf/isencao-dmae', follow=True)
        self.assertEqual(resp.request['PATH_INFO'], reverse('dmae:lista'))
        self.assertEqual(resp.status_code, 200)

    def test_exige_login(self):
        self.client.logout()
        for nome in ('dmae:lista', 'dmae:criar'):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 302)


class EditarRequerimentoTests(TestCase):
    def setUp(self):
        self.autor = Usuario.objects.create_user('autor', password='x')
        self.client.force_login(Usuario.objects.create_user('outro', password='x'))
        self.requerimento = IsencaoDmae.objects.create(
            data=date(2026, 11, 5), solicitacao='RENOVACAO', nome='Ana Exemplo', servidor=self.autor,
        )
        self.evolucao = EvolucaoDmae.objects.create(
            requerimento=self.requerimento, data=date(2026, 11, 6), procedimento='Visita',
        )
        self.url = reverse('dmae:editar', args=[self.requerimento.pk])

    def linha(self, **campos):
        linha = {'id': str(self.evolucao.pk), 'requerimento': str(self.requerimento.pk),
                 'data': '2026-11-06', 'procedimento': 'Visita'}
        linha.update(campos)
        return linha

    def test_datas_gravadas_aparecem_na_edicao(self):
        resp = self.client.get(self.url)
        for dia in ('2026-11-05', '2026-11-06'):
            self.assertContains(resp, f'value="{dia}"')
        self.assertEqual(resp.context['evolucoes'].total_form_count(), 1)

    def test_acrescenta_linha_na_evolucao_sem_trocar_o_servidor(self):
        resp = self.client.post(self.url, dados(
            solicitacao='RENOVACAO', evolucoes_iniciais=1,
            evolucoes=[self.linha(), {'data': '2026-11-20', 'procedimento': 'Entrega de documentos'}],
        ))
        self.assertRedirects(resp, reverse('dmae:lista'))
        self.assertEqual(self.requerimento.evolucoes.count(), 2)
        self.requerimento.refresh_from_db()
        self.assertEqual(self.requerimento.servidor, self.autor)

    def test_remove_linha_da_evolucao(self):
        self.client.post(self.url, dados(evolucoes_iniciais=1, evolucoes=[self.linha(DELETE='on')]))
        self.assertFalse(self.requerimento.evolucoes.exists())

    def test_requerimento_deferido_nao_pode_ser_editado(self):
        IsencaoDmae.objects.filter(pk=self.requerimento.pk).update(resultado='DEFERIDO')
        resp = self.client.post(self.url, dados(nome='Outro Nome'))
        self.assertRedirects(resp, reverse('dmae:lista'))
        self.requerimento.refresh_from_db()
        self.assertEqual(self.requerimento.nome, 'Ana Exemplo')
        self.assertNotContains(self.client.get(reverse('dmae:lista')), self.url)
