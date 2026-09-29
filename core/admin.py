# Archivo: core/admin.py
from django.contrib import admin

from .models import Configuracion


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Reservas y pagos", {"fields": [
            "porcentaje_anticipo", "dias_retiro_antes", "dias_devolucion_despues",
            "dias_cancelacion", "recargo_diario_pct",
        ]}),
        ("Descuento por parejas", {"fields": ["descuento_parejas_activo", "minimo_parejas", "descuento_pct"]}),
    ]

    def has_add_permission(self, request):
        return not Configuracion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False