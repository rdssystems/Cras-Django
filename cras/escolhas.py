"""Opções usadas por mais de um app."""
from django.db import models


class SimNao(models.TextChoices):
    NAO = 'NAO', 'Não'
    SIM = 'SIM', 'Sim'


class EstadoCivil(models.TextChoices):
    SOLTEIRO = 'SOLTEIRO', 'Solteiro(a)'
    CASADO = 'CASADO', 'Casado(a)'
    SEPARADO = 'SEPARADO', 'Separado(a)'
    DIVORCIADO = 'DIVORCIADO', 'Divorciado(a)'
    AMASIADO = 'AMASIADO', 'Amasiado(a)'
    VIUVO = 'VIUVO', 'Viúvo(a)'


class Resultado(models.TextChoices):
    """Resultado do deferimento. Em branco = pendente."""

    DEFERIDO = 'DEFERIDO', 'DEFERIDO'
    INDEFERIDO = 'INDEFERIDO', 'INDEFERIDO'


class Solicitacao(models.TextChoices):
    PRIMEIRA_VEZ = 'PRIMEIRA', '1ª vez'
    RENOVACAO = 'RENOVACAO', 'Renovação'
