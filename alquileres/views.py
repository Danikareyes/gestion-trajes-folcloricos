# Archivo: alquileres/views.py
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalogo.models import DisenoPrenda, VarianteGenero
from cuentas.models import Cliente
from pagos.models import Pago

from .carrito import NOMBRES_TALLA, Carrito
from .disponibilidad import (
    SinDisponibilidad, asignar_unidades, disenos_disponibles, fechas_para_evento,
    tallas_de_diseno, tallas_de_variante, trajes_disponibles,
)
from .forms import AgregarPrendaForm, AgregarTrajeForm, FechaForm, ReservaForm
from .models import Alquiler, LineaAlquiler


def _mostrar_errores(request, form):
    for errores in form.errors.values():
        messages.error(request, errores[0])


def _fecha_distinta(request, carrito, fecha):
    if len(carrito) and carrito.fecha_evento and carrito.fecha_evento != fecha:
        messages.error(
            request,
            f"Tu reserva ya es para el {carrito.fecha_evento:%d/%m/%Y}. Cada reserva corresponde a un solo "
            "evento; si necesitas otra fecha, cámbiala desde Mi reserva.",
        )
        return True
    return False


@require_POST
def agregar_traje(request, variante_id):
    variante = get_object_or_404(VarianteGenero.objects.select_related("modelo"), pk=variante_id, modelo__activo=True)
    volver = reverse("catalogo:traje", args=[variante.modelo.slug]) + f"?genero={variante.genero}"
    form = AgregarTrajeForm(request.POST, tallas=tallas_de_variante(variante))
    if not form.is_valid():
        _mostrar_errores(request, form)
        return redirect(volver)

    datos = form.cleaned_data
    carrito = Carrito(request)
    if _fecha_distinta(request, carrito, datos["fecha_evento"]):
        return redirect(volver)

    retiro, devolucion = fechas_para_evento(datos["fecha_evento"])
    en_carrito = carrito.cantidad_de("traje", variante.pk, datos["talla"])
    libres = trajes_disponibles(variante, datos["talla"], retiro, devolucion) - en_carrito
    talla = NOMBRES_TALLA.get(datos["talla"], datos["talla"])
    if libres < datos["cantidad"]:
        messages.error(
            request,
            f"Para esa fecha quedan {max(libres, 0)} traje(s) disponible(s) en talla {talla}. "
            "Prueba otra talla u otra fecha.",
        )
        return redirect(volver)

    carrito.fijar_fecha(datos["fecha_evento"])
    carrito.agregar("traje", variante.pk, datos["talla"], datos["cantidad"])
    messages.success(request, f"Agregaste {variante} talla {talla} a tu reserva.")
    return redirect(volver)


@require_POST
def agregar_prenda(request, diseno_id):
    diseno = get_object_or_404(
        DisenoPrenda.objects.select_related("prenda__tipo_prenda", "prenda__variante__modelo__localidad__region"),
        pk=diseno_id, activo=True, prenda__variante__modelo__activo=True,
        prenda__variante__modelo__solo_completo=False,
    )
    region = diseno.prenda.variante.modelo.localidad.region
    volver = reverse("catalogo:region", args=[region.slug]) + "?vista=prendas"
    if diseno.prenda.tipo_prenda:
        volver += f"&tipo={diseno.prenda.tipo_prenda.slug}"

    form = AgregarPrendaForm(request.POST, tallas=tallas_de_diseno(diseno))
    if not form.is_valid():
        _mostrar_errores(request, form)
        return redirect(volver)

    datos = form.cleaned_data
    carrito = Carrito(request)
    talla = NOMBRES_TALLA.get(datos["talla"], datos["talla"])
    if carrito.fecha_evento:
        retiro, devolucion = fechas_para_evento(carrito.fecha_evento)
        libres = disenos_disponibles(diseno, datos["talla"], retiro, devolucion) - carrito.cantidad_de(
            "prenda", diseno.pk, datos["talla"]
        )
        if libres < datos["cantidad"]:
            messages.error(
                request,
                f"Para el {carrito.fecha_evento:%d/%m/%Y} quedan {max(libres, 0)} unidad(es) de "
                f"{diseno.prenda.nombre} {diseno.nombre} en talla {talla}.",
            )
            return redirect(volver)

    carrito.agregar("prenda", diseno.pk, datos["talla"], datos["cantidad"])
    mensaje = f"Agregaste {diseno.prenda.nombre} {diseno.nombre} talla {talla} a tu reserva."
    if not carrito.fecha_evento:
        mensaje += " Elige la fecha del evento en Mi reserva para confirmar la disponibilidad."
    messages.success(request, mensaje)
    return redirect(volver)


