from django.conf import settings
from django.db import models

from cras.escolhas import SimNao


class Certidao(models.Model):
    """Solicitação de 2ª via de certidão: a ficha enviada ao cartório mais o acompanhamento até a entrega.

    Os registros importados da planilha só têm o acompanhamento (`ficha_preenchida=False`).
    """

    # Certidão pedida: (campo, rótulo), na ordem da ficha.
    TIPOS = (
        ('certidao_nascimento', 'Nascimento'),
        ('certidao_casamento', 'Casamento'),
        ('certidao_obito', 'Óbito'),
        ('com_averbacao', 'Com averbação'),
    )

    data_solicitacao = models.DateField('Data solicitação')
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    certidao_nascimento = models.BooleanField('Nascimento', default=False)
    certidao_casamento = models.BooleanField('Casamento', default=False)
    certidao_obito = models.BooleanField('Óbito', default=False)
    com_averbacao = models.BooleanField('Com averbação', default=False)

    # Registrado(a)
    de_quem = models.CharField('De quem', max_length=200)
    filiacao = models.CharField('Filiação', max_length=300, blank=True)
    data_nascimento = models.DateField('Data de nascimento', null=True, blank=True)
    cpf = models.CharField('CPF', max_length=11, blank=True)
    telefone = models.CharField('Telefone', max_length=30, blank=True)
    endereco = models.CharField('Endereço', max_length=200, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    cad_unico = models.CharField('Está cadastrado no CadÚnico?', max_length=3, choices=SimNao.choices, blank=True)
    nis = models.CharField('NIS', max_length=20, blank=True)

    # Responsável que assina a declaração (parente ou cônjuge)
    quem_solicitou = models.CharField('Quem solicitou', max_length=200)
    parentesco = models.CharField('Parentesco', max_length=60, blank=True)

    servidor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Servidor',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='certidoes'
    )

    # Acompanhamento
    data_recebimento = models.DateField('Data recebimento', null=True, blank=True)
    nome_contato = models.CharField('Nome do contato', max_length=200, blank=True)
    contato_em = models.CharField('Contato em', max_length=200, blank=True)
    data_entrega = models.DateField('Data entrega', null=True, blank=True)
    entregue_para = models.CharField('Entregue para', max_length=200, blank=True)
    # Nome do servidor como estava escrito na planilha (sem conta no sistema).
    servidor_legado = models.CharField('Servidor (histórico)', max_length=200, blank=True)
    # Anotações livres; a importação guarda aqui o texto das colunas de data que não era só uma data.
    observacoes = models.TextField('Observações', blank=True)
    ficha_preenchida = models.BooleanField('Ficha preenchida no sistema', default=False, editable=False)

    class Meta:
        ordering = ['-data_solicitacao', '-id']
        verbose_name = 'Certidão'
        verbose_name_plural = 'Certidões'

    def __str__(self):
        return f'{self.de_quem} - solicitado em {self.data_solicitacao}'

    @property
    def servidor_nome(self):
        return str(self.servidor) if self.servidor_id else self.servidor_legado

    @property
    def tipos(self):
        """Ex.: "Nascimento, Casamento, Com averbação"."""
        return ', '.join(rotulo for campo, rotulo in self.TIPOS if getattr(self, campo))
