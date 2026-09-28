from django.conf import settings


def negocio(request):
    """Datos del negocio disponibles en todas las plantillas."""
    return {
        "NOMBRE_NEGOCIO": settings.NOMBRE_NEGOCIO,
        "WHATSAPP_NUMERO": settings.WHATSAPP_NUMERO,
    }
