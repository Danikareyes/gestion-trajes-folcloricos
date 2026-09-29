# Archivo: alquileres/migrations/0001_extension_btree_gist.py
from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Activa la extensión btree_gist, necesaria para impedir fechas cruzadas por unidad."""

    initial = True
    dependencies = []
    operations = [BtreeGistExtension()]