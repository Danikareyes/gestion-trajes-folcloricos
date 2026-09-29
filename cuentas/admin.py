# Archivo: cuentas/admin.py
from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nombre", "cedula_ruc", "telefono", "tipo", "institucion", "bloqueado"]
    list_filter = ["tipo", "bloqueado"]
    search_fields = ["nombre", "cedula_ruc", "telefono", "email", "institucion"]
    readonly_fields = ["creado"]