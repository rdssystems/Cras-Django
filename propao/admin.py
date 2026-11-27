from django.contrib import admin

from .models import PessoaProPao, ProcedimentoProPao, RequerimentoProPao


class PessoaInline(admin.TabularInline):
    model = PessoaProPao
    extra = 0


class ProcedimentoInline(admin.TabularInline):
    model = ProcedimentoProPao
    extra = 0


@admin.register(RequerimentoProPao)
class RequerimentoProPaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'solicitacao', 'data', 'resultado', 'servidor')
    list_filter = ('resultado', 'solicitacao', 'data')
    search_fields = ('nome', 'cpf')
    inlines = [PessoaInline, ProcedimentoInline]
