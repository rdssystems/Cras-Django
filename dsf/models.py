from django.conf import settings
from django.db import models


class Dsf(models.Model):
    class Resultado(models.TextChoices):
        DEFERIDO = 'DEFERIDO', 'DEFERIDO'
        INDEFERIDO = 'INDEFERIDO', 'INDEFERIDO'

    class Beneficio(models.TextChoices):
        CESTA_BASICA = 'CESTA BÁSICA', 'Cesta Básica'
        FRALDA = 'FRALDA', 'Fralda'
        ABSORVENTE = 'ABSORVENTE', 'Absorvente'

    nome = models.CharField('Nome', max_length=200)
    beneficio_solicitado = models.CharField('Benefício solicitado', max_length=200, choices=Beneficio.choices)
    data = models.DateField('Data')
    resultado = models.CharField('Deferido/Indeferido', max_length=15, choices=Resultado.choices, default=Resultado.DEFERIDO)
    tecnico_responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Técnico responsável',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='dsfs'
    )

    class Meta:
        ordering = ['-data']
        verbose_name = 'DSF Concluído'
        verbose_name_plural = 'DSF Concluídos'

    def __str__(self):
        return f'{self.nome} - {self.get_beneficio_solicitado_display()}'
