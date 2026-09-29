# Archivo: pagos/models.py
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Pago(models.Model):
    """Cada cobro o devolución se registra por separado (RF-49, RN-22)."""

    class Tipo(models.TextChoices):
        ANTICIPO = "anticipo", "Anticipo"
        SALDO = "saldo", "Saldo"
        GARANTIA = "garantia", "Garantía"
        CARGO = "cargo", "Cargo por daño o faltante"
        DEVOLUCION_GARANTIA = "devolucion_garantia", "Devolución de garantía"

    class Metodo(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        TRANSFERENCIA = "transferencia", "Transferencia"
        PASARELA = "pasarela", "Pasarela de pago"

    class Estado(models.TextChoices):
        POR_VALIDAR = "por_validar", "Por validar"
        VALIDADO = "validado", "Validado"
        RECHAZADO = "rechazado", "Rechazado"

    alquiler = models.ForeignKey("alquileres.Alquiler", on_delete=models.CASCADE, related_name="pagos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.ANTICIPO)
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    metodo = models.CharField("método", max_length=15, choices=Metodo.choices, default=Metodo.TRANSFERENCIA)
    comprobante = models.FileField(upload_to="comprobantes/%Y/%m/", blank=True, help_text="Imagen o PDF")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.POR_VALIDAR)
    motivo_rechazo = models.CharField("motivo del rechazo", max_length=200, blank=True)
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False
    )
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_validacion = models.DateTimeField("fecha de validación", null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "pago"
        verbose_name_plural = "pagos"

    def __str__(self):
        return f"{self.get_tipo_display()} ${self.monto} · {self.alquiler.codigo}"