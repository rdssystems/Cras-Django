from django.contrib import admin

from .models import TapDiario


@admin.register(TapDiario)
class TapDiarioAdmin(admin.ModelAdmin):
    list_display = ('data', 'tap_diario')
    list_filter = ('data',)
