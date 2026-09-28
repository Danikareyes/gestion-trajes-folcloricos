from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

PRECIO = {"max_digits": 8, "decimal_places": 2, "validators": [MinValueValidator(Decimal("0"))]}


class Region(models.Model):
    nombre = models.CharField("nombre", max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    descripcion = models.TextField("descripción", blank=True)
    imagen = models.ImageField(upload_to="regiones/", blank=True)
    orden = models.PositiveSmallIntegerField(default=0, help_text="Orden en el menú del catálogo")

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "región"
        verbose_name_plural = "regiones"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)


class Localidad(models.Model):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="localidades", verbose_name="región")
    nombre = models.CharField(max_length=80, help_text="Ej.: Cañar, Otavalo, Trajes de gala")
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    descripcion_cultural = models.TextField("descripción cultural", blank=True)
    imagen = models.ImageField(upload_to="localidades/", blank=True)

    class Meta:
        ordering = ["region__orden", "nombre"]
        verbose_name = "localidad"
        verbose_name_plural = "localidades"
        constraints = [models.UniqueConstraint(fields=["region", "nombre"], name="localidad_unica_por_region")]

    def __str__(self):
        return f"{self.nombre} ({self.region})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.region.nombre}-{self.nombre}")
        super().save(*args, **kwargs)


class ModeloTraje(models.Model):
    class Categoria(models.TextChoices):
        DANZA = "danza", "Danza tradicional"
        CERTAMEN = "certamen", "Certamen y reinas"

    localidad = models.ForeignKey(Localidad, on_delete=models.PROTECT, related_name="modelos")
    nombre = models.CharField(max_length=100, help_text="Ej.: Traje de Cañar")
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    categoria = models.CharField("categoría", max_length=10, choices=Categoria.choices, default=Categoria.DANZA)
    descripcion = models.TextField("descripción", blank=True)
    solo_completo = models.BooleanField(
        "solo se alquila completo", default=False,
        help_text="Se activa solo en certámenes: no se ofrecen prendas sueltas (RN-25).",
    )
    activo = models.BooleanField(default=True, help_text="Desmarca para ocultarlo del catálogo")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["localidad__region__orden", "localidad__nombre", "nombre"]
        verbose_name = "modelo de traje"
        verbose_name_plural = "modelos de traje"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        if self.categoria == self.Categoria.CERTAMEN:
            self.solo_completo = True
        super().save(*args, **kwargs)


class VarianteGenero(models.Model):
    class Genero(models.TextChoices):
        MUJER = "mujer", "Mujer"
        HOMBRE = "hombre", "Hombre"
        INFANTIL = "infantil", "Infantil"

    modelo = models.ForeignKey(ModeloTraje, on_delete=models.CASCADE, related_name="variantes")
    genero = models.CharField("género", max_length=10, choices=Genero.choices)
    precio_completo = models.DecimalField("precio traje completo", **PRECIO)
    garantia_completo = models.DecimalField("garantía traje completo", **PRECIO)
    dias_buffer_lavado = models.PositiveSmallIntegerField(
        "días de lavado", default=1, help_text="Días que la prenda no se alquila tras la devolución"
    )
    foto_principal = models.ImageField(upload_to="trajes/", blank=True, help_text="Traje completo con sus accesorios")

    class Meta:
        ordering = ["modelo", "genero"]
        verbose_name = "variante por género"
        verbose_name_plural = "variantes por género"
        constraints = [models.UniqueConstraint(fields=["modelo", "genero"], name="variante_unica_por_genero")]

    def __str__(self):
        return f"{self.modelo} · {self.get_genero_display()}"

    @property
    def suma_prendas(self):
        """Lo que costaría alquilar todas las prendas por separado (para RN-07)."""
        return sum((p.precio_individual * p.cantidad_por_traje for p in self.prendas.all()), Decimal("0"))


class Prenda(models.Model):
    class Tipo(models.TextChoices):
        PRENDA = "prenda", "Prenda"
        ACCESORIO = "accesorio", "Accesorio"

    variante = models.ForeignKey(VarianteGenero, on_delete=models.CASCADE, related_name="prendas")
    nombre = models.CharField(max_length=60, help_text="Ej.: Pollera, Poncho, Collar")
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.PRENDA)
    precio_individual = models.DecimalField("precio individual", **PRECIO)
    garantia_individual = models.DecimalField("garantía individual", default=Decimal("0"), **PRECIO)
    incluida_sin_costo = models.BooleanField(
        "incluida sin costo", default=False, help_text="Marca para collar y aretes que van gratis en el traje completo"
    )
    cantidad_por_traje = models.PositiveSmallIntegerField("cantidad por traje", default=1)
    foto = models.ImageField(upload_to="prendas/", blank=True)

    class Meta:
        ordering = ["variante", "tipo", "nombre"]
        verbose_name = "prenda"
        verbose_name_plural = "prendas"
        constraints = [models.UniqueConstraint(fields=["variante", "nombre"], name="prenda_unica_por_variante")]

    def __str__(self):
        return f"{self.nombre} — {self.variante}"


