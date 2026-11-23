from django.conf import settings
from django.db import models


class Certidao(models.Model):
    data_solicitacao = models.DateField('Data solicitação')
    quem_solicitou = models.CharField('Quem solicitou', max_length=200)
    de_quem = models.CharField('De quem', max_length=200)
    telefone = models.CharField('Telefone', max_length=30, blank=True)
    servidor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Servidor',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='certidoes'
    )
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    data_recebimento = models.DateField('Data recebimento', null=True, blank=True)
    nome_contato = models.CharField('Nome do contato', max_length=200, blank=True)
    contato_em = models.CharField('Contato em', max_length=200, blank=True)
    data_entrega = models.DateField('Data entrega', null=True, blank=True)
    entregue_para = models.CharField('Entregue para', max_length=200, blank=True)

    class Meta:
        ordering = ['-data_solicitacao']
        verbose_name = 'Certidão'
        verbose_name_plural = 'Certidões'

    def __str__(self):
        return f'{self.de_quem} - solicitado em {self.data_solicitacao}'
