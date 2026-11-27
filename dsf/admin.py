from django.contrib import admin

from .models import Dsf, MembroFamiliar


class MembroFamiliarInline(admin.TabularInline):
    model = MembroFamiliar
    extra = 0


@admin.register(Dsf)
class DsfAdmin(admin.ModelAdmin):
    list_display = ('nome', 'beneficio_solicitado', 'data', 'resultado', 'tecnico_responsavel')
    list_filter = ('resultado', 'beneficio_solicitado', 'data')
    search_fields = ('nome', 'cpf')
    inlines = [MembroFamiliarInline]
