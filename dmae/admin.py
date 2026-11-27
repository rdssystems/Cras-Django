from django.contrib import admin

from .models import EvolucaoDmae, IsencaoDmae, MembroDmae


class MembroInline(admin.TabularInline):
    model = MembroDmae
    extra = 0


class EvolucaoInline(admin.TabularInline):
    model = EvolucaoDmae
    extra = 0


@admin.register(IsencaoDmae)
class IsencaoDmaeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'solicitacao', 'codigo_imovel', 'data', 'resultado', 'servidor')
    list_filter = ('resultado', 'solicitacao', 'data')
    search_fields = ('nome', 'cpf', 'codigo_imovel')
    inlines = [MembroInline, EvolucaoInline]
