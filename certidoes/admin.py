from django.contrib import admin

from .models import Certidao


@admin.register(Certidao)
class CertidaoAdmin(admin.ModelAdmin):
    list_display = ('data_solicitacao', 'quem_solicitou', 'de_quem', 'cidade', 'data_recebimento', 'data_entrega', 'entregue_para')
    list_filter = ('data_solicitacao', 'data_entrega', 'cidade')
    search_fields = ('quem_solicitou', 'de_quem', 'telefone')
