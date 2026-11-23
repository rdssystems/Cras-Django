from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('CRAS', {'fields': ('cargo',)}),
    )
    list_display = ('username', 'first_name', 'last_name', 'cargo', 'is_active', 'is_staff')
    list_filter = ('cargo', 'is_active', 'is_staff')
