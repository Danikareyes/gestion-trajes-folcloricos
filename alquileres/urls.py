# Archivo: alquileres/urls.py
from django.urls import path

from . import views

app_name = "alquileres"

urlpatterns = [
    path("mi-reserva/", views.mi_reserva, name="mi_reserva"),
    path("mi-reserva/agregar-traje/<int:variante_id>/", views.agregar_traje, name="agregar_traje"),
    path("mi-reserva/agregar-prenda/<int:diseno_id>/", views.agregar_prenda, name="agregar_prenda"),
    path("mi-reserva/fecha/", views.cambiar_fecha, name="cambiar_fecha"),
    path("mi-reserva/quitar/<int:indice>/", views.quitar, name="quitar"),
    path("mi-reserva/enviar/", views.enviar_reserva, name="enviar"),
    path("reserva/<str:codigo>/", views.reserva_enviada, name="reserva_enviada"),
]