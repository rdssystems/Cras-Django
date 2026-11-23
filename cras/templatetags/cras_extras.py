import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(caminho):
    """URL do estático com ?v=<data de modificação>: ao editar o CSS/JS o navegador baixa de novo."""
    url = static(caminho)
    arquivo = finders.find(caminho)
    if arquivo:
        url += f'?v={int(os.path.getmtime(arquivo))}'
    return url


@register.filter
def get_item(dicionario, chave):
    if isinstance(dicionario, dict):
        return dicionario.get(chave)
    return None


@register.filter
def split(valor, separador):
    if isinstance(valor, str):
        return valor.split(separador)
    return []


@register.filter
def startswith(valor, prefixo):
    return isinstance(valor, str) and valor.startswith(prefixo)


@register.filter
def status_classe(valor):
    v = str(valor)
    if v.startswith('ATENDIDO'):
        return 'badge-verde'
    if v.startswith('AGUARDANDO'):
        return 'badge-ambar'
    if 'PSICOSSOCIAL' in v:
        return 'badge-azul'
    return 'badge-neutro'
