from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import DisenoPrenda, Localidad, ModeloTraje, Prenda, Region, TipoPrenda, VarianteGenero


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
    fields = ["genero", "precio_completo", "garantia_completo", "dias_buffer_lavado", "foto_principal", "editar_prendas"]
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


@admin.register(TipoPrenda)
class TipoPrendaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "orden"]
    list_editable = ["orden"]
    prepopulated_fields = {"slug": ["nombre"]}
    search_fields = ["nombre"]


class PrendaInline(admin.TabularInline):
    model = Prenda
    extra = 3
    fields = ["nombre", "tipo_prenda", "tipo", "precio_individual", "garantia_individual",
              "incluida_sin_costo", "cantidad_por_traje", "foto", "editar_disenos"]
    readonly_fields = ["editar_disenos"]

    @admin.display(description="diseños")
    def editar_disenos(self, obj):
        if not obj.pk:
            return "Guarda primero"
        url = reverse("admin:catalogo_prenda_change", args=[obj.pk])
        return format_html('<a href="{}">Diseños y fotos ({})</a>', url, obj.disenos.count())


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


class DisenoPrendaInline(admin.TabularInline):
    model = DisenoPrenda
    extra = 3
    fields = ["nombre", "foto", "vista_previa", "activo"]
    readonly_fields = ["vista_previa"]

    @admin.display(description="vista previa")
    def vista_previa(self, obj):
        if obj.pk and obj.foto:
            return format_html('<img src="{}" style="height:60px;border-radius:6px">', obj.foto.url)
        return "—"


@admin.register(Prenda)
class PrendaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo_prenda", "variante", "precio_individual", "total_disenos", "incluida_sin_costo"]
    list_filter = ["tipo_prenda", "tipo", "incluida_sin_costo", "variante__modelo__localidad__region"]
    search_fields = ["nombre", "variante__modelo__nombre"]
    inlines = [DisenoPrendaInline]

    @admin.display(description="n.º diseños")
    def total_disenos(self, obj):
        return obj.disenos.count()


@admin.register(DisenoPrenda)
class DisenoPrendaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "prenda", "activo"]
    list_filter = ["activo", "prenda__tipo_prenda", "prenda__variante__modelo__localidad__region"]
    search_fields = ["nombre", "prenda__nombre", "prenda__variante__modelo__nombre"]