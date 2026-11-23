from django.contrib import admin

from .models import RegistroAdministrativo


@admin.register(RegistroAdministrativo)
class RegistroAdministrativoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'bairro', 'telefone', 'data_atendimento', 'motivo', 'servidor')
    list_filter = ('data_atendimento', 'bairro')
    search_fields = ('nome', 'cpf', 'motivo')
