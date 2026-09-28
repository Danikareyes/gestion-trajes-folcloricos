from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("catalogo/<slug:slug>/", views.region, name="region"),
    path("traje/<slug:slug>/", views.traje, name="traje"),
]
