# Archivo: alquileres/admin.py
from django.contrib import admin, messages
from django.utils.html import format_html

from pagos.models import Pago

from .disponibilidad import SinDisponibilidad, asignar_unidades, liberar_unidades
from .models import Alquiler, LineaAlquiler

COLORES_ESTADO = {
    "pendiente_pago": ("#FFF4D6", "#7A4E0E"),
    "confirmado": ("#E0ECF4", "#17557A"),
    "entregado": ("#F6EAD3", "#7A4E0E"),
    "devuelto": ("#DDEFF2", "#1E6377"),
    "cerrado": ("#E3EFE6", "#245A38"),
    "cancelado": ("#ECE8E4", "#5C534B"),
}


class LineaAlquilerInline(admin.TabularInline):
    model = LineaAlquiler
    extra = 1
    fields = ["tipo", "variante", "diseno", "talla", "cantidad", "precio_unitario", "subtotal_linea", "unidades"]
    readonly_fields = ["precio_unitario", "subtotal_linea", "unidades"]
    autocomplete_fields = ["variante", "diseno"]

    @admin.display(description="subtotal")
    def subtotal_linea(self, obj):
        return f"${obj.subtotal}" if obj.pk else "—"

    @admin.display(description="prendas bloqueadas")
    def unidades(self, obj):
        if not obj.pk:
            return "—"
        codigos = [a.unidad.codigo for a in obj.asignaciones.filter(activa=True).select_related("unidad")]
        return ", ".join(codigos) if codigos else "Sin asignar"


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    fields = ["tipo", "monto", "metodo", "comprobante", "estado", "motivo_rechazo", "validado_por", "fecha"]
    readonly_fields = ["validado_por", "fecha"]


@admin.register(Alquiler)
class AlquilerAdmin(admin.ModelAdmin):
    list_display = ["codigo", "cliente", "fecha_evento", "fecha_retiro", "estado_color", "total", "anticipo"]
    list_filter = ["estado", "tipo"]
    search_fields = ["codigo", "cliente__nombre", "cliente__cedula_ruc"]
    autocomplete_fields = ["cliente"]
    date_hierarchy = "fecha_evento"
    readonly_fields = ["codigo", "subtotal", "descuento", "total", "anticipo", "saldo", "garantia_total", "creado"]
    fieldsets = [
        (None, {"fields": ["codigo", "cliente", "tipo", "estado"]}),
        ("Fechas", {"fields": ["fecha_evento", "fecha_retiro", "fecha_devolucion", "fecha_devolucion_real"]}),
        ("Montos", {"fields": ["subtotal", "descuento", "recargos", "total", "anticipo", "saldo",
                               "garantia_total", "estado_garantia"]}),
        ("Otros", {"fields": ["autoriza_uso_imagen", "observaciones", "creado"]}),
    ]
    inlines = [LineaAlquilerInline, PagoInline]
    actions = ["cancelar_alquileres", "reintentar_asignacion"]

    @admin.display(description="estado", ordering="estado")
    def estado_color(self, obj):
        fondo, texto = COLORES_ESTADO.get(obj.estado, ("#EEE", "#333"))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;font-weight:600">{}</span>',
            fondo, texto, obj.get_estado_display(),
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        alquiler = form.instance
        alquiler.recalcular_totales()
        if alquiler.estado != Alquiler.Estado.CANCELADO:
            self._asignar(request, alquiler)

    def _asignar(self, request, alquiler):
        try:
            asignar_unidades(alquiler)
        except SinDisponibilidad as error:
            self.message_user(
                request,
                f"{alquiler.codigo}: no hay prendas suficientes para esas fechas. {error}. "
                "La reserva se guardó, pero esas prendas no quedaron bloqueadas.",
                messages.WARNING,
            )

    @admin.action(description="Cancelar y liberar las prendas")
    def cancelar_alquileres(self, request, queryset):
        for alquiler in queryset.exclude(estado=Alquiler.Estado.CANCELADO):
            liberar_unidades(alquiler)
            alquiler.estado = Alquiler.Estado.CANCELADO
            alquiler.save(update_fields=["estado"])
        self.message_user(request, "Alquileres cancelados; sus prendas quedaron libres.")

    @admin.action(description="Volver a intentar bloquear prendas")
    def reintentar_asignacion(self, request, queryset):
        for alquiler in queryset.exclude(estado=Alquiler.Estado.CANCELADO):
            self._asignar(request, alquiler)
        self.message_user(request, "Revisión terminada.")