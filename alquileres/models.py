# Archivo: alquileres/models.py
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from catalogo.models import DisenoPrenda, VarianteGenero
from core.models import Configuracion
from cuentas.models import Cliente
from inventario.models import UnidadInventario

CENTAVO = Decimal("0.01")


def dinero(**extra):
    return models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"), **extra)


class Alquiler(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE_PAGO = "pendiente_pago", "Pendiente de pago"
        CONFIRMADO = "confirmado", "Confirmado"
        ENTREGADO = "entregado", "Entregado"
        DEVUELTO = "devuelto", "Devuelto"
        CERRADO = "cerrado", "Cerrado"
        CANCELADO = "cancelado", "Cancelado"

    class Tipo(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        GRUPAL = "grupal", "Grupal"

    class EstadoGarantia(models.TextChoices):
        POR_COBRAR = "por_cobrar", "Por cobrar"
        RETENIDA = "retenida", "Retenida"
        DEVUELTA = "devuelta", "Devuelta"
        APLICADA = "aplicada", "Aplicada parcialmente"

    codigo = models.CharField("código", max_length=12, unique=True, blank=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="alquileres")
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.INDIVIDUAL)
    fecha_evento = models.DateField("fecha del evento")
    fecha_retiro = models.DateField(
        "fecha de retiro", null=True, blank=True, help_text="Déjala vacía y se calcula según la configuración"
    )
    fecha_devolucion = models.DateField(
        "devolución pactada", null=True, blank=True, help_text="Déjala vacía y se calcula según la configuración"
    )
    fecha_devolucion_real = models.DateField("devolución real", null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE_PAGO)
    subtotal = dinero(editable=False)
    descuento = dinero(editable=False, verbose_name="descuento por parejas")
    recargos = dinero(verbose_name="recargos por atraso")
    total = dinero(editable=False)
    anticipo = dinero(editable=False)
    garantia_total = dinero(editable=False, verbose_name="garantía")
    estado_garantia = models.CharField(
        "estado de la garantía", max_length=12, choices=EstadoGarantia.choices, default=EstadoGarantia.POR_COBRAR
    )
    autoriza_uso_imagen = models.BooleanField("autoriza uso de imagen", default=False)
    observaciones = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False
    )

    class Meta:
        ordering = ["-creado"]
        verbose_name = "alquiler"
        verbose_name_plural = "alquileres"

    def __str__(self):
        return f"{self.codigo or 'Nuevo alquiler'} · {self.cliente.nombre}"

    @property
    def saldo(self):
        return self.total - self.anticipo

    def clean(self):
        if self.fecha_evento and not self.pk and self.fecha_evento < date.today():
            raise ValidationError({"fecha_evento": "La fecha del evento no puede estar en el pasado."})
        if self.fecha_retiro and self.fecha_devolucion and self.fecha_devolucion < self.fecha_retiro:
            raise ValidationError({"fecha_devolucion": "La devolución no puede ser antes del retiro."})

    def save(self, *args, **kwargs):
        if self.fecha_evento and (not self.fecha_retiro or not self.fecha_devolucion):
            configuracion = Configuracion.actual()
            self.fecha_retiro = self.fecha_retiro or self.fecha_evento - timedelta(days=configuracion.dias_retiro_antes)
            self.fecha_devolucion = self.fecha_devolucion or self.fecha_evento + timedelta(
                days=configuracion.dias_devolucion_despues
            )
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f"ALQ-{self.pk:04d}"
            super().save(update_fields=["codigo"])

    def recalcular_totales(self):
        """Subtotal, descuento por parejas (RN-18), total, anticipo (RN-13) y garantía (RN-14)."""
        configuracion = Configuracion.actual()
        lineas = list(self.lineas.select_related("variante", "diseno__prenda"))
        subtotal = sum((linea.subtotal for linea in lineas), Decimal("0"))
        trajes = [linea for linea in lineas if linea.es_traje]
        subtotal_trajes = sum((linea.subtotal for linea in trajes), Decimal("0"))
        mujeres = sum(linea.cantidad for linea in trajes if linea.variante.genero == VarianteGenero.Genero.MUJER)
        hombres = sum(linea.cantidad for linea in trajes if linea.variante.genero == VarianteGenero.Genero.HOMBRE)

        descuento = Decimal("0")
        if configuracion.descuento_parejas_activo and min(mujeres, hombres) >= configuracion.minimo_parejas:
            descuento = (subtotal_trajes * configuracion.descuento_pct / 100).quantize(CENTAVO, ROUND_HALF_UP)

        self.subtotal = subtotal
        self.descuento = descuento
        self.total = subtotal - descuento + self.recargos
        self.anticipo = (self.total * configuracion.porcentaje_anticipo / 100).quantize(CENTAVO, ROUND_HALF_UP)
        self.garantia_total = sum((linea.garantia for linea in lineas), Decimal("0"))
        self.save(update_fields=["subtotal", "descuento", "total", "anticipo", "garantia_total"])


