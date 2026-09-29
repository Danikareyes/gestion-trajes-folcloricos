# Archivo: catalogo/views.py
from urllib.parse import quote

from django.db.models import Max, Min
from django.shortcuts import get_object_or_404, render

from alquileres.carrito import Carrito
from alquileres.disponibilidad import tallas_de_diseno, tallas_de_variante
from alquileres.forms import AgregarPrendaForm, AgregarTrajeForm
from inventario.models import UnidadInventario

from .models import DisenoPrenda, ModeloTraje, Region, TipoPrenda, VarianteGenero

NOMBRES_TALLA = dict(UnidadInventario.Talla.choices)


def _rango(minimo, maximo):
    if minimo is None:
        return "—"
    return f"{minimo}" if minimo == maximo else f"{minimo}–{maximo}"


def medidas_por_talla(variante):
    """Tabla de medidas de referencia (cm) por talla, a partir de las unidades del inventario."""
    filas = (
        UnidadInventario.objects.filter(prenda__variante=variante)
        .exclude(talla=UnidadInventario.Talla.UNICA)
        .values("talla")
        .annotate(
            busto_min=Min("busto_cm"), busto_max=Max("busto_cm"),
            cintura_min=Min("cintura_cm"), cintura_max=Max("cintura_cm"),
            cadera_min=Min("cadera_cm"), cadera_max=Max("cadera_cm"),
            largo_min=Min("largo_cm"), largo_max=Max("largo_cm"),
        )
    )
    orden = [valor for valor, _ in UnidadInventario.Talla.choices]
    tabla = []
    for fila in sorted(filas, key=lambda f: orden.index(f["talla"])):
        medidas = {
            "busto": _rango(fila["busto_min"], fila["busto_max"]),
            "cintura": _rango(fila["cintura_min"], fila["cintura_max"]),
            "cadera": _rango(fila["cadera_min"], fila["cadera_max"]),
            "largo": _rango(fila["largo_min"], fila["largo_max"]),
        }
        if any(valor != "—" for valor in medidas.values()):
            tabla.append({"talla": NOMBRES_TALLA.get(fila["talla"], fila["talla"]), **medidas})
    return tabla


def region(request, slug):
    """Página de una región con dos pestañas: trajes completos y prendas individuales."""
    region = get_object_or_404(Region, slug=slug)
    vista = "prendas" if request.GET.get("vista") == "prendas" else "trajes"
    contexto = {"region": region, "vista": vista}

    if vista == "trajes":
        trajes = (
            ModeloTraje.objects.filter(localidad__region=region, activo=True)
            .select_related("localidad")
            .prefetch_related("variantes")
            .annotate(precio_desde=Min("variantes__precio_completo"))
        )
        localidad = request.GET.get("localidad", "")
        genero = request.GET.get("genero", "")
        if localidad:
            trajes = trajes.filter(localidad__slug=localidad)
        if genero:
            trajes = trajes.filter(variantes__genero=genero).distinct()

        trajes = list(trajes)
        for traje in trajes:
            variantes = list(traje.variantes.all())
            traje.portada = next((v.foto_principal for v in variantes if v.foto_principal), None)
            traje.generos = " · ".join(v.get_genero_display() for v in variantes)

        contexto.update(
            trajes=trajes,
            localidades=region.localidades.all(),
            localidad_activa=localidad,
            genero_activo=genero,
            generos=VarianteGenero.Genero.choices,
        )
    else:
        disenos_region = DisenoPrenda.objects.filter(
            activo=True,
            prenda__tipo_prenda__isnull=False,
            prenda__variante__modelo__activo=True,
            prenda__variante__modelo__solo_completo=False,
            prenda__variante__modelo__localidad__region=region,
        )
        tipos = TipoPrenda.objects.filter(prendas__disenos__in=disenos_region).distinct()
        tipo_slug = request.GET.get("tipo", "")
        tipo = tipos.filter(slug=tipo_slug).first() if tipo_slug else tipos.first()
        disenos = list(
            disenos_region.filter(prenda__tipo_prenda=tipo)
            .select_related("prenda__variante__modelo__localidad")
            if tipo else []
        )
        for diseno in disenos:
            tallas = tallas_de_diseno(diseno)
            diseno.form = AgregarPrendaForm(tallas=tallas, auto_id=f"d{diseno.pk}_%s") if tallas else None
        contexto.update(tipos=tipos, tipo_activo=tipo, disenos=disenos)

    return render(request, "catalogo/region.html", contexto)


def traje(request, slug):
    """Ficha de un traje completo, con selector de género."""
    modelo = get_object_or_404(
        ModeloTraje.objects.select_related("localidad__region"), slug=slug, activo=True
    )
    variantes = list(modelo.variantes.prefetch_related("prendas"))
    genero = request.GET.get("genero", "")
    variante = next((v for v in variantes if v.genero == genero), variantes[0] if variantes else None)

    contexto = {"modelo": modelo, "variantes": variantes, "variante": variante}
    if variante:
        prendas = list(variante.prendas.all())
        contexto["prendas"] = [p for p in prendas if not p.incluida_sin_costo]
        contexto["regalos"] = [p for p in prendas if p.incluida_sin_costo]
        mensaje = (
            f"Hola, quiero consultar la disponibilidad del {modelo.nombre} "
            f"({variante.get_genero_display()}) para mi evento."
        )
        contexto["whatsapp_texto"] = quote(mensaje)
        tallas = tallas_de_variante(variante)
        carrito = Carrito(request)
        contexto["form"] = AgregarTrajeForm(tallas=tallas, initial={"fecha_evento": carrito.fecha_evento})
        contexto["medidas"] = medidas_por_talla(variante)

    return render(request, "catalogo/traje.html", contexto)