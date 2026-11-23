from django.contrib import admin

from .models import Dsf


@admin.register(Dsf)
class DsfAdmin(admin.ModelAdmin):
    list_display = ('nome', 'beneficio_solicitado', 'data', 'resultado', 'tecnico_responsavel')
    list_filter = ('resultado', 'data')
    search_fields = ('nome', 'beneficio_solicitado')
