# Archivo: core/views.py
import random

from django.shortcuts import render
from django.urls import reverse

from catalogo.models import DisenoPrenda, Region, VarianteGenero

MAXIMO_FOTOS = 12
MINIMO_FOTOS = 4
SEGUNDOS_POR_FOTO = 4


def fotos_para_marquee():
    """Fotos al azar de trajes y diseños activos para la franja de la portada (RF-80)."""
    fotos = []

    variantes = (
        VarianteGenero.objects.exclude(foto_principal="")
        .filter(modelo__activo=True)
        .select_related("modelo")
        .order_by("?")[:MAXIMO_FOTOS]
    )
    for variante in variantes:
        fotos.append({
            "url": variante.foto_principal.url,
            "texto": str(variante),
            "enlace": reverse("catalogo:traje", args=[variante.modelo.slug]) + f"?genero={variante.genero}",
        })

    disenos = (
        DisenoPrenda.objects.exclude(foto="")
        .filter(
            activo=True,
            prenda__tipo_prenda__isnull=False,
            prenda__variante__modelo__activo=True,
            prenda__variante__modelo__solo_completo=False,
        )
        .select_related("prenda__tipo_prenda", "prenda__variante__modelo__localidad__region")
        .order_by("?")[:MAXIMO_FOTOS]
    )
    for diseno in disenos:
        region = diseno.prenda.variante.modelo.localidad.region
        fotos.append({
            "url": diseno.foto.url,
            "texto": f"{diseno.prenda.nombre} {diseno.nombre}",
            "enlace": reverse("catalogo:region", args=[region.slug])
            + f"?vista=prendas&tipo={diseno.prenda.tipo_prenda.slug}",
        })

    random.shuffle(fotos)
    return fotos[:MAXIMO_FOTOS]


def inicio(request):
    fotos = fotos_para_marquee()
    if len(fotos) < MINIMO_FOTOS:
        fotos = []  # con pocas fotos la franja se ve vacía: mejor no mostrarla
    contexto = {
        "regiones": Region.objects.all(),
        "fotos_marquee": fotos,
        "duracion_marquee": max(len(fotos) * SEGUNDOS_POR_FOTO, 20),
    }
    return render(request, "core/inicio.html", contexto)