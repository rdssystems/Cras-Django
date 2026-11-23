from django.contrib import admin

from .models import Atendimento


@admin.register(Atendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'data', 'nome', 'cpf', 'hora_entrada', 'hora_atendimento', 'status', 'servidor_triagem', 'servidor1')
    list_filter = ('data', 'status')
    search_fields = ('nome', 'cpf')
    readonly_fields = ('numero', 'hora_entrada', 'criado_em')