def _pagina_mi_reserva(request, carrito, form_reserva=None):
    lineas = carrito.lineas()
    fecha = carrito.fecha_evento
    retiro = devolucion = None
    todo_disponible = bool(lineas) and fecha is not None
    if fecha:
        retiro, devolucion = fechas_para_evento(fecha)
        for linea in lineas:
            if linea["tipo"] == "traje":
                libres = trajes_disponibles(linea["objeto"], linea["talla"], retiro, devolucion)
            else:
                libres = disenos_disponibles(linea["objeto"], linea["talla"], retiro, devolucion)
            linea["disponible"] = libres >= linea["cantidad"]
            todo_disponible = todo_disponible and linea["disponible"]

    contexto = {
        "lineas": lineas,
        "resumen": carrito.resumen(lineas),
        "fecha_evento": fecha,
        "fecha_retiro": retiro,
        "fecha_devolucion": devolucion,
        "todo_disponible": todo_disponible,
        "form_fecha": FechaForm(initial={"fecha_evento": fecha}),
        "form_reserva": form_reserva or ReservaForm(),
        "datos_transferencia": settings.DATOS_TRANSFERENCIA,
    }
    return render(request, "alquileres/mi_reserva.html", contexto)


def mi_reserva(request):
    return _pagina_mi_reserva(request, Carrito(request))


@require_POST
def cambiar_fecha(request):
    form = FechaForm(request.POST)
    if form.is_valid():
        Carrito(request).fijar_fecha(form.cleaned_data["fecha_evento"])
        messages.success(request, "Fecha actualizada. Revisamos la disponibilidad de cada prenda.")
    else:
        _mostrar_errores(request, form)
    return redirect("alquileres:mi_reserva")


@require_POST
def quitar(request, indice):
    Carrito(request).quitar(indice)
    return redirect("alquileres:mi_reserva")


@require_POST
def enviar_reserva(request):
    carrito = Carrito(request)
    lineas = carrito.lineas()
    if not lineas:
        messages.error(request, "Tu reserva está vacía.")
        return redirect("alquileres:mi_reserva")
    if not carrito.fecha_evento:
        messages.error(request, "Elige la fecha del evento antes de enviar la reserva.")
        return redirect("alquileres:mi_reserva")

    fecha_valida = FechaForm({"fecha_evento": carrito.fecha_evento.isoformat()})
    if not fecha_valida.is_valid():
        _mostrar_errores(request, fecha_valida)
        return redirect("alquileres:mi_reserva")

    form = ReservaForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Revisa los datos marcados en el formulario.")
        return _pagina_mi_reserva(request, carrito, form)

    datos = form.cleaned_data
    cliente = Cliente.objects.filter(cedula_ruc=datos["cedula_ruc"]).first()
    if cliente and cliente.bloqueado:
        messages.error(request, "No es posible completar la reserva en línea. Escríbenos por WhatsApp, por favor.")
        return redirect("alquileres:mi_reserva")

    try:
        with transaction.atomic():
            if cliente is None:
                cliente = Cliente(cedula_ruc=datos["cedula_ruc"])
            cliente.nombre = datos["nombre"]
            cliente.telefono = datos["telefono"]
            cliente.email = datos["email"]
            cliente.tipo = datos["tipo"]
            cliente.institucion = datos["institucion"]
            cliente.save()

            alquiler = Alquiler.objects.create(
                cliente=cliente,
                fecha_evento=carrito.fecha_evento,
                tipo=Alquiler.Tipo.INDIVIDUAL if cliente.tipo == Cliente.Tipo.PERSONA else Alquiler.Tipo.GRUPAL,
                autoriza_uso_imagen=datos["autoriza_uso_imagen"],
            )
            for linea in lineas:
                es_traje = linea["tipo"] == "traje"
                LineaAlquiler.objects.create(
                    alquiler=alquiler,
                    tipo=LineaAlquiler.Tipo.TRAJE if es_traje else LineaAlquiler.Tipo.PRENDA,
                    variante=linea["objeto"] if es_traje else None,
                    diseno=None if es_traje else linea["objeto"],
                    talla=linea["talla"],
                    cantidad=linea["cantidad"],
                )
            alquiler.recalcular_totales()
            asignar_unidades(alquiler)  # si falta algo, se deshace toda la reserva
            Pago.objects.create(
                alquiler=alquiler,
                tipo=Pago.Tipo.ANTICIPO,
                monto=alquiler.anticipo,
                metodo=Pago.Metodo.TRANSFERENCIA,
                comprobante=datos["comprobante"],
            )
    except SinDisponibilidad as error:
        messages.error(
            request,
            f"Mientras completabas tus datos, algunas prendas dejaron de estar disponibles: {error}. "
            "Ajusta tu reserva y vuelve a enviarla.",
        )
        return redirect("alquileres:mi_reserva")

    carrito.vaciar()
    request.session["ultima_reserva"] = alquiler.codigo
    return redirect("alquileres:reserva_enviada", codigo=alquiler.codigo)


def reserva_enviada(request, codigo):
    # Solo quien acaba de enviar la reserva puede ver esta página
    if request.session.get("ultima_reserva") != codigo:
        raise Http404
    alquiler = get_object_or_404(Alquiler.objects.select_related("cliente"), codigo=codigo)
    mensaje = (
        f"Hola, envié la reserva {alquiler.codigo} para el {alquiler.fecha_evento:%d/%m/%Y} "
        f"a nombre de {alquiler.cliente.nombre}."
    )
    contexto = {
        "alquiler": alquiler,
        "lineas": alquiler.lineas.select_related("variante", "diseno__prenda"),
        "whatsapp_texto": quote(mensaje),
        "datos_transferencia": settings.DATOS_TRANSFERENCIA,
    }
    return render(request, "alquileres/reserva_enviada.html", contexto)