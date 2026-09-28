from django.shortcuts import render

from catalogo.models import Region


def inicio(request):
    regiones = Region.objects.all()
    return render(request, "core/inicio.html", {"regiones": regiones})
