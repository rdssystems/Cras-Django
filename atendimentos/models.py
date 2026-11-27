from django.conf import settings
from django.db import models
from django.utils import timezone


class RegistroAtendimento(models.Model):
    class Tipo(models.TextChoices):
        PSICOSSOCIAL = 'ATENDIMENTO PSICOSSOCIAL', 'ATENDIMENTO PSICOSSOCIAL'
        ADMINISTRATIVO = 'ATENDIMENTO ADMINISTRATIVO', 'ATENDIMENTO ADMINISTRATIVO'
        ORIENTACAO = 'ORIENTAÇÃO', 'ORIENTAÇÃO'
        OUTRO = 'OUTRO', 'OUTRO'

    MOTIVOS = [
        'ATUALIZAÇÃO CADASTRAL - CADÚNICO',
        'CADASTRO NOVO - CADÚNICO',
        'DMAE',
        'CERTIDÃO DE NASCIMENTO',
        'ORIENTAÇÃO',
        'SEGUNDA VIA RG',
        'CERTIDÃO DE CASAMENTO',
        'PSICOSSOCIAL',
        'FOLHA RESUMO',
        'SOLICITAÇÃO DE CESTA BÁSICA',  # era "CESTA BÁSICA" (renomeado em 26/11/2026, migração 0005)
        'CERTIDÃO DE ÓBITO',
        'ORIENTAÇÃO BPC',
        'CARTEIRINHA DO IDOSO',
        'ORIENTAÇÕES PASSE LIVRE',
        'SOLICITAÇÃO DE CADASTRO EM DOMICÍLIO',
        'PRÓ-PÃO',
        'OUTRO',  # sempre por último
    ]

    data = models.DateField('Data', default=timezone.localdate)
    nome = models.CharField('Nome', max_length=200)
    cpf = models.CharField('CPF', max_length=20, blank=True)
    hora_entrada = models.TimeField('Hora entrada', null=True, blank=True)
    hora_atendimento = models.TimeField('Hora atendimento', null=True, blank=True)
    tipo_atendimento = models.CharField('Tipo de atendimento', max_length=40, choices=Tipo.choices, default=Tipo.ADMINISTRATIVO)
    # Um ou mais motivos (múltipla escolha no "Atender"), separados por SEPARADOR_MOTIVOS.
    motivo = models.CharField('Motivo do atendimento', max_length=300, blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Responsável pelo atendimento',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='registros_atendimento'
    )
    responsavel_legado = models.CharField('Responsável (histórico)', max_length=200, blank=True)
    observacoes = models.TextField('Observações/Pendências', blank=True)
    atendimento_origem = models.ForeignKey(
        'triagem.Atendimento', verbose_name='Atendimento origem (triagem)',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='registros'
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        ordering = ['-data', '-id']
        verbose_name = 'Registro de Atendimento'
        verbose_name_plural = 'Registro de Atendimentos'

    def __str__(self):
        return f'{self.data} - {self.nome} ({self.tipo_atendimento})'

    SEPARADOR_MOTIVOS = '; '

    @classmethod
    def juntar_motivos(cls, escolhidos):
        """Só aceita motivos da lista oficial, na ordem da lista (a ordem dos cliques não importa)."""
        escolhidos = set(escolhidos)
        return cls.SEPARADOR_MOTIVOS.join(m for m in cls.MOTIVOS if m in escolhidos)

    @property
    def motivos(self):
        partes = (self.motivo or '').split(self.SEPARADOR_MOTIVOS.strip())
        return [m.strip() for m in partes if m.strip()]

    @property
    def responsavel_nome(self):
        return str(self.responsavel) if self.responsavel_id else self.responsavel_legado
