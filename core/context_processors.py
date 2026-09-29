# Archivo: core/context_processors.py
from django.conf import settings

from alquileres.carrito import Carrito


def negocio(request):
    """Datos disponibles en todas las plantillas: negocio y cantidad de artículos en Mi reserva."""
    return {
        "NOMBRE_NEGOCIO": settings.NOMBRE_NEGOCIO,
        "WHATSAPP_NUMERO": settings.WHATSAPP_NUMERO,
        "CARRITO_CANTIDAD": len(Carrito(request)),
    }