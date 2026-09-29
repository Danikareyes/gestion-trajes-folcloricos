# Archivo: alquileres/carrito.py
"""
Carrito "Mi reserva", guardado en la sesión del navegador.
No requiere cuenta: funciona igual para invitados (RF-17).
Una reserva corresponde a un solo evento, así que tiene una sola fecha.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from catalogo.models import DisenoPrenda, VarianteGenero
from core.models import Configuracion
from inventario.models import UnidadInventario

CLAVE_SESION = "mi_reserva"
CENTAVO = Decimal("0.01")
NOMBRES_TALLA = dict(UnidadInventario.Talla.choices)


def _porcentaje(valor):
    """50.00 → 50 ; 12.50 → 12.5 (para mostrarlo sin ceros de más)."""
    return int(valor) if valor == valor.to_integral_value() else valor.quantize(Decimal("0.1"))


class Carrito:
    def __init__(self, request):
        self.session = request.session
        datos = self.session.get(CLAVE_SESION) or {}
        self.fecha_texto = datos.get("fecha_evento", "")
        self.items = datos.get("items", [])

    def __len__(self):
        return sum(item["cantidad"] for item in self.items)

    @property
    def fecha_evento(self):
        try:
            return date.fromisoformat(self.fecha_texto) if self.fecha_texto else None
        except ValueError:
            return None

    def guardar(self):
        self.session[CLAVE_SESION] = {"fecha_evento": self.fecha_texto, "items": self.items}
        self.session.modified = True

    def fijar_fecha(self, fecha):
        self.fecha_texto = fecha.isoformat()
        self.guardar()

    def cantidad_de(self, tipo, objeto_id, talla):
        return sum(
            item["cantidad"] for item in self.items
            if item["tipo"] == tipo and item["id"] == objeto_id and item["talla"] == talla
        )

    def agregar(self, tipo, objeto_id, talla, cantidad):
        for item in self.items:
            if item["tipo"] == tipo and item["id"] == objeto_id and item["talla"] == talla:
                item["cantidad"] += cantidad
                break
        else:
            self.items.append({"tipo": tipo, "id": objeto_id, "talla": talla, "cantidad": cantidad})
        self.guardar()

    def quitar(self, indice):
        if 0 <= indice < len(self.items):
            self.items.pop(indice)
            if not self.items:
                self.fecha_texto = ""
            self.guardar()

    def vaciar(self):
        self.session.pop(CLAVE_SESION, None)
        self.session.modified = True

    def lineas(self):
        """Líneas con sus objetos del catálogo. Descarta las que ya no existen o se desactivaron."""
        ids_trajes = [item["id"] for item in self.items if item["tipo"] == "traje"]
        ids_disenos = [item["id"] for item in self.items if item["tipo"] == "prenda"]
        variantes = VarianteGenero.objects.filter(pk__in=ids_trajes, modelo__activo=True).select_related(
            "modelo__localidad"
        )
        disenos = DisenoPrenda.objects.filter(
            pk__in=ids_disenos, activo=True, prenda__variante__modelo__activo=True
        ).select_related("prenda__variante__modelo__localidad")
        por_clave = {("traje", v.pk): v for v in variantes}
        por_clave.update({("prenda", d.pk): d for d in disenos})

        resultado = []
        for indice, item in enumerate(self.items):
            objeto = por_clave.get((item["tipo"], item["id"]))
            if objeto is None:
                continue
            if item["tipo"] == "traje":
                datos = {
                    "nombre": str(objeto),
                    "detalle": "Traje completo",
                    "genero": objeto.genero,
                    "foto": objeto.foto_principal,
                    "precio": objeto.precio_completo,
                    "garantia_unitaria": objeto.garantia_completo,
                }
            else:
                datos = {
                    "nombre": f"{objeto.prenda.nombre} · {objeto.nombre}",
                    "detalle": f"Prenda individual · {objeto.prenda.variante.modelo.localidad.nombre}",
                    "genero": None,
                    "foto": objeto.foto,
                    "precio": objeto.prenda.precio_individual,
                    "garantia_unitaria": objeto.prenda.garantia_individual,
                }
            datos.update({
                "indice": indice,
                "tipo": item["tipo"],
                "objeto": objeto,
                "talla": item["talla"],
                "talla_nombre": NOMBRES_TALLA.get(item["talla"], item["talla"]),
                "cantidad": item["cantidad"],
                "subtotal": datos["precio"] * item["cantidad"],
                "garantia": datos["garantia_unitaria"] * item["cantidad"],
            })
            resultado.append(datos)
        return resultado

    def resumen(self, lineas):
        """Vista previa de montos. Los valores finales los calcula Alquiler.recalcular_totales()."""
        configuracion = Configuracion.actual()
        trajes = [linea for linea in lineas if linea["tipo"] == "traje"]
        subtotal = sum((linea["subtotal"] for linea in lineas), Decimal("0"))
        mujeres = sum(linea["cantidad"] for linea in trajes if linea["genero"] == "mujer")
        hombres = sum(linea["cantidad"] for linea in trajes if linea["genero"] == "hombre")

        descuento = Decimal("0")
        if configuracion.descuento_parejas_activo and min(mujeres, hombres) >= configuracion.minimo_parejas:
            subtotal_trajes = sum((linea["subtotal"] for linea in trajes), Decimal("0"))
            descuento = (subtotal_trajes * configuracion.descuento_pct / 100).quantize(CENTAVO, ROUND_HALF_UP)

        total = subtotal - descuento
        anticipo = (total * configuracion.porcentaje_anticipo / 100).quantize(CENTAVO, ROUND_HALF_UP)
        return {
            "subtotal": subtotal,
            "descuento": descuento,
            "total": total,
            "anticipo": anticipo,
            "saldo": total - anticipo,
            "garantia": sum((linea["garantia"] for linea in lineas), Decimal("0")),
            "porcentaje_anticipo": _porcentaje(configuracion.porcentaje_anticipo),
        }