from django.db import models


class TapDiario(models.Model):
    data = models.DateField('Data', unique=True)
    tap_diario = models.PositiveIntegerField('TAP Diário', default=0)

    class Meta:
        ordering = ['data']
        verbose_name = 'TAP Diário'
        verbose_name_plural = 'TAP Mensal'

    def __str__(self):
        return f'{self.data} - {self.tap_diario}'
