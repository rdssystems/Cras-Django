from django.conf import settings
from django.db import models

from cras.campos import reais, sim_nao, texto
from cras.escolhas import EstadoCivil, Resultado
from usuarios.models import Usuario

# A ficha do DSF é feita por estes cargos (e pelo administrador do sistema).
CARGOS_DO_DSF = (Usuario.Cargo.ASSISTENTE_SOCIAL, Usuario.Cargo.PSICOLOGO)


def pode_preencher_dsf(usuario):
    return usuario.is_authenticated and (usuario.is_superuser or usuario.cargo in CARGOS_DO_DSF)


class Dsf(models.Model):
    """Diagnóstico Sócio Familiar (DSF): a ficha de papel do CRAS, mais o parecer.

    Os registros importados da planilha só têm nome, benefício, data, resultado e técnico
    (`ficha_preenchida=False`).
    """

    Resultado = Resultado

    class Beneficio(models.TextChoices):
        CESTA_BASICA = 'CESTA BÁSICA', 'Cesta Básica'
        FRALDA = 'FRALDA', 'Fralda'
        ABSORVENTE = 'ABSORVENTE', 'Absorvente'

    class Moradia(models.TextChoices):
        PROPRIA = 'PROPRIA', 'Própria'
        ALUGADA = 'ALUGADA', 'Alugada'
        FINANCIADA = 'FINANCIADA', 'Financiada'
        CEDIDA = 'CEDIDA', 'Cedida'
        INVADIDA = 'INVADIDA', 'Invadida'
        FAVOR = 'FAVOR', 'Morando de favor'

    class Construcao(models.TextChoices):
        ALVENARIA = 'ALVENARIA', 'Alvenaria'
        PLACA = 'PLACA', 'Placa de muro'
        BARRACO = 'BARRACO', 'Barraco lona/madeirite'
        OUTROS = 'OUTROS', 'Outros'

    # 1. Solicitação
    data = models.DateField('Data')
    beneficio_solicitado = models.CharField('Benefício solicitado', max_length=200, choices=Beneficio.choices)

    # I. Identificação
    nome = models.CharField('Nome', max_length=200)
    cpf = texto('CPF', 11)
    data_nascimento = models.DateField('Data de nascimento', null=True, blank=True)
    nome_mae = texto('Nome da mãe')
    endereco = texto('Endereço')
    bairro = texto('Bairro', 100)
    complemento = texto('Complemento', 100)
    telefone = texto('Telefone', 30)
    estado_civil = models.CharField('Estado civil', max_length=12, choices=EstadoCivil.choices, blank=True)

    # II. Composição familiar (as pessoas ficam em MembroFamiliar)
    tempo_uberlandia = texto('Há quanto tempo reside em Uberlândia?', 100)
    naturalidade = texto('Nasceu em', 100)
    morou_outros_lugares = sim_nao('Já morou em outros lugares?')
    outros_lugares = texto('Quais lugares?')
    motivo_mudanca = texto('Motivo da mudança', 300)

    # III. Condição socioeconômica
    pensao_alimenticia = reais('Pensão alimentícia (R$)')
    bpc_loas = reais('BPC/LOAS (R$)')
    pensao_inss = reais('Pensão INSS (R$)')
    aposentadoria = reais('Aposentadoria (R$)')
    bolsa_familia_valor = reais('Bolsa Família (R$)')
    outras_fontes = texto('Outras fontes')
    renda_familiar = reais('Renda familiar (R$)')
    renda_per_capita = reais('Renda per capita (R$)')
    observacoes = models.TextField('Observações', blank=True)

    # IV. Condição de habitabilidade
    moradia = models.CharField('Moradia', max_length=12, choices=Moradia.choices, blank=True)
    moradia_valor = reais('Valor do aluguel ou da parcela (R$)')
    cedida_por = texto('Cedida por')
    tipo_construcao = models.CharField('Tipo de construção', max_length=12, choices=Construcao.choices, blank=True)
    construcao_outros = texto('Outro tipo de construção')
    realidade_habitacao = models.TextField('Realidade da habitação visitada', blank=True)

    # VI. Condições de saúde (a ficha de papel não tem a seção V)
    tem_deficiencia = sim_nao('Há pessoa com deficiência na casa?')
    deficiencia_quem = texto('Quem tem deficiência?')
    deficiencia_fisica = models.BooleanField('Física', default=False)
    deficiencia_mental = models.BooleanField('Mental', default=False)
    deficiencia_auditiva = models.BooleanField('Auditiva', default=False)
    deficiencia_visual = models.BooleanField('Visual', default=False)
    deficiencia_outra = models.BooleanField('Outra', default=False)
    deficiencia_outra_qual = texto('Outra deficiência: qual?')
    gestante = sim_nao('Gestante?')
    gestante_quem = texto('Quem é a gestante?')
    gestante_mes = texto('Mês de gestação', 30)
    enfermidades = sim_nao('Enfermidades?')
    enfermidades_quem = texto('Quem tem enfermidade?')
    acompanhamento_medico = sim_nao('Acompanhamento médico')
    gasto_medicamentos = sim_nao('Uso e gastos com medicamentos')

    # VII. Benefícios sociais
    dmae = sim_nao('DMAE')
    dmae_detalhe = texto('DMAE: detalhe')
    cemig = sim_nao('CEMIG')
    cemig_detalhe = texto('CEMIG: detalhe')
    beneficio_bolsa_familia = sim_nao('Bolsa Família')
    beneficio_bolsa_familia_detalhe = texto('Bolsa Família: detalhe')

    # Abordagens
    abordagem1_data = models.DateField('Data da 1ª abordagem', null=True, blank=True)
    abordagem1_tecnico = texto('Técnico(a) da 1ª abordagem')
    abordagem2_data = models.DateField('Data da 2ª abordagem', null=True, blank=True)
    abordagem2_tecnico = texto('Técnico(a) da 2ª abordagem')

    # VIII. Parecer: em branco até o deferimento
    resultado = models.CharField('Deferido/Indeferido', max_length=15, choices=Resultado.choices, blank=True)
    tecnico_responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Técnico responsável',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='dsfs'
    )
    # Nome do técnico como estava escrito na planilha (sem conta no sistema).
    tecnico_legado = models.CharField('Técnico responsável (histórico)', max_length=200, blank=True)
    ficha_preenchida = models.BooleanField('Ficha preenchida no sistema', default=False, editable=False)

    class Meta:
        ordering = ['-data', '-id']
        verbose_name = 'DSF'
        verbose_name_plural = 'DSF'

    def __str__(self):
        return f'{self.nome} - {self.get_beneficio_solicitado_display()}'

    @property
    def pendente(self):
        """Ficha feita no sistema e ainda sem parecer (só estas podem ser editadas)."""
        return self.ficha_preenchida and not self.resultado

    @property
    def tecnico_nome(self):
        return str(self.tecnico_responsavel) if self.tecnico_responsavel_id else self.tecnico_legado


class MembroFamiliar(models.Model):
    dsf = models.ForeignKey(Dsf, on_delete=models.CASCADE, related_name='membros')
    nome = models.CharField('Nome completo', max_length=200)
    parentesco = texto('Parentesco', 60)
    idade = models.PositiveSmallIntegerField('Idade', null=True, blank=True)
    ocupacao = texto('Profissão/Ocupação', 100)
    escolaridade = texto('Escolaridade', 100)
    renda = reais('Renda (R$)')

    class Meta:
        ordering = ['id']
        verbose_name = 'Pessoa da composição familiar'
        verbose_name_plural = 'Composição familiar'

    def __str__(self):
        return self.nome
