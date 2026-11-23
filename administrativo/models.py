from django.db import models


class RegistroAdministrativo(models.Model):
    nome = models.CharField('Nome', max_length=200)
    data_nasc = models.DateField('Data nascimento', null=True, blank=True)
    cpf = models.CharField('CPF', max_length=20, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    telefone = models.CharField('Telefone', max_length=30, blank=True)
    data_atendimento = models.DateField('Data atendimento', null=True, blank=True)
    motivo = models.CharField('Motivo do atendimento', max_length=200, blank=True)
    servidor = models.CharField('Servidor', max_length=200, blank=True)

    class Meta:
        ordering = ['nome', 'data_atendimento']
        verbose_name = 'Registro Administrativo'
        verbose_name_plural = 'Atendimentos Administrativos (histórico)'

    def __str__(self):
        return f'{self.nome} - {self.data_atendimento}'
