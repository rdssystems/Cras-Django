from django.contrib import admin

from .models import RegistroAtendimento


@admin.register(RegistroAtendimento)
class RegistroAtendimentoAdmin(admin.ModelAdmin):
    list_display = ('data', 'nome', 'cpf', 'hora_entrada', 'hora_atendimento', 'tipo_atendimento', 'motivo', 'responsavel_nome')
    list_filter = ('data', 'tipo_atendimento')
    search_fields = ('nome', 'cpf', 'motivo')
