"""Campos de modelo repetidos nas fichas (todos opcionais)."""
from django.db import models

from .escolhas import SimNao


def texto(rotulo, tamanho=200):
    return models.CharField(rotulo, max_length=tamanho, blank=True)


def reais(rotulo):
    return models.DecimalField(rotulo, max_digits=10, decimal_places=2, null=True, blank=True)


def sim_nao(rotulo):
    return models.CharField(rotulo, max_length=3, choices=SimNao.choices, blank=True)
