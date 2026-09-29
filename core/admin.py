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


# Orden del menú del panel: primero lo que se usa a diario y en el orden en que se llena
ORDEN_APPS = ["alquileres", "pagos", "catalogo", "inventario", "cuentas", "core", "auth"]
ORDEN_MODELOS = {
    "catalogo": ["Region", "Localidad", "TipoPrenda", "ModeloTraje", "VarianteGenero", "Prenda", "DisenoPrenda"],
}
_lista_original = admin.AdminSite.get_app_list


def _posicion(lista, valor):
    return lista.index(valor) if valor in lista else len(lista)


def lista_ordenada(self, request, app_label=None):
    apps = _lista_original(self, request, app_label)
    for app in apps:
        orden = ORDEN_MODELOS.get(app["app_label"])
        if orden:
            app["models"].sort(key=lambda modelo: _posicion(orden, modelo["object_name"]))
    apps.sort(key=lambda app: _posicion(ORDEN_APPS, app["app_label"]))
    return apps


admin.AdminSite.get_app_list = lista_ordenada