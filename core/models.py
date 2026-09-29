# Archivo: core/models.py
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

PORCENTAJE = [MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))]


class Configuracion(models.Model):
    """Parámetros del negocio editables desde el panel (un solo registro)."""

    porcentaje_anticipo = models.DecimalField(
        "anticipo para reservar (%)", max_digits=5, decimal_places=2, default=Decimal("50"), validators=PORCENTAJE
    )
    dias_retiro_antes = models.PositiveSmallIntegerField("días de retiro antes del evento", default=1)
    dias_devolucion_despues = models.PositiveSmallIntegerField("días de devolución después del evento", default=1)
    dias_cancelacion = models.PositiveSmallIntegerField(
        "días mínimos para cancelar con devolución del anticipo", default=7
    )
    recargo_diario_pct = models.DecimalField(
        "recargo por día de atraso (%)", max_digits=5, decimal_places=2, default=Decimal("20"), validators=PORCENTAJE
    )
    descuento_parejas_activo = models.BooleanField("descuento por parejas activo", default=True)
    minimo_parejas = models.PositiveSmallIntegerField("mínimo de parejas para el descuento", default=10)
    descuento_pct = models.DecimalField(
        "descuento por parejas (%)", max_digits=5, decimal_places=2, default=Decimal("10"), validators=PORCENTAJE
    )

    class Meta:
        verbose_name = "configuración"
        verbose_name_plural = "configuración"

    def __str__(self):
        return "Configuración del negocio"

    def save(self, *args, **kwargs):
        self.pk = 1  # siempre el mismo registro
        super().save(*args, **kwargs)

    @classmethod
    def actual(cls):
        configuracion, _ = cls.objects.get_or_create(pk=1)
        return configuracion