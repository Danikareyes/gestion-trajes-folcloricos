# Archivo: pagos/admin.py
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from alquileres.models import Alquiler

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ["alquiler", "tipo", "monto", "metodo", "estado", "ver_comprobante", "fecha"]
    list_filter = ["estado", "tipo", "metodo"]
    search_fields = ["alquiler__codigo", "alquiler__cliente__nombre", "alquiler__cliente__cedula_ruc"]
    autocomplete_fields = ["alquiler"]
    readonly_fields = ["validado_por", "fecha_validacion", "fecha"]
    actions = ["validar_pagos", "rechazar_pagos"]

    @admin.display(description="comprobante")
    def ver_comprobante(self, obj):
        if obj.comprobante:
            return format_html('<a href="{}" target="_blank">Ver</a>', obj.comprobante.url)
        return "—"

    @admin.action(description="Validar los pagos seleccionados")
    def validar_pagos(self, request, queryset):
        validados = 0
        for pago in queryset.filter(estado=Pago.Estado.POR_VALIDAR).select_related("alquiler"):
            pago.estado = Pago.Estado.VALIDADO
            pago.validado_por = request.user
            pago.fecha_validacion = timezone.now()
            pago.save()
            alquiler = pago.alquiler
            if pago.tipo == Pago.Tipo.ANTICIPO and alquiler.estado == Alquiler.Estado.PENDIENTE_PAGO:
                alquiler.estado = Alquiler.Estado.CONFIRMADO
                alquiler.save(update_fields=["estado"])
            validados += 1
        self.message_user(request, f"{validados} pago(s) validado(s). Los anticipos confirman su reserva.")

    @admin.action(description="Rechazar los pagos seleccionados")
    def rechazar_pagos(self, request, queryset):
        rechazados = queryset.filter(estado=Pago.Estado.POR_VALIDAR).update(
            estado=Pago.Estado.RECHAZADO, validado_por=request.user, fecha_validacion=timezone.now()
        )
        self.message_user(
            request,
            f"{rechazados} pago(s) rechazado(s). Abre cada uno y escribe el motivo del rechazo.",
            messages.WARNING,
        )