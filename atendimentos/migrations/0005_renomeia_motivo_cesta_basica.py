"""Renomeia o motivo "CESTA BÁSICA" para "SOLICITAÇÃO DE CESTA BÁSICA" nos atendimentos já gravados.

O campo `motivo` guarda uma lista separada por "; ". A troca é feita item a item, só quando o item é
exatamente o nome antigo, para não estragar textos que já digam "SOLICITAÇÃO DE CESTA BÁSICA".
"""
from django.db import migrations

ANTIGO = 'CESTA BÁSICA'
NOVO = 'SOLICITAÇÃO DE CESTA BÁSICA'


def trocar_item(motivo, de, para):
    itens = [item.strip() for item in (motivo or '').split(';')]
    if de not in itens:
        return motivo
    return '; '.join(para if item == de else item for item in itens if item)


def _aplicar(apps, de, para):
    RegistroAtendimento = apps.get_model('atendimentos', 'RegistroAtendimento')
    for registro in RegistroAtendimento.objects.filter(motivo__contains=de).only('id', 'motivo'):
        novo = trocar_item(registro.motivo, de, para)
        if novo != registro.motivo:
            RegistroAtendimento.objects.filter(pk=registro.pk).update(motivo=novo)


def renomear(apps, schema_editor):
    _aplicar(apps, ANTIGO, NOVO)


def desfazer(apps, schema_editor):
    _aplicar(apps, NOVO, ANTIGO)


class Migration(migrations.Migration):

    dependencies = [
        ('atendimentos', '0004_alter_registroatendimento_motivo'),
    ]

    operations = [
        migrations.RunPython(renomear, desfazer),
    ]
