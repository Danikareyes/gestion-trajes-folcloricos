# Archivo: cuentas/models.py
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

validar_cedula_ruc = RegexValidator(
    r"^\d{10}(\d{3})?$", "Escribe 10 dígitos (cédula) o 13 dígitos (RUC), sin guiones."
)


class Cliente(models.Model):
    class Tipo(models.TextChoices):
        PERSONA = "persona", "Persona"
        INSTITUCION = "institucion", "Institución educativa"
        GRUPO = "grupo", "Grupo de danza"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cliente", help_text="Solo si el cliente creó su cuenta",
    )
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.PERSONA)
    nombre = models.CharField(max_length=120)
    cedula_ruc = models.CharField("cédula o RUC", max_length=13, unique=True, validators=[validar_cedula_ruc])
    telefono = models.CharField("WhatsApp", max_length=20)
    email = models.EmailField("correo", blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    institucion = models.CharField("institución", max_length=120, blank=True)
    bloqueado = models.BooleanField(default=False, help_text="Un cliente bloqueado no puede reservar en línea")
    notas = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return f"{self.nombre} ({self.cedula_ruc})"