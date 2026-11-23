from datetime import datetime

from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.db.models import Max
from django.utils import timezone


def hora_atual():
    return timezone.localtime().time()


class Atendimento(models.Model):
    class Status(models.TextChoices):
        ATENDIDO_TRIAGEM = 'ATENDIDO TRIAGEM / ORIENTAÇÃO', 'ATENDIDO TRIAGEM / ORIENTAÇÃO'
        ATENDIDO = 'ATENDIDO', 'ATENDIDO'
        AGUARDANDO = 'AGUARDANDO ATENDIMENTO', 'AGUARDANDO ATENDIMENTO'
        AGUARDANDO_PSICO = 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL', 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL'
        AGUARDANDO_60 = 'AGUARDANDO ATENDIMENTO 60+', 'AGUARDANDO ATENDIMENTO 60+'
        AGUARDANDO_PSICO_60 = 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL 60+', 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL 60+'
        AGUARDANDO_GESTANTE = 'AGUARDANDO ATENDIMENTO GESTANTE / CRIANÇA DE COLO', 'AGUARDANDO ATENDIMENTO GESTANTE / CRIANÇA DE COLO'
        AGUARDANDO_PSICO_GESTANTE = 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL GESTANTE / CRIANÇA DE COLO', 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL GESTANTE / CRIANÇA DE COLO'
        AGUARDANDO_80 = 'AGUARDANDO ATENDIMENTO 80+', 'AGUARDANDO ATENDIMENTO 80+'
        AGUARDANDO_PSICO_80 = 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL 80+', 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL 80+'
        AGUARDANDO_PCD = 'AGUARDANDO ATENDIMENTO PCD', 'AGUARDANDO ATENDIMENTO PCD'
        AGUARDANDO_PSICO_PCD = 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL PCD', 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL PCD'
        AGUARDANDO_AUTISTA = 'AGUARDANDO ATENDIMENTO AUTISTA', 'AGUARDANDO ATENDIMENTO AUTISTA'
        AGUARDANDO_PSICO_AUTISTA = 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL AUTISTA', 'AGUARDANDO ATENDIMENTO PSICOSSOCIAL AUTISTA'
        LIBRAS = 'LIBRAS', 'LIBRAS'
        LIBRAS_PSICO = 'LIBRAS PSICOSSOCIAL', 'LIBRAS PSICOSSOCIAL'
        REUNIAO = 'REUNIÃO', 'REUNIÃO'

    numero = models.PositiveIntegerField('Número', editable=False, default=0)
    data = models.DateField('Data', default=timezone.localdate)
    nome = models.CharField('Nome', max_length=200)
    cpf = models.CharField('CPF', max_length=20, blank=True)
    # default (e não auto_now_add) para que a importação consiga gravar a hora original da planilha.
    hora_entrada = models.TimeField('Hora entrada', default=hora_atual, null=True, blank=True)
    hora_atendimento = models.TimeField('Hora atendimento', null=True, blank=True)
    status = models.CharField('Status do atendimento', max_length=70, choices=Status.choices, default=Status.AGUARDANDO)
    servidor_triagem = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Servidor triagem',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='triagens'
    )
    servidor1 = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Servidor 1',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='atendimentos_realizados'
    )
    servidor2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Servidor 2',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='atendimentos_apoio'
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        ordering = ['-data', '-id']
        verbose_name = 'Atendimento (Triagem)'
        verbose_name_plural = 'Atendimentos (Triagem)'
        constraints = [
            models.UniqueConstraint(fields=['data', 'numero'], name='triagem_numero_unico_por_dia'),
        ]

    TENTATIVAS_NUMERO = 5

    def __str__(self):
        return f'{self.data} #{self.numero} - {self.nome}'

    def save(self, *args, **kwargs):
        if self.numero:
            return super().save(*args, **kwargs)
        # Duas triagens simultâneas podem calcular o mesmo número; a constraint
        # (data, numero) barra a segunda, que tenta de novo com o próximo livre.
        for tentativa in range(self.TENTATIVAS_NUMERO):
            self.numero = self._proximo_numero()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.numero = 0
                if tentativa == self.TENTATIVAS_NUMERO - 1:
                    raise

    def _proximo_numero(self):
        ultimo = Atendimento.objects.filter(data=self.data).aggregate(m=Max('numero'))['m']
        return (ultimo or 0) + 1

    @property
    def tone(self):
        return tone_do_status(self.status)

    @property
    def etiqueta(self):
        """Qualificador do status (80+, PcD, Libras, Reunião...) sem o 'psicossocial'."""
        return ETIQUETA_DO_STATUS.get(str(self.status))

    @property
    def nivel_prioridade(self):
        return nivel_prioridade(self.status)

    @property
    def prioritario(self):
        return self.nivel_prioridade < NIVEL_GERAL

    @property
    def tempo_espera_min(self):
        if not self.hora_entrada:
            return None
        agora = timezone.localtime()
        entrada = datetime.combine(agora.date(), self.hora_entrada)
        entrada = timezone.make_aware(entrada) if timezone.is_naive(entrada) else entrada
        return max(0, int((agora - entrada).total_seconds() // 60))


FILAS = [
    Atendimento.Status.AGUARDANDO,
    Atendimento.Status.AGUARDANDO_PSICO,
    Atendimento.Status.AGUARDANDO_60,
    Atendimento.Status.AGUARDANDO_PSICO_60,
    Atendimento.Status.AGUARDANDO_GESTANTE,
    Atendimento.Status.AGUARDANDO_PSICO_GESTANTE,
    Atendimento.Status.AGUARDANDO_80,
    Atendimento.Status.AGUARDANDO_PSICO_80,
    Atendimento.Status.AGUARDANDO_PCD,
    Atendimento.Status.AGUARDANDO_PSICO_PCD,
    Atendimento.Status.AGUARDANDO_AUTISTA,
    Atendimento.Status.AGUARDANDO_PSICO_AUTISTA,
    Atendimento.Status.LIBRAS,
    Atendimento.Status.LIBRAS_PSICO,
    Atendimento.Status.REUNIAO,
]

STATUS_FILA = {s.value for s in FILAS}

STATUS_PSICOSSOCIAL = {
    Atendimento.Status.AGUARDANDO_PSICO,
    Atendimento.Status.AGUARDANDO_PSICO_60,
    Atendimento.Status.AGUARDANDO_PSICO_GESTANTE,
    Atendimento.Status.AGUARDANDO_PSICO_80,
    Atendimento.Status.AGUARDANDO_PSICO_PCD,
    Atendimento.Status.AGUARDANDO_PSICO_AUTISTA,
    Atendimento.Status.LIBRAS_PSICO,
}

CARGOS_PSICOSSOCIAL = {'PSICOLOGO', 'ASSISTENTE_SOCIAL'}

_S = Atendimento.Status


# ---------------------------------------------------------------- triagem: tipo de fila + prioridade
# A tela de triagem pergunta duas coisas (fila e prioridade); o banco guarda o status combinado,
# no mesmo vocabulário da planilha ("AGUARDANDO ATENDIMENTO PSICOSSOCIAL 60+").

class TipoFila(models.TextChoices):
    ADMINISTRATIVO = 'ADMINISTRATIVO', 'Atendimento administrativo'
    PSICOSSOCIAL = 'PSICOSSOCIAL', 'Atendimento psicossocial'


SEM_PRIORIDADE = ''
PRIORIDADES = [
    (SEM_PRIORIDADE, 'Sem prioridade'),
    ('60+', '60+'),
    ('80+', '80+'),
    ('PCD', 'PcD'),
    ('AUTISTA', 'Autista'),
    ('GESTANTE', 'Gestante ou criança de colo'),
    ('LIBRAS', 'Libras (pessoa surda)'),
]

# .value: o hash de um membro de Enum vem do nome, então a chave precisa ser str pura.
_ADM, _PSI = TipoFila.ADMINISTRATIVO.value, TipoFila.PSICOSSOCIAL.value
STATUS_DA_FILA = {
    (_ADM, SEM_PRIORIDADE): _S.AGUARDANDO, (_PSI, SEM_PRIORIDADE): _S.AGUARDANDO_PSICO,
    (_ADM, '60+'): _S.AGUARDANDO_60, (_PSI, '60+'): _S.AGUARDANDO_PSICO_60,
    (_ADM, '80+'): _S.AGUARDANDO_80, (_PSI, '80+'): _S.AGUARDANDO_PSICO_80,
    (_ADM, 'PCD'): _S.AGUARDANDO_PCD, (_PSI, 'PCD'): _S.AGUARDANDO_PSICO_PCD,
    (_ADM, 'AUTISTA'): _S.AGUARDANDO_AUTISTA, (_PSI, 'AUTISTA'): _S.AGUARDANDO_PSICO_AUTISTA,
    (_ADM, 'GESTANTE'): _S.AGUARDANDO_GESTANTE, (_PSI, 'GESTANTE'): _S.AGUARDANDO_PSICO_GESTANTE,
    (_ADM, 'LIBRAS'): _S.LIBRAS, (_PSI, 'LIBRAS'): _S.LIBRAS_PSICO,
}

# Ordem de chamada: 80+ -> demais prioritários -> geral; empate pela senha (ordem de chegada).
NIVEL_80, NIVEL_PRIORITARIO, NIVEL_GERAL = 0, 1, 2

STATUS_PRIORIDADE_80 = {s.value for s in (_S.AGUARDANDO_80, _S.AGUARDANDO_PSICO_80)}

STATUS_PRIORITARIOS = {s.value for s in (
    _S.AGUARDANDO_60, _S.AGUARDANDO_PSICO_60,
    _S.AGUARDANDO_PCD, _S.AGUARDANDO_PSICO_PCD,
    _S.AGUARDANDO_AUTISTA, _S.AGUARDANDO_PSICO_AUTISTA,
    _S.AGUARDANDO_GESTANTE, _S.AGUARDANDO_PSICO_GESTANTE,
    _S.LIBRAS, _S.LIBRAS_PSICO,  # pessoa surda conta como PcD
)}

ETIQUETA_DO_STATUS = {
    **{s.value: '80+' for s in (_S.AGUARDANDO_80, _S.AGUARDANDO_PSICO_80)},
    **{s.value: '60+' for s in (_S.AGUARDANDO_60, _S.AGUARDANDO_PSICO_60)},
    **{s.value: 'PcD' for s in (_S.AGUARDANDO_PCD, _S.AGUARDANDO_PSICO_PCD)},
    **{s.value: 'Autista' for s in (_S.AGUARDANDO_AUTISTA, _S.AGUARDANDO_PSICO_AUTISTA)},
    **{s.value: 'Gestante / colo' for s in (_S.AGUARDANDO_GESTANTE, _S.AGUARDANDO_PSICO_GESTANTE)},
    **{s.value: 'Libras' for s in (_S.LIBRAS, _S.LIBRAS_PSICO)},
    _S.REUNIAO.value: 'Reunião',
}


def nivel_prioridade(status):
    status = str(status)
    if status in STATUS_PRIORIDADE_80:
        return NIVEL_80
    if status in STATUS_PRIORITARIOS:
        return NIVEL_PRIORITARIO
    return NIVEL_GERAL


def tone_do_status(status):
    status = str(status)
    if status in {s.value for s in STATUS_PSICOSSOCIAL}:
        return 'azul'
    if any(p in status for p in ('60+', '80+', 'PCD', 'AUTISTA', 'GESTANTE')):
        return 'ambar'
    if status == Atendimento.Status.AGUARDANDO.value:
        return 'teal'
    return 'cinza'


def pode_atender(usuario, status):
    if not usuario.is_authenticated:
        return False
    if status not in STATUS_FILA:
        return False
    if usuario.is_superuser:
        return True
    if status in STATUS_PSICOSSOCIAL:
        return usuario.cargo in CARGOS_PSICOSSOCIAL
    return usuario.cargo is not None


def listas_de_chamada(dia):
    """As duas filas do dia (administrativa e psicossocial), cada uma já na ordem de chamada."""
    administrativo, psicossocial = [], []
    for item in Atendimento.objects.filter(data=dia, status__in=STATUS_FILA):
        (psicossocial if item.status in STATUS_PSICOSSOCIAL else administrativo).append(item)

    def ordem(item):
        return (item.nivel_prioridade, item.numero)

    def fila(chave, tipo, tone, itens):
        esperas = [i.tempo_espera_min for i in itens if i.tempo_espera_min is not None]
        return {
            'chave': chave, 'titulo': tipo.label, 'tone': tone,
            'itens': sorted(itens, key=ordem), 'count': len(itens),
            'espera_max': max(esperas) if esperas else None,
        }

    return [
        fila('administrativo', TipoFila.ADMINISTRATIVO, 'teal', administrativo),
        fila('psicossocial', TipoFila.PSICOSSOCIAL, 'azul', psicossocial),
    ]
