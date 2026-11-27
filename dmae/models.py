from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models

from cras.campos import reais, sim_nao, texto
from cras.escolhas import EstadoCivil, Resultado, Solicitacao


class IsencaoDmae(models.Model):
    """Requerimento DMAE (Leis nº 309/2003 e 315/2003): a ficha de papel do CRAS."""

    Resultado = Resultado
    Solicitacao = Solicitacao

    class TipoDeImovel(models.TextChoices):
        CASA = 'CASA', 'Casa'
        BARRACO = 'BARRACO', 'Barraco'
        APARTAMENTO = 'APARTAMENTO', 'Apartamento'

    class SituacaoDoImovel(models.TextChoices):
        PROPRIA = 'PROPRIA', 'Própria'
        ALUGADA = 'ALUGADA', 'Alugada'
        FINANCIADA = 'FINANCIADA', 'Financiada'
        CEDIDO = 'CEDIDO', 'Cedido'
        INVASAO = 'INVASAO', 'Invasão'

    data = models.DateField('Data')
    solicitacao = models.CharField('Solicitação', max_length=10, choices=Solicitacao.choices)
    codigo_imovel = texto('Código do imóvel', 30)

    # I. Identificação
    nome = models.CharField('Nome', max_length=200)
    endereco = texto('Endereço')
    bairro = texto('Bairro', 100)
    cpf = texto('CPF', 11)
    naturalidade = texto('Naturalidade', 100)
    estado_civil = models.CharField('Estado civil', max_length=12, choices=EstadoCivil.choices, blank=True)
    cargo = texto('Cargo', 100)
    telefone = texto('Telefone', 30)
    cad_unico = sim_nao('Está cadastrado no CadÚnico?')
    nis = texto('NIS', 20)

    # II. Composição familiar (as pessoas ficam em MembroDmae)
    renda_familiar = reais('Renda familiar (R$)')

    # III. Situação habitacional
    tipo_imovel = models.CharField('Tipo de imóvel', max_length=12, choices=TipoDeImovel.choices, blank=True)
    situacao_imovel = models.CharField(
        'Situação do imóvel', max_length=12, choices=SituacaoDoImovel.choices, blank=True
    )
    mais_de_um_imovel = sim_nao('Possui mais de um imóvel?')

    # IV. Consumo de água (três meses, no formato MM/AAAA)
    consumo1_mes = texto('1º mês (MM/AAAA)', 7)
    consumo1_m3 = models.PositiveIntegerField('1º mês: consumo (m³)', null=True, blank=True)
    consumo2_mes = texto('2º mês (MM/AAAA)', 7)
    consumo2_m3 = models.PositiveIntegerField('2º mês: consumo (m³)', null=True, blank=True)
    consumo3_mes = texto('3º mês (MM/AAAA)', 7)
    consumo3_m3 = models.PositiveIntegerField('3º mês: consumo (m³)', null=True, blank=True)

    # V. Evolução fica em EvolucaoDmae. VI. Parecer social:
    parecer_social = models.TextField('Parecer social', blank=True)

    resultado = models.CharField('Deferido/Indeferido', max_length=15, choices=Resultado.choices, blank=True)
    servidor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Servidor',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='isencoes_dmae'
    )

    class Meta:
        ordering = ['-data', '-id']
        verbose_name = 'Requerimento DMAE'
        verbose_name_plural = 'Requerimentos DMAE'

    def __str__(self):
        return f'{self.nome} - {self.get_solicitacao_display()}'

    @property
    def pendente(self):
        """Ainda sem deferimento (só estes podem ser editados)."""
        return not self.resultado

    @property
    def consumo_medio(self):
        """Média, em m³, dos meses preenchidos; None se nenhum foi preenchido."""
        meses = [v for v in (self.consumo1_m3, self.consumo2_m3, self.consumo3_m3) if v is not None]
        if not meses:
            return None
        return (Decimal(sum(meses)) / len(meses)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


class MembroDmae(models.Model):
    requerimento = models.ForeignKey(IsencaoDmae, on_delete=models.CASCADE, related_name='membros')
    nome = models.CharField('Nome', max_length=200)
    parentesco = texto('Parentesco', 60)
    idade = models.PositiveSmallIntegerField('Idade', null=True, blank=True)
    profissao = texto('Profissão', 100)
    renda = reais('Renda (R$)')

    class Meta:
        ordering = ['id']
        verbose_name = 'Pessoa da composição familiar'
        verbose_name_plural = 'Composição familiar'

    def __str__(self):
        return self.nome


class EvolucaoDmae(models.Model):
    requerimento = models.ForeignKey(IsencaoDmae, on_delete=models.CASCADE, related_name='evolucoes')
    data = models.DateField('Data')
    procedimento = models.TextField('Procedimento')

    class Meta:
        ordering = ['data', 'id']
        verbose_name = 'Evolução'
        verbose_name_plural = 'Evolução'

    def __str__(self):
        return f'{self.data:%d/%m/%Y} - {self.procedimento[:60]}'
