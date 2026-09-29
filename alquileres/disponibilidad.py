# Archivo: alquileres/disponibilidad.py
"""
Disponibilidad de prendas por fecha y talla (RN-09 a RN-12).

Una unidad está ocupada desde el retiro hasta la devolución más los días de lavado
de su traje. Las unidades dañadas, en mantenimiento o dadas de baja nunca cuentan.
"""

from datetime import timedelta

from django.db import transaction
from django.db.backends.postgresql.psycopg_any import DateRange

from core.models import Configuracion
from inventario.models import UnidadInventario

from .models import AsignacionUnidad

ESTADOS_NO_ALQUILABLES = [
    UnidadInventario.Estado.DANADO,
    UnidadInventario.Estado.EN_MANTENIMIENTO,
    UnidadInventario.Estado.BAJA,
]


class SinDisponibilidad(Exception):
    """No hay unidades suficientes para completar el alquiler."""


def fechas_para_evento(fecha_evento):
    """Devuelve (fecha_retiro, fecha_devolucion) según la configuración del negocio."""
    configuracion = Configuracion.actual()
    return (
        fecha_evento - timedelta(days=configuracion.dias_retiro_antes),
        fecha_evento + timedelta(days=configuracion.dias_devolucion_despues),
    )


def periodo_bloqueo(retiro, devolucion, dias_lavado):
    """Rango con el retiro y el último día de lavado incluidos."""
    return DateRange(retiro, devolucion + timedelta(days=dias_lavado + 1), "[)")


def unidades_libres(prenda, talla, retiro, devolucion, diseno=None):
    rango = periodo_bloqueo(retiro, devolucion, prenda.variante.dias_buffer_lavado)
    ocupadas = AsignacionUnidad.objects.filter(activa=True, periodo__overlap=rango).values("unidad_id")
    unidades = (
        UnidadInventario.objects.filter(prenda=prenda, talla__in=[talla, UnidadInventario.Talla.UNICA])
        .exclude(estado__in=ESTADOS_NO_ALQUILABLES)
        .exclude(pk__in=ocupadas)
    )
    if diseno is not None:
        unidades = unidades.filter(diseno=diseno)
    return unidades


def trajes_disponibles(variante, talla, retiro, devolucion):
    """Cuántos trajes completos se pueden armar: el límite lo pone la prenda más escasa."""
    posibles = []
    for prenda in variante.prendas.select_related("variante"):
        libres = unidades_libres(prenda, talla, retiro, devolucion).count()
        posibles.append(libres // max(prenda.cantidad_por_traje, 1))
    return min(posibles) if posibles else 0


def disenos_disponibles(diseno, talla, retiro, devolucion):
    return unidades_libres(diseno.prenda, talla, retiro, devolucion, diseno=diseno).count()


@transaction.atomic
def asignar_unidades(alquiler):
    """
    Bloquea unidades físicas para cada línea que todavía no las tiene.
    Si falta alguna, no se bloquea nada y se lanza SinDisponibilidad con el detalle.
    """
    faltantes = []
    lineas = alquiler.lineas.select_related("variante", "diseno__prenda__variante")
    for linea in lineas:
        if linea.es_traje:
            requeridas = [
                (prenda, None, prenda.cantidad_por_traje * linea.cantidad)
                for prenda in linea.variante.prendas.select_related("variante")
            ]
        else:
            requeridas = [(linea.diseno.prenda, linea.diseno, linea.cantidad)]

        for prenda, diseno, cantidad in requeridas:
            ya_asignadas = linea.asignaciones.filter(activa=True, unidad__prenda=prenda).count()
            necesarias = cantidad - ya_asignadas
            if necesarias <= 0:
                continue
            libres = list(
                unidades_libres(prenda, linea.talla, alquiler.fecha_retiro, alquiler.fecha_devolucion, diseno)
                .select_for_update()[:necesarias]
            )
            if len(libres) < necesarias:
                faltantes.append(
                    f"{prenda.nombre} ({prenda.variante}) talla {linea.get_talla_display()}: "
                    f"faltan {necesarias - len(libres)}"
                )
                continue
            rango = periodo_bloqueo(alquiler.fecha_retiro, alquiler.fecha_devolucion, prenda.variante.dias_buffer_lavado)
            AsignacionUnidad.objects.bulk_create(
                [AsignacionUnidad(linea=linea, unidad=unidad, periodo=rango) for unidad in libres]
            )

    if faltantes:
        raise SinDisponibilidad("; ".join(faltantes))


def liberar_unidades(alquiler):
    """Libera las prendas bloqueadas (por ejemplo, al cancelar)."""
    return AsignacionUnidad.objects.filter(linea__alquiler=alquiler, activa=True).update(activa=False)