# Archivo: inventario/admin.py
from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import HistorialEstado, UnidadInventario

# Colores de la paleta aprobada: (fondo, texto)
COLORES_ESTADO = {
    "disponible": ("#E3EFE6", "#245A38"),
    "reservado": ("#E0ECF4", "#17557A"),
    "alquilado": ("#F6EAD3", "#7A4E0E"),
    "en_lavado": ("#DDEFF2", "#1E6377"),
    "en_mantenimiento": ("#ECE3F2", "#55306F"),
    "danado": ("#F5E1DD", "#8A2717"),
    "baja": ("#ECE8E4", "#5C534B"),
}


class UnidadInventarioForm(forms.ModelForm):
    motivo_cambio = forms.CharField(
        label="Motivo del cambio de estado", required=False, max_length=200,
        help_text="Obligatorio si cambias el estado. Queda en el historial.",
    )

    class Meta:
        model = UnidadInventario
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.estado_original = self.instance.estado if self.instance.pk else None

    def clean(self):
        datos = super().clean()
        nuevo = datos.get("estado")
        actual = self.estado_original
        if actual and nuevo and nuevo != actual:
            if not UnidadInventario.transicion_valida(actual, nuevo):
                permitidos = ", ".join(
                    UnidadInventario.Estado(e).label for e in UnidadInventario.TRANSICIONES[actual]
                ) or "ninguno (estado final)"
                self.add_error(
                    "estado",
                    f"No se puede pasar de «{UnidadInventario.Estado(actual).label}» a "
                    f"«{UnidadInventario.Estado(nuevo).label}». Permitidos: {permitidos}.",
                )
            if not datos.get("motivo_cambio"):
                self.add_error("motivo_cambio", "Indica el motivo del cambio de estado.")
        return datos


class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    can_delete = False
    fields = ["fecha", "estado_anterior", "estado_nuevo", "motivo", "usuario"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UnidadInventario)
class UnidadInventarioAdmin(admin.ModelAdmin):
    form = UnidadInventarioForm
    list_display = ["codigo", "prenda_nombre", "diseno", "modelo", "talla", "estado_color", "condicion", "ubicacion"]
    list_filter = ["estado", "talla", "condicion", "prenda__tipo_prenda", "prenda__variante__modelo__localidad__region",
                   "prenda__variante__modelo"]
    search_fields = ["codigo", "prenda__nombre", "diseno__nombre", "prenda__variante__modelo__nombre"]
    autocomplete_fields = ["prenda", "diseno"]
    readonly_fields = ["veces_alquilada"]
    inlines = [HistorialEstadoInline]
    fieldsets = [
        (None, {"fields": ["prenda", "diseno", "codigo", "talla", "condicion", "ubicacion"]}),
        ("Medidas", {"fields": [("busto_cm", "cintura_cm", "cadera_cm", "largo_cm")],
                     "description": "Llena solo las que apliquen a la prenda (ej.: una pollera no tiene busto)."}),
        ("Estado", {"fields": ["estado", "motivo_cambio"]}),
        ("Compra y notas", {"classes": ["collapse"],
                            "fields": ["fecha_adquisicion", "costo_adquisicion", "veces_alquilada", "notas"]}),
    ]

    @admin.display(description="prenda", ordering="prenda__nombre")
    def prenda_nombre(self, obj):
        return obj.prenda.nombre

    @admin.display(description="modelo", ordering="prenda__variante__modelo__nombre")
    def modelo(self, obj):
        return obj.prenda.variante

    @admin.display(description="estado", ordering="estado")
    def estado_color(self, obj):
        fondo, texto = COLORES_ESTADO.get(obj.estado, ("#EEE", "#333"))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;font-weight:600">{}</span>',
            fondo, texto, obj.get_estado_display(),
        )

    def save_model(self, request, obj, form, change):
        anterior = form.estado_original
        super().save_model(request, obj, form, change)
        if not change:
            HistorialEstado.objects.create(unidad=obj, estado_anterior="", estado_nuevo=obj.estado,
                                           motivo="Alta en inventario", usuario=request.user)
        elif anterior != obj.estado:
            HistorialEstado.objects.create(unidad=obj, estado_anterior=anterior, estado_nuevo=obj.estado,
                                           motivo=form.cleaned_data["motivo_cambio"], usuario=request.user)