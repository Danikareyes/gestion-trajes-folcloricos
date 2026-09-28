from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Localidad, ModeloTraje, Prenda, Region, VarianteGenero


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["nombre", "orden", "total_localidades"]
    list_editable = ["orden"]
    prepopulated_fields = {"slug": ["nombre"]}

    @admin.display(description="localidades")
    def total_localidades(self, obj):
        return obj.localidades.count()


@admin.register(Localidad)
class LocalidadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "region"]
    list_filter = ["region"]
    search_fields = ["nombre"]
    prepopulated_fields = {"slug": ["nombre"]}


class VarianteGeneroInline(admin.TabularInline):
    model = VarianteGenero
    extra = 1
    fields = ["genero", "precio_completo", "garantia_completo", "dias_buffer_lavado", "foto_principal",
              "editar_prendas"]
    readonly_fields = ["editar_prendas"]

    @admin.display(description="prendas")
    def editar_prendas(self, obj):
        if not obj.pk:
            return "Guarda primero"
        url = reverse("admin:catalogo_variantegenero_change", args=[obj.pk])
        return format_html('<a href="{}">Editar prendas ({})</a>', url, obj.prendas.count())


@admin.register(ModeloTraje)
class ModeloTrajeAdmin(admin.ModelAdmin):
    list_display = ["nombre", "localidad", "region", "categoria", "activo"]
    list_filter = ["localidad__region", "categoria", "activo"]
    list_editable = ["activo"]
    search_fields = ["nombre", "localidad__nombre"]
    prepopulated_fields = {"slug": ["nombre"]}
    readonly_fields = ["solo_completo"]
    inlines = [VarianteGeneroInline]

    @admin.display(description="región", ordering="localidad__region")
    def region(self, obj):
        return obj.localidad.region


class PrendaInline(admin.TabularInline):
    model = Prenda
    extra = 3
    fields = ["nombre", "tipo", "precio_individual", "garantia_individual",
              "incluida_sin_costo", "cantidad_por_traje", "foto"]


@admin.register(VarianteGenero)
class VarianteGeneroAdmin(admin.ModelAdmin):
    list_display = ["__str__", "precio_completo", "suma_por_prendas", "garantia_completo", "total_prendas"]
    list_filter = ["genero", "modelo__localidad__region"]
    search_fields = ["modelo__nombre"]
    readonly_fields = ["suma_por_prendas"]
    inlines = [PrendaInline]

    @admin.display(description="suma por prendas")
    def suma_por_prendas(self, obj):
        suma = obj.suma_prendas
        color = "#245A38" if suma >= obj.precio_completo else "#8A2717"
        return format_html('<span style="color:{}">${}</span>', color, suma)

    @admin.display(description="n.º prendas")
    def total_prendas(self, obj):
        return obj.prendas.count()


@admin.register(Prenda)
class PrendaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "variante", "tipo", "precio_individual", "incluida_sin_costo"]
    list_filter = ["tipo", "incluida_sin_costo", "variante__modelo__localidad__region"]
    search_fields = ["nombre", "variante__modelo__nombre"]


