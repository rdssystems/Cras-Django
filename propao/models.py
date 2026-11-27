from django.conf import settings
from django.db import models

from cras.campos import reais, sim_nao, texto
from cras.escolhas import EstadoCivil, Resultado, Solicitacao


class RequerimentoProPao(models.Model):
    """Requerimento do PRÓ-PÃO: a ficha de papel do CRAS."""

    Resultado = Resultado
    Solicitacao = Solicitacao

    class SituacaoDoImovel(models.TextChoices):
        PROPRIA = 'PROPRIA', 'Própria'
        CEDIDA = 'CEDIDA', 'Cedida'
        ALUGADA = 'ALUGADA', 'Alugada'
        FINANCIADA = 'FINANCIADA', 'Financiada'
        OCUPACAO = 'OCUPACAO', 'Ocupação'

    class SegundoImovel(models.TextChoices):
        NAO = 'NAO', 'Não há 2 imóveis'
        SIM = 'SIM', 'Possui 2º imóvel'

    data = models.DateField('Data')
    solicitacao = models.CharField('Tipo de solicitação', max_length=10, choices=Solicitacao.choices)

    # I. Identificação
    nome = models.CharField('Nome', max_length=200)
    data_nascimento = models.DateField('Data de nascimento', null=True, blank=True)
    endereco = texto('Endereço')
    numero = texto('Nº', 20)
    complemento = texto('Complemento', 100)
    bairro = texto('Bairro', 100)
    cep = texto('CEP', 9)
    documento = texto('Documento de identidade', 30)
    orgao_emissor = texto('SSP/UF', 20)
    cpf = texto('CPF', 11)
    naturalidade = texto('Naturalidade', 100)
    estado_civil = models.CharField('Estado civil', max_length=12, choices=EstadoCivil.choices, blank=True)
    telefone = texto('Telefone', 30)
    cad_unico = sim_nao('Está cadastrado no CadÚnico?')
    nis = texto('NIS', 20)

    # II. Composição familiar fica em PessoaProPao. III. Renda familiar:
    renda_familiar = reais('Renda familiar (R$)')

    # IV. Situação habitacional
    situacao_imovel = models.CharField(
        'Situação do imóvel', max_length=12, choices=SituacaoDoImovel.choices, blank=True
    )
    valor_imovel = reais('Valor do aluguel ou da parcela (R$)')
    ocupacao_imovel = texto('Ocupação (detalhe)')

    # V. Preenchido pela analista do sistema
    segundo_imovel = models.CharField('Segundo imóvel', max_length=3, choices=SegundoImovel.choices, blank=True)
    segundo_imovel_titular = models.BooleanField('Titular', default=False)
    segundo_imovel_conjuge = models.BooleanField('Cônjuge', default=False)
    segundo_imovel_endereco = texto('Endereço do 2º imóvel')
    sistema = texto('Sistema')
    data_analise = models.DateField('Data da análise', null=True, blank=True)

    resultado = models.CharField('Deferido/Indeferido', max_length=15, choices=Resultado.choices, blank=True)
    servidor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Servidor',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='requerimentos_pro_pao'
    )

    class Meta:
        ordering = ['-data', '-id']
        verbose_name = 'Requerimento PRÓ-PÃO'
        verbose_name_plural = 'Requerimentos PRÓ-PÃO'

    def __str__(self):
        return f'{self.nome} - {self.get_solicitacao_display()}'

    @property
    def pendente(self):
        """Ainda sem deferimento (só estes podem ser editados)."""
        return not self.resultado


class PessoaProPao(models.Model):
    requerimento = models.ForeignKey(RequerimentoProPao, on_delete=models.CASCADE, related_name='pessoas')
    nome = models.CharField('Nome', max_length=200)
    parentesco = texto('Parentesco', 60)
    idade = models.PositiveSmallIntegerField('Idade', null=True, blank=True)
    ocupacao = texto('Profissão/Ocupação', 100)
    renda = reais('Renda (R$)')

    class Meta:
        ordering = ['id']
        verbose_name = 'Pessoa da composição familiar'
        verbose_name_plural = 'Composição familiar'

    def __str__(self):
        return self.nome


class ProcedimentoProPao(models.Model):
    requerimento = models.ForeignKey(RequerimentoProPao, on_delete=models.CASCADE, related_name='procedimentos')
    data = models.DateField('Data')
    procedimento = models.TextField('Procedimento')

    class Meta:
        ordering = ['data', 'id']
        verbose_name = 'Procedimento'
        verbose_name_plural = 'Procedimentos'

    def __str__(self):
        return f'{self.data:%d/%m/%Y} - {self.procedimento[:60]}'
