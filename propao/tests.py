from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Usuario

from .models import ProcedimentoProPao, RequerimentoProPao

CPF_DE_TESTE = '52998224725'  # exemplo com dígitos verificadores válidos


def linhas(prefixo, itens, iniciais=0):
    post = {
        f'{prefixo}-TOTAL_FORMS': str(len(itens)), f'{prefixo}-INITIAL_FORMS': str(iniciais),
        f'{prefixo}-MIN_NUM_FORMS': '0', f'{prefixo}-MAX_NUM_FORMS': '1000',
    }
    for i, item in enumerate(itens):
        post.update({f'{prefixo}-{i}-{campo}': valor for campo, valor in item.items()})
    return post


def dados(pessoas=(), procedimentos=(), procedimentos_iniciais=0, **campos):
    post = {'data': '2026-11-26', 'solicitacao': 'PRIMEIRA', 'nome': 'Ana Exemplo'}
    post.update(campos)
    post.update(linhas('pessoas', pessoas))
    post.update(linhas('procedimentos', procedimentos, procedimentos_iniciais))
    return post


class NovoRequerimentoTests(TestCase):
    def setUp(self):
        self.servidor = Usuario.objects.create_user('adm', password='x', cargo='TECNICO_ADMINISTRATIVO')
        self.client.force_login(self.servidor)

    def test_formulario_traz_a_ficha_com_data_de_hoje(self):
        resp = self.client.get(reverse('propao:criar'))
        for trecho in ('1ª vez', 'Renovação', 'CEP', 'SSP/UF', 'Composição familiar', 'Renda familiar',
                       'Ocupação', 'Análise do sistema', 'Não há 2 imóveis', 'Cônjuge',
                       'data-adicionar="procedimentos"', f'value="{timezone.localdate():%Y-%m-%d}"'):
            self.assertContains(resp, trecho)
        self.assertNotContains(resp, 'name="resultado"')
        self.assertEqual(resp.context['pessoas'].total_form_count(), 4)
        self.assertEqual(resp.context['procedimentos'].total_form_count(), 1)

    def test_ficha_completa_nasce_pendente_e_e_listada(self):
        resp = self.client.post(reverse('propao:criar'), dados(
            data_nascimento='1990-05-10', bairro='Bairro Exemplo', cep='38.400-000', cpf=CPF_DE_TESTE,
            documento='MG-00.000.000', orgao_emissor='MG', cad_unico='SIM', renda_familiar='R$ 1.200',
            situacao_imovel='ALUGADA', valor_imovel='650,00', segundo_imovel='SIM',
            segundo_imovel_titular='on', segundo_imovel_conjuge='on', segundo_imovel_endereco='Rua Exemplo, 1',
            sistema='Sistema de exemplo', data_analise='2026-11-27',
            pessoas=[{'nome': 'Bia Exemplo', 'parentesco': 'Filha', 'idade': '8', 'renda': '600'}, {}],
            procedimentos=[{'data': '2026-11-26', 'procedimento': 'Visita'}],
        ))
        self.assertRedirects(resp, reverse('propao:lista'))
        requerimento = RequerimentoProPao.objects.get()
        self.assertEqual(requerimento.servidor, self.servidor)
        self.assertTrue(requerimento.pendente)
        self.assertEqual(requerimento.cep, '38400-000')
        self.assertEqual(requerimento.renda_familiar, Decimal('1200'))
        self.assertEqual(requerimento.valor_imovel, Decimal('650'))
        self.assertTrue(requerimento.segundo_imovel_titular and requerimento.segundo_imovel_conjuge)
        self.assertEqual([p.nome for p in requerimento.pessoas.all()], ['Bia Exemplo'])
        self.assertEqual([p.procedimento for p in requerimento.procedimentos.all()], ['Visita'])
        lista = self.client.get(reverse('propao:lista'))
        for trecho in ('Ana Exemplo', 'Bairro Exemplo', 'PENDENTE'):
            self.assertContains(lista, trecho)

    def test_exige_data_solicitacao_e_nome(self):
        resp = self.client.post(reverse('propao:criar'), dados(data='', solicitacao='', nome=''))
        self.assertFalse(RequerimentoProPao.objects.exists())
        self.assertEqual({'data', 'solicitacao', 'nome'}, set(resp.context['form'].errors))

    def test_recusa_cpf_e_cep_invalidos(self):
        resp = self.client.post(reverse('propao:criar'), dados(cpf='12345678900', cep='3840'))
        self.assertFalse(RequerimentoProPao.objects.exists())
        self.assertEqual({'cpf', 'cep'}, set(resp.context['form'].errors))

    def test_dono_do_segundo_imovel_so_vale_se_houver_segundo_imovel(self):
        for escolha in ('', 'NAO'):
            resp = self.client.post(reverse('propao:criar'), dados(
                segundo_imovel=escolha, segundo_imovel_conjuge='on',
            ))
            self.assertEqual({'segundo_imovel'}, set(resp.context['form'].errors))
        self.assertFalse(RequerimentoProPao.objects.exists())

    def test_exige_login(self):
        self.client.logout()
        for nome in ('propao:lista', 'propao:criar'):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 302)

    def test_endereco_antigo_leva_a_pagina_nova(self):
        resp = self.client.get('/dsf/pro-pao', follow=True)
        self.assertEqual(resp.request['PATH_INFO'], reverse('propao:lista'))
        self.assertEqual(resp.status_code, 200)


class EditarRequerimentoTests(TestCase):
    def setUp(self):
        self.autor = Usuario.objects.create_user('autor', password='x')
        self.client.force_login(Usuario.objects.create_user('outro', password='x'))
        self.requerimento = RequerimentoProPao.objects.create(
            data=date(2026, 11, 5), solicitacao='RENOVACAO', nome='Ana Exemplo', servidor=self.autor,
            data_nascimento=date(1990, 5, 10), data_analise=date(2026, 11, 8),
        )
        self.procedimento = ProcedimentoProPao.objects.create(
            requerimento=self.requerimento, data=date(2026, 11, 6), procedimento='Visita',
        )
        self.url = reverse('propao:editar', args=[self.requerimento.pk])

    def test_datas_gravadas_aparecem_na_edicao(self):
        resp = self.client.get(self.url)
        for dia in ('2026-11-05', '1990-05-10', '2026-11-08', '2026-11-06'):
            self.assertContains(resp, f'value="{dia}"')

    def test_acrescenta_procedimento_sem_trocar_o_servidor(self):
        existente = {'id': str(self.procedimento.pk), 'requerimento': str(self.requerimento.pk),
                     'data': '2026-11-06', 'procedimento': 'Visita'}
        resp = self.client.post(self.url, dados(
            solicitacao='RENOVACAO', procedimentos_iniciais=1,
            procedimentos=[existente, {'data': '2026-11-20', 'procedimento': 'Entrega de documentos'}],
        ))
        self.assertRedirects(resp, reverse('propao:lista'))
        self.assertEqual(self.requerimento.procedimentos.count(), 2)
        self.requerimento.refresh_from_db()
        self.assertEqual(self.requerimento.servidor, self.autor)

    def test_requerimento_deferido_nao_pode_ser_editado(self):
        RequerimentoProPao.objects.filter(pk=self.requerimento.pk).update(resultado='INDEFERIDO')
        resp = self.client.post(self.url, dados(nome='Outro Nome'))
        self.assertRedirects(resp, reverse('propao:lista'))
        self.requerimento.refresh_from_db()
        self.assertEqual(self.requerimento.nome, 'Ana Exemplo')
        self.assertNotContains(self.client.get(reverse('propao:lista')), self.url)
