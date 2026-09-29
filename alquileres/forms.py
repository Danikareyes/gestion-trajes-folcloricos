# Archivo: alquileres/forms.py
from datetime import date

from django import forms
from django.core.validators import FileExtensionValidator

from cuentas.models import Cliente, validar_cedula_ruc
from inventario.models import UnidadInventario

from .disponibilidad import fechas_para_evento

NOMBRES_TALLA = dict(UnidadInventario.Talla.choices)
TAMANO_MAXIMO_COMPROBANTE = 5 * 1024 * 1024  # 5 MB


def validar_fecha_evento(fecha):
    """El retiro (un día antes, según configuración) no puede quedar en el pasado."""
    retiro, _ = fechas_para_evento(fecha)
    if retiro < date.today():
        raise forms.ValidationError(
            "Esa fecha es muy próxima: el retiro quedaría en el pasado. Elige una fecha posterior."
        )
    return fecha


class CampoFecha(forms.DateField):
    def __init__(self, **kwargs):
        kwargs.setdefault("label", "¿Para qué fecha lo necesitas?")
        kwargs.setdefault("widget", forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))
        kwargs.setdefault("validators", [validar_fecha_evento])
        super().__init__(**kwargs)


class ConTallas(forms.Form):
    talla = forms.ChoiceField(label="Talla")
    cantidad = forms.IntegerField(label="Cantidad", min_value=1, max_value=50, initial=1)

    def __init__(self, *args, tallas=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["talla"].choices = [(t, NOMBRES_TALLA.get(t, t)) for t in tallas]


class AgregarTrajeForm(ConTallas):
    fecha_evento = CampoFecha()


class AgregarPrendaForm(ConTallas):
    pass


class FechaForm(forms.Form):
    fecha_evento = CampoFecha(label="Fecha del evento")


class ReservaForm(forms.Form):
    nombre = forms.CharField(label="Nombre completo", max_length=120)
    cedula_ruc = forms.CharField(label="Cédula o RUC", max_length=13, validators=[validar_cedula_ruc])
    telefono = forms.CharField(label="WhatsApp", max_length=20)
    email = forms.EmailField(label="Correo")
    tipo = forms.ChoiceField(label="Reservas como", choices=Cliente.Tipo.choices)
    institucion = forms.CharField(label="Institución o grupo (si aplica)", max_length=120, required=False)
    comprobante = forms.FileField(
        label="Comprobante de la transferencia del anticipo",
        help_text="Imagen o PDF, máximo 5 MB.",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "pdf"])],
    )
    autoriza_uso_imagen = forms.BooleanField(
        label="Opcional: autorizo el uso de fotos con el traje en la página. Puedo retirar esta autorización cuando quiera.",
        required=False,
    )
    acepta_politicas = forms.BooleanField(
        label="Acepto las políticas de alquiler (garantía, atrasos y cancelación) y la política de privacidad."
    )

    def clean_comprobante(self):
        archivo = self.cleaned_data["comprobante"]
        if archivo.size > TAMANO_MAXIMO_COMPROBANTE:
            raise forms.ValidationError("El archivo pesa más de 5 MB. Envía una foto más liviana.")
        return archivo

    def clean(self):
        datos = super().clean()
        if datos.get("tipo") in (Cliente.Tipo.INSTITUCION, Cliente.Tipo.GRUPO) and not datos.get("institucion"):
            self.add_error("institucion", "Escribe el nombre de la institución o del grupo.")
        return datos