class LineaAlquiler(models.Model):
    class Tipo(models.TextChoices):
        TRAJE = "traje", "Traje completo"
        PRENDA = "prenda", "Prenda individual"

    alquiler = models.ForeignKey(Alquiler, on_delete=models.CASCADE, related_name="lineas")
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.TRAJE)
    variante = models.ForeignKey(
        VarianteGenero, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name="traje", help_text="Solo para traje completo",
    )
    diseno = models.ForeignKey(
        DisenoPrenda, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name="diseño de prenda", help_text="Solo para prenda individual",
    )
    talla = models.CharField(max_length=3, choices=UnidadInventario.Talla.choices)
    cantidad = models.PositiveSmallIntegerField(default=1)
    precio_unitario = dinero(editable=False, verbose_name="precio unitario")

    class Meta:
        verbose_name = "línea del alquiler"
        verbose_name_plural = "líneas del alquiler"

    def __str__(self):
        articulo = self.variante if self.es_traje else self.diseno
        return f"{articulo} · talla {self.get_talla_display()} × {self.cantidad}"

    @property
    def es_traje(self):
        return self.tipo == self.Tipo.TRAJE

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    @property
    def garantia(self):
        if self.es_traje:
            return self.variante.garantia_completo * self.cantidad
        return self.diseno.prenda.garantia_individual * self.cantidad

    def clean(self):
        if self.es_traje and not self.variante:
            raise ValidationError({"variante": "Elige el traje."})
        if not self.es_traje:
            if not self.diseno:
                raise ValidationError({"diseno": "Elige el diseño de la prenda."})
            if self.diseno.prenda.variante.modelo.solo_completo:
                raise ValidationError({"diseno": "Los trajes de certamen solo se alquilan completos (RN-25)."})

    def save(self, *args, **kwargs):
        if self.es_traje:
            self.diseno = None
            self.precio_unitario = self.variante.precio_completo
        else:
            self.variante = None
            self.precio_unitario = self.diseno.prenda.precio_individual
        super().save(*args, **kwargs)


class AsignacionUnidad(models.Model):
    """Unidad física bloqueada para una línea durante el retiro, el uso y el lavado."""

    class Condicion(models.TextChoices):
        CORRECTA = "correcta", "Correcta"
        SUCIA = "sucia", "Sucia"
        DANADA = "danada", "Dañada"
        FALTANTE = "faltante", "Faltante"

    linea = models.ForeignKey(LineaAlquiler, on_delete=models.CASCADE, related_name="asignaciones")
    unidad = models.ForeignKey(UnidadInventario, on_delete=models.PROTECT, related_name="asignaciones")
    periodo = DateRangeField(help_text="Desde el retiro hasta la devolución más los días de lavado")
    activa = models.BooleanField(default=True, help_text="Se desactiva si el alquiler se cancela")
    entregada = models.BooleanField(default=False)
    condicion_retorno = models.CharField(
        "condición al volver", max_length=10, choices=Condicion.choices, blank=True
    )
    cargo = dinero()

    class Meta:
        verbose_name = "unidad asignada"
        verbose_name_plural = "unidades asignadas"
        constraints = [
            ExclusionConstraint(
                name="unidad_sin_fechas_cruzadas",
                expressions=[("unidad", RangeOperators.EQUAL), ("periodo", RangeOperators.OVERLAPS)],
                condition=Q(activa=True),
            ),
        ]

    def __str__(self):
        return f"{self.unidad.codigo} → {self.linea.alquiler.codigo}"