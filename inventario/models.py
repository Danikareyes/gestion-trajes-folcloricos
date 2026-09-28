from django.conf import settings
from django.db import models
from django.utils.text import slugify

from catalogo.models import Prenda


class UnidadInventario(models.Model):
    class Estado(models.TextChoices):
        DISPONIBLE = "disponible", "Disponible"
        RESERVADO = "reservado", "Reservado"
        ALQUILADO = "alquilado", "Alquilado"
        EN_LAVADO = "en_lavado", "En lavado"
        EN_MANTENIMIENTO = "en_mantenimiento", "En mantenimiento"
        DANADO = "danado", "Dañado"
        BAJA = "baja", "Dado de baja"

    class Condicion(models.TextChoices):
        NUEVO = "nuevo", "Nuevo"
        BUENO = "bueno", "Bueno"
        REGULAR = "regular", "Regular"
        DESGASTADO = "desgastado", "Desgastado"

    class Talla(models.TextChoices):
        XS = "XS", "XS"
        S = "S", "S"
        M = "M", "M"
        L = "L", "L"
        XL = "XL", "XL"
        XXL = "XXL", "XXL"
        UNICA = "U", "Única"
        INF_4 = "4", "Infantil 4"
        INF_6 = "6", "Infantil 6"
        INF_8 = "8", "Infantil 8"
        INF_10 = "10", "Infantil 10"
        INF_12 = "12", "Infantil 12"

    # Transiciones permitidas (SRS, sección 6.2)
    TRANSICIONES = {
        Estado.DISPONIBLE: [Estado.RESERVADO, Estado.EN_MANTENIMIENTO, Estado.BAJA],
        Estado.RESERVADO: [Estado.ALQUILADO, Estado.DISPONIBLE],
        Estado.ALQUILADO: [Estado.EN_LAVADO, Estado.DANADO],
        Estado.EN_LAVADO: [Estado.DISPONIBLE, Estado.EN_MANTENIMIENTO],
        Estado.EN_MANTENIMIENTO: [Estado.DISPONIBLE, Estado.BAJA],
        Estado.DANADO: [Estado.EN_MANTENIMIENTO, Estado.BAJA],
        Estado.BAJA: [],
    }

    prenda = models.ForeignKey(Prenda, on_delete=models.PROTECT, related_name="unidades")
    codigo = models.CharField(
        "código", max_length=40, unique=True, blank=True,
        help_text="Déjalo vacío y se genera solo (ej.: SIE-CAN-M-POL-M-01)",
    )
    talla = models.CharField(max_length=3, choices=Talla.choices)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.DISPONIBLE)
    condicion = models.CharField("condición", max_length=12, choices=Condicion.choices, default=Condicion.BUENO)
    ubicacion = models.CharField("ubicación", max_length=60, blank=True, help_text="Ej.: Percha A3")
    fecha_adquisicion = models.DateField("fecha de adquisición", null=True, blank=True)
    costo_adquisicion = models.DecimalField("costo de adquisición", max_digits=8, decimal_places=2, null=True,
                                            blank=True)
    veces_alquilada = models.PositiveIntegerField(default=0)
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "unidad de inventario"
        verbose_name_plural = "unidades de inventario"

    def __str__(self):
        return f"{self.codigo} · {self.prenda.nombre} talla {self.get_talla_display()}"

    @classmethod
    def transicion_valida(cls, actual, nuevo):
        return nuevo in cls.TRANSICIONES.get(actual, [])

    def generar_codigo(self):
        variante = self.prenda.variante
        partes = [
            slugify(variante.modelo.localidad.region.nombre)[:3],
            slugify(variante.modelo.localidad.nombre)[:3],
            variante.genero[0],
            slugify(self.prenda.nombre)[:3],
            self.talla,
        ]
        prefijo = "-".join(partes).upper()
        numero = UnidadInventario.objects.filter(codigo__startswith=prefijo).count() + 1
        codigo = f"{prefijo}-{numero:02d}"
        while UnidadInventario.objects.filter(codigo=codigo).exists():
            numero += 1
            codigo = f"{prefijo}-{numero:02d}"
        return codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo()
        super().save(*args, **kwargs)


class HistorialEstado(models.Model):
    unidad = models.ForeignKey(UnidadInventario, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(max_length=20, blank=True)
    estado_nuevo = models.CharField(max_length=20)
    motivo = models.CharField(max_length=200)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "cambio de estado"
        verbose_name_plural = "historial de estados"

    def __str__(self):
        return f"{self.unidad.codigo}: {self.estado_anterior or '—'} → {self.estado_nuevo}"